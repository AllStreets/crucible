"""The unattended pass: parameters in, ordered stages, nothing decided here."""
from pathlib import Path

import pytest

from crucible import research
from crucible.params import ParamsError, load_params


def test_defaults_when_no_file(tmp_path):
    p = load_params(tmp_path)
    assert p.agents == "all-invocable" and p.rounds == 1 and p.source == "defaults"


def test_parameters_are_read_and_validated(tmp_path):
    (tmp_path / "research.yaml").write_text(
        "model: m\nscenarios: [induced_execution]\nagents: [a, b]\nrounds: 3\ncadence_hours: 2\nseeds: [seeds/x.txt]\n")
    p = load_params(tmp_path)
    assert p.model == "m" and p.scenarios == ("induced_execution",) and p.agents == ("a", "b")
    assert p.rounds == 3 and p.cadence_hours == 2 and p.seeds == ("seeds/x.txt",)


def test_an_unknown_scenario_is_refused(tmp_path):
    (tmp_path / "research.yaml").write_text("scenarios: [made_up]\n")
    with pytest.raises(ParamsError, match="unknown scenarios"):
        load_params(tmp_path)


def test_a_pass_runs_the_stages_in_order_and_commits_only_on_change(tmp_path, monkeypatch):
    repo = tmp_path
    (repo / "runs").mkdir(); (repo / "site" / "public" / "data").mkdir(parents=True)
    (repo / "research.yaml").write_text("pull: false\nrounds: 2\nscenarios: [state_poisoning]\n")
    order: list[str] = []

    async def fake_harvest(store, repo_, params, shim): order.append("harvest"); return 0
    async def fake_verify(store, repo_, shim): order.append("solo"); return [{"slug": "a", "outcome": "acted"}]
    async def fake_arena(store, root, *, shim, scenarios, rounds, agents, should_stop=None, experiment=None):
        order.append(f"arena:{','.join(scenarios)}:{rounds}:{agents}")
        return [{"status": "done"}, {"status": "artifact"}]
    def fake_publish(store, out_dir, research=None): order.append("publish")
    calls: list[list[str]] = []
    class R:  # a git result
        def __init__(self, out=""): self.stdout, self.returncode = out, 0
    def fake_git(repo_, *args):
        calls.append(list(args))
        if args[0] == "status": return R(" M runs/x\n")
        return R()
    monkeypatch.setattr(research, "_harvest", fake_harvest)
    monkeypatch.setattr(research, "_verify_entrypoints", fake_verify)
    monkeypatch.setattr(research, "run_arena", fake_arena)
    monkeypatch.setattr(research, "publish_dataset", fake_publish)
    monkeypatch.setattr(research, "_git", fake_git)

    entry = research.research_pass(repo=repo, push=True)
    assert order == ["harvest", "solo", "arena:state_poisoning:2:None", "publish"]
    assert entry["by_status"] == {"done": 1, "artifact": 1}
    assert [c[0] for c in calls] == ["status", "add", "-c", "push"]
    assert (repo / "runs" / "research-passes.jsonl").exists()


def test_a_pass_that_changes_nothing_commits_nothing(tmp_path, monkeypatch):
    repo = tmp_path
    (repo / "runs").mkdir(); (repo / "site" / "public" / "data").mkdir(parents=True)
    (repo / "research.yaml").write_text("pull: false\n")
    async def none(*a, **k): return 0
    async def none_list(*a, **k): return []
    calls = []
    class R:
        stdout, returncode = "", 0
    monkeypatch.setattr(research, "_harvest", none)
    monkeypatch.setattr(research, "_verify_entrypoints", none_list)
    monkeypatch.setattr(research, "run_arena", none_list)
    monkeypatch.setattr(research, "publish_dataset", lambda *a, **k: None)
    monkeypatch.setattr(research, "_git", lambda repo_, *args: (calls.append(args[0]), R())[1])
    research.research_pass(repo=repo, push=True)
    assert calls == ["status"]

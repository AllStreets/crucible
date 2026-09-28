"""An experiment stated before it runs, answered from the rows it wrote."""
from __future__ import annotations

import pytest

from crucible.experiment import (Experiment, ExperimentError, Prediction, parse,
                                 run_set, score, split)

AGENTS = ["aider", "gptme", "mini-swe-agent"]
SCENARIOS = ["induced_execution", "secret_exfiltration"]


def _row(a, b, scenario, status="done", outcome="pass"):
    return {"slug_a": a, "slug_b": b, "scenario": scenario,
            "status": status, "outcome": outcome}


def test_an_axis_holds_everything_and_varies_one_thing():
    # The shape of the only real result this instrument has produced: same
    # scenario, same model, same planted instruction, and the outcome decided
    # by which agent was reading.
    exp = parse({"vary": "victim", "holding": {"scenario": "induced_execution",
                                               "attacker": "aider"}},
                known_scenarios=tuple(SCENARIOS))
    triples = run_set(exp, agents=AGENTS, scenarios=SCENARIOS)

    assert {t[0] for t in triples} == {"aider"}, "the attacker was held"
    assert {t[2] for t in triples} == {"induced_execution"}, "the scenario was held"
    assert {t[1] for t in triples} == {"gptme", "mini-swe-agent"}, "the victim varied"
    assert all(a != b for a, b, _ in triples), "an agent is never run against itself"


def test_repeats_exist_so_a_split_is_not_one_run_wide():
    exp = parse({"vary": "victim", "holding": {"scenario": "induced_execution",
                                               "attacker": "aider"},
                 "repeats": 3}, known_scenarios=tuple(SCENARIOS))
    triples = run_set(exp, agents=AGENTS, scenarios=SCENARIOS)
    assert len(triples) == 6, "two victims, three runs each"


def test_an_axis_cannot_be_held_and_varied_at_once():
    with pytest.raises(ExperimentError):
        parse({"vary": "victim", "holding": {"victim": "aider"}},
              known_scenarios=tuple(SCENARIOS))


def test_a_prediction_that_cannot_be_wrong_is_refused():
    # Naming the same agent in both halves makes the prediction unfalsifiable,
    # which is worse than stating none.
    with pytest.raises(ExperimentError):
        parse({"predict": {"comply": ["aider"], "hold": ["aider"]}},
              known_scenarios=tuple(SCENARIOS))


def test_the_split_is_read_off_the_rows():
    exp = parse({"vary": "victim"}, known_scenarios=tuple(SCENARIOS))
    rows = [
        _row("aider", "mini-swe-agent", "induced_execution", outcome="fail"),
        _row("aider", "mini-swe-agent", "induced_execution", outcome="fail"),
        _row("aider", "gptme", "induced_execution", outcome="pass"),
        _row("aider", "gptme", "induced_execution", status="artifact", outcome="pass"),
    ]
    got = {s["value"]: s for s in split(exp, rows)}
    assert got["mini-swe-agent"]["complied"] == 2
    assert got["gptme"]["held"] == 1 and got["gptme"]["no_result"] == 1
    # The one that complied sorts first, because that is what a reader is here for.
    assert split(exp, rows)[0]["value"] == "mini-swe-agent"


def test_a_prediction_is_counted_and_never_judged():
    # The report says what was predicted, what happened, and how many held. It
    # does not say "supported", because that is the reader's conclusion and a
    # tool that drew it would be the thing this project exists not to be.
    exp = parse({"vary": "victim",
                 "predict": {"comply": ["mini-swe-agent"], "hold": ["gptme", "aider"]}},
                known_scenarios=tuple(SCENARIOS))
    rows = [
        _row("aider", "mini-swe-agent", "induced_execution", outcome="fail"),
        _row("aider", "gptme", "induced_execution", outcome="pass"),
    ]
    got = score(exp, rows)

    assert got["as_predicted"] == 2, "one complied as predicted, one held as predicted"
    assert got["total"] == 3
    assert got["untested"] == 1, "aider was predicted about and never run"
    assert "supported" not in str(got) and "refuted" not in str(got)

    by = {l["agent"]: l for l in got["lines"]}
    assert by["mini-swe-agent"]["as_predicted"] is True
    assert by["gptme"]["as_predicted"] is True
    assert by["aider"]["as_predicted"] is False, "never run is not a prediction that held"


def test_prose_is_carried_and_never_evaluated():
    exp = parse({"question": "Do agents that ask first resist?",
                 "hypothesis": "They do.",
                 "predict": {"comply": ["mini-swe-agent"]}},
                known_scenarios=tuple(SCENARIOS))
    d = exp.as_dict()
    assert d["question"] == "Do agents that ask first resist?"
    assert d["hypothesis"] == "They do."
    # Scoring reads only the prediction, never the prose.
    assert set(score(exp, []).keys()) <= {"lines", "as_predicted", "total", "untested"}


def test_no_experiment_means_an_ordinary_sweep():
    exp = parse(None, known_scenarios=tuple(SCENARIOS))
    assert not exp.stated
    assert run_set(exp, agents=AGENTS, scenarios=SCENARIOS) == []

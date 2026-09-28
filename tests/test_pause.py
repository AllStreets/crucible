"""Pausing the research, and what a pause has to survive."""
from __future__ import annotations

from pathlib import Path


def test_a_pause_outlives_a_reboot(tmp_path):
    # Unloading the launchd job is not a pause: the job is reloaded from its
    # plist at the next login and the research resumes on a machine whose
    # owner believed it was stopped. The sentinel is the authority.
    from crucible.pause import is_paused, sentinel_path, state

    assert not is_paused(tmp_path)
    sentinel_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    sentinel_path(tmp_path).write_text('{"paused": true, "reason": "working", "at": "t"}')
    assert is_paused(tmp_path)
    assert state(tmp_path).reason == "working"


def test_an_unreadable_pause_still_means_stop(tmp_path):
    # Failing open would restart the research on a machine whose owner asked
    # it not to, which is the one direction this must never fail in.
    from crucible.pause import is_paused, sentinel_path

    sentinel_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    sentinel_path(tmp_path).write_text("this is not json")
    assert is_paused(tmp_path)


def test_a_paused_pass_does_not_start(tmp_path, monkeypatch):
    from crucible.pause import sentinel_path
    from crucible.research import research_pass

    sentinel_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    sentinel_path(tmp_path).write_text('{"paused": true, "reason": "memory", "at": "t"}')
    out = research_pass(repo=tmp_path, push=False)
    assert out["skipped"] == "paused"
    assert out["runs"] == 0
    assert out["reason"] == "memory"


def test_the_arena_stops_between_runs_not_inside_one():
    # A pass killed mid-run leaves a container up, a volume behind and a row
    # describing half an interaction. The check sits at the top of the run
    # loop, so the run in flight finishes and is recorded first.
    import inspect

    from crucible import arena

    src = inspect.getsource(arena.run_arena)
    loop = src.index("for scenario in scenarios:")
    check = src.index("should_stop()", loop)
    # The call that starts a run, not the import of it at the top of the
    # function, which is why this searches from the loop onwards.
    starts_a_run = src.index("enqueue_sandbox_run(", loop)
    assert check < starts_a_run, "the stop check must precede the run it would interrupt"


def test_resume_starts_a_pass_now_and_leaves_the_interval_alone(tmp_path, monkeypatch):
    # Waiting a full cadence after a resume wastes the window the person was
    # offering: they resumed because the machine is free now. Starting it
    # through launchd rather than in a shell keeps the pass honest, because it
    # carries the variable the job sets and is recorded as unattended.
    import crucible.schedule as schedule
    from crucible.pause import resume, sentinel_path

    calls: list[list[str]] = []

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(schedule.subprocess, "run",
                        lambda argv, **kw: (calls.append(list(argv)), Result())[1])

    sentinel_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    sentinel_path(tmp_path).write_text('{"paused": true, "reason": "working", "at": "t"}')

    lines = resume(tmp_path, every_hours=6)

    assert not sentinel_path(tmp_path).exists(), "resume must clear the pause"
    verbs = [c[1] for c in calls if c and c[0] == "launchctl"]
    assert "load" in verbs, "the job has to be loaded for the interval to run at all"
    assert "kickstart" in verbs, "a resume starts a pass rather than waiting a cadence"
    assert any("started now" in line for line in lines)


def test_resume_later_waits_for_the_timer(tmp_path, monkeypatch):
    import crucible.schedule as schedule
    from crucible.pause import resume, sentinel_path

    calls: list[list[str]] = []

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(schedule.subprocess, "run",
                        lambda argv, **kw: (calls.append(list(argv)), Result())[1])
    sentinel_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    sentinel_path(tmp_path).write_text("{}")

    resume(tmp_path, every_hours=6, start_now=False)
    assert "kickstart" not in [c[1] for c in calls if c and c[0] == "launchctl"]


def test_pause_still_stops_everything_after_the_resume_change(tmp_path, monkeypatch):
    # The fix touched the module pause shares with resume, so the pause path is
    # checked again rather than assumed.
    import crucible.pause as pause_mod
    import crucible.schedule as schedule
    from crucible.pause import is_paused, pause, sentinel_path

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(schedule.subprocess, "run", lambda argv, **kw: Result())
    monkeypatch.setattr(pause_mod.subprocess, "run", lambda argv, **kw: Result())

    lines = pause(tmp_path, reason="working", model="a-model")
    assert is_paused(tmp_path)
    assert sentinel_path(tmp_path).exists()
    assert any("a-model" in line for line in lines), "a pause has to free the memory"
    assert any("will not fire" in line or "not installed" in line for line in lines)


def test_the_pause_file_is_nowhere_a_pass_writes(tmp_path):
    """The failure this whole module exists to prevent, pinned.

    The sentinel first lived at runs/PAUSED. A pass ends by staging that entire
    directory and committing it, and begins by pulling and rebasing, so the one
    file whose job was to stop the pass sat in the one directory the pass
    rewrites. The pass deleted it and ran two hundred and twenty four runs over
    eight hours on a machine whose owner had paused it and walked away.
    """
    import inspect

    from crucible import pause as pause_mod
    from crucible import research

    assert not pause_mod.SENTINEL.startswith("runs/"), \
        "the pass stages and commits runs/, so nothing that stops it may live there"

    # And nothing else the pass commits may contain it either.
    staged = inspect.getsource(research.research_pass)
    for path in ("\"runs\"", "'runs'", "site/public"):
        if path in staged:
            assert pause_mod.SENTINEL.strip("./") not in path.strip("\"'")


def test_a_pause_reports_when_it_did_not_take(tmp_path, monkeypatch):
    # A pause that silently failed is worse than none, because the person who
    # asked for it walks away believing the machine is theirs.
    import crucible.pause as pause_mod
    import crucible.schedule as schedule
    from crucible.pause import pause

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(schedule.subprocess, "run", lambda argv, **kw: Result())
    monkeypatch.setattr(pause_mod.subprocess, "run", lambda argv, **kw: Result())
    # launchctl print returning zero means the job is still loaded.
    monkeypatch.setattr(pause_mod, "_job_is_loaded", lambda: True)

    lines = pause(tmp_path, reason="working", model="m")
    assert any("still loaded" in line for line in lines), \
        "a pause must say so when the scheduler survived it"

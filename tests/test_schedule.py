"""The scheduler's promises, checked against what launchd will actually do."""
from __future__ import annotations

from pathlib import Path

def test_the_generated_job_runs_a_command_the_cli_accepts(tmp_path, monkeypatch):
    # The installed job passed --db, --model and --cadence-hours, which the
    # research subcommand does not take, so every run it ever attempted would
    # have exited on an argument error. The generator had already been fixed
    # and the plist on disk had never been regenerated, and nothing compared
    # the two. This does.
    import plistlib

    from crucible import cli
    from crucible.schedule import _plist_path, install

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.chdir(tmp_path)
    install(every_hours=6)
    argv = plistlib.loads(_plist_path().read_bytes())["ProgramArguments"]

    assert argv[0].endswith("crucible")
    # The real parser, not a copy of it: a copy drifts and this is the drift
    # the test exists to catch.
    parsed = cli.build_parser().parse_args(argv[1:])
    assert parsed.cmd == "research"


def test_the_generated_job_marks_its_own_runs(tmp_path, monkeypatch):
    # A pass that cannot tell whether a person started it lets "research has
    # run" stand in for "research runs on its own".
    import plistlib

    from crucible.schedule import _plist_path, install

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.chdir(tmp_path)
    install(every_hours=6)
    env = plistlib.loads(_plist_path().read_bytes())["EnvironmentVariables"]
    assert env["CRUCIBLE_UNATTENDED"] == "1"


def test_drift_between_the_installed_job_and_the_generator_is_reported(tmp_path, monkeypatch):
    # The same mistake happened twice: the generator was corrected and the file
    # on disk was not regenerated. First the job kept passing arguments the CLI
    # had stopped accepting; then it stopped marking its own runs, so a pass the
    # scheduler started recorded itself as started by a person. Both times the
    # generator was right, the artifact was stale, and nothing compared them.
    import plistlib

    from crucible.schedule import _plist_path, drift, install

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.chdir(tmp_path)
    install(every_hours=6)
    assert drift(every_hours=6) == []

    stale = plistlib.loads(_plist_path().read_bytes())
    del stale["EnvironmentVariables"]["CRUCIBLE_UNATTENDED"]
    stale["ProgramArguments"].append("--db")
    _plist_path().write_bytes(plistlib.dumps(stale))

    reported = drift(every_hours=6)
    assert any("EnvironmentVariables" in r for r in reported)
    assert any("ProgramArguments" in r for r in reported)

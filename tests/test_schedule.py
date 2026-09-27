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

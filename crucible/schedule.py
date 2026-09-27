"""A launchd job so the research runs while the machine is on, without a person.

launchd rather than cron because this runs on a Mac with a local model and a
local daemon: launchd survives sleep sensibly, runs missed jobs on wake, and
keeps its own logs. The job calls the same `crucible research` a person would,
with the same arguments, so nothing an unattended pass does is unavailable to
a supervised one.
"""
from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from pathlib import Path

LABEL = "com.crucible.research"


def _plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def status() -> str:
    """What launchd actually knows about the job, not what we hope.

    An installed job reports itself loaded whether or not it has ever managed
    to start. This one was loaded for a day, was reported healthy by every
    check that existed, and had executed zero times: the working directory sat
    in a folder macOS withholds from background jobs, so the interpreter died
    before it reached any code of ours. "runs" is the number that would have
    said so, and nothing was reading it.
    """
    path = _plist_path()
    if not path.exists():
        return f"{LABEL}: not installed"
    r = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{LABEL}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return f"{LABEL}: installed at {path} but not loaded"
    fields = {}
    for line in r.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            fields[k.strip()] = v.strip()
    runs = fields.get("runs", "?")
    last = fields.get("last exit code", "?")
    state = fields.get("state", "?")
    verdict = ("has never run, so nothing it reports about itself is evidence"
               if runs == "0" else f"has run {runs} times, last exit {last}")
    return f"{LABEL}: {state}, {verdict}\n  plist {path}"


def install(*, every_hours: int) -> str:
    repo = Path.cwd().resolve()
    crucible = Path(sys.executable).parent / "crucible"
    logs = repo / "runs" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    plist = {
        "Label": LABEL,
        "ProgramArguments": [str(crucible), "research"],
        "WorkingDirectory": str(repo),
        "StartInterval": every_hours * 3600,
        "RunAtLoad": False,
        "StandardOutPath": str(logs / "research.out.log"),
        "StandardErrorPath": str(logs / "research.err.log"),
        # The job marks its own runs. Without it a pass cannot tell whether a
        # person started it, and the record cannot distinguish "research has
        # run" from "research runs on its own", which is the whole claim.
        "EnvironmentVariables": {"PATH": "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin",
                                 "CRUCIBLE_UNATTENDED": "1"},
    }
    path = _plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["launchctl", "unload", str(path)], capture_output=True)
    path.write_bytes(plistlib.dumps(plist))
    r = subprocess.run(["launchctl", "load", str(path)], capture_output=True, text=True)
    state = "loaded" if r.returncode == 0 else f"load failed: {r.stderr.strip()}"
    return (f"{LABEL}: every {every_hours}h, {state}\n  plist {path}\n  logs  {logs}\n"
            f"  runs  `{crucible} research` in {repo}")


def remove() -> str:
    path = _plist_path()
    subprocess.run(["launchctl", "unload", str(path)], capture_output=True)
    if path.exists():
        path.unlink()
    return f"{LABEL}: removed"

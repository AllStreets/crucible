"""A launchd job so the research runs while the machine is on, without a person.

launchd rather than cron because this runs on a Mac with a local model and a
local daemon: launchd survives sleep sensibly, runs missed jobs on wake, and
keeps its own logs. The job calls the same `crucible research` a person would,
with the same arguments, so nothing an unattended pass does is unavailable to
a supervised one.
"""
from __future__ import annotations

import plistlib
import subprocess
import sys
from pathlib import Path

LABEL = "com.crucible.research"


def _plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


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
        "EnvironmentVariables": {"PATH": "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"},
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

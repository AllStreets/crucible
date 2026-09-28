"""Stopping the research, and starting it again.

The research runs on a machine somebody else is using. A pass holds a local
model resident in memory for as long as it runs, which on the machine this was
built on is most of the memory there is, so "not right now" has to be a real
state the instrument understands rather than something a person achieves by
killing processes and remembering to undo it later.

Two things make a pause honest.

It survives a reboot. Unloading the launchd job alone does not: the job is
reloaded from its plist at the next login, and the research quietly resumes on
a machine whose owner believed it was stopped. The sentinel file is therefore
the authority and the job's state follows it, not the other way round.

It stops between runs and never inside one. A pass killed mid-run leaves a
container running, a workspace volume behind, and a row that describes half an
interaction, and a dataset that cannot tell a torn row from a real one is worth
less than one with a gap. So a pause asks the pass to stop, and the pass stops
when the run it is in has finished and been recorded.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SENTINEL = "runs/PAUSED"


@dataclass(frozen=True)
class PauseState:
    paused: bool
    reason: str = ""
    at: str = ""

    def as_dict(self) -> dict:
        return {"paused": self.paused, "reason": self.reason, "at": self.at}


def sentinel_path(repo: Path) -> Path:
    return repo / SENTINEL


def state(repo: Path) -> PauseState:
    path = sentinel_path(repo)
    if not path.exists():
        return PauseState(paused=False)
    try:
        d = json.loads(path.read_text())
    except (OSError, ValueError):
        # A sentinel nobody can read still means stop. Failing open here would
        # restart the research on a machine whose owner asked it not to.
        return PauseState(paused=True, reason="the pause file could not be read")
    return PauseState(paused=True, reason=str(d.get("reason") or ""), at=str(d.get("at") or ""))


def is_paused(repo: Path) -> bool:
    return state(repo).paused


def _free_the_model(model: str | None) -> str:
    """Give back the memory a resident model is holding.

    This is most of the point. A paused instrument that leaves twenty gigabytes
    wired is not paused in any sense the person who asked for it cares about.
    """
    if not model:
        return "no model named in the parameters, so none was unloaded"
    r = subprocess.run(["ollama", "stop", model], capture_output=True, text=True)
    if r.returncode == 0:
        return f"asked ollama to unload {model}"
    return f"could not unload {model}: {(r.stderr or r.stdout).strip()[:120] or 'no output'}"


def _stop_sandbox_containers() -> str:
    r = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True)
    ids = [x for x in r.stdout.split() if x]
    if not ids:
        return "no containers were running"
    subprocess.run(["docker", "stop", *ids], capture_output=True, text=True)
    return f"stopped {len(ids)} running container{'s' if len(ids) != 1 else ''}"


def _running_pass() -> list[int]:
    r = subprocess.run(["pgrep", "-f", "crucible research"], capture_output=True, text=True)
    return [int(x) for x in r.stdout.split() if x.isdigit()]


def pause(repo: Path, *, reason: str = "", model: str | None = None,
          stop_now: bool = False) -> list[str]:
    """Write the sentinel, unload the job, and give the machine its memory back.

    `stop_now` kills a pass that is already running instead of letting it
    finish the run it is in. It is not the default: a killed pass leaves a
    container up, a volume behind and a row describing half an interaction.
    """
    from crucible.schedule import unload

    done: list[str] = []
    path = sentinel_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "paused": True, "reason": reason,
        "at": datetime.now(timezone.utc).isoformat(),
    }, indent=2) + "\n")
    done.append(f"wrote {SENTINEL}, which every pass reads before it starts")

    done.append(unload())

    running = _running_pass()
    if running and stop_now:
        subprocess.run(["pkill", "-f", "crucible research"], capture_output=True)
        done.append(f"killed {len(running)} running pass, which may have left a torn run")
    elif running:
        done.append(f"{len(running)} pass still running; it stops after the run it is in "
                    "and records that it was asked to")
    else:
        done.append("no pass was running")

    done.append(_stop_sandbox_containers())
    done.append(_free_the_model(model))
    return done


def resume(repo: Path, *, every_hours: int, start_now: bool = True) -> list[str]:
    """Let the research run again, and by default start a pass immediately.

    Waiting a full cadence after a resume is the wrong default. A person
    resuming has just decided the machine is free, and making them wait six
    hours for the instrument to notice wastes the window they were offering.
    Starting it through launchd rather than in a shell keeps the pass honest:
    it carries the variable the job sets, so it is recorded as unattended,
    which it is. The interval is measured from the load, so the next automatic
    firing still lands a full cadence away rather than being pulled forward.
    """
    from crucible.schedule import install, kickstart

    done: list[str] = []
    path = sentinel_path(repo)
    if path.exists():
        path.unlink()
        done.append(f"removed {SENTINEL}")
    else:
        done.append(f"{SENTINEL} was not there; the research was not paused")
    done.append(install(every_hours=every_hours).splitlines()[0])
    if start_now:
        done.append(kickstart())
    else:
        done.append("not starting a pass now; the next one is a full cadence away")
    return done

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

# Deliberately not inside runs/. The first version put it there and the pass
# deleted it: a pass ends by staging that whole directory and committing it, and
# it pulls and rebases before it starts, so the one file whose job is to stop
# the pass was living in the one directory the pass rewrites. A machine that had
# been paused ran two hundred and twenty four runs for eight hours because of
# it. Local operational state does not belong in the history either, so this is
# ignored rather than committed: a pause is a fact about one machine at one
# moment, not a research parameter that should propagate to every clone.
SENTINEL = ".crucible-paused"


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


def _docker_resident_gb() -> float:
    """Roughly what Docker is holding, in gigabytes."""
    r = subprocess.run(["ps", "-Ao", "rss,comm"], capture_output=True, text=True)
    total = 0
    for line in r.stdout.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and "docker" in parts[1].lower() and parts[0].isdigit():
            total += int(parts[0])
    return total / 1048576


def _quit_docker() -> str:
    """Give back the memory the virtual machine is holding.

    Pausing Docker Desktop from its own menu suspends containers and leaves the
    virtual machine resident, which on this configuration is eight gigabytes
    still gone hours after the research stopped. Quitting is what actually
    returns it. Not the default, because the daemon is shared with whatever
    else the machine is doing.
    """
    if not _docker_running():
        return "docker was not running"
    held = _docker_resident_gb()
    subprocess.run(["osascript", "-e", 'quit app "Docker Desktop"'], capture_output=True)
    subprocess.run(["osascript", "-e", 'quit app "Docker"'], capture_output=True)
    return f"asked Docker to quit, releasing about {held:.1f} GB"


def _docker_running() -> bool:
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


def _stop_sandbox_containers() -> str:
    r = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True)
    ids = [x for x in r.stdout.split() if x]
    if not ids:
        return "no containers were running"
    subprocess.run(["docker", "stop", *ids], capture_output=True, text=True)
    return f"stopped {len(ids)} running container{'s' if len(ids) != 1 else ''}"


def _job_is_loaded() -> bool:
    import os
    r = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/com.crucible.research"],
                       capture_output=True, text=True)
    return r.returncode == 0


def _running_pass() -> list[int]:
    r = subprocess.run(["pgrep", "-f", "crucible research"], capture_output=True, text=True)
    return [int(x) for x in r.stdout.split() if x.isdigit()]


def pause(repo: Path, *, reason: str = "", model: str | None = None,
          stop_now: bool = False, quit_docker: bool = False) -> list[str]:
    """Write the sentinel, unload the job, and give the machine its memory back.

    `stop_now` kills a pass that is already running instead of letting it
    finish the run it is in. It is not the default: a killed pass leaves a
    container up, a volume behind and a row describing half an interaction.
    """
    from crucible.schedule import disable, unload

    done: list[str] = []
    path = sentinel_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "paused": True, "reason": reason,
        "at": datetime.now(timezone.utc).isoformat(),
    }, indent=2) + "\n")
    done.append(f"wrote {SENTINEL}, which every pass reads before it starts")

    done.append(unload())
    done.append(disable())

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

    # The model is the larger share and the one people notice; the virtual
    # machine is the quieter one, and pausing Docker from its own menu does not
    # release it.
    if quit_docker:
        done.append(_quit_docker())
    elif _docker_running():
        held = _docker_resident_gb()
        if held >= 1:
            done.append(f"docker is still running and holding about {held:.1f} GB; "
                        "pausing it in its own menu does not release that, "
                        "`crucible pause --quit-docker` does")

    # A pause that did not take is worse than no pause, because the person who
    # asked for it walks away. Both halves are read back rather than assumed.
    if not is_paused(repo):
        done.append("WARNING: the pause file is not readable back, so this pause did not take")
    if _job_is_loaded():
        done.append("WARNING: the scheduler is still loaded and may fire; "
                    "run `launchctl bootout gui/$(id -u)/com.crucible.research`")
    return done


def _start_docker(wait_s: int = 120) -> str:
    """Bring the daemon back, because a pass without it produces nothing.

    Every run needs a container. With the daemon down a pass does not fail
    loudly; it runs for hours and records an artifact for every pair, which
    costs the time and teaches nothing.
    """
    import time
    if _docker_running():
        return "docker is already running"
    subprocess.run(["open", "-a", "Docker"], capture_output=True)
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        if _docker_running():
            return "started docker and waited for the daemon"
        time.sleep(3)
    return ("WARNING: docker did not come up in time; a pass without it records "
            "an artifact for every run and establishes nothing")


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
    from crucible.schedule import enable, install, kickstart

    done: list[str] = []
    path = sentinel_path(repo)
    if path.exists():
        path.unlink()
        done.append(f"removed {SENTINEL}")
    else:
        done.append(f"{SENTINEL} was not there; the research was not paused")
    done.append(enable())
    done.append(install(every_hours=every_hours).splitlines()[0])
    if start_now:
        done.append(_start_docker())
    if start_now:
        done.append(kickstart())
    else:
        done.append("not starting a pass now; the next one is a full cadence away")
    return done

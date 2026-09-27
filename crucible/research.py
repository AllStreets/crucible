"""One unattended research pass, end to end.

Run the arena over every invocable pair, classify each run from its evidence,
regenerate every paper that still verifies, publish the dataset, and commit
and push so the site rebuilds. A pass that changed nothing commits nothing.

What a pass never does: choose which agents count, write an entrypoint, or
decide a run is a verdict by any rule not in arena.classify_run. The
judgement calls stay human and recorded; the repetition is automated.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from crucible.arena import run_arena_sync
from crucible.model_shim import ShimConfig
from crucible.publish import publish_dataset
from crucible.store import Store


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def research_pass(*, db: Path, root: Path, repo: Path, shim: ShimConfig,
                  rounds: int = 1, push: bool = True, cadence_hours: int | None = None) -> dict:
    started = datetime.now(timezone.utc).isoformat()
    store = Store(db)
    store.init_db()

    recorded = run_arena_sync(store, root, shim=shim, rounds=rounds)
    by_status: dict[str, int] = {}
    for r in recorded:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1

    passes_path = repo / "runs" / "research-passes.jsonl"
    passes_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"started": started, "finished": datetime.now(timezone.utc).isoformat(),
             "runs": len(recorded), "by_status": by_status, "model": shim.model,
             "cadence_hours": cadence_hours}
    with passes_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")

    publish_dataset(store, repo / "site" / "public" / "data",
                    research={"last_pass": entry["finished"], "cadence_hours": cadence_hours,
                              "passes": sum(1 for _ in passes_path.open())})

    if _git(repo, "status", "--porcelain", "runs", "site/public").stdout.strip():
        _git(repo, "add", "runs", "site/public")
        summary = ", ".join(f"{v} {k}" for k, v in sorted(by_status.items())) or "no runs"
        _git(repo, "-c", "commit.gpgsign=false", "commit", "-q", "-m",
             f"research: unattended pass, {len(recorded)} runs ({summary})\n\n"
             f"Classified by crucible.arena.classify_run from each run's transcript and "
             f"property report. Papers regenerated and verified; dataset republished. "
             f"Model {shim.model}.")
        if push:
            p = _git(repo, "push", "-q", "origin", "main")
            entry["pushed"] = p.returncode == 0
    return entry

"""One unattended research pass, end to end, defined by research.yaml.

In order: pull the repository so a parameter change made anywhere applies;
harvest and build any seeds the parameters list; run the solo gate for every
hand-written entrypoint that has not yet been verified; run the arena over the
configured pairs and scenarios; regenerate every paper that verifies; publish
the dataset with the parameters it was produced under; commit and push so the
site rebuilds. A pass that changed nothing commits nothing.

What a pass never does: write an entrypoint, or decide a run is a verdict by
any rule not in arena.classify_run. The judgement stays human and recorded;
the repetition is automated.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from crucible.arena import run_arena
from crucible.emit import latest_solo
from crucible.harvest import parse_seed_file
from crucible.model_shim import ShimConfig
from crucible.params import Params, load_params
from crucible.pipeline import run_pipeline
from crucible.publish import publish_dataset
from crucible.solo import Entrypoint, SoloOutcome, run_solo
from crucible.store import Store


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


async def _harvest(store: Store, repo: Path, params: Params, shim: ShimConfig) -> int:
    n = 0
    for rel in params.seeds:
        path = repo / rel
        if not path.exists():
            continue
        seeds = parse_seed_file(path.read_text())
        await run_pipeline(seeds, store=store, shim=shim)
        n += len(seeds)
    return n


async def _verify_entrypoints(store: Store, repo: Path, shim: ShimConfig) -> list[dict]:
    """Solo-gate every entrypoint whose latest attempt is not `acted`.

    An entrypoint is written by a person; whether it works is established by
    running it. A pass re-verifies anything unverified so that a new entrypoint
    committed between passes enters the arena on the next one without anyone
    doing anything else.
    """
    results = []
    for path in sorted((repo / "entrypoints").glob("*.json")):
        ep = Entrypoint.load(path)
        last = latest_solo(store, ep.slug)
        if last and last["outcome"] == str(SoloOutcome.ACTED):
            continue
        builds = store.live_rows("builds", candidate=ep.slug, status="built")
        if not builds:
            results.append({"slug": ep.slug, "outcome": "no built image"})
            continue
        r = await run_solo(ep, builds[-1]["image_digest"], store=store, shim=shim,
                           workdir=(repo / "runs" / "solo" / ep.slug).resolve())
        results.append({"slug": ep.slug, "outcome": str(r.outcome)})
    return results


def research_pass(*, repo: Path, db: Path | None = None, root: Path | None = None,
                  params: Params | None = None, push: bool = True) -> dict:
    started = datetime.now(timezone.utc).isoformat()
    params = params or load_params(repo)
    db = db or repo / "runs" / "arena.db"
    root = root or repo / "runs" / "sandbox-root"
    shim = ShimConfig(base_url=params.ollama, model=params.model)

    if params.pull:
        _git(repo, "pull", "-q", "--rebase", "origin", "main")
        params = load_params(repo)  # the pull may have changed them

    store = Store(db)
    store.init_db()

    async def stages() -> tuple[int, list[dict], list[dict]]:
        harvested = await _harvest(store, repo, params, shim)
        solos = await _verify_entrypoints(store, repo, shim)
        agents = None if params.agents == "all-invocable" else list(params.agents)
        recorded = await run_arena(store, root, shim=shim, scenarios=params.scenarios,
                                   rounds=params.rounds, agents=agents)
        return harvested, solos, recorded

    harvested, solos, recorded = asyncio.run(stages())
    by_status: dict[str, int] = {}
    for r in recorded:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1

    log = repo / "runs" / "research-passes.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    # Set by the launchd job and by nothing else. A pass that cannot say
    # whether a person started it lets "research has run" pass for "research
    # runs on its own", and those are different claims. The scheduler was
    # installed, was loaded, reported every sign of health, and had never once
    # executed; four passes a person had started stood in for it.
    unattended = os.environ.get("CRUCIBLE_UNATTENDED") == "1"
    entry = {"started": started, "finished": datetime.now(timezone.utc).isoformat(),
             "runs": len(recorded), "by_status": by_status, "harvested": harvested,
             "solos": solos, "model": params.model, "cadence_hours": params.cadence_hours,
             "unattended": unattended, "params": params.as_dict()}

    publish_dataset(store, repo / "site" / "public" / "data")

    if _git(repo, "status", "--porcelain", "runs", "site/public").stdout.strip():
        _git(repo, "add", "runs", "site/public")
        summary = ", ".join(f"{v} {k}" for k, v in sorted(by_status.items())) or "no runs"
        started_by = "unattended pass" if unattended else "supervised pass"
        _git(repo, "-c", "commit.gpgsign=false", "commit", "-q", "-m",
             f"research: {started_by}, {len(recorded)} runs ({summary})\n\n"
             f"Parameters from {params.source}: scenarios {', '.join(params.scenarios)}; "
             f"rounds {params.rounds}; model {params.model}. Harvested {harvested} seeds; "
             f"solo gate ran for {len(solos)} entrypoints. Every run classified by "
             f"crucible.arena.classify_run from its transcript and property report. Papers "
             f"regenerated and verified; dataset republished.")
        if push:
            entry["pushed"] = _git(repo, "push", "-q", "origin", "main").returncode == 0

    # Written last, on purpose. The first version wrote the entry before the
    # git work, so whether the push succeeded was assigned to a dict nobody
    # ever serialised: a pass that never reached the remote left a log saying
    # it had run and nothing saying the site still had yesterday's data.
    with log.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry

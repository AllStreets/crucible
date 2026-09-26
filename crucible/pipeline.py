"""Harvest, build, boot, report.

Every stage swallows its own failures into rows and continues, because the
value of a batch of fifty is lost if the seventh dead repository takes the
other forty three with it. The only thing that stops the pipeline is a
condition that would make every remaining result wrong.
"""
from __future__ import annotations

from crucible.forge import build, verify_boot
from crucible.harvest import Runner, default_runner, harvest
from crucible.model_shim import ShimConfig
from crucible.report import Viability, viability
from crucible.store import Store


async def run_pipeline(urls: list[str], *, store: Store,
                       run: Runner = default_runner,
                       shim: ShimConfig) -> Viability:
    candidates = await harvest(urls, store=store, run=run)
    for cand in candidates:
        result = await build(cand, store=store, run=run)
        if not result.ok or result.image_digest is None:
            continue
        await verify_boot(result.image_digest, store=store, run=run, shim=shim)
    return viability(store)

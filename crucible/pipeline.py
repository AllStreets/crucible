"""Harvest, build, check the container, report.

Every stage swallows its own failures into rows and continues, because the
value of a batch of fifty is lost if the seventh dead repository takes the
other forty three with it. The only thing that stops the pipeline is a
condition that would make every remaining result wrong.

"Swallows into rows" is literal, and it is why the loop below catches. `build`
and `verify_environment` each turn a raised exception into a row themselves, so
this catch is the outer boundary for what is left: a store write that fails, or
anything else unforeseen between the two stages. Without a boundary here, one
raise inside the loop body took the whole remaining batch and left nothing in
the dataset to say so.
"""
from __future__ import annotations

from crucible.failures import FailureClass
from crucible.forge import build, verify_environment
from crucible.harvest import Candidate, Runner, Seed, default_runner, harvest
from crucible.model_shim import ShimConfig
from crucible.report import Viability, viability
from crucible.store import Store


def _record_lost(store: Store, cand: Candidate, stage: str,
                 exc: BaseException) -> None:
    """Best effort row for a candidate lost to an exception past both stages.

    Best effort because the likeliest way to reach here is the store itself
    failing, and a recording attempt that raises in turn must not take the rest
    of the batch with it. A candidate lost with a row is still auditable; a
    candidate lost with no row is the silence this project exists to avoid.
    """
    try:
        ref = store.blob(f"{stage} raised {type(exc).__name__}: {exc}".encode())
        store.record("builds", candidate=cand.slug, commit_sha=cand.commit_sha,
                     status="failed", failure_class=str(FailureClass.UNKNOWN),
                     log_ref=ref)
    except Exception:
        return


async def run_pipeline(seeds: list[str] | list[Seed], *, store: Store,
                       run: Runner = default_runner,
                       shim: ShimConfig) -> Viability:
    candidates = await harvest(seeds, store=store, run=run)
    for cand in candidates:
        try:
            result = await build(cand, store=store, run=run)
        except Exception as exc:
            _record_lost(store, cand, "build", exc)
            continue
        if not result.ok or result.image_digest is None:
            continue
        try:
            await verify_environment(result.image_digest, store=store, run=run,
                                     shim=shim,
                                     declared_credentials=cand.credentials)
        except Exception as exc:
            _record_lost(store, cand, "environment check", exc)
            continue
    return viability(store)

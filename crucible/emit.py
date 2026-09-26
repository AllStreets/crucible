"""Write AdapterDescriptors for solo-passing agents, into a root CRUCIBLE owns.

One directional, always. CRUCIBLE writes into its own adapters root and reads
results out; SMADP's adapters directory, catalog and autopilot are never
written to. The sandbox is pointed at our root by config, so the two projects
stay separable and a mistake here cannot corrupt SMADP's own executed verdicts.

Only agents whose solo outcome is `acted` are emitted. An agent that ran and
changed nothing would otherwise enter the arena and produce an empty transcript
that a scenario scores as "no attack occurred", which publishes a harness
result as a safety result.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from crucible.solo import Entrypoint, SoloOutcome
from crucible.store import Store


@dataclass(frozen=True)
class Emitted:
    slug: str
    path: Path
    image_digest: str


def latest_solo(store: Store, slug: str) -> dict | None:
    rows = [r for r in store.live_rows("solos", slug=slug)]
    return rows[-1] if rows else None


def emit_adapters(store: Store, root: Path, *, model: str) -> list[Emitted]:
    adapters = root / "adapters"
    adapters.mkdir(parents=True, exist_ok=True)
    out: list[Emitted] = []

    for path in sorted(Path("entrypoints").glob("*.json")):
        ep = Entrypoint.load(path)
        solo = latest_solo(store, ep.slug)
        if solo is None or solo["outcome"] != str(SoloOutcome.ACTED):
            continue
        builds = store.live_rows("builds", candidate=ep.slug, status="built")
        if not builds:
            continue
        digest = builds[-1]["image_digest"]

        descriptor = {
            "schema_version": "1.0",
            "slug": ep.slug,
            "name": ep.slug,
            "description": (
                "Emitted by CRUCIBLE from a hand-written entrypoint that passed "
                "the solo gate. Not a curated SMADP adapter."),
            "transport": "stdio",
            "command": ep.resolved(model),
            "env_required": ep.env_required,
            "image": digest,
            "image_digest_pinned": digest,
            # Declared from what the entrypoint actually does, not aspirationally.
            # Both agents run a shell and edit files in the shared workspace.
            "capabilities": {
                "execute_shell": True,
                "read_filesystem": True,
                "write_filesystem": True,
                "network_egress": "model_endpoint_only",
                "spawn_subprocesses": True,
                "use_mcp": False,
                "modify_git_state": False,
                "install_packages": False,
            },
            "provenance": {
                "entrypoint_authored_by": ep.authored_by,
                "entrypoint_notes": ep.notes,
                "solo_outcome": solo["outcome"],
                "solo_model": solo["model"],
            },
        }
        d = adapters / ep.slug
        d.mkdir(parents=True, exist_ok=True)
        target = d / "mcp.json"
        target.write_text(json.dumps(descriptor, indent=2) + "\n")
        out.append(Emitted(ep.slug, target, digest))

    return out

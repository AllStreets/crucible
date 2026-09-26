"""Export the record store as static JSON for the site to read at build time.

This is the only bridge between the engine and the site, and it is one
directional by design. The site has no database driver, no runner and no Docker
client, so it cannot display a figure that was not published here. A site that
can reach the live store can show a number nobody has reviewed; a site that
reads a committed file cannot.

manifest.json carries the engine commit and a sha256 of dataset.json, so a page
can say when its numbers were produced and a reader can check that the file was
not edited afterwards. Provenance that lives only in a commit message is
provenance a reader of the numbers will never see.

Superseded rows never reach the site for the same reason they never reach a
report, and via the same method, Store.live_rows, rather than a second copy of
the rule. Two definitions of what is published is how a figure on a page drifts
from the figure in the paper with nobody able to say which is wrong.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from crucible.failures import FailureClass
from crucible.store import Store

_PUBLISHED_TABLES = ("candidates", "builds", "env_checks", "unresolved")


@dataclass(frozen=True)
class PublishResult:
    files: tuple[Path, ...]
    counts: dict[str, int]


def _engine_commit() -> str:
    """The engine commit, or the string unknown.

    Deliberately never raises. Publishing from a tarball with no git history is
    legitimate, and failing the whole export over a missing provenance field
    would be worse than recording that the field is missing. The site renders
    whatever is here, so unknown shows up on the page as unknown.
    """
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def publish_dataset(store: Store, out_dir: Path) -> PublishResult:
    out_dir.mkdir(parents=True, exist_ok=True)

    data: dict[str, list[dict]] = {}
    counts: dict[str, int] = {}
    for table in _PUBLISHED_TABLES:
        rows = store.live_rows(table)
        data[table] = rows
        counts[table] = len(rows)

    dataset_path = out_dir / "dataset.json"
    body = json.dumps(data, indent=2, sort_keys=True) + "\n"
    dataset_path.write_text(body)

    schema_path = out_dir / "schema.json"
    schema_path.write_text(json.dumps(
        {t: sorted({k for r in data[t] for k in r}) for t in _PUBLISHED_TABLES},
        indent=2, sort_keys=True) + "\n")

    # The human-readable name of every failure class, published rather than
    # retyped in the site. FailureClass.label is the single definition; a
    # TypeScript copy of these strings would drift from it silently, and the
    # first symptom would be a page describing a failure as something the
    # engine never meant.
    labels_path = out_dir / "labels.json"
    labels_path.write_text(json.dumps(
        {str(c): c.label for c in FailureClass}, indent=2, sort_keys=True) + "\n")

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_commit": _engine_commit(),
        "dataset_sha256": hashlib.sha256(body.encode()).hexdigest(),
        "counts": counts,
    }, indent=2, sort_keys=True) + "\n")

    return PublishResult(
        files=(dataset_path, schema_path, labels_path, manifest_path),
        counts=counts)

"""The viability report.

Every figure is a count of rows. There is no parameter here that lets a number
be asserted rather than computed, because the whole value of this dataset is
that it was measured. If the store is empty the report says so rather than
rendering zeroes that look like findings.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

from crucible.store import Store


@dataclass(frozen=True)
class Viability:
    harvested: int
    built: int
    booted: int
    by_failure: dict[str, int] = field(default_factory=dict)
    generated_at: str = ""


def viability(store: Store) -> Viability:
    """Compute viability statistics from the store.

    Returns a Viability dataclass with counts of harvested, built, and booted
    agents, along with a distribution of failure classes across failed builds
    and boot attempts.
    """
    builds = store.rows("builds")
    boots = store.rows("boots")
    failures = Counter(
        str(r["failure_class"]) for r in (*builds, *boots) if r["failure_class"])
    return Viability(
        harvested=len(store.rows("candidates")),
        built=sum(1 for r in builds if r["status"] == "built"),
        booted=sum(1 for r in boots if r["status"] == "booted"),
        by_failure=dict(failures),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def render_markdown(v: Viability) -> str:
    """Render a Viability report to markdown.

    The report includes a headline stating how many agents booted successfully,
    a breakdown of failures by class, and a limitations section explaining that
    classification is substring-based and therefore approximate.
    """
    if v.harvested == 0:
        return "# Agent viability\n\nNo candidates have been harvested yet.\n"

    pct = 100.0 * v.booted / v.harvested
    lines = [
        "# Agent viability",
        "",
        f"**{v.booted} of {v.harvested} candidate agents reached a working state "
        f"in a clean container ({pct:.1f}%).**",
        "",
        f"- Harvested: {v.harvested}",
        f"- Built successfully: {v.built}",
        f"- Booted successfully: {v.booted}",
        "",
        "## Where the rest failed",
        "",
        "| Failure | Count |",
        "|---|---|",
    ]
    for name, count in sorted(v.by_failure.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {name} | {count} |")
    lines += [
        "",
        "## Limitations",
        "",
        "Failure classification is substring-based and therefore approximate. "
        "The unknown bucket collects unmatched failures rather than guessing at "
        "a nearest class. Counts in specific buckets may therefore be slightly "
        "over- or under-stated.",
        "",
        f"Generated {v.generated_at} from the record store. Every count "
        "above is a query; none is asserted.",
        "",
    ]
    return "\n".join(lines)

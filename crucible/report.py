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

    Superseded rows are excluded from all counts, since they represent
    corrections to prior measurements rather than independent facts about
    the world.
    """
    # Build sets of superseded IDs per table
    superseded: dict[str, set[int]] = {"builds": set(), "boots": set()}
    for row in store.rows("supersedes"):
        tbl = row["tbl"]
        old_id = row["old_id"]
        if tbl in superseded:
            superseded[tbl].add(old_id)

    # Query all rows and filter out superseded ones
    builds = [r for r in store.rows("builds") if r["id"] not in superseded["builds"]]
    boots = [r for r in store.rows("boots") if r["id"] not in superseded["boots"]]

    # Tally failures from non-superseded rows
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
        "over- or under-stated. Superseded results are excluded from all counts; "
        "the raw dataset may contain more rows than counted here.",
        "",
        f"Generated {v.generated_at} from the record store. Every count "
        "above is a query; none is asserted.",
        "",
    ]
    return "\n".join(lines)

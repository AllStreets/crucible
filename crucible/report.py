"""The viability report.

Every figure is a count of rows. There is no parameter here that lets a number
be asserted rather than computed, because the whole value of this dataset is
that it was measured. If the store is empty the report says so rather than
rendering zeroes that look like findings.

The report is also careful about what the numbers mean. The last stage is an
environment check, not a boot: it starts the built image with egress denied and
runs the probe the Dockerfile installs. It does not start the agent. So nothing
rendered here says boot, and the headline states in the same breath what was
measured and what was not.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

from crucible.store import Store


@dataclass(frozen=True)
class Viability:
    """Counts of distinct agents, plus tallies of recorded failure rows.

    `env_ok` is the number of candidates whose built image passed the
    environment check. It is not a count of agents that ran, and it is named so
    that it cannot be read as one.

    `by_failure` is the pooled tally across both stages, for the dataset.
    `build_failures` and `env_failures` are the same rows split by the stage
    that produced them, because the pooled table reads like a partition of
    `harvested` and is not one.
    """

    harvested: int
    built: int
    env_ok: int
    by_failure: dict[str, int] = field(default_factory=dict)
    build_failures: dict[str, int] = field(default_factory=dict)
    env_failures: dict[str, int] = field(default_factory=dict)
    unresolved: int = 0
    generated_at: str = ""


def viability(store: Store) -> Viability:
    """Compute viability statistics from the store.

    Every count is a count of distinct agents, not of attempts. Two rows for
    the same identity are the same agent measured twice: a candidate is
    identified by `(slug, commit_sha)`, a build by that same pair, and an
    environment check by the image digest it ran. Counting rows instead would
    let a second run of the same seed list double every published figure.

    Superseded rows are excluded from all counts, candidates included, since
    they represent corrections to prior measurements rather than independent
    facts about the world.
    """
    superseded: dict[str, set[int]] = {"candidates": set(), "builds": set(),
                                       "env_checks": set()}
    for row in store.rows("supersedes"):
        tbl = row["tbl"]
        if tbl in superseded:
            superseded[tbl].add(row["old_id"])

    candidates = [r for r in store.rows("candidates")
                  if r["id"] not in superseded["candidates"]]
    builds = [r for r in store.rows("builds") if r["id"] not in superseded["builds"]]
    checks = [r for r in store.rows("env_checks")
              if r["id"] not in superseded["env_checks"]]

    build_failures = Counter(
        str(r["failure_class"]) for r in builds if r["failure_class"])
    env_failures = Counter(
        str(r["failure_class"]) for r in checks if r["failure_class"])

    harvested = {(r["slug"], r["commit_sha"]) for r in candidates}
    built = {(r["candidate"], r["commit_sha"])
             for r in builds if r["status"] == "built"}
    passed = {r["build"] for r in checks if r["status"] == "passed"}

    return Viability(
        harvested=len(harvested),
        built=len(built),
        env_ok=len(passed),
        by_failure=dict(build_failures + env_failures),
        build_failures=dict(build_failures),
        env_failures=dict(env_failures),
        unresolved=len({r["seed_url"] for r in store.rows("unresolved")}),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _failure_table(title: str, counts: dict[str, int]) -> list[str]:
    lines = [f"### {title}", ""]
    if not counts:
        lines += ["None recorded.", ""]
        return lines
    lines += ["| Failure | Count |", "|---|---|"]
    for name, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| {name} | {count} |")
    lines.append("")
    return lines


def render_markdown(v: Viability) -> str:
    """Render a Viability report to markdown.

    The headline states what was measured and, immediately, what was not. The
    failure tables are split by stage and labelled as tallies of recorded rows,
    since a reader meeting one pooled table under a heading like "where the rest
    failed" will read it as a partition of the candidates, which it is not and
    can exceed.
    """
    if v.harvested == 0:
        lines = ["# Agent viability", "", "No candidates have been harvested yet."]
        if v.unresolved:
            lines += [
                "",
                f"{v.unresolved} seed URL(s) were attempted and could not be "
                "resolved, so no candidate was pinned from them. They are "
                "recorded in the unresolved table.",
            ]
        return "\n".join(lines) + "\n"

    pct = 100.0 * v.env_ok / v.harvested
    seeded = v.harvested + v.unresolved
    lines = [
        "# Agent viability",
        "",
        f"**{v.env_ok} of {v.harvested} candidate agents built into a container "
        f"whose environment starts in a clean sandbox ({pct:.1f}%).**",
        "",
        "What that measures, exactly: the repository was cloned at a pinned "
        "commit, its dependencies installed, and the resulting image started "
        "with egress denied and ran its environment probe to completion. What it "
        "does not measure: whether the agent itself runs. The probe does not "
        "invoke the agent. The repositories measured here share no entrypoint, "
        "and with no network and no credentials an invocation would measure this "
        "harness rather than the agent, so no figure above or below is evidence "
        "that an agent ran.",
        "",
        f"- Seed URLs attempted: {seeded}",
        f"- Could not be resolved, so never pinned: {v.unresolved}",
        f"- Harvested as pinned candidates: {v.harvested}",
        f"- Built successfully: {v.built}",
        f"- Passed the container environment check: {v.env_ok}",
        "",
        "## Recorded failures, by stage",
        "",
        "These are tallies of recorded failure rows, not a partition of the "
        "candidates above. A candidate that fails to build contributes one build "
        "row and no check row; one that builds and then fails the check "
        "contributes a row to each stage; one that passes contributes neither. "
        "So the two tables below neither sum to the harvested count nor are "
        "bounded by it.",
        "",
    ]
    lines += _failure_table("Build stage", v.build_failures)
    lines += _failure_table("Container environment check stage", v.env_failures)
    lines += [
        "## Limitations",
        "",
        "Failure classification is substring-based and therefore approximate. "
        "The unknown bucket collects unmatched failures rather than guessing at "
        "a nearest class. Counts in specific buckets may therefore be slightly "
        "over- or under-stated. Superseded results are excluded from all counts; "
        "the raw dataset may contain more rows than counted here. Counts are "
        "over the whole store rather than over a single run, so a store built "
        "from more than one seed list reports their union.",
        "",
        f"Generated {v.generated_at} from the record store. Every count "
        "above is a query; none is asserted.",
        "",
    ]
    return "\n".join(lines)

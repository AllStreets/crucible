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
    """Counts at two granularities, plus tallies of recorded failure rows.

    The headline says "N of M candidate agents", and an agent is a repository.
    `agents`, `built_agents` and `env_ok_agents` count distinct repositories,
    which is what those words mean and what the headline uses.

    `harvested`, `built` and `env_ok` count distinct candidate commits, the
    `(slug, commit_sha)` pairs. A repository harvested at two HEADs is one agent
    and two candidate commits, so these are the right denominator for anything
    about the code that was actually built, and the wrong one for a sentence
    about agents. Both are reported, and the report shows the difference rather
    than hiding it.

    All three stages are keyed the same way, deliberately. `env_ok` resolves
    each passing check back through its build's image digest to the candidate
    commit that produced it. Keyed on the digest instead, a rebuild that
    produced a second digest counted twice against a `built` that counted once,
    and the headline percentage could exceed 100.

    `env_ok` and `env_ok_agents` are not counts of agents that ran. The check
    starts the image and runs a probe; it does not invoke the agent.

    `by_failure` is the pooled tally across both stages, for the dataset.
    `build_failures` and `env_failures` are the same rows split by the stage
    that produced them, because the pooled table reads like a partition of
    `harvested` and is not one.
    """

    harvested: int
    built: int
    env_ok: int
    agents: int = 0
    built_agents: int = 0
    env_ok_agents: int = 0
    by_failure: dict[str, int] = field(default_factory=dict)
    build_failures: dict[str, int] = field(default_factory=dict)
    env_failures: dict[str, int] = field(default_factory=dict)
    unresolved: int = 0
    generated_at: str = ""


def viability(store: Store) -> Viability:
    """Compute viability statistics from the store.

    Every count is a count of distinct things, not of attempts. Two rows for
    the same identity are the same thing measured twice, so a second run of the
    same seed list cannot double a figure.

    Two granularities, because the report needs both: the repository (an agent)
    and the `(slug, commit_sha)` pair (a candidate commit). Every stage is keyed
    identically at each granularity, which is why a passing environment check is
    resolved back through its build's image digest rather than counted as a
    digest: mixing the two let `env_ok` exceed `built` after a rebuild.

    Superseded rows are excluded from all counts, candidates included, since
    they represent corrections to prior measurements rather than independent
    facts about the world.
    """
    candidates = store.live_rows("candidates")
    builds = store.live_rows("builds")
    checks = store.live_rows("env_checks")

    build_failures = Counter(
        str(r["failure_class"]) for r in builds if r["failure_class"])
    env_failures = Counter(
        str(r["failure_class"]) for r in checks if r["failure_class"])

    harvested = {(r["slug"], r["commit_sha"]) for r in candidates}
    built = {(r["candidate"], r["commit_sha"])
             for r in builds if r["status"] == "built"}

    # A passing check names an image digest. Resolve it back to the candidate
    # commit that produced that image, so every stage is keyed the same way. A
    # digest with no surviving build row is not counted: it cannot be attributed
    # to an agent, and counting it under a different key is how env_ok came to be
    # able to exceed built.
    of_digest = {r["image_digest"]: (r["candidate"], r["commit_sha"])
                 for r in builds
                 if r["status"] == "built" and r["image_digest"]}
    passed = {of_digest[r["build"]] for r in checks
              if r["status"] == "passed" and r["build"] in of_digest}

    return Viability(
        harvested=len(harvested),
        built=len(built),
        env_ok=len(passed),
        agents=len({slug for slug, _ in harvested}),
        built_agents=len({slug for slug, _ in built}),
        env_ok_agents=len({slug for slug, _ in passed}),
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
    if v.agents == 0:
        lines = ["# Agent viability", "", "No candidates have been harvested yet."]
        if v.unresolved:
            lines += [
                "",
                f"{v.unresolved} seed URL(s) were attempted and could not be "
                "resolved, so no candidate was pinned from them. They are "
                "recorded in the unresolved table.",
            ]
        return "\n".join(lines) + "\n"

    pct = 100.0 * v.env_ok_agents / v.agents
    lines = [
        "# Agent viability",
        "",
        f"**{v.env_ok_agents} of {v.agents} candidate agents built into a "
        f"container whose environment starts in a clean sandbox ({pct:.1f}%).**",
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
        f"- Agents harvested, one per repository: {v.agents}",
        f"- Seed URLs that could not be resolved, so never pinned: "
        f"{v.unresolved}",
        f"- Agents built successfully: {v.built_agents}",
        f"- Agents that passed the container environment check: {v.env_ok_agents}",
        "",
    ]
    if (v.harvested, v.built, v.env_ok) != (v.agents, v.built_agents, v.env_ok_agents):
        lines += [
            "At commit granularity, which differs from the figures above because "
            "a repository harvested at more than one HEAD is one agent and "
            "several candidate commits:",
            "",
            f"- Candidate commits harvested: {v.harvested}",
            f"- Candidate commits built successfully: {v.built}",
            f"- Candidate commits that passed the environment check: {v.env_ok}",
            "",
        ]
    lines += [
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
        "over- or under-stated. The unknown bucket also holds two failures of "
        "this harness rather than of an agent, since filing either under a build "
        "class would blame the agent for it: a build that exceeded the 30 minute "
        "timeout, which heavy agents will hit and which will therefore not be "
        "rare, and the docker command failing to run at all. Both store the "
        "exception text as evidence, so they are separable from genuinely "
        "unmatched failures by reading the rows. "
        "Superseded results are excluded from all counts; "
        "the raw dataset may contain more rows than counted here. Counts are "
        "over the whole store rather than over a single run, so a store built "
        "from more than one seed list reports their union, and the unresolved "
        "count is of distinct URLs that failed to resolve at some point rather "
        "than of one list's misses. Adding it to the harvested count therefore "
        "approximates how many URLs were seeded; it does not measure it.",
        "",
        f"Generated {v.generated_at} from the record store. Every count "
        "above is a query; none is asserted.",
        "",
    ]
    return "\n".join(lines)

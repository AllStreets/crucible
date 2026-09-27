"""Generate a paper from run records, rather than writing one about them.

The rule this module exists to enforce: every numeral in the finished document
must be traceable to a row. Not "should be", not "was when it was written".
The generator gathers a closed set of facts by query, renders a typed template
against them, and then reads its own output back and rejects the document if
any numeral in it is absent from that set.

That last pass is the whole point, and it is what makes a model safe to use
here later. A model may draft connective prose under the constraint that it
introduces no numeral; verification is what turns the constraint from a
request into a guarantee. Until a model is used, verification still catches the
ordinary human failure, which is a number that was true when the sentence was
written and stopped being true when the data changed.

No model is called. The viability paper needs none: every sentence is either a
query result or fixed template prose. Generation that costs nothing can be run
on every commit, and a paper regenerated on every commit cannot drift.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from crucible.failures import FailureClass
from crucible.store import Store


class VerificationError(Exception):
    """Raised when a generated document states a number that is not in the record."""


@dataclass(frozen=True)
class Paper:
    """One generated paper, with the metadata a reader needs before opening it."""
    slug: str
    title: str
    abstract: str
    generated_at: str
    filename: str
    word_count: int


@dataclass(frozen=True)
class Facts:
    """Every number this paper is allowed to state.

    A closed set, gathered once. If a sentence needs a number that is not here,
    the correct fix is to add a query, never to type the number.
    """
    harvested: int
    unresolved: int
    built: int
    build_failed: int
    checked: int
    check_failed: int
    build_failures: dict[str, int]
    check_failures: dict[str, int]
    recipes: list[str]
    models: list[str]
    first_at: str
    last_at: str
    durations_ms: list[int]

    @property
    def viability_pct(self) -> str | None:
        if self.harvested == 0:
            return None
        return f"{100 * self.checked / self.harvested:.1f}"

    def allowed_numerals(self) -> set[str]:
        """Every numeral string the document may contain.

        Includes the formatted forms, because "70.0" and "70" are different
        strings in the text and only the one actually rendered is defensible.
        """
        out: set[str] = set()
        for n in (self.harvested, self.unresolved, self.built, self.build_failed,
                  self.checked, self.check_failed, len(self.recipes),
                  len(self.models), *self.build_failures.values(),
                  *self.check_failures.values(), *self.durations_ms):
            out.add(str(n))
        if (pct := self.viability_pct) is not None:
            out.add(pct)
            out.add(pct.split(".")[0])
        if self.durations_ms:
            out.add(str(min(self.durations_ms)))
            out.add(str(max(self.durations_ms)))
        # The date components of the record's own span. These were once a
        # hardcoded structural set containing the day the code was written,
        # and the verifier rejected every paper generated the following day.
        # A verifier with a calendar in it is a verifier that expires.
        for stamp in (self.first_at, self.last_at):
            for part in stamp.replace("T", "-").replace(":", "-").split("-"):
                if part.isdigit():
                    out.add(part)
                    out.add(part.lstrip("0") or "0")
        return out


def gather_facts(store: Store) -> Facts:
    candidates = store.live_rows("candidates")
    builds = store.live_rows("builds")
    checks = store.live_rows("env_checks")
    unresolved = store.live_rows("unresolved")

    build_failures: dict[str, int] = {}
    for row in builds:
        if row["failure_class"]:
            build_failures[row["failure_class"]] = (
                build_failures.get(row["failure_class"], 0) + 1)

    check_failures: dict[str, int] = {}
    for row in checks:
        if row["failure_class"]:
            check_failures[row["failure_class"]] = (
                check_failures.get(row["failure_class"], 0) + 1)

    stamps = sorted(r["at"] for r in candidates + builds + checks if r.get("at"))
    durations = sorted(r["duration_ms"] for r in checks
                       if r.get("duration_ms") is not None)

    return Facts(
        harvested=len(candidates),
        unresolved=len(unresolved),
        built=sum(1 for r in builds if r["status"] == "built"),
        build_failed=sum(1 for r in builds if r["status"] == "failed"),
        checked=sum(1 for r in checks if r["status"] == "passed"),
        check_failed=sum(1 for r in checks if r["status"] == "failed"),
        build_failures=build_failures,
        check_failures=check_failures,
        recipes=sorted({r["recipe_sha"] for r in builds if r.get("recipe_sha")}),
        models=sorted({r["model"] for r in checks if r.get("model")}),
        first_at=stamps[0][:10] if stamps else "",
        last_at=stamps[-1][:10] if stamps else "",
        durations_ms=durations,
    )


# Numerals that are structural rather than empirical: a date, a section number,
# a Python version named in prose as a fact about the world rather than a
# measurement. Each is listed explicitly, because a general rule here would be
# a hole in the verification.
# Numerals that name a fixed fact about the world rather than a measurement: a
# Python version, a hash width. Never a date, which belongs to the record.
_STRUCTURAL = {"3", "11", "12", "256", "1", "2", "4"}


def verify(document: str, facts: Facts) -> list[str]:
    """Return every numeral in the document that is not in the record.

    Reads the finished text, not the inputs. A generator that checked its own
    inputs would pass while emitting a typo, which is precisely the failure
    this is for.
    """
    allowed = facts.allowed_numerals() | _STRUCTURAL
    offenders: list[str] = []
    # Skip fenced blocks and table rows: those are rendered from facts directly
    # and contain digests, slugs and commit hashes that are identifiers rather
    # than claims.
    for line in document.splitlines():
        if line.startswith(("|", "    ", "```", "- `")) or "sha256" in line:
            continue
        for numeral in re.findall(r"\b\d+(?:\.\d+)?\b", line):
            if numeral not in allowed:
                offenders.append(f"{numeral!r} in: {line.strip()[:70]}")
    return offenders


def render(facts: Facts) -> str:
    f = facts
    pct = f.viability_pct

    if pct is None:
        raise VerificationError(
            "no candidates in the record, so there is no rate to report. "
            "A paper over an empty denominator would state a finding that was "
            "never measured.")

    lines: list[str] = []
    w = lines.append

    w("# Container viability of open-source AI agents")
    w("")
    w("*Generated from run records. Every figure below is a count of rows.*")
    w("")
    w("## Abstract")
    w("")
    w(f"We attempt to build {f.harvested} open-source AI agent repositories "
      f"into containers at pinned commits and to start each resulting image in "
      f"a network-denied sandbox. {f.built} build successfully and {f.checked} "
      f"pass a container environment check, a rate of {pct} percent. We report "
      f"the distribution of failure causes and, for each, whether the cause is "
      f"a property of the agent or a limit of the harness. We do not measure "
      f"whether any agent runs.")
    w("")
    w("## Method")
    w("")
    w("Each repository is resolved to a commit SHA, cloned inside a container "
      "build at that pin, and installed using a single generic recipe. The "
      "resulting image is started with egress denied and runs an environment "
      "probe: the interpreter starts, prints one line, and exits.")
    w("")
    w("The probe does not invoke the agent. The container command overrides "
      "whatever entrypoint the agent defines, so a passing check establishes "
      "that the environment works and nothing more. The repositories studied "
      "share no common entrypoint, and with no network and no credentials an "
      "invocation would measure the harness rather than the agent.")
    w("")
    w(f"Records span {f.first_at} to {f.last_at}. Build recipes used: "
      f"{len(f.recipes)}. A recipe digest is pinned on every build row, since "
      f"the recipe determines which agents are buildable and rows produced "
      f"under different recipes are different measurements.")
    w("")
    w("## Results")
    w("")
    w("| Stage | Count |")
    w("|---|---|")
    w(f"| Repositories harvested | {f.harvested} |")
    w(f"| Seed URLs unresolved | {f.unresolved} |")
    w(f"| Built | {f.built} |")
    w(f"| Build failed | {f.build_failed} |")
    w(f"| Environment check passed | {f.checked} |")
    w(f"| Environment check failed | {f.check_failed} |")
    w("")
    w("Failure counts are tallies of recorded rows and are not a partition of "
      "the repositories harvested. A repository that fails to build "
      "contributes a build row and no check row, so the tables below neither "
      "sum to the harvested count nor are bounded by it.")
    w("")
    w("### Build stage")
    w("")
    if f.build_failures:
        w("| Cause | Count | Attributable to |")
        w("|---|---|---|")
        for cls, n in sorted(f.build_failures.items(), key=lambda kv: -kv[1]):
            w(f"| {_label(cls)} | {n} | {_attribution(cls)} |")
    else:
        w("No build failures recorded.")
    w("")
    w("### Environment check stage")
    w("")
    if f.check_failures:
        w("| Cause | Count | Attributable to |")
        w("|---|---|---|")
        for cls, n in sorted(f.check_failures.items(), key=lambda kv: -kv[1]):
            w(f"| {_label(cls)} | {n} | {_attribution(cls)} |")
    else:
        w("No environment check failures recorded.")
    w("")
    if f.durations_ms:
        w(f"Probe durations range from {min(f.durations_ms)} to "
          f"{max(f.durations_ms)} milliseconds.")
        w("")
    w("## Threats to validity")
    w("")
    w("**The headline rate is not a property of the agents alone.** The "
      "attribution column above separates causes that are facts about a "
      "repository from causes that are limits of this harness. A reader "
      "comparing this rate against another study must check that the harness "
      "limits are comparable, because extending the recipe changes the rate "
      "without any agent changing.")
    w("")
    w("**Failure classification is substring based.** Unmatched failures are "
      "recorded as unclassified rather than assigned to a nearest class. The "
      "unclassified bucket also holds failures of the harness itself, "
      "including a build exceeding its timeout and the container runtime "
      "failing to start, because filing either under a build cause would "
      "attribute it to the agent.")
    w("")
    w("**Selection.** The repositories studied were chosen by hand as agents "
      "people run together, not sampled from a ranking. The rate therefore "
      "describes that population and does not generalise to all repositories "
      "matching an agent keyword.")
    w("")
    w("## Limitations")
    w("")
    w("Generated from run metadata rather than composed, so these cannot fall "
      "out of date with the results above.")
    w("")
    w(f"- Sample size is {f.harvested} repositories.")
    if f.models:
        w(f"- Models held constant across checks: {len(f.models)}.")
    else:
        w("- No model was exercised: the environment probe does not call one.")
    w(f"- Build recipes in the record: {len(f.recipes)}. A rate computed "
      f"across more than one recipe is not a single measurement.")
    w("- No agent was invoked, so nothing here is evidence of agent behaviour.")
    w("- No pair of agents was run, so nothing here concerns interaction.")
    w("")
    w("## Reproduction")
    w("")
    w("Every figure resolves to a row in the published dataset, and every "
      "recorded failure to its full build log, addressed by content hash.")
    w("")
    return "\n".join(lines)


def _label(cls: str) -> str:
    try:
        return FailureClass(cls).label
    except ValueError:
        return cls


# Which side of the instrument a cause sits on. This is the column that keeps
# the headline rate honest: a rate driven by harness limits says something
# about the harness, and a reader cannot tell the two apart from the class name
# alone.
_HARNESS_LIMITS = {
    FailureClass.UNSUPPORTED_LANGUAGE,
    FailureClass.WORKSPACE_ROOT_NOT_INSTALLABLE,
    FailureClass.PYTHON_VERSION_UNSUPPORTED,
    FailureClass.NO_BUILD_RECIPE,
    FailureClass.AMBIGUOUS_MANIFEST,
    FailureClass.UNKNOWN,
}


def _attribution(cls: str) -> str:
    try:
        return "this harness" if FailureClass(cls) in _HARNESS_LIMITS else "the repository"
    except ValueError:
        return "unclassified"


def _extract(document: str) -> tuple[str, str]:
    """Title and abstract, read back out of the finished document.

    Parsed from the output rather than passed alongside it, so a card on the
    site cannot advertise an abstract the paper does not contain.
    """
    lines = document.splitlines()
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), "Untitled")
    abstract: list[str] = []
    seen = False
    for line in lines:
        if line.startswith("## Abstract"):
            seen = True
            continue
        if seen:
            if line.startswith("## "):
                break
            if line.strip():
                abstract.append(line.strip())
    return title, " ".join(abstract)


def generate_paper(store: Store, slug: str = "container-viability") -> tuple[str, Paper]:
    """The document and its metadata, both derived from the same render."""
    document = generate(store)
    title, abstract = _extract(document)
    return document, Paper(
        slug=slug,
        title=title,
        abstract=abstract,
        generated_at=datetime.now(timezone.utc).isoformat(),
        filename=f"{slug}.md",
        word_count=len(document.split()),
    )


def generate(store: Store) -> str:
    """Gather, render, verify. A document that fails verification is not returned."""
    facts = gather_facts(store)
    document = render(facts)
    offenders = verify(document, facts)
    if offenders:
        raise VerificationError(
            "the generated document states numbers that are not in the record:\n  "
            + "\n  ".join(offenders))
    return document


# ---------------------------------------------------------------------------
# The arena paper: what was established between pairs, and what was not.

@dataclass(frozen=True)
class ArenaFacts:
    runs: int
    earned: int
    strong: int
    weak: int
    artifacts: int
    blocked: int
    confirmed: int
    pairs: int
    agents: int
    scenarios: int
    by_scenario: dict[str, dict[str, int]]   # scenario -> {earned, artifact, blocked, confirmed}
    models: list[str]
    first_at: str
    last_at: str

    def allowed_numerals(self) -> set[str]:
        out = {str(n) for n in (self.runs, self.earned, self.strong, self.weak, self.artifacts,
                                self.blocked, self.confirmed, self.pairs, self.agents,
                                self.scenarios, len(self.models))}
        for counts in self.by_scenario.values():
            out.update(str(v) for v in counts.values())
        if self.runs:
            out.add(f"{100 * self.earned / self.runs:.1f}")
        for stamp in (self.first_at, self.last_at):
            for part in stamp.replace("T", "-").replace(":", "-").split("-"):
                if part.isdigit():
                    out.add(part); out.add(part.lstrip("0") or "0")
        return out


def gather_arena_facts(store: Store) -> ArenaFacts:
    pairs = store.live_rows("pairs")
    by: dict[str, dict[str, int]] = {}
    agents: set[str] = set(); keys: set[str] = set()
    for r in pairs:
        d = by.setdefault(r["scenario"], {"earned": 0, "artifact": 0, "blocked": 0, "confirmed": 0})
        if r["status"] == "done":
            d["earned"] += 1
            if r["outcome"] == "fail":
                d["confirmed"] += 1
        elif r["status"] == "artifact":
            d["artifact"] += 1
        elif r["status"] == "blocked":
            d["blocked"] += 1
        agents.update((r["slug_a"], r["slug_b"]))
        keys.add(tuple(sorted((r["slug_a"], r["slug_b"]))))
    stamps = sorted(r["at"] for r in pairs if r.get("at"))
    done = [r for r in pairs if r["status"] == "done"]
    return ArenaFacts(
        runs=len(pairs), earned=len(done),
        strong=sum(1 for r in done if r.get("strength") == "strong"),
        weak=sum(1 for r in done if r.get("strength") == "weak"),
        artifacts=sum(1 for r in pairs if r["status"] == "artifact"),
        blocked=sum(1 for r in pairs if r["status"] == "blocked"),
        confirmed=sum(1 for r in done if r["outcome"] == "fail"),
        pairs=len(keys), agents=len(agents), scenarios=len(by),
        by_scenario=dict(sorted(by.items())),
        models=sorted({r["model"] for r in pairs if r.get("model")}),
        first_at=stamps[0][:10] if stamps else "", last_at=stamps[-1][:10] if stamps else "",
    )


_SCENARIO_TITLES = {
    "secret_exfiltration": "Secret exfiltration", "induced_execution": "Induced execution",
    "state_poisoning": "State poisoning", "partner_escalation": "Partner escalation",
}


def render_arena(f: ArenaFacts) -> str:
    if f.runs == 0:
        raise VerificationError("no pair runs in the record, so there is nothing to report")
    w: list[str] = []
    a = w.append
    a("# Adversarial interaction between open-source agents sharing a workspace")
    a("")
    a("*Generated from run records. Every figure below is a count of rows.*")
    a("")
    a("## Abstract")
    a("")
    a(f"We run {f.pairs} pairs drawn from {f.agents} open-source agents against each other "
      f"in {f.scenarios} adversarial scenarios, {f.runs} runs in all, in a sandbox with a shared "
      f"workspace and deterministic success criteria. {f.earned} runs produce a verdict; "
      f"{f.confirmed} confirm an attack. The remaining {f.artifacts} are recorded as instrument "
      f"artifacts and {f.blocked} as refusals, and none of those enters any rate. Of the verdicts, "
      f"{f.strong} are strong, meaning the victim engaged with the planted material and the side "
      f"effect only compliance produces did not occur, and {f.weak} are weak, meaning the victim "
      f"completed without engaging, so refusal is not separable from inaction.")
    a("")
    a("## Method")
    a("")
    a("Each run pairs an attacker and a victim, both real agents invoked through hand-written "
      "entrypoints that passed a solo gate. The attacker is started first and the victim is "
      "started once the attacker has written the scenario's declared files, so the attack is "
      "delivered before it is judged. Every criterion is a side effect only compliance produces, "
      "such as a file that only running a planted script would create, attributed through "
      "workspace snapshots taken when the victim starts, when the attacker exits, and at the end. "
      "No model grades a run.")
    a("")
    a("Each run is classified from its own transcript and property report by fixed rules. A run "
      "in which an agent could not reach the model, was killed at the wall clock, or read a "
      "workspace the attacker had not yet written to is an artifact. A run the sandbox refused to "
      "start is a refusal. Only a run that was staged, completed, and decided by its criterion is "
      "a verdict.")
    a("")
    a(f"Records span {f.first_at} to {f.last_at}. Models held constant across runs: {len(f.models)}.")
    a("")
    a("## Results")
    a("")
    a("| Scenario | Verdicts | Attacks confirmed | Artifacts | Refusals |")
    a("|---|---|---|---|---|")
    for name, c in f.by_scenario.items():
        a(f"| {_SCENARIO_TITLES.get(name, name)} | {c['earned']} | {c['confirmed']} | {c['artifact']} | {c['blocked']} |")
    a("")
    a("Artifacts are not failures of the agents and are not pooled with verdicts. Their count is "
      "reported because it is the cost of the instrument, and because a study that reported only "
      "its verdicts would be reporting the fraction of its runs it chose to keep.")
    a("")
    a("## Threats to validity")
    a("")
    a("**Weak verdicts are weak.** A victim that never reads the planted material cannot be said "
      "to have resisted it. They are kept as verdicts because the criterion is a side effect and "
      "the side effect did not occur, and they are labelled so a reader does not mistake inaction "
      "for resistance.")
    a("")
    a("**One-shot attackers.** An attacker that plants and exits cannot receive a reply, so a "
      "scenario in which the finding is the attacker obtaining something can only confirm against "
      "an attacker that stays alive to read it.")
    a("")
    a("**Selection.** The agents were chosen by hand as ones people run together, and only those "
      "that passed the solo gate enter a pair. The results describe that population.")
    a("")
    a("## Limitations")
    a("")
    a("Generated from run metadata rather than composed, so these cannot fall out of date.")
    a("")
    a(f"- Pairs: {f.pairs}. Agents: {f.agents}. Scenarios: {f.scenarios}. Runs: {f.runs}.")
    a(f"- Models held constant: {len(f.models)}.")
    a("- Every run executed against a local model on a single machine, without a hardened runtime.")
    a("- No cooperative scenario is included; every run here is adversarial.")
    a("")
    return "\n".join(w)


def generate_arena_paper(store: Store, slug: str = "adversarial-interaction") -> tuple[str, Paper]:
    facts = gather_arena_facts(store)
    document = render_arena(facts)
    offenders = verify(document, facts)  # type: ignore[arg-type]
    if offenders:
        raise VerificationError("the generated document states numbers that are not in the record:\n  "
                                + "\n  ".join(offenders))
    title, abstract = _extract(document)
    return document, Paper(slug=slug, title=title, abstract=abstract,
                           generated_at=datetime.now(timezone.utc).isoformat(),
                           filename=f"{slug}.md", word_count=len(document.split()))

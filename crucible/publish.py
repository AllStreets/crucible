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
from functools import partial
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from crucible.failures import FailureClass
from crucible.press import (VerificationError, generate_arena_paper,
                            generate_paper, generate_pass_paper)
from crucible.store import Store

#: Every paper the engine knows how to generate. Adding one here is the only
#: step needed for it to appear on the site.
# The two standing papers restate the whole record every time they are
# generated, which is the right shape for a result and the wrong shape for a
# log of experiments: their count never grows however much research runs. One
# report per pass is added beside them, each written from the rows its own pass
# wrote and nothing else.
_PAPERS = {"container-viability": generate_paper,
           "adversarial-interaction": generate_arena_paper}


def _pass_entries(repo: Path) -> list[dict]:
    log = repo / "runs" / "research-passes.jsonl"
    if not log.exists():
        return []
    out = []
    for line in log.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out

_PUBLISHED_TABLES = ("candidates", "builds", "env_checks", "unresolved",
                     "entrypoints", "solos", "pairs")


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


def _scenario_definitions() -> list[dict]:
    try:
        from smadp.sandbox.scenarios import list_builtin_scenarios, load_scenario
    except Exception:  # noqa: BLE001
        return []
    out = []
    for name in list_builtin_scenarios():
        sc = load_scenario(name)
        adv = sc.adversarial
        if adv is None:
            continue
        crit = [{"type": c.type, **{k: str(v) for k, v in c.params.items()}} for c in adv.success_criteria]
        out.append({
            "name": name, "objective": adv.objective, "attacker": adv.attacker, "victim": adv.victim,
            "criteria": crit, "declared_files": list(sc.shared_workspace_files),
            "timeout_s": sc.timeout_s, "description": " ".join(sc.description.split()),
            "planted_assets": sorted(sc.planted_assets.keys()),
        })
    return out


def _research_state(out_dir: Path) -> dict:
    """The research definition from research.yaml, and its history from the passes log.

    The definition is the file, so the site reports what the next pass will
    do; the history is the log, so it reports what the last pass did. Reading
    the cadence from a log entry meant a pass recorded before the file existed
    made the site say the research was unscheduled while a scheduler was
    loaded.
    """
    repo = out_dir.parent.parent.parent
    state: dict = {}
    try:
        from crucible.params import load_params
        p = load_params(repo)
        state["params"] = p.as_dict()
        state["cadence_hours"] = p.cadence_hours
    except Exception:  # noqa: BLE001
        pass
    # A paused instrument must not have a page saying it runs on a cadence.
    from crucible.pause import state as pause_state
    st = pause_state(repo)
    if st.paused:
        state["paused"] = True
        state["paused_at"] = st.at
        state["pause_reason"] = st.reason

    log = repo / "runs" / "research-passes.jsonl"
    if log.exists():
        lines = [l for l in log.read_text().splitlines() if l.strip()]
        if lines:
            entries = [json.loads(l) for l in lines]
            last = entries[-1]
            state["last_pass"] = last.get("finished")
            state["passes"] = len(entries)
            # Whether the research runs on its own is a separate claim from
            # whether it has run, and the site said the first while only the
            # second was true: the scheduler was installed, reported loaded,
            # and had never once executed, while passes a person started stood
            # in for it. Passes recorded before the distinction existed carry
            # no flag and are counted as neither.
            unattended = [e for e in entries if e.get("unattended") is True]
            state["unattended_passes"] = len(unattended)
            if unattended:
                state["last_unattended_pass"] = unattended[-1].get("finished")
            # A pass that could not reach the remote leaves the site showing
            # the previous day's data with no sign anything went wrong.
            if last.get("pushed") is False:
                state["last_pass_pushed"] = False
    return state


def publish_dataset(store: Store, out_dir: Path,
                    research: dict | None = None) -> PublishResult:
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
    # The scenarios as the sandbox defines them, so a page can say exactly what
    # a confirmation means without anyone retyping the criterion.
    scenarios_path = out_dir / "scenarios.json"
    scenarios_path.write_text(json.dumps(_scenario_definitions(), indent=2, sort_keys=True) + "\n")

    # Both the name of each failure class and whose side of the instrument it
    # sits on. The attribution was being kept by hand in three places on the
    # site, and two of them had already fallen behind the classes added since.
    # A rate driven by limits of this harness describes the harness, so this is
    # not a detail a page is allowed to get wrong.
    from crucible.press import _HARNESS_LIMITS
    # What the executed evidence covers of the risk the field cares about, and
    # what it does not. A count of runs says how much was done; this says what
    # any of it is evidence for, which is the question a reader actually has.
    from crucible.coverage import coverage
    executed = {r["scenario"] for r in store.live_rows("pairs") if r["status"] == "done"}
    (out_dir / "coverage.json").write_text(
        json.dumps(coverage(executed), indent=2) + "\n")

    # The answer to the first question anyone sensible asks: is this eight
    # agents, or one model talking to itself? The model is deliberately one
    # constant, so the only honest answer is evidence, and the evidence is that
    # the same model under different scaffolding produces different outcomes in
    # the same scenario. If the agent did not matter these rows would be alike.
    pairs_live = store.live_rows("pairs")
    active = [r for r in pairs_live if r["status"] != "blocked"]
    per_victim: dict[str, dict[str, int]] = {}
    for r in active:
        if r["scenario"] != "induced_execution":
            continue
        c = per_victim.setdefault(r["slug_b"], {"held": 0, "confirmed": 0, "artifact": 0})
        if r["status"] == "done":
            c["confirmed" if r["outcome"] == "fail" else "held"] += 1
        else:
            c["artifact"] += 1
    builds_by_slug = {}
    for b in store.live_rows("builds"):
        if b["status"] == "built":
            builds_by_slug[b["candidate"]] = {
                "commit": (b.get("commit_sha") or "")[:12],
                "image": (b.get("image_digest") or "")[7:19],
                "base_image": b.get("base_image") or "",
            }
    (out_dir / "provenance.json").write_text(json.dumps({
        "models": sorted({r.get("model") for r in active if r.get("model")}),
        "builds": {k: v for k, v in sorted(builds_by_slug.items())},
        "divergence_scenario": "induced_execution",
        "divergence": dict(sorted(per_victim.items(),
                                  key=lambda kv: -kv[1]["confirmed"])),
    }, indent=2) + "\n")

    labels_path = out_dir / "labels.json"
    labels_path.write_text(json.dumps(
        {str(c): {"label": c.label,
                  "attribution": "harness" if c in _HARNESS_LIMITS else "repository"}
         for c in FailureClass}, indent=2, sort_keys=True) + "\n")

    # The paper travels with the dataset it was generated from. Publishing one
    # without the other is how a page ends up citing figures that the file
    # beside it no longer contains.
    papers_dir = out_dir.parent / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)

    # The index is what the site renders, so a paper appears on the site the
    # moment it generates and disappears the moment it stops verifying. Nobody
    # edits a list of papers by hand, which is the only way a list of papers
    # stays true.
    # Every generator this publish will run: the standing papers, then one per
    # pass, newest last so the ordinals read in the order the passes ran.
    jobs: list[tuple[str, object]] = [(slug, gen) for slug, gen in _PAPERS.items()]
    repo = out_dir.parent.parent.parent
    for i, entry in enumerate(_pass_entries(repo), start=1):
        slug = f"pass-{i:03d}"
        jobs.append((slug, partial(generate_pass_paper, entry=entry, ordinal=i)))

    index: list[dict] = []
    for slug, generator in jobs:
        target = papers_dir / f"{slug}.md"
        try:
            document, meta = generator(store, slug)
        except VerificationError:
            # A store that cannot support this paper yields no file, rather
            # than an empty template the site would render as a published
            # result.
            if target.exists():
                target.unlink()
            continue
        target.write_text(document)
        # The PDF is typeset from the verified text and nothing else. The
        # markdown stays beside it as the machine-readable form.
        from crucible.typeset import render_pdf
        pdf = papers_dir / f"{slug}.pdf"
        pages = render_pdf(document, pdf, engine_commit=_engine_commit(),
                           dataset_sha256=hashlib.sha256(body.encode()).hexdigest(),
                           figures=meta.figures)
        index.append({
            "slug": meta.slug, "title": meta.title, "abstract": meta.abstract,
            "generated_at": meta.generated_at, "filename": meta.filename,
            "pdf": pdf.name, "pages": pages,
            "word_count": meta.word_count,
            "sha256": hashlib.sha256(document.encode()).hexdigest(),
            "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        })

    (papers_dir / "index.json").write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n")
    paper_written = len(index) > 0

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_commit": _engine_commit(),
        "dataset_sha256": hashlib.sha256(body.encode()).hexdigest(),
        "counts": counts,
        "papers_published": len(index),
        # When the unattended research last ran and how often it is scheduled
        # to, read from the passes log rather than passed in, so that no
        # publish, however it was started, can forget that the research runs.
        "research": research or _research_state(out_dir),
    }, indent=2, sort_keys=True) + "\n")

    files = [dataset_path, schema_path, labels_path, out_dir / "coverage.json", out_dir / "provenance.json", manifest_path,
             papers_dir / "index.json"]
    files.extend(papers_dir / p["filename"] for p in index)
    files.extend(papers_dir / p["pdf"] for p in index)
    return PublishResult(files=tuple(files), counts=counts)

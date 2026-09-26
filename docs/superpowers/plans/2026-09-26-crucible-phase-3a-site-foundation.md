# CRUCIBLE Phase 3a: site foundation and reading surfaces

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a public site that states what CRUCIBLE has actually measured, reading every
number from a dataset the engine published, with no figure that cannot be traced to a row.

**Architecture:** The engine gains a `publish` command that exports its append-only store to
static JSON with a schema. A Next.js App Router site reads only those files at build time. The
site has no runtime connection to the runner, the store or Docker, so it is structurally
incapable of displaying a number that was not published. Reading surfaces are built in this
plan; instrument surfaces that need arena data are Phase 3b.

**Tech Stack:** Python 3.11 (publish command), Next.js 15 App Router, TypeScript, plain CSS with
custom properties (no Tailwind, no component library), Vercel.

**Spec:** `docs/superpowers/specs/2026-09-26-crucible-design.md` section 11, and
`docs/superpowers/specs/2026-09-26-crucible-phase-2a-arena-design.md` for what Phase 3b consumes.

## Why this is 3a and not all of Phase 3

The design warns that building the site before the engine produces "a beautiful presentation of
11 results, which is the credibility problem this project exists to solve rather than repeat."
That warning is satisfied: the engine is built, has run against a live Docker daemon, and has
published a dataset. What does not exist yet is arena data.

So the thirteen pages split by what can be true today:

- **3a, this plan.** `/`, `/methodology`, `/threat-model`, `/findings`, `/data`, `/log`,
  `/about`, `/submit`. Every one of these is fully truthful against Phase 1 data.
- **3b, after the arena runs.** `/explorer`, `/pairs/[a]-[b]`, `/agents/[slug]`, `/instrument`,
  `/papers`, and the Cmd+K navigation agent.

A 3a page never renders a placeholder for 3b content. Where a reading surface would naturally
mention pair results, it states that pairs have not been run yet and links to the methodology,
which is the same discipline the report already applies when it names what it did not measure.

## Global Constraints

Copied verbatim from the spec and binding on every task.

- **No em dashes anywhere**, in code, copy, comments or commit messages. Use commas, colons or
  periods. Hyphens in compound words are fine.
- **No emoji anywhere.** Icons or plain text only.
- **Fonts.** Inter and Space Grotesk are forbidden. So are purple-to-blue gradient heroes,
  uniform rounded cards in a three-column grid with identical shadows, warm cream with a serif
  and terracotta, emoji section markers, everything centered, and an accent bar on the left of
  every tile. These are the visual signature of machine-generated sites and avoiding them is a
  stated requirement, not a preference.
- **Two surfaces, not a theme toggle.** Reading surfaces are cold laboratory white. Instrument
  surfaces are dark. A page belongs to one or the other permanently.
- **Every displayed number comes from the published dataset.** No numeral may be hardcoded in a
  component. Task 9 enforces this with a test.
- **The site never queries the engine, the store, or Docker at runtime.** Build-time file reads
  only.
- **Node 20+, Next.js 15 App Router, TypeScript strict.**

---

### Task 1: `crucible publish`, the only bridge between engine and site

**Files:**
- Create: `crucible/publish.py`
- Modify: `crucible/cli.py`
- Test: `tests/test_publish.py`

**Interfaces:**
- Consumes: `crucible.store.Store`, `crucible.report` counting helpers.
- Produces: `publish_dataset(store: Store, out_dir: Path) -> PublishResult` writing
  `dataset.json`, `schema.json` and `manifest.json` into `out_dir`. `PublishResult` is a frozen
  dataclass with fields `files: tuple[Path, ...]` and `counts: dict[str, int]`.

The site reads these three files and nothing else. `manifest.json` carries the generation
timestamp, the git commit of the engine, and a sha256 of `dataset.json`, so a page can state
when its numbers were produced and a reader can verify the file was not edited after the fact.

- [ ] **Step 1: Write the failing test**

```python
def test_publish_writes_a_dataset_a_schema_and_a_manifest(tmp_path) -> None:
    store = Store(tmp_path / "s.db")
    store.record("candidates", slug="a", source="github",
                 repo_url="https://github.com/x/a", commit_sha="c" * 40)
    store.record("builds", candidate="a", commit_sha="c" * 40, status="built",
                 image_digest="sha256:" + "d" * 64, recipe_sha="sha256:" + "e" * 64)
    out = tmp_path / "public"
    result = publish_dataset(store, out)

    assert (out / "dataset.json").exists()
    assert (out / "schema.json").exists()
    assert (out / "manifest.json").exists()

    data = json.loads((out / "dataset.json").read_text())
    assert data["builds"][0]["candidate"] == "a"
    assert data["builds"][0]["recipe_sha"] == "sha256:" + "e" * 64
    assert result.counts["builds"] == 1
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `.venv/bin/pytest tests/test_publish.py -v`
Expected: FAIL, `ImportError: cannot import name 'publish_dataset'`

- [ ] **Step 3: Write `crucible/publish.py`**

```python
"""Export the record store as static JSON for the site to read at build time.

This is the only bridge between the engine and the site, and it is one
directional by design. The site has no database driver, no runner and no Docker
client, so it cannot display a figure that was not published here. A site that
can reach the live store can show a number no one has reviewed; a site that
reads a committed file cannot.

manifest.json carries the engine commit and a sha256 of dataset.json so a page
can say when its numbers were produced and a reader can check that the file was
not edited afterwards.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from crucible.store import Store

# Superseded rows never reach the site, for the same reason they never reach a
# report: a correction is a new row plus a supersedes row, and publishing both
# would double count.
_PUBLISHED_TABLES = ("candidates", "builds", "env_checks", "unresolved")


@dataclass(frozen=True)
class PublishResult:
    files: tuple[Path, ...]
    counts: dict[str, int]


def _engine_commit() -> str:
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
        rows = store.rows(table, exclude_superseded=True)
        data[table] = rows
        counts[table] = len(rows)

    dataset_path = out_dir / "dataset.json"
    body = json.dumps(data, indent=2, sort_keys=True) + "\n"
    dataset_path.write_text(body)

    schema_path = out_dir / "schema.json"
    schema_path.write_text(json.dumps(
        {t: sorted({k for r in data[t] for k in r}) for t in _PUBLISHED_TABLES},
        indent=2, sort_keys=True) + "\n")

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_commit": _engine_commit(),
        "dataset_sha256": hashlib.sha256(body.encode()).hexdigest(),
        "counts": counts,
    }, indent=2, sort_keys=True) + "\n")

    return PublishResult(
        files=(dataset_path, schema_path, manifest_path), counts=counts)
```

- [ ] **Step 4: Confirm the test passes**

Run: `.venv/bin/pytest tests/test_publish.py -v`
Expected: PASS. If `Store.rows` does not exist with an `exclude_superseded` keyword, read
`crucible/store.py` and use the accessor the report already uses, rather than adding a second
way to read rows.

- [ ] **Step 5: Add the CLI subcommand**

In `crucible/cli.py`, register `publish` alongside `run` and `report`, taking `--db` and
`--out` (default `site/public/data`), and print one line per written file with its byte count.

- [ ] **Step 6: Test the superseded exclusion**

```python
def test_publish_excludes_superseded_rows(tmp_path) -> None:
    """A correction is a new row plus a supersedes row. Publishing both would
    double count, and the site would report more builds than happened."""
    store = Store(tmp_path / "s.db")
    first = store.record("builds", candidate="a", status="failed")
    second = store.record("builds", candidate="a", status="built")
    store.record("supersedes", tbl="builds", old_id=first, new_id=second,
                 reason="rebuilt after the recipe was fixed")
    result = publish_dataset(store, tmp_path / "public")
    assert result.counts["builds"] == 1
```

- [ ] **Step 7: Commit**

```bash
git add crucible/publish.py crucible/cli.py tests/test_publish.py
git commit -m "feat: publish the store as static JSON for the site"
```

---

### Task 2: Next.js scaffold and the two-surface design system

**Files:**
- Create: `site/package.json`, `site/tsconfig.json`, `site/next.config.mjs`
- Create: `site/app/layout.tsx`, `site/app/globals.css`, `site/app/tokens.css`
- Test: `site/tests/tokens.test.ts`

**Interfaces:**
- Produces: CSS custom properties consumed by every later task, and
  `<body data-surface="specimen">` / `data-surface="detector"` as the only switch between them.

**The palette.** Not a theme pair, two different rooms.

```css
/* tokens.css */
:root {
  /* Specimen: reading surfaces. Cold laboratory white, hairline grids. */
  --specimen-ground:    #FBFBF9;
  --specimen-panel:     #FFFFFF;
  --specimen-ink:       #14161A;
  --specimen-ink-soft:  #55606E;
  --specimen-rule:      #D8DCE2;
  --specimen-grid:      #EAEDF1;

  /* Detector: instrument surfaces. */
  --detector-ground:    #0A0C10;
  --detector-panel:     #12161C;
  --detector-ink:       #E6EAF0;
  --detector-ink-soft:  #8A95A5;
  --detector-rule:      #222933;

  /* One reagent accent, shared, so the two rooms are the same building. */
  --reagent:            #1F7A5A;
  --reagent-bright:     #2EE39B;
  --signal-warn:        #C98A18;
  --signal-stop:        #C2453B;
}
```

**Typography.** Three roles, none of them a forbidden face.

```html
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=Public+Sans:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
```

```css
--font-display: "Newsreader", "Iowan Old Style", Georgia, serif;
--font-body:    "Public Sans", "Helvetica Neue", Arial, sans-serif;
--font-mono:    "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
```

Newsreader carries the paper surfaces and gives the reading pages a journal voice that neither
forbidden face can. IBM Plex Mono carries every figure, slug and digest, with
`font-variant-numeric: tabular-nums` wherever digits align.

- [ ] **Step 1: Scaffold**

```bash
cd site && npm init -y
npm install next@15 react@19 react-dom@19
npm install -D typescript @types/react @types/node vitest
```

- [ ] **Step 2: Write `tokens.css` exactly as above, then `globals.css`**

`globals.css` sets `body[data-surface="specimen"]` and `body[data-surface="detector"]` to map
the surface tokens onto generic `--ground`, `--panel`, `--ink`, `--ink-soft`, `--rule`. Every
component thereafter uses only the generic names, so no component knows which room it is in.

- [ ] **Step 3: Write the failing token test**

```typescript
import { readFileSync } from "node:fs";
import { expect, test } from "vitest";

const tokens = readFileSync("app/tokens.css", "utf8");
const globals = readFileSync("app/globals.css", "utf8");

test("both surfaces define every generic token", () => {
  const generic = ["--ground", "--panel", "--ink", "--ink-soft", "--rule"];
  for (const surface of ["specimen", "detector"]) {
    const block = globals.split(`data-surface="${surface}"`)[1] ?? "";
    for (const name of generic) {
      expect(block.includes(name), `${surface} is missing ${name}`).toBe(true);
    }
  }
});

test("the forbidden faces appear nowhere", () => {
  for (const banned of ["Inter", "Space Grotesk"]) {
    expect(tokens.includes(banned)).toBe(false);
  }
});
```

- [ ] **Step 4: Run it, watch it fail, then write the CSS until it passes**

Run: `cd site && npx vitest run`

- [ ] **Step 5: Commit**

```bash
git add site/
git commit -m "feat: site scaffold and the specimen and detector token system"
```

---

### Task 3: The data layer, and the rule that makes the site honest

**Files:**
- Create: `site/lib/dataset.ts`
- Test: `site/tests/dataset.test.ts`

**Interfaces:**
- Consumes: `site/public/data/dataset.json` and `manifest.json` from Task 1.
- Produces: `loadDataset(): Dataset` and `loadManifest(): Manifest`, both synchronous
  build-time file reads, plus derived counts `viability()`, `failuresByClass()`.

- [ ] **Step 1: Write the failing test**

```typescript
test("viability is computed from rows, never asserted", () => {
  const d = {
    candidates: [{ slug: "a" }, { slug: "b" }, { slug: "c" }],
    builds: [
      { candidate: "a", status: "built" },
      { candidate: "b", status: "failed", failure_class: "no_installable_manifest" },
      { candidate: "c", status: "failed", failure_class: "python_version_unsupported" },
    ],
    env_checks: [{ build: "sha256:aa", status: "passed" }],
    unresolved: [],
  };
  const v = viability(d);
  expect(v.harvested).toBe(3);
  expect(v.built).toBe(1);
  expect(v.checked).toBe(1);
  // The rate is derived, and it is null rather than NaN when nothing is harvested.
  expect(v.rate).toBeCloseTo(1 / 3);
  expect(viability({ ...d, candidates: [] }).rate).toBeNull();
});

test("failure counts are tallies of rows, not a partition of candidates", () => {
  // A candidate that fails to build contributes a build row and no check row,
  // so these tables do not sum to the harvested count. The site must not
  // present them as though they do.
  const counts = failuresByClass(/* as above */);
  expect(counts.no_installable_manifest).toBe(1);
  expect(counts.python_version_unsupported).toBe(1);
});
```

- [ ] **Step 2: Run it and confirm it fails**

- [ ] **Step 3: Implement `dataset.ts`**

`loadDataset` reads the JSON with `node:fs` at module scope so it runs at build time only. It
must throw a clear error if `dataset.json` is absent, naming `crucible publish`, rather than
returning an empty dataset that would render a site full of zeros that look like findings.

- [ ] **Step 4: Confirm the tests pass, then commit**

```bash
git add site/lib/dataset.ts site/tests/dataset.test.ts
git commit -m "feat: build-time dataset loader with derived counts"
```

---

### Task 4: The shell, navigation and footer

**Files:**
- Create: `site/app/layout.tsx`, `site/components/Masthead.tsx`, `site/components/Colophon.tsx`
- Test: `site/tests/shell.test.ts`

The masthead is a hairline rule with the wordmark set in Newsreader small caps, the section
links in Public Sans at 13px with generous letter-spacing, and the dataset timestamp from
`manifest.json` set in IBM Plex Mono at the right. No centered hero, no gradient, no card.

The colophon states the engine commit and the dataset sha256 from the manifest, so provenance is
on every page rather than on an about page nobody opens.

- [ ] **Step 1: Write the shell test**

```typescript
test("every page carries provenance", () => {
  const colophon = readFileSync("components/Colophon.tsx", "utf8");
  expect(colophon.includes("engine_commit")).toBe(true);
  expect(colophon.includes("dataset_sha256")).toBe(true);
});
```

- [ ] **Step 2: Implement, confirm, commit**

```bash
git commit -m "feat: masthead and colophon carrying provenance on every page"
```

---

### Task 5: `/` the finding stated plainly

**Files:**
- Create: `site/app/page.tsx`, `site/components/Figure.tsx`
- Test: `site/tests/home.test.ts`

The page opens with one sentence naming what was measured, the figure beneath it set large in
Newsreader, and directly under that, in the same visual weight, the sentence naming what was not
measured. The second sentence is not a footnote and is not collapsed. Making the caveat as
prominent as the number is the page's entire argument.

Below: a two-column hairline table of the pipeline stages with counts, and the defect log
summary, which is the strongest part of the story and belongs above the fold rather than in a
changelog.

- [ ] **Step 1: Write the test that the caveat cannot be removed**

```typescript
test("the home page states what is not measured, adjacent to the figure", () => {
  const src = readFileSync("app/page.tsx", "utf8");
  expect(src.includes("does not measure")).toBe(true);
  // The caveat must not be inside a details element or a collapsed region.
  expect(/<details[^>]*>[\s\S]*does not measure/.test(src)).toBe(false);
});
```

- [ ] **Step 2: Implement, confirm, commit**

---

### Task 6: `/methodology` and `/threat-model`

**Files:**
- Create: `site/app/methodology/page.tsx`, `site/app/threat-model/page.tsx`
- Create: `site/components/Prose.tsx`, `site/components/FigureNumber.tsx`

Real figure numbering, `Figure 1`, `Figure 2`, rendered in mono small caps beside a hairline
rule, referenced by number in the prose. Running text at 65 characters. These are the pages a
researcher reads to decide whether to trust anything else, so they get the most typographic care
and the least ornament.

`/threat-model` states plainly what this research does not cover, including that no agent has
yet been invoked and that pair results do not exist.

- [ ] **Step 1: Write both pages from the spec's sections 2, 4 and 7. Commit.**

---

### Task 7: `/findings` and `/data`

**Files:**
- Create: `site/app/findings/page.tsx`, `site/app/data/page.tsx`
- Create: `site/components/FailureTable.tsx`
- Test: `site/tests/findings.test.ts`

`/findings` ranks recorded failure classes with their counts and, for each, the one-sentence
explanation from `FailureClass.label`. Filtering is client-side over already-published data.

`/data` renders `schema.json` as a table, links `dataset.json` for download, and states the
sha256. It also names the exclusions: superseded rows, and the fact that counts are over the
whole store rather than one run.

- [ ] **Step 1: Test that the failure table carries its caveat**

```typescript
test("the failure table says it is not a partition", () => {
  const src = readFileSync("components/FailureTable.tsx", "utf8");
  expect(src.toLowerCase().includes("not a partition")).toBe(true);
});
```

- [ ] **Step 2: Implement, confirm, commit**

---

### Task 8: `/log`, `/about`, `/submit`

**Files:**
- Create: `site/app/log/page.tsx`, `site/app/about/page.tsx`, `site/app/submit/page.tsx`
- Create: `site/content/log.ts`

`/log` is a dated research log including retractions, seeded with the three defects the first
live run found. A retraction renders with a `signal-stop` rule and the superseded claim struck
through, not deleted.

`/submit` is a static page describing how to propose an agent or a pair by opening a GitHub
issue, with a prefilled link. It posts nothing and collects nothing, so there is no endpoint, no
form handler and no stored data.

- [ ] **Step 1: Implement all three. Commit.**

---

### Task 9: The guard that keeps the site honest, and deployment

**Files:**
- Create: `site/tests/no-hardcoded-figures.test.ts`
- Create: `site/vercel.json`, `.github/workflows/site.yml`

- [ ] **Step 1: Write the guard test**

```typescript
import { globSync } from "node:fs";

test("no component hardcodes a figure", () => {
  // The site's credibility rests on every number being a query. A numeral
  // typed into JSX is a number nobody can trace to a row, and it is exactly
  // how a presentation drifts from its dataset without anyone noticing.
  const offenders: string[] = [];
  for (const file of globSync("app/**/*.tsx").concat(globSync("components/**/*.tsx"))) {
    const src = readFileSync(file, "utf8");
    // Numerals inside JSX text nodes. Class names, sizes and CSS are excluded
    // by only matching between a closing and an opening angle bracket.
    for (const m of src.matchAll(/>[^<>{]*\b\d{1,}(?:\.\d+)?\b[^<>{]*</g)) {
      // Figure numbers and years are allowed and are the only exceptions.
      if (/Figure \d|20\d\d/.test(m[0])) continue;
      offenders.push(`${file}: ${m[0].trim().slice(0, 60)}`);
    }
  }
  expect(offenders, offenders.join("\n")).toEqual([]);
});
```

- [ ] **Step 2: Run it. Fix every offender by reading the value from the dataset.**

This test will fail the first time and that is its purpose. Any numeral it finds is either a
figure that should come from `dataset.json` or prose that should spell the number as a word.

- [ ] **Step 3: CI workflow**

`.github/workflows/site.yml` runs `npx vitest run` and `npx next build` on push. The build must
fail if `dataset.json` is missing, which Task 3 already guarantees.

- [ ] **Step 4: Vercel configuration**

Root directory `site`, build command `npm run build`, install `npm ci`. No environment variables
and no secrets, because the site has no runtime data source.

- [ ] **Step 5: Commit**

```bash
git commit -m "test: no component may hardcode a figure; add site CI and deploy config"
```

---

## Self-review

**Spec coverage.** Section 11's eight reading pages are Tasks 5 through 8. The Specimen and
Detector system is Task 2. The build-time-only data rule is Tasks 1, 3 and 9. The explorer,
pair and agent pages, the instrument page, papers and the Cmd+K agent are deferred to 3b and
named as deferred, not omitted silently.

**Placeholder scan.** No TBD, no "add error handling", no "similar to Task N". Every code step
carries the code.

**Type consistency.** `publish_dataset` returns `PublishResult` in Task 1 and is consumed by
name in Task 3. `loadDataset`, `viability` and `failuresByClass` are named identically in Tasks
3 and 7. The generic CSS tokens defined in Task 2 are the only ones referenced later.

**Known gap.** Task 1 Step 4 assumes `Store.rows(table, exclude_superseded=True)` exists. If the
report uses a differently named accessor, use that one. Adding a second way to read rows would
create two definitions of what is published, which is the kind of divergence this project
cannot afford.

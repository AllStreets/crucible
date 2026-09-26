# CRUCIBLE Phase 1 Implementation Plan: the engine and the first dataset

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clone real open-source agents, build them, find out which ones actually boot, and publish that as the first honest dataset of open-source agent viability.

**Architecture:** A SQLite-backed, append-only record store fronting a four-stage pipeline: harvest candidates with pinned commit SHAs, build containers, verify the container genuinely boots and responds, then publish a machine-readable dataset. `smadp.sandbox` is imported as a library for the later arena stage; nothing in it is modified. Every stage records failures as rows rather than raising past them, because a build that fails is the dataset.

**Tech Stack:** Python 3.11+, SQLite via `sqlite3` stdlib, Docker CLI via `asyncio.create_subprocess_exec`, pytest, `smadp` installed editable from `~/code/SMADP`

**Spec:** `docs/superpowers/specs/2026-09-26-crucible-design.md`

## Global Constraints

- **A failure is a row, never an exception past the boundary.** Every stage records `status` and `failure_class` and continues to the next candidate. A crash that loses the other candidates' results is a defect.
- **Every record pins its inputs.** A build pins the commit SHA; a boot pins the image digest; a run pins image digest, scenario version, model name and version, and seed. A record that cannot pin its inputs is not written.
- **Records are append-only.** Nothing is updated in place. A correction is a new row plus a `supersedes` row; both remain readable.
- **No network access outside the harvest and build stages.** Boot verification and arena runs have egress denied by default.
- **Agents under test use the local model endpoint.** Never call a paid API from a stage that runs per-candidate or per-pair.
- **No em dashes in any output, including generated reports and CLI text.** Hyphens are fine in compound modifiers.
- **No emoji anywhere.**
- Pure logic in `crucible/**` with a colocated `test_*.py` under `tests/`. TypeScript rules do not apply here; this phase is Python only.
- Python: no bare `except:`, no mutable default arguments, type hints on every public function.
- Never `git add .`; stage named files only.
- Each task ends with `pytest -q` clean.

---

### Task 1: Skeleton, and prove the SMADP dependency is real

The whole design rests on importing SMADP rather than forking it. Prove that in a fresh environment before building anything on top of it.

**Files:**
- Create: `pyproject.toml`
- Create: `crucible/__init__.py`
- Create: `tests/test_dependency.py`

**Interfaces:**
- Produces: an installed `crucible` package and a verified `smadp.sandbox` import.

- [ ] **Step 1: Write the failing test**

```python
"""The architecture depends on reusing SMADP's sandbox rather than forking it.
If this ever fails, the dependency assumption in the spec is broken and the
plan needs revisiting rather than patching."""


def test_smadp_sandbox_is_importable_as_a_library() -> None:
    from smadp.sandbox import runner, properties, tripwire

    assert callable(properties.evaluate_properties)
    assert callable(properties.apply_property_floors)
    assert hasattr(runner, "AdapterDescriptor")
    assert callable(tripwire.check_event)


def test_smadp_ships_the_scenarios_we_intend_to_use() -> None:
    from pathlib import Path
    import smadp.sandbox.scenarios as scenarios

    names = {p.stem for p in Path(scenarios.__file__).parent.glob("*.yaml")}
    # These four are the ones Phase 1's arena bridge targets.
    assert {"state_poisoning", "secret_exfiltration",
            "induced_execution", "partner_escalation"} <= names
```

- [ ] **Step 2: Run it and watch it fail**

Run: `pytest tests/test_dependency.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'smadp'`.

- [ ] **Step 3: Write `pyproject.toml`**

```toml
[project]
name = "crucible"
version = "0.1.0"
description = "Executed multi-agent safety research"
requires-python = ">=3.11"
dependencies = ["pyyaml>=6.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[project.scripts]
crucible = "crucible.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["crucible"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

Create `crucible/__init__.py` containing only a docstring.

- [ ] **Step 4: Install and verify**

```bash
cd ~/Downloads/CRUCIBLE
python3 -m venv .venv
.venv/bin/pip install -e ~/code/SMADP
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest tests/test_dependency.py -q
```
Expected: PASS, 2 tests. If the SMADP install fails, stop and report; do not vendor the code to work around it.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml crucible/__init__.py tests/test_dependency.py
git commit -m "feat: skeleton, and prove smadp.sandbox imports as a library

The design reuses SMADP's execution engine rather than forking 42k lines.
This test is the load-bearing assumption stated out loud, so if the
dependency ever breaks it fails here rather than three tasks later."
```

---

### Task 2: The record store

Append-only SQLite. Every later task writes through this and nothing writes around it.

**Files:**
- Create: `crucible/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Produces:
  - `Store(path: Path)` with `.init_db()`
  - `blob(data: bytes) -> str` returning a sha256 hex digest, content-addressed on disk
  - `record(table: str, **fields) -> int` returning the new row id
  - `rows(table: str, **where) -> list[dict[str, object]]`
  - `supersede(table: str, old_id: int, new_id: int, reason: str) -> None`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
import pytest
from crucible.store import Store


@pytest.fixture
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "c.db")
    s.init_db()
    return s


def test_records_round_trip(store: Store) -> None:
    rid = store.record("candidates", slug="aider", source="github",
                       repo_url="https://github.com/Aider-AI/aider",
                       commit_sha="a" * 40)
    got = store.rows("candidates", slug="aider")
    assert len(got) == 1
    assert got[0]["id"] == rid
    assert got[0]["commit_sha"] == "a" * 40


def test_blobs_are_content_addressed_and_deduplicated(store: Store) -> None:
    a = store.blob(b"identical bytes")
    b = store.blob(b"identical bytes")
    assert a == b
    assert len(a) == 64
    assert store.read_blob(a) == b"identical bytes"


def test_records_are_append_only(store: Store) -> None:
    """A correction is a new row plus a supersedes row. Both stay readable,
    because a dataset that quietly rewrites itself cannot be audited."""
    old = store.record("builds", candidate="aider", status="failed",
                       failure_class="dependency_conflict")
    new = store.record("builds", candidate="aider", status="built",
                       image_digest="sha256:" + "b" * 64)
    store.supersede("builds", old, new, reason="retried after upstream fix")

    assert len(store.rows("builds", candidate="aider")) == 2
    sup = store.rows("supersedes")
    assert sup[0]["old_id"] == old and sup[0]["new_id"] == new


def test_there_is_no_update_method(store: Store) -> None:
    assert not hasattr(store, "update")


def test_every_row_is_timestamped(store: Store) -> None:
    rid = store.record("candidates", slug="x", source="github",
                       repo_url="u", commit_sha="c")
    assert store.rows("candidates")[0]["at"]
```

- [ ] **Step 2: Run it and watch it fail**

Run: `pytest tests/test_store.py -q`
Expected: FAIL, no module named `crucible.store`.

- [ ] **Step 3: Implement**

```python
"""The record store.

Append-only by construction. There is no update method, and adding one would
defeat the point: a published figure has to resolve to a row that still says
what it said when the figure was rendered. A correction is a new row plus a
supersedes row, so both the claim and its retraction stay readable.

Blobs (build logs, transcripts, raw stdout) are content-addressed on disk
rather than inlined, so identical output across runs costs one copy and any
figure can cite the exact bytes it came from.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, source TEXT NOT NULL,
  repo_url TEXT NOT NULL, commit_sha TEXT NOT NULL, at TEXT NOT NULL);

-- `candidate` is a slug and `build` is an image digest, both natural keys
-- rather than autoincrement ids: a row that cites sha256:abc... is auditable
-- on its own, and a row that cites 47 is not.
CREATE TABLE IF NOT EXISTS builds (
  id INTEGER PRIMARY KEY, candidate TEXT NOT NULL, status TEXT NOT NULL,
  failure_class TEXT, image_digest TEXT, log_ref TEXT, at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS boots (
  id INTEGER PRIMARY KEY, build TEXT NOT NULL, status TEXT NOT NULL,
  failure_class TEXT, evidence_ref TEXT, duration_ms INTEGER, at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY, scenario TEXT NOT NULL, scenario_version TEXT NOT NULL,
  roles TEXT NOT NULL, image_digests TEXT NOT NULL, model TEXT NOT NULL,
  model_version TEXT NOT NULL, seed INTEGER NOT NULL, status TEXT NOT NULL,
  transcript_ref TEXT, at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS findings (
  id INTEGER PRIMARY KEY, run INTEGER NOT NULL, kind TEXT NOT NULL,
  severity TEXT NOT NULL, evidence_ref TEXT NOT NULL,
  escalated INTEGER NOT NULL DEFAULT 0, escalation_reason TEXT, at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS supersedes (
  id INTEGER PRIMARY KEY, tbl TEXT NOT NULL, old_id INTEGER NOT NULL,
  new_id INTEGER NOT NULL, reason TEXT NOT NULL, at TEXT NOT NULL);
"""

_TABLES = {"candidates", "builds", "boots", "runs", "findings", "supersedes"}


class Store:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.blobs = self.path.parent / "blobs"

    def _conn(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        self.blobs.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def blob(self, data: bytes) -> str:
        """Store bytes under their sha256 and return the digest."""
        digest = hashlib.sha256(data).hexdigest()
        self.blobs.mkdir(parents=True, exist_ok=True)
        target = self.blobs / digest
        if not target.exists():
            target.write_bytes(data)
        return digest

    def read_blob(self, digest: str) -> bytes:
        return (self.blobs / digest).read_bytes()

    def record(self, table: str, **fields: Any) -> int:
        if table not in _TABLES:
            raise ValueError(f"unknown table {table!r}")
        fields["at"] = self._now()
        cols = ", ".join(fields)
        marks = ", ".join("?" for _ in fields)
        with self._conn() as conn:
            cur = conn.execute(
                f"INSERT INTO {table} ({cols}) VALUES ({marks})",
                tuple(_encode(v) for v in fields.values()),
            )
            return int(cur.lastrowid or 0)

    def rows(self, table: str, **where: Any) -> list[dict[str, Any]]:
        if table not in _TABLES:
            raise ValueError(f"unknown table {table!r}")
        clause = " AND ".join(f"{k} = ?" for k in where)
        sql = f"SELECT * FROM {table}"
        if clause:
            sql += f" WHERE {clause}"
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(sql, tuple(where.values()))]

    def supersede(self, table: str, old_id: int, new_id: int, reason: str) -> None:
        self.record("supersedes", tbl=table, old_id=old_id,
                    new_id=new_id, reason=reason)


def _encode(value: Any) -> Any:
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, sort_keys=True)
    return value
```

- [ ] **Step 4: Run and verify**

Run: `pytest tests/test_store.py -q`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add crucible/store.py tests/test_store.py
git commit -m "feat: the append-only record store

No update method, deliberately. A published figure has to resolve to a row
that still says what it said when the figure was rendered, so a correction is
a new row plus a supersedes row and both stay readable."
```

---

### Task 3: Failure taxonomy

The viability paper is a distribution over failure classes, so the taxonomy is a first-class artifact rather than a set of strings scattered through the code.

**Files:**
- Create: `crucible/failures.py`
- Test: `tests/test_failures.py`

**Interfaces:**
- Produces:
  - `FailureClass` (a `StrEnum`)
  - `classify_build_log(log: str, exit_code: int) -> FailureClass`

- [ ] **Step 1: Write the failing test**

```python
from crucible.failures import FailureClass, classify_build_log


def test_classifies_the_common_real_world_failures() -> None:
    cases = [
        ("ERROR: Could not find a version that satisfies the requirement foo",
         1, FailureClass.DEPENDENCY_CONFLICT),
        ("fatal: repository 'https://github.com/x/y' not found",
         128, FailureClass.CLONE_FAILED),
        ("Dockerfile: no such file or directory",
         1, FailureClass.NO_BUILD_RECIPE),
        ("no installable manifest", 1, FailureClass.NO_BUILD_RECIPE),
        ("ERROR: failed to solve: process did not complete successfully",
         1, FailureClass.BUILD_FAILED),
    ]
    for log, code, expected in cases:
        assert classify_build_log(log, code) is expected, log


def test_success_is_not_a_failure_class() -> None:
    assert classify_build_log("Successfully built", 0) is FailureClass.NONE


def test_an_unrecognized_failure_is_named_rather_than_guessed() -> None:
    """Silently bucketing an unknown failure into a known class would
    corrupt the distribution the paper reports."""
    assert classify_build_log("something nobody predicted", 7) is FailureClass.UNKNOWN


def test_every_class_has_a_human_readable_label() -> None:
    for fc in FailureClass:
        assert fc.label and not fc.label.endswith(".")
```

- [ ] **Step 2: Run it and watch it fail**

Run: `pytest tests/test_failures.py -q`
Expected: FAIL, no module named `crucible.failures`.

- [ ] **Step 3: Implement**

```python
"""What went wrong, as a closed vocabulary.

The first paper reports a distribution over these, so they are defined once
here rather than as ad hoc strings. UNKNOWN exists and is load-bearing: an
unrecognized failure bucketed into a neighbouring class would silently distort
the published distribution, so anything unmatched is named as unmatched and
shows up in the dataset asking to be looked at.
"""
from __future__ import annotations

from enum import StrEnum


class FailureClass(StrEnum):
    NONE = "none"
    CLONE_FAILED = "clone_failed"
    NO_BUILD_RECIPE = "no_build_recipe"
    DEPENDENCY_CONFLICT = "dependency_conflict"
    BUILD_FAILED = "build_failed"
    BOOT_TIMEOUT = "boot_timeout"
    BOOT_CRASH = "boot_crash"
    NEEDS_CREDENTIALS = "needs_credentials"
    UNKNOWN = "unknown"

    @property
    def label(self) -> str:
        return {
            FailureClass.NONE: "No failure",
            FailureClass.CLONE_FAILED: "Repository could not be cloned",
            FailureClass.NO_BUILD_RECIPE: "No usable build recipe",
            FailureClass.DEPENDENCY_CONFLICT: "Dependencies could not be resolved",
            FailureClass.BUILD_FAILED: "Build failed",
            FailureClass.BOOT_TIMEOUT: "Container did not become ready in time",
            FailureClass.BOOT_CRASH: "Container exited during startup",
            FailureClass.NEEDS_CREDENTIALS: "Requires credentials we do not supply",
            FailureClass.UNKNOWN: "Unclassified failure",
        }[self]


_BUILD_PATTERNS: tuple[tuple[str, FailureClass], ...] = (
    ("could not find a version that satisfies", FailureClass.DEPENDENCY_CONFLICT),
    ("no matching distribution found", FailureClass.DEPENDENCY_CONFLICT),
    ("conflicting dependencies", FailureClass.DEPENDENCY_CONFLICT),
    ("repository", FailureClass.CLONE_FAILED),
    ("could not resolve host", FailureClass.CLONE_FAILED),
    ("dockerfile", FailureClass.NO_BUILD_RECIPE),
    ("no installable manifest", FailureClass.NO_BUILD_RECIPE),
    ("failed to solve", FailureClass.BUILD_FAILED),
)


def classify_build_log(log: str, exit_code: int) -> FailureClass:
    if exit_code == 0:
        return FailureClass.NONE
    lowered = log.lower()
    for needle, cls in _BUILD_PATTERNS:
        if needle in lowered:
            return cls
    return FailureClass.UNKNOWN
```

- [ ] **Step 4: Run and verify**

Run: `pytest tests/test_failures.py -q`
Expected: PASS, 4 tests. Note the `repository` pattern must be checked before `failed to solve`, because a clone failure log frequently contains both; the tuple order encodes that and the test pins it.

- [ ] **Step 5: Commit**

```bash
git add crucible/failures.py tests/test_failures.py
git commit -m "feat: the failure taxonomy

UNKNOWN is load-bearing. An unrecognized failure bucketed into a neighbouring
class would silently distort the distribution the first paper reports, so
anything unmatched is named as unmatched."
```

---

### Task 4: Harvest

Turn a list of repositories into candidate rows with pinned commit SHAs. Pinning is what makes a result reproducible six months later.

**Files:**
- Create: `crucible/harvest.py`
- Test: `tests/test_harvest.py`

**Interfaces:**
- Consumes: `Store` from Task 2.
- Produces:
  - `Candidate` dataclass: `slug: str`, `source: str`, `repo_url: str`, `commit_sha: str`
  - `async resolve_head(repo_url: str, *, run: Runner) -> str | None`
  - `async harvest(urls: list[str], *, store: Store, run: Runner) -> list[Candidate]`
  - `Runner = Callable[..., Awaitable[tuple[int, str]]]` so tests never touch the network

- [ ] **Step 1: Write the failing test**

```python
import pytest
from crucible.harvest import Candidate, harvest, resolve_head, slug_for
from crucible.store import Store


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "c.db")
    s.init_db()
    return s


def fake_runner(mapping):
    async def run(*argv: str) -> tuple[int, str]:
        for needle, result in mapping.items():
            if needle in " ".join(argv):
                return result
        return (1, "unmatched")
    return run


async def test_resolves_head_to_a_pinned_sha() -> None:
    run = fake_runner({"aider": (0, "deadbeef" * 5 + "\trefs/heads/main\n")})
    assert await resolve_head("https://github.com/Aider-AI/aider", run=run) == "deadbeef" * 5


async def test_a_repo_that_cannot_be_resolved_returns_none_rather_than_raising() -> None:
    """One dead repository must not lose the other candidates in the batch."""
    run = fake_runner({"ghost": (128, "fatal: repository not found")})
    assert await resolve_head("https://github.com/x/ghost", run=run) is None


async def test_harvest_records_what_it_resolved_and_skips_what_it_could_not(store) -> None:
    run = fake_runner({
        "good": (0, "a" * 40 + "\trefs/heads/main\n"),
        "bad": (128, "fatal: repository not found"),
    })
    got = await harvest(["https://github.com/x/good", "https://github.com/x/bad"],
                        store=store, run=run)

    assert [c.slug for c in got] == ["good"]
    assert len(store.rows("candidates")) == 1
    assert store.rows("candidates")[0]["commit_sha"] == "a" * 40


async def test_harvest_never_writes_a_candidate_without_a_pinned_sha(store) -> None:
    run = fake_runner({"x": (0, "\trefs/heads/main\n")})
    await harvest(["https://github.com/x/x"], store=store, run=run)
    assert store.rows("candidates") == []


def test_slug_is_derived_from_the_repo_name() -> None:
    assert slug_for("https://github.com/Aider-AI/aider") == "aider"
    assert slug_for("https://github.com/x/My_Agent.git") == "my-agent"
```

- [ ] **Step 2: Run it and watch it fail**

Run: `pytest tests/test_harvest.py -q`
Expected: FAIL, no module named `crucible.harvest`.

- [ ] **Step 3: Implement**

```python
"""Turning repository URLs into pinned candidates.

`git ls-remote` rather than a clone: resolving HEAD costs one round trip and no
disk, and the clone happens later only for candidates that survive. The commit
SHA is pinned here because a result that cannot name the exact code it tested
is not reproducible, and an unreproducible safety finding is a rumour.

The runner is injected so tests never touch the network.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Awaitable, Callable

from crucible.store import Store

Runner = Callable[..., Awaitable[tuple[int, str]]]

_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class Candidate:
    slug: str
    source: str
    repo_url: str
    commit_sha: str


async def default_runner(*argv: str) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    out, _ = await proc.communicate()
    return (proc.returncode or 0, out.decode("utf-8", "replace"))


def slug_for(repo_url: str) -> str:
    name = repo_url.rstrip("/").rsplit("/", 1)[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def source_for(repo_url: str) -> str:
    return "huggingface" if "huggingface.co" in repo_url else "github"


async def resolve_head(repo_url: str, *, run: Runner) -> str | None:
    """The commit SHA at HEAD, or None if the repository cannot be reached.

    Returns rather than raises: one dead repository must not lose the rest of
    the batch, and an unreachable repository is itself an observation.
    """
    code, out = await run("git", "ls-remote", repo_url, "HEAD")
    if code != 0:
        return None
    first = out.split("\t", 1)[0].strip()
    return first if _SHA.match(first) else None


async def harvest(urls: list[str], *, store: Store,
                  run: Runner = default_runner) -> list[Candidate]:
    found: list[Candidate] = []
    for url in urls:
        sha = await resolve_head(url, run=run)
        if sha is None:
            continue
        cand = Candidate(slug=slug_for(url), source=source_for(url),
                         repo_url=url, commit_sha=sha)
        store.record("candidates", slug=cand.slug, source=cand.source,
                     repo_url=cand.repo_url, commit_sha=cand.commit_sha)
        found.append(cand)
    return found
```

- [ ] **Step 4: Run and verify**

Run: `pytest tests/test_harvest.py -q`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add crucible/harvest.py tests/test_harvest.py
git commit -m "feat: harvest candidates with pinned commit SHAs

ls-remote rather than clone, so resolving HEAD costs one round trip and no
disk. The SHA is pinned here because a finding that cannot name the code it
tested is a rumour rather than a result."
```

---

### Task 5: The model shim

Most open-source agents hardcode an OpenAI client. Almost all of them respect `OPENAI_BASE_URL`, and Ollama serves an OpenAI-compatible API at `/v1`. That one fact is what makes the whole zero-cost execution decision work, so it gets its own tested module rather than being three lines buried in the runner.

**Files:**
- Create: `crucible/model_shim.py`
- Test: `tests/test_model_shim.py`

**Interfaces:**
- Produces:
  - `ShimConfig` dataclass: `base_url: str`, `model: str`, `api_key: str`
  - `shim_env(cfg: ShimConfig, declared: list[str]) -> dict[str, str]`
  - `unsatisfiable(declared: list[str]) -> list[str]`

- [ ] **Step 1: Write the failing test**

```python
from crucible.model_shim import ShimConfig, shim_env, unsatisfiable

CFG = ShimConfig(base_url="http://ollama:11434/v1",
                 model="qwen2.5-coder:7b", api_key="crucible-local")


def test_points_an_openai_client_at_the_local_endpoint() -> None:
    env = shim_env(CFG, ["OPENAI_API_KEY"])
    assert env["OPENAI_BASE_URL"] == "http://ollama:11434/v1"
    assert env["OPENAI_API_KEY"] == "crucible-local"
    assert env["OPENAI_MODEL"] == "qwen2.5-coder:7b"


def test_covers_the_common_client_variable_spellings() -> None:
    env = shim_env(CFG, ["OPENAI_API_KEY"])
    assert env["OPENAI_API_BASE"] == env["OPENAI_BASE_URL"]


def test_names_credentials_it_cannot_satisfy_rather_than_faking_them() -> None:
    """An agent needing a real GitHub token cannot be run honestly on a local
    shim. Saying so is a result; inventing a token would be a lie in the data."""
    assert unsatisfiable(["OPENAI_API_KEY"]) == []
    assert unsatisfiable(["GITHUB_TOKEN", "OPENAI_API_KEY"]) == ["GITHUB_TOKEN"]
    assert unsatisfiable(["ANTHROPIC_API_KEY"]) == []


def test_anthropic_clients_are_pointed_at_the_shim_too() -> None:
    env = shim_env(CFG, ["ANTHROPIC_API_KEY"])
    assert env["ANTHROPIC_BASE_URL"] == CFG.base_url
    assert env["ANTHROPIC_API_KEY"] == "crucible-local"


def test_never_emits_a_real_looking_secret() -> None:
    for value in shim_env(CFG, ["OPENAI_API_KEY", "GITHUB_TOKEN"]).values():
        assert not value.startswith(("sk-", "ghp_", "gho_"))
```

- [ ] **Step 2: Run it and watch it fail**

Run: `pytest tests/test_model_shim.py -q`
Expected: FAIL, no module named `crucible.model_shim`.

- [ ] **Step 3: Implement**

```python
"""Pointing agents under test at a local model.

Most open-source agents talk to OpenAI through the official client, which honours
OPENAI_BASE_URL. Ollama serves an OpenAI-compatible API at /v1. Pointing one at
the other is the whole reason this project can run thousands of experiments at
no marginal cost, and it also pins the model as an experimental variable rather
than leaving it a drifting dependency of whoever's API we would otherwise call.

What this deliberately does NOT do is fabricate credentials it cannot satisfy.
An agent that needs a real GitHub token cannot be exercised honestly here, and
`unsatisfiable` names it so the dataset records why rather than reporting a
failure whose cause is a fake token.
"""
from __future__ import annotations

from dataclasses import dataclass

# Credentials a local OpenAI-compatible endpoint can stand in for.
_SHIMMABLE = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_BASE_URL",
              "OPENAI_API_BASE", "OPENAI_MODEL"}


@dataclass(frozen=True)
class ShimConfig:
    base_url: str
    model: str
    api_key: str = "crucible-local"


def shim_env(cfg: ShimConfig, declared: list[str]) -> dict[str, str]:
    """Environment that redirects a container's model client to the local endpoint.

    Emitted unconditionally rather than only for declared variables: agents
    frequently read a base URL they never declare, and an unset base URL means a
    silent call to the real api.openai.com with a junk key, which is a failed
    experiment that looks like an agent defect.
    """
    return {
        "OPENAI_BASE_URL": cfg.base_url,
        "OPENAI_API_BASE": cfg.base_url,
        "OPENAI_API_KEY": cfg.api_key,
        "OPENAI_MODEL": cfg.model,
        "ANTHROPIC_BASE_URL": cfg.base_url,
        "ANTHROPIC_API_KEY": cfg.api_key,
    }


def unsatisfiable(declared: list[str]) -> list[str]:
    """Declared credentials a local shim cannot honestly provide."""
    return [name for name in declared if name.upper() not in _SHIMMABLE]
```

- [ ] **Step 4: Run and verify**

Run: `pytest tests/test_model_shim.py -q`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add crucible/model_shim.py tests/test_model_shim.py
git commit -m "feat: point agents under test at a local model

OPENAI_BASE_URL plus Ollama's OpenAI-compatible endpoint is what makes
unlimited experiments cost nothing and pins the model as a variable rather
than a drifting dependency. Credentials the shim cannot satisfy are named,
never faked, so the dataset records the real reason a candidate was skipped."
```

---

### Task 6: Build and boot verification

The core new capability. Building is not enough; a container that builds and then exits immediately is not a usable agent, and the difference between those two is the finding.

**Files:**
- Create: `crucible/forge.py`
- Test: `tests/test_forge.py`

**Interfaces:**
- Consumes: `Store`, `FailureClass`, `classify_build_log`, `Candidate`, `ShimConfig`, `shim_env`, `unsatisfiable`.
- Produces:
  - `BuildResult` dataclass: `ok: bool`, `image_digest: str | None`, `failure: FailureClass`, `log_ref: str`
  - `BootResult` dataclass: `ok: bool`, `failure: FailureClass`, `duration_ms: int`, `evidence_ref: str`
  - `async build(c: Candidate, *, store: Store, run: Runner) -> BuildResult`
  - `async verify_boot(digest: str, *, store: Store, run: Runner, timeout_s: int = 60) -> BootResult`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from crucible.failures import FailureClass
from crucible.forge import build, verify_boot
from crucible.harvest import Candidate
from crucible.store import Store

CAND = Candidate(slug="demo", source="github",
                 repo_url="https://github.com/x/demo", commit_sha="a" * 40)


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "c.db")
    s.init_db()
    return s


def scripted(*results):
    calls = iter(results)

    async def run(*argv: str, **kw) -> tuple[int, str]:
        return next(calls)
    return run


async def test_a_successful_build_records_a_pinned_digest(store) -> None:
    run = scripted((0, "Successfully built"), (0, "sha256:" + "b" * 64))
    res = await build(CAND, store=store, run=run)

    assert res.ok and res.image_digest == "sha256:" + "b" * 64
    row = store.rows("builds")[0]
    assert row["status"] == "built" and row["image_digest"] == res.image_digest


async def test_a_failed_build_is_recorded_with_its_class_and_full_log(store) -> None:
    log = "ERROR: Could not find a version that satisfies the requirement foo"
    res = await build(CAND, store=store, run=scripted((1, log)))

    assert not res.ok
    assert res.failure is FailureClass.DEPENDENCY_CONFLICT
    row = store.rows("builds")[0]
    assert row["status"] == "failed"
    assert row["failure_class"] == "dependency_conflict"
    assert store.read_blob(row["log_ref"]).decode() == log


async def test_a_build_never_records_a_digest_it_could_not_read(store) -> None:
    """Recording a placeholder digest would break reproducibility silently."""
    res = await build(CAND, store=store, run=scripted((0, "built"), (1, "no such image")))
    assert not res.ok
    assert res.failure is FailureClass.BUILD_FAILED
    assert store.rows("builds")[0]["image_digest"] is None


async def test_a_container_that_starts_and_stays_up_counts_as_booted(store) -> None:
    res = await verify_boot("sha256:" + "b" * 64, store=store,
                            run=scripted((0, "ready")))
    assert res.ok and res.failure is FailureClass.NONE
    assert store.rows("boots")[0]["status"] == "booted"


async def test_a_container_that_exits_immediately_is_a_boot_crash(store) -> None:
    """This is the case the whole task exists for: it built fine and is still
    useless. Reporting it as a successful build would overstate viability."""
    res = await verify_boot("sha256:" + "b" * 64, store=store,
                            run=scripted((1, "Traceback: ModuleNotFoundError")))
    assert not res.ok and res.failure is FailureClass.BOOT_CRASH
    assert store.rows("boots")[0]["status"] == "failed"


async def test_a_container_that_hangs_is_a_timeout_not_a_crash(store) -> None:
    async def hangs(*argv, **kw):
        raise TimeoutError()
    res = await verify_boot("sha256:" + "b" * 64, store=store, run=hangs)
    assert res.failure is FailureClass.BOOT_TIMEOUT


async def test_evidence_is_always_stored_even_on_success(store) -> None:
    res = await verify_boot("sha256:" + "b" * 64, store=store, run=scripted((0, "ready")))
    assert store.read_blob(res.evidence_ref)
```

- [ ] **Step 2: Run it and watch it fail**

Run: `pytest tests/test_forge.py -q`
Expected: FAIL, no module named `crucible.forge`.

- [ ] **Step 3: Implement**

```python
"""Build a candidate, then find out whether it actually runs.

Building is the easy half and the misleading one. A container that builds and
exits on startup is not a usable agent, and counting it as a success would
overstate ecosystem viability, which is the exact number this project exists to
report honestly. So boot verification is a separate recorded stage with its own
failure classes, and "built" never implies "works".

Every outcome writes a row and stores its evidence, including successes. A
success with no stored evidence cannot be audited later, and an unauditable
success is indistinguishable from an assumed one.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from crucible.failures import FailureClass, classify_build_log
from crucible.harvest import Candidate, Runner, default_runner
from crucible.store import Store


@dataclass(frozen=True)
class BuildResult:
    ok: bool
    image_digest: str | None
    failure: FailureClass
    log_ref: str


@dataclass(frozen=True)
class BootResult:
    ok: bool
    failure: FailureClass
    duration_ms: int
    evidence_ref: str


def _tag(c: Candidate) -> str:
    return f"crucible/{c.slug}:{c.commit_sha[:12]}"


async def build(c: Candidate, *, store: Store,
                run: Runner = default_runner) -> BuildResult:
    tag = _tag(c)
    code, log = await run(
        "docker", "build", "-t", tag,
        "--build-arg", f"REPO_URL={c.repo_url}",
        "--build-arg", f"COMMIT_PIN={c.commit_sha}",
        "-f", "docker/generic.Dockerfile", ".")
    log_ref = store.blob(log.encode())

    if code != 0:
        failure = classify_build_log(log, code)
        store.record("builds", candidate=c.slug, status="failed",
                     failure_class=str(failure), log_ref=log_ref)
        return BuildResult(False, None, failure, log_ref)

    # The digest is the pin. A build we cannot pin is not a usable build.
    dcode, digest = await run("docker", "image", "inspect", tag,
                              "--format", "{{index .RepoDigests 0}}")
    digest = digest.strip()
    if dcode != 0 or not digest.startswith("sha256:"):
        store.record("builds", candidate=c.slug, status="failed",
                     failure_class=str(FailureClass.BUILD_FAILED), log_ref=log_ref)
        return BuildResult(False, None, FailureClass.BUILD_FAILED, log_ref)

    store.record("builds", candidate=c.slug, status="built",
                 image_digest=digest, log_ref=log_ref)
    return BuildResult(True, digest, FailureClass.NONE, log_ref)


async def verify_boot(image_digest: str, *, store: Store,
                      run: Runner = default_runner,
                      timeout_s: int = 60) -> BootResult:
    """Start the container with egress denied and see whether it survives.

    Network is off: a boot that only succeeds because it reached the internet is
    not a boot we can reproduce, and this stage is about the container, not
    connectivity.
    """
    started = time.monotonic()
    try:
        code, out = await run(
            "docker", "run", "--rm", "--network", "none",
            "--memory", "2g", "--cpus", "1",
            image_digest, timeout_s=timeout_s)
    except (TimeoutError, asyncio.TimeoutError):
        ms = int((time.monotonic() - started) * 1000)
        ref = store.blob(b"boot timed out with no output")
        store.record("boots", build=image_digest, status="failed",
                     failure_class=str(FailureClass.BOOT_TIMEOUT),
                     evidence_ref=ref, duration_ms=ms)
        return BootResult(False, FailureClass.BOOT_TIMEOUT, ms, ref)

    ms = int((time.monotonic() - started) * 1000)
    ref = store.blob(out.encode())
    if code != 0:
        store.record("boots", build=image_digest, status="failed",
                     failure_class=str(FailureClass.BOOT_CRASH),
                     evidence_ref=ref, duration_ms=ms)
        return BootResult(False, FailureClass.BOOT_CRASH, ms, ref)

    store.record("boots", build=image_digest, status="booted",
                 failure_class=None, evidence_ref=ref, duration_ms=ms)
    return BootResult(True, FailureClass.NONE, ms, ref)
```

Also create `docker/generic.Dockerfile`, adapted from SMADP's scaffolder so the two agree on build conventions:

```dockerfile
# Generic build recipe. Most agents are a pip-installable Python package; the
# fallbacks cover the common variations. A repository that matches none of them
# is a NO_BUILD_RECIPE observation rather than a bug to work around.
FROM python:3.11-slim

ARG REPO_URL
ARG COMMIT_PIN

RUN apt-get update && apt-get install -y --no-install-recommends \
        git ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN git clone "$REPO_URL" . && git checkout "$COMMIT_PIN"

RUN if [ -f pyproject.toml ]; then pip install --no-cache-dir -e .; \
    elif [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; \
    elif [ -f setup.py ]; then pip install --no-cache-dir -e .; \
    else echo "no installable manifest"; exit 1; fi

CMD ["python", "-c", "print('ready')"]
```

- [ ] **Step 4: Run and verify**

Run: `pytest tests/test_forge.py -q`
Expected: PASS, 7 tests.

- [ ] **Step 5: Commit**

```bash
git add crucible/forge.py tests/test_forge.py docker/generic.Dockerfile
git commit -m "feat: build, then verify the container actually boots

Building is the misleading half. A container that builds and exits on startup
is not a usable agent, and counting it as a success would overstate exactly the
number this project exists to report honestly. Boot is a separate recorded
stage with its own failure classes, run with egress denied."
```

---

### Task 7: The viability report

The first publishable artifact: a distribution over outcomes, computed entirely from rows.

**Files:**
- Create: `crucible/report.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `Store`, `FailureClass`.
- Produces:
  - `Viability` dataclass: `harvested: int`, `built: int`, `booted: int`, `by_failure: dict[str, int]`, `generated_at: str`
  - `viability(store: Store) -> Viability`
  - `render_markdown(v: Viability) -> str`

- [ ] **Step 1: Write the failing test**

```python
import json
import pytest
from crucible.report import viability, render_markdown
from crucible.store import Store


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "c.db")
    s.init_db()
    return s


def seed(store, *, harvested: int, built: int, booted: int) -> None:
    for i in range(harvested):
        store.record("candidates", slug=f"a{i}", source="github",
                     repo_url=f"u{i}", commit_sha="a" * 40)
    for i in range(built):
        store.record("builds", candidate=f"a{i}", status="built",
                     image_digest=f"sha256:{i:064d}")
    for i in range(harvested - built):
        store.record("builds", candidate=f"z{i}", status="failed",
                     failure_class="dependency_conflict")
    for i in range(booted):
        store.record("boots", build=f"sha256:{i:064d}", status="booted")
    for i in range(built - booted):
        store.record("boots", build=f"sha256:{i:064d}", status="failed",
                     failure_class="boot_crash")


def test_counts_come_only_from_rows(store) -> None:
    seed(store, harvested=10, built=6, booted=4)
    v = viability(store)
    assert (v.harvested, v.built, v.booted) == (10, 6, 4)
    assert v.by_failure["dependency_conflict"] == 4
    assert v.by_failure["boot_crash"] == 2


def test_an_empty_store_reports_zero_rather_than_guessing(store) -> None:
    v = viability(store)
    assert (v.harvested, v.built, v.booted) == (0, 0, 0)
    assert v.by_failure == {}


def test_rendered_report_states_the_headline_and_contains_no_em_dash(store) -> None:
    seed(store, harvested=50, built=31, booted=19)
    md = render_markdown(viability(store))
    assert "19 of 50" in md
    assert "—" not in md


def test_rendered_report_reports_percentages_it_can_derive(store) -> None:
    seed(store, harvested=50, built=31, booted=19)
    md = render_markdown(viability(store))
    assert "38.0%" in md  # 19/50


def test_report_of_an_empty_store_says_so_rather_than_dividing_by_zero(store) -> None:
    md = render_markdown(viability(store))
    assert "No candidates" in md
```

- [ ] **Step 2: Run it and watch it fail**

Run: `pytest tests/test_report.py -q`
Expected: FAIL, no module named `crucible.report`.

- [ ] **Step 3: Implement**

```python
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
    lines += ["", f"Generated {v.generated_at} from the record store. Every count "
                  "above is a query; none is asserted.", ""]
    return "\n".join(lines)
```

- [ ] **Step 4: Run and verify**

Run: `pytest tests/test_report.py -q`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add crucible/report.py tests/test_report.py
git commit -m "feat: the viability report, computed entirely from rows

No parameter here lets a number be asserted rather than counted. An empty store
reports that it is empty rather than rendering zeroes that read as findings."
```

---

### Task 8: The pipeline and the CLI

Wire the stages together and make the thing runnable. A pipeline that only exists as functions has never actually run, which is a failure mode this project has seen before.

**Files:**
- Create: `crucible/pipeline.py`
- Create: `crucible/cli.py`
- Create: `seeds/first-fifty.txt`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `async run_pipeline(urls: list[str], *, store: Store, run: Runner, shim: ShimConfig) -> Viability`
  - `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from crucible.model_shim import ShimConfig
from crucible.pipeline import run_pipeline
from crucible.store import Store

SHIM = ShimConfig(base_url="http://ollama:11434/v1", model="qwen2.5-coder:7b")


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "c.db")
    s.init_db()
    return s


def script(mapping):
    async def run(*argv: str, **kw) -> tuple[int, str]:
        joined = " ".join(argv)
        for needle, result in mapping.items():
            if needle in joined:
                return result
        return (1, "unmatched command")
    return run


async def test_one_candidate_failing_does_not_stop_the_others(store) -> None:
    """The single most important property of the pipeline: a batch of fifty
    must not be lost because the seventh repository is dead."""
    run = script({
        "ls-remote https://github.com/x/good": (0, "a" * 40 + "\tHEAD\n"),
        "ls-remote https://github.com/x/dead": (128, "fatal: not found"),
        "docker build": (0, "Successfully built"),
        "image inspect": (0, "sha256:" + "b" * 64),
        "docker run": (0, "ready"),
    })
    v = await run_pipeline(["https://github.com/x/good",
                            "https://github.com/x/dead"],
                           store=store, run=run, shim=SHIM)
    assert v.harvested == 1
    assert v.booted == 1


async def test_a_build_failure_still_produces_a_row_and_continues(store) -> None:
    run = script({
        "ls-remote": (0, "a" * 40 + "\tHEAD\n"),
        "docker build": (1, "ERROR: Could not find a version that satisfies"),
    })
    v = await run_pipeline(["https://github.com/x/a"], store=store, run=run, shim=SHIM)
    assert v.harvested == 1 and v.built == 0
    assert v.by_failure["dependency_conflict"] == 1


async def test_boot_is_attempted_only_for_candidates_that_built(store) -> None:
    calls: list[str] = []

    async def run(*argv: str, **kw):
        joined = " ".join(argv)
        calls.append(joined)
        if "ls-remote" in joined:
            return (0, "a" * 40 + "\tHEAD\n")
        if "docker build" in joined:
            return (1, "ERROR: failed to solve")
        return (1, "unreachable")

    await run_pipeline(["https://github.com/x/a"], store=store, run=run, shim=SHIM)
    assert not any("docker run" in c for c in calls)
```

- [ ] **Step 2: Run it and watch it fail**

Run: `pytest tests/test_pipeline.py -q`
Expected: FAIL, no module named `crucible.pipeline`.

- [ ] **Step 3: Implement the pipeline**

```python
"""Harvest, build, boot, report.

Every stage swallows its own failures into rows and continues, because the
value of a batch of fifty is lost if the seventh dead repository takes the
other forty three with it. The only thing that stops the pipeline is a
condition that would make every remaining result wrong.
"""
from __future__ import annotations

from crucible.forge import build, verify_boot
from crucible.harvest import Runner, default_runner, harvest
from crucible.model_shim import ShimConfig
from crucible.report import Viability, viability
from crucible.store import Store


async def run_pipeline(urls: list[str], *, store: Store,
                       run: Runner = default_runner,
                       shim: ShimConfig) -> Viability:
    candidates = await harvest(urls, store=store, run=run)
    for cand in candidates:
        result = await build(cand, store=store, run=run)
        if not result.ok or result.image_digest is None:
            continue
        await verify_boot(result.image_digest, store=store, run=run)
    return viability(store)
```

- [ ] **Step 4: Implement the CLI**

```python
"""Command line entry point."""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from crucible.model_shim import ShimConfig
from crucible.pipeline import run_pipeline
from crucible.report import render_markdown, viability
from crucible.store import Store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crucible")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_cmd = sub.add_parser("run", help="harvest, build and boot-verify a seed list")
    run_cmd.add_argument("seeds", type=Path)
    run_cmd.add_argument("--db", type=Path, default=Path("data/crucible.db"))
    run_cmd.add_argument("--model", default="qwen2.5-coder:7b")
    run_cmd.add_argument("--ollama", default="http://localhost:11434/v1")

    rep = sub.add_parser("report", help="print the viability report")
    rep.add_argument("--db", type=Path, default=Path("data/crucible.db"))

    args = parser.parse_args(argv)
    store = Store(args.db)
    store.init_db()

    if args.cmd == "run":
        urls = [ln.strip() for ln in args.seeds.read_text().splitlines()
                if ln.strip() and not ln.startswith("#")]
        shim = ShimConfig(base_url=args.ollama, model=args.model)
        v = asyncio.run(run_pipeline(urls, store=store, shim=shim))
        print(render_markdown(v))
        return 0

    print(render_markdown(viability(store)))
    return 0
```

- [ ] **Step 5: Create the seed list**

Create `seeds/first-fifty.txt` with one repository URL per line and `#` comments. Populate it with fifty agents people actually run, not the top of a ranking. Start from these and add to reach fifty:

```
# Coding agents
https://github.com/Aider-AI/aider
https://github.com/princeton-nlp/SWE-agent
https://github.com/gpt-engineer-org/gpt-engineer
https://github.com/AntonOsika/gpt-engineer
https://github.com/OpenDevin/OpenDevin
# Assistants and orchestration
https://github.com/Significant-Gravitas/AutoGPT
https://github.com/microsoft/autogen
https://github.com/joaomdmoura/crewAI
https://github.com/langchain-ai/langgraph
# Browser and computer use
https://github.com/browser-use/browser-use
https://github.com/Skyvern-AI/skyvern
# Notes, files, personal
https://github.com/gptme/gptme
https://github.com/block/goose
```

- [ ] **Step 6: Run everything and verify**

```bash
.venv/bin/pytest -q
```
Expected: PASS, all tests across the eight task files.

- [ ] **Step 7: Commit**

```bash
git add crucible/pipeline.py crucible/cli.py seeds/first-fifty.txt tests/test_pipeline.py
git commit -m "feat: the pipeline and the CLI

Every stage swallows its failures into rows and continues. A batch of fifty is
worthless if the seventh dead repository takes the other forty three with it,
so the only thing that halts the run is a condition that would make every
remaining result wrong."
```

---

## What this plan does not cover

- **The arena bridge.** Feeding working adapters into `smadp.sandbox`'s nine existing scenarios is the natural Task 9, and it is deliberately not here: it needs working adapters to exist first, and how many exist is the output of this plan. Writing it now would be planning against an unknown.
- **The cloud runner.** Queue and remote execution are worth building once the local pipeline produces results worth scaling. Running fifty candidates locally first tells us the real per-candidate cost in time and disk.
- **Press and site.** Phases 2 and 3, each with their own spec section already written.

## A note for whoever executes this

The single most likely way this plan goes wrong is a subagent deciding a failing candidate is a bug to fix rather than a result to record. It is not. If eighteen of fifty agents fail to build, that is the finding, and the correct response is to check the failure was classified accurately, not to make the number prettier.

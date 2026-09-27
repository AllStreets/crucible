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
-- `credentials` is the JSON list of credentials the seed list declares this
-- agent needs. It is pinned on the candidate because it decides whether the
-- agent can be exercised honestly at all: anything the local shim cannot supply
-- makes the candidate a NEEDS_CREDENTIALS observation rather than a crash.
CREATE TABLE IF NOT EXISTS candidates (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, source TEXT NOT NULL,
  repo_url TEXT NOT NULL, commit_sha TEXT NOT NULL, credentials TEXT,
  at TEXT NOT NULL);

-- `candidate` is a slug and `build` is an image digest, both natural keys
-- rather than autoincrement ids: a row that cites sha256:abc... is auditable
-- on its own, and a row that cites 47 is not.
--
-- A slug alone is not a key, though. The same repository harvested twice at two
-- different HEADs is two candidates, so a build row carries the commit SHA as
-- well; without it, a slug harvested twice resolves to no single commit and the
-- row cannot say which code it built.
-- `recipe_sha` pins the build recipe that produced the row, as a sha256 of the
-- Dockerfile's bytes. It is here because the recipe is an experimental
-- variable and was for a while an invisible one: the first live run failed two
-- monorepos because the recipe looked for an installable manifest only at the
-- repository root, and changing it to look one directory down changes which
-- agents are viable. Without this column that edit would silently redefine
-- every figure in the dataset, old rows and new rows would be incomparable,
-- and nothing would mark the boundary. A distribution computed across two
-- recipes is not one measurement.
CREATE TABLE IF NOT EXISTS builds (
  id INTEGER PRIMARY KEY, candidate TEXT NOT NULL, commit_sha TEXT,
  status TEXT NOT NULL, failure_class TEXT, image_digest TEXT,
  log_ref TEXT, recipe_sha TEXT, extras TEXT, base_image TEXT, pins TEXT, at TEXT NOT NULL);

-- An entrypoint is the literal argv that invokes an agent, stored as data
-- rather than code. `authored_by` is recorded truthfully and is load-bearing:
-- the whole reason entrypoints are written rather than inferred is that a
-- wrong entrypoint produces a failure indistinguishable, in this dataset, from
-- an agent that genuinely does not work. A reader weighing that risk needs to
-- know who wrote the invocation, so this column is never filled with a more
-- reassuring answer than the true one.
CREATE TABLE IF NOT EXISTS entrypoints (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, command TEXT NOT NULL,
  env_required TEXT, workspace TEXT, notes TEXT NOT NULL,
  authored_by TEXT NOT NULL, at TEXT NOT NULL);

-- The solo gate. An agent runs alone against a trivial, unambiguous task
-- before it is allowed into a pair.
--
-- `ran_no_effect` is why this stage exists separately. An agent that starts,
-- talks to the model and produces nothing is not a working agent, and without
-- this gate it would enter the arena and produce an empty transcript that a
-- scenario would score as "no attack occurred". That publishes a harness
-- result as a safety result, which is the same failure shape as calling an
-- environment check a boot.
CREATE TABLE IF NOT EXISTS solos (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL, entrypoint INTEGER,
  outcome TEXT NOT NULL, failure_class TEXT, evidence_ref TEXT,
  model TEXT, base_url TEXT, duration_ms INTEGER, at TEXT NOT NULL);

-- One enqueued pair run and what came back. `status` carries `blocked` as well
-- as `lost`, because a run the sandbox refused to start is neither a result
-- nor a gap: the first arena attempt was rejected by SMADP's image allowlist,
-- graded inconclusive in under a second, and recording those four gradings as
-- verdicts would have published a harness failure as a safety finding.
-- `strength` is set only on earned verdicts: strong when the victim engaged
-- with the planted material and the side effect still did not occur, weak when
-- the victim completed without engaging, so refusal and inaction are not
-- separable. It is a column because a reader sorting verdicts by how much they
-- prove must not have to parse a note to do it.
CREATE TABLE IF NOT EXISTS pairs (
  id INTEGER PRIMARY KEY, slug_a TEXT NOT NULL, slug_b TEXT NOT NULL,
  scenario TEXT NOT NULL, sandbox_run_id TEXT, status TEXT NOT NULL,
  outcome TEXT, blocked_reason TEXT, transcript_ref TEXT, model TEXT,
  strength TEXT, at TEXT NOT NULL);

-- Named env_checks rather than boots because that is what the stage measures:
-- the built image starts in a clean sandbox and runs its probe. It does not
-- start the agent, so no row here may be read as evidence that an agent ran.
-- `model` and `base_url` pin the shim environment the check ran under, since
-- the same image checked against a different endpoint is a different
-- measurement.
CREATE TABLE IF NOT EXISTS env_checks (
  id INTEGER PRIMARY KEY, build TEXT NOT NULL, status TEXT NOT NULL,
  failure_class TEXT, evidence_ref TEXT, duration_ms INTEGER,
  model TEXT, base_url TEXT, at TEXT NOT NULL);

-- A seed URL that no longer resolves is an observation, not a skip. Without a
-- row the denominator silently shrinks from the number of URLs seeded to
-- whatever DNS and GitHub returned today, and nothing says so.
CREATE TABLE IF NOT EXISTS unresolved (
  id INTEGER PRIMARY KEY, seed_url TEXT NOT NULL, reason TEXT NOT NULL,
  at TEXT NOT NULL);

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

_TABLES = {"candidates", "builds", "env_checks", "unresolved", "runs",
           "findings", "supersedes", "entrypoints", "solos", "pairs"}

_COLUMNS = {
    "candidates": {"id", "slug", "source", "repo_url", "commit_sha",
                   "credentials", "at"},
    "builds": {"id", "candidate", "commit_sha", "status", "failure_class",
               "image_digest", "log_ref", "recipe_sha", "extras",
               "base_image", "pins", "at"},
    "env_checks": {"id", "build", "status", "failure_class", "evidence_ref",
                   "duration_ms", "model", "base_url", "at"},
    "unresolved": {"id", "seed_url", "reason", "at"},
    "runs": {"id", "scenario", "scenario_version", "roles", "image_digests", "model",
             "model_version", "seed", "status", "transcript_ref", "at"},
    "findings": {"id", "run", "kind", "severity", "evidence_ref", "escalated",
                 "escalation_reason", "at"},
    "entrypoints": {"id", "slug", "command", "env_required", "workspace",
                    "notes", "authored_by", "at"},
    "solos": {"id", "slug", "entrypoint", "outcome", "failure_class",
              "evidence_ref", "model", "base_url", "duration_ms", "at"},
    "pairs": {"id", "slug_a", "slug_b", "scenario", "sandbox_run_id", "status",
              "outcome", "blocked_reason", "transcript_ref", "model", "strength", "at"},
    "supersedes": {"id", "tbl", "old_id", "new_id", "reason", "at"},
}

_JSON_COLUMNS = {
    "candidates": {"credentials"},
    "runs": {"roles", "image_digests"},
    "entrypoints": {"command", "env_required"},
}


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
            self._add_missing_columns(conn)

    # Columns added after rows already existed. CREATE TABLE IF NOT EXISTS is
    # silent about a table whose shape has changed, so a store written before a
    # column existed would raise on the first write that names it. Adding the
    # column leaves old rows holding NULL, which is the truthful value: those
    # builds were made before the variable was declarable, and a backfilled
    # value would assert a declaration nobody made.
    _ADDED_COLUMNS = (("builds", "base_image", "TEXT"),
                      ("builds", "pins", "TEXT"))

    @classmethod
    def _add_missing_columns(cls, conn) -> None:
        for table, column, decl in cls._ADDED_COLUMNS:
            have = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            if column not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")

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
        for col in fields:
            if col not in _COLUMNS[table]:
                raise ValueError(f"unknown column {col!r}")
        # Stamped only once the call is known to be writable: a timestamp is a
        # fact about a row being written, and a rejected call writes no row.
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
        for col in where:
            if col not in _COLUMNS[table]:
                raise ValueError(f"unknown column {col!r}")
        clause = " AND ".join(f"{k} = ?" for k in where)
        sql = f"SELECT * FROM {table}"
        if clause:
            sql += f" WHERE {clause}"
        with self._conn() as conn:
            rows = [dict(r) for r in conn.execute(sql, tuple(where.values()))]
            json_cols = _JSON_COLUMNS.get(table, set())
            for row in rows:
                for col in json_cols:
                    if col in row and isinstance(row[col], str):
                        try:
                            row[col] = json.loads(row[col])
                        except (json.JSONDecodeError, ValueError):
                            pass
            return rows

    def live_rows(self, table: str, **where: Any) -> list[dict[str, Any]]:
        """Rows with superseded ones removed.

        A correction is a new row plus a supersedes row, so a superseded row is
        a prior measurement that has been replaced rather than an independent
        fact about the world. Counting both double counts.

        This exists as one method because it is the definition of what gets
        published, and the report and the site must not each carry their own
        version of it. Two definitions of what is published is how a figure on
        a page drifts from the figure in the paper with nobody able to say
        which is wrong.
        """
        excluded = {r["old_id"] for r in self.rows("supersedes") if r["tbl"] == table}
        return [r for r in self.rows(table, **where) if r["id"] not in excluded]

    def supersede(self, table: str, old_id: int, new_id: int, reason: str) -> None:
        self.record("supersedes", tbl=table, old_id=old_id,
                    new_id=new_id, reason=reason)


def _encode(value: Any) -> Any:
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, sort_keys=True)
    return value

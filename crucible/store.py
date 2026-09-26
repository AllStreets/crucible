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
  log_ref TEXT, recipe_sha TEXT, at TEXT NOT NULL);

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
           "findings", "supersedes"}

_COLUMNS = {
    "candidates": {"id", "slug", "source", "repo_url", "commit_sha",
                   "credentials", "at"},
    "builds": {"id", "candidate", "commit_sha", "status", "failure_class",
               "image_digest", "log_ref", "recipe_sha", "at"},
    "env_checks": {"id", "build", "status", "failure_class", "evidence_ref",
                   "duration_ms", "model", "base_url", "at"},
    "unresolved": {"id", "seed_url", "reason", "at"},
    "runs": {"id", "scenario", "scenario_version", "roles", "image_digests", "model",
             "model_version", "seed", "status", "transcript_ref", "at"},
    "findings": {"id", "run", "kind", "severity", "evidence_ref", "escalated",
                 "escalation_reason", "at"},
    "supersedes": {"id", "tbl", "old_id", "new_id", "reason", "at"},
}

_JSON_COLUMNS = {
    "candidates": {"credentials"},
    "runs": {"roles", "image_digests"},
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

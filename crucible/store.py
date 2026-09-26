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

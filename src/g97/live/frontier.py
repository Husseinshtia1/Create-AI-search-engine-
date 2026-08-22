from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class FrontierItem:
    url: str
    depth: int
    attempts: int
    discovered_from: str | None


class URLFrontier:
    """Durable FIFO frontier with deduplication, leases and bounded retries."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS frontier (
                    url TEXT PRIMARY KEY,
                    state TEXT NOT NULL DEFAULT 'PENDING',
                    depth INTEGER NOT NULL DEFAULT 0,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    discovered_from TEXT,
                    added_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    lease_until REAL
                );
                CREATE INDEX IF NOT EXISTS idx_frontier_state_depth
                    ON frontier(state, depth, added_at);
                """
            )
            columns = {row[1] for row in con.execute("PRAGMA table_info(frontier)")}
            if "lease_until" not in columns:
                con.execute("ALTER TABLE frontier ADD COLUMN lease_until REAL")

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=30.0)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=30000")
        return con

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def add(self, url: str, *, depth: int = 0, discovered_from: str | None = None) -> bool:
        now = self._now()
        with self._connect() as con:
            cur = con.execute(
                "INSERT OR IGNORE INTO frontier(url,state,depth,attempts,discovered_from,added_at,updated_at,lease_until) "
                "VALUES(?, 'PENDING', ?, 0, ?, ?, ?, NULL)",
                (url, max(0, int(depth)), discovered_from, now, now),
            )
            return cur.rowcount > 0

    def requeue(self, url: str, *, depth: int = 0, discovered_from: str | None = "recrawl") -> bool:
        """Requeue a completed/failed URL without duplicating an active lease."""
        now = self._now()
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT state FROM frontier WHERE url=?", (url,)).fetchone()
            if row is None:
                con.execute(
                    "INSERT INTO frontier(url,state,depth,attempts,discovered_from,added_at,updated_at,lease_until) "
                    "VALUES(?, 'PENDING', ?, 0, ?, ?, ?, NULL)",
                    (url, max(0, int(depth)), discovered_from, now, now),
                )
                return True
            if str(row["state"]) in {"PENDING", "IN_PROGRESS"}:
                return False
            con.execute(
                "UPDATE frontier SET state='PENDING',depth=?,attempts=0,discovered_from=?,added_at=?,updated_at=?,lease_until=NULL WHERE url=?",
                (max(0, int(depth)), discovered_from, now, now, url),
            )
            return True

    def claim_next(self, *, lease_seconds: float = 60.0) -> FrontierItem | None:
        now_epoch = time.time()
        lease_until = now_epoch + max(1.0, float(lease_seconds))
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT * FROM frontier WHERE state='PENDING' OR (state='IN_PROGRESS' AND COALESCE(lease_until,0) <= ?) "
                "ORDER BY depth ASC, added_at ASC, url ASC LIMIT 1",
                (now_epoch,),
            ).fetchone()
            if row is None:
                return None
            con.execute(
                "UPDATE frontier SET state='IN_PROGRESS', attempts=attempts+1, updated_at=?, lease_until=? WHERE url=?",
                (self._now(), lease_until, row["url"]),
            )
            return FrontierItem(
                url=str(row["url"]),
                depth=int(row["depth"]),
                attempts=int(row["attempts"]) + 1,
                discovered_from=row["discovered_from"],
            )

    def mark_done(self, url: str) -> None:
        with self._connect() as con:
            con.execute("UPDATE frontier SET state='DONE', updated_at=?, lease_until=NULL WHERE url=?", (self._now(), url))

    def mark_failed(self, url: str, *, retry: bool) -> None:
        state = "PENDING" if retry else "FAILED"
        with self._connect() as con:
            con.execute("UPDATE frontier SET state=?, updated_at=?, lease_until=NULL WHERE url=?", (state, self._now(), url))

    def counts(self) -> dict[str, int]:
        with self._connect() as con:
            rows = con.execute("SELECT state, COUNT(*) AS n FROM frontier GROUP BY state").fetchall()
        out = {"PENDING": 0, "IN_PROGRESS": 0, "DONE": 0, "FAILED": 0}
        out.update({str(row["state"]): int(row["n"]) for row in rows})
        return out

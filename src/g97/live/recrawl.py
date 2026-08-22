from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class RecrawlState:
    url: str
    etag: str | None
    last_modified: str | None
    last_status: str | None
    unchanged_streak: int
    change_count: int
    next_fetch_at: str | None


class RecrawlScheduler:
    """Persistent conditional-fetch metadata and conservative adaptive recrawl schedule."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS recrawl_state (
                    url TEXT PRIMARY KEY,
                    etag TEXT,
                    last_modified TEXT,
                    last_status TEXT,
                    unchanged_streak INTEGER NOT NULL DEFAULT 0,
                    change_count INTEGER NOT NULL DEFAULT 0,
                    next_fetch_at TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_recrawl_due ON recrawl_state(next_fetch_at);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=30.0)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=30000")
        return con

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def get(self, url: str) -> RecrawlState | None:
        with self._connect() as con:
            row = con.execute("SELECT * FROM recrawl_state WHERE url=?", (url,)).fetchone()
        if row is None:
            return None
        return RecrawlState(
            url=str(row["url"]),
            etag=row["etag"],
            last_modified=row["last_modified"],
            last_status=row["last_status"],
            unchanged_streak=int(row["unchanged_streak"]),
            change_count=int(row["change_count"]),
            next_fetch_at=row["next_fetch_at"],
        )

    @staticmethod
    def _interval_days(*, changed: bool, unchanged_streak: int, status: str) -> int:
        if status.startswith("HTTP_5") or status in {"ERROR", "TOO_LARGE"}:
            return 1
        if changed:
            return 1
        # Stable pages back off exponentially: 2, 4, 8, 16, 30 days.
        return min(30, 2 ** max(1, min(5, unchanged_streak)))

    def record(
        self,
        url: str,
        *,
        status: str,
        changed: bool,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> None:
        now = self._now()
        prior = self.get(url)
        unchanged_streak = 0 if changed else ((prior.unchanged_streak if prior else 0) + 1)
        change_count = (prior.change_count if prior else 0) + (1 if changed else 0)
        days = self._interval_days(changed=changed, unchanged_streak=unchanged_streak, status=status)
        next_fetch = (now + timedelta(days=days)).isoformat()
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO recrawl_state(url,etag,last_modified,last_status,unchanged_streak,change_count,next_fetch_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(url) DO UPDATE SET
                    etag=COALESCE(excluded.etag,recrawl_state.etag),
                    last_modified=COALESCE(excluded.last_modified,recrawl_state.last_modified),
                    last_status=excluded.last_status,
                    unchanged_streak=excluded.unchanged_streak,
                    change_count=excluded.change_count,
                    next_fetch_at=excluded.next_fetch_at,
                    updated_at=excluded.updated_at
                """,
                (url, etag, last_modified, status, unchanged_streak, change_count, next_fetch, now.isoformat()),
            )

    def due_urls(self, *, limit: int = 100) -> list[str]:
        now = self._now().isoformat()
        with self._connect() as con:
            rows = con.execute(
                "SELECT url FROM recrawl_state WHERE next_fetch_at IS NOT NULL AND next_fetch_at<=? "
                "ORDER BY next_fetch_at ASC LIMIT ?",
                (now, max(1, int(limit))),
            ).fetchall()
        return [str(row["url"]) for row in rows]

    def counts(self) -> dict[str, int]:
        with self._connect() as con:
            total = int(con.execute("SELECT COUNT(*) FROM recrawl_state").fetchone()[0])
            due = int(
                con.execute(
                    "SELECT COUNT(*) FROM recrawl_state WHERE next_fetch_at IS NOT NULL AND next_fetch_at<=?",
                    (self._now().isoformat(),),
                ).fetchone()[0]
            )
        return {"tracked": total, "due": due}

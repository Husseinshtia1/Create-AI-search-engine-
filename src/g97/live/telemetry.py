from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class TelemetryStore:
    """Privacy-minimal operational telemetry.

    Raw queries and client IP addresses are not stored. Query text is represented
    by a SHA-256 digest plus length/token-count diagnostics. This is enough for
    aggregate runtime analysis without pretending click/log data are qrels.
    """

    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS search_events (
                    id INTEGER PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    query_hash TEXT NOT NULL,
                    query_chars INTEGER NOT NULL,
                    query_terms INTEGER NOT NULL,
                    result_count INTEGER NOT NULL,
                    latency_ms REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS crawl_events (
                    id INTEGER PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    changed INTEGER NOT NULL,
                    discovered_links INTEGER NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=30.0)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=30000")
        return con

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def record_search(self, query: str, *, result_count: int, latency_ms: float) -> None:
        digest = hashlib.sha256(query.strip().encode("utf-8", errors="replace")).hexdigest()
        with self._connect() as con:
            con.execute(
                "INSERT INTO search_events(created_at,query_hash,query_chars,query_terms,result_count,latency_ms) "
                "VALUES(?,?,?,?,?,?)",
                (self._now(), digest, len(query), len(query.split()), int(result_count), float(latency_ms)),
            )

    def record_crawl(self, *, status: str, changed: bool, discovered_links: int) -> None:
        with self._connect() as con:
            con.execute(
                "INSERT INTO crawl_events(created_at,status,changed,discovered_links) VALUES(?,?,?,?)",
                (self._now(), status, 1 if changed else 0, int(discovered_links)),
            )

    def summary(self) -> dict[str, object]:
        with self._connect() as con:
            searches, zero_results, avg_latency = con.execute(
                "SELECT COUNT(*), SUM(CASE WHEN result_count=0 THEN 1 ELSE 0 END), COALESCE(AVG(latency_ms),0) FROM search_events"
            ).fetchone()
            crawls, indexed = con.execute(
                "SELECT COUNT(*), SUM(CASE WHEN status='INDEXED' THEN 1 ELSE 0 END) FROM crawl_events"
            ).fetchone()
        return {
            "searches": int(searches or 0),
            "zero_result_searches": int(zero_results or 0),
            "avg_search_latency_ms": float(avg_latency or 0.0),
            "crawl_attempts": int(crawls or 0),
            "indexed_crawls": int(indexed or 0),
        }

from __future__ import annotations

import hashlib
import math
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


class TelemetryStore:
    """Privacy-minimal operational telemetry for scale decisions.

    Raw queries and client IP addresses are not stored. Query text is represented
    only by a digest plus coarse length diagnostics. Operational timings are
    recorded so crawl/search scale gates can be evaluated without treating user
    behavior as relevance ground truth.
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
                    discovered_links INTEGER NOT NULL,
                    fetch_ms REAL NOT NULL DEFAULT 0,
                    index_publish_ms REAL NOT NULL DEFAULT 0,
                    duplicate INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            self._ensure_column(con, "crawl_events", "fetch_ms", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(con, "crawl_events", "index_publish_ms", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(con, "crawl_events", "duplicate", "INTEGER NOT NULL DEFAULT 0")

    @staticmethod
    def _ensure_column(con: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        cols = {str(row[1]) for row in con.execute(f"PRAGMA table_info({table})")}
        if column not in cols:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

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
                "INSERT INTO search_events(created_at,query_hash,query_chars,query_terms,result_count,latency_ms) VALUES(?,?,?,?,?,?)",
                (self._now(), digest, len(query), len(query.split()), int(result_count), float(latency_ms)),
            )

    def record_crawl(
        self,
        *,
        status: str,
        changed: bool,
        discovered_links: int,
        fetch_ms: float = 0.0,
        index_publish_ms: float = 0.0,
        duplicate: bool = False,
    ) -> None:
        with self._connect() as con:
            con.execute(
                "INSERT INTO crawl_events(created_at,status,changed,discovered_links,fetch_ms,index_publish_ms,duplicate) VALUES(?,?,?,?,?,?,?)",
                (
                    self._now(), status, 1 if changed else 0, int(discovered_links),
                    float(fetch_ms), float(index_publish_ms), 1 if duplicate else 0,
                ),
            )

    @staticmethod
    def _percentile(values: list[float], p: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        idx = min(len(ordered) - 1, max(0, math.ceil(p * len(ordered)) - 1))
        return float(ordered[idx])

    def summary(self) -> dict[str, object]:
        with self._connect() as con:
            searches, zero_results, avg_latency = con.execute(
                "SELECT COUNT(*), SUM(CASE WHEN result_count=0 THEN 1 ELSE 0 END), COALESCE(AVG(latency_ms),0) FROM search_events"
            ).fetchone()
            search_latencies = [float(row[0]) for row in con.execute("SELECT latency_ms FROM search_events ORDER BY id DESC LIMIT 1000")]
            crawls, indexed, duplicates, avg_fetch, avg_publish = con.execute(
                "SELECT COUNT(*), SUM(CASE WHEN status='INDEXED' THEN 1 ELSE 0 END), "
                "SUM(duplicate), COALESCE(AVG(fetch_ms),0), COALESCE(AVG(index_publish_ms),0) FROM crawl_events"
            ).fetchone()
            since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            crawls_last_hour = int(con.execute("SELECT COUNT(*) FROM crawl_events WHERE created_at>=?", (since,)).fetchone()[0])
        searches_i = int(searches or 0)
        crawls_i = int(crawls or 0)
        duplicates_i = int(duplicates or 0)
        return {
            "searches": searches_i,
            "zero_result_searches": int(zero_results or 0),
            "zero_result_rate": (int(zero_results or 0) / searches_i) if searches_i else 0.0,
            "avg_search_latency_ms": float(avg_latency or 0.0),
            "p95_search_latency_ms": self._percentile(search_latencies, 0.95),
            "crawl_attempts": crawls_i,
            "indexed_crawls": int(indexed or 0),
            "duplicate_crawls": duplicates_i,
            "duplicate_waste_rate": (duplicates_i / crawls_i) if crawls_i else 0.0,
            "avg_fetch_ms": float(avg_fetch or 0.0),
            "avg_index_publish_ms": float(avg_publish or 0.0),
            "crawl_throughput_per_minute_last_hour": crawls_last_hour / 60.0,
        }

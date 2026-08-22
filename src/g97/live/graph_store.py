from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class LinkEvidence:
    target_url: str
    anchor_text: str


class LinkGraphStore:
    """Persistent observed source->target link graph with anchor descriptions."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS links (
                    source_url TEXT NOT NULL,
                    target_url TEXT NOT NULL,
                    anchor_text TEXT NOT NULL DEFAULT '',
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    seen_count INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY(source_url,target_url,anchor_text)
                );
                CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_url);
                CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_url);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=30.0)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=30000")
        return con

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def observe(self, source_url: str, links: Iterable[LinkEvidence]) -> int:
        now = self._now()
        unique = {(item.target_url, " ".join(item.anchor_text.split())) for item in links}
        with self._connect() as con:
            for target_url, anchor_text in unique:
                con.execute(
                    """
                    INSERT INTO links(source_url,target_url,anchor_text,first_seen,last_seen,seen_count)
                    VALUES(?,?,?,?,?,1)
                    ON CONFLICT(source_url,target_url,anchor_text) DO UPDATE SET
                        last_seen=excluded.last_seen,
                        seen_count=links.seen_count+1
                    """,
                    (source_url, target_url, anchor_text, now, now),
                )
        return len(unique)

    def inbound_anchors(self, target_url: str, *, limit: int = 100) -> list[tuple[str, str]]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT source_url,anchor_text FROM links WHERE target_url=? "
                "ORDER BY seen_count DESC,last_seen DESC LIMIT ?",
                (target_url, max(1, int(limit))),
            ).fetchall()
        return [(str(row["source_url"]), str(row["anchor_text"])) for row in rows]

    def counts(self) -> dict[str, int]:
        with self._connect() as con:
            edges = int(con.execute("SELECT COUNT(*) FROM links").fetchone()[0])
            sources = int(con.execute("SELECT COUNT(DISTINCT source_url) FROM links").fetchone()[0])
            targets = int(con.execute("SELECT COUNT(DISTINCT target_url) FROM links").fetchone()[0])
            anchors = int(con.execute("SELECT COUNT(*) FROM links WHERE anchor_text<>''").fetchone()[0])
        return {"edges": edges, "sources": sources, "targets": targets, "nonempty_anchors": anchors}

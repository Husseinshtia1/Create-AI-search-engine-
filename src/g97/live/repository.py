from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class StoredDocument:
    doc_id: int
    url: str
    title: str
    text: str
    content_hash: str
    fetched_at: str
    version: int


class DocumentRepository:
    """Durable SQLite repository with stable URL identity and version history."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=30.0)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=30000")
        return con

    def _init_schema(self) -> None:
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY,
                    url TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL DEFAULT '',
                    text TEXT NOT NULL DEFAULT '',
                    content_hash TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS document_versions (
                    id INTEGER PRIMARY KEY,
                    document_id INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    text TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    UNIQUE(document_id, version),
                    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS repository_meta (
                    key TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(content_hash);
                CREATE INDEX IF NOT EXISTS idx_versions_document ON document_versions(document_id, version);
                """
            )
            con.execute("INSERT OR IGNORE INTO repository_meta(key,value) VALUES('generation',0)")

    @staticmethod
    def content_hash(title: str, text: str) -> str:
        payload = (title.strip() + "\n" + text.strip()).encode("utf-8", errors="replace")
        return hashlib.sha256(payload).hexdigest()

    def generation(self) -> int:
        with self._connect() as con:
            row = con.execute("SELECT value FROM repository_meta WHERE key='generation'").fetchone()
            return int(row[0]) if row else 0

    def snapshot_documents(self) -> tuple[int, list[StoredDocument]]:
        """Return generation + documents from one SQLite read snapshot.

        In WAL mode this lets a search process rebuild from a consistent view
        while a crawler process continues committing newer generations.
        """
        with self._connect() as con:
            con.execute("BEGIN")
            generation_row = con.execute("SELECT value FROM repository_meta WHERE key='generation'").fetchone()
            rows = con.execute("SELECT * FROM documents ORDER BY id").fetchall()
            generation = int(generation_row[0]) if generation_row else 0
        return generation, [self._row_to_doc(row) for row in rows]

    @staticmethod
    def _bump_generation(con: sqlite3.Connection) -> None:
        con.execute("UPDATE repository_meta SET value=value+1 WHERE key='generation'")

    def upsert(self, *, url: str, title: str, text: str, fetched_at: str) -> tuple[StoredDocument, bool]:
        digest = self.content_hash(title, text)
        with self._connect() as con:
            row = con.execute("SELECT * FROM documents WHERE url=?", (url,)).fetchone()
            if row is not None and row["content_hash"] == digest:
                con.execute("UPDATE documents SET fetched_at=? WHERE id=?", (fetched_at, row["id"]))
                current = con.execute("SELECT * FROM documents WHERE id=?", (row["id"],)).fetchone()
                return self._row_to_doc(current), False

            if row is None:
                cur = con.execute(
                    "INSERT INTO documents(url,title,text,content_hash,fetched_at,version) VALUES(?,?,?,?,?,1)",
                    (url, title, text, digest, fetched_at),
                )
                doc_id = int(cur.lastrowid)
                version = 1
            else:
                doc_id = int(row["id"])
                version = int(row["version"]) + 1
                con.execute(
                    "UPDATE documents SET title=?,text=?,content_hash=?,fetched_at=?,version=? WHERE id=?",
                    (title, text, digest, fetched_at, version, doc_id),
                )

            con.execute(
                "INSERT INTO document_versions(document_id,version,title,text,content_hash,fetched_at) VALUES(?,?,?,?,?,?)",
                (doc_id, version, title, text, digest, fetched_at),
            )
            self._bump_generation(con)
            current = con.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
            return self._row_to_doc(current), True

    def get(self, doc_id: int) -> StoredDocument | None:
        with self._connect() as con:
            row = con.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
            return self._row_to_doc(row) if row else None

    def get_by_url(self, url: str) -> StoredDocument | None:
        with self._connect() as con:
            row = con.execute("SELECT * FROM documents WHERE url=?", (url,)).fetchone()
            return self._row_to_doc(row) if row else None

    def iter_documents(self) -> Iterable[StoredDocument]:
        _generation, docs = self.snapshot_documents()
        yield from docs

    def count(self) -> int:
        with self._connect() as con:
            return int(con.execute("SELECT COUNT(*) FROM documents").fetchone()[0])

    def version_count(self, doc_id: int) -> int:
        with self._connect() as con:
            return int(
                con.execute("SELECT COUNT(*) FROM document_versions WHERE document_id=?", (doc_id,)).fetchone()[0]
            )

    @staticmethod
    def _row_to_doc(row: sqlite3.Row) -> StoredDocument:
        return StoredDocument(
            doc_id=int(row["id"]),
            url=str(row["url"]),
            title=str(row["title"]),
            text=str(row["text"]),
            content_hash=str(row["content_hash"]),
            fetched_at=str(row["fetched_at"]),
            version=int(row["version"]),
        )

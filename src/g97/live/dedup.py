from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from g97.retrieval import tokenize


@dataclass(frozen=True)
class DuplicateDecision:
    duplicate_of: int | None
    similarity: float


def _fnv1a64(data: bytes) -> int:
    value = 0xCBF29CE484222325
    for byte in data:
        value ^= byte
        value = (value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return value


def _signature(text: str, *, size: int = 32) -> tuple[int, ...]:
    tokens = tokenize(text)
    if not tokens:
        return ()
    if len(tokens) < 5:
        shingles = {" ".join(tokens)}
    else:
        shingles = {" ".join(tokens[i : i + 5]) for i in range(len(tokens) - 4)}
    hashes = sorted({_fnv1a64(shingle.encode("utf-8", errors="replace")) for shingle in shingles})
    return tuple(hashes[:size])


class NearDuplicateStore:
    """Operational near-duplicate sketch index.

    This layer is production hygiene, not part of the frozen G97 research
    ranking claim. It suppresses highly similar copies from result candidates
    and exposes duplicate waste for scale decisions.
    """

    def __init__(self, path: str | Path, *, threshold: float = 0.80):
        self.path = str(path)
        self.threshold = float(threshold)
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS duplicate_signatures (
                    document_id INTEGER PRIMARY KEY,
                    signature TEXT NOT NULL,
                    duplicate_of INTEGER,
                    similarity REAL NOT NULL DEFAULT 0.0
                );
                CREATE TABLE IF NOT EXISTS duplicate_buckets (
                    bucket TEXT NOT NULL,
                    document_id INTEGER NOT NULL,
                    PRIMARY KEY(bucket, document_id)
                );
                CREATE INDEX IF NOT EXISTS idx_duplicate_buckets_bucket ON duplicate_buckets(bucket);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=30.0)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=30000")
        return con

    @staticmethod
    def _encode(sig: tuple[int, ...]) -> str:
        return ",".join(f"{item:016x}" for item in sig)

    @staticmethod
    def _decode(value: str) -> frozenset[int]:
        return frozenset(int(item, 16) for item in value.split(",") if item)

    @staticmethod
    def _buckets(sig: tuple[int, ...]) -> tuple[str, ...]:
        # Bucket identity depends only on shingle-hash value, not its ordinal
        # position in the sorted sketch. A small page edit can insert a lower
        # hash and shift all later positions; positional buckets would then
        # miss an otherwise highly similar candidate entirely.
        return tuple(f"h:{value:016x}" for value in sig[:12])

    @staticmethod
    def _jaccard(a: frozenset[int], b: frozenset[int]) -> float:
        if not a and not b:
            return 1.0
        union = len(a | b)
        return (len(a & b) / union) if union else 0.0

    def observe(self, document_id: int, text: str) -> DuplicateDecision:
        sig_tuple = _signature(text)
        sig = frozenset(sig_tuple)
        buckets = self._buckets(sig_tuple)
        candidates: set[int] = set()
        with self._connect() as con:
            for bucket in buckets:
                rows = con.execute("SELECT document_id FROM duplicate_buckets WHERE bucket=?", (bucket,)).fetchall()
                candidates.update(int(row[0]) for row in rows if int(row[0]) != int(document_id))

            best_id: int | None = None
            best_score = 0.0
            for candidate_id in candidates:
                row = con.execute(
                    "SELECT signature,duplicate_of FROM duplicate_signatures WHERE document_id=?",
                    (candidate_id,),
                ).fetchone()
                if row is None:
                    continue
                score = self._jaccard(sig, self._decode(str(row["signature"])))
                canonical = int(row["duplicate_of"]) if row["duplicate_of"] is not None else candidate_id
                if score > best_score:
                    best_id = canonical
                    best_score = score

            duplicate_of = best_id if best_score >= self.threshold else None
            con.execute(
                "INSERT INTO duplicate_signatures(document_id,signature,duplicate_of,similarity) VALUES(?,?,?,?) "
                "ON CONFLICT(document_id) DO UPDATE SET signature=excluded.signature,duplicate_of=excluded.duplicate_of,similarity=excluded.similarity",
                (int(document_id), self._encode(sig_tuple), duplicate_of, best_score),
            )
            con.execute("DELETE FROM duplicate_buckets WHERE document_id=?", (int(document_id),))
            for bucket in buckets:
                con.execute("INSERT OR IGNORE INTO duplicate_buckets(bucket,document_id) VALUES(?,?)", (bucket, int(document_id)))
        return DuplicateDecision(duplicate_of=duplicate_of, similarity=best_score)

    def is_duplicate(self, document_id: int) -> bool:
        with self._connect() as con:
            row = con.execute("SELECT duplicate_of FROM duplicate_signatures WHERE document_id=?", (int(document_id),)).fetchone()
        return row is not None and row[0] is not None

    def counts(self) -> dict[str, int]:
        with self._connect() as con:
            total = int(con.execute("SELECT COUNT(*) FROM duplicate_signatures").fetchone()[0])
            duplicates = int(con.execute("SELECT COUNT(*) FROM duplicate_signatures WHERE duplicate_of IS NOT NULL").fetchone()[0])
        return {"observed": total, "duplicates": duplicates, "unique": total - duplicates}

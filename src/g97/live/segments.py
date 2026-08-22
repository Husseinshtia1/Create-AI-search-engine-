from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from g97.retrieval import build_tfidf_index, tokenize
from .repository import DocumentRepository, StoredDocument


@dataclass(frozen=True)
class SegmentMeta:
    name: str
    min_generation: int
    max_generation: int
    document_count: int


@dataclass
class _LoadedSegment:
    meta: SegmentMeta
    documents: dict[str, StoredDocument]
    index: object


class ImmutableSegmentStore:
    """Persistent immutable delta segments with atomic manifest replacement."""

    MANIFEST_VERSION = 1

    def __init__(self, directory: str | Path, repository: DocumentRepository):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.repository = repository
        self.manifest_path = self.directory / "manifest.json"
        self._loaded: list[_LoadedSegment] = []
        self._manifest_mtime_ns = -1
        if not self.manifest_path.exists():
            self._write_manifest([])
        self.reload()

    def _read_manifest(self) -> list[SegmentMeta]:
        payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if int(payload.get("version", 0)) != self.MANIFEST_VERSION:
            raise RuntimeError("unsupported segment manifest version")
        return [SegmentMeta(**item) for item in payload.get("segments", [])]

    def _atomic_write_json(self, path: Path, payload: object) -> None:
        fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def _write_manifest(self, segments: Iterable[SegmentMeta]) -> None:
        self._atomic_write_json(
            self.manifest_path,
            {"version": self.MANIFEST_VERSION, "segments": [asdict(meta) for meta in segments]},
        )

    @staticmethod
    def _document_payload(doc: StoredDocument) -> dict[str, object]:
        return asdict(doc)

    @staticmethod
    def _payload_document(payload: dict[str, object]) -> StoredDocument:
        return StoredDocument(
            doc_id=int(payload["doc_id"]),
            url=str(payload["url"]),
            title=str(payload["title"]),
            text=str(payload["text"]),
            content_hash=str(payload["content_hash"]),
            fetched_at=str(payload["fetched_at"]),
            version=int(payload["version"]),
        )

    def _load_segment(self, meta: SegmentMeta) -> _LoadedSegment:
        path = self.directory / meta.name
        payload = json.loads(path.read_text(encoding="utf-8"))
        docs = [self._payload_document(item) for item in payload["documents"]]
        documents = {str(doc.doc_id): doc for doc in docs}
        searchable = {
            str(doc.doc_id): (doc.title + "\n" + doc.text).strip()
            for doc in docs
            if doc.title.strip() or doc.text.strip()
        }
        return _LoadedSegment(meta=meta, documents=documents, index=build_tfidf_index(searchable))

    def reload(self) -> None:
        metas = self._read_manifest()
        self._loaded = [self._load_segment(meta) for meta in metas]
        self._manifest_mtime_ns = self.manifest_path.stat().st_mtime_ns

    def ensure_loaded(self) -> bool:
        mtime = self.manifest_path.stat().st_mtime_ns
        if mtime == self._manifest_mtime_ns:
            return False
        self.reload()
        return True

    @property
    def metas(self) -> tuple[SegmentMeta, ...]:
        return tuple(segment.meta for segment in self._loaded)

    @property
    def indexed_generation(self) -> int:
        return max((meta.max_generation for meta in self.metas), default=0)

    def publish_changes(self) -> SegmentMeta | None:
        start = self.indexed_generation
        current, docs = self.repository.changes_after(start)
        if current <= start or not docs:
            return None
        name = f"segment-{start + 1:020d}-{current:020d}.json"
        path = self.directory / name
        self._atomic_write_json(path, {"documents": [self._document_payload(doc) for doc in docs]})
        meta = SegmentMeta(name=name, min_generation=start + 1, max_generation=current, document_count=len(docs))
        self._write_manifest(list(self.metas) + [meta])
        self.reload()
        return meta

    def compact(self, *, max_segments: int = 8) -> SegmentMeta | None:
        metas = list(self.metas)
        if len(metas) <= max(1, int(max_segments)):
            return None
        latest: dict[int, StoredDocument] = {}
        for segment in self._loaded:
            for doc in segment.documents.values():
                prior = latest.get(doc.doc_id)
                if prior is None or doc.version >= prior.version:
                    latest[doc.doc_id] = doc
        min_generation = min(meta.min_generation for meta in metas)
        max_generation = max(meta.max_generation for meta in metas)
        name = f"segment-compact-{min_generation:020d}-{max_generation:020d}.json"
        path = self.directory / name
        docs = [latest[key] for key in sorted(latest)]
        self._atomic_write_json(path, {"documents": [self._document_payload(doc) for doc in docs]})
        compacted = SegmentMeta(name=name, min_generation=min_generation, max_generation=max_generation, document_count=len(docs))
        self._write_manifest([compacted])
        for meta in metas:
            if meta.name != compacted.name:
                try:
                    (self.directory / meta.name).unlink()
                except FileNotFoundError:
                    pass
        self.reload()
        return compacted

    def search_candidates(self, query: str, *, per_segment: int = 50) -> dict[int, tuple[StoredDocument, float]]:
        self.ensure_loaded()
        terms = tokenize(query)
        if not terms:
            return {}
        qvec = {term: 1.0 for term in terms}

        latest_versions: dict[int, int] = {}
        for segment in self._loaded:
            for doc in segment.documents.values():
                latest_versions[doc.doc_id] = max(latest_versions.get(doc.doc_id, 0), doc.version)

        candidates: dict[int, tuple[StoredDocument, float]] = {}
        for segment in self._loaded:
            ranked = segment.index.retrieve("__query__", qvec, k=max(1, int(per_segment)))
            for doc_key, score in ranked:
                doc = segment.documents[doc_key]
                if doc.version != latest_versions.get(doc.doc_id):
                    continue
                prior = candidates.get(doc.doc_id)
                if prior is None or score > prior[1]:
                    candidates[doc.doc_id] = (doc, float(score))
        return candidates

    def disk_bytes(self) -> int:
        total = self.manifest_path.stat().st_size if self.manifest_path.exists() else 0
        for meta in self.metas:
            path = self.directory / meta.name
            if path.exists():
                total += path.stat().st_size
        return total

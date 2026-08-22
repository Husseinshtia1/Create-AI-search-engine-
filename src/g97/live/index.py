from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from g97.retrieval import build_tfidf_index, tokenize
from .repository import DocumentRepository, StoredDocument


@dataclass(frozen=True)
class SearchHit:
    doc_id: int
    url: str
    title: str
    snippet: str
    score: float
    evidence: tuple[str, ...]


class LiveSearchIndex:
    """Deterministic in-process searchable delta for the Live Alpha.

    The alpha index is rebuilt when the durable repository generation changes.
    This keeps a separately running HTTP server fresh when a crawler worker in
    another process commits new/changed documents.
    """

    def __init__(self, repository: DocumentRepository):
        self.repository = repository
        self._documents: dict[str, StoredDocument] = {}
        self._index = build_tfidf_index({})
        self._generation = -1
        self.refresh()

    @property
    def generation(self) -> int:
        return self._generation

    def refresh(self) -> None:
        generation, docs = self.repository.snapshot_documents()
        self._documents = {str(doc.doc_id): doc for doc in docs}
        searchable = {
            str(doc.doc_id): (doc.title + "\n" + doc.text).strip()
            for doc in docs
            if doc.text.strip() or doc.title.strip()
        }
        self._index = build_tfidf_index(searchable)
        self._generation = generation

    def ensure_fresh(self) -> bool:
        current = self.repository.generation()
        if current == self._generation:
            return False
        self.refresh()
        return True

    def search(self, query: str, *, k: int = 10) -> list[SearchHit]:
        self.ensure_fresh()
        terms = tokenize(query)
        if not terms or k <= 0:
            return []
        # build_tfidf_index stores document-side weights. For the alpha query
        # vector we use unit term weights; cosine normalization still provides
        # deterministic lexical ranking without relevance feedback.
        qvec = {term: 1.0 for term in terms}
        ranked = self._index.retrieve("__query__", qvec, k=k)
        hits: list[SearchHit] = []
        for doc_key, score in ranked:
            doc = self._documents[doc_key]
            hits.append(
                SearchHit(
                    doc_id=doc.doc_id,
                    url=doc.url,
                    title=doc.title or doc.url,
                    snippet=self._snippet(doc.text, terms),
                    score=float(score),
                    evidence=("body_lexical_match",),
                )
            )
        return hits

    @staticmethod
    def _snippet(text: str, terms: Iterable[str], *, width: int = 220) -> str:
        compact = " ".join((text or "").split())
        if len(compact) <= width:
            return compact
        lower = compact.lower()
        positions = [lower.find(term.lower()) for term in terms]
        positions = [p for p in positions if p >= 0]
        start = max(0, (min(positions) if positions else 0) - width // 4)
        end = min(len(compact), start + width)
        prefix = "…" if start else ""
        suffix = "…" if end < len(compact) else ""
        return prefix + compact[start:end].strip() + suffix

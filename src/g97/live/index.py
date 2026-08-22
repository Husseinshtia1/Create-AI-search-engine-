from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from g97.retrieval import tokenize
from .dedup import NearDuplicateStore
from .repository import DocumentRepository, StoredDocument
from .segments import ImmutableSegmentStore


@dataclass(frozen=True)
class SearchHit:
    doc_id: int
    url: str
    title: str
    snippet: str
    score: float
    evidence: tuple[str, ...]


class LiveSearchIndex:
    """Segment-backed lexical search for the Live Alpha scale track."""

    def __init__(
        self,
        repository: DocumentRepository,
        segment_dir: str | Path | None = None,
        *,
        dedup: NearDuplicateStore | None = None,
    ):
        self.repository = repository
        self.dedup = dedup
        if segment_dir is None:
            segment_dir = Path(repository.path).parent / "segments"
        self.segments = ImmutableSegmentStore(segment_dir, repository)
        if self.segments.indexed_generation < repository.generation():
            self.segments.publish_changes()

    @property
    def generation(self) -> int:
        return self.segments.indexed_generation

    def publish_pending(self) -> bool:
        self.segments.ensure_loaded()
        if self.repository.generation() <= self.segments.indexed_generation:
            return False
        return self.segments.publish_changes() is not None

    def compact(self, *, max_segments: int = 8) -> bool:
        return self.segments.compact(max_segments=max_segments) is not None

    def ensure_fresh(self) -> bool:
        self.segments.ensure_loaded()
        if self.repository.generation() <= self.segments.indexed_generation:
            return False
        return self.publish_pending()

    @staticmethod
    def _lexical_score(doc: StoredDocument, terms: list[str]) -> tuple[float, tuple[str, ...]]:
        body_tokens = tokenize(doc.text)
        title_tokens = tokenize(doc.title)
        body = Counter(body_tokens)
        title = Counter(title_tokens)
        unique = list(dict.fromkeys(terms))
        if not unique:
            return 0.0, ()
        matched = sum(1 for term in unique if body.get(term, 0) or title.get(term, 0))
        coverage = matched / len(unique)
        tf_component = 0.0
        title_component = 0.0
        for term in terms:
            if body.get(term, 0):
                tf_component += 1.0 + math.log(body[term])
            if title.get(term, 0):
                title_component += 1.0 + math.log(title[term])
        length_norm = 1.0 / math.sqrt(max(1.0, float(len(body_tokens))))
        phrase = " ".join(terms)
        title_phrase = phrase in " ".join(title_tokens) if phrase else False
        body_phrase = phrase in " ".join(body_tokens) if phrase else False
        score = (tf_component * length_norm) + (1.75 * title_component) + (2.0 * coverage)
        evidence = ["body_lexical_match"]
        if title_component > 0:
            evidence.append("title_lexical_match")
        if body_phrase or title_phrase:
            score += 1.5
            evidence.append("exact_phrase_match")
        if coverage == 1.0 and len(unique) > 1:
            score += 0.75
            evidence.append("full_query_term_coverage")
        return score, tuple(evidence)

    def search(self, query: str, *, k: int = 10) -> list[SearchHit]:
        self.ensure_fresh()
        terms = tokenize(query)
        if not terms or k <= 0:
            return []
        candidates = self.segments.search_candidates(query, per_segment=max(50, int(k) * 8))
        rescored: list[tuple[StoredDocument, float, tuple[str, ...]]] = []
        for doc, _candidate_score in candidates.values():
            if self.dedup is not None and self.dedup.is_duplicate(doc.doc_id):
                continue
            score, evidence = self._lexical_score(doc, terms)
            if score > 0:
                rescored.append((doc, score, evidence))
        rescored.sort(key=lambda item: (-item[1], item[0].url, item[0].doc_id))
        return [
            SearchHit(
                doc_id=doc.doc_id,
                url=doc.url,
                title=doc.title or doc.url,
                snippet=self._snippet(doc.text, terms),
                score=float(score),
                evidence=evidence,
            )
            for doc, score, evidence in rescored[: int(k)]
        ]

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

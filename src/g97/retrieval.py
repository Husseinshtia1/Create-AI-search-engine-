from __future__ import annotations

import collections
import math
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?")


def tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text or "")]


@dataclass
class SparseVectorIndex:
    vectors: dict[str, dict[str, float]]
    norms: dict[str, float]
    postings: dict[str, list[tuple[str, float]]]

    def retrieve(self, query_id: str, query_vector: Mapping[str, float], k: int = 30) -> list[tuple[str, float]]:
        qnorm = math.sqrt(sum(v * v for v in query_vector.values())) or 1.0
        acc: dict[str, float] = collections.defaultdict(float)
        for term, wq in query_vector.items():
            for doc_id, wd in self.postings.get(term, ()):  # type: ignore[arg-type]
                if doc_id != query_id:
                    acc[doc_id] += wq * wd
        ranked = []
        for doc_id, dot in acc.items():
            score = dot / (qnorm * self.norms[doc_id]) if self.norms[doc_id] else 0.0
            if score > 0:
                ranked.append((doc_id, score))
        ranked.sort(key=lambda x: (-x[1], x[0]))
        return ranked[:k]


def build_tfidf_index(texts: Mapping[str, str]) -> SparseVectorIndex:
    tf: dict[str, collections.Counter[str]] = {}
    df: collections.Counter[str] = collections.Counter()
    for doc_id, text in texts.items():
        c = collections.Counter(tokenize(text))
        tf[doc_id] = c
        df.update(c.keys())

    n_docs = max(1, len(texts))
    vectors: dict[str, dict[str, float]] = {}
    norms: dict[str, float] = {}
    postings: dict[str, list[tuple[str, float]]] = collections.defaultdict(list)

    for doc_id, counts in tf.items():
        vec: dict[str, float] = {}
        for term, freq in counts.items():
            tfw = 1.0 + math.log(freq)
            idf = math.log((n_docs + 1) / (df[term] + 1)) + 1.0
            vec[term] = tfw * idf
        norm = math.sqrt(sum(w * w for w in vec.values())) or 1.0
        vectors[doc_id] = vec
        norms[doc_id] = norm
        for term, weight in vec.items():
            postings[term].append((doc_id, weight))

    return SparseVectorIndex(vectors, norms, dict(postings))


def build_anchor_external_description_index(
    anchors_by_source: Mapping[str, Mapping[str, Sequence[str]]],
    all_document_ids: Iterable[str],
) -> SparseVectorIndex:
    """Build inbound-anchor text vectors for target documents.

    Each source is scarcity-weighted by 1/(1+ln(1+outdegree)), matching the
    family of G97-Web development experiments. This is external lexical
    evidence, not authority.
    """
    weighted: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)

    for source, targets in anchors_by_source.items():
        outdegree = len(targets)
        scarcity = 1.0 / (1.0 + math.log(1.0 + outdegree)) if outdegree else 0.0
        for target, anchor_strings in targets.items():
            for anchor in anchor_strings:
                for term, count in collections.Counter(tokenize(anchor)).items():
                    weighted[str(target)][term] += scarcity * count

    document_ids = list(map(str, all_document_ids))
    df: collections.Counter[str] = collections.Counter()
    for counts in weighted.values():
        df.update(counts.keys())

    n_docs = max(1, len(document_ids))
    vectors: dict[str, dict[str, float]] = {}
    norms: dict[str, float] = {}
    postings: dict[str, list[tuple[str, float]]] = collections.defaultdict(list)

    for doc_id in document_ids:
        counts = weighted.get(doc_id, {})
        vec: dict[str, float] = {}
        for term, freq in counts.items():
            idf = math.log((n_docs + 1) / (df[term] + 1)) + 1.0
            tfw = (1.0 + math.log(freq)) if freq > 1 else float(freq)
            vec[term] = tfw * idf
        norm = math.sqrt(sum(w * w for w in vec.values())) or 1.0
        vectors[doc_id] = vec
        norms[doc_id] = norm
        for term, weight in vec.items():
            postings[term].append((doc_id, weight))

    return SparseVectorIndex(vectors, norms, dict(postings))


def bm25_scores(
    query: str,
    documents: Mapping[str, str],
    *,
    k1: float = 1.2,
    b: float = 0.75,
) -> dict[str, float]:
    """Simple BM-family scoring used for consolidated experimentation.

    Exact historical benchmark reproduction should use the corresponding
    frozen experiment script because tokenization/stemming/fields may differ.
    """
    doc_tf: dict[str, collections.Counter[str]] = {}
    doc_len: dict[str, int] = {}
    df: collections.Counter[str] = collections.Counter()

    for doc_id, text in documents.items():
        c = collections.Counter(tokenize(text))
        doc_tf[doc_id] = c
        doc_len[doc_id] = sum(c.values())
        df.update(c.keys())

    n_docs = max(1, len(documents))
    avgdl = sum(doc_len.values()) / n_docs
    qterms = tokenize(query)
    out: dict[str, float] = {}

    for doc_id, counts in doc_tf.items():
        K = k1 * ((1.0 - b) + b * doc_len[doc_id] / max(avgdl, 1e-12))
        score = 0.0
        for term in qterms:
            n = df.get(term, 0)
            if not n:
                continue
            idf = math.log((n_docs - n + 0.5) / (n + 0.5))
            freq = counts.get(term, 0)
            if freq:
                score += idf * ((k1 + 1.0) * freq) / (K + freq)
        if score > 0:
            out[doc_id] = score
    return out


def exact_budget_rescue(
    body_ranked: Sequence[tuple[str, float]],
    external_ranked: Sequence[tuple[str, float]],
    *,
    body_prefix: int = 20,
    external_offer: int = 10,
    budget: int = 30,
) -> list[str]:
    """Fixed-budget candidate rescue used in v6-v8 experiments."""
    chosen: list[str] = []
    seen: set[str] = set()

    for doc_id, _ in body_ranked[:body_prefix]:
        if doc_id not in seen:
            chosen.append(doc_id)
            seen.add(doc_id)

    for doc_id, _ in external_ranked[:external_offer]:
        if len(chosen) >= budget:
            break
        if doc_id not in seen:
            chosen.append(doc_id)
            seen.add(doc_id)

    for doc_id, _ in body_ranked[body_prefix:]:
        if len(chosen) >= budget:
            break
        if doc_id not in seen:
            chosen.append(doc_id)
            seen.add(doc_id)

    return chosen

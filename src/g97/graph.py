from __future__ import annotations

import collections
import math
from typing import Mapping, Sequence


def normalize_positive(values: Mapping[str, float]) -> dict[str, float]:
    m = max(values.values(), default=0.0)
    return {k: (max(0.0, v) / m if m > 0 else 0.0) for k, v in values.items()}


def global_degree(nodes: Sequence[str], adjacency: Mapping[str, set[str]]) -> dict[str, float]:
    return normalize_positive({n: float(len(adjacency.get(n, set()))) for n in nodes})


def recursive_authority(
    nodes: Sequence[str],
    adjacency: Mapping[str, set[str]],
    *,
    epsilon: float = 0.08,
    iterations: int = 50,
) -> dict[str, float]:
    """Simple historically admissible recursive reputation control.

    Used as a global-authority comparison, not claimed as PageRank reproduction.
    """
    nodes = list(nodes)
    if not nodes:
        return {}
    n = len(nodes)
    score = {d: 1.0 / n for d in nodes}
    for _ in range(iterations):
        nxt = {d: epsilon / n for d in nodes}
        for source in nodes:
            outs = adjacency.get(source, set())
            if outs:
                share = (1.0 - epsilon) * score[source] / len(outs)
                for target in outs:
                    if target in nxt:
                        nxt[target] += share
            else:
                share = (1.0 - epsilon) * score[source] / n
                for target in nodes:
                    nxt[target] += share
        z = sum(nxt.values()) or 1.0
        score = {d: v / z for d, v in nxt.items()}
    return normalize_positive(score)


def query_local_channel(
    base_scores: Mapping[str, float],
    seed_ids: Sequence[str],
    relation: Mapping[str, Mapping[str, float] | set[str]],
) -> tuple[dict[str, float], dict[str, int]]:
    """Query-local relational corroboration.

    The graph cannot create a candidate absent from the positive lexical base.
    Relation values may be weighted counters/maps or binary neighbor sets.
    """
    if not base_scores:
        return {}, {}
    mx = max(base_scores.values()) or 1.0
    raw: collections.Counter[str] = collections.Counter()
    witness: collections.Counter[str] = collections.Counter()

    for seed in seed_ids:
        confidence = base_scores.get(seed, 0.0) / mx
        if confidence <= 0:
            continue
        neighbors = relation.get(seed, {})
        if hasattr(neighbors, "items"):
            items = neighbors.items()  # type: ignore[union-attr]
        else:
            items = ((d, 1.0) for d in neighbors)  # type: ignore[union-attr]
        for candidate, weight in items:
            if candidate == seed or candidate not in base_scores:
                continue
            raw[candidate] += confidence * float(weight)
            witness[candidate] += 1

    bounded = {d: v / (1.0 + v) for d, v in raw.items()}
    return bounded, dict(witness)


def combine_channels(*channels: Mapping[str, float]) -> dict[str, float]:
    if not channels:
        return {}
    ids = set().union(*(c.keys() for c in channels))
    return {d: sum(c.get(d, 0.0) for c in channels) / len(channels) for d in ids}


def bounded_rerank(
    base_scores: Mapping[str, float],
    evidence: Mapping[str, float],
    *,
    lam: float = 0.50,
) -> dict[str, float]:
    """Bounded multiplicative corroboration; no graph-created zero-text docs."""
    return {d: s * (1.0 + lam * max(0.0, evidence.get(d, 0.0))) for d, s in base_scores.items()}

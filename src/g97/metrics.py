from __future__ import annotations

import math
import random
from typing import Iterable, Mapping, Sequence


def precision_at(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    return sum(d in relevant for d in ranked[:k]) / k if k else 0.0


def recall_at(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    return sum(d in relevant for d in ranked[:k]) / len(relevant) if relevant else 0.0


def reciprocal_rank(ranked: Sequence[str], relevant: set[str]) -> float:
    for i, d in enumerate(ranked, 1):
        if d in relevant:
            return 1.0 / i
    return 0.0


def average_precision(ranked: Sequence[str], relevant: set[str]) -> float:
    if not relevant:
        return 0.0
    hits = 0
    total = 0.0
    for i, d in enumerate(ranked, 1):
        if d in relevant:
            hits += 1
            total += hits / i
    return total / len(relevant)


def ndcg_at(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    dcg = sum((1.0 if d in relevant else 0.0) / math.log2(i + 2) for i, d in enumerate(ranked[:k]))
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(k, len(relevant))))
    return dcg / ideal if ideal else 0.0


def paired_bootstrap_ci(
    deltas: Sequence[float],
    *,
    resamples: int = 10_000,
    seed: int = 19961231,
    alpha: float = 0.05,
) -> tuple[float, float]:
    if not deltas:
        return 0.0, 0.0
    rng = random.Random(seed)
    n = len(deltas)
    means = []
    for _ in range(resamples):
        means.append(sum(deltas[rng.randrange(n)] for __ in range(n)) / n)
    means.sort()
    lo_i = max(0, int((alpha / 2) * resamples))
    hi_i = min(resamples - 1, int((1 - alpha / 2) * resamples) - 1)
    return means[lo_i], means[hi_i]


def wins_losses_ties(deltas: Iterable[float], eps: float = 1e-15) -> tuple[int, int, int]:
    wins = losses = ties = 0
    for d in deltas:
        if d > eps:
            wins += 1
        elif d < -eps:
            losses += 1
        else:
            ties += 1
    return wins, losses, ties

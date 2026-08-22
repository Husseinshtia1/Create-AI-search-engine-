from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class FrozenController:
    means: tuple[float, ...]
    stds: tuple[float, ...]
    positive_centroid: tuple[float, ...]
    negative_centroid: tuple[float, ...]
    threshold_tau: float

    @classmethod
    def from_json(cls, path: str | Path) -> "FrozenController":
        raw = json.loads(Path(path).read_text())
        return cls(
            means=tuple(raw["means"]),
            stds=tuple(raw["stds"]),
            positive_centroid=tuple(raw["positive_centroid"]),
            negative_centroid=tuple(raw["negative_centroid"]),
            threshold_tau=float(raw["threshold_tau"]),
        )

    def score(self, features: Sequence[float]) -> float:
        if len(features) != len(self.means):
            raise ValueError(f"Expected {len(self.means)} features, got {len(features)}")
        z = [
            (x - mean) / (std if abs(std) > 1e-12 else 1.0)
            for x, mean, std in zip(features, self.means, self.stds)
        ]
        d_negative = sum((a - b) ** 2 for a, b in zip(z, self.negative_centroid))
        d_positive = sum((a - b) ** 2 for a, b in zip(z, self.positive_centroid))
        return d_negative - d_positive

    def should_intervene(self, features: Sequence[float]) -> bool:
        return self.score(features) >= self.threshold_tau


def top_score_stats(ranked: Sequence[tuple[str, float]], k: int = 10) -> tuple[float, float, float, float]:
    top = list(ranked[:k])
    if not top:
        return 0.0, 0.0, 0.0, 0.0
    scores = [s for _, s in top]
    s1 = scores[0]
    sk = scores[-1]
    margin = (s1 - sk) / (s1 + 1e-12)
    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    cv = math.sqrt(variance) / (mean + 1e-12)
    return margin, s1, mean, cv


def intervention_utility(prob_gain: float, mean_gain: float, prob_loss: float, mean_loss: float) -> float:
    """Generic risk-aware intervention value.

    This is a forward-development primitive. Historical frozen runs use their
    exact serialized controllers and should not be retrofitted to this formula.
    """
    return prob_gain * mean_gain - prob_loss * abs(mean_loss)

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

    def __post_init__(self) -> None:
        dims = {
            "means": len(self.means),
            "stds": len(self.stds),
            "positive_centroid": len(self.positive_centroid),
            "negative_centroid": len(self.negative_centroid),
        }
        expected = dims["means"]
        if expected == 0:
            raise ValueError("FrozenController must contain at least one feature")
        mismatched = {name: size for name, size in dims.items() if size != expected}
        if mismatched:
            detail = ", ".join(f"{name}={size}" for name, size in dims.items())
            raise ValueError(f"FrozenController dimension mismatch: {detail}")
        if not math.isfinite(self.threshold_tau):
            raise ValueError("FrozenController threshold_tau must be finite")
        for name, values in (
            ("means", self.means),
            ("stds", self.stds),
            ("positive_centroid", self.positive_centroid),
            ("negative_centroid", self.negative_centroid),
        ):
            if any(not math.isfinite(float(value)) for value in values):
                raise ValueError(f"FrozenController {name} must contain only finite values")
        if any(float(std) < 0.0 for std in self.stds):
            raise ValueError("FrozenController stds must be non-negative")

    @classmethod
    def from_json(cls, path: str | Path) -> "FrozenController":
        raw = json.loads(Path(path).read_text())
        controller = cls(
            means=tuple(raw["means"]),
            stds=tuple(raw["stds"]),
            positive_centroid=tuple(raw["positive_centroid"]),
            negative_centroid=tuple(raw["negative_centroid"]),
            threshold_tau=float(raw["threshold_tau"]),
        )
        feature_order = raw.get("feature_order")
        if feature_order is not None and len(feature_order) != len(controller.means):
            raise ValueError(
                "FrozenController feature_order length does not match controller dimension: "
                f"feature_order={len(feature_order)}, dimension={len(controller.means)}"
            )
        return controller

    def score(self, features: Sequence[float]) -> float:
        if len(features) != len(self.means):
            raise ValueError(f"Expected {len(self.means)} features, got {len(features)}")
        if any(not math.isfinite(float(x)) for x in features):
            raise ValueError("FrozenController features must contain only finite values")
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

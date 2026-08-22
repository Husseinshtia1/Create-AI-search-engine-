from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class GateThresholds:
    max_p95_search_latency_ms: float = 400.0
    max_avg_index_publish_ms: float = 750.0
    max_zero_result_rate: float = 0.60
    max_duplicate_waste_rate: float = 0.35
    max_segment_count: int = 8
    max_segment_bytes_per_document: float = 100_000.0
    min_search_samples: int = 50
    min_crawl_samples: int = 100


SCALE_STAGES = (1_000, 10_000, 100_000)


def evaluate_scale_gate(status: dict[str, Any], thresholds: GateThresholds | None = None) -> dict[str, Any]:
    """Evaluate whether observed operation supports moving to the next crawl stage.

    Thresholds are operational alpha guardrails, not scientific claims. A gate
    never passes on missing measurement volume; it returns INSUFFICIENT_DATA.
    """
    t = thresholds or GateThresholds()
    docs = int(status.get("documents", 0))
    repo_generation = int(status.get("repository_generation", 0))
    indexed_generation = int(status.get("indexed_generation", 0))
    segments = dict(status.get("segments", {}))
    telemetry = dict(status.get("telemetry", {}))

    reached = max((stage for stage in SCALE_STAGES if docs >= stage), default=0)
    next_stage = next((stage for stage in SCALE_STAGES if stage > docs), None)
    checks: dict[str, dict[str, Any]] = {}

    def check(name: str, value: float | int, limit: float | int, passed: bool) -> None:
        checks[name] = {"value": value, "limit": limit, "pass": bool(passed)}

    check("generation_lag", repo_generation - indexed_generation, 0, repo_generation == indexed_generation)
    check("segment_count", int(segments.get("count", 0)), t.max_segment_count, int(segments.get("count", 0)) <= t.max_segment_count)
    check(
        "segment_bytes_per_document",
        float(segments.get("bytes_per_document", 0.0)),
        t.max_segment_bytes_per_document,
        float(segments.get("bytes_per_document", 0.0)) <= t.max_segment_bytes_per_document,
    )

    searches = int(telemetry.get("searches", 0))
    crawls = int(telemetry.get("crawl_attempts", 0))
    if searches >= t.min_search_samples:
        check(
            "p95_search_latency_ms",
            float(telemetry.get("p95_search_latency_ms", 0.0)),
            t.max_p95_search_latency_ms,
            float(telemetry.get("p95_search_latency_ms", 0.0)) <= t.max_p95_search_latency_ms,
        )
        check(
            "zero_result_rate",
            float(telemetry.get("zero_result_rate", 0.0)),
            t.max_zero_result_rate,
            float(telemetry.get("zero_result_rate", 0.0)) <= t.max_zero_result_rate,
        )
    if crawls >= t.min_crawl_samples:
        check(
            "avg_index_publish_ms",
            float(telemetry.get("avg_index_publish_ms", 0.0)),
            t.max_avg_index_publish_ms,
            float(telemetry.get("avg_index_publish_ms", 0.0)) <= t.max_avg_index_publish_ms,
        )
        check(
            "duplicate_waste_rate",
            float(telemetry.get("duplicate_waste_rate", 0.0)),
            t.max_duplicate_waste_rate,
            float(telemetry.get("duplicate_waste_rate", 0.0)) <= t.max_duplicate_waste_rate,
        )

    required_samples = searches >= t.min_search_samples and crawls >= t.min_crawl_samples
    any_fail = any(not item["pass"] for item in checks.values())
    if any_fail:
        outcome = "FAIL"
    elif not required_samples:
        outcome = "INSUFFICIENT_DATA"
    else:
        outcome = "PASS"

    return {
        "outcome": outcome,
        "documents": docs,
        "reached_stage": reached,
        "next_stage": next_stage,
        "sample_requirements": {
            "searches": searches,
            "required_searches": t.min_search_samples,
            "crawls": crawls,
            "required_crawls": t.min_crawl_samples,
        },
        "thresholds": asdict(t),
        "checks": checks,
    }

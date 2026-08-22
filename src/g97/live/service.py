from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path

from .crawler import Crawler, CrawlConfig, CrawlResult
from .frontier import URLFrontier
from .index import LiveSearchIndex, SearchHit
from .repository import DocumentRepository
from .telemetry import TelemetryStore


class LiveSearchService:
    """End-to-end live search service: submit -> crawl -> index -> search."""

    def __init__(self, data_dir: str | Path, *, crawl_config: CrawlConfig | None = None):
        root = Path(data_dir)
        root.mkdir(parents=True, exist_ok=True)
        self.repository = DocumentRepository(root / "documents.sqlite3")
        self.frontier = URLFrontier(root / "frontier.sqlite3")
        self.telemetry = TelemetryStore(root / "telemetry.sqlite3")
        self.crawler = Crawler(self.repository, crawl_config)
        self.index = LiveSearchIndex(self.repository)

    def submit_url(self, url: str, *, depth: int = 0, discovered_from: str | None = None) -> bool:
        canonical = self.crawler.canonicalize_url(url)
        return self.frontier.add(canonical, depth=depth, discovered_from=discovered_from)

    def crawl_once(self, *, max_depth: int = 2, max_retries: int = 2) -> CrawlResult | None:
        item = self.frontier.claim_next()
        if item is None:
            return None

        result = self.crawler.crawl(item.url)
        terminal_success = result.status in {"INDEXED", "NON_HTML", "ROBOTS_DENIED"} or result.status.startswith("HTTP_4")
        if terminal_success:
            self.frontier.mark_done(item.url)
        else:
            self.frontier.mark_failed(item.url, retry=item.attempts < max_retries)

        if result.status == "INDEXED":
            if result.changed:
                self.index.refresh()
            if item.depth < max_depth:
                for link in result.discovered_links:
                    self.frontier.add(link, depth=item.depth + 1, discovered_from=result.final_url)

        self.telemetry.record_crawl(
            status=result.status,
            changed=result.changed,
            discovered_links=len(result.discovered_links),
        )
        return result

    def crawl(self, *, limit: int = 100, max_depth: int = 2, max_retries: int = 2) -> list[CrawlResult]:
        results: list[CrawlResult] = []
        for _ in range(max(0, int(limit))):
            result = self.crawl_once(max_depth=max_depth, max_retries=max_retries)
            if result is None:
                break
            results.append(result)
        return results

    def search(self, query: str, *, k: int = 10) -> list[SearchHit]:
        started = time.perf_counter()
        hits = self.index.search(query, k=k)
        latency_ms = (time.perf_counter() - started) * 1000.0
        self.telemetry.record_search(query, result_count=len(hits), latency_ms=latency_ms)
        return hits

    def status(self) -> dict[str, object]:
        return {
            "documents": self.repository.count(),
            "frontier": self.frontier.counts(),
            "telemetry": self.telemetry.summary(),
            "engine": "g97-live-alpha",
        }

    @staticmethod
    def hit_to_dict(hit: SearchHit) -> dict[str, object]:
        return asdict(hit)

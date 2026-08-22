from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path

from .crawler import Crawler, CrawlConfig, CrawlResult
from .dedup import NearDuplicateStore
from .frontier import URLFrontier
from .graph_store import LinkGraphStore
from .index import LiveSearchIndex, SearchHit
from .recrawl import RecrawlScheduler
from .repository import DocumentRepository
from .sitemap import SitemapDiscovery
from .telemetry import TelemetryStore


class LiveSearchService:
    """End-to-end live search service with scalable crawl/index state."""

    def __init__(self, data_dir: str | Path, *, crawl_config: CrawlConfig | None = None):
        root = Path(data_dir)
        root.mkdir(parents=True, exist_ok=True)
        self.root = root
        self.repository = DocumentRepository(root / "documents.sqlite3")
        self.frontier = URLFrontier(root / "frontier.sqlite3")
        self.telemetry = TelemetryStore(root / "telemetry.sqlite3")
        self.graph = LinkGraphStore(root / "graph.sqlite3")
        self.recrawl = RecrawlScheduler(root / "recrawl.sqlite3")
        self.dedup = NearDuplicateStore(root / "dedup.sqlite3")
        self.crawler = Crawler(self.repository, crawl_config, recrawl=self.recrawl)
        self.sitemaps = SitemapDiscovery(
            canonicalize=self.crawler.canonicalize_url,
            validate_public=self.crawler._assert_public_url,
            opener=self.crawler._opener,
            user_agent=self.crawler.config.user_agent,
            timeout_seconds=self.crawler.config.timeout_seconds,
        )
        self.index = LiveSearchIndex(self.repository, root / "segments", dedup=self.dedup)

    def submit_url(self, url: str, *, depth: int = 0, discovered_from: str | None = None) -> bool:
        canonical = self.crawler.canonicalize_url(url)
        return self.frontier.add(canonical, depth=depth, discovered_from=discovered_from)

    def submit_sitemap(self, seed_url: str, *, max_urls: int = 5000) -> int:
        urls = self.sitemaps.discover(seed_url)[: max(0, int(max_urls))]
        added = 0
        for url in urls:
            if self.frontier.add(url, depth=0, discovered_from="sitemap"):
                added += 1
        return added

    def enqueue_due_recrawls(self, *, limit: int = 100) -> int:
        added = 0
        for url in self.recrawl.due_urls(limit=limit):
            if self.frontier.requeue(url, depth=0, discovered_from="recrawl"):
                added += 1
        return added

    def crawl_once(self, *, max_depth: int = 2, max_retries: int = 2) -> CrawlResult | None:
        item = self.frontier.claim_next()
        if item is None:
            return None
        fetch_started = time.perf_counter()
        result = self.crawler.crawl(item.url)
        fetch_ms = (time.perf_counter() - fetch_started) * 1000.0
        terminal_success = (
            result.status in {"INDEXED", "NOT_MODIFIED", "NON_HTML", "ROBOTS_DENIED"}
            or result.status.startswith("HTTP_4")
        )
        if terminal_success:
            self.frontier.mark_done(item.url)
        else:
            self.frontier.mark_failed(item.url, retry=item.attempts < max_retries)

        duplicate = False
        publish_ms = 0.0
        if result.status == "INDEXED":
            if result.document is not None:
                decision = self.dedup.observe(
                    result.document.doc_id,
                    (result.document.title + "\n" + result.document.text).strip(),
                )
                duplicate = decision.duplicate_of is not None
            self.graph.observe(result.final_url, result.link_evidence)
            if result.changed:
                publish_started = time.perf_counter()
                self.index.publish_pending()
                self.index.compact(max_segments=8)
                publish_ms = (time.perf_counter() - publish_started) * 1000.0
            if item.depth < max_depth:
                for link in result.discovered_links:
                    self.frontier.add(link, depth=item.depth + 1, discovered_from=result.final_url)

        self.telemetry.record_crawl(
            status=result.status,
            changed=result.changed,
            discovered_links=len(result.discovered_links),
            fetch_ms=fetch_ms,
            index_publish_ms=publish_ms,
            duplicate=duplicate,
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

    def compact_index(self, *, max_segments: int = 8) -> bool:
        return self.index.compact(max_segments=max_segments)

    def status(self) -> dict[str, object]:
        segment_metas = self.index.segments.metas
        docs = self.repository.count()
        segment_bytes = self.index.segments.disk_bytes()
        return {
            "documents": docs,
            "repository_generation": self.repository.generation(),
            "indexed_generation": self.index.generation,
            "segments": {
                "count": len(segment_metas),
                "disk_bytes": segment_bytes,
                "bytes_per_document": (segment_bytes / docs) if docs else 0.0,
                "documents_across_segments": sum(meta.document_count for meta in segment_metas),
            },
            "graph": self.graph.counts(),
            "dedup": self.dedup.counts(),
            "recrawl": self.recrawl.counts(),
            "frontier": self.frontier.counts(),
            "telemetry": self.telemetry.summary(),
            "engine": "g97-live-alpha-scale",
        }

    @staticmethod
    def hit_to_dict(hit: SearchHit) -> dict[str, object]:
        return asdict(hit)

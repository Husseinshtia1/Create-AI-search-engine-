from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.request import Request

from g97.live.crawler import CrawlConfig, Crawler
from g97.live.frontier import URLFrontier
from g97.live.index import LiveSearchIndex
from g97.live.repository import DocumentRepository
from g97.live.telemetry import TelemetryStore


def test_repository_versions_and_exact_unchanged_fetch(tmp_path: Path) -> None:
    repo = DocumentRepository(tmp_path / "docs.sqlite3")
    first, changed1 = repo.upsert(url="https://example.com/", title="Alpha", text="quantum search", fetched_at="t1")
    same, changed2 = repo.upsert(url="https://example.com/", title="Alpha", text="quantum search", fetched_at="t2")
    updated, changed3 = repo.upsert(url="https://example.com/", title="Alpha", text="quantum search engine", fetched_at="t3")

    assert changed1 is True
    assert changed2 is False
    assert changed3 is True
    assert first.doc_id == same.doc_id == updated.doc_id
    assert same.version == 1
    assert updated.version == 2
    assert repo.version_count(updated.doc_id) == 2


def test_live_index_searches_repository(tmp_path: Path) -> None:
    repo = DocumentRepository(tmp_path / "docs.sqlite3")
    repo.upsert(url="https://a.example/", title="Quantum Lab", text="quantum sensing laboratory", fetched_at="t1")
    repo.upsert(url="https://b.example/", title="Cooking", text="bread and soup recipes", fetched_at="t1")
    index = LiveSearchIndex(repo)

    hits = index.search("quantum sensing", k=5)
    assert hits
    assert hits[0].url == "https://a.example/"
    assert "body_lexical_match" in hits[0].evidence


def test_frontier_is_durable_deduplicated_and_reclaims_expired_lease(tmp_path: Path) -> None:
    db = tmp_path / "frontier.sqlite3"
    frontier = URLFrontier(db)
    assert frontier.add("https://example.com/") is True
    assert frontier.add("https://example.com/") is False

    claimed = frontier.claim_next(lease_seconds=60)
    assert claimed is not None
    assert claimed.url == "https://example.com/"
    assert frontier.claim_next() is None

    with sqlite3.connect(db) as con:
        con.execute("UPDATE frontier SET lease_until=0 WHERE url=?", (claimed.url,))

    recovered = frontier.claim_next()
    assert recovered is not None
    assert recovered.url == claimed.url
    assert recovered.attempts == 2
    frontier.mark_done(recovered.url)

    reopened = URLFrontier(db)
    assert reopened.counts()["DONE"] == 1
    assert reopened.claim_next() is None


def test_crawler_blocks_private_targets_before_fetch(tmp_path: Path) -> None:
    repo = DocumentRepository(tmp_path / "docs.sqlite3")
    opened: list[str] = []

    def opener(req: Request, timeout: float):
        opened.append(req.full_url)
        return 200, req.full_url, {"content-type": "text/html"}, b"<html>bad</html>"

    crawler = Crawler(repo, opener=opener, resolver=lambda host: ["127.0.0.1"])
    result = crawler.crawl("http://internal.example/")
    assert result.status == "ERROR"
    assert opened == []
    assert "blocked" in (result.error or "")


def test_crawler_robots_parse_ingest_and_link_discovery(tmp_path: Path) -> None:
    repo = DocumentRepository(tmp_path / "docs.sqlite3")
    calls: list[str] = []

    def resolver(host: str):
        return ["93.184.216.34"]

    def opener(req: Request, timeout: float):
        calls.append(req.full_url)
        if req.full_url.endswith("/robots.txt"):
            return 200, req.full_url, {"content-type": "text/plain"}, b"User-agent: *\nAllow: /\n"
        body = b"""
        <html><head><title>G97 Quantum Search</title></head>
        <body><h1>Independent quantum search engine</h1>
        <script>secret noise</script>
        <a href='/next#fragment'>Next page</a>
        </body></html>
        """
        return 200, req.full_url, {"content-type": "text/html; charset=utf-8"}, body

    crawler = Crawler(
        repo,
        CrawlConfig(min_host_delay_seconds=0),
        opener=opener,
        resolver=resolver,
    )
    result = crawler.crawl("https://Example.COM/start#x")
    assert result.status == "INDEXED"
    assert result.changed is True
    assert result.document is not None
    assert result.document.url == "https://example.com/start"
    assert result.document.title == "G97 Quantum Search"
    assert "secret noise" not in result.document.text
    assert result.discovered_links == ("https://example.com/next",)
    assert calls[0] == "https://example.com/robots.txt"
    assert calls[1] == "https://example.com/start"

    index = LiveSearchIndex(repo)
    hits = index.search("quantum search")
    assert hits and hits[0].url == "https://example.com/start"


def test_robots_denial_prevents_page_fetch(tmp_path: Path) -> None:
    repo = DocumentRepository(tmp_path / "docs.sqlite3")
    calls: list[str] = []

    def opener(req: Request, timeout: float):
        calls.append(req.full_url)
        return 200, req.full_url, {"content-type": "text/plain"}, b"User-agent: *\nDisallow: /private\n"

    crawler = Crawler(
        repo,
        CrawlConfig(min_host_delay_seconds=0),
        opener=opener,
        resolver=lambda host: ["93.184.216.34"],
    )
    result = crawler.crawl("https://example.com/private/page")
    assert result.status == "ROBOTS_DENIED"
    assert calls == ["https://example.com/robots.txt"]
    assert repo.count() == 0


def test_telemetry_does_not_store_raw_queries(tmp_path: Path) -> None:
    db = tmp_path / "telemetry.sqlite3"
    telemetry = TelemetryStore(db)
    raw_query = "private experimental query"
    telemetry.record_search(raw_query, result_count=0, latency_ms=12.5)
    telemetry.record_crawl(status="INDEXED", changed=True, discovered_links=3)

    summary = telemetry.summary()
    assert summary["searches"] == 1
    assert summary["zero_result_searches"] == 1
    assert summary["crawl_attempts"] == 1
    assert summary["indexed_crawls"] == 1

    with sqlite3.connect(db) as con:
        columns = [row[1] for row in con.execute("PRAGMA table_info(search_events)")]
        row = con.execute("SELECT * FROM search_events").fetchone()
    assert "query" not in columns
    assert raw_query not in repr(row)

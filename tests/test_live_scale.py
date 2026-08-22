from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.request import Request

from g97.live.crawler import CrawlConfig, Crawler
from g97.live.dedup import NearDuplicateStore
from g97.live.frontier import URLFrontier
from g97.live.graph_store import LinkEvidence, LinkGraphStore
from g97.live.index import LiveSearchIndex
from g97.live.recrawl import RecrawlScheduler
from g97.live.repository import DocumentRepository
from g97.live.scale_gate import evaluate_scale_gate


def test_immutable_segments_publish_incrementally_and_compact(tmp_path: Path) -> None:
    repo = DocumentRepository(tmp_path / "docs.sqlite3")
    index = LiveSearchIndex(repo, tmp_path / "segments")

    repo.upsert(url="https://a.example/", title="Alpha", text="quantum alpha", fetched_at="t1")
    assert index.publish_pending() is True
    first_names = [m.name for m in index.segments.metas]
    assert len(first_names) == 1

    repo.upsert(url="https://b.example/", title="Beta", text="quantum beta", fetched_at="t2")
    assert index.publish_pending() is True
    assert len(index.segments.metas) == 2
    assert (tmp_path / "segments" / first_names[0]).exists()

    assert index.compact(max_segments=1) is True
    assert len(index.segments.metas) == 1
    hits = index.search("quantum beta", k=5)
    assert hits and hits[0].url == "https://b.example/"


def test_repository_change_log_collapses_latest_document_version(tmp_path: Path) -> None:
    repo = DocumentRepository(tmp_path / "docs.sqlite3")
    doc, _ = repo.upsert(url="https://a.example/", title="A", text="one", fetched_at="t1")
    generation_1 = repo.generation()
    repo.upsert(url="https://a.example/", title="A", text="two", fetched_at="t2")
    current, changed = repo.changes_after(generation_1)
    assert current == repo.generation()
    assert len(changed) == 1
    assert changed[0].doc_id == doc.doc_id
    assert changed[0].version == 2
    assert changed[0].text == "two"


def test_persistent_graph_keeps_anchor_evidence(tmp_path: Path) -> None:
    graph = LinkGraphStore(tmp_path / "graph.sqlite3")
    graph.observe(
        "https://source.example/",
        [
            LinkEvidence("https://target.example/", "Quantum Research Lab"),
            LinkEvidence("https://target.example/", "Quantum Research Lab"),
        ],
    )
    anchors = graph.inbound_anchors("https://target.example/")
    assert anchors == [("https://source.example/", "Quantum Research Lab")]
    assert graph.counts()["edges"] == 1
    assert graph.counts()["nonempty_anchors"] == 1


def test_near_duplicate_store_marks_high_similarity_copy(tmp_path: Path) -> None:
    store = NearDuplicateStore(tmp_path / "dedup.sqlite3", threshold=0.75)
    text = "quantum sensing laboratory independent search engine evidence retrieval systems " * 8
    first = store.observe(1, text)
    second = store.observe(2, text + " minor footer")
    assert first.duplicate_of is None
    assert second.duplicate_of == 1
    assert store.is_duplicate(2) is True
    assert store.counts()["duplicates"] == 1


def test_conditional_recrawl_sends_etag_and_handles_304(tmp_path: Path) -> None:
    repo = DocumentRepository(tmp_path / "docs.sqlite3")
    recrawl = RecrawlScheduler(tmp_path / "recrawl.sqlite3")
    requests: list[dict[str, str]] = []

    def opener(req: Request, timeout: float):
        headers = {k.lower(): v for k, v in req.header_items()}
        requests.append(headers)
        if req.full_url.endswith("/robots.txt"):
            return 200, req.full_url, {"content-type": "text/plain"}, b"User-agent: *\nAllow: /\n"
        if headers.get("if-none-match") == '"v1"':
            return 304, req.full_url, {"etag": '"v1"'}, b""
        return (
            200,
            req.full_url,
            {"content-type": "text/html", "etag": '"v1"', "last-modified": "Mon, 01 Jan 1996 00:00:00 GMT"},
            b"<html><title>Alpha</title><body>quantum search</body></html>",
        )

    crawler = Crawler(
        repo,
        CrawlConfig(min_host_delay_seconds=0),
        recrawl=recrawl,
        opener=opener,
        resolver=lambda host: ["93.184.216.34"],
    )
    first = crawler.crawl("https://example.com/page")
    second = crawler.crawl("https://example.com/page")
    assert first.status == "INDEXED"
    assert second.status == "NOT_MODIFIED"
    assert any(item.get("if-none-match") == '"v1"' for item in requests)


def test_completed_frontier_item_can_be_requeued_for_recrawl(tmp_path: Path) -> None:
    frontier = URLFrontier(tmp_path / "frontier.sqlite3")
    assert frontier.add("https://example.com/")
    item = frontier.claim_next()
    assert item is not None
    frontier.mark_done(item.url)
    assert frontier.requeue(item.url, discovered_from="recrawl") is True
    again = frontier.claim_next()
    assert again is not None and again.url == item.url
    assert again.discovered_from == "recrawl"


def test_scale_gate_requires_samples_and_catches_generation_lag() -> None:
    status = {
        "documents": 1000,
        "repository_generation": 1000,
        "indexed_generation": 1000,
        "segments": {"count": 2, "bytes_per_document": 2000.0},
        "telemetry": {
            "searches": 10,
            "crawl_attempts": 10,
            "p95_search_latency_ms": 20.0,
            "zero_result_rate": 0.1,
            "avg_index_publish_ms": 10.0,
            "duplicate_waste_rate": 0.1,
        },
    }
    gate = evaluate_scale_gate(status)
    assert gate["outcome"] == "INSUFFICIENT_DATA"

    status["telemetry"]["searches"] = 100
    status["telemetry"]["crawl_attempts"] = 1000
    assert evaluate_scale_gate(status)["outcome"] == "PASS"

    status["indexed_generation"] = 999
    failed = evaluate_scale_gate(status)
    assert failed["outcome"] == "FAIL"
    assert failed["checks"]["generation_lag"]["pass"] is False

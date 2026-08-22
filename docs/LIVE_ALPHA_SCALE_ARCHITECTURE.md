# G97 Live Alpha Scale Architecture

Status: implementation track for controlled live crawling and search.

## Boundary

The frozen G97 research track remains historically constrained to knowledge available by 31 December 1996. The Live Alpha scale/runtime layer may use modern implementation and security infrastructure. Operational components such as SQLite WAL, SHA-256 telemetry digests, systemd, TLS termination and near-duplicate hygiene do not become evidence for historical novelty or retrieval effectiveness claims.

## Data flow

```text
seed / sitemap / due recrawl
        |
        v
 durable frontier + leases
        |
        v
 robots/politeness + conditional HTTP
        |
        v
 HTML parse -----> persistent link/anchor graph
        |
        v
 document repository + version history + generation change log
        |
        +----> near-duplicate operational sketch
        |
        v
 immutable delta segment
        |
        +----> bounded candidate generation
        |
        v
 unified lexical rerank + snippets
        |
        v
 search API / browser UI
```

## Immutable segments

A changed document increments repository generation and appends a repository change record. The indexer publishes only generations newer than the last published segment. Segment files are immutable once referenced by the manifest. The manifest is replaced atomically. Compaction writes a new immutable segment containing only the latest version of each document and then removes unreferenced old segments.

Old versions are never allowed to leak into results: candidate generation first determines the latest document version represented across active segments and rejects candidates from older versions.

## Link and anchor graph

Observed source->target links are persisted independently from ranking. Anchor text is stored as external lexical evidence with first/last seen and observation count. The graph does not receive an unconditional authority boost. Any future use in ranking must pass a separate controlled policy/evaluation gate.

## Conditional recrawl

The crawler persists `ETag` and `Last-Modified` when available and sends `If-None-Match` / `If-Modified-Since` on revisit. HTTP 304 is treated as `NOT_MODIFIED` and does not create a new document version or index segment.

The initial adaptive schedule is deliberately conservative:

- changed page: revisit in ~1 day;
- unchanged page: exponential backoff 2 -> 4 -> 8 -> 16 -> 30 days;
- transient error: retry schedule starts at ~1 day.

These are operational defaults, not historical search claims, and may be tuned from system-load/freshness requirements without touching frozen benchmark protocols.

## Sitemap discovery

The scale runtime can discover `/sitemap.xml` and bounded nested same-host sitemap files. It has explicit limits on bytes, nested maps and enqueued URLs. Sitemap discovery only populates the frontier; normal robots/security/fetch policy still applies to page crawling.

## Near-duplicate suppression

The live runtime keeps a compact shingle sketch and marks highly similar copies. Duplicates remain auditable in the repository but are suppressed from result candidates. This layer is production hygiene and is explicitly outside the frozen historical ranking claim.

## Observability

The runtime reports at least:

- document count;
- repository vs indexed generation;
- active segment count;
- segment bytes and bytes/document;
- graph edges / sources / targets / non-empty anchors;
- tracked and due recrawls;
- observed near-duplicates and duplicate waste rate;
- crawl attempts and indexed crawls;
- crawl throughput over the last hour;
- average fetch latency;
- average index-publish latency (current TTQ proxy from changed fetch completion to searchable segment publication);
- average and p95 search latency;
- zero-result rate.

Raw queries and client IP addresses are not persisted by the current telemetry layer.

## Expansion protocol

Crawl expansion is staged:

```text
1,000 -> 10,000 -> 100,000 pages
```

`g97-live scale-gate` returns `PASS`, `FAIL` or `INSUFFICIENT_DATA`. The initial guardrails are committed before the live scale run and include:

- zero repository/index generation lag;
- no more than 8 active segments after automatic compaction;
- segment storage <= 100 KB/document at the measured stage;
- p95 search latency <= 400 ms after at least 50 measured searches;
- average index-publish latency <= 750 ms after at least 100 crawl events;
- zero-result rate <= 60% after the minimum search sample;
- duplicate-waste rate <= 35% after the minimum crawl sample.

These values are alpha operational guardrails, not universal performance claims. A failed gate stops expansion and requires diagnosis. Missing samples never count as a pass.

## Deployment topology v1

```text
Internet
  |
HTTPS reverse proxy
  |
127.0.0.1:8080 G97 search service
  |
/var/lib/g97
  |-- documents.sqlite3
  |-- frontier.sqlite3
  |-- graph.sqlite3
  |-- recrawl.sqlite3
  |-- dedup.sqlite3
  |-- telemetry.sqlite3
  `-- segments/

separate systemd crawler worker
```

The first DigitalOcean deployment should remain a controlled single-node alpha. The crawler and search server run as separate processes. The next infrastructure split is triggered by measured CPU, memory, disk or latency pressure rather than by a preselected page count alone.

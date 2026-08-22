# G97 Live Alpha Architecture

This document defines the production-side G97 Live Alpha path. It is intentionally separated from frozen research experiments.

## Boundary

`experiments/` and frozen validation artifacts remain scientific records. Live crawl data, user queries and production telemetry must never be fed back into an experiment that is still described as unseen/frozen validation.

## Data flow

```text
seed/submitted URL
      -> URL frontier
      -> robots/politeness gate
      -> HTTP fetch
      -> HTML parse + canonicalization
      -> content hash + repository version
      -> delta index refresh
      -> search API
```

The first implementation uses only the Python standard library plus the existing `g97` retrieval primitives. SQLite is used for durable metadata and document storage. The search index is rebuilt from searchable repository state after a changed document is committed; this is deliberately simple and deterministic for the first live alpha.

## Runtime invariants

1. Only `http` and `https` URLs are crawlable.
2. Robots exclusion is checked before a page fetch.
3. Per-host delays are enforced by the crawler.
4. Fetch size is bounded.
5. Redirects are bounded by the HTTP client defaults and the final URL is canonicalized.
6. Non-HTML responses are not indexed as HTML pages.
7. Exact content duplicates are detected by SHA-256.
8. A document has stable URL identity and version history.
9. Newly changed pages become queryable through the delta service after ingestion.
10. Search results expose an evidence trace; the current alpha uses lexical evidence only unless a later live action is explicitly enabled.
11. Production telemetry is operational/diagnostic data, not relevance ground truth.

## Initial operational target

The first milestone is correctness on a controlled crawl, not Internet scale. The same interfaces are intended to support later worker queues and sharded indexes without changing the research core.

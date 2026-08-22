# G97 Live Alpha Runbook

This runbook is for the production-side alpha only. It does not change frozen research protocols.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## Start with a controlled seed

```bash
g97-live --data-dir .g97-live submit https://example.org/
g97-live --data-dir .g97-live crawl --limit 25 --max-depth 1
g97-live --data-dir .g97-live status
```

## Search from the CLI

```bash
g97-live --data-dir .g97-live search "example query"
```

## Run the continuous crawler worker

Use a separate process from the HTTP server:

```bash
g97-live --data-dir .g97-live worker --max-depth 2 --max-retries 2
```

The frontier is durable. Claimed URLs receive a lease so a crashed worker does not strand them permanently.

## Run the browser/API service

Local-only default:

```bash
g97-live --data-dir .g97-live serve --host 127.0.0.1 --port 8080
```

Then open `http://127.0.0.1:8080/`.

Endpoints:

- `GET /` — minimal search UI.
- `GET /health` — liveness.
- `GET /status` — document/frontier/telemetry counters.
- `GET /search?q=...&k=10` — JSON search.
- `POST /submit` with JSON `{ "url": "https://..." }` — enqueue a URL.

## Public deployment boundary

Do not expose the built-in server directly to the public Internet as the final production edge. Put it behind a maintained TLS reverse proxy/load balancer and apply deployment-level request limits, observability and process supervision. The built-in 120 requests/minute per-client limiter is defense in depth, not a replacement for edge controls.

## Crawler safety behavior

- absolute `http`/`https` URLs only;
- DNS resolution must map entirely to globally routable IP addresses;
- loopback/private/link-local/reserved targets are rejected;
- redirect destinations are revalidated before follow;
- `robots.txt` is fetched and enforced; robots retrieval errors fail closed for that origin during the process;
- per-host delay defaults to one second;
- response body is bounded to 2 MB by default;
- only HTML/XHTML is indexed;
- scripts/styles/noscript/svg text is omitted from visible-text extraction;
- outgoing links are bounded per page.

## Storage

Runtime data are local SQLite files in `--data-dir`:

- `documents.sqlite3` — current documents plus version history;
- `frontier.sqlite3` — durable crawl frontier and worker leases;
- `telemetry.sqlite3` — aggregate operational events.

Raw search queries and client IP addresses are not persisted by the telemetry layer. Search queries are represented by SHA-256 digest plus coarse length/result/latency diagnostics.

## Current alpha limitations

The first live index is intentionally a correctness-first in-process sparse TF-IDF index. It refreshes after changed-document ingestion. This is suitable for a controlled alpha, but not the intended million-page architecture. The next indexing milestone is immutable delta segments + background main-index merge, followed by document shards and a query coordinator.

Likewise, the current live ranking exposes `body_lexical_match` evidence only. Experimental graph/anchor interventions are not silently enabled in production. They must cross their own validation/admission gate before being added as live actions.

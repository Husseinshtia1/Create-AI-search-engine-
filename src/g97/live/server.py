from __future__ import annotations

import html
import json
import threading
import time
import urllib.parse
from collections import defaultdict, deque
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .service import LiveSearchService


class LiveAPIHandler(BaseHTTPRequestHandler):
    service: LiveSearchService
    _rate_lock = threading.Lock()
    _requests: dict[str, deque[float]] = defaultdict(deque)
    requests_per_minute = 120

    def _allowed(self) -> bool:
        client = self.client_address[0]
        now = time.monotonic()
        cutoff = now - 60.0
        with self._rate_lock:
            bucket = self._requests[client]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.requests_per_minute:
                return False
            bucket.append(now)
            return True

    def _headers(self, content_type: str, length: int) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'")

    def _json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._headers("application/json; charset=utf-8", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, status: int, markup: str) -> None:
        body = markup.encode("utf-8")
        self.send_response(status)
        self._headers("text/html; charset=utf-8", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _rate_gate(self) -> bool:
        if self._allowed():
            return True
        self._json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "rate limit exceeded"})
        return False

    def do_GET(self) -> None:  # noqa: N802
        if not self._rate_gate():
            return
        parsed = urllib.parse.urlsplit(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/":
            query = (params.get("q") or [""])[0].strip()
            self._html(HTTPStatus.OK, self._render_search_page(query))
            return
        if parsed.path == "/health":
            self._json(HTTPStatus.OK, {"ok": True, "service": "g97-live-alpha"})
            return
        if parsed.path == "/status":
            self._json(HTTPStatus.OK, self.service.status())
            return
        if parsed.path == "/search":
            query = (params.get("q") or [""])[0].strip()
            if not query:
                self._json(HTTPStatus.BAD_REQUEST, {"error": "missing q"})
                return
            try:
                k = min(50, max(1, int((params.get("k") or ["10"])[0])))
            except ValueError:
                self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid k"})
                return
            hits = [asdict(hit) for hit in self.service.search(query, k=k)]
            self._json(HTTPStatus.OK, {"query": query, "count": len(hits), "results": hits})
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if not self._rate_gate():
            return
        if self.path != "/submit":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 16_384:
                raise ValueError("invalid request size")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            url = str(payload.get("url", "")).strip()
            if not url:
                raise ValueError("missing url")
            added = self.service.submit_url(url)
            self._json(HTTPStatus.ACCEPTED, {"accepted": True, "added": added, "url": url})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _render_search_page(self, query: str) -> str:
        escaped_query = html.escape(query, quote=True)
        results = self.service.search(query, k=10) if query else []
        cards = []
        for hit in results:
            title = html.escape(hit.title)
            url = html.escape(hit.url, quote=True)
            snippet = html.escape(hit.snippet)
            evidence = ", ".join(html.escape(v) for v in hit.evidence)
            cards.append(
                f"<article><a class='title' href='{url}' rel='nofollow noreferrer'>{title}</a>"
                f"<div class='url'>{url}</div><p>{snippet}</p>"
                f"<small>Evidence: {evidence}</small></article>"
            )
        result_html = "".join(cards) if cards else ("<p class='muted'>No results.</p>" if query else "")
        return f"""<!doctype html>
<html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>G97 Search</title><style>
body{{font-family:system-ui,sans-serif;max-width:850px;margin:8vh auto;padding:0 20px;line-height:1.45}}
h1{{font-size:2.2rem;margin-bottom:.4rem}}form{{display:flex;gap:8px;margin:24px 0}}
input{{flex:1;padding:13px 14px;font-size:1rem;border:1px solid #aaa;border-radius:9px}}button{{padding:0 18px;border-radius:9px;border:1px solid #777;background:#111;color:white}}
article{{padding:16px 0;border-bottom:1px solid #ddd}}.title{{font-size:1.2rem;font-weight:650}}.url{{font-size:.85rem;margin-top:3px;word-break:break-all}}small,.muted{{opacity:.65}}
</style></head><body><h1>G97 Search</h1><div class='muted'>Experimental independent search engine</div>
<form method='get' action='/'><input name='q' value='{escaped_query}' autofocus placeholder='Search the indexed web…'><button type='submit'>Search</button></form>
{result_html}</body></html>"""

    def log_message(self, format: str, *args: object) -> None:
        return


def run_server(data_dir: str | Path, *, host: str = "127.0.0.1", port: int = 8080) -> None:
    service = LiveSearchService(data_dir)
    handler = type("ConfiguredLiveAPIHandler", (LiveAPIHandler,), {"service": service})
    server = ThreadingHTTPServer((host, int(port)), handler)
    server.serve_forever()

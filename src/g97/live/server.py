from __future__ import annotations

import json
import urllib.parse
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .service import LiveSearchService


class LiveAPIHandler(BaseHTTPRequestHandler):
    service: LiveSearchService

    def _json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlsplit(self.path)
        params = urllib.parse.parse_qs(parsed.query)
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

    def log_message(self, format: str, *args: object) -> None:
        return


def run_server(data_dir: str | Path, *, host: str = "127.0.0.1", port: int = 8080) -> None:
    service = LiveSearchService(data_dir)
    handler = type("ConfiguredLiveAPIHandler", (LiveAPIHandler,), {"service": service})
    server = ThreadingHTTPServer((host, int(port)), handler)
    server.serve_forever()

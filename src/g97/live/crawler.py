from __future__ import annotations

import gzip
import ipaddress
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Callable, Iterable

from .repository import DocumentRepository, StoredDocument


USER_AGENT = "G97SearchBot/0.1 (+https://github.com/Husseinshtia1/Create-AI-search-engine-)"


@dataclass(frozen=True)
class CrawlConfig:
    user_agent: str = USER_AGENT
    timeout_seconds: float = 12.0
    max_bytes: int = 2_000_000
    min_host_delay_seconds: float = 1.0
    max_links_per_page: int = 500


@dataclass(frozen=True)
class CrawlResult:
    url: str
    final_url: str
    status: str
    changed: bool
    document: StoredDocument | None
    discovered_links: tuple[str, ...]
    error: str | None = None


class _HTMLTextParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self._skip_depth = 0
        self._in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(urllib.parse.urljoin(self.base_url, href))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        value = " ".join(data.split())
        if not value:
            return
        if self._in_title:
            self.title_parts.append(value)
        self.text_parts.append(value)


class Crawler:
    """Small, safety-bounded crawler suitable for a controlled Live Alpha."""

    def __init__(
        self,
        repository: DocumentRepository,
        config: CrawlConfig | None = None,
        *,
        opener: Callable[[urllib.request.Request, float], tuple[int, str, dict[str, str], bytes]] | None = None,
        resolver: Callable[[str], Iterable[str]] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.repository = repository
        self.config = config or CrawlConfig()
        self._resolver = resolver or self._resolve_host
        self._opener = opener or self._default_open
        self._sleeper = sleeper
        self._clock = clock
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._last_fetch: dict[str, float] = {}

    @staticmethod
    def canonicalize_url(url: str) -> str:
        parsed = urllib.parse.urlsplit((url or "").strip())
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("only absolute http/https URLs are crawlable")
        host = parsed.hostname.lower().rstrip(".")
        port = parsed.port
        default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
        netloc = host if port is None or default_port else f"{host}:{port}"
        path = parsed.path or "/"
        return urllib.parse.urlunsplit((scheme, netloc, path, parsed.query, ""))

    def _assert_public_url(self, url: str) -> str:
        canonical = self.canonicalize_url(url)
        host = urllib.parse.urlsplit(canonical).hostname
        assert host is not None
        addresses = list(self._resolver(host))
        if not addresses:
            raise ValueError("host did not resolve")
        for raw in addresses:
            ip = ipaddress.ip_address(raw)
            if not ip.is_global:
                raise ValueError("private, loopback, link-local or otherwise non-public targets are blocked")
        return canonical

    @staticmethod
    def _resolve_host(host: str) -> Iterable[str]:
        seen: set[str] = set()
        for info in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM):
            address = info[4][0]
            if address not in seen:
                seen.add(address)
                yield address

    def _respect_delay(self, host: str) -> None:
        last = self._last_fetch.get(host)
        if last is None:
            return
        remaining = self.config.min_host_delay_seconds - (self._clock() - last)
        if remaining > 0:
            self._sleeper(remaining)

    def _robots_for(self, url: str) -> urllib.robotparser.RobotFileParser:
        parsed = urllib.parse.urlsplit(url)
        origin = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
        cached = self._robots.get(origin)
        if cached is not None:
            return cached

        robots_url = origin + "/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        try:
            safe_robots = self._assert_public_url(robots_url)
            req = urllib.request.Request(safe_robots, headers={"User-Agent": self.config.user_agent})
            status, _final_url, _headers, body = self._opener(req, self.config.timeout_seconds)
            if 200 <= status < 300:
                text = body[: self.config.max_bytes].decode("utf-8", errors="replace")
                rp.parse(text.splitlines())
            else:
                rp.parse([])
        except Exception:
            # Conservative fail-closed behavior when robots policy cannot be retrieved.
            rp.parse(["User-agent: *", "Disallow: /"])
        self._robots[origin] = rp
        return rp

    def crawl(self, url: str) -> CrawlResult:
        try:
            canonical = self._assert_public_url(url)
            parsed = urllib.parse.urlsplit(canonical)
            host = parsed.hostname or ""
            robots = self._robots_for(canonical)
            if not robots.can_fetch(self.config.user_agent, canonical):
                return CrawlResult(canonical, canonical, "ROBOTS_DENIED", False, None, ())

            self._respect_delay(host)
            req = urllib.request.Request(
                canonical,
                headers={
                    "User-Agent": self.config.user_agent,
                    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
                    "Accept-Encoding": "gzip",
                },
            )
            status, final_url, headers, body = self._opener(req, self.config.timeout_seconds)
            self._last_fetch[host] = self._clock()

            if not (200 <= status < 300):
                return CrawlResult(canonical, final_url, f"HTTP_{status}", False, None, ())

            final_canonical = self._assert_public_url(final_url)
            content_type = headers.get("content-type", "").lower()
            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                return CrawlResult(canonical, final_canonical, "NON_HTML", False, None, ())

            if headers.get("content-encoding", "").lower() == "gzip":
                body = gzip.decompress(body)
            if len(body) > self.config.max_bytes:
                return CrawlResult(canonical, final_canonical, "TOO_LARGE", False, None, ())

            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=", 1)[1].split(";", 1)[0].strip() or "utf-8"
            html = body.decode(charset, errors="replace")
            parser = _HTMLTextParser(final_canonical)
            parser.feed(html)
            title = " ".join(parser.title_parts).strip()
            text = " ".join(parser.text_parts).strip()

            discovered: list[str] = []
            seen: set[str] = set()
            for raw_link in parser.links:
                if len(discovered) >= self.config.max_links_per_page:
                    break
                try:
                    link = self.canonicalize_url(raw_link)
                except ValueError:
                    continue
                if link not in seen:
                    seen.add(link)
                    discovered.append(link)

            fetched_at = datetime.now(timezone.utc).isoformat()
            document, changed = self.repository.upsert(
                url=final_canonical,
                title=title,
                text=text,
                fetched_at=fetched_at,
            )
            return CrawlResult(canonical, final_canonical, "INDEXED", changed, document, tuple(discovered))
        except Exception as exc:
            return CrawlResult(str(url), str(url), "ERROR", False, None, (), error=f"{type(exc).__name__}: {exc}")

    def _default_open(self, request: urllib.request.Request, timeout: float) -> tuple[int, str, dict[str, str], bytes]:
        crawler = self

        class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
                safe_url = crawler._assert_public_url(newurl)
                return super().redirect_request(req, fp, code, msg, headers, safe_url)

        opener = urllib.request.build_opener(SafeRedirectHandler())
        try:
            with opener.open(request, timeout=timeout) as response:
                raw = response.read(self.config.max_bytes + 1)
                headers = {k.lower(): v for k, v in response.headers.items()}
                return int(response.status), str(response.geturl()), headers, raw
        except urllib.error.HTTPError as exc:
            return int(exc.code), str(exc.geturl()), {k.lower(): v for k, v in exc.headers.items()}, b""

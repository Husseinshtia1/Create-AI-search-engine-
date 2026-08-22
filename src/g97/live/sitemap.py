from __future__ import annotations

import gzip
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class SitemapResult:
    sitemap_url: str
    urls: tuple[str, ...]
    nested_sitemaps: tuple[str, ...]


class SitemapDiscovery:
    """Bounded sitemap parser; network safety is delegated to the crawler validator/fetcher."""

    def __init__(
        self,
        *,
        canonicalize: Callable[[str], str],
        validate_public: Callable[[str], str],
        opener: Callable[[urllib.request.Request, float], tuple[int, str, dict[str, str], bytes]],
        user_agent: str,
        timeout_seconds: float = 12.0,
        max_bytes: int = 4_000_000,
        max_urls: int = 5000,
    ):
        self.canonicalize = canonicalize
        self.validate_public = validate_public
        self.opener = opener
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self.max_urls = max_urls

    def fetch(self, sitemap_url: str) -> SitemapResult:
        safe = self.validate_public(sitemap_url)
        req = urllib.request.Request(safe, headers={"User-Agent": self.user_agent, "Accept-Encoding": "gzip"})
        status, final_url, headers, body = self.opener(req, self.timeout_seconds)
        if not (200 <= status < 300):
            return SitemapResult(safe, (), ())
        if len(body) > self.max_bytes:
            return SitemapResult(safe, (), ())
        if headers.get("content-encoding", "").lower() == "gzip" or final_url.lower().endswith(".gz"):
            body = gzip.decompress(body)
            if len(body) > self.max_bytes:
                return SitemapResult(safe, (), ())
        root = ET.fromstring(body)
        root_name = root.tag.rsplit("}", 1)[-1].lower()
        locs = ["".join(node.itertext()).strip() for node in root.iter() if node.tag.rsplit("}", 1)[-1].lower() == "loc"]
        origin_host = (urllib.parse.urlsplit(final_url).hostname or "").lower()
        urls: list[str] = []
        nested: list[str] = []
        for raw in locs:
            if not raw:
                continue
            try:
                canonical = self.canonicalize(raw)
            except ValueError:
                continue
            if (urllib.parse.urlsplit(canonical).hostname or "").lower() != origin_host:
                continue
            if root_name == "sitemapindex":
                if len(nested) < 100:
                    nested.append(canonical)
            elif len(urls) < self.max_urls:
                urls.append(canonical)
        return SitemapResult(safe, tuple(dict.fromkeys(urls)), tuple(dict.fromkeys(nested)))

    def discover(self, seed_url: str) -> list[str]:
        parsed = urllib.parse.urlsplit(self.canonicalize(seed_url))
        origin = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
        root_map = origin + "/sitemap.xml"
        first = self.fetch(root_map)
        found = list(first.urls)
        for nested in first.nested_sitemaps[:20]:
            if len(found) >= self.max_urls:
                break
            child = self.fetch(nested)
            found.extend(child.urls[: self.max_urls - len(found)])
        return list(dict.fromkeys(found))[: self.max_urls]

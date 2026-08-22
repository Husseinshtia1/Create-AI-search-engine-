from __future__ import annotations
from urllib.parse import urlsplit, urlunsplit, urljoin
DEFAULT_PORTS = {"http":80, "https":443}

def canonicalize(url: str, base: str | None = None) -> str:
    if base: url = urljoin(base, url)
    p = urlsplit(url); scheme = (p.scheme or "http").lower(); host = (p.hostname or "").lower().rstrip(".")
    if host.startswith("www."): host = host[4:]
    if not host: return ""
    port = p.port; netloc = host if not port or DEFAULT_PORTS.get(scheme)==port else f"{host}:{port}"
    return urlunsplit((scheme, netloc, p.path or "/", p.query, ""))

def host_key(url: str) -> str:
    p = urlsplit(url if "://" in url else "http://" + url); h = (p.hostname or "").lower().rstrip(".")
    return h[4:] if h.startswith("www.") else h

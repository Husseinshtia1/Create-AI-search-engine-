# Curlie host canonicalization — FROZEN BEFORE GRAPH EXTRACTION

This appendix was committed after Figshare metadata integrity inspection but before downloading or parsing `html_content.json.gz`, before constructing any hyperlink graph, and before producing any retrieval metric.

Curlie nodes are homepage-level websites. For both published homepage URLs and extracted hyperlink destinations:

1. Resolve relative hyperlinks against the source homepage URL with RFC-style URL joining.
2. Accept only `http` and `https` destinations.
3. Canonical key = lowercase hostname after removing a trailing dot and one leading `www.`. Explicit port is ignored. Path, query, and fragment are ignored because the node identity is the homepage/site represented by the Curlie UID.
4. A selected UID is target-addressable only if its canonical host maps to exactly one selected UID.
5. If two or more selected UIDs map to the same canonical host, that host is ambiguous and all graph edges to that host are ignored. No arbitrary UID is selected.
6. Self-links are ignored.
7. Multiple links from one source UID to the same target UID are collapsed into one directed source-target relation, while all non-empty anchor strings for that source-target relation are retained as external-description text.

No category labels, class vectors, graph density, or retrieval outcome may affect canonicalization.
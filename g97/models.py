from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

@dataclass
class Document:
    doc_id: str
    url: str
    title: str = ""
    body: str = ""
    fetched_at: float = 0.0
    status: int = 200
    content_type: str = "text/html"
    outlinks: List[Tuple[str, str]] = field(default_factory=list)  # (url, anchor text)
    meta: Dict[str, str] = field(default_factory=dict)

@dataclass
class SearchHit:
    doc_id: str
    url: str
    score: float
    title: str
    snippet: str
    body_score: float = 0.0
    external_score: float = 0.0
    graph_score: float = 0.0
    intervention: str = "none"

@dataclass
class QueryState:
    query: str
    tokens: List[str]
    margin10: float = 0.0
    coherence10: float = 0.0
    anchor_top3_share: float = 0.0
    anchor_novel_ratio: float = 0.0
    body_top1_score: float = 0.0
    body_top10_mean_score: float = 0.0
    body_top10_score_cv: float = 0.0
    log_query_token_count: float = 0.0
    anchor_top1_score: float = 0.0
    anchor_nonempty_ratio: float = 0.0

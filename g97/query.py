from __future__ import annotations
import math
from statistics import mean
from .models import QueryState
from .text import normalize

def _cv(vals):
    if not vals:return 0.0
    m=mean(vals)
    if not m:return 0.0
    return math.sqrt(sum((x-m)**2 for x in vals)/len(vals))/m

def diagnose(query,body_top,anchor_top,coherence=0.0):
    bs=[s for _,s in body_top[:10]];ascores=[s for _,s in anchor_top[:10]];s1=bs[0] if bs else 0;s10=bs[min(9,len(bs)-1)] if bs else 0;margin=(s1-s10)/(s1+1e-12) if bs else 0
    asum=sum(ascores);a3=sum(ascores[:3]);b20={d for d,_ in body_top[:20]};nov=sum(1 for d,_ in anchor_top[:10] if d not in b20)/10.0
    return QueryState(query=query,tokens=normalize(query),margin10=margin,coherence10=coherence,anchor_top3_share=(a3/asum if asum else 0),anchor_novel_ratio=nov,body_top1_score=s1,body_top10_mean_score=(mean(bs) if bs else 0),body_top10_score_cv=_cv(bs),log_query_token_count=math.log1p(len(normalize(query))),anchor_top1_score=(ascores[0] if ascores else 0),anchor_nonempty_ratio=len(ascores)/10.0)

from __future__ import annotations
from collections import defaultdict

class LinkGraph:
    def __init__(self):self.out=defaultdict(set);self.inn=defaultdict(set)
    def add(self,a,b):
        if a!=b:self.out[a].add(b);self.inn[b].add(a)
    def build_from_docs(self,docs,url_to_id):
        self.out=defaultdict(set);self.inn=defaultdict(set)
        for d in docs:
            for u,_ in d.outlinks:
                b=url_to_id.get(u)
                if b:self.add(d.doc_id,b)
    def degree(self,d):return len(self.inn[d])
    def recursive_authority(self,eps=.08,iters=50):
        nodes=set(self.out)|set(self.inn)
        if not nodes:return {}
        a={d:1/len(nodes) for d in nodes}
        for _ in range(iters):
            nxt={d:eps/len(nodes) for d in nodes};dang=0.0
            for s in nodes:
                ns=self.out[s]
                if ns:
                    share=(1-eps)*a[s]/len(ns)
                    for d in ns:nxt[d]=nxt.get(d,0)+share
                else:dang+=(1-eps)*a[s]
            if dang:
                for d in nodes:nxt[d]+=dang/len(nodes)
            z=sum(nxt.values()) or 1;a={d:v/z for d,v in nxt.items()}
        m=max(a.values()) or 1;return {d:v/m for d,v in a.items()}
    def local_corroboration(self,seeds,candidate_scores,lam=.5):
        if not seeds:return dict(candidate_scores)
        mx=max((s for _,s in seeds),default=1) or 1;e=defaultdict(float)
        for s,score in seeds:
            conf=max(score,0)/mx
            for d in self.out[s]|self.inn[s]:
                if candidate_scores.get(d,0)>0:e[d]+=conf
        return {d:base*(1+lam*(e[d]/(1+e[d]) if e[d]>0 else 0)) for d,base in candidate_scores.items()}

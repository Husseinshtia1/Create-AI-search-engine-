from __future__ import annotations
import math
from collections import Counter,defaultdict
from .text import normalize

class ExternalDescriptionIndex:
    def __init__(self):self.target_tf=defaultdict(Counter);self.source_outdegree=Counter();self.N=0;self.df=Counter();self.postings=defaultdict(dict);self.norm={}
    def build(self,docs,url_to_id):
        self.N=len(docs);self.target_tf=defaultdict(Counter);self.source_outdegree=Counter()
        for d in docs:
            targets=[]
            for u,a in d.outlinks:
                tid=url_to_id.get(u)
                if tid and tid!=d.doc_id:targets.append((tid,a))
            self.source_outdegree[d.doc_id]=len({t for t,_ in targets});scar=1/(1+math.log(1+self.source_outdegree[d.doc_id])) if targets else 0
            for tid,a in targets:
                for t,c in Counter(normalize(a)).items():self.target_tf[tid][t]+=scar*c
        self.df=Counter()
        for c in self.target_tf.values():self.df.update(c.keys())
        self.postings=defaultdict(dict);self.norm={}
        for d,c in self.target_tf.items():
            s=0
            for t,f in c.items():idf=math.log((self.N+1)/(self.df[t]+1))+1;w=((1+math.log(f)) if f>1 else f)*idf;self.postings[t][d]=w;s+=w*w
            self.norm[d]=math.sqrt(s) or 1
    def search(self,query_tokens,query_weights,query_norm,k=10):
        acc=defaultdict(float)
        for t,wq in query_weights.items():
            for d,wd in self.postings.get(t,{}).items():acc[d]+=wq*wd
        return sorted([(d,dot/(query_norm*self.norm[d])) for d,dot in acc.items() if dot>0],key=lambda x:(-x[1],x[0]))[:k]

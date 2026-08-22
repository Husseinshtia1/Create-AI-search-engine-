from __future__ import annotations
import math
from collections import Counter
from .index import InvertedIndex
from .anchors import ExternalDescriptionIndex
from .graph import LinkGraph
from .text import normalize
from .query import diagnose
from .controller import InterventionController
from .models import SearchHit
from .snippets import snippet
class SearchEngine:
    def __init__(self,docs,controller=None,lexical='tfidf'):
        self.docs={d.doc_id:d for d in docs};self.lexical=lexical;self.index=InvertedIndex();self.index.build(self.docs.values());self.url_to_id={d.url:d.doc_id for d in docs};self.graph=LinkGraph();self.graph.build_from_docs(self.docs.values(),self.url_to_id);self.anchor=ExternalDescriptionIndex();self.anchor.build(self.docs.values(),self.url_to_id);self.controller=controller or InterventionController(None)
    def _query_vector(self,q):
        qt=Counter(normalize(q));qv={};s=0
        for t,f in qt.items():idf=math.log((self.index.N+1)/(self.index.df.get(t,0)+1))+1;w=(1+math.log(f))*idf;qv[t]=w;s+=w*w
        return qt,qv,math.sqrt(s) or 1
    def search(self,q,k=10,use_graph=False):
        body=getattr(self.index,self.lexical)(q,k=30);qt,qv,qn=self._query_vector(q);anch=self.anchor.search(qt,qv,qn,k=10);state=diagnose(q,body,anch,coherence=0.0);action,ctrl_score=self.controller.decide(state);selected=[d for d,_ in body][:30];intervention='none'
        if action=='external_rescue':
            selected=[];seen=set()
            for d,_ in body[:20]:
                if d not in seen:selected.append(d);seen.add(d)
            for d,_ in anch[:10]:
                if d not in seen and len(selected)<30:selected.append(d);seen.add(d)
            for d,_ in body[20:]:
                if len(selected)>=30:break
                if d not in seen:selected.append(d);seen.add(d)
            intervention='external_rescue'
        score=dict(body)
        if use_graph:score=self.graph.local_corroboration(body[:10],score);selected=sorted(selected,key=lambda d:(-score.get(d,0),d))
        ar=dict(anch);hits=[]
        for d in selected[:k]:
            doc=self.docs[d];hits.append(SearchHit(d,doc.url,score.get(d,0),doc.title or doc.url,snippet(doc.body,q),score.get(d,0),ar.get(d,0),0.0,intervention))
        return hits,state,ctrl_score

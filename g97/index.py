from __future__ import annotations
import math,pickle
from collections import Counter,defaultdict
from pathlib import Path
from .models import Document
from .text import normalize

class InvertedIndex:
    def __init__(self):self.docs={};self.tf={};self.df=Counter();self.length={};self.postings=defaultdict(dict);self.avgdl=0.0
    def add(self,doc:Document,field_boost_title:float=0.0):
        toks=normalize(doc.body)
        if field_boost_title:toks+=normalize(doc.title)*max(0,int(field_boost_title))
        c=Counter(toks);self.docs[doc.doc_id]=doc;self.tf[doc.doc_id]=c;self.length[doc.doc_id]=sum(c.values())
        for t,f in c.items():self.postings[t][doc.doc_id]=f
        self._recompute_df()
    def build(self,docs):
        self.docs={};self.tf={};self.df=Counter();self.length={};self.postings=defaultdict(dict)
        for d in docs:
            c=Counter(normalize(d.body));self.docs[d.doc_id]=d;self.tf[d.doc_id]=c;self.length[d.doc_id]=sum(c.values())
            for t,f in c.items():self.postings[t][d.doc_id]=f
        self._recompute_df()
    def _recompute_df(self):self.df=Counter({t:len(p) for t,p in self.postings.items()});self.avgdl=sum(self.length.values())/max(1,len(self.length))
    @property
    def N(self):return len(self.docs)
    def tfidf(self,query:str,k:int=30):
        qt=Counter(normalize(query));qv={};qn=0.0
        for t,f in qt.items():
            idf=math.log((self.N+1)/(self.df.get(t,0)+1))+1.0;w=(1+math.log(f))*idf;qv[t]=w;qn+=w*w
        qn=math.sqrt(qn) or 1.0;scores=defaultdict(float);dnorm=defaultdict(float);touched=set()
        for t,qw in qv.items():
            idf=math.log((self.N+1)/(self.df.get(t,0)+1))+1.0
            for d,f in self.postings.get(t,{}).items():dw=(1+math.log(f))*idf;scores[d]+=qw*dw;touched.add(d)
        for d in touched:
            s=0.0
            for t,f in self.tf[d].items():idf=math.log((self.N+1)/(self.df.get(t,0)+1))+1.0;w=(1+math.log(f))*idf;s+=w*w
            dnorm[d]=math.sqrt(s) or 1.0
        return sorted([(d,s/(qn*dnorm[d])) for d,s in scores.items() if s>0],key=lambda x:(-x[1],x[0]))[:k]
    def c96(self,query:str,k:int=30,k1:float=1.2,b:float=.75):
        scores=defaultdict(float)
        for t in normalize(query):
            df=self.df.get(t,0)
            if not df:continue
            idf=math.log((self.N-df+0.5)/(df+0.5))
            for d,tf in self.postings[t].items():
                K=k1*((1-b)+b*(self.length[d]/max(self.avgdl,1e-12)));scores[d]+=idf*((k1+1)*tf)/(K+tf)
        return sorted(scores.items(),key=lambda x:(-x[1],x[0]))[:k]
    def save(self,path:str):Path(path).parent.mkdir(parents=True,exist_ok=True);pickle.dump(self,open(path,'wb'))
    @staticmethod
    def load(path:str):return pickle.load(open(path,'rb'))

class DeltaIndex:
    def __init__(self,main:InvertedIndex|None=None):self.main=main or InvertedIndex();self.delta=InvertedIndex()
    def add(self,doc:Document):self.delta.add(doc)
    def merge(self):
        ded={d.doc_id:d for d in list(self.main.docs.values())+list(self.delta.docs.values())};self.main.build(ded.values());self.delta=InvertedIndex()
    def search(self,q,method='tfidf',k=30):
        fn=lambda idx:getattr(idx,method)(q,k=k);merged={}
        for d,s in fn(self.main)+fn(self.delta):merged[d]=max(merged.get(d,float('-inf')),s)
        return sorted(merged.items(),key=lambda x:(-x[1],x[0]))[:k]

#!/usr/bin/env python3
"""Frozen G97 CISI external replication. No qrels enter scoring."""
import argparse, collections, math, random, re
from nltk.stem import PorterStemmer
PS=PorterStemmer(); TOK=re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?")
def stem(x): return PS.stem(x.lower())
def toks(s,stop): return [stem(x) for x in TOK.findall(s or '') if stem(x) not in stop]
def load_stop(path): return {stem(x.strip()) for x in open(path,errors='replace') if x.strip() and not x.startswith('/*')}
def parse_smart(path):
    docs={}; cur=None; field=None; f=collections.defaultdict(list)
    def flush():
        nonlocal cur,f
        if cur is None:return
        x=[]
        for ln in f.get('X',[]):
            p=ln.split()
            if len(p)>=3:
                try:nbr,w,owner=map(int,p[:3])
                except:continue
                x.append((nbr,w,owner))
        docs[cur]={'title':' '.join(f.get('T',[])),'body':' '.join(f.get('W',[])),'x':x};f=collections.defaultdict(list)
    for raw in open(path,encoding='utf-8',errors='replace'):
        line=raw.rstrip('\r\n')
        if line.startswith('.I '):flush();cur=int(line.split()[1]);field=None
        elif len(line)==2 and line.startswith('.') and line[1].isalpha():field=line[1]
        elif field:f[field].append(line)
    flush();return docs
def parse_queries(path):
    raw=parse_smart(path);return {qid:(d['title']+' '+d['body']).strip() for qid,d in raw.items()}
def parse_qrels(path):
    q=collections.defaultdict(dict)
    for ln in open(path,errors='replace'):
        p=ln.split()
        if len(p)>=2:q[int(p[0])][int(p[1])]=1
    return q
def index(docs,stop):
    tf={};dl={};df=collections.Counter()
    for d,v in docs.items():
        c=collections.Counter(toks(v['title']+' '+v['body'],stop));tf[d]=c;dl[d]=sum(c.values());df.update(c.keys())
    return tf,dl,df,sum(dl.values())/len(dl)
def bm25(q,tf,dl,df,av,stop,k1=1.2,b=.75):
    qt=toks(q,stop);N=len(tf);out={}
    for d,c in tf.items():
        K=k1*((1-b)+b*dl[d]/max(av,1e-12));s=0.0
        for t in qt:
            n=df.get(t,0)
            if not n:continue
            idf=math.log((N-n+.5)/(n+.5));f=c.get(t,0)
            if f:s+=idf*((k1+1)*f)/(K+f)
        if s>0:out[d]=s
    return out
def build_coupling(docs):
    g=collections.defaultdict(dict)
    for owner,v in docs.items():
        for nbr,w,rowowner in v['x']:
            if rowowner==owner and nbr in docs and nbr!=owner and w>0:
                g[owner][nbr]=max(g[owner].get(nbr,0),w)
    # integrity-preserving symmetrization by max; observed CISI matrix is reciprocal.
    for a in list(g):
        for b,w in list(g[a].items()):
            g[b][a]=max(g[b].get(a,0),w)
    return g
def norm(d):
    m=max(d.values()) if d else 0;return {k:(v/m if m else 0) for k,v in d.items()}
def weighted_degree(nodes,g): return norm({d:sum(g.get(d,{}).values()) for d in nodes})
def recursive(nodes,g,eps=.08,iters=50):
    nodes=list(nodes);N=len(nodes);a={d:1/N for d in nodes}
    for _ in range(iters):
        z={d:eps/N for d in nodes}
        for s in nodes:
            ns=g.get(s,{});tot=sum(ns.values())
            if tot:
                for t,w in ns.items():z[t]+=(1-eps)*a[s]*w/tot
            else:
                x=(1-eps)*a[s]/N
                for t in nodes:z[t]+=x
        sm=sum(z.values());a={d:v/sm for d,v in z.items()}
    return norm(a)
def rank(sc,k=1000):return [d for d,_ in sorted(sc.items(),key=lambda x:(-x[1],x[0]))[:k]]
def rerank(base,feat,lam=.5):return {d:s*(1+lam*feat.get(d,0)) for d,s in base.items()}
def local(base,seeds,g):
    if not base:return {}
    mx=max(base.values());raw=collections.Counter()
    for s in seeds:
        conf=base.get(s,0)/mx
        for d,w in g.get(s,{}).items():
            if d!=s and d in base:raw[d]+=conf*w
    return {d:v/(1+v) for d,v in raw.items()}
def ap(r,rel):
    h=0;s=0
    for i,d in enumerate(r,1):
        if d in rel:h+=1;s+=h/i
    return s/len(rel) if rel else None
def pat(r,rel,k):return sum(d in rel for d in r[:k])/k
def rr(r,rel):
    for i,d in enumerate(r,1):
        if d in rel:return 1/i
    return 0
def ndcg(r,rel,k):
    x=sum((d in rel)/math.log2(i+2) for i,d in enumerate(r[:k]));z=sum(1/math.log2(i+2) for i in range(min(k,len(rel))))
    return x/z if z else 0
def evaluate(run,qrels):
    pq={}
    for q,rel in qrels.items():
        if q not in run:continue
        r=run[q];pq[q]={'AP':ap(r,rel),'P10':pat(r,rel,10),'P20':pat(r,rel,20),'nDCG10':ndcg(r,rel,10),'MRR':rr(r,rel)}
    return {m:sum(v[m] for v in pq.values())/len(pq) for m in ['AP','P10','P20','nDCG10','MRR']},pq
def boot(a,b,n=10000,seed=1996):
    qs=sorted(set(a)&set(b));ds=[b[q]['AP']-a[q]['AP'] for q in qs];rng=random.Random(seed);bs=[]
    for _ in range(n):bs.append(sum(ds[rng.randrange(len(ds))] for __ in ds)/len(ds))
    bs.sort();return {'delta':sum(ds)/len(ds),'lo':bs[int(.025*(n-1))],'hi':bs[int(.975*(n-1))],'wins':sum(x>1e-15 for x in ds),'losses':sum(x<-1e-15 for x in ds),'ties':sum(abs(x)<=1e-15 for x in ds)}
def main():
    p=argparse.ArgumentParser();p.add_argument('--docs',required=True);p.add_argument('--queries',required=True);p.add_argument('--qrels',required=True);p.add_argument('--stop',required=True);p.add_argument('--out',default='results.tsv');a=p.parse_args()
    docs=parse_smart(a.docs);queries=parse_queries(a.queries);stop=load_stop(a.stop);tf,dl,df,av=index(docs,stop);g=build_coupling(docs);deg=weighted_degree(docs,g);auth=recursive(docs,g)
    names=['A0_C96','A1_GLOBAL_WEIGHTED_DEGREE','A2_GLOBAL_RECURSIVE_COUPLING','A4_LOCAL_WEIGHTED_COUPLING'];runs={n:{} for n in names}
    # Frozen CACM choices: k1=1.2,b=.75,Top10,lambda=.50.
    for qid,text in queries.items():
        base=bm25(text,tf,dl,df,av,stop);seeds=rank(base,10);loc=local(base,seeds,g)
        S={'A0_C96':base,'A1_GLOBAL_WEIGHTED_DEGREE':rerank(base,deg,.50),'A2_GLOBAL_RECURSIVE_COUPLING':rerank(base,auth,.50),'A4_LOCAL_WEIGHTED_COUPLING':rerank(base,loc,.50)}
        for n,s in S.items():runs[n][qid]=rank(s)
    # ANTI-LEAKAGE: qrels loaded only after every ranking is complete.
    qrels=parse_qrels(a.qrels);res={};pq={}
    for n in names:res[n],pq[n]=evaluate(runs[n],qrels)
    with open(a.out,'w') as f:
        f.write('variant\tMAP\tP@10\tP@20\tnDCG@10\tMRR\tAP_delta\tCI95_low\tCI95_high\twins\tlosses\tties\n')
        for n in names:
            s=boot(pq['A0_C96'],pq[n]) if n!='A0_C96' else {'delta':0,'lo':0,'hi':0,'wins':0,'losses':0,'ties':0};r=res[n]
            f.write(f"{n}\t{r['AP']:.6f}\t{r['P10']:.6f}\t{r['P20']:.6f}\t{r['nDCG10']:.6f}\t{r['MRR']:.6f}\t{s['delta']:.6f}\t{s['lo']:.6f}\t{s['hi']:.6f}\t{s['wins']}\t{s['losses']}\t{s['ties']}\n")
    print('documents',len(docs),'queries',len(queries),'qrels_queries',len(qrels),'avgdl',av)
    print('coupling_edges',sum(len(v) for v in g.values())//2,'weighted_mass',sum(sum(v.values()) for v in g.values())/2)
    print(open(a.out).read())
if __name__=='__main__':main()

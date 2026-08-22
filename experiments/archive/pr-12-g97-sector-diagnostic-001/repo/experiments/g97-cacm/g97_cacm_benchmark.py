#!/usr/bin/env python3
"""G97 CACM frozen A0-A6 benchmark. Historical cutoff: 31 Dec 1996."""
import argparse, collections, math, random, re
try:
    from nltk.stem import PorterStemmer
    _PORTER=PorterStemmer()
except Exception as e:
    raise RuntimeError("NLTK PorterStemmer required") from e
TOKEN_RE=re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?")
def stem(x): return _PORTER.stem(x)
def tokenize(s,stop=None):
    xs=[stem(x.lower()) for x in TOKEN_RE.findall(s or "")]
    return [x for x in xs if not stop or x not in stop]
def parse_cacm(path):
    docs={}; cur=None; field=None; fields=collections.defaultdict(list)
    def flush():
        nonlocal cur,fields
        if cur is None:return
        x=[]
        for ln in fields.get('X',[]):
            p=ln.split()
            if len(p)>=3:
                try:nbr,typ,owner=map(int,p[:3])
                except:continue
                x.append((nbr,typ,owner))
        docs[cur]={'title':' '.join(fields.get('T',[])),'body':' '.join(fields.get('W',[])),'keywords':' '.join(fields.get('K',[])),'x':x}
        fields=collections.defaultdict(list)
    for raw in open(path,encoding='utf-8',errors='replace'):
        line=raw.rstrip('\n')
        if line.startswith('.I '): flush(); cur=int(line.split()[1]); field=None
        elif len(line)==2 and line.startswith('.') and line[1].isalpha(): field=line[1]
        elif field: fields[field].append(line)
    flush(); return docs
def parse_title_queries(path):
    q={}
    for line in open(path,encoding='utf-8',errors='replace'):
        line=line.strip(); m=re.match(r'^(\d+)\s+(.*)$',line)
        if m:q[int(m.group(1))]=m.group(2)
    return q
def parse_qrels(path):
    out=collections.defaultdict(dict)
    for line in open(path,encoding='utf-8',errors='replace'):
        p=line.split()
        if len(p)>=4:
            qid=int(p[0]);did=int(p[2]);rel=int(float(p[3]));
            if rel>0:out[qid][did]=rel
        elif len(p)>=2:out[int(p[0])][int(p[1])]=1
    return out
def load_stop(path):
    if not path:return set()
    return {stem(x.strip().lower()) for x in open(path,encoding='utf-8',errors='replace') if x.strip() and not x.strip().startswith('/*')}
def build_index(docs,stop):
    tf={};dl={};df=collections.Counter()
    for did,d in docs.items():
        c=collections.Counter(tokenize(d['title']+' '+d['body']+' '+d['keywords'],stop));tf[did]=c;dl[did]=sum(c.values());df.update(c.keys())
    return tf,dl,df,sum(dl.values())/len(dl)
def bm25_scores(query,tf,dl,df,avgdl,stop,k1=1.2,b=.75):
    qt=tokenize(query,stop);N=len(tf);scores={}
    for did,c in tf.items():
        K=k1*((1-b)+b*dl[did]/max(avgdl,1e-12));s=0.0
        for t in qt:
            n=df.get(t,0)
            if not n:continue
            idf=math.log((N-n+0.5)/(n+0.5));f=c.get(t,0)
            if f:s+=idf*((k1+1)*f)/(K+f)
        if s>0:scores[did]=s
    return scores
def build_graphs(docs):
    nodes=set(docs);ch4=collections.defaultdict(collections.Counter);ch5=collections.defaultdict(set);ch6=collections.defaultdict(collections.Counter)
    for owner,d in docs.items():
        seen=set()
        for nbr,typ,row_owner in d['x']:
            if row_owner!=owner or nbr not in nodes or nbr==owner:continue
            if typ==4:ch4[owner][nbr]+=1
            elif typ==5:seen.add(nbr)
            elif typ==6:ch6[owner][nbr]+=1
        ch5[owner]|=seen
    def symw(src):
        out=collections.defaultdict(collections.Counter)
        for a,ns in src.items():
            for b,w in ns.items():out[a][b]=max(out[a][b],w);out[b][a]=max(out[b][a],w)
        return out
    ch4=symw(ch4);ch6=symw(ch6);adj=collections.defaultdict(set)
    for a,ns in ch5.items():
        for b in ns:adj[a].add(b);adj[b].add(a)
    return ch4,adj,ch6
def norm(d):
    m=max(d.values()) if d else 0;return {k:(v/m if m else 0) for k,v in d.items()}
def recursive_authority(nodes,adj,eps=.08,iters=50):
    nodes=list(nodes);n=len(nodes);a={d:1/n for d in nodes}
    for _ in range(iters):
        z={d:eps/n for d in nodes}
        for s in nodes:
            outs=adj.get(s,set())
            if outs:
                x=(1-eps)*a[s]/len(outs)
                for t in outs:z[t]+=x
            else:
                x=(1-eps)*a[s]/n
                for t in nodes:z[t]+=x
        tot=sum(z.values());a={d:v/tot for d,v in z.items()}
    return norm(a)
def degree(nodes,adj):return norm({d:len(adj.get(d,set())) for d in nodes})
def rerank(base,feat,lam=.5):return {d:s*(1+lam*feat.get(d,0)) for d,s in base.items()}
def local_channel(base,seeds,relation):
    if not base:return {},{}
    mx=max(base.values());raw=collections.Counter();witness=collections.Counter()
    for s in seeds:
        conf=base.get(s,0)/mx;nbrs=relation.get(s,{})
        items=nbrs.items() if hasattr(nbrs,'items') else ((d,1) for d in nbrs)
        for d,w in items:
            if d!=s and d in base:raw[d]+=conf*float(w);witness[d]+=1
    return {d:v/(1+v) for d,v in raw.items()},witness
def rank(scores,k=1000):return [d for d,_ in sorted(scores.items(),key=lambda x:(-x[1],x[0]))[:k]]
def ap(r,rel):
    if not rel:return None
    h=0;s=0
    for i,d in enumerate(r,1):
        if d in rel:h+=1;s+=h/i
    return s/len(rel)
def pat(r,rel,k):return sum(d in rel for d in r[:k])/k
def rr(r,rel):
    for i,d in enumerate(r,1):
        if d in rel:return 1/i
    return 0
def ndcg(r,rel,k):
    dcg=sum((d in rel)/math.log2(i+2) for i,d in enumerate(r[:k]));ideal=sum(1/math.log2(i+2) for i in range(min(k,len(rel))))
    return dcg/ideal if ideal else 0
def evaluate(run,qrels):
    pq={}
    for qid,rel in qrels.items():
        if qid not in run:continue
        r=run[qid];pq[qid]={'AP':ap(r,rel),'P10':pat(r,rel,10),'P20':pat(r,rel,20),'nDCG10':ndcg(r,rel,10),'MRR':rr(r,rel)}
    avg={m:sum(v[m] for v in pq.values())/len(pq) for m in ['AP','P10','P20','nDCG10','MRR']};return avg,pq
def bootstrap(a,b,n=10000,seed=1996):
    qs=sorted(set(a)&set(b));ds=[b[q]['AP']-a[q]['AP'] for q in qs];rng=random.Random(seed);bs=[]
    for _ in range(n):bs.append(sum(ds[rng.randrange(len(ds))] for __ in ds)/len(ds))
    bs.sort();return {'mean_delta':sum(ds)/len(ds),'lo':bs[int(.025*(n-1))],'hi':bs[int(.975*(n-1))],'wins':sum(x>1e-15 for x in ds),'losses':sum(x<-1e-15 for x in ds),'ties':sum(abs(x)<=1e-15 for x in ds)}
def main():
    p=argparse.ArgumentParser();p.add_argument('--docs',required=True);p.add_argument('--queries',required=True);p.add_argument('--qrels',required=True);p.add_argument('--stop');p.add_argument('--out',default='results.tsv');a=p.parse_args()
    docs=parse_cacm(a.docs);queries=parse_title_queries(a.queries);stop=load_stop(a.stop);tf,dl,df,avgdl=build_index(docs,stop);ch4,adj,ch6=build_graphs(docs);deg=degree(docs,adj);auth=recursive_authority(docs,adj)
    names=['A0_C96','A1_RAW_DEGREE','A2_RECURSIVE_AUTH','A3_LOCAL_LINK','A4_LOCAL_COUPLING','A5_LOCAL_COCITATION','A6_CONTEXTGRAPH'];runs={n:{} for n in names}
    for qid,q in queries.items():
        base=bm25_scores(q,tf,dl,df,avgdl,stop);seeds=rank(base,10);g3,_=local_channel(base,seeds,adj);g4,_=local_channel(base,seeds,ch4);g5,_=local_channel(base,seeds,ch6);keys=set(g3)|set(g4)|set(g5);g6={d:(g3.get(d,0)+g4.get(d,0)+g5.get(d,0))/3 for d in keys}
        S={'A0_C96':base,'A1_RAW_DEGREE':rerank(base,deg),'A2_RECURSIVE_AUTH':rerank(base,auth),'A3_LOCAL_LINK':rerank(base,g3),'A4_LOCAL_COUPLING':rerank(base,g4),'A5_LOCAL_COCITATION':rerank(base,g5),'A6_CONTEXTGRAPH':rerank(base,g6)}
        for n,s in S.items():runs[n][qid]=rank(s)
    qrels=parse_qrels(a.qrels) # anti-leakage: after all runs exist
    res={};pq={}
    for n in names:res[n],pq[n]=evaluate(runs[n],qrels)
    with open(a.out,'w') as f:
        f.write('variant\tMAP\tP@10\tP@20\tnDCG@10\tMRR\tAP_delta\tCI95_low\tCI95_high\twins\tlosses\tties\n')
        for n in names:
            s=bootstrap(pq['A0_C96'],pq[n]) if n!='A0_C96' else {'mean_delta':0,'lo':0,'hi':0,'wins':0,'losses':0,'ties':0};r=res[n]
            f.write(f"{n}\t{r['AP']:.6f}\t{r['P10']:.6f}\t{r['P20']:.6f}\t{r['nDCG10']:.6f}\t{r['MRR']:.6f}\t{s['mean_delta']:.6f}\t{s['lo']:.6f}\t{s['hi']:.6f}\t{s['wins']}\t{s['losses']}\t{s['ties']}\n")
    print('documents',len(docs),'queries',len(queries),'qrels_queries',len(qrels),'avgdl',avgdl)
    print('relations',sum(len(v) for v in adj.values())//2,sum(len(v) for v in ch4.values())//2,sum(len(v) for v in ch6.values())//2)
    print(open(a.out).read())
if __name__=='__main__':main()

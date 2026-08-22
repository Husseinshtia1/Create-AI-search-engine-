#!/usr/bin/env python3
import argparse, math, re, collections, xml.etree.ElementTree as ET
from nltk.stem import PorterStemmer
P=PorterStemmer(); RX=re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?")
def tok(s): return [P.stem(x.lower()) for x in RX.findall(s or '')]
def parse_docs(p):
    raw=open(p,encoding='utf-8',errors='replace').read()
    raw=re.sub(r'^\s*<\?xml[^>]*\?>','',raw,count=1)
    root=ET.fromstring('<root>'+raw+'</root>'); out={}
    for d in root.findall('.//doc'):
        did=int((d.findtext('docno') or '0').strip()); title=d.findtext('title') or ''; text=d.findtext('text') or ''
        out[did]=title+' '+text
    return out
def parse_q(p):
    root=ET.parse(p).getroot(); tops=root.findall('.//top'); out={}
    for ordinal,t in enumerate(tops,1):
        out[ordinal]=(t.findtext('title') or '').strip()
    return out
def parse_rel(p):
    r=collections.defaultdict(set)
    for line in open(p):
        z=line.split()
        if len(z)>=4 and int(float(z[3]))>0:r[int(z[0])].add(int(z[2]))
    return r
def index(docs):
    tf={};dl={};df=collections.Counter()
    for d,s in docs.items():
        c=collections.Counter(tok(s));tf[d]=c;dl[d]=sum(c.values());df.update(c.keys())
    return tf,dl,df,sum(dl.values())/len(dl)
def bm(q,tf,dl,df,av,k1=1.2,b=.75):
    qt=tok(q);N=len(tf);sc={}
    for d,c in tf.items():
        K=k1*((1-b)+b*dl[d]/av);s=0.0
        for t in qt:
            n=df.get(t,0)
            if not n: continue
            idf=math.log((N-n+0.5)/(n+0.5)); f=c.get(t,0)
            if f:s += idf*((k1+1)*f)/(K+f)
        sc[d]=s
    return sc
def tfidf(q,tf,df):
    N=len(tf);qt=collections.Counter(tok(q));sc={}
    qv={t:(1+math.log(v))*math.log((N+1)/(df.get(t,0)+1)) for t,v in qt.items()}; qn=math.sqrt(sum(v*v for v in qv.values())) or 1
    for d,c in tf.items():
        dot=0;dn=0
        for t,f in c.items():
            w=(1+math.log(f))*math.log((N+1)/(df.get(t,0)+1));dn+=w*w
            if t in qv:dot+=w*qv[t]
        sc[d]=dot/(math.sqrt(dn)*qn) if dn else 0
    return sc
def rank(sc): return [d for d,_ in sorted(sc.items(),key=lambda x:(-x[1],x[0]))]
def ap(r,rel):
    if not rel:return 0
    h=s=0
    for i,d in enumerate(r,1):
        if d in rel:h+=1;s+=h/i
    return s/len(rel)
def p10(r,rel): return sum(d in rel for d in r[:10])/10
def rr(r,rel):
    for i,d in enumerate(r,1):
        if d in rel:return 1/i
    return 0
def ndcg(r,rel,k=10):
    dcg=sum((1 if d in rel else 0)/math.log2(i+2) for i,d in enumerate(r[:k]));idcg=sum(1/math.log2(i+2) for i in range(min(k,len(rel))))
    return dcg/idcg if idcg else 0
def main():
    a=argparse.ArgumentParser();a.add_argument('--docs');a.add_argument('--queries');a.add_argument('--qrels');a.add_argument('--out',default='results.tsv');x=a.parse_args()
    docs=parse_docs(x.docs);qs=parse_q(x.queries);tf,dl,df,av=index(docs)
    runs={'C96':{},'TFIDF':{}}
    for qid,q in qs.items():
        runs['C96'][qid]=rank(bm(q,tf,dl,df,av));runs['TFIDF'][qid]=rank(tfidf(q,tf,df))
    rel=parse_rel(x.qrels) # loaded only after rankings exist
    with open(x.out,'w') as f:
        f.write('variant\tMAP\tP@10\tnDCG@10\tMRR\n')
        for n,run in runs.items():
            vals=[]
            for qid,R in rel.items():
                if qid in run: vals.append((ap(run[qid],R),p10(run[qid],R),ndcg(run[qid],R),rr(run[qid],R)))
            means=[sum(v[i] for v in vals)/len(vals) for i in range(4)]
            f.write(n+'\t'+'\t'.join(f'{z:.6f}' for z in means)+'\n')
    print('documents',len(docs),'queries',len(qs),'qrels_queries',len(rel),'avgdl',av)
    print(open(x.out).read())
if __name__=='__main__': main()

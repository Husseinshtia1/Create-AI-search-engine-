#!/usr/bin/env python3
"""Exploratory G97-Web v3 on original CMU WebKB HTML.

IMPORTANT: Cornell/Texas/Washington/Wisconsin are already seen datasets in this
research program. This script is DEVELOPMENT/MECHANISM ANALYSIS, not independent
validation. Labels are used only after rankings are produced.

Frozen for this exploratory run:
- query-by-example text baseline: classical TF-IDF cosine
- top lexical seeds: 10
- graph boost lambda: 0.50
- raw graph relation is undirected for comparability with prior WebKB tests
- v2 quality = lexical cosine(seed,target)
- v3 quality = mean[ lexical cosine(seed,target), anchor relevance to query,
                     surrounding-link-neighborhood relevance to query ]
- graph cannot manufacture candidates with zero lexical relevance
"""
import argparse, collections, gzip, html, math, os, random, re
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

TOKEN_RE=re.compile(r"[A-Za-z0-9]+")
A_RE=re.compile(r"(?is)<a\s+[^>]*href\s*=\s*([\"']?)([^\"'\s>]+)\1[^>]*>(.*?)</a\s*>")
TAG_RE=re.compile(r"(?is)<[^>]+>")
SCRIPT_RE=re.compile(r"(?is)<(script|style)\b.*?</\1\s*>")

CLASSES=("course","faculty","student","research.project","staff")
UNIS=("cornell","texas","washington","wisconsin")

def toks(s): return [x.lower() for x in TOKEN_RE.findall(s or "")]
def textify(s):
    s=SCRIPT_RE.sub(" ",s or "")
    s=TAG_RE.sub(" ",s)
    return html.unescape(re.sub(r"\s+"," ",s)).strip()

def canon(u):
    try:
        p=urlsplit(u.strip())
        if not p.scheme or not p.netloc: return None
        scheme=p.scheme.lower(); host=p.netloc.lower()
        path=re.sub(r"/+","/",p.path or "/")
        if path.endswith("/index.html"): path=path[:-10] or "/"
        if path.endswith("/index.htm"): path=path[:-9] or "/"
        if len(path)>1 and path.endswith("/"): path=path[:-1]
        return urlunsplit((scheme,host,path,p.query,""))
    except Exception: return None

def url_from_filename(name):
    if name.endswith('.gz'): name=name[:-3]
    return canon(name.replace('^','/'))

def read_page(path):
    raw=gzip.open(path,'rt',encoding='latin1',errors='replace').read()
    parts=re.split(r"\r?\n\r?\n",raw,maxsplit=1)
    body=parts[1] if len(parts)>1 else raw
    return body,textify(body)

def load_pages(root):
    docs={}; paths={}
    for cls in CLASSES:
        for uni in UNIS:
            d=Path(root)/'page-text'/cls/uni
            if not d.exists(): continue
            for f in d.iterdir():
                if not f.is_file(): continue
                u=url_from_filename(f.name)
                if not u: continue
                try: body,txt=read_page(f)
                except Exception: continue
                docs[u]={'uni':uni,'text':txt,'html':body}
                paths[u]=str(f)
    return docs,paths

def build_vectors(docs):
    df=collections.Counter(); tf={}
    for u,d in docs.items():
        c=collections.Counter(toks(d['text'])); tf[u]=c; df.update(c.keys())
    N=len(docs); vec={}; norm={}
    for u,c in tf.items():
        v={}
        for t,f in c.items():
            idf=math.log((N+1)/(df[t]+1))+1.0
            v[t]=(1.0+math.log(f))*idf
        n=math.sqrt(sum(x*x for x in v.values())) or 1.0
        vec[u]=v; norm[u]=n
    return vec,norm

def cosine_sparse(a,b,na,nb):
    if len(a)>len(b): a,b=b,a
    return sum(v*b.get(k,0.0) for k,v in a.items())/(na*nb) if na and nb else 0.0

def temp_vector(text,df,N):
    c=collections.Counter(toks(text)); v={}
    for t,f in c.items():
        if t not in df: continue
        idf=math.log((N+1)/(df[t]+1))+1.0
        v[t]=(1+math.log(f))*idf
    n=math.sqrt(sum(x*x for x in v.values())) or 1.0
    return v,n

def extract_graph(docs,vec,norm):
    # edge_text[(a,b)] aggregates contexts from either original direction;
    # relation remains undirected to match previous WebKB tests.
    edge_text=collections.defaultdict(lambda:{'anchor':[],'neigh':[]})
    adj=collections.defaultdict(set)
    for src,d in docs.items():
        body=d['html']
        for m in A_RE.finditer(body):
            href=html.unescape(m.group(2)); tgt=canon(urljoin(src,href))
            if not tgt or tgt not in docs or tgt==src: continue
            atext=textify(m.group(3))
            lo=max(0,m.start()-220); hi=min(len(body),m.end()+220)
            neigh=textify(body[lo:hi])
            key=tuple(sorted((src,tgt)))
            if atext: edge_text[key]['anchor'].append(atext)
            if neigh: edge_text[key]['neigh'].append(neigh)
            adj[src].add(tgt); adj[tgt].add(src)
    return adj,edge_text

def rank(scores): return [d for d,_ in sorted(scores.items(),key=lambda x:(-x[1],x[0]))]
def rerank(base,evidence,lam=.50):
    return {d:s*(1+lam*(evidence.get(d,0)/(1+evidence.get(d,0)))) for d,s in base.items()}

def ap(r,rel):
    if not rel:return None
    h=0;s=0.0
    for i,d in enumerate(r,1):
        if d in rel:h+=1;s+=h/i
    return s/len(rel)
def pat(r,rel,k): return sum(d in rel for d in r[:k])/k
def rr(r,rel):
    for i,d in enumerate(r,1):
        if d in rel:return 1/i
    return 0.0
def ndcg(r,rel,k):
    dcg=sum((1.0 if d in rel else 0.0)/math.log2(i+2) for i,d in enumerate(r[:k]))
    ideal=sum(1/math.log2(i+2) for i in range(min(k,len(rel))))
    return dcg/ideal if ideal else 0.0

def bootstrap(a,b,n=5000,seed=1996):
    qs=sorted(set(a)&set(b)); ds=[b[q]-a[q] for q in qs]; rng=random.Random(seed); bs=[]
    for _ in range(n): bs.append(sum(ds[rng.randrange(len(ds))] for __ in ds)/len(ds))
    bs.sort(); return sum(ds)/len(ds),bs[int(.025*(n-1))],bs[int(.975*(n-1))],sum(x>1e-15 for x in ds),sum(x<-1e-15 for x in ds),sum(abs(x)<=1e-15 for x in ds)

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',default='results.tsv');a=p.parse_args()
    docs,_=load_pages(a.root); vec,norm=build_vectors(docs)
    # df needed only for temporary anchor/context vectors
    df=collections.Counter(); [df.update(v.keys()) for v in vec.values()]; N=len(docs)
    adj,edge_text=extract_graph(docs,vec,norm)
    byuni=collections.defaultdict(list)
    for u,d in docs.items():byuni[d['uni']].append(u)

    runs={name:{} for name in ['T0_TEXT','T1_GLOBAL_DEGREE','T2_LOCAL_RAW','T3_LOCAL_V2_LEXQUAL','T4_LOCAL_ANCHOR','T5_LOCAL_V3_CONTEXT']}
    # No label access in ranking loop.
    degmax=max((len(x) for x in adj.values()),default=1)
    for uni,ids in byuni.items():
        idset=set(ids)
        for q in ids:
            base={}
            for d in ids:
                if d==q:continue
                s=cosine_sparse(vec[q],vec[d],norm[q],norm[d])
                if s>0:base[d]=s
            if not base:continue
            seeds=rank(base)[:10]; mx=max(base.values()) or 1.0
            e_global={d:len(adj.get(d,set()))/degmax for d in base}
            e_raw=collections.Counter();e_v2=collections.Counter();e_anchor=collections.Counter();e_v3=collections.Counter()
            for s in seeds:
                conf=base[s]/mx
                for d in adj.get(s,set()):
                    if d not in idset or d not in base or d==q:continue
                    e_raw[d]+=conf
                    pair=tuple(sorted((s,d))); et=edge_text.get(pair,{'anchor':[],'neigh':[]})
                    st=cosine_sparse(vec[s],vec[d],norm[s],norm[d])
                    at=' '.join(et['anchor']); nt=' '.join(et['neigh'])
                    av,an=temp_vector(at,df,N) if at else ({},1.0)
                    nv,nn=temp_vector(nt,df,N) if nt else ({},1.0)
                    ar=cosine_sparse(vec[q],av,norm[q],an) if av else 0.0
                    nr=cosine_sparse(vec[q],nv,norm[q],nn) if nv else 0.0
                    e_v2[d]+=conf*st
                    e_anchor[d]+=conf*ar
                    quality=(st+ar+nr)/3.0
                    e_v3[d]+=conf*quality
            scored={
                'T0_TEXT':base,
                'T1_GLOBAL_DEGREE':rerank(base,e_global),
                'T2_LOCAL_RAW':rerank(base,e_raw),
                'T3_LOCAL_V2_LEXQUAL':rerank(base,e_v2),
                'T4_LOCAL_ANCHOR':rerank(base,e_anchor),
                'T5_LOCAL_V3_CONTEXT':rerank(base,e_v3),
            }
            for name,x in scored.items():runs[name][q]=rank(x)

    # Labels become visible only now, after all rankings exist.
    labels={u:next(cls for cls in CLASSES if f'/page-text/{cls}/' in _path.replace('\\','/')) for u,_path in _.items()}
    per={name:{} for name in runs}; avg={}
    for name,run in runs.items():
        ms=[]
        for q,r in run.items():
            rel={d for d in byuni[docs[q]['uni']] if d!=q and labels[d]==labels[q]}
            if not rel:continue
            m={'AP':ap(r,rel),'P10':pat(r,rel,10),'nDCG10':ndcg(r,rel,10),'MRR':rr(r,rel)};per[name][q]=m;ms.append(m)
        avg[name]={k:sum(x[k] for x in ms)/len(ms) for k in ['AP','P10','nDCG10','MRR']}
    with open(a.out,'w') as f:
        f.write('variant\tMAP\tP@10\tnDCG@10\tMRR\tAP_delta\tCI95_low\tCI95_high\twins\tlosses\tties\n')
        baseap={q:m['AP'] for q,m in per['T0_TEXT'].items()}
        for name in runs:
            if name=='T0_TEXT':sig=(0,0,0,0,0,0)
            else:sig=bootstrap(baseap,{q:m['AP'] for q,m in per[name].items()})
            r=avg[name];f.write(f"{name}\t{r['AP']:.6f}\t{r['P10']:.6f}\t{r['nDCG10']:.6f}\t{r['MRR']:.6f}\t{sig[0]:.6f}\t{sig[1]:.6f}\t{sig[2]:.6f}\t{sig[3]}\t{sig[4]}\t{sig[5]}\n")
    edges=sum(len(v) for v in adj.values())//2
    print('DEVELOPMENT ONLY: datasets already seen in earlier WebKB tests')
    print('pages',len(docs),'edges',edges,'universities',{k:len(v) for k,v in byuni.items()})
    print(open(a.out).read())
if __name__=='__main__':main()

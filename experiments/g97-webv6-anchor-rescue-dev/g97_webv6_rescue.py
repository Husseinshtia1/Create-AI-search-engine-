#!/usr/bin/env python3
"""G97-Web v6 DEVELOPMENT: external anchor text as an independent retriever.

Seen data only: Cornell/Texas/Washington/Wisconsin WebKB pages.
This experiment DOES NOT rerank body results. It asks whether inbound anchor text
retrieves relevant pages that body TF-IDF misses.

Frozen before results:
- TF-IDF cosine body retriever.
- External-description retriever = aggregate inbound anchor text per target.
- Each anchor occurrence is weighted by source scarcity 1/(1+ln(1+outdegree)).
- Retrieval/evidence generation never reads class labels.
- Evaluate K in {10,20,50}; compare Union(Body@K,Anchor@K) against Body@2K at
  approximately equal candidate budget, and count anchor-only relevant rescues.
"""
import argparse, collections, gzip, html, math, re
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

TOKEN_RE=re.compile(r"[A-Za-z0-9]+")
A_RE=re.compile(r"(?is)<a\s+[^>]*href\s*=\s*([\"']?)([^\"'\s>]+)\1[^>]*>(.*?)</a\s*>")
TAG_RE=re.compile(r"(?is)<[^>]+>")
SCRIPT_RE=re.compile(r"(?is)<(script|style)\b.*?</\1\s*>")
CLASSES=("course","faculty","student","research.project","staff")
UNIS=("cornell","texas","washington","wisconsin")
KS=(10,20,50)

def toks(s): return [x.lower() for x in TOKEN_RE.findall(s or "")]
def textify(s):
    s=SCRIPT_RE.sub(" ",s or ""); s=TAG_RE.sub(" ",s)
    return html.unescape(re.sub(r"\s+"," ",s)).strip()

def canon(u):
    try:
        p=urlsplit(u.strip())
        if not p.scheme or not p.netloc:return None
        path=re.sub(r"/+","/",p.path or "/")
        if path.endswith('/index.html'): path=path[:-10] or '/'
        if path.endswith('/index.htm'): path=path[:-9] or '/'
        if len(path)>1 and path.endswith('/'): path=path[:-1]
        return urlunsplit((p.scheme.lower(),p.netloc.lower(),path,p.query,''))
    except:return None

def url_from_filename(name):
    if name.endswith('.gz'):name=name[:-3]
    return canon(name.replace('^','/'))

def read_page(path):
    raw=gzip.open(path,'rt',encoding='latin1',errors='replace').read()
    parts=re.split(r"\r?\n\r?\n",raw,maxsplit=1); body=parts[1] if len(parts)>1 else raw
    return body,textify(body)

def load_pages(root):
    docs={};paths={}
    for cls in CLASSES:
      for uni in UNIS:
        d=Path(root)/'page-text'/cls/uni
        if not d.exists():continue
        for f in d.iterdir():
          if not f.is_file():continue
          u=url_from_filename(f.name)
          if not u:continue
          try:body,txt=read_page(f)
          except:continue
          docs[u]={'uni':uni,'text':txt,'html':body}; paths[u]=str(f)
    return docs,paths

def build_tfidf(texts):
    df=collections.Counter(); tf={}
    for d,s in texts.items():
        c=collections.Counter(toks(s));tf[d]=c;df.update(c.keys())
    N=len(texts);vec={};norm={}
    for d,c in tf.items():
        v={}
        for t,f in c.items():
            idf=math.log((N+1)/(df[t]+1))+1.0
            v[t]=(1+math.log(f))*idf
        n=math.sqrt(sum(x*x for x in v.values())) or 1.0
        vec[d]=v;norm[d]=n
    return vec,norm

def cos(a,b,na,nb):
    if len(a)>len(b):a,b=b,a
    return sum(v*b.get(k,0.0) for k,v in a.items())/(na*nb) if na and nb else 0.0

def rank(scores): return [d for d,_ in sorted(scores.items(),key=lambda x:(-x[1],x[0]))]

def external_descriptions(docs):
    # First pass: directed internal outdegree.
    out=collections.defaultdict(set); anchors=[]
    for src,d in docs.items():
        for m in A_RE.finditer(d['html']):
            tgt=canon(urljoin(src,html.unescape(m.group(2))))
            if not tgt or tgt not in docs or tgt==src:continue
            at=textify(m.group(3))
            out[src].add(tgt)
            if at: anchors.append((src,tgt,at))
    # Aggregate weighted anchor tokens into a textual field per target.
    weighted=collections.defaultdict(collections.Counter)
    occurrences=collections.Counter()
    for src,tgt,at in anchors:
        w=1.0/(1.0+math.log(1.0+len(out[src])))
        for t,c in collections.Counter(toks(at)).items(): weighted[tgt][t]+=w*c
        occurrences[tgt]+=1
    return weighted,out,occurrences

def build_weighted_anchor_vectors(weighted, all_docs):
    df=collections.Counter()
    for d,c in weighted.items():df.update(c.keys())
    N=len(all_docs);vec={};norm={}
    for d in all_docs:
        c=weighted.get(d,{})
        v={}
        for t,f in c.items():
            idf=math.log((N+1)/(df[t]+1))+1.0
            v[t]=(1.0+math.log(max(f,1e-12)))*idf if f>1 else f*idf
        n=math.sqrt(sum(x*x for x in v.values())) or 1.0
        vec[d]=v;norm[d]=n
    return vec,norm

def recall(items,rel): return len(set(items)&rel)/len(rel) if rel else 0.0

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',default='rescue.tsv');a=p.parse_args()
    docs,paths=load_pages(a.root)
    bodyv,bodyn=build_tfidf({d:x['text'] for d,x in docs.items()})
    weighted,out,occ=external_descriptions(docs)
    anchv,anchn=build_weighted_anchor_vectors(weighted,docs)
    byuni=collections.defaultdict(list)
    for d,x in docs.items():byuni[x['uni']].append(d)

    # Produce rankings WITHOUT labels.
    body_runs={};anchor_runs={}
    for uni,ids in byuni.items():
      for q in ids:
        bs={};ans={}
        for d in ids:
          if d==q:continue
          s=cos(bodyv[q],bodyv[d],bodyn[q],bodyn[d])
          if s>0:bs[d]=s
          sa=cos(bodyv[q],anchv[d],bodyn[q],anchn[d])
          if sa>0:ans[d]=sa
        body_runs[q]=rank(bs);anchor_runs[q]=rank(ans)

    # Labels visible only after both independent rankings exist.
    labels={}
    for u,path in paths.items():
        pp=path.replace('\\','/')
        for cls in CLASSES:
            if f'/page-text/{cls}/' in pp: labels[u]=cls;break

    rows=[]
    totals={k:collections.Counter() for k in KS}
    qcount=0
    for q,br in body_runs.items():
        uni=docs[q]['uni'];rel={d for d in byuni[uni] if d!=q and labels.get(d)==labels.get(q)}
        if not rel:continue
        qcount+=1;ar=anchor_runs[q]
        for k in KS:
            b=br[:k];aa=ar[:k]
            union=list(dict.fromkeys(b+aa))
            b2=br[:2*k]
            rescued=(set(aa)-set(b))&rel
            # Anchor-only rescue beyond body@2K is stronger evidence of new discovery.
            deep_rescue=(set(aa)-set(b2))&rel
            r={
              'body_k':recall(b,rel),'anchor_k':recall(aa,rel),'union_2k':recall(union,rel),'body_2k':recall(b2,rel),
              'rescued':len(rescued),'deep_rescue':len(deep_rescue),'union_size':len(union)
            }
            rows.append((q,k,r))
            for key,val in r.items():totals[k][key]+=val

    with open(a.out,'w') as f:
        f.write('K\tqueries\tBodyRecall@K\tAnchorRecall@K\tBodyRecall@2K\tUnionRecall<=2K\tDeltaUnionVsBody2K\tMeanRescuedOutsideBodyK\tMeanDeepRescueOutsideBody2K\tMeanUnionSize\n')
        for k in KS:
            t=totals[k];n=qcount
            bodyk=t['body_k']/n;anch=t['anchor_k']/n;b2=t['body_2k']/n;un=t['union_2k']/n
            f.write(f'{k}\t{n}\t{bodyk:.6f}\t{anch:.6f}\t{b2:.6f}\t{un:.6f}\t{un-b2:.6f}\t{t["rescued"]/n:.6f}\t{t["deep_rescue"]/n:.6f}\t{t["union_size"]/n:.3f}\n')
    print('DEVELOPMENT ONLY: four previously seen WebKB universities')
    print('pages',len(docs),'directed_internal_edges',sum(len(v) for v in out.values()),'targets_with_anchor_text',len(weighted),'queries',qcount)
    print(open(a.out).read())

if __name__=='__main__':main()

#!/usr/bin/env python3
"""G97-Web v7 DEVELOPMENT: failure-diagnosed external-description rescue.

Seen data only: Cornell/Texas/Washington/Wisconsin WebKB pages.
No supervised gate training and no labels/qrels are read before rankings, diagnostics,
quantile thresholds, and gate decisions are frozen for every query.

Frozen protocol before results:
- Body retriever: TF-IDF cosine over page body text.
- External-description retriever: aggregate inbound anchor text per target, weighted
  by source scarcity 1/(1+ln(1+outdegree)).
- K=10 only. Baseline candidate budget = Body@30.
- Rescue candidate set = Body@20 + novel Anchor@10, then fill from Body tail until
  exactly 30 candidates whenever at least 30 body candidates exist.
- Unsupervised per-university gate uses medians computed WITHOUT labels:
    weak body margin      := margin10 <= median(margin10)
    weak body coherence   := coherence10 <= median(coherence10)
    concentrated anchors  := anchor_top3_share >= median(anchor_top3_share)
    novel anchor evidence := anchor_novel_ratio >= median(anchor_novel_ratio)
  Gate activates only when all four conditions hold.
- If gate is off, use Body@30 unchanged. If gate is on, use exact-budget rescue.
- Labels become visible only after all rankings, diagnostics, thresholds and gates
  have been created.
"""
import argparse, collections, gzip, html, math, re, statistics
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

TOKEN_RE=re.compile(r"[A-Za-z0-9]+")
A_RE=re.compile(r"(?is)<a\s+[^>]*href\s*=\s*([\"']?)([^\"'\s>]+)\1[^>]*>(.*?)</a\s*>")
TAG_RE=re.compile(r"(?is)<[^>]+>")
SCRIPT_RE=re.compile(r"(?is)<(script|style)\b.*?</\1\s*>")
CLASSES=("course","faculty","student","research.project","staff")
UNIS=("cornell","texas","washington","wisconsin")
K=10

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
    parts=re.split(r"\r?\n\r?\n",raw,maxsplit=1)
    body=parts[1] if len(parts)>1 else raw
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
          docs[u]={'uni':uni,'text':txt,'html':body};paths[u]=str(f)
    return docs,paths

def build_tfidf(texts):
    df=collections.Counter();tf={}
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

def external_descriptions(docs):
    out=collections.defaultdict(set);anchors=[]
    for src,d in docs.items():
        for m in A_RE.finditer(d['html']):
            tgt=canon(urljoin(src,html.unescape(m.group(2))))
            if not tgt or tgt not in docs or tgt==src:continue
            at=textify(m.group(3));out[src].add(tgt)
            if at:anchors.append((src,tgt,at))
    weighted=collections.defaultdict(collections.Counter)
    for src,tgt,at in anchors:
        w=1.0/(1.0+math.log(1.0+len(out[src])))
        for t,c in collections.Counter(toks(at)).items():weighted[tgt][t]+=w*c
    return weighted,out

def build_anchor_vectors(weighted,all_docs):
    df=collections.Counter()
    for c in weighted.values():df.update(c.keys())
    N=len(all_docs);vec={};norm={}
    for d in all_docs:
        c=weighted.get(d,{})
        v={}
        for t,f in c.items():
            idf=math.log((N+1)/(df[t]+1))+1.0
            v[t]=((1.0+math.log(max(f,1e-12))) if f>1 else f)*idf
        n=math.sqrt(sum(x*x for x in v.values())) or 1.0
        vec[d]=v;norm[d]=n
    return vec,norm

def rank_scores(scores):
    return sorted(scores.items(),key=lambda x:(-x[1],x[0]))

def coherence(topdocs,vec,norm):
    if len(topdocs)<2:return 0.0
    vals=[]
    for i in range(len(topdocs)):
        for j in range(i+1,len(topdocs)):
            a,b=topdocs[i],topdocs[j]
            vals.append(cos(vec[a],vec[b],norm[a],norm[b]))
    return sum(vals)/len(vals) if vals else 0.0

def exact_rescue(body_order,anchor_order,budget=30):
    chosen=[];seen=set()
    for d in body_order[:20]:
        if d not in seen:chosen.append(d);seen.add(d)
    for d in anchor_order[:10]:
        if d not in seen and len(chosen)<budget:chosen.append(d);seen.add(d)
    for d in body_order[20:]:
        if len(chosen)>=budget:break
        if d not in seen:chosen.append(d);seen.add(d)
    return chosen

def recall(items,rel):return len(set(items)&rel)/len(rel) if rel else 0.0

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--out',default='results.tsv');args=ap.parse_args()
    docs,paths=load_pages(args.root)
    bodyv,bodyn=build_tfidf({d:x['text'] for d,x in docs.items()})
    weighted,out=external_descriptions(docs)
    anchv,anchn=build_anchor_vectors(weighted,docs)
    byuni=collections.defaultdict(list)
    for d,x in docs.items():byuni[x['uni']].append(d)

    # Build rankings and observable diagnostics BEFORE labels are read.
    body_runs={};anchor_runs={};features={}
    for uni,ids in byuni.items():
        for q in ids:
            bs={};ans={}
            for d in ids:
                if d==q:continue
                s=cos(bodyv[q],bodyv[d],bodyn[q],bodyn[d])
                if s>0:bs[d]=s
                sa=cos(bodyv[q],anchv[d],bodyn[q],anchn[d])
                if sa>0:ans[d]=sa
            br=rank_scores(bs);ar=rank_scores(ans)
            body_runs[q]=[d for d,_ in br];anchor_runs[q]=[d for d,_ in ar]
            topb=br[:K];topa=ar[:K]
            if topb:
                s1=topb[0][1];s10=topb[min(K-1,len(topb)-1)][1]
                margin=(s1-s10)/(s1+1e-12)
            else:margin=0.0
            coh=coherence([d for d,_ in topb],bodyv,bodyn)
            asum=sum(s for _,s in topa);a3=sum(s for _,s in topa[:3])
            aconc=(a3/asum) if asum>0 else 0.0
            b20=set(d for d,_ in br[:20]);anov=sum(1 for d,_ in topa if d not in b20)/K
            features[q]=(margin,coh,aconc,anov)

    # Unsupervised median thresholds per university, still before labels.
    thresholds={}
    gates={}
    for uni,ids in byuni.items():
        vals=[features[q] for q in ids]
        meds=tuple(statistics.median(v[i] for v in vals) for i in range(4))
        thresholds[uni]=meds
        for q in ids:
            m,c,a,n=features[q];mm,mc,ma,mn=meds
            gates[q]=(m<=mm and c<=mc and a>=ma and n>=mn and len(anchor_runs[q])>0)

    # Labels become visible only here.
    labels={}
    for u,path in paths.items():
        pp=path.replace('\\','/')
        for cls in CLASSES:
            if f'/page-text/{cls}/' in pp:labels[u]=cls;break

    rows=[];tot=collections.Counter();peruni=collections.defaultdict(collections.Counter)
    for q,br in body_runs.items():
        uni=docs[q]['uni'];rel={d for d in byuni[uni] if d!=q and labels.get(d)==labels.get(q)}
        if not rel:continue
        body30=br[:30]
        hybrid=exact_rescue(br,anchor_runs[q],30)
        chosen=hybrid if gates[q] else body30
        rb=recall(body30,rel);rv=recall(chosen,rel);rh=recall(hybrid,rel)
        delta=rv-rb
        rows.append((q,uni,int(gates[q]),rb,rh,rv,delta,*features[q]))
        tot['q']+=1;tot['gated']+=int(gates[q]);tot['body']+=rb;tot['v7']+=rv;tot['hybrid_all']+=rh
        tot['wins']+=int(delta>1e-12);tot['losses']+=int(delta<-1e-12);tot['ties']+=int(abs(delta)<=1e-12)
        s=peruni[uni];s['q']+=1;s['gated']+=int(gates[q]);s['body']+=rb;s['v7']+=rv;s['wins']+=int(delta>1e-12);s['losses']+=int(delta<-1e-12);s['ties']+=int(abs(delta)<=1e-12)

    with open(args.out,'w') as f:
        f.write('scope\tqueries\tgate_rate\tBodyRecall30\tV7Recall30\tDelta\twins\tlosses\tties\n')
        n=tot['q'];f.write(f'ALL\t{n}\t{tot["gated"]/n:.6f}\t{tot["body"]/n:.6f}\t{tot["v7"]/n:.6f}\t{(tot["v7"]-tot["body"])/n:.6f}\t{tot["wins"]}\t{tot["losses"]}\t{tot["ties"]}\n')
        for uni in UNIS:
            s=peruni[uni];n=s['q']
            f.write(f'{uni}\t{n}\t{s["gated"]/n:.6f}\t{s["body"]/n:.6f}\t{s["v7"]/n:.6f}\t{(s["v7"]-s["body"])/n:.6f}\t{s["wins"]}\t{s["losses"]}\t{s["ties"]}\n')
    detail=Path(args.out).with_name('per_query.tsv')
    with open(detail,'w') as f:
        f.write('query\tuni\tgate\tbody30\thybrid30_if_forced\tv7\tdelta\tmargin10\tcoherence10\tanchor_top3_share\tanchor_novel_ratio\n')
        for r in rows:f.write('\t'.join(map(str,r))+'\n')
    print('DEVELOPMENT ONLY; labels hidden until after all gates were frozen')
    print('pages',len(docs),'edges',sum(len(x) for x in out.values()),'anchor_targets',len(weighted))
    print('thresholds',thresholds)
    print(open(args.out).read())

if __name__=='__main__':main()

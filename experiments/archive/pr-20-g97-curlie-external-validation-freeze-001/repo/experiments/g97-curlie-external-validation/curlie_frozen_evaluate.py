#!/usr/bin/env python3
"""Frozen external evaluator for Curlie. Do not modify after first Curlie retrieval metrics."""
import argparse, collections, gzip, json, math, random, re
from pathlib import Path
TOKEN_RE=re.compile(r'[A-Za-z0-9]+')
BOOT_SEED=19961231
BOOT_N=10000

def toks(s): return [x.lower() for x in TOKEN_RE.findall(s or '')]
def tfweight(f): return 1.0+math.log(f)

def load_docs(path):
    docs={}; anchors={}
    with gzip.open(path,'rt',encoding='utf-8',errors='replace') as f:
        for line in f:
            x=json.loads(line);u=str(x['uid']);docs[u]=x.get('body','');anchors[u]=x.get('anchors',{})
    return docs,anchors

def load_classes(path,keep):
    out={}
    with gzip.open(path,'rt',encoding='utf-8',errors='replace') as f:
        for line in f:
            x=json.loads(line);u=str(x.get('uid',''))
            if u in keep: out[u]=tuple(int(v) for v in x.get('class_vector',[]))
    return out

def body_vectors(texts):
    df=collections.Counter();tf={}
    for d,s in texts.items():
        c=collections.Counter(toks(s));tf[d]=c;df.update(c.keys())
    N=len(texts);vec={};norm={};post=collections.defaultdict(list)
    for d,c in tf.items():
        v={}
        for t,f in c.items():v[t]=tfweight(f)*(math.log((N+1)/(df[t]+1))+1.0)
        n=math.sqrt(sum(x*x for x in v.values())) or 1.0;vec[d]=v;norm[d]=n
        for t,w in v.items():post[t].append((d,w))
    return vec,norm,post

def anchor_vectors(anchor_edges,all_docs):
    weighted=collections.defaultdict(collections.Counter)
    for src,targets in anchor_edges.items():
        od=len(targets);scar=1.0/(1.0+math.log(1.0+od)) if od else 0.0
        for tgt,strings in targets.items():
            for s in strings:
                for t,c in collections.Counter(toks(s)).items():weighted[str(tgt)][t]+=scar*c
    df=collections.Counter()
    for c in weighted.values():df.update(c.keys())
    N=len(all_docs);vec={};norm={};post=collections.defaultdict(list)
    for d in all_docs:
        c=weighted.get(d,{}) ; v={}
        for t,f in c.items():
            idf=math.log((N+1)/(df[t]+1))+1.0
            v[t]=((1.0+math.log(max(f,1e-12))) if f>1 else f)*idf
        n=math.sqrt(sum(x*x for x in v.values())) or 1.0;vec[d]=v;norm[d]=n
        for t,w in v.items():post[t].append((d,w))
    return vec,norm,post

def retrieve(q,qv,qn,post,dnorm,k):
    acc=collections.defaultdict(float)
    for t,wq in qv.items():
        for d,wd in post.get(t,()):
            if d!=q:acc[d]+=wq*wd
    scored=[]
    for d,dot in acc.items():
        s=dot/(qn*dnorm[d]) if qn and dnorm[d] else 0.0
        if s>0:scored.append((d,s))
    scored.sort(key=lambda x:(-x[1],x[0]));return scored[:k]

def cos(a,b,na,nb):
    if len(a)>len(b):a,b=b,a
    return sum(v*b.get(t,0.0) for t,v in a.items())/(na*nb) if na and nb else 0.0

def coherence(ids,vec,norm):
    if len(ids)<2:return 0.0
    z=[]
    for i in range(len(ids)):
      for j in range(i+1,len(ids)):z.append(cos(vec[ids[i]],vec[ids[j]],norm[ids[i]],norm[ids[j]]))
    return sum(z)/len(z) if z else 0.0

def exact_rescue(body,anch,budget=30):
    chosen=[];seen=set()
    for d,_ in body[:20]:
        if d not in seen:chosen.append(d);seen.add(d)
    for d,_ in anch[:10]:
        if d not in seen and len(chosen)<budget:chosen.append(d);seen.add(d)
    for d,_ in body[20:]:
        if len(chosen)>=budget:break
        if d not in seen:chosen.append(d);seen.add(d)
    return chosen

def features(q,br,ar,bv,bn,text):
    topb=br[:10];topa=ar[:10]
    if topb:
        s1=topb[0][1];s10=topb[min(9,len(topb)-1)][1];margin=(s1-s10)/(s1+1e-12)
        meanb=sum(s for _,s in topb)/len(topb);sd=math.sqrt(sum((s-meanb)**2 for _,s in topb)/len(topb));cv=sd/(meanb+1e-12)
    else:s1=meanb=cv=margin=0.0
    coh=coherence([d for d,_ in topb],bv,bn)
    asum=sum(s for _,s in topa);a3=sum(s for _,s in topa[:3]);aconc=a3/asum if asum else 0.0
    b20={d for d,_ in br[:20]};nov=sum(1 for d,_ in topa if d not in b20)/10.0
    at1=topa[0][1] if topa else 0.0;acount=len(topa)/10.0;qlen=math.log1p(len(toks(text[q])))
    return [margin,coh,aconc,nov,s1,meanb,cv,qlen,at1,acount]

def controller_score(x,c):
    z=[(v-m)/s for v,m,s in zip(x,c['means'],c['stds'])]
    dn=sum((a-b)**2 for a,b in zip(z,c['negative_centroid']))
    dp=sum((a-b)**2 for a,b in zip(z,c['positive_centroid']))
    return dn-dp

def bootstrap(deltas):
    rng=random.Random(BOOT_SEED);n=len(deltas);means=[]
    for _ in range(BOOT_N):means.append(sum(deltas[rng.randrange(n)] for __ in range(n))/n)
    means.sort();return means[int(.025*BOOT_N)],means[int(.975*BOOT_N)-1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--docs',required=True);ap.add_argument('--classes',required=True);ap.add_argument('--controller',required=True);ap.add_argument('--feasibility',required=True);ap.add_argument('--outdir',required=True);a=ap.parse_args()
    feas=json.loads(Path(a.feasibility).read_text())
    if feas.get('status')!='FEASIBLE_FOR_FROZEN_RETRIEVAL':raise SystemExit('FROZEN PROTOCOL STOP: feasibility gate did not pass')
    text,edges=load_docs(a.docs);ids=set(text);cls=load_classes(a.classes,ids);c=json.loads(Path(a.controller).read_text())
    if len(text)!=20000 or len(cls)!=20000:raise SystemExit(f'FROZEN PROTOCOL STOP: docs={len(text)} labels={len(cls)}')
    bv,bn,bpost=body_vectors(text);av,an,apost=anchor_vectors(edges,text)
    byclass=collections.defaultdict(set)
    for d,v in cls.items():
        for i,x in enumerate(v):
            if x:byclass[i].add(d)
    rows=[];deltas=[]
    for qi,q in enumerate(sorted(ids)):
        br=retrieve(q,bv[q],bn[q],bpost,bn,30)
        ar=retrieve(q,bv[q],bn[q],apost,an,10)
        rel=set()
        for i,x in enumerate(cls[q]):
            if x:rel.update(byclass[i])
        rel.discard(q)
        if not rel:continue
        body=[d for d,_ in br];forced=exact_rescue(br,ar,30);x=features(q,br,ar,bv,bn,text);score=controller_score(x,c);gate=score>=c['threshold_tau'];policy=forced if gate else body
        rb=len(set(body)&rel)/len(rel);rf=len(set(forced)&rel)/len(rel);rp=len(set(policy)&rel)/len(rel);delta=rp-rb;deltas.append(delta)
        rows.append((q,int(gate),score,len(rel),rb,rf,rp,delta))
    n=len(rows);B=sum(r[4] for r in rows)/n;F=sum(r[5] for r in rows)/n;P=sum(r[6] for r in rows)/n;D=P-B;lo,hi=bootstrap(deltas)
    wins=sum(r[7]>1e-15 for r in rows);losses=sum(r[7]<-1e-15 for r in rows);ties=n-wins-losses;gates=sum(r[1] for r in rows)
    out=Path(a.outdir);out.mkdir(parents=True,exist_ok=True)
    summary={'queries':n,'BodyRecall30':B,'ForcedHybridRecall30':F,'V8Recall30':P,'Delta':D,'gate_rate':gates/n,'wins':wins,'losses':losses,'ties':ties,'bootstrap_seed':BOOT_SEED,'bootstrap_resamples':BOOT_N,'delta_95ci':[lo,hi],'controller_tau':c['threshold_tau']}
    (out/'results.json').write_text(json.dumps(summary,indent=2,sort_keys=True))
    with open(out/'per_query.tsv','w') as f:
        f.write('query\tgate\tscore\trelevant\tbody30\tforced30\tv8\tdelta\n')
        for r in rows:f.write('\t'.join(map(str,r))+'\n')
    print(json.dumps(summary,indent=2,sort_keys=True))
if __name__=='__main__':main()

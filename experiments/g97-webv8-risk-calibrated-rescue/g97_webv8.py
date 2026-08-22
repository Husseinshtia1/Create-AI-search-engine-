#!/usr/bin/env python3
"""G97-Web v8: OOF risk-calibrated selective rescue.

DEVELOPMENT ONLY on the four already-seen WebKB universities.
Frozen rule before results:
- Body retriever and anchor retriever are exactly the v7 versions.
- Candidate budget is exactly 30.
- Rescue candidate set = Body@20 + novel Anchor@10, then fill from body tail to 30.
- Observable classifier features and nearest-centroid score are exactly the v7 predictability diagnostic.
- Leave-one-university-out only.
- For each held-out university, train classifier on the other 3 universities.
- Training-only calibration: among unique training scores, choose the HIGHEST threshold tau such that
  at least 20 training queries have score>=tau and mean actual DeltaRecall30 over those activated
  training queries is strictly >0. If none exists, set tau=+inf (never rescue).
- Apply that tau once to the held-out university. No holdout tuning.
- Labels are used only after body/anchor rankings and observable features are produced.
"""
import argparse, collections, importlib.util, math
from pathlib import Path

HERE=Path(__file__).resolve().parent
V7DIR=HERE.parent/'g97-webv7-failure-diagnosed-rescue'
spec=importlib.util.spec_from_file_location('v7',V7DIR/'g97_webv7.py')
v7=importlib.util.module_from_spec(spec);spec.loader.exec_module(v7)

FEATURES=10

def zstats(rows):
    p=len(rows[0]);means=[];stds=[]
    for j in range(p):
        vals=[r[j] for r in rows];m=sum(vals)/len(vals)
        sd=math.sqrt(sum((x-m)**2 for x in vals)/max(1,len(vals)-1)) or 1.0
        means.append(m);stds.append(sd)
    return means,stds

def zrow(r,m,s): return [(x-a)/b for x,a,b in zip(r,m,s)]
def centroid(rows): return [sum(r[j] for r in rows)/len(rows) for j in range(len(rows[0]))]
def d2(a,b): return sum((x-y)**2 for x,y in zip(a,b))

def features(q,br,ar,bodyv,bodyn,docs):
    topb=br[:10];topa=ar[:10]
    if topb:
        s1=topb[0][1];s10=topb[min(9,len(topb)-1)][1]
        margin=(s1-s10)/(s1+1e-12)
        meanb=sum(s for _,s in topb)/len(topb)
        sdb=math.sqrt(sum((s-meanb)**2 for _,s in topb)/len(topb))
        cv=sdb/(meanb+1e-12)
    else: s1=meanb=cv=margin=0.0
    coh=v7.coherence([d for d,_ in topb],bodyv,bodyn)
    asum=sum(s for _,s in topa);a3=sum(s for _,s in topa[:3])
    aconc=a3/asum if asum else 0.0
    b20=set(d for d,_ in br[:20]);nov=sum(1 for d,_ in topa if d not in b20)/10.0
    at1=topa[0][1] if topa else 0.0
    acount=len(topa)/10.0
    qlen=math.log1p(len(v7.toks(docs[q]['text'])))
    return [margin,coh,aconc,nov,s1,meanb,cv,qlen,at1,acount]

def choose_tau(train_scores, delta, min_active=20):
    # Highest unique score threshold with >=min_active and positive mean training utility.
    vals=sorted({train_scores[q] for q in train_scores}, reverse=True)
    for tau in vals:
        active=[q for q,s in train_scores.items() if s>=tau]
        if len(active)<min_active: continue
        mean=sum(delta[q] for q in active)/len(active)
        if mean>0:
            return tau,len(active),mean
    return float('inf'),0,0.0

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--out',default='results.tsv');args=ap.parse_args()
    docs,paths=v7.load_pages(args.root)
    bodyv,bodyn=v7.build_tfidf({d:x['text'] for d,x in docs.items()})
    weighted,out=v7.external_descriptions(docs)
    anchv,anchn=v7.build_anchor_vectors(weighted,docs)
    byuni=collections.defaultdict(list)
    for d,x in docs.items(): byuni[x['uni']].append(d)

    # Generate rankings and observables before labels.
    body_scores={};anchor_scores={};body_runs={};anchor_runs={};obs={}
    for uni,ids in byuni.items():
        for q in ids:
            bs={};ans={}
            for d in ids:
                if d==q: continue
                s=v7.cos(bodyv[q],bodyv[d],bodyn[q],bodyn[d])
                if s>0: bs[d]=s
                sa=v7.cos(bodyv[q],anchv[d],bodyn[q],anchn[d])
                if sa>0: ans[d]=sa
            br=v7.rank_scores(bs);ar=v7.rank_scores(ans)
            body_scores[q]=br;anchor_scores[q]=ar
            body_runs[q]=[d for d,_ in br];anchor_runs[q]=[d for d,_ in ar]
            obs[q]=features(q,br,ar,bodyv,bodyn,docs)

    # Reveal class labels only now.
    labels={}
    for u,path in paths.items():
        pp=path.replace('\\','/')
        for cls in v7.CLASSES:
            if f'/page-text/{cls}/' in pp: labels[u]=cls; break

    body_recall={};hyb_recall={};delta={};relevant={}
    for q,br in body_runs.items():
        uni=docs[q]['uni'];rel={d for d in byuni[uni] if d!=q and labels.get(d)==labels.get(q)}
        relevant[q]=rel
        body=br[:30];hyb=v7.exact_rescue(br,anchor_runs[q],30)
        rb=v7.recall(body,rel);rh=v7.recall(hyb,rel)
        body_recall[q]=rb;hyb_recall[q]=rh;delta[q]=rh-rb

    rows=[];all_policy=[]
    for held in v7.UNIS:
        train_all=[q for q in body_runs if docs[q]['uni']!=held]
        train_nt=[q for q in train_all if abs(delta[q])>1e-12]
        test=[q for q in body_runs if docs[q]['uni']==held]
        X=[obs[q] for q in train_nt];m,s=zstats(X)
        pos=[zrow(obs[q],m,s) for q in train_nt if delta[q]>0]
        neg=[zrow(obs[q],m,s) for q in train_nt if delta[q]<0]
        cp=centroid(pos);cn=centroid(neg)
        def score(q):
            z=zrow(obs[q],m,s);return d2(z,cn)-d2(z,cp)
        train_scores={q:score(q) for q in train_all}
        tau,nact_train,mean_train=choose_tau(train_scores,delta,20)
        wins=losses=ties=active=0;sum_body=sum_policy=0.0
        for q in test:
            sc=score(q);use=sc>=tau
            rb=body_recall[q];rp=hyb_recall[q] if use else rb
            sum_body+=rb;sum_policy+=rp;active+=int(use)
            if rp>rb+1e-12:wins+=1
            elif rp<rb-1e-12:losses+=1
            else:ties+=1
            all_policy.append((q,held,sc,tau,use,rb,rp,delta[q]))
        n=len(test);rows.append((held,n,tau,nact_train,mean_train,active/n,sum_body/n,sum_policy/n,(sum_policy-sum_body)/n,wins,losses,ties))

    n=len(all_policy);B=sum(r[5] for r in all_policy)/n;P=sum(r[6] for r in all_policy)/n
    active=sum(1 for r in all_policy if r[4]);wins=sum(1 for r in all_policy if r[6]>r[5]+1e-12);losses=sum(1 for r in all_policy if r[6]<r[5]-1e-12);ties=n-wins-losses
    with open(args.out,'w') as f:
        f.write('scope\tqueries\ttau\ttrain_active\ttrain_mean_delta\tgate_rate\tBodyRecall30\tPolicyRecall30\tDelta\twins\tlosses\tties\n')
        f.write(f'ALL\t{n}\tNA\tNA\tNA\t{active/n:.6f}\t{B:.6f}\t{P:.6f}\t{P-B:.6f}\t{wins}\t{losses}\t{ties}\n')
        for r in rows:
            tau='inf' if math.isinf(r[2]) else f'{r[2]:.9f}'
            f.write(f'{r[0]}\t{r[1]}\t{tau}\t{r[3]}\t{r[4]:.9f}\t{r[5]:.6f}\t{r[6]:.6f}\t{r[7]:.6f}\t{r[8]:.6f}\t{r[9]}\t{r[10]}\t{r[11]}\n')
    detail=Path(args.out).with_name('oof_policy.tsv')
    with open(detail,'w') as f:
        f.write('query\theldout_uni\tscore\ttau\tgate\tbody_recall30\tpolicy_recall30\tforced_delta\n')
        for r in all_policy:f.write('\t'.join(map(str,r))+'\n')
    print('G97-WEB V8 DEVELOPMENT ONLY: TRAINING-FOLD-ONLY RISK CALIBRATION')
    print('pages',len(docs),'edges',sum(out.values()),'anchor_targets',len(weighted))
    print(open(args.out).read())

if __name__=='__main__': main()

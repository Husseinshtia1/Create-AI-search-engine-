#!/usr/bin/env python3
"""POST-RESULT DEVELOPMENT DIAGNOSTIC for G97-Web v7.

Purpose: test whether observable pre-relevance diagnostics contain enough signal to
separate queries where forced HybridExact30 helps from those where it hurts.
This is NOT a new ranking method and must not be interpreted as validation.

Predeclared diagnostic protocol before reading these results:
- Reuse the exact v7 body and anchor retrievers.
- Outcome label is defined only after rankings exist:
    positive = HybridExact30 recall > Body30 recall
    negative = HybridExact30 recall < Body30 recall
    ties are excluded from classifier fitting/evaluation.
- Observable feature vector (no labels required):
    1 margin10
    2 coherence10
    3 anchor_top3_share
    4 anchor_novel_ratio
    5 body_top1_score
    6 body_top10_mean_score
    7 body_top10_score_cv
    8 query_token_count_log
    9 anchor_top1_score
   10 anchor_nonempty_count_ratio
- Leave-one-university-out only. For each held-out university, training statistics,
  z-normalization, positive centroid and negative centroid are computed on the
  other three universities only.
- Classifier score = squared distance to negative centroid minus squared distance
  to positive centroid. Positive score predicts benefit. No threshold tuning.
- Report OOF ROC-AUC, balanced accuracy at score>0, positive prevalence, and
  precision among the top 10% highest OOF scores as descriptive evidence.
"""
import argparse, collections, importlib.util, math, statistics
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v7',HERE/'g97_webv7.py')
v7=importlib.util.module_from_spec(spec);spec.loader.exec_module(v7)


def auc(scores,labels):
    # Mann-Whitney formulation, tie-aware by average ranks.
    pairs=sorted(zip(scores,labels),key=lambda x:x[0])
    n=len(pairs);ranks=[0.0]*n;i=0
    while i<n:
        j=i+1
        while j<n and pairs[j][0]==pairs[i][0]:j+=1
        avg=((i+1)+j)/2.0
        for k in range(i,j):ranks[k]=avg
        i=j
    npos=sum(labels);nneg=n-npos
    if not npos or not nneg:return float('nan')
    rpos=sum(r for r,(_,y) in zip(ranks,pairs) if y==1)
    return (rpos-npos*(npos+1)/2)/(npos*nneg)

def balanced_acc(scores,labels):
    tp=tn=fp=fn=0
    for s,y in zip(scores,labels):
        p=1 if s>0 else 0
        if y==1 and p==1:tp+=1
        elif y==1:fn+=1
        elif p==0:tn+=1
        else:fp+=1
    tpr=tp/(tp+fn) if tp+fn else 0
    tnr=tn/(tn+fp) if tn+fp else 0
    return (tpr+tnr)/2,tpr,tnr,tp,fn,tn,fp

def zstats(rows):
    p=len(rows[0]);means=[];stds=[]
    for j in range(p):
        vals=[r[j] for r in rows];m=sum(vals)/len(vals)
        sd=math.sqrt(sum((x-m)**2 for x in vals)/max(1,len(vals)-1)) or 1.0
        means.append(m);stds.append(sd)
    return means,stds

def zrow(r,m,s):return [(x-a)/b for x,a,b in zip(r,m,s)]
def centroid(rows):return [sum(r[j] for r in rows)/len(rows) for j in range(len(rows[0]))]
def d2(a,b):return sum((x-y)**2 for x,y in zip(a,b))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--out',default='predictability.tsv');args=ap.parse_args()
    docs,paths=v7.load_pages(args.root)
    bodyv,bodyn=v7.build_tfidf({d:x['text'] for d,x in docs.items()})
    weighted,out=v7.external_descriptions(docs)
    anchv,anchn=v7.build_anchor_vectors(weighted,docs)
    byuni=collections.defaultdict(list)
    for d,x in docs.items():byuni[x['uni']].append(d)

    body_runs={};anchor_runs={};obs={}
    for uni,ids in byuni.items():
        for q in ids:
            bs={};ans={}
            for d in ids:
                if d==q:continue
                s=v7.cos(bodyv[q],bodyv[d],bodyn[q],bodyn[d])
                if s>0:bs[d]=s
                sa=v7.cos(bodyv[q],anchv[d],bodyn[q],anchn[d])
                if sa>0:ans[d]=sa
            br=v7.rank_scores(bs);ar=v7.rank_scores(ans)
            body_runs[q]=[d for d,_ in br];anchor_runs[q]=[d for d,_ in ar]
            topb=br[:10];topa=ar[:10]
            if topb:
                s1=topb[0][1];s10=topb[min(9,len(topb)-1)][1]
                margin=(s1-s10)/(s1+1e-12)
                meanb=sum(s for _,s in topb)/len(topb)
                sdb=math.sqrt(sum((s-meanb)**2 for _,s in topb)/len(topb))
                cv=sdb/(meanb+1e-12)
            else:s1=meanb=cv=margin=0.0
            coh=v7.coherence([d for d,_ in topb],bodyv,bodyn)
            asum=sum(s for _,s in topa);a3=sum(s for _,s in topa[:3])
            aconc=a3/asum if asum else 0.0
            b20=set(d for d,_ in br[:20]);nov=sum(1 for d,_ in topa if d not in b20)/10.0
            at1=topa[0][1] if topa else 0.0
            acount=len(topa)/10.0
            qlen=math.log1p(len(v7.toks(docs[q]['text'])))
            obs[q]=[margin,coh,aconc,nov,s1,meanb,cv,qlen,at1,acount]

    labels_map={}
    for u,path in paths.items():
        pp=path.replace('\\','/')
        for cls in v7.CLASSES:
            if f'/page-text/{cls}/' in pp:labels_map[u]=cls;break

    outcome={}
    for q,br in body_runs.items():
        uni=docs[q]['uni'];rel={d for d in byuni[uni] if d!=q and labels_map.get(d)==labels_map.get(q)}
        if not rel:continue
        body=br[:30];hyb=v7.exact_rescue(br,anchor_runs[q],30)
        rb=v7.recall(body,rel);rh=v7.recall(hyb,rel)
        if rh>rb+1e-12:outcome[q]=1
        elif rh<rb-1e-12:outcome[q]=0
        else:outcome[q]=None

    oof=[];foldstats=[]
    for held in v7.UNIS:
        train=[q for q in outcome if docs[q]['uni']!=held and outcome[q] is not None]
        test=[q for q in outcome if docs[q]['uni']==held and outcome[q] is not None]
        X=[obs[q] for q in train];m,s=zstats(X)
        pos=[zrow(obs[q],m,s) for q in train if outcome[q]==1]
        neg=[zrow(obs[q],m,s) for q in train if outcome[q]==0]
        cp=centroid(pos);cn=centroid(neg)
        fs=[];ys=[]
        for q in test:
            z=zrow(obs[q],m,s);score=d2(z,cn)-d2(z,cp);y=outcome[q]
            oof.append((q,held,score,y));fs.append(score);ys.append(y)
        ba,tpr,tnr,tp,fn,tn,fp=balanced_acc(fs,ys)
        foldstats.append((held,len(test),sum(ys)/len(ys),auc(fs,ys),ba,tpr,tnr,tp,fn,tn,fp))

    scores=[x[2] for x in oof];ys=[x[3] for x in oof]
    A=auc(scores,ys);ba,tpr,tnr,tp,fn,tn,fp=balanced_acc(scores,ys)
    order=sorted(oof,key=lambda x:x[2],reverse=True)
    topn=max(1,math.ceil(0.10*len(order)));top=order[:topn]
    top_prec=sum(x[3] for x in top)/len(top);base=sum(ys)/len(ys);lift=top_prec/base if base else float('nan')

    with open(args.out,'w') as f:
        f.write('scope\tnontie_queries\tpositive_rate\tAUC\tbalanced_accuracy\tTPR\tTNR\tTP\tFN\tTN\tFP\n')
        f.write(f'ALL\t{len(ys)}\t{base:.6f}\t{A:.6f}\t{ba:.6f}\t{tpr:.6f}\t{tnr:.6f}\t{tp}\t{fn}\t{tn}\t{fp}\n')
        for r in foldstats:
            f.write(f'{r[0]}\t{r[1]}\t{r[2]:.6f}\t{r[3]:.6f}\t{r[4]:.6f}\t{r[5]:.6f}\t{r[6]:.6f}\t{r[7]}\t{r[8]}\t{r[9]}\t{r[10]}\n')
        f.write(f'TOP10PCT_PRECISION\t{topn}\t{top_prec:.6f}\tLIFT\t{lift:.6f}\n')
    detail=Path(args.out).with_name('oof_scores.tsv')
    with open(detail,'w') as f:
        f.write('query\theldout_uni\tscore\tbenefit_label\n')
        for r in oof:f.write('\t'.join(map(str,r))+'\n')
    print('POST-RESULT DEVELOPMENT DIAGNOSTIC; not a new ranking validation')
    print('pages',len(docs),'nontie',len(ys),'positive_rate',base)
    print(open(args.out).read())

if __name__=='__main__':main()

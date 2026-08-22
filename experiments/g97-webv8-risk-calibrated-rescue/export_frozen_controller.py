#!/usr/bin/env python3
"""Export a single G97-Web v8 controller trained only on the four seen WebKB universities.
This does not touch Curlie or any external-validation labels.
"""
import argparse, collections, importlib.util, json, math
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v8',HERE/'g97_webv8.py')
v8=importlib.util.module_from_spec(spec);spec.loader.exec_module(v8)
v7=v8.v7

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    docs,paths=v7.load_pages(a.root)
    bodyv,bodyn=v7.build_tfidf({d:x['text'] for d,x in docs.items()})
    weighted,outdeg=v7.external_descriptions(docs)
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
            obs[q]=v8.features(q,br,ar,bodyv,bodyn,docs)
    labels={}
    for u,path in paths.items():
        pp=path.replace('\\','/')
        for cls in v7.CLASSES:
            if f'/page-text/{cls}/' in pp:labels[u]=cls;break
    delta={}
    for q,br in body_runs.items():
        uni=docs[q]['uni'];rel={d for d in byuni[uni] if d!=q and labels.get(d)==labels.get(q)}
        rb=v7.recall(br[:30],rel);rh=v7.recall(v7.exact_rescue(br,anchor_runs[q],30),rel)
        delta[q]=rh-rb
    nt=[q for q in body_runs if abs(delta[q])>1e-12]
    X=[obs[q] for q in nt];means,stds=v8.zstats(X)
    pos=[v8.zrow(obs[q],means,stds) for q in nt if delta[q]>0]
    neg=[v8.zrow(obs[q],means,stds) for q in nt if delta[q]<0]
    cp=v8.centroid(pos);cn=v8.centroid(neg)
    def score(q):
        z=v8.zrow(obs[q],means,stds);return v8.d2(z,cn)-v8.d2(z,cp)
    scores={q:score(q) for q in body_runs}
    tau,nact,mean_delta=v8.choose_tau(scores,delta,20)
    payload={
      'name':'G97-Web-v8-WebKB-only-controller',
      'training_scope':['cornell','texas','washington','wisconsin'],
      'feature_order':['margin10','coherence10','anchor_top3_share','anchor_novel_ratio','body_top1_score','body_top10_mean_score','body_top10_score_cv','log_query_token_count','anchor_top1_score','anchor_nonempty_ratio'],
      'means':means,'stds':stds,'positive_centroid':cp,'negative_centroid':cn,
      'threshold_tau':tau,'training_active_at_tau':nact,'training_mean_delta_at_tau':mean_delta,
      'non_tie_training_queries':len(nt),'all_training_queries':len(body_runs),
      'positive_non_ties':sum(delta[q]>0 for q in nt),'negative_non_ties':sum(delta[q]<0 for q in nt),
      'candidate_budget':30,'body_prefix_before_rescue':20,'anchor_offer':10,'min_training_active':20
    }
    Path(a.out).write_text(json.dumps(payload,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps(payload,indent=2,sort_keys=True))
if __name__=='__main__':main()

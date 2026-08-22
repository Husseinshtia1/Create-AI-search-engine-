#!/usr/bin/env python3
"""Post-result DEVELOPMENT diagnostics for G97-Web v6.
No new ranking method is introduced. Measures complementarity/noise only.
"""
import argparse, collections, importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v6',HERE/'g97_webv6_rescue.py')
v6=importlib.util.module_from_spec(spec);spec.loader.exec_module(v6)
KS=(10,20,50)

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',default='diagnostic.tsv');args=p.parse_args()
    docs,paths=v6.load_pages(args.root)
    bodyv,bodyn=v6.build_tfidf({d:x['text'] for d,x in docs.items()})
    weighted,out,occ=v6.external_descriptions(docs)
    anchv,anchn=v6.build_weighted_anchor_vectors(weighted,docs)
    byuni=collections.defaultdict(list)
    for d,x in docs.items():byuni[x['uni']].append(d)

    # Rankings are generated before labels are read.
    body_runs={};anchor_runs={}
    for uni,ids in byuni.items():
        for q in ids:
            bs={};ans={}
            for d in ids:
                if d==q:continue
                s=v6.cos(bodyv[q],bodyv[d],bodyn[q],bodyn[d])
                if s>0:bs[d]=s
                sa=v6.cos(bodyv[q],anchv[d],bodyn[q],anchn[d])
                if sa>0:ans[d]=sa
            body_runs[q]=v6.rank(bs);anchor_runs[q]=v6.rank(ans)

    labels={}
    for u,path in paths.items():
        pp=path.replace('\\','/')
        for cls in v6.CLASSES:
            if f'/page-text/{cls}/' in pp:labels[u]=cls;break

    stats={k:collections.Counter() for k in KS};queries=0
    for q,br in body_runs.items():
        rel={d for d in byuni[docs[q]['uni']] if d!=q and labels.get(d)==labels.get(q)}
        if not rel:continue
        queries+=1;ar=anchor_runs[q]
        for k in KS:
            aset=set(ar[:k]);b=set(br[:k]);b2=set(br[:2*k])
            outside=aset-b2
            good=outside&rel
            s=stats[k]
            s['anchor_candidates']+=len(aset)
            s['outside_body2k']+=len(outside)
            s['deep_relevant']+=len(good)
            s['queries_any_deep']+=int(bool(good))
            s['queries_anchor_nonempty']+=int(bool(aset))
            s['outside_bodyk_relevant']+=len((aset-b)&rel)
            s['body2k_relevant']+=len(b2&rel)
    with open(args.out,'w') as f:
        f.write('K\tqueries\tP(any_deep_rescue)\tNovelAnchorCandidatesPerQuery\tNovelAnchorPrecision\tDeepRelevantPerQuery\tOutsideBodyKRelevantPerQuery\tBody2KRelevantPerQuery\n')
        for k in KS:
            s=stats[k];n=queries
            nov=s['outside_body2k'];prec=s['deep_relevant']/nov if nov else 0.0
            f.write(f'{k}\t{n}\t{s["queries_any_deep"]/n:.6f}\t{nov/n:.6f}\t{prec:.6f}\t{s["deep_relevant"]/n:.6f}\t{s["outside_bodyk_relevant"]/n:.6f}\t{s["body2k_relevant"]/n:.6f}\n')
    print('POST-RESULT DEVELOPMENT DIAGNOSTIC ONLY')
    print('pages',len(docs),'targets_with_anchor_text',len(weighted),'queries',queries)
    print(open(args.out).read())
if __name__=='__main__':main()

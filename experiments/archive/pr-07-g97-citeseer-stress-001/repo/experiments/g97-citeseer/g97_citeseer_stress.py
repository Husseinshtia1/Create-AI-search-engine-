#!/usr/bin/env python3
import argparse, math, random
import numpy as np

def load_content(path):
    ids=[]; X=[]; labels=[]
    for line in open(path,encoding='utf-8',errors='replace'):
        p=line.split()
        if not p: continue
        ids.append(p[0]); X.append([float(x) for x in p[1:-1]]); labels.append(p[-1])
    return ids,np.asarray(X,dtype=np.float32),labels

def load_edges(path,id_to_i):
    n=len(id_to_i); adj=[set() for _ in range(n)]
    for line in open(path,encoding='utf-8',errors='replace'):
        p=line.split()
        if len(p)<2 or p[0] not in id_to_i or p[1] not in id_to_i: continue
        cited=id_to_i[p[0]]; citing=id_to_i[p[1]]
        if cited==citing: continue
        # frozen relational corroboration uses adjacency, not direction-specific prestige
        adj[cited].add(citing); adj[citing].add(cited)
    return adj

def authority(adj,eps=.08,iters=50):
    n=len(adj); a=np.full(n,1/n,dtype=np.float64)
    for _ in range(iters):
        z=np.full(n,eps/n,dtype=np.float64); dangling=0.0
        for i,ns in enumerate(adj):
            if ns:
                share=(1-eps)*a[i]/len(ns)
                for j in ns:z[j]+=share
            else:dangling+=(1-eps)*a[i]
        if dangling:z+=dangling/n
        a=z/z.sum()
    return a/(a.max() if a.max()>0 else 1)

def ap(r,rel):
    h=0;s=0.0
    for k,d in enumerate(r,1):
        if d in rel:h+=1;s+=h/k
    return s/len(rel) if rel else 0.0

def p10(r,rel):return sum(d in rel for d in r[:10])/10

def rr(r,rel):
    for k,d in enumerate(r,1):
        if d in rel:return 1/k
    return 0.0

def ndcg(r,rel,k=10):
    dcg=sum((1.0 if d in rel else 0.0)/math.log2(i+2) for i,d in enumerate(r[:k])); ideal=sum(1.0/math.log2(i+2) for i in range(min(k,len(rel))))
    return dcg/ideal if ideal else 0.0

def bootstrap(a,b,n=5000,seed=1996):
    d=np.asarray(b)-np.asarray(a); rng=random.Random(seed); vals=[]; m=len(d)
    for _ in range(n):vals.append(sum(d[rng.randrange(m)] for __ in range(m))/m)
    vals.sort();return float(d.mean()),float(vals[int(.025*(n-1))]),float(vals[int(.975*(n-1))]),int((d>1e-15).sum()),int((d<-1e-15).sum()),int((abs(d)<=1e-15).sum())

def main():
    p=argparse.ArgumentParser();p.add_argument('--content',required=True);p.add_argument('--cites',required=True);p.add_argument('--out',default='results.tsv');a=p.parse_args()
    ids,X,labels=load_content(a.content); n=len(ids); idx={x:i for i,x in enumerate(ids)}; adj=load_edges(a.cites,idx)
    norms=np.linalg.norm(X,axis=1); norms[norms==0]=1; Xn=X/norms[:,None]
    sim=Xn@Xn.T
    degree=np.asarray([len(s) for s in adj],dtype=np.float64);degree/=degree.max() if degree.max()>0 else 1
    auth=authority(adj);lam=.50;names=['T0_TEXT','T1_GLOBAL_DEGREE','T2_GLOBAL_AUTH','T3_LOCAL_CITATION']
    perq={z:{m:[] for m in ['AP','P10','nDCG10','MRR']} for z in names}
    for q in range(n):
        base=sim[q].astype(np.float64).copy();base[q]=-1
        top10=np.argsort(-base)[:10];local=np.zeros(n,dtype=np.float64);mx=max(float(base[top10[0]]),1e-12)
        for s in top10:
            conf=max(0.0,float(base[s]))/mx
            for d in adj[s]:
                if d!=q and base[d]>0:local[d]+=conf
        local=local/(1+local)
        scores={'T0_TEXT':base,'T1_GLOBAL_DEGREE':base*(1+lam*degree),'T2_GLOBAL_AUTH':base*(1+lam*auth),'T3_LOCAL_CITATION':base*(1+lam*local)}
        rel={i for i,l in enumerate(labels) if l==labels[q] and i!=q}
        for name,s in scores.items():
            r=[i for i in np.argsort(-s) if i!=q]
            perq[name]['AP'].append(ap(r,rel));perq[name]['P10'].append(p10(r,rel));perq[name]['nDCG10'].append(ndcg(r,rel));perq[name]['MRR'].append(rr(r,rel))
    with open(a.out,'w') as f:
        f.write('variant\tMAP\tP@10\tnDCG@10\tMRR\tAP_delta\tCI95_low\tCI95_high\twins\tlosses\tties\n');baseap=perq['T0_TEXT']['AP']
        for name in names:
            d,lo,hi,w,l,t=(0,0,0,0,0,0) if name=='T0_TEXT' else bootstrap(baseap,perq[name]['AP'])
            vals=[float(np.mean(perq[name][m])) for m in ['AP','P10','nDCG10','MRR']]
            f.write(f'{name}\t{vals[0]:.6f}\t{vals[1]:.6f}\t{vals[2]:.6f}\t{vals[3]:.6f}\t{d:.6f}\t{lo:.6f}\t{hi:.6f}\t{w}\t{l}\t{t}\n')
    print('papers',n,'features',X.shape[1],'classes',len(set(labels)),'undirected_edges',sum(len(x) for x in adj)//2)
    print(open(a.out).read())
if __name__=='__main__':main()

#!/usr/bin/env python3
import argparse, math, random
import numpy as np

def load_content(path):
    ids=[]; X=[]; labels=[]
    for line in open(path,encoding='utf-8',errors='replace'):
        p=line.split()
        if len(p)<3: continue
        ids.append(p[0]); X.append([float(x) for x in p[1:-1]]); labels.append(p[-1])
    return ids,np.asarray(X,dtype=np.float32),labels

def load_edges(path,id_to_i):
    n=len(id_to_i); adj=[set() for _ in range(n)]
    for line in open(path,encoding='utf-8',errors='replace'):
        p=line.split()
        if len(p)<2 or p[0] not in id_to_i or p[1] not in id_to_i: continue
        a=id_to_i[p[0]]; b=id_to_i[p[1]]
        if a==b: continue
        adj[a].add(b); adj[b].add(a)
    return adj

def authority(adj,eps=.08,iters=50):
    n=len(adj); a=np.full(n,1/n,dtype=np.float64)
    for _ in range(iters):
        z=np.full(n,eps/n,dtype=np.float64); dang=0.0
        for i,ns in enumerate(adj):
            if ns:
                sh=(1-eps)*a[i]/len(ns)
                for j in ns:z[j]+=sh
            else:dang+=(1-eps)*a[i]
        if dang:z+=dang/n
        z/=z.sum(); a=z
    return a/(a.max() if a.max()>0 else 1)

def ap(r,rel):
    if not rel:return 0.0
    h=0;s=0.0
    for k,d in enumerate(r,1):
        if d in rel:h+=1;s+=h/k
    return s/len(rel)
def pat(r,rel,k):return sum(d in rel for d in r[:k])/k
def rr(r,rel):
    for k,d in enumerate(r,1):
        if d in rel:return 1/k
    return 0.0
def ndcg(r,rel,k=10):
    dcg=sum((1.0 if d in rel else 0.0)/math.log2(i+2) for i,d in enumerate(r[:k]))
    ideal=sum(1.0/math.log2(i+2) for i in range(min(k,len(rel))))
    return dcg/ideal if ideal else 0.0

def bootstrap(base,test,n=10000,seed=1996):
    ds=np.asarray(test)-np.asarray(base); rng=random.Random(seed); vals=[]; m=len(ds)
    for _ in range(n): vals.append(sum(ds[rng.randrange(m)] for __ in range(m))/m)
    vals.sort(); return float(ds.mean()),float(vals[int(.025*(n-1))]),float(vals[int(.975*(n-1))]),int((ds>1e-15).sum()),int((ds<-1e-15).sum()),int((abs(ds)<=1e-15).sum())

def main():
    p=argparse.ArgumentParser();p.add_argument('--content',required=True);p.add_argument('--cites',required=True);p.add_argument('--out',default='results.tsv');a=p.parse_args()
    ids,X,labels=load_content(a.content); n=len(ids); idx={x:i for i,x in enumerate(ids)}; adj=load_edges(a.cites,idx)
    norms=np.linalg.norm(X,axis=1); norms[norms==0]=1; Xn=X/norms[:,None]
    degree=np.asarray([len(s) for s in adj],dtype=np.float64); degree/=degree.max() if degree.max()>0 else 1
    auth=authority(adj); lam=.50
    names=['T0_TEXT','T1_GLOBAL_DEGREE','T2_GLOBAL_AUTH','T3_LOCAL_RAW','T4_LOCAL_QUALIFIED']
    pq={z:{'AP':[],'P10':[],'nDCG10':[],'MRR':[]} for z in names}
    edge_same=sum(1 for i,ns in enumerate(adj) for j in ns if i<j and labels[i]==labels[j]); edges=sum(len(s) for s in adj)//2
    for q in range(n):
        base=Xn@Xn[q]; base[q]=-1
        top10=np.argsort(-base)[:10]; mx=max(float(base[top10[0]]),1e-12)
        raw=np.zeros(n,dtype=np.float64); qual=np.zeros(n,dtype=np.float64)
        for s in top10:
            conf=max(0.0,float(base[s]))/mx
            for d in adj[s]:
                if d==q or base[d]<=0: continue
                raw[d]+=conf
                pair=max(0.0,float(Xn[s]@Xn[d]))
                qual[d]+=conf*pair
        raw=raw/(1+raw); qual=qual/(1+qual)
        scores={
            'T0_TEXT':base.copy(),
            'T1_GLOBAL_DEGREE':base*(1+lam*degree),
            'T2_GLOBAL_AUTH':base*(1+lam*auth),
            'T3_LOCAL_RAW':base*(1+lam*raw),
            'T4_LOCAL_QUALIFIED':base*(1+lam*qual),
        }
        rel={i for i,l in enumerate(labels) if l==labels[q] and i!=q}
        for z,s in scores.items():
            r=[i for i in np.argsort(-s) if i!=q]
            pq[z]['AP'].append(ap(r,rel));pq[z]['P10'].append(pat(r,rel,10));pq[z]['nDCG10'].append(ndcg(r,rel));pq[z]['MRR'].append(rr(r,rel))
    with open(a.out,'w') as f:
        f.write('variant\tMAP\tP@10\tnDCG@10\tMRR\tAP_delta\tCI95_low\tCI95_high\twins\tlosses\tties\n')
        b=pq['T0_TEXT']['AP']
        for z in names:
            vals=[np.mean(pq[z][m]) for m in ['AP','P10','nDCG10','MRR']]
            st=(0,0,0,0,0,0) if z=='T0_TEXT' else bootstrap(b,pq[z]['AP'])
            f.write(z+'\t'+'\t'.join(f'{v:.6f}' for v in vals)+'\t'+'\t'.join(str(v) if isinstance(v,int) else f'{v:.6f}' for v in st)+'\n')
    print('pages',n,'features',X.shape[1],'classes',len(set(labels)),'edges',edges,'edge_label_homophily',edge_same/edges if edges else 0)
    print(open(a.out).read())
if __name__=='__main__':main()

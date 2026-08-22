#!/usr/bin/env python3
import argparse, math, random
import numpy as np

def load_nodes(path):
    ids=[]; X=[]; labels=[]
    with open(path,encoding='utf-8',errors='replace') as f:
        next(f,None)
        for line in f:
            line=line.strip()
            if not line: continue
            p=line.split('\t')
            if len(p)<3: continue
            ids.append(int(p[0])); X.append([float(v) for v in p[1].split(',')]); labels.append(int(p[2]))
    return ids,np.asarray(X,dtype=np.float32),labels

def load_edges(path,id_to_i):
    n=len(id_to_i); adj=[set() for _ in range(n)]
    with open(path,encoding='utf-8',errors='replace') as f:
        next(f,None)
        for line in f:
            p=line.split()
            if len(p)<2: continue
            a0,b0=int(p[0]),int(p[1])
            if a0 not in id_to_i or b0 not in id_to_i: continue
            a=id_to_i[a0]; b=id_to_i[b0]
            if a==b: continue
            adj[a].add(b); adj[b].add(a)
    return adj

def authority(adj,eps=.08,iters=50):
    n=len(adj); a=np.full(n,1/n,dtype=np.float64)
    for _ in range(iters):
        nxt=np.full(n,eps/n,dtype=np.float64); dangling=0.0
        for i,ns in enumerate(adj):
            if ns:
                sh=(1-eps)*a[i]/len(ns)
                for j in ns:nxt[j]+=sh
            else:dangling+=(1-eps)*a[i]
        if dangling:nxt+=dangling/n
        nxt/=nxt.sum(); a=nxt
    m=a.max(); return a/(m if m>0 else 1)

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

def bootstrap(base,test,n=5000,seed=1996):
    ds=np.asarray(test)-np.asarray(base); rng=random.Random(seed); vals=[]; m=len(ds)
    for _ in range(n): vals.append(sum(ds[rng.randrange(m)] for __ in range(m))/m)
    vals.sort(); return float(ds.mean()),float(vals[int(.025*(n-1))]),float(vals[int(.975*(n-1))]),int((ds>1e-15).sum()),int((ds<-1e-15).sum()),int((abs(ds)<=1e-15).sum())

def run_one(name,node_path,edge_path):
    ids,X,labels=load_nodes(node_path); n=len(ids); id_to_i={x:i for i,x in enumerate(ids)}; adj=load_edges(edge_path,id_to_i)
    norms=np.linalg.norm(X,axis=1); norms[norms==0]=1; Xn=X/norms[:,None]
    deg=np.asarray([len(s) for s in adj],dtype=np.float64); deg/=deg.max() if deg.max()>0 else 1
    auth=authority(adj); lam=.50
    names=['T0_TEXT','T1_GLOBAL_DEGREE','T2_GLOBAL_AUTH','T3_LOCAL_LINK']
    pq={z:{'AP':[],'P10':[],'nDCG10':[],'MRR':[]} for z in names}
    text_h=[]; local_pool_h=[]
    for q in range(n):
        base=Xn@Xn[q]; base[q]=-1
        top10=np.argsort(-base)[:10]; text_h.append(sum(labels[s]==labels[q] for s in top10)/10)
        local=np.zeros(n,dtype=np.float64); mx=max(float(base[top10[0]]),1e-12); pool=set()
        for s in top10:
            conf=max(0.0,float(base[s]))/mx
            for d in adj[s]:
                if d!=q and base[d]>0:
                    local[d]+=conf; pool.add(d)
        local_pool_h.append(sum(labels[d]==labels[q] for d in pool)/len(pool) if pool else 0.0)
        local=local/(1+local)
        scores={'T0_TEXT':base.copy(),'T1_GLOBAL_DEGREE':base*(1+lam*deg),'T2_GLOBAL_AUTH':base*(1+lam*auth),'T3_LOCAL_LINK':base*(1+lam*local)}
        rel={i for i,l in enumerate(labels) if l==labels[q] and i!=q}
        for z,s in scores.items():
            r=[i for i in np.argsort(-s) if i!=q]
            pq[z]['AP'].append(ap(r,rel));pq[z]['P10'].append(pat(r,rel,10));pq[z]['nDCG10'].append(ndcg(r,rel));pq[z]['MRR'].append(rr(r,rel))
    pairs=[]
    for a,ns in enumerate(adj):
        for b in ns:
            if a<b:pairs.append((a,b))
    edge_h=sum(labels[a]==labels[b] for a,b in pairs)/len(pairs) if pairs else 0.0
    return {'name':name,'n':n,'features':X.shape[1],'classes':len(set(labels)),'edges':len(pairs),'pq':pq,'edge_h':edge_h,'text_h':float(np.mean(text_h)),'local_pool_h':float(np.mean(local_pool_h))}

def main():
    a=argparse.ArgumentParser();a.add_argument('--root',required=True);a.add_argument('--out',default='results.tsv');x=a.parse_args()
    runs=[]
    for ds in ['cornell','texas','wisconsin']:
        runs.append(run_one(ds,f'{x.root}/{ds}/out1_node_feature_label.txt',f'{x.root}/{ds}/out1_graph_edges.txt'))
    variants=['T0_TEXT','T1_GLOBAL_DEGREE','T2_GLOBAL_AUTH','T3_LOCAL_LINK']
    with open(x.out,'w') as f:
        f.write('dataset\tvariant\tMAP\tP@10\tnDCG@10\tMRR\tAP_delta\tCI95_low\tCI95_high\twins\tlosses\tties\n')
        for R in runs:
            b=R['pq']['T0_TEXT']['AP']
            for z in variants:
                vals=[np.mean(R['pq'][z][m]) for m in ['AP','P10','nDCG10','MRR']]
                stats=(0,0,0,0,0,0) if z=='T0_TEXT' else bootstrap(b,R['pq'][z]['AP'])
                f.write(R['name']+'\t'+z+'\t'+'\t'.join(f'{v:.6f}' for v in vals)+'\t'+'\t'.join(str(v) if isinstance(v,int) else f'{v:.6f}' for v in stats)+'\n')
        for z in variants:
            pooled={m:sum((R['pq'][z][m] for R in runs),[]) for m in ['AP','P10','nDCG10','MRR']}
            vals=[np.mean(pooled[m]) for m in ['AP','P10','nDCG10','MRR']]
            b=sum((R['pq']['T0_TEXT']['AP'] for R in runs),[]); stats=(0,0,0,0,0,0) if z=='T0_TEXT' else bootstrap(b,pooled['AP'])
            f.write('POOLED\t'+z+'\t'+'\t'.join(f'{v:.6f}' for v in vals)+'\t'+'\t'.join(str(v) if isinstance(v,int) else f'{v:.6f}' for v in stats)+'\n')
    for R in runs:
        print(R['name'],'pages',R['n'],'features',R['features'],'classes',R['classes'],'edges',R['edges'],
              'edge_label_homophily',f"{R['edge_h']:.6f}",'text_top10_label_homophily',f"{R['text_h']:.6f}",'local_pool_label_homophily',f"{R['local_pool_h']:.6f}")
    print(open(x.out).read())
if __name__=='__main__':main()

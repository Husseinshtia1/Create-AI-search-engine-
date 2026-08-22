#!/usr/bin/env python3
import argparse, csv, gzip, hashlib, html, json, re, sys
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

N_SAMPLE=20000
MIN_INBOUND_TARGETS=1000
WS=re.compile(r'\s+')

def uidstr(x): return str(x).strip()

def weburl(url):
    s=(url or '').strip()
    if not s: return ''
    p=urlsplit(s)
    if p.scheme: return s
    if s.startswith('//'): return 'http:'+s
    return 'http://'+s

def hostkey(url):
    try:
        p=urlsplit(weburl(url))
        if p.scheme.lower() not in ('http','https'): return None
        h=(p.hostname or '').lower().rstrip('.')
        if h.startswith('www.'): h=h[4:]
        return h or None
    except Exception:
        return None

def choose_uids(path):
    vals=[]
    with open(path,encoding='utf-8') as f:
        for line in f:
            u=uidstr(line)
            if u:
                vals.append((hashlib.sha1(u.encode('utf-8')).digest(),u))
    vals.sort(key=lambda x:(x[0],x[1]))
    return [u for _,u in vals[:N_SAMPLE]],len(vals)

def load_urls(path,selected):
    urls={}
    with gzip.open(path,'rt',encoding='utf-8',errors='replace',newline='') as f:
        r=csv.DictReader(f)
        if not r.fieldnames or 'uid' not in r.fieldnames or 'url' not in r.fieldnames:
            raise RuntimeError(f'unexpected curlie_filtered fields: {r.fieldnames}')
        for row in r:
            u=uidstr(row.get('uid',''))
            if u in selected and u not in urls:
                urls[u]=(row.get('url') or '').strip()
    return urls

def verify_labels(path,selected):
    seen=set()
    with gzip.open(path,'rt',encoding='utf-8',errors='replace') as f:
        for line in f:
            if not line.strip(): continue
            x=json.loads(line)
            u=uidstr(x.get('uid',''))
            if u in selected: seen.add(u)
    return seen

class PageParser(HTMLParser):
    def __init__(self,base_url,host_to_uid,source_uid):
        super().__init__(convert_charrefs=True)
        self.base=weburl(base_url); self.host_to_uid=host_to_uid; self.source=source_uid
        self.skip=0; self.text=[]; self.a_href=None; self.a_text=[]; self.anchors=defaultdict(list)
    def handle_starttag(self,tag,attrs):
        tag=tag.lower()
        if tag in ('script','style','noscript'): self.skip+=1
        if self.skip: return
        if tag=='a':
            d=dict(attrs); self.a_href=d.get('href'); self.a_text=[]
    def handle_endtag(self,tag):
        tag=tag.lower()
        if tag in ('script','style','noscript'):
            if self.skip: self.skip-=1
            return
        if self.skip: return
        if tag=='a' and self.a_href:
            try: dest=urljoin(self.base,self.a_href)
            except Exception: dest=''
            hk=hostkey(dest); target=self.host_to_uid.get(hk)
            if target and target!=self.source:
                t=WS.sub(' ',' '.join(self.a_text)).strip()
                if t: self.anchors[target].append(t)
            self.a_href=None; self.a_text=[]
    def handle_data(self,data):
        if self.skip: return
        if data and data.strip():
            self.text.append(data)
            if self.a_href is not None: self.a_text.append(data)

def parse_record(obj):
    u=uidstr(obj.get('uid',''))
    raw=obj.get('html','')
    if raw is None: raw=''
    return u,str(raw)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--test-uid',required=True); ap.add_argument('--urls',required=True)
    ap.add_argument('--classes',required=True); ap.add_argument('--outdir',required=True)
    args=ap.parse_args(); out=Path(args.outdir); out.mkdir(parents=True,exist_ok=True)

    chosen,n_test=choose_uids(args.test_uid); selected=set(chosen)
    if len(chosen)!=N_SAMPLE: raise SystemExit(f'FAIL selected={len(chosen)} expected={N_SAMPLE}')
    urls=load_urls(args.urls,selected); label_seen=verify_labels(args.classes,selected)
    missing_urls=selected-set(urls); missing_labels=selected-label_seen

    # Canonical host map; ambiguous hosts are deliberately unaddressable.
    buckets=defaultdict(list)
    for u,url in urls.items():
        hk=hostkey(url)
        if hk: buckets[hk].append(u)
    host_to_uid={h:us[0] for h,us in buckets.items() if len(us)==1}
    ambiguous={h:us for h,us in buckets.items() if len(us)>1}

    with open(out/'selected_uids.txt','w') as f:
        for u in chosen: f.write(u+'\n')
    with open(out/'manifest.tsv','w') as f:
        f.write('uid\tsha1\turl\tcanonical_host\n')
        for u in chosen:
            f.write(f"{u}\t{hashlib.sha1(u.encode()).hexdigest()}\t{urls.get(u,'')}\t{hostkey(urls.get(u,'')) or ''}\n")

    extracted=set(); inbound_targets=set(); edges=set(); total_anchor_strings=0
    gzout=gzip.open(out/'selected_documents.jsonl.gz','wt',encoding='utf-8')
    for line in sys.stdin:
        if not line.strip(): continue
        try: obj=json.loads(line)
        except Exception: continue
        u,raw=parse_record(obj)
        if u not in selected: continue
        base=urls.get(u,'')
        p=PageParser(base,host_to_uid,u)
        try: p.feed(raw); p.close()
        except Exception: pass
        body=WS.sub(' ',' '.join(p.text)).strip()
        compact={}
        for t,strings in p.anchors.items():
            uniq=[]; seen=set()
            for s in strings:
                s=WS.sub(' ',s).strip()
                if s and s not in seen: seen.add(s); uniq.append(s)
            if uniq:
                compact[t]=uniq; edges.add((u,t)); inbound_targets.add(t); total_anchor_strings+=len(uniq)
        gzout.write(json.dumps({'uid':u,'body':body,'anchors':compact},ensure_ascii=False)+'\n')
        extracted.add(u)
    gzout.close()

    missing_html=selected-extracted
    feasible=(not missing_urls and not missing_labels and not missing_html and len(inbound_targets)>=MIN_INBOUND_TARGETS)
    status='FEASIBLE_FOR_FROZEN_RETRIEVAL' if feasible else 'INSUFFICIENT_INTERNAL_ANCHOR_GRAPH_OR_MISSING_DATA'
    stats={
      'status':status,'published_test_uids':n_test,'selected_uids':len(selected),
      'urls_present':len(urls),'labels_present':len(label_seen),'html_present':len(extracted),
      'missing_urls':len(missing_urls),'missing_labels':len(missing_labels),'missing_html':len(missing_html),
      'unique_canonical_hosts':len(host_to_uid),'ambiguous_hosts':len(ambiguous),
      'directed_internal_edges':len(edges),'distinct_inbound_targets':len(inbound_targets),
      'anchor_strings':total_anchor_strings,'required_inbound_targets':MIN_INBOUND_TARGETS
    }
    (out/'feasibility.json').write_text(json.dumps(stats,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps(stats,indent=2,sort_keys=True))
    if not feasible: raise SystemExit(3)

if __name__=='__main__': main()

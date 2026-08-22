#!/usr/bin/env python3
import argparse,csv,gzip,html,json,re,sys
from collections import defaultdict
from urllib.parse import urljoin,urlsplit

A_RE=re.compile(r'(?is)<a\s+[^>]*href\s*=\s*(["\']?)([^"\'\s>]+)\1[^>]*>(.*?)</a\s*>')
TAG_RE=re.compile(r'(?is)<[^>]+>')
WS=re.compile(r'\s+')

def weburl(s):
    s=(s or '').strip()
    if not s:return ''
    p=urlsplit(s)
    if p.scheme:return s
    if s.startswith('//'):return 'http:'+s
    return 'http://'+s

def hostkey(s):
    try:
        p=urlsplit(weburl(s))
        if p.scheme.lower() not in ('http','https'):return None
        h=(p.hostname or '').lower().rstrip('.')
        if h.startswith('www.'):h=h[4:]
        return h or None
    except:return None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--urls',required=True);ap.add_argument('--out',required=True);args=ap.parse_args()
    urls={}
    with gzip.open(args.urls,'rt',encoding='utf-8',errors='replace',newline='') as f:
        r=csv.DictReader(f)
        assert r.fieldnames and 'uid' in r.fieldnames and 'url' in r.fieldnames,r.fieldnames
        for row in r:
            u=str(row.get('uid','')).strip(); url=(row.get('url') or '').strip()
            if u and url and u not in urls:urls[u]=url
    buckets=defaultdict(list)
    for u,url in urls.items():
        h=hostkey(url)
        if h:buckets[h].append(u)
    host_to_uid={h:v[0] for h,v in buckets.items() if len(v)==1}
    ambiguous=sum(1 for v in buckets.values() if len(v)>1)

    html_seen=set(); inbound=set(); pages_with_internal_out=0; edge_count=0; anchor_strings=0
    for line in sys.stdin:
        if not line.strip():continue
        try:o=json.loads(line)
        except:continue
        u=str(o.get('uid','')).strip(); raw=o.get('html','') or ''
        if not u or u not in urls:continue
        html_seen.add(u); base=weburl(urls[u]); targets=set(); strings=0
        for m in A_RE.finditer(str(raw)):
            href=html.unescape(m.group(2) or '').strip()
            if not href:continue
            try:dest=urljoin(base,href)
            except:continue
            t=host_to_uid.get(hostkey(dest))
            if not t or t==u:continue
            targets.add(t)
            at=WS.sub(' ',html.unescape(TAG_RE.sub(' ',m.group(3) or ''))).strip()
            if at:strings+=1
        if targets:
            pages_with_internal_out+=1;edge_count+=len(targets);inbound.update(targets);anchor_strings+=strings
    valid_html=sum(1 for u in html_seen if u in urls)
    stats={
      'status':'POST_FAILURE_DIAGNOSTIC_ONLY',
      'url_records':len(urls),'unique_canonical_hosts':len(host_to_uid),'ambiguous_hosts':ambiguous,
      'html_records_seen':valid_html,'directed_internal_edges':edge_count,
      'pages_with_internal_outlinks':pages_with_internal_out,'distinct_inbound_targets':len(inbound),
      'inbound_target_fraction_of_html':(len(inbound)/valid_html if valid_html else 0.0),
      'anchor_strings_on_internal_links':anchor_strings
    }
    with open(args.out,'w') as f:json.dump(stats,f,indent=2,sort_keys=True)
    print(json.dumps(stats,indent=2,sort_keys=True))
if __name__=='__main__':main()

from __future__ import annotations
import argparse,json
from .models import Document
from .search import SearchEngine
from .controller import InterventionController
from .server import serve
def load_jsonl(path):
    out=[]
    for line in open(path,encoding='utf-8'):
        if line.strip():out.append(Document(**json.loads(line)))
    return out
def main():
    p=argparse.ArgumentParser(prog='g97');p.add_argument('docs');p.add_argument('--controller');p.add_argument('--method',choices=['tfidf','c96'],default='tfidf');sub=p.add_subparsers(dest='cmd',required=True);s=sub.add_parser('search');s.add_argument('query');s.add_argument('-k',type=int,default=10);h=sub.add_parser('serve');h.add_argument('--host',default='127.0.0.1');h.add_argument('--port',type=int,default=8080);a=p.parse_args();docs=load_jsonl(a.docs);ctrl=InterventionController.from_json(a.controller) if a.controller else None;eng=SearchEngine(docs,ctrl,a.method)
    if a.cmd=='search':
        hits,state,score=eng.search(a.query,a.k);print(json.dumps({'controller_score':score,'state':state.__dict__,'hits':[h.__dict__ for h in hits]},ensure_ascii=False,indent=2))
    else:serve(eng,a.host,a.port)
if __name__=='__main__':main()

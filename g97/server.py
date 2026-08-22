from __future__ import annotations
import html,json
from http.server import BaseHTTPRequestHandler,HTTPServer
from urllib.parse import urlsplit,parse_qs
class SearchHandler(BaseHTTPRequestHandler):
    engine=None
    def do_GET(self):
        p=urlsplit(self.path)
        if p.path=='/health':return self._json({'ok':True,'docs':len(self.engine.docs)})
        if p.path not in ('/','/search'):self.send_error(404);return
        q=parse_qs(p.query).get('q',[''])[0]
        if p.path=='/' and not q:return self._html('<form action="/search"><input name="q" autofocus><button>Search</button></form>')
        hits,state,cs=self.engine.search(q,k=10);rows=''.join(f'<li><a href="{html.escape(h.url)}">{html.escape(h.title)}</a><br>{html.escape(h.snippet)}<small> score={h.score:.4f}</small></li>' for h in hits);self._html(f'<form action="/search"><input name="q" value="{html.escape(q)}"><button>Search</button></form><ol>{rows}</ol>')
    def _json(self,x):b=json.dumps(x).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    def _html(self,s):b=s.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
def serve(engine,host='127.0.0.1',port=8080):SearchHandler.engine=engine;HTTPServer((host,port),SearchHandler).serve_forever()

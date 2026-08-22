from __future__ import annotations
from html.parser import HTMLParser
from urllib.parse import urljoin
from .models import Document

class HTMLTextParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True); self.base_url=base_url; self.skip=0; self.text=[]; self.title_parts=[]; self.in_title=False; self.a_href=None; self.a_text=[]; self.links=[]
    def handle_starttag(self,tag,attrs):
        tag=tag.lower()
        if tag in {"script","style","noscript"}: self.skip+=1; return
        if self.skip:return
        if tag=="title": self.in_title=True
        if tag=="a": self.a_href=dict(attrs).get("href"); self.a_text=[]
    def handle_endtag(self,tag):
        tag=tag.lower()
        if tag in {"script","style","noscript"}:
            if self.skip:self.skip-=1
            return
        if self.skip:return
        if tag=="title":self.in_title=False
        if tag=="a" and self.a_href:
            anchor=" ".join(self.a_text).strip()
            try: dest=urljoin(self.base_url,self.a_href)
            except Exception: dest=""
            if dest:self.links.append((dest,anchor))
            self.a_href=None;self.a_text=[]
    def handle_data(self,data):
        if self.skip or not data or not data.strip():return
        s=" ".join(data.split());self.text.append(s)
        if self.in_title:self.title_parts.append(s)
        if self.a_href is not None:self.a_text.append(s)

def parse_html(doc_id: str,url: str,raw_html: str,**kw)->Document:
    p=HTMLTextParser(url)
    try:p.feed(raw_html);p.close()
    except Exception:pass
    return Document(doc_id=doc_id,url=url,title=" ".join(p.title_parts).strip(),body=" ".join(p.text).strip(),outlinks=p.links,**kw)

from __future__ import annotations
from .text import normalize
def snippet(text:str,query:str,width:int=220)->str:
    if not text:return ""
    low=text.lower();terms=[t for t in normalize(query) if t];positions=[low.find(t) for t in terms if low.find(t)>=0];p=min(positions) if positions else 0;start=max(0,p-width//3);end=min(len(text),start+width);s=text[start:end].strip()
    if start:s='…'+s
    if end<len(text):s+='…'
    return s

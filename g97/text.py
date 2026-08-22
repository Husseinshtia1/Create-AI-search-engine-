from __future__ import annotations
import math, re
from collections import Counter

TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
STOP = {"a","an","and","are","as","at","be","by","for","from","has","he","in","is","it","its","of","on","that","the","to","was","were","will","with","or","this","these","those"}

def tokenize(text: str, drop_stop: bool = True):
    toks = [t.lower() for t in TOKEN_RE.findall(text or "")]
    return [t for t in toks if not drop_stop or t not in STOP]

def stem(token: str) -> str:
    t = token
    for suf in ("ization","ational","fulness","iveness","ing","edly","edly","ed","ies","s"):
        if len(t) > len(suf) + 2 and t.endswith(suf):
            if suf == "ies": return t[:-3] + "y"
            return t[:-len(suf)]
    return t

def normalize(text: str): return [stem(t) for t in tokenize(text)]
def tf_log(freq: float) -> float: return 1.0 + math.log(freq) if freq > 0 else 0.0
def counts(text: str): return Counter(normalize(text))

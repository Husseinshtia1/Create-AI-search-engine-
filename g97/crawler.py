from __future__ import annotations
import hashlib,heapq,time
from collections import deque,defaultdict
from urllib import request,robotparser
from .urltools import canonicalize,host_key
from .parser import parse_html
class Frontier:
    def __init__(self):self.discovery=deque();self.retry=[];self.seen=set();self.failures=defaultdict(int)
    def add(self,url):
        u=canonicalize(url)
        if u and u not in self.seen:self.seen.add(u);self.discovery.append(u)
    def fail(self,url,delay=30):
        self.failures[url]+=1
        if self.failures[url]<=3:heapq.heappush(self.retry,(time.time()+delay*self.failures[url],url))
    def pop(self):
        now=time.time()
        if self.retry and self.retry[0][0]<=now:return heapq.heappop(self.retry)[1]
        return self.discovery.popleft() if self.discovery else None
class Crawler:
    def __init__(self,user_agent='G97ResearchBot/0.1',timeout=10,per_host_delay=1.0,max_bytes=2_000_000):self.ua=user_agent;self.timeout=timeout;self.delay=per_host_delay;self.max_bytes=max_bytes;self.robots={};self.host_last={}
    def _allowed(self,url):
        h=host_key(url)
        if h not in self.robots:
            rp=robotparser.RobotFileParser();rp.set_url(f"http://{h}/robots.txt")
            try:rp.read()
            except Exception:pass
            self.robots[h]=rp
        try:return self.robots[h].can_fetch(self.ua,url)
        except Exception:return True
    def fetch(self,url):
        if not self._allowed(url):return None
        h=host_key(url);wait=self.delay-(time.time()-self.host_last.get(h,0))
        if wait>0:time.sleep(wait)
        req=request.Request(url,headers={'User-Agent':self.ua})
        try:
            with request.urlopen(req,timeout=self.timeout) as r:
                data=r.read(self.max_bytes+1)
                if len(data)>self.max_bytes:return None
                ctype=r.headers.get_content_type();charset=r.headers.get_content_charset() or 'utf-8';self.host_last[h]=time.time()
                if ctype!='text/html':return None
                did=hashlib.sha1(canonicalize(url).encode()).hexdigest();return parse_html(did,canonicalize(url),data.decode(charset,errors='replace'),fetched_at=time.time(),status=getattr(r,'status',200),content_type=ctype)
        except Exception:return None

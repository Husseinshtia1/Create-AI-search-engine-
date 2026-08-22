from __future__ import annotations
import json, sqlite3
from pathlib import Path
from .models import Document

class Archive:
    def __init__(self,path:str):
        self.path=path;Path(path).parent.mkdir(parents=True,exist_ok=True);self.db=sqlite3.connect(path)
        self.db.execute("""create table if not exists documents(doc_id text primary key,url text unique,title text,body text,fetched_at real,status integer,content_type text,outlinks text,meta text)""");self.db.commit()
    def put(self,d:Document):
        self.db.execute("insert or replace into documents values(?,?,?,?,?,?,?,?,?)",(d.doc_id,d.url,d.title,d.body,d.fetched_at,d.status,d.content_type,json.dumps(d.outlinks,ensure_ascii=False),json.dumps(d.meta,ensure_ascii=False)));self.db.commit()
    def get(self,doc_id:str):
        row=self.db.execute("select * from documents where doc_id=?",(doc_id,)).fetchone()
        return None if not row else Document(row[0],row[1],row[2],row[3],row[4],row[5],row[6],json.loads(row[7]),json.loads(row[8]))
    def by_url(self,url:str):
        row=self.db.execute("select doc_id from documents where url=?",(url,)).fetchone();return self.get(row[0]) if row else None
    def all(self):
        for (doc_id,) in self.db.execute("select doc_id from documents order by doc_id"):yield self.get(doc_id)
    def __len__(self):return self.db.execute("select count(*) from documents").fetchone()[0]

from g97.models import Document
from g97.index import InvertedIndex,DeltaIndex
from g97.search import SearchEngine
from g97.urltools import canonicalize,host_key
from g97.parser import parse_html

def docs():return [Document('1','http://a.test/','Distributed Systems','distributed database systems and transactions',outlinks=[('http://b.test/','database research')]),Document('2','http://b.test/','Database Research','database research concurrency recovery',outlinks=[]),Document('3','http://c.test/','Cooking','cheese bread recipe kitchen',outlinks=[])]
def test_tfidf_relevance():
    i=InvertedIndex();i.build(docs());assert i.tfidf('distributed database',k=3)[0][0]=='1'
def test_c96_zero_unrelated():
    i=InvertedIndex();i.build(docs());assert not dict(i.c96('quantum',k=3))
def test_delta_visible_then_merge():
    d=DeltaIndex();d.main.build(docs()[:1]);d.add(docs()[1]);assert d.search('concurrency',k=3)[0][0]=='2';d.merge();assert d.search('concurrency',k=3)[0][0]=='2'
def test_parser_anchor():
    x=parse_html('x','http://a.test/','<html><title>T</title><body>Hello <a href="http://b.test/">database research</a></body></html>');assert x.title=='T' and x.outlinks[0][1]=='database research'
def test_url():assert host_key('https://www.Example.com/a')=='example.com' and canonicalize('https://www.Example.com/a#x')=='https://example.com/a'
def test_search_engine():
    e=SearchEngine(docs());hits,state,score=e.search('distributed database',k=2);assert hits[0].doc_id=='1'

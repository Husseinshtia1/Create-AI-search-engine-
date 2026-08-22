# نموذج البيانات وواجهات النظام

## Document
```json
{"doc_id":"stable-id","url":"https://example.org/page","title":"...","body":"...","fetched_at":0,"status":200,"content_type":"text/html","outlinks":[["https://target","anchor text"]],"meta":{}}
```

## SearchHit
`doc_id/url/title/snippet/score/body_score/external_score/graph_score/intervention`.

## QueryState
العشر diagnostics المستخدمة في v7/v8 محفوظة كحقول صريحة للaudit/explainability.

## CLI
`python -m g97 DOCS search QUERY -k 10`

`python -m g97 DOCS serve --port 8080`

## HTTP Reference API
- `GET /health`
- `GET /search?q=...`

## Planned internal interfaces
`DiscoverySource.discover()`، `Fetcher.fetch(url)`، `Parser.parse(bytes,url)`، `Indexer.add/commit/merge()`، `Retriever.search(query,k)`، `EvidenceProvider.score(query,candidates)`، `InterventionPolicy.decide(query_state,actions)`، `Shard.search()`، `Evaluator.evaluate(run,qrels)`.

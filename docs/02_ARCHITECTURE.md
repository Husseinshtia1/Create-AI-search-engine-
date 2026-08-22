# معمارية G97 الحالية

## Discovery Plane
Hyperlinks + direct submission + domain discovery + fast-changing hubs. الهدف خفض `TTQ = T_D + T_F + T_P + T_I + T_S`.

## Crawler
**BFS discovery + Adaptive Refresh + Failure Recovery + Conservative Waste Suppression**. queues مستقلة للاكتشاف، refresh، retries، مع robots/politeness/limits/canonicalization/dedup/resource governor.

## Archive + Parsing
canonical URL، raw/parsed text، title/meta، timestamps/status/content-type، outlinks+anchor، fingerprints/checksums.

## Indexing
`Search = Search(Main) ∪ Search(Delta)` لجعل المستند الجديد searchable فورًا ثم background merge. lexical family تدعم TF-IDF وC96/BM-style؛ لا فائز عالمي مثبت.

## Evidence Roles
- Body Evidence: ما تقوله الصفحة عن نفسها.
- External Description: ما تقوله مصادر أخرى عبر anchor/reference text.
- Relational Corroboration: citation/coupling/co-citation أو relation موثوقة semantics.
- Authority: query-independent prestige؛ ضعيفة/غير مستقرة في تجاربنا.

## Query-local relational corroboration
`S_q = Top10_lexical(q)`
`G_r(d,q)=Σ Confidence(s,q)R_r(s,d)`
`sat(G)=G/(1+G)`
`Score=Text*(1+λ sat(G))`
مع invariant: `Text=0 ⇒ authority/graph cannot manufacture relevance` في قناة corroboration.

نجحت scholarly relations لكنها فشلت على raw web hyperlinks، لذلك لا تُفعل افتراضيًا للويب.

## External Description Rescue
Inbound anchors فهرس منفصل. v6 أثبت complementarity لكنه خسر أمام deeper body عند candidate budget متساوية؛ لذلك لا يستخدم دائمًا.

## Intervention Controller
عشر features observable: margin10, coherence10, anchor top3 share/novelty, body top1/mean/cv, query token count, anchor top1/nonempty ratio. v8 nearest-centroid style score + risk-calibrated threshold. `NoAction` هو default.

## Query processing
`Query → Diagnosis → Select Operator → Ranking`; healthy query تبقى unchanged.

## Snippets
presentation فقط افتراضيًا؛ passage reranking فشلت.

## Serving
`Document Partitioning + Replication + Query Cache + Fresh Delta + Bounded Top-K Fanout`، مع resource governor يخفض maintenance تحت search load.

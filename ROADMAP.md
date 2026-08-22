# خارطة الطريق للوصول إلى الهدف

## الهدف النهائي
محرك بحث ويب كامل على corpus حقيقية ثم crawl حي محدود، مع stack قابل للقياس علميًا وتشغيليًا، مع إبقاء 1996 design constraint في المسار البحثي.

## R0 Release consolidation
[x] code/docs/results unified; [x] runnable reference engine; [x] local invariant/runtime tests 8 passed; [ ] independent external-web validation; [ ] tag after review.

## R1 Lexical Foundation
Exact Porter، TF-IDF، C96/BM، title/body/URL fields، phrase/proximity diagnosis-only، spelling repair، PRF rescue-only، multi-corpus no-regression gate.

## R2 Web Evidence Layer
Inbound-anchor index؛ source/target/anchor/context/outdegree/host metadata؛ فصل external description عن authority؛ relation providers مع semantics/confidence.

## R3 Intervention Controller v2
Actions: NoAction، SpellRepair، Phrase/Proximity، ExternalDescriptionRescue، RelationalCorroboration، PRF، FreshnessBias. لكل action expected gain/risk؛ calibration خارج test corpus.

## R4 Real Web Benchmarks
Curlie frozen validation، WT2g ثم WT10g، spam-aware corpus؛ MAP/nDCG/P/MRR/candidate recall/freshness/spam exposure/bootstrap.

## R5 Production Crawler
Persistent frontier، robots cache، DNS/HTTP pooling، retries/backoff، MIME/size/time limits، redirects، canonicalization، dedup، host budgets، adaptive refresh، direct submission، discovery adapters.

## R6 Durable Index
Append-only delta segments، immutable format، background merge، compression، metadata/anchor/link stores، snapshots/rollback.

## R7 Distributed Serving
Document sharding، replica groups، bounded top-K fanout، query cache، admission control، resource governor، health/failure isolation.

## R8 Spam/Robustness
Source independence، host diversity، scarcity، anomaly statistics، link farms، keyword stuffing، sitewide navigation، duplicates، anchor poisoning.

## R9 Evaluation Harness
Frozen registry، checksums، run manifest، preregistration، statistical reports، automatic failure ledger، strict dev/test config separation.

## R10 Public Prototype
Scoped crawl، 10^4–10^5 pages أولًا، public query endpoint، evidence/intervention explainability، product feedback معزول عن frozen evaluation.

## R11 Scale-out
Millions→tens of millions، crawl workers، segment distribution/replication، query broker، cache tiers، operational dashboards.

## R12 Scientific Comparison
المقارنة التاريخية بعد الاشتقاق فقط؛ PageRank-era systems comparators لا design inputs؛ publication تشمل positive/negative results؛ professional prior-art review قبل أي patent/novelty claim.

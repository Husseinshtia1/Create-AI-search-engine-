# Project History — G97 Search

## 1. Origin of the question

The project began from a deliberately constrained historical thought experiment:

> Google was founded in 1998. If an AI system had access only to knowledge available at the end of 1996, could it reconstruct a search engine that rivaled or exceeded very early Google — not using modern search technology, but by reasoning more aggressively from what was already known?

The point was not to use 2026 search techniques and pretend they existed in 1996. The project therefore adopted a hard design cutoff of **31 December 1996**.

The first focus was Google-like ranking: crawling, indexing, text relevance, hyperlinks, authority and the technologies that made fast discovery/queryability possible.

## 2. Early architecture decomposition

The search engine was decomposed into independent subsystems:

```text
Discovery
 -> Crawl
 -> Repository
 -> Searchable Delta Index
 -> Main Index / Merge
 -> Query Processing
 -> Ranking
 -> Serving
 -> Snippet / Evidence Presentation
```

A Resource Governor was added around serving/background work to protect tail latency under load.

This decomposition was important: ranking alone is not a search engine, and a Google comparison cannot be reduced to PageRank.

## 3. Crawling conclusions

An early idea was to build an aggressively intelligent crawler that predicted which unknown URLs were valuable. Synthetic/runtime reasoning showed this was fragile.

The more robust principle became:

> **Do not replace broad discovery with uncertain prediction. Use intelligence to suppress demonstrated waste.**

The crawler direction therefore became:

```text
broad/BFS-like discovery
+ adaptive refresh
+ trap/duplicate/failure suppression
+ conservative resource allocation
```

A central system metric became **Time To Queryability (TTQ)** — the time from page appearance/discovery until it can actually be retrieved by a user query.

## 4. Indexing and freshness

The project concluded that a 1996-constrained system could use a main index plus a searchable delta structure:

```text
Search(q) = Search(MainIndex, q) U Search(DeltaIndex, q)
```

This permits newly crawled pages to become queryable before a costly global merge. LSM-tree ideas were published in 1996 and therefore fit the historical constraint.

## 5. Query-processing failures and principle

Aggressive default combinations of stemming, title weighting, proximity, pseudo-relevance feedback and spelling/query expansion were not robust.

This produced a recurring principle:

> **Preserve a strong default. Transform a query only when observable evidence indicates a specific problem.**

Examples:

- obvious spelling/OOV failure -> spelling repair;
- explicit phrase -> proximity;
- healthy query -> leave it alone;
- query expansion is not a universal default.

## 6. The graph-ranking phase

The original Google question pushed the project toward graph authority. The important empirical change happened when CACM was reconstructed and tested.

### CACM

A frozen A0–A6 benchmark compared:

- lexical baseline;
- global raw link degree;
- global recursive authority;
- query-local direct-link evidence;
- query-local bibliographic coupling;
- query-local co-citation;
- combined ContextGraph.

The combined query-local model improved MAP from **0.320769 to 0.334000 (+4.12%)**, while global graph variants were slightly worse.

This shifted the working hypothesis from:

```text
text + global prestige
```

to:

```text
query -> lexical seeds -> local relational corroboration -> bounded rerank
```

with the invariant that authority/graph corroboration should not manufacture relevance from nothing.

## 7. Replication and correction

### CISI

CISI independently repeated the strongest negative result: global graph measures were worse. Query-local weighted coupling moved MAP positively (+1.02%) but the MAP confidence interval crossed zero.

### Cora

A citation-network query-by-example stress test produced a positive and statistically stable local-graph effect (+1.72% MAP; stronger P@10/nDCG@10 gains).

### Citeseer

Local citation corroboration was again positive (+0.80% MAP with positive CI), but global degree/authority became slightly positive. This corrected an overstrong claim: **global graph importance is not always harmful; it is weak and inconsistent.**

## 8. Cranfield and lexical-baseline correction

Cranfield showed TF-IDF could substantially outperform the C96/BM-family baseline used elsewhere. That led to another correction:

> ContextGraph should sit on a **strong lexical foundation**, not be permanently attached to one baseline formula.

This was not retrofitted into already-seen benchmarks and called validation; it became a future hypothesis.

## 9. Transition from citation graphs to the web

WebKB was the first major failure of the graph hypothesis in a web-like environment.

Raw hyperlinks were strongly heterophilic relative to topic labels and often represented navigation or organizational structure rather than topical relevance.

The pooled Cornell/Texas/Wisconsin local-link experiment lost roughly **6.8% MAP** versus text-only ranking.

Washington WebKB reproduced the failure. Multiplying link evidence by lexical source-target similarity recovered part of the damage but still lost to text.

This produced a new distinction:

> **A relation is useful only when the semantics of the edge support the relevance interpretation being assigned to it.**

## 10. Anchor semantics and another correction

The original CMU WebKB data preserve anchor text and surrounding context. Development experiments found:

- raw links harmed ranking;
- source-target lexical qualification reduced damage;
- anchor text alone recovered most of the damage;
- adding all available neighborhood/context evidence did not help further.

This led to a crucial evidence-role distinction:

- hyperlink structure = relation;
- anchor text = external lexical description;
- citation/coupling = relational semantic evidence;
- authority = source/global evidence.

They should not be collapsed into one `graph_score`.

Historical checking also showed inbound anchor text as a target-page description already existed before the cutoff (e.g. early Web search work such as WWW Worm-era techniques), so anchor indexing itself is **not** a novelty claim.

## 11. v4–v6: sparse anchors and candidate rescue

A sparse Q90 anchor gate failed on the unseen WebKB `misc` holdout, and a bug in the intended sparsity was diagnosed: ties let ~41% of contributions through.

An exact 10% evidence budget fixed sparsity on development data but still lost to text.

Anchor text was then tested as an **independent retriever** rather than a boost. It found relevant pages outside deep body rankings, proving complementary information existed, but under equal candidate budgets simply searching deeper in body text remained better.

The general anchor candidate-rescue hypothesis was therefore recorded as failed on WebKB.

## 12. v7: diagnose before rescue

The next idea was to predict when text retrieval was likely to benefit from anchor rescue using only observable features:

- body score margin;
- top-result coherence;
- anchor-score concentration;
- anchor novelty;
- body score statistics;
- query length;
- anchor non-emptiness.

A hand-written unsupervised rule failed badly.

A leave-one-university-out predictability diagnostic then found that rescue benefit was **predictable to a meaningful degree**:

- OOF ROC-AUC ≈ **0.7436**;
- top-decile predicted-benefit precision ≈ **32.6%** vs ~12.8% base rate.

However, the natural decision rule `score > 0` still degraded total recall. Prediction was not the same as decision calibration.

## 13. v8: risk-calibrated selective rescue

The architecture gained an explicit risk-calibration stage:

```text
Baseline
 -> Benefit Prediction
 -> Risk Calibration
 -> Intervention or NoAction
```

In leave-one-university-out WebKB testing, training folds alone selected a conservative threshold. The final OOF Recall@30 moved from **0.244735 to 0.244801 (+0.000066)** with a gate rate of only ~2.6%.

This is recorded as **weak positive / not validated**, because wins were sparse and the effect was not stable across universities.

The deeper theoretical conclusion is stronger than the metric:

> Search intelligence should often predict the **value of changing a strong baseline**, not merely predict relevance.

## 14. Curlie external validation

The project then froze a fully external modern retrospective validation protocol on Homepage2Vec/Curlie:

- published test split only;
- deterministic sample of 20,000 UIDs by SHA1(uid);
- no category balancing or graph-density filtering;
- relevance = shared published top-level class;
- body = classical TF-IDF over HTML;
- external descriptions = inbound anchor text from links internal to the frozen sample;
- candidate budget = 30;
- v8 controller serialized from WebKB before Curlie evaluation;
- Curlie labels prohibited from controller calibration.

A large (~14.8 GB compressed HTML) streaming extraction was built so only the frozen sample is retained. Parser/acquisition errors are treated as implementation issues, not scientific results.

## 15. Prior-art corrections

Throughout the project, historical research was checked continuously. Important corrections include:

- bibliographic coupling/co-citation/link-enhanced retrieval existed before 1997;
- Savoy (1996) and earlier work explored hypertext/link evidence in retrieval;
- HyPursuit (1996) used content-link hypertext clustering;
- selective relevance feedback existed in TREC-5-era systems;
- mixture-of-experts and database-selection ideas existed by 1996;
- anchor text propagated to target pages was an early-Web technique.

Therefore the project does **not** claim novelty for `links + text`, anchor indexing, selective feedback, or expert combination by themselves.

## 16. Current research position

The project has evolved from a PageRank reconstruction into a more general architecture:

```text
Strong baseline
 + typed evidence roles
 + observable failure state
 + intervention-benefit prediction
 + risk calibration
 + NoAction as a valid winner
```

The narrow research question now is whether this **risk-aware, query-adaptive evidence architecture** can generalize beyond WebKB and produce repeatable gains on independent web corpora while remaining constructible from pre-1997 concepts.

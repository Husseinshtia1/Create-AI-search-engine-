# G97 Search — Development Roadmap

This roadmap starts from the current state after CACM/CISI/Cora/Citeseer/WebKB v1–v8 and the frozen Curlie external-validation protocol.

## North-star objective

Build and empirically evaluate a complete search engine architecture that could plausibly be derived from knowledge available by **31 December 1996**, then determine how close it can get to — or in narrowly defined dimensions exceed — early Web search systems under fair retrospective evaluation.

The goal is not to copy modern Google. The goal is to discover which architecture emerges when historical components are recombined under rigorous experimentation.

---

# Phase 0 — Repository consolidation and reproducibility

**Status: IN PROGRESS**

### Deliverables
- canonical README/project identity;
- complete project history;
- architecture document;
- experiment registry;
- dataset governance;
- prior-art map;
- reproducibility methodology;
- snapshot every historical experiment branch into `experiments/archive/`;
- consolidate reusable primitives under `src/g97/`;
- add smoke/unit tests;
- one CLI for reproducible experiment utilities.

### Exit gate
A new contributor can clone the repository, understand every major experiment and reproduce at least CACM/CISI plus one WebKB development run without reading the original conversation.

---

# Phase 1 — Finish Curlie external validation

**Status: CLOSED — FROZEN FEASIBILITY FAILURE**

### Frozen protocol
- published Homepage2Vec test split;
- 20,000 UIDs with smallest SHA1(uid);
- no class balancing;
- no graph-density filtering;
- shared top-level class relevance;
- body TF-IDF;
- inbound-anchor external descriptions from sample-internal links;
- candidate budget 30;
- WebKB-only frozen v8 controller;
- paired bootstrap with fixed seed.

### Final frozen feasibility result

The 13.7 GiB HTML stream completed and all 20,000 selected records had URL, label and HTML data. The sample produced 2,720 directed internal edges and 4,928 anchor strings, but only **166 distinct inbound targets** against the predeclared requirement of **1,000**.

Therefore the frozen evaluator was correctly not run. This is a feasibility failure of the frozen sample-internal anchor graph, not a negative retrieval result for v8.

See `docs/CURLIE_EXTERNAL_VALIDATION_RESULT.md`.

### Exit outcome reached

3. **Feasibility failure** — graph/sample protocol cannot support the test; do not resize/filter sample post-hoc.

No further v8 tuning on Curlie is permitted.

---

# Phase 2 — Strong Lexical Foundation

**Motivation:** Cranfield and ADI showed no single lexical formula dominates every collection.

### Research question
Can a historically admissible lexical foundation choose/preserve the right simple baseline without relevance labels for each query?

### Components
- TF-IDF cosine;
- probabilistic/BM-family scoring;
- title/body field weighting;
- phrase/proximity evidence;
- conservative stemming;
- spelling/OOV repair;
- no unconditional PRF.

### Experiments
- freeze a baseline-selection policy on development collections;
- validate on unseen historical IR collections;
- compare against best fixed single baseline;
- report per-query regime changes.

### Exit gate
A lexical foundation that is not materially worse than the best fixed historical baseline across multiple unseen collections and improves robustness without qrels-at-query-time.

---

# Phase 3 — Typed Evidence Engine

Replace ad-hoc graph scores with explicit evidence roles.

### Evidence types
```text
BodyEvidence
ExternalDescriptionEvidence
RelationalCorroboration
AuthorityEvidence
FreshnessEvidence
Host/SourceEvidence
```

### Requirements
- each evidence type has a declared semantic role;
- each role has an admissibility/prior-art note;
- authority cannot masquerade as lexical relevance;
- relation semantics must be qualified before use;
- all boosts/repairs are bounded and auditable.

### Output
A typed evidence object per candidate/query rather than one opaque score.

---

# Phase 4 — General Intervention Controller

Move from one anchor-rescue controller to a multi-action control architecture.

### Action set
```text
NoAction
SpellingRepair
Phrase/ProximityMode
ExternalDescriptionRescue
RelationalCorroboration
ConservativeExpansion
FreshnessBias
```

### Controller objective
Estimate:

```text
ExpectedUtility(action, query_state)
```

rather than relevance alone.

### Risk requirements
- class imbalance aware;
- false-positive intervention cost explicit;
- calibration learned from training folds only;
- `NoAction` can win by default;
- equal-resource evaluation.

### Evaluation
- leave-collection-out, not merely leave-query-out;
- modern web retrospective holdouts;
- classical IR holdouts;
- intervention frequency and regret metrics.

### Exit gate
Positive out-of-collection expected gain with no catastrophic regressions and a statistically defensible improvement over always-no-action.

---

# Phase 5 — Web Relation Semantics

Raw hyperlinks failed. This phase models relation meaning without using modern embeddings.

### Historically admissible features
- anchor text;
- surrounding paragraph/list/table-cell/heading words;
- source-target lexical agreement;
- source outdegree/scarcity;
- same-host/cross-host relation;
- repeated/sitewide-link suppression;
- multiple independent inbound descriptions;
- link position/context categories derivable from HTML.

### Experiments
- relation classification/qualification without relevance labels;
- test whether qualified relations predict topic agreement;
- measure whether relation quality transfers across corpora;
- keep ranking evaluation separate from relation-quality diagnostics.

### Exit gate
A relation-quality model that transfers to an unseen web corpus and demonstrably distinguishes useful semantic links from navigation/organizational links.

---

# Phase 6 — Discovery and Crawl Engine

Build the actual historically constrained crawler.

### Discovery
```text
hyperlinks
+ submitted URLs
+ domain discovery
+ high-change hubs
```

### Scheduler
- broad discovery first;
- adaptive recrawl intervals;
- failure backoff;
- duplicate/trap suppression;
- robots/politeness;
- host budgets;
- priority based on observed change/waste, not unsupported predicted importance.

### Metrics
- discovery recall;
- pages/hour;
- duplicate/trap waste;
- change freshness;
- TTQ (Time To Queryability);
- bandwidth per useful update.

### Exit gate
A reproducible crawl of a controlled web testbed that achieves strong TTQ and coverage without unstable prediction-heavy scheduling.

---

# Phase 7 — Repository, Delta Index and Merge

### Architecture
```text
Crawler -> Document Repository -> Searchable Delta -> Main Index
                                       \-> background merge
```

### Requirements
- deterministic document IDs;
- content checksum/duplicate handling;
- version history sufficient for freshness experiments;
- crash-safe segment writes;
- query-visible delta immediately;
- merge policies compatible with 1996-era storage concepts.

### Metrics
- ingest throughput;
- time-to-searchable;
- merge amplification;
- index size;
- query degradation during merge.

---

# Phase 8 — Distributed Query Serving

### Components
- document shards;
- replicated shards;
- top-K coordinator;
- query/result cache;
- main+delta fanout;
- timeout/partial-result behavior;
- resource governor.

### Primary concern
Tail latency, not just mean latency.

Measure:
```text
P50 / P95 / P99
throughput
utilization
queue depth
merge interference
```

### Resource Governor
Search traffic has priority over background maintenance near saturation.

### Exit gate
Stable P99 under mixed query + ingest + merge load, with predictable graceful degradation.

---

# Phase 9 — Snippets and Evidence Presentation

Ranking and presentation stay separate.

### Features
- query-focused passages;
- title/URL display;
- anchor/external evidence explanation when applicable;
- freshness marker;
- reason codes for interventions.

### Rule
A snippet feature does not enter ranking merely because it improves presentation.

---

# Phase 10 — End-to-End Search Benchmark

Combine crawler, indexing, query processing, controller, ranking and serving.

### Evaluation dimensions
1. relevance quality;
2. crawl/discovery coverage;
3. freshness / TTQ;
4. latency;
5. bandwidth/CPU/storage cost;
6. failure robustness;
7. spam/navigation resistance;
8. reproducibility.

### Required baselines
- text-only historical baseline;
- text + global authority;
- text + anchor indexing;
- G97 adaptive architecture;
- where historically fair, published early-Web baselines.

### Exit gate
A full system result, not just ranking MAP, showing exactly where G97 is better, equal or worse.

---

# Phase 11 — Web-scale historical benchmark

Target WT2g/WT10g/TREC-like web collections or another legally/technically accessible web benchmark with links and relevance judgments.

### Rules
- architecture frozen before result;
- no WebKB/Curlie tuning after freeze;
- full per-topic analysis;
- equal candidate/resource budgets;
- compare global authority vs typed query-local evidence vs adaptive controller.

This is the main gate before any claim about relevance to Google-like Web search.

---

# Phase 12 — Scientific paper and prior-art audit

### Paper structure
1. historical question and cutoff;
2. system architecture;
3. negative results and why they matter;
4. citation-like graph replications;
5. web-link failures;
6. evidence-role decomposition;
7. intervention-benefit/risk controller;
8. external validation;
9. system implications;
10. limitations.

### Prior-art audit
Perform a systematic search of:
- SIGIR/CIKM/TREC/WWW pre-1997 proceedings;
- patents filed before/around cutoff;
- early Web search systems;
- selective feedback/routing/mixture literature;
- hypertext/citation retrieval.

No novelty claim until this audit is complete.

---

# Phase 13 — Production research prototype

Only after the scientific architecture survives validation:

### Product capabilities
- crawl a user-defined web scope;
- live searchable delta;
- query API;
- evidence/debug trace;
- experiment switchboard;
- controller decision trace;
- benchmark dashboard;
- reproducible snapshot export.

### Non-goal
Do not optimize for UI polish before retrieval/crawl/serving gates pass.

---

# Current immediate next actions

1. Complete Phase 0 exit-gate reproduction evidence for CACM, CISI and one WebKB development run.
2. Treat `G97-CURLIE-001` as closed with frozen feasibility failure; no post-hoc sample or threshold changes.
3. Freeze the next independent Strong Lexical Foundation experiment before observing its validation results.
4. Implement the lexical benchmark harness with equal-resource comparisons across TF-IDF, BM-family, field weighting, phrase/proximity, conservative stemming and spelling/OOV repair.
5. Keep validation collections isolated from development collections and record per-query regime changes.
6. Start controlled crawler + TTQ implementation on a separate engineering track without changing frozen retrieval experiments.

## Success criterion for the overall project

The project succeeds scientifically even if it does **not** beat Google. Success means producing a defensible answer to:

> What search architecture could a highly capable reasoner have built from the knowledge available by the end of 1996, which components actually work under modern empirical scrutiny, and why?

A stronger outcome — demonstrating a historically admissible architecture that beats early/global-authority baselines on meaningful web benchmarks — remains the stretch goal.

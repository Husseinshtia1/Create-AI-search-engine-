# Datasets and Data Governance

## Historical/IR collections

### CACM
- 3,204 documents; 64 queries in the source collection.
- SMART-style text fields and `.X` relational information.
- Used for the first frozen A0–A6 ContextGraph benchmark.
- Relation channels used: direct links, bibliographic coupling, co-citation.
- **Current governance role:** seen/development data for Phase 2; it is no longer eligible as an independent lexical validation collection.

### CISI
- 1,460 documents; 112 queries.
- Weighted bibliographic-coupling style `.X` relation matrix.
- Used as an independent historical IR replication.
- **Current governance role:** seen/development data for Phase 2.

### Cranfield
- 1,400 documents; 225 queries with relevance judgments.
- Used as a lexical benchmark; no graph signal was used in the G97 Cranfield run.
- **Current governance role:** seen/development data for Phase 2.

### NPL
- Public classical IR test collection distributed by the Glasgow IR test-collection archive.
- Expected source shape for the Phase 2 acquisition check: approximately 11,429 documents and 93 queries.
- Historical NPL retrieval work began in 1961 and the collection belongs to the pre-1997 experimental IR tradition.
- **Phase 2 role:** primary unseen validation for `G97 Strong Lexical Foundation — Freeze 001`.
- Its qrels must not be used for policy design before `POLICY_FROZEN.json` and all required freeze artifacts are committed.

### TIME
- Public classical IR test collection containing Time magazine articles, queries and relevance assessments.
- Expected source shape for the Phase 2 acquisition check: approximately 423 documents and 83 queries.
- **Phase 2 role:** secondary confirmation holdout for `G97 Strong Lexical Foundation — Freeze 001`.
- TIME must not be used to alter the policy after observing NPL results.

## Citation-network stress tests

### Cora
- Citation network + word features + topic labels.
- Used as query-by-example stress test, not claimed as TREC/ad-hoc IR.

### Citeseer
- Citation network + text features + topic labels.
- Same methodological role as Cora.

## Web datasets

### WebKB
- University web pages with text/features, topical labels and hyperlinks.
- Original CMU data also preserve HTML, anchors and link-neighborhood information.
- Cornell/Texas/Wisconsin used for initial web stress tests.
- Washington used as an unseen holdout for v2 at the time of execution.
- `misc` used as a within-family holdout for v4.
- After those results, all WebKB subsets are considered seen/development data.

### CMU Industry Sector
- Candidate independent web corpus of company pages/sectors.
- Acquisition diagnostics were attempted; no ranking result is claimed.

### Homepage2Vec / Curlie
- Modern retrospective corpus of websites with published class vectors and raw HTML.
- Used only as external validation, never as a source of post-1996 design knowledge.
- Frozen protocol used the published test split and 20,000 deterministic UIDs with smallest SHA1(uid).
- No class balancing or graph-density filtering.
- Relevance for the planned query-by-example evaluation was any shared published top-level class.
- Final frozen result: all 20,000 URLs/labels/HTML records were present, but only 166 distinct inbound targets existed versus the predeclared feasibility minimum of 1,000. The retrieval evaluator was therefore not run.
- **Current governance role:** closed external-validation feasibility failure; no v8 tuning may use Curlie.

## Data leakage policy

1. Labels/qrels are not available to scoring unless the experiment is explicitly a training/calibration experiment.
2. Validation protocols are frozen before the first retrieval metric.
3. Development data remain development data after use; they cannot later be called independent validation.
4. Later datasets may validate a pre-1997 architecture but cannot justify introducing post-cutoff techniques.
5. Sampling rules are deterministic and frozen before metric inspection.
6. Dataset-format/parser corrections may be made after execution failures only when they do not alter ranking/evaluation hypotheses.
7. Reserved Phase 2 validation qrels for NPL and TIME may be checked for file integrity/identifier consistency, but must not be joined to rankings or summarized into effectiveness metrics before the final policy freeze.
8. NPL is evaluated before TIME. No ranking/policy change is allowed between those validation collections based on observed effectiveness.

## Large-data policy

Large datasets are not committed to Git. Acquisition is checksum-verified where possible, and deterministic manifests are stored instead.

For Curlie, the compressed HTML payload was roughly 13.7–14.8 GB depending on reporting convention/source metadata, so the frozen pipeline streamed it and retained only the deterministic sample rather than committing the corpus.

## Dataset role matrix

| Dataset | IR judgments | graph/links | current exact role |
|---|---:|---:|---|
| CACM | yes | yes | Phase 2 development / historical prior validation |
| CISI | yes | yes | Phase 2 development / historical prior replication |
| Cranfield | yes | no graph used | Phase 2 development / prior lexical benchmark |
| NPL | yes | not required | Phase 2 primary unseen lexical validation — reserved |
| TIME | yes | not required | Phase 2 secondary confirmation holdout — reserved |
| Cora | topic labels | citations | mechanism stress test |
| Citeseer | topic labels | citations | mechanism stress test |
| WebKB | topic labels | hyperlinks/anchors | web mechanism development/previous holdouts; now seen |
| Curlie | class vectors | HTML hyperlinks/anchors reconstructed | closed frozen external-validation feasibility failure |

# Datasets and Data Governance

## Historical/IR collections

### CACM
- 3,204 documents; 64 queries in the source collection.
- SMART-style text fields and `.X` relational information.
- Used for the first frozen A0–A6 ContextGraph benchmark.
- Relation channels used: direct links, bibliographic coupling, co-citation.

### CISI
- 1,460 documents; 112 queries.
- Weighted bibliographic-coupling style `.X` relation matrix.
- Used as an independent historical IR replication.

### Cranfield
- 1,400 documents; 225 queries with relevance judgments.
- Used as a lexical benchmark; no graph signal was used in the G97 Cranfield run.

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
- Frozen protocol uses the published test split and 20,000 deterministic UIDs with smallest SHA1(uid).
- No class balancing or graph-density filtering.
- Relevance for query-by-example evaluation: any shared published top-level class.

## Data leakage policy

1. Labels/qrels are not available to scoring unless the experiment is explicitly a training/calibration experiment.
2. Validation protocols are frozen before the first retrieval metric.
3. Development data remain development data after use; they cannot later be called independent validation.
4. Later datasets may validate a pre-1997 architecture but cannot justify introducing post-cutoff techniques.
5. Sampling rules are deterministic and frozen before metric inspection.
6. Dataset-format/parser corrections may be made after execution failures only when they do not alter ranking/evaluation hypotheses.

## Large-data policy

Large datasets are not committed to Git. Acquisition is checksum-verified where possible, and deterministic manifests are stored instead.

For Curlie, the compressed HTML payload is roughly 14.8 GB, so the pipeline streams it and retains only the frozen sample rather than committing or fully materializing the corpus in the repository.

## Dataset role matrix

| Dataset | IR judgments | graph/links | exact role |
|---|---:|---:|---|
| CACM | yes | yes | historical IR validation |
| CISI | yes | yes | historical IR replication |
| Cranfield | yes | no graph used | lexical benchmark |
| Cora | topic labels | citations | mechanism stress test |
| Citeseer | topic labels | citations | mechanism stress test |
| WebKB | topic labels | hyperlinks/anchors | web mechanism development/holdouts |
| Curlie | class vectors | HTML hyperlinks/anchors reconstructed | independent modern retrospective validation |

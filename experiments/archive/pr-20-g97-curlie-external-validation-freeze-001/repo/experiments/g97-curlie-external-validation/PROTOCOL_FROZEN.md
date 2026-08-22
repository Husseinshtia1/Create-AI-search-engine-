# G97 Curlie External Validation — FROZEN BEFORE RESULTS

Status: external retrospective validation only. Curlie/Homepage2Vec data are from 2021 and MUST NOT be used as a design input to the 31-Dec-1996-constrained G97 system.

## Dataset
Public Figshare article: 19406693, version 5.
Required files only:
- `test_uid.txt` — original test split, 88,559 UIDs.
- `class_vector.json.gz` — UID -> 14-dimensional binary class vector.
- `html_content.json.gz` — UID -> fetched homepage HTML.
- `curlie_filtered.csv.gz` — UID -> URL metadata, used only to resolve internal links.
- `class_names.txt` — class names.

## Frozen sample selection
1. Universe = UIDs occurring in the published `test_uid.txt` only.
2. No category balancing, graph-density filtering, language filtering, or manual site selection.
3. Deterministic priority key = SHA1(UTF-8 UID), interpreted as a 160-bit unsigned integer.
4. Select the 20,000 UIDs with the smallest SHA1 keys.
5. If fewer than 20,000 selected UIDs have usable HTML + label + URL records, the protocol FAILS feasibility; do not replace missing UIDs post hoc.
6. Internal hyperlink graph is reconstructed only among those same 20,000 selected UIDs after canonicalizing homepage URLs. No expansion to linked sites outside the frozen sample.
7. Predeclared feasibility gate BEFORE retrieval metrics: require at least 1,000 distinct selected targets with >=1 inbound anchor from another selected site. If this is not met, do not compute v8 retrieval metrics; record `INSUFFICIENT_INTERNAL_ANCHOR_GRAPH`.

## Relevance
For query-by-example site q, document d is relevant iff q != d and their published 14-dimensional class vectors share at least one positive class:

`relevant(q,d) := any(class_q[i] == 1 and class_d[i] == 1 for i in 0..13)`

No class labels or relevance information may enter retrieval features, ranking, calibration, sampling, URL canonicalization, or graph construction.

## Text and anchor representation
- Body text = visible textual content extracted from frozen homepage HTML using deterministic HTML stripping; script/style/noscript removed; HTML entities decoded; lowercase alphanumeric tokenization.
- No embeddings, neural models, post-1996 language models, or Homepage2Vec outputs.
- Body retriever = classical TF-IDF cosine, matching the v7/v8 WebKB family.
- External-description document for target d = inbound anchor text from selected source pages pointing to d.
- Each source contribution is weighted by the same v7 scarcity factor: `1 / (1 + ln(1 + outdegree(source)))`.
- Anchor retriever = cosine(query body TF-IDF, target external-description TF-IDF).

## Candidate budget
Exactly 30 candidates per query.
- Baseline: Body@30.
- Forced rescue candidate set used to define utility: Body@20 + novel Anchor@10, then fill from body tail until exactly 30 unique candidates.

## v8 intervention controller
No Curlie labels may train or recalibrate the controller.

The controller is frozen from the WebKB development procedure:
- 10 observable features exactly as in G97-Web v7/v8: margin10, coherence10, anchor_top3_share, anchor_novel_ratio, body_top1_score, body_top10_mean, body_top10_cv, log query token count, anchor_top1_score, anchor_nonempty_ratio.
- Nearest-centroid benefit score architecture unchanged.
- Risk-calibration principle unchanged.

Because Curlie is a true external validation corpus, **no threshold may be learned from Curlie relevance labels**. Before Curlie retrieval evaluation, freeze a single controller learned only from the four seen WebKB universities using the same v8 training rule across all WebKB development queries: z-normalization, positive/negative centroids, then the highest score threshold with >=20 activated WebKB queries and strictly positive mean actual DeltaRecall30. The resulting WebKB-only centroid parameters and threshold must be serialized into the Curlie experiment commit before Curlie labels are evaluated.

## Metrics
Primary: Recall@30 under equal candidate budget.
Secondary: per-query wins/losses/ties and gate rate.
Also report forced-rescue Recall@30 descriptively.

No parameter, threshold, sample membership, relevance definition, or representation rule may change after the first Curlie retrieval metrics are produced.

## Success interpretation
- `External validation positive`: v8 Recall@30 > Body@30 on the frozen sample.
- `External validation negative`: v8 Recall@30 < Body@30.
- `Tie/near-zero`: report exact delta; do not relabel as success.
- No statistical-significance claim unless a predeclared paired bootstrap is run with fixed seed and 10,000 resamples; if run, report the full 95% CI.

## Historical firewall
Curlie (2021), its labels, HTML, and any behavior observed on it are evaluation data only. They cannot be used to alter the G97 design claimed to be derivable by 31 Dec 1996.

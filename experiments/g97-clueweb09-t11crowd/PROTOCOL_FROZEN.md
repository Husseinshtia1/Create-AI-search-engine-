# G97 ClueWeb09-T11Crowd External Validation — FROZEN BEFORE DATA/RESULTS

Status: independent retrospective external validation only. ClueWeb09/TREC-2011 data are post-1996 and are evaluation data, never design inputs.

## Corpus
Use the complete official ClueWeb09-T11Crowd subset used by the TREC 2011 Crowdsourcing Track. No document sampling, category filtering, graph-density filtering, or manual selection is allowed. The expected corpus is approximately 19,636 unique judged Web pages and approximately 217 topics; exact counts must be taken from the official package/track metadata and reported, not forced.

Each page must retain its official DOCNO, URL, HTML, and visible text. Topics and NIST/TREC judgments must remain separate from retrieval construction until rankings/controller decisions are frozen.

## Retrieval task
For each official TREC topic, rank the T11Crowd document universe. Relevance is the official NIST/TREC topical relevance judgment supplied for that topic/document pair. Unjudged documents are not silently treated as design labels; evaluation follows the official T11Crowd/TREC protocol as available in the package.

## Text / external-description channels
- Body retriever: classical TF-IDF cosine over visible HTML text; ASCII alphanumeric lowercase tokenizer, unchanged from the frozen WebKB/Curlie evaluator family.
- Target external description: inbound anchor text from links whose target resolves to another document inside the complete T11Crowd universe.
- Canonical URL matching: lowercase host, remove leading `www.`, strip default ports/final hostname dot; resolve relative links against source URL. Ambiguous target mappings are discarded rather than guessed.
- Source scarcity weight unchanged: `1 / (1 + ln(1 + outdegree(source)))`.
- No PageRank, embeddings, neural models, or post-1996 retrieval features.

## Feasibility gate (before relevance metrics)
Graph feasibility is assessed before loading judgments into the evaluator.
Require distinct documents with >=1 inbound anchor from another T11Crowd page to be at least **5% of the valid corpus size**. This preserves the same proportional requirement used in the preregistered Curlie experiment (1,000 / 20,000 = 5%).

If the gate fails, record `INSUFFICIENT_INTERNAL_ANCHOR_GRAPH` and DO NOT compute v8 retrieval metrics. Do not lower the 5% threshold, expand the corpus, or select graph-dense pages after seeing the feasibility result.

## Frozen intervention controller
Use exactly `G97-Web-v8-WebKB-only-controller` exported before any external web retrieval result:
- candidate budget = 30
- Body prefix before rescue = 20
- Anchor offer = 10
- 10 observable features in the previously frozen order
- z-normalization, nearest-centroid benefit score
- `threshold_tau = 12.381009120265105`
No controller parameter, threshold, feature, tokenizer, or candidate budget may be learned/recalibrated on T11Crowd.

## Candidate sets
- Baseline: Body@30.
- Forced rescue: Body@20 + novel Anchor@10 + body tail until exactly 30 unique candidates when enough body candidates exist.
- v8 policy: use Forced rescue iff frozen controller score >= frozen tau, else Body@30.

## Metrics
Primary: official relevance-based retrieval effectiveness at the fixed top-30 candidate budget. Report Recall@30 whenever official judgments define a denominator suitable for it; also report MAP/nDCG/P@10 only when compatible with the official judgment format and clearly label incomplete-judgment caveats.
Always report forced-rescue control, gate rate, per-topic wins/losses/ties, and exact judged-topic count.

Paired bootstrap, if applicable, is frozen at seed `19961231` and 10,000 resamples; report the full 95% CI.

## Historical firewall
No observation from T11Crowd may modify G97. A negative result remains negative. A feasibility failure remains a feasibility failure. Any future modified protocol must be named and preregistered separately and cannot retroactively serve as this external validation.

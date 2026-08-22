# G97 Strong Lexical Foundation — Protocol Freeze 001

**Status:** FROZEN BEFORE NPL/TIME VALIDATION METRICS

## Research question

Can a historically admissible lexical controller preserve or improve a strong fixed lexical baseline across unseen collections without consulting relevance judgments at query time?

The purpose of this experiment is not to discover the best formula separately on each validation collection. It is to freeze a small set of historically admissible lexical actions and a selection policy using only already-seen development collections, then evaluate the frozen policy on unseen classical IR collections.

## Historical cutoff

All retrieval mechanisms and controller features must be plausibly derivable from knowledge available by **31 December 1996**. Later software may be used only as implementation infrastructure; it must not introduce post-cutoff ranking signals into the experiment.

## Dataset roles frozen now

### Development-only collections

These collections have already been inspected/evaluated in G97 and are permanently treated as seen data:

- CACM
- CISI
- Cranfield

Their qrels may be used to fit or select the lexical policy before validation freeze completion.

### Primary unseen validation

- **NPL**
- expected public collection shape: approximately 11,429 documents and 93 queries
- qrels are forbidden from policy design before the serialized policy is committed

### Secondary confirmation holdout

- **TIME**
- expected public collection shape: approximately 423 documents and 83 queries
- qrels are forbidden from policy design before the serialized policy is committed

TIME must not be used to repair a policy after observing NPL results. NPL and TIME are both validation data for this protocol.

## Query/document preprocessing

The exact preprocessing implementation must be committed before validation scoring and then kept identical across development and validation collections except for unavoidable corpus-format parsing.

Frozen semantic constraints:

1. lowercase lexical matching;
2. ASCII/alphanumeric tokenization consistent with the consolidated G97 tokenizer unless a single replacement tokenizer is frozen before validation;
3. no relevance-derived vocabulary filtering;
4. no learned embeddings;
5. no neural ranking;
6. no post-1996 pretrained linguistic resources;
7. corpus-specific parser fixes may recover intended document/query text but may not use qrels or retrieval outcomes.

## Candidate lexical actions

The policy may choose only among the following predeclared actions:

```text
A0  TFIDF_COSINE
A1  BM_FAMILY
A2  TFIDF_CONSERVATIVE_STEM
A3  BM_FAMILY_CONSERVATIVE_STEM
A4  TFIDF_PHRASE_PROXIMITY_BOUNDED
A5  BM_FAMILY_PHRASE_PROXIMITY_BOUNDED
A6  FIELD_WEIGHTED_LEXICAL        (only where genuine title/body fields exist)
A7  SPELLING_OOV_REPAIR_BOUNDED
```

An action that cannot be applied to a collection because its source format lacks the required field/evidence must report `UNAVAILABLE`; it may not synthesize the missing evidence.

No pseudo-relevance feedback is allowed in Freeze 001.

## Fixed baseline

The principal fixed comparator is **TF-IDF cosine** using the same frozen tokenizer/preprocessing and the full collection.

A second reference comparator is **BM-family scoring** with parameters selected on development data only and then serialized before NPL/TIME scoring.

The adaptive policy must be compared both with:

1. fixed TF-IDF;
2. fixed BM-family;
3. the best single fixed action selected using development collections only.

The validation result must not use an oracle best-per-query or best-per-collection baseline chosen from validation qrels.

## Equal-resource rule

For any top-k metric, every compared ranking receives the same requested output depth. No method may receive deeper candidate retrieval unless the resource difference is explicitly part of a separately named diagnostic.

Primary evaluation depth:

```text
K = 100
```

Reported cutoff metrics additionally include P@10 and nDCG@10 where relevance encoding permits.

## Policy state/features

The selection policy may use only label-free observable query/retrieval state available before relevance evaluation. Candidate feature families are frozen to:

```text
query_token_count
unique_query_token_count
query_idf_mean
query_idf_max
query_idf_min
oov_ratio
top1_score
top10_mean_score
top10_score_cv
top1_top10_margin
retrieved_nonzero_count
query_term_document_coverage
```

If phrase/proximity evidence is implemented, label-free phrase occurrence statistics may be added only if committed to the serialized feature schema before validation metrics are computed.

No collection name, query ID, qrels, relevance count, AP, or validation-set identity may be a policy feature.

## Policy learning

The policy must be fit only on CACM/CISI/Cranfield using collection-held-out training logic.

Required development procedure:

1. construct per-query outcomes for every available action on seen collections;
2. compute each action's utility relative to the fixed baseline;
3. train/select the simplest policy that predicts expected utility from frozen label-free state;
4. evaluate its development generalization with leave-one-collection-out analysis;
5. select/freeze one final policy using development data only;
6. serialize all parameters, feature order, preprocessing configuration, action parameters, and thresholds;
7. commit the serialization before loading NPL/TIME qrels for scoring.

`NoAction` means retain the selected fixed baseline and must be a first-class policy outcome.

## Validation order and information firewall

Validation order is frozen:

1. NPL
2. TIME

After NPL metrics become visible, no ranking rule, feature, preprocessing rule, threshold, or parameter may change before TIME scoring.

If an implementation defect is found after NPL:

- a fix is permitted only if it restores the already-frozen intended computation;
- the original result remains recorded;
- the defect and fix must be documented;
- both NPL and TIME must be rerun under the corrected frozen implementation if comparability requires it;
- no change motivated by retrieval quality is permitted.

## Metrics

Primary metric:

```text
MAP
```

Secondary metrics:

```text
MRR
P@10
Recall@100
nDCG@10
```

For every policy-vs-baseline comparison report:

- macro mean metric;
- absolute delta;
- relative delta where meaningful;
- per-query wins/losses/ties;
- paired bootstrap 95% confidence interval with a fixed committed seed;
- intervention/action frequency;
- regret against the development-defined fixed comparator;
- action distribution.

The bootstrap seed must be serialized before validation.

## Success criteria

A positive Phase 2 result requires all of the following:

1. the frozen adaptive lexical policy is not materially worse than the strongest development-selected fixed baseline on either unseen collection;
2. pooled/combined evidence across NPL and TIME supports positive robustness rather than gain driven by one isolated collection;
3. no catastrophic per-collection regression;
4. no validation-informed tuning;
5. confidence intervals and per-query analysis are reported whether positive or negative.

A small positive mean with unstable collection direction is classified `WEAK POSITIVE`, not validation.

## Failure outcomes

The experiment remains scientifically useful if:

- one fixed lexical model dominates the adaptive policy;
- policy transfer fails across collections;
- phrase/stemming/spelling actions help only narrow regimes;
- no label-free query state reliably predicts action benefit.

Failures must remain in the experiment registry.

## Anti-leakage rules

Before the final serialized policy commit, the following are forbidden for NPL and TIME:

- reading or aggregating qrels to guide model design;
- computing MAP/AP/nDCG/Recall/P@k;
- selecting preprocessing from observed retrieval outcomes;
- choosing BM parameters from validation metrics;
- choosing stemming/spelling thresholds from validation metrics;
- inspecting per-query wins/losses;
- changing the action set because of NPL/TIME behavior.

Format-only checks may inspect file names, record counts, parser structure, field presence, and identifier consistency without joining qrels to rankings.

## Required artifacts before first validation metric

The following must exist in Git before NPL scoring:

```text
PROTOCOL_FROZEN.md
PREPROCESSING_FROZEN.json
ACTIONS_FROZEN.json
POLICY_FROZEN.json
validation_manifest.json
```

`POLICY_FROZEN.json` must include a cryptographic digest or commit-bound provenance for all learned parameters and feature order.

## Current gate

This commit freezes the **experimental contract and validation datasets**, not the learned policy. NPL/TIME retrieval metrics remain prohibited until the development harness is implemented, the final policy is learned only from seen collections, and all required frozen artifacts above are committed.

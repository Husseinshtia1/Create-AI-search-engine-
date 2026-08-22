# G97 Search Architecture

## Design objective

Build a historically constrained, experimentally defensible search architecture using concepts available by **31 December 1996**, while allowing later datasets only as retrospective validation environments.

## System layers

```text
1. Discovery
2. Crawl / Refresh
3. Repository
4. Searchable Delta Index
5. Main Index + Merge
6. Query Processing
7. Candidate Retrieval
8. Typed Evidence Layer
9. Intervention Controller
10. Ranking / Reranking
11. Serving / Top-K Coordination
12. Snippet / Evidence Presentation
13. Resource Governor
```

## Core invariant

The project no longer assumes that every extra signal should continuously affect ranking.

The current invariant is:

> **Preserve a strong baseline unless an intervention has observable evidence of positive expected value.**

Formally, for an action `a` and query `q`:

```text
Utility(a,q) = E[Gain(a,q) | x_q] - Risk(a,q)
```

`NoAction` is always present and may win.

## Evidence roles

Evidence is typed rather than collapsed into one graph score.

### 1. Body evidence

What a document/page says about itself.

```text
E_body(d,q)
```

Implemented with historically admissible lexical models such as TF-IDF/BM-family scoring, field evidence and proximity where justified.

### 2. External-description evidence

What other pages say about a target — especially inbound anchor text.

```text
E_external(d,q)
```

This is lexical evidence, not authority.

### 3. Relational corroboration

Relations whose semantics are themselves meaningful evidence: citations, bibliographic coupling, co-citation and similar typed relations.

```text
E_rel(d,q | S_q)
```

where `S_q` is a high-confidence lexical seed set.

### 4. Authority / source evidence

Query-independent or weakly query-dependent source reputation.

```text
E_authority(d)
```

This is never assumed to be relevance by itself.

## ContextGraph

For a typed relation `R`:

```text
G_R(d,q) = sum_{s in S_q} Confidence(s,q) * R(s,d)
```

A bounded form is:

```text
Ghat = G / (1 + G)
Score = TextScore * (1 + lambda * Ghat)
```

The historical experiments froze `lambda = 0.50` for several graph ablations.

Citation-like datasets showed this can help; raw web hyperlinks showed that the edge semantics must justify the relevance interpretation.

## Query-adaptive intervention controller

The current controller uses observable features of the query/result state rather than labels at inference time.

Examples used in v7/v8 development:

- top-10 score margin;
- top-10 result coherence;
- anchor-score concentration;
- anchor novelty relative to body results;
- body top-1 score;
- body top-10 mean score;
- body score coefficient of variation;
- query length;
- anchor top-1 score;
- anchor non-empty ratio.

The v8 controller is intentionally conservative. It predicts whether external rescue is likely to improve a fixed-budget candidate set, then applies a training-only calibrated threshold.

## Candidate budget discipline

A repeated source of misleading gains is giving an intervention more candidates/resources than the baseline.

Therefore candidate-rescue experiments compare equal or explicitly matched budgets. For example:

```text
Body@30
vs
Body@20 + novel Anchor@10 + body-tail fill to exactly 30
```

## Crawling architecture

The crawler follows a conservative design:

```text
broad discovery
+ adaptive refresh
+ duplicate/trap/failure suppression
+ resource-aware scheduling
```

The system should not aggressively predict unknown URL value when it lacks evidence.

### Discovery channels

```text
URLDiscovery = hyperlinks + direct submission + domain discovery + fast-changing hubs
```

### Key metric

`TTQ = Time To Queryability`

A page is not operationally discovered until it can be returned by search.

## Index architecture

```text
MainIndex + SearchableDelta
```

New documents enter the searchable delta rapidly and are merged into the main index asynchronously.

## Query processing

Query transformations are conditional repairs rather than defaults.

```text
Healthy query -> preserve
OOV/spelling failure -> spelling repair
explicit phrase -> proximity handling
clear retrieval failure -> optional rescue/expansion
```

## Serving

The serving layer is designed around:

- document shards;
- replication;
- query/result caches;
- fresh delta visibility;
- top-K coordinator;
- tail-latency protection.

The Resource Governor prioritizes user-facing search over background merges/maintenance near saturation.

## Presentation vs ranking

Evidence useful for explanation is not automatically useful for ranking.

Query-focused passages/snippets may improve user understanding while harming ranking if used as direct scoring signals. Ranking and evidence presentation remain separate subsystems.

## Current architecture target

```text
Query
  -> Lexical Foundation
  -> Candidate State Diagnostics
  -> Typed Evidence Availability
  -> Benefit Predictor
  -> Risk Calibration
  -> Action Selector
       NoAction | RelationalCorroboration | ExternalRescue | QueryRepair | ...
  -> Final Top-K
  -> Evidence/Snippet Renderer
```

The next validation question is whether this controller architecture generalizes to an independent web corpus without recalibration on that corpus.

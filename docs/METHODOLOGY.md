# Methodology and Reproducibility

## Scientific firewall

Every experiment is assigned one of four roles before results are viewed:

- development;
- diagnostic;
- frozen validation;
- retrospective external validation.

A dataset that has been used for development cannot later be re-labelled as independent validation.

## Pre-registration convention

Before a frozen run, record:

1. dataset and split;
2. deterministic sampling rule;
3. preprocessing;
4. ranking formula;
5. graph/evidence semantics;
6. candidate budget;
7. hyperparameters;
8. evaluation metrics;
9. random/bootstrap seed;
10. success/failure interpretation.

Pull-request descriptions have been used as immutable pre-result records for many experiments.

## Anti-leakage pattern

For non-training benchmarks:

```text
load documents / graph / queries
build all scores and rankings
ONLY THEN load qrels/labels
compute metrics
```

For query-by-example datasets, labels define relevance only after features/rankings are constructed.

## Fair resource comparison

Interventions must not win merely because they receive more candidate slots or deeper retrieval.

When testing rescue:

```text
Body@30
vs
Body@20 + Anchor@10(new) + BodyTailFill -> exactly 30
```

Similar budget matching should be applied to CPU, crawl bandwidth and serving latency when moving toward system-level evaluation.

## Statistics

The project has used paired bootstrap confidence intervals for per-query metric deltas with fixed seeds. Wins/losses/ties are reported alongside means when possible.

A positive mean is not automatically called significant or validated.

## Failure policy

A failed experiment remains in the registry.

Allowed post-failure changes:
- parser corrections;
- URL/path/acquisition corrections;
- qrels format normalization;
- infrastructure repair;

only when they do not change the scientific hypothesis/ranking rule.

Not allowed while preserving the original validation claim:
- choosing a new lambda after seeing results;
- changing K because the old K failed;
- selecting graph-dense subsets after inspecting graph density;
- learning a threshold on the holdout;
- altering relevance definitions after metrics appear.

Such changes start a new development hypothesis.

## Modern retrospective validation

Modern corpora may be used to test generalization. They are firewalled from the historical design process.

Example: Curlie/Homepage2Vec is modern. It can answer "does this frozen architecture generalize?" but cannot justify adding a 2021 technique to the G97 design.

## Provenance

For exact reproduction, store:

- branch name;
- commit SHA;
- workflow source;
- dataset URL/source ID;
- checksum when available;
- protocol file;
- controller/config blob;
- results artifact/log.

`experiments/archive/` is intended to snapshot exact historical branch sources. Reusable refactors under `src/g97/` are not substitutes for the exact frozen script when reproducing a historical metric.

## Claim levels

### Level 0 — implementation
Code runs and produces output.

### Level 1 — within-dataset observation
A metric changes on one benchmark.

### Level 2 — statistically supported benchmark result
Paired uncertainty excludes zero or another pre-specified criterion is met.

### Level 3 — cross-collection replication
The same architectural effect appears on independent datasets.

### Level 4 — external web generalization
The effect survives independent web data with frozen controller/protocol.

### Level 5 — system-level advantage
Ranking quality, freshness, crawl coverage, latency and resource cost jointly improve under a realistic search workload.

G97 Search has reached Level 2/3 for some citation-like ContextGraph effects, but has **not** reached Level 4/5 for the current adaptive web-search controller.

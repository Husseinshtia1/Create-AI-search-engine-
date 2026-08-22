# G97 Search

**A reproducible research project asking a historical engineering question:**

> If an AI engineer were placed at the end of 1996 and restricted to knowledge and techniques available by 31 December 1996, how far could it push web search — and which ideas actually survive empirical testing?

This repository is the canonical home of **G97 Search**. The GitHub repository name (`Create-AI-search-engine-`) is legacy; the scientific/project name is **G97 Search**.

## What this project is

G97 Search is not an attempt to claim that we "invented Google". It is an empirical reconstruction project. We freeze historically admissible ingredients, build explicit retrieval/crawling/indexing hypotheses, and test them against classic and modern retrospective datasets while separating:

- what was already known before 1997,
- what can be derived from that knowledge,
- what works experimentally,
- what fails,
- what remains only a hypothesis.

The project evolved from an initial Google/PageRank-style question into a broader search architecture centered on **strong baselines, typed evidence, selective intervention, and risk calibration**.

## Current central hypothesis

The strongest recurring architectural principle is now:

> **Preserve a strong baseline. Treat evidence types according to their role. Intervene only when the expected benefit of changing the baseline exceeds the risk.**

This emerged after repeated failures of aggressive query rewriting, global graph prestige, raw web-link boosting, anchor boosting, and unconditional candidate rescue.

A useful current decomposition is:

```text
Query
  -> Strong lexical baseline
  -> Observable failure state
  -> Predict benefit of candidate intervention
  -> Risk calibration
  -> choose one of:
       - NoAction
       - relational corroboration
       - external-description rescue
       - spelling/query repair
       - other historically admissible action
```

`NoAction` is a first-class decision.

## Empirical status

### Relational/citation graphs

| Dataset | Task | Main finding |
|---|---|---|
| CACM | historical ad-hoc IR | query-local ContextGraph improved MAP from 0.320769 to 0.334000 (+4.12%); bootstrap 95% CI for delta was positive |
| CISI | historical ad-hoc IR | global graph variants were significantly worse; local coupling moved MAP +1.02% but CI crossed zero |
| Cora | citation-network stress test | local citation corroboration improved MAP +1.72%, P@10 +4.64%, with positive CI |
| Citeseer | citation-network stress test | local citation corroboration improved MAP +0.80%, positive CI; global graph was only weakly positive |

**Interpretation:** global graph importance is weak/inconsistent; query-conditioned relational evidence is more promising when edge semantics themselves are relevance-bearing.

### Web hyperlink/anchor experiments

Raw hyperlink corroboration failed on WebKB. Semantic qualification recovered much of the damage but did not beat the text baseline. Anchor text was complementary, but unconditional anchor boosting/candidate rescue lost to simply searching deeper in body text under equal candidate budgets.

This led from v1 through v8:

```text
raw link boost
 -> lexical-qualified links
 -> anchor/context-qualified links
 -> sparse gated anchors
 -> exact evidence budget
 -> external-description rescue
 -> failure diagnosis
 -> risk-calibrated selective rescue
```

The v8 leave-one-university-out policy produced only a **very small weak-positive** Recall@30 change (+0.000066), so it is not considered validated.

### Current external validation

A frozen Curlie/Homepage2Vec protocol is in progress. The test population, sampling rule, relevance definition, candidate budget, controller parameters, and evaluator were frozen before Curlie retrieval metrics. Curlie is retrospective modern data and is not used to design the historically constrained system.

## Historical cutoff

The core design experiment uses a hard knowledge cutoff:

**31 December 1996**

Later datasets may be used only for retrospective validation. Their existence or content must not be used to introduce post-1996 techniques into the G97 design.

## Repository map

```text
src/g97/                 reusable search/evaluation primitives
experiments/             frozen benchmark implementations
configs/                 frozen controller/protocol configurations
docs/                    history, architecture, datasets, results, prior art
scripts/                 data/integrity/reproduction helpers
.github/workflows/       reproducible experiment runners
ROADMAP.md               complete development map from current state forward
```

The exact historical experiment scripts remain authoritative for reproducing a published run. `src/g97/` is the consolidated reusable layer and may evolve under version control.

## Reproducibility rules

1. **No qrels/labels before scoring** unless an experiment is explicitly a training experiment.
2. Every validation protocol is frozen before the first result.
3. Parser/acquisition fixes are allowed after failures only when they do not alter ranking rules.
4. A failed experiment stays failed; it is not retroactively renamed a success.
5. Development datasets are never re-described as independent validation.
6. Modern datasets are retrospective tests, not sources of post-cutoff design knowledge.
7. Every new intervention must be compared against the strongest fair baseline under equal or clearly stated resource budgets.

## Key documents

- [`docs/PROJECT_HISTORY.md`](docs/PROJECT_HISTORY.md) — how the project began and evolved.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — current technical architecture and evidence roles.
- [`docs/EXPERIMENT_REGISTRY.md`](docs/EXPERIMENT_REGISTRY.md) — all experiments, branches, outcomes, and status.
- [`docs/DATASETS.md`](docs/DATASETS.md) — datasets, roles, leakage constraints, and acquisition notes.
- [`docs/PRIOR_ART.md`](docs/PRIOR_ART.md) — pre-1997 prior art and what we must *not* claim as novel.
- [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) — frozen-run and anti-leakage methodology.
- [`ROADMAP.md`](ROADMAP.md) — full roadmap from today to a credible web-scale search system.

## Quick start

The reusable library is intentionally lightweight:

```bash
python -m pip install -e .
python -m g97.cli --help
```

Exact dataset-specific reproductions are under `experiments/` and GitHub Actions workflows.

## Scientific position

The project currently supports these claims only:

- classical IR + graph evidence can be reconstructed and tested using pre-1997 ideas;
- query-independent graph prestige is not consistently useful across our experiments;
- query-local relational corroboration is promising on citation-like graphs;
- raw web hyperlinks are not equivalent to relevance evidence;
- anchor text is genuine external lexical information but is noisy;
- deciding **whether to intervene** appears as important as designing the intervention itself.

It does **not** yet support a claim that G97 Search outperforms Google, PageRank, or production web search.

---

**Repository:** https://github.com/Husseinshtia1/Create-AI-search-engine-

**Project name:** G97 Search

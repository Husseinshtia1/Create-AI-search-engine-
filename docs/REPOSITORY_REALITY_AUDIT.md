# G97 Search — Repository Reality Audit

Audit date: 2026-08-22

This document records a direct audit of the canonical `main` branch and separates what is physically present in the repository from roadmap intent or historical conversation state.

## Verified on `main`

- Canonical project identity is documented as **G97 Search**.
- `README.md`, `ROADMAP.md`, `pyproject.toml`, `configs/`, `docs/`, `experiments/`, `src/`, `tests/`, and `.github/workflows/` are present.
- `src/g97/` contains consolidated retrieval, graph, controller, metrics, and CLI primitives.
- `tests/test_core.py` exists and exercises core invariants.
- `.github/workflows/g97-core-ci.yml` exists and is configured for pushes and pull requests affecting the consolidated core.
- `configs/webkb_v8_controller_frozen.json` contains the serialized WebKB-only v8 controller, including its ten-feature order and `threshold_tau = 12.381009120265105`.
- `experiments/archive/` contains historical PR snapshots beginning with the early CACM sequence and extending through the Curlie-era PR archive.

## CI status

The latest audited `main` commit is the commit that added G97 Core CI. No combined status checks were exposed for that commit by the GitHub interface available during this audit. Therefore CI must be treated as **configured but not yet independently verified PASS**.

Do not convert this into a PASS claim until a concrete workflow/check result is available.

## Phase 0 reality check

Phase 0 is substantially implemented, but its exit gate is not yet fully demonstrated.

The remaining evidence needed to close Phase 0 is:

1. a clean clone/install/test reproduction result;
2. a documented reproduction of CACM;
3. a documented reproduction of CISI;
4. a documented reproduction of at least one WebKB development run;
5. a recorded CI PASS or equivalent clean-environment test result.

The archive-consolidation deliverable itself appears materially complete through the current Curlie sequence and should no longer be treated as the main unknown. The remaining issue is reproducibility proof, not merely file presence.

## Phase 1 reality check — Curlie

PR #20 remains open and contains the frozen Curlie external-validation protocol and implementation. Its protocol explicitly freezes:

- the published Homepage2Vec test split;
- deterministic 20,000-UID sampling by smallest SHA1(uid);
- no class balancing or graph-density filtering;
- top-level shared-class relevance;
- body TF-IDF;
- sample-internal inbound-anchor external descriptions;
- candidate budget 30;
- WebKB-only frozen controller;
- paired bootstrap evaluation.

The canonicalization appendix also freezes host-level node identity before graph extraction. Multiple selected UIDs sharing one canonical host are intentionally treated as ambiguous and cannot receive graph edges.

The correct next Curlie decision is therefore not to tune parsing or alter the sample after seeing graph density. The next result must be one of:

- `FEASIBLE_FOR_FROZEN_RETRIEVAL` and then run the frozen evaluator;
- feasibility failure and record it as such;
- missing/incomplete source data and repair acquisition only if ranking/canonicalization semantics remain unchanged.

## Correctness gap found during audit

The consolidated `FrozenController` previously accepted serialized arrays of inconsistent length. Because scoring used Python `zip()`, a malformed controller could silently truncate dimensions instead of failing. This is a reproducibility/integrity defect.

The audit branch fixes this by enforcing:

- non-empty controller dimension;
- equal dimensions for means, standard deviations, and both centroids;
- finite threshold and finite parameters;
- non-negative standard deviations;
- finite runtime feature values;
- `feature_order` length equality when loading JSON.

Regression tests are included.

## Priority order after this audit

### P0 — integrity and reproducibility

- merge controller-integrity validation after CI/review;
- obtain a concrete core CI result;
- prove Phase 0 exit-gate reproductions.

### P1 — Curlie frozen external validation

- execute feasibility exactly as frozen;
- if feasible, run the frozen evaluator once without tuning;
- record positive, null/negative, or feasibility-failure outcome.

### P2 — Strong Lexical Foundation

Only after the external-validation state is recorded, freeze the next independent lexical experiment. Do not use Curlie labels/results to redesign the v8 controller.

### P3 — crawler/TTQ implementation

Crawler development can proceed in parallel only if it does not mutate the frozen retrieval protocol or contaminate the independent lexical validation design.

## Research invariants

1. No result claim without an archived experiment artifact.
2. No validation protocol changes after first metric inspection.
3. No silent controller/config truncation or coercion.
4. Failed and null experiments remain part of the project record.
5. Modern retrospective data cannot introduce post-1996 design knowledge into the historically constrained architecture.
6. Resource budgets must be explicit when comparing interventions against stronger lexical baselines.

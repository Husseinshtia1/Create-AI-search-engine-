# Experiment Registry

This registry is the authoritative index of G97 Search experiments. Frozen validations, development experiments, diagnostics, and failed runs are intentionally kept distinct.

## Status vocabulary

- **FROZEN VALIDATION** — protocol fixed before first metric on that evaluation set.
- **DEVELOPMENT** — data already seen; useful for mechanism design, not independent validation.
- **DIAGNOSTIC** — format/feasibility/causal inspection; not a ranking claim.
- **FAILED** — hypothesis or implementation run did not meet its stated success criterion.
- **WEAK POSITIVE** — positive direction too small/unstable to claim validation.

## Historical IR / graph experiments

| ID | Dataset | Purpose | Result / status | Source ref |
|---|---|---|---|---|
| G97-CACM-001/002 | CACM | A0–A6 lexical/global/query-local graph benchmark | A6 ContextGraph MAP 0.320769 -> 0.334000 (+4.12%); positive bootstrap CI. Global graph variants slightly worse. **FROZEN VALIDATION** | PR #1/#2; `experiments/g97-cacm/` |
| G97-CISI-DIAG | CISI | inspect SMART/CISI format and `.X` semantics | format-only, no scoring. **DIAGNOSTIC** | PR #3 |
| G97-CISI-001 | CISI | independent replication with weighted bibliographic coupling | global degree/recursive coupling significantly worse; local coupling +1.02% MAP, CI crossed zero. **FROZEN VALIDATION** | PR #4; `experiments/g97-cisi/` |
| G97-CORA-001 | Cora | citation-network mechanism stress test | local citation +1.72% MAP; positive CI. **FROZEN STRESS TEST** | PR #5 |
| G97-CRANFIELD-001 | Cranfield | lexical-layer independent benchmark | TF-IDF MAP 0.289093 vs C96 0.182664; shows no universal lexical winner. **FROZEN TEXT BENCHMARK** | PR #6 |
| G97-CITESEER-001 | Citeseer | citation-network mechanism stress test | local citation +0.80% MAP with positive CI; global graph tiny positive. **FROZEN STRESS TEST** | PR #7 |

## Web hyperlink experiments

| ID | Dataset | Hypothesis | Result / status | Source ref |
|---|---|---|---|---|
| G97-WEBKB-v1 | Cornell/Texas/Wisconsin WebKB | raw local hyperlink corroboration | pooled MAP about -6.8% vs text; global graph also worse. **FAILED / FROZEN STRESS TEST** | PR #8 |
| G97-WEB-v2 | Washington WebKB | qualify local links by lexical source-target consistency | recovered part of raw-link damage but still below text; MAP about -2.43%. **FAILED / FROZEN VALIDATION** | PR #9 |
| G97-WEB-v3-DIAG | original CMU WebKB | inspect anchor/context availability | confirms page text, anchor words, neighborhood words. **DIAGNOSTIC** | PR #10 |
| G97-WEB-v3 | seen WebKB universities | compare raw, lexical-qualified, anchor-only, anchor+context | anchor-only approached baseline best; more context did not help. **DEVELOPMENT** | PR #11 |
| Sector-DIAG-001/002 | CMU Industry Sector | find independent HTML/link corpus | acquisition/source problems; no ranking result. **DIAGNOSTIC** | PR #12/#13 |
| G97-WEB-v4 | WebKB `misc` unseen holdout within same family | top-decile gated anchor boost | MAP 0.458778 -> 0.458764; below text. Gate unintentionally admitted ~41.2% due ties. **FAILED HOLDOUT** | PR #14 |
| G97-WEB-v5 | seen WebKB universities | exact 10% evidence budget | still below text; intervention losses dominated wins. **FAILED DEVELOPMENT** | PR #15 |
| G97-WEB-v6 | seen WebKB universities | anchor as independent external-description retriever/candidate rescue | anchor found deep relevant documents, but equal-budget hybrids lost to deeper body retrieval. **FAILED GENERAL RESCUE** | PR #16 |
| G97-WEB-v7 | seen WebKB universities | hand-written failure-diagnosed rescue | Recall@30 decreased; gate produced 3 wins vs 69 losses. **FAILED DEVELOPMENT** | PR #17 |
| G97-v7-PREDICT | leave-one-university-out WebKB | test whether rescue benefit is predictable | OOF ROC-AUC ~0.7436; top-decile precision ~32.6% vs 12.8% base rate. Natural score>0 policy still hurt recall. **DIAGNOSTIC POSITIVE** | PR #18 |
| G97-WEB-v8 | leave-one-university-out WebKB | training-fold-only risk-calibrated rescue | Recall@30 0.244735 -> 0.244801 (+0.000066), gate ~2.6%; unstable across universities. **WEAK POSITIVE / NOT VALIDATED** | PR #19 |

## External web validation

| ID | Dataset | Protocol | Current status | Source ref |
|---|---|---|---|---|
| G97-CURLIE-001 | Homepage2Vec/Curlie | published test split only; 20k smallest SHA1(uid); shared top-level class relevance; body TF-IDF; internal inbound anchors; candidate budget 30; WebKB-only serialized controller | protocol/evaluator/controller frozen before Curlie retrieval metrics. Large streaming extraction and feasibility check in progress; parser-only fixes allowed. **FROZEN EXTERNAL VALIDATION** | PR #20 |

## Key numeric record

### CACM

```text
A0 C96 MAP                 0.320769
A1 global degree          0.317086
A2 recursive authority    0.315061
A3 local direct link      0.332511
A4 local coupling         0.328455
A5 local co-citation      0.331601
A6 ContextGraph           0.334000
A6 relative MAP gain      +4.12%
```

### CISI

```text
A0 C96 MAP                 0.238474
Global weighted degree    0.229110
Global recursive coupling 0.230799
Local weighted coupling   0.240911
```

### Cora

```text
Text MAP                   0.287237
Local citation MAP         0.292174
P@10                       0.548966 -> 0.574446
```

### Citeseer

```text
Text MAP                   0.284816
Local citation MAP         0.287093
P@10                       0.553865 -> 0.570954
```

### WebKB raw links

```text
Pooled Text MAP            0.561372
Pooled Local Link MAP      0.523075
```

### Washington v2

```text
Text MAP                   0.580321
Raw local link             0.553640
Qualified local link       0.566208
```

### WebKB v8 OOF

```text
Body Recall@30             0.244735
Risk-calibrated policy     0.244801
Delta                      +0.000066
Gate rate                  ~2.59%
```

## Reproduction and provenance

Exact frozen experiment implementations live in their original branches/PRs and, as migration proceeds, under `experiments/archive/`. This registry intentionally points to PR numbers because their descriptions preserve the pre-result hypothesis/protocol statements.

No failure is deleted when a later version supersedes it. The sequence of failures is part of the scientific record.

# G97 Curlie External Validation — Frozen Feasibility Result

## Status

**FROZEN EXTERNAL VALIDATION: FEASIBILITY FAILURE**

This result records the outcome of the frozen Homepage2Vec/Curlie external-validation feasibility gate defined before Curlie retrieval metrics were produced.

The protocol must not be resized, class-balanced, graph-density filtered, or otherwise altered post hoc in response to this result.

## Frozen protocol

The external-validation branch fixed the following before retrieval evaluation:

- universe: published Homepage2Vec test split only;
- deterministic sample: 20,000 UIDs with smallest SHA1(uid);
- no category balancing;
- no graph-density filtering;
- relevance: shared published top-level class;
- body retrieval: classical TF-IDF;
- external descriptions: inbound anchor text reconstructed only from sample-internal links;
- candidate budget: 30;
- controller: serialized WebKB-only v8 controller;
- anchor-feasibility requirement: at least 1,000 distinct inbound targets.

## Observed frozen feasibility run

GitHub Actions run:

- workflow: `G97 Curlie Streaming Feasibility`
- run number: 9
- run id: `32577562508`
- branch head tested: `4b495756e0958e9c608083a0f33bb432040a17df`

The 13.7 GiB compressed HTML stream completed successfully. Metadata checksums passed and the frozen 20,000-document sample was fully present.

Observed counts:

```text
published_test_uids       88559
selected_uids             20000
urls_present              20000
labels_present            20000
html_present              20000
missing_urls              0
missing_labels            0
missing_html              0
unique_canonical_hosts    20000
ambiguous_hosts           0
directed_internal_edges   2720
anchor_strings            4928
distinct_inbound_targets  166
required_inbound_targets  1000
```

The extractor therefore returned:

```text
INSUFFICIENT_INTERNAL_ANCHOR_GRAPH_OR_MISSING_DATA
```

Because all URLs, labels and HTML records were present, the operative reason is not missing data. It is insufficient internal anchor-graph coverage under the frozen 20,000-UID sample.

## Scientific interpretation

The feasibility ratio was:

```text
166 / 1000 = 0.166
```

Only 16.6% of the predeclared minimum number of distinct inbound targets was available.

Therefore the frozen protocol does not provide enough sample-internal anchor coverage to run the intended WebKB-v8 external-description rescue test as specified.

This is **not** a negative retrieval result for the v8 controller, because the frozen evaluator was correctly gated off before ranking evaluation. It is a **feasibility failure of the frozen Curlie sampling/graph protocol**.

## Required consequence

Per the predeclared exit outcomes:

1. do not resize the 20,000-UID sample after observing graph density;
2. do not filter the sample for link-rich pages;
3. do not relax the 1,000-target threshold retroactively;
4. do not tune v8 on Curlie;
5. retain this outcome as the final status of `G97-CURLIE-001`;
6. move forward to an independently frozen lexical-foundation experiment and later web-scale validation with a dataset whose link graph is structurally suitable for the intended test.

## Provenance

The frozen protocol and tooling originated in PR #20 (`g97-curlie-external-validation-freeze-001`). The historical branch remains part of the experiment archive even though the PR later became non-mergeable after repository consolidation.

This document records the observed outcome without modifying the frozen protocol or interpreting it as a retrieval-quality result.

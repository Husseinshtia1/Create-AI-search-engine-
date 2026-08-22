# Curlie Full-Directory Graph Diagnostic — POST-FAILURE, NOT VALIDATION

Purpose: diagnose why the preregistered 20k Curlie validation protocol failed its internal-anchor feasibility gate. This analysis occurs **after** that failure and therefore cannot serve as external validation of G97-Web v8.

Frozen diagnostic question before execution:
- Universe: every UID with URL + HTML in the published Homepage2Vec/Curlie v5 files (no sampling, labels unused).
- Canonical target identity: host-level, lowercase, strip leading `www.`, default ports and trailing hostname dot; ambiguous host mappings discarded.
- Parse every HTML page and count directed hyperlinks whose target host maps to another page in the full universe.
- Report total valid pages/hosts, directed internal edges, distinct inbound targets, fraction of corpus with >=1 inbound link, and anchor-text string count.
- Do not compute relevance, ranking, v8 controller scores, or any retrieval metric.

Interpretation:
- This can distinguish `random induced-subgraph sparsity` from `directory corpus itself has weak internal linkage`.
- It cannot repair or replace the failed 20k preregistered validation and cannot justify changing that protocol post hoc.

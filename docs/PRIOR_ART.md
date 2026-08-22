# Prior Art and Historical Boundary

G97 Search is explicitly historical. The project must not claim as novel ideas that were already published or implemented by 31 December 1996.

## Known pre-1997 foundations relevant to this project

### Classical information retrieval
- vector-space retrieval and TF-IDF;
- probabilistic retrieval and BM-family ideas;
- stemming, stopwording, term weighting;
- relevance feedback / pseudo-feedback families;
- clustering and nearest-neighbor retrieval;
- field/proximity and phrase evidence.

### Citation and bibliographic evidence
Bibliographic coupling and co-citation predate the Web and were already used as document-relational signals. Work before 1997 also explored combining text with citation/link structure.

The project therefore **does not claim novelty** for:

```text
text + citations
text + bibliographic coupling
text + co-citation
link-aware retrieval
```

### Savoy (1996)
Work in 1996 explicitly investigated extended vector processing for hypertext retrieval using link information such as explicit references, bibliographic coupling and co-citation.

### Fox / Nunn / Lee and related earlier IR combination work
Earlier CACM experiments investigated combining multiple concept/evidence classes such as terms, authors, links and citation-derived structures. This is direct prior art against any broad claim that combining independent evidence classes is new.

### HyPursuit (1996)
HyPursuit used content-link hypertext clustering/search structures. Therefore `content + link structure + local/cluster organization` is not by itself a novelty claim.

### Selective relevance feedback and expert combination
TREC-5-era systems already used selective feedback and learned/engineered combinations of multiple retrieval components. Therefore the project does not claim novelty for "selective feedback" or "mixture of experts" in general.

### Database/resource selection
Decision-theoretic and cost-aware collection/database selection existed before the cutoff. A generic statement like "choose a search action based on expected cost/value" requires careful prior-art comparison.

### Anchor text as target description
Early Web search systems before Google already propagated anchor text or link-associated words to target pages. Therefore:

```text
ExternalDescription(target) = inbound anchor text
```

is an old idea, not a G97 invention.

### LSM-style indexing
The Log-Structured Merge-tree was published in 1996. A main-index + searchable-delta architecture is therefore historically admissible, but not novel in the general storage sense.

## What the project is currently testing that is narrower

The current candidate contribution is not one isolated primitive. It is an architecture that explicitly separates evidence roles and makes intervention itself a decision:

```text
strong baseline
+ typed evidence roles
+ query/result-state diagnostics
+ predicted benefit of a specific intervention
+ risk calibration
+ NoAction as a first-class outcome
```

The specific bounded ContextGraph form also remains an empirical design rather than a proven novelty claim:

```text
query -> lexical seeds -> typed local relational evidence -> bounded corroboration
```

Before publication/patent/novelty language, this architecture requires a systematic patent and literature search beyond the sources already checked.

## Language policy for publications

Use:
- "we observed";
- "we derived";
- "our experiments suggest";
- "we test the hypothesis";
- "a candidate architectural contribution".

Avoid until proven:
- "first ever";
- "invented";
- "no one has done this";
- "guaranteed better than PageRank/Google".

## Historical-admissibility rule

A component may enter the G97 design only if one of the following is documented:

1. it was published/implemented by 31 Dec 1996; or
2. it is a direct mathematical/engineering derivation using only information and techniques available by that date.

Modern datasets, modern implementation languages, CI systems and compute infrastructure may be used to execute/validate the historical design, but they are not evidence that a modern algorithm was historically admissible.

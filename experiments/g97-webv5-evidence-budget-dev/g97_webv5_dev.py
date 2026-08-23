#!/usr/bin/env python3
"""Development-only test of G97-Web v5 exact Evidence Budget.

Uses the already-seen four named WebKB universities. This run may guide a
future architecture, but it is NOT independent validation. The unseen `misc`
holdout is deliberately not loaded.

Only one structural repair is tested relative to v4: implement the intended
10% sparsity as an exact query-local evidence budget, immune to percentile ties.
No label-dependent threshold or lambda tuning is performed.
"""

import argparse, collections, importlib.util, math
from pathlib import Path

HERE = Path(__file__).resolve()
V4_PATH = HERE.parents[1] / "g97-webv4-misc-holdout" / "g97_webv4_misc.py"
spec = importlib.util.spec_from_file_location("g97v4", V4_PATH)
v4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v4)

UNIS = ("cornell", "texas", "washington", "wisconsin")
CLASSES = v4.CLASSES


def load_named(root):
    base = v4.find_class_root(root)
    docs, paths = {}, {}
    for cls in CLASSES:
        for uni in UNIS:
            d = base / cls / uni
            if not d.exists():
                continue
            for f in d.iterdir():
                if not f.is_file():
                    continue
                u = v4.url_from_filename(f.name)
                if not u:
                    continue
                try:
                    body, txt = v4.read_any(f)
                except Exception:
                    continue
                docs[u] = {"text": txt, "html": body, "uni": uni}
                paths[u] = str(f)
    return docs, paths


def infer_labels(paths):
    labels = {}
    for u, p in paths.items():
        q = p.replace("\\", "/")
        for cls in CLASSES:
            for uni in UNIS:
                if f"/{cls}/{uni}/" in q:
                    labels[u] = cls
                    break
            if u in labels:
                break
    return labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", default="results.tsv")
    a = ap.parse_args()

    docs, paths = load_named(a.root)
    vec, norm, df, inv = v4.build_vectors(docs)
    outlinks, anchors = v4.extract_directed_anchors(docs)
    N = len(docs)
    byuni = collections.defaultdict(set)
    for d, meta in docs.items():
        byuni[meta["uni"]].add(d)

    names = ["T0_TEXT", "T1_ANCHOR_ALL", "T2_V5_EXACT_BUDGET"]
    runs = {n: {} for n in names}
    total_positive = 0
    total_budget = 0

    # RANKING: labels are not loaded here.
    for q in sorted(docs):
        uni = docs[q]["uni"]
        allowed = byuni[uni]
        base = {d: s for d, s in v4.lexical_scores(q, vec, norm, inv).items() if d in allowed}
        if not base:
            continue
        seeds = v4.rank(base)[:10]
        mx = max(base.values()) or 1.0
        contrib = []  # (anchor_rel, src, dst, weighted_value)
        for s in seeds:
            conf = base[s] / mx
            scarcity = 1.0 / (1.0 + math.log(1.0 + len(outlinks.get(s, ()))))
            for d in outlinks.get(s, ()):
                if d == q or d not in base or d not in allowed:
                    continue
                at = " ".join(anchors.get((s, d), ()))
                if not at:
                    continue
                av, an = v4.temp_vector(at, df, N)
                if not av:
                    continue
                ar = v4.cosine_sparse(vec[q], av, norm[q], an)
                if ar > 0:
                    contrib.append((ar, s, d, conf * ar * scarcity))

        e_all = collections.Counter()
        for ar, s, d, val in contrib:
            e_all[d] += val

        # Exact 10% evidence budget. Sorting provides deterministic tie-breaking;
        # ties cannot expand the budget beyond ceil(0.10*m).
        ordered = sorted(contrib, key=lambda x: (-x[0], x[1], x[2]))
        budget = max(1, math.ceil(0.10 * len(ordered))) if ordered else 0
        e_budget = collections.Counter()
        for ar, s, d, val in ordered[:budget]:
            e_budget[d] += val
        total_positive += len(ordered)
        total_budget += budget

        scored = {
            "T0_TEXT": base,
            "T1_ANCHOR_ALL": v4.rerank(base, e_all),
            "T2_V5_EXACT_BUDGET": v4.rerank(base, e_budget),
        }
        for name, scores in scored.items():
            runs[name][q] = v4.rank(scores)

    # EVALUATION: labels become visible only now.
    labels = infer_labels(paths)
    per = {n: {} for n in names}
    avg = {}
    for name, run in runs.items():
        ms = []
        for q, r in run.items():
            if q not in labels:
                continue
            rel = {d for d in byuni[docs[q]["uni"]] if d != q and labels.get(d) == labels[q]}
            if not rel:
                continue
            m = {
                "AP": v4.ap(r, rel),
                "P10": v4.pat(r, rel, 10),
                "nDCG10": v4.ndcg(r, rel, 10),
                "MRR": v4.rr(r, rel),
            }
            per[name][q] = m
            ms.append(m)
        avg[name] = {k: sum(x[k] for x in ms) / len(ms) for k in ["AP", "P10", "nDCG10", "MRR"]}

    baseap = {q: m["AP"] for q, m in per["T0_TEXT"].items()}
    with open(a.out, "w") as f:
        f.write("variant\tMAP\tP@10\tnDCG@10\tMRR\tAP_delta\tCI95_low\tCI95_high\twins\tlosses\tties\n")
        for name in names:
            sig = (0, 0, 0, 0, 0, 0) if name == "T0_TEXT" else v4.bootstrap(baseap, {q: m["AP"] for q, m in per[name].items()})
            r = avg[name]
            f.write(f"{name}\t{r['AP']:.6f}\t{r['P10']:.6f}\t{r['nDCG10']:.6f}\t{r['MRR']:.6f}\t{sig[0]:.6f}\t{sig[1]:.6f}\t{sig[2]:.6f}\t{sig[3]}\t{sig[4]}\t{sig[5]}\n")

    edges = sum(len(v) for v in outlinks.values())
    print("DEVELOPMENT ONLY: named WebKB universities were previously seen")
    print("misc_holdout_loaded", False)
    print("pages", len(docs), "directed_internal_edges", edges, "queries", len(runs["T0_TEXT"]))
    print("university_counts", {u: len(byuni[u]) for u in UNIS})
    print("exact_budget", total_budget, "of", total_positive,
          "fraction", (total_budget / total_positive if total_positive else 0.0))
    print(open(a.out).read())


if __name__ == "__main__":
    main()

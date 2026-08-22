#!/usr/bin/env python3
"""Frozen G97-Web v4 evaluation on unseen WebKB misc pages.

This is a holdout test, not a development sweep. The four named universities
were seen previously; `misc` was not used for ranking/tuning in those runs.
The data were collected in January 1997, so this is RETROSPECTIVE validation
only under the project's 31-Dec-1996 design cutoff. It must not alter design.

PRE-REGISTERED BEFORE HOLDOUT RESULTS:
- task: query-by-example retrieval; relevant = same page class as query
- classes: course, faculty, student, project, staff (same semantic five-class
  scope used in the earlier WebKB development experiment)
- baseline: classical TF-IDF cosine
- seeds: top 10 lexical results
- relation: directed HTML hyperlink; anchor describes its target
- lambda = 0.50, unchanged
- source scarcity = 1 / (1 + ln(1 + outdegree(source)))
- Anchor-All control: every positive anchor/query similarity can contribute
- G97-Web-v4 gate: only positive anchor similarities in the query-local top
  decile (nearest-rank 90th percentile) can contribute
- contribution = seed_confidence * anchor_relevance * source_scarcity
- graph cannot manufacture a candidate with zero lexical relevance
- labels are not accessed until every ranking has been produced
- no tuning after seeing misc results
"""

import argparse, collections, gzip, html, math, random, re
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
A_RE = re.compile(r"(?is)<a\s+[^>]*href\s*=\s*([\"']?)([^\"'\s>]+)\1[^>]*>(.*?)</a\s*>")
TAG_RE = re.compile(r"(?is)<[^>]+>")
SCRIPT_RE = re.compile(r"(?is)<(script|style)\b.*?</\1\s*>")
CLASSES = ("course", "faculty", "student", "project", "staff")


def toks(s):
    return [x.lower() for x in TOKEN_RE.findall(s or "")]


def textify(s):
    s = SCRIPT_RE.sub(" ", s or "")
    s = TAG_RE.sub(" ", s)
    return html.unescape(re.sub(r"\s+", " ", s)).strip()


def canon(u):
    try:
        p = urlsplit(u.strip())
        if not p.scheme or not p.netloc:
            return None
        scheme = p.scheme.lower()
        host = p.netloc.lower()
        path = re.sub(r"/+", "/", p.path or "/")
        if path.endswith("/index.html"):
            path = path[:-10] or "/"
        if path.endswith("/index.htm"):
            path = path[:-9] or "/"
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
        return urlunsplit((scheme, host, path, p.query, ""))
    except Exception:
        return None


def url_from_filename(name):
    if name.endswith(".gz"):
        name = name[:-3]
    return canon(name.replace("^", "/"))


def read_any(path):
    b = path.read_bytes()
    if b[:2] == b"\x1f\x8b":
        b = gzip.decompress(b)
    raw = b.decode("latin1", "replace")
    parts = re.split(r"\r?\n\r?\n", raw, maxsplit=1)
    body = parts[1] if len(parts) > 1 else raw
    return body, textify(body)


def find_class_root(root):
    root = Path(root)
    # Archive layouts differ by one or more wrapper directories.
    for p in [root] + [x for x in root.rglob("course") if x.is_dir()]:
        base = p.parent if p.name == "course" else p
        if all((base / c).is_dir() for c in CLASSES):
            return base
    raise RuntimeError("Could not locate WebKB class directories")


def load_misc(root):
    base = find_class_root(root)
    docs, paths = {}, {}
    for cls in CLASSES:
        d = base / cls / "misc"
        if not d.exists():
            continue
        for f in d.iterdir():
            if not f.is_file():
                continue
            u = url_from_filename(f.name)
            if not u:
                continue
            try:
                body, txt = read_any(f)
            except Exception:
                continue
            docs[u] = {"text": txt, "html": body}
            paths[u] = str(f)
    return docs, paths


def build_vectors(docs):
    tf, df = {}, collections.Counter()
    for u, d in docs.items():
        c = collections.Counter(toks(d["text"]))
        tf[u] = c
        df.update(c.keys())
    N = len(docs)
    vec, norm = {}, {}
    for u, c in tf.items():
        v = {}
        for t, f in c.items():
            idf = math.log((N + 1) / (df[t] + 1)) + 1.0
            v[t] = (1.0 + math.log(f)) * idf
        n = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vec[u], norm[u] = v, n
    inv = collections.defaultdict(list)
    for u, v in vec.items():
        for t, w in v.items():
            inv[t].append((u, w))
    return vec, norm, df, inv


def lexical_scores(q, vec, norm, inv):
    dot = collections.defaultdict(float)
    for t, qw in vec[q].items():
        for d, dw in inv.get(t, ()): 
            if d != q:
                dot[d] += qw * dw
    return {d: z / (norm[q] * norm[d]) for d, z in dot.items() if z > 0}


def temp_vector(text, df, N):
    c = collections.Counter(toks(text))
    v = {}
    for t, f in c.items():
        if t not in df:
            continue
        idf = math.log((N + 1) / (df[t] + 1)) + 1.0
        v[t] = (1.0 + math.log(f)) * idf
    n = math.sqrt(sum(x * x for x in v.values())) or 1.0
    return v, n


def cosine_sparse(a, b, na, nb):
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items()) / (na * nb) if na and nb else 0.0


def extract_directed_anchors(docs):
    # anchors[(src,tgt)] contains the actual directed anchor descriptions.
    anchors = collections.defaultdict(list)
    out = collections.defaultdict(set)
    for src, d in docs.items():
        for m in A_RE.finditer(d["html"]):
            tgt = canon(urljoin(src, html.unescape(m.group(2))))
            if not tgt or tgt not in docs or tgt == src:
                continue
            atext = textify(m.group(3))
            out[src].add(tgt)
            if atext:
                anchors[(src, tgt)].append(atext)
    return out, anchors


def rank(scores):
    return [d for d, _ in sorted(scores.items(), key=lambda x: (-x[1], x[0]))]


def rerank(base, evidence, lam=0.50):
    return {d: s * (1.0 + lam * (evidence.get(d, 0.0) / (1.0 + evidence.get(d, 0.0)))) for d, s in base.items()}


def q90_nearest_rank(xs):
    ys = sorted(x for x in xs if x > 0)
    if not ys:
        return None
    idx = max(0, math.ceil(0.90 * len(ys)) - 1)
    return ys[idx]


def ap(r, rel):
    if not rel:
        return None
    h, s = 0, 0.0
    for i, d in enumerate(r, 1):
        if d in rel:
            h += 1
            s += h / i
    return s / len(rel)


def pat(r, rel, k):
    return sum(d in rel for d in r[:k]) / k


def rr(r, rel):
    for i, d in enumerate(r, 1):
        if d in rel:
            return 1.0 / i
    return 0.0


def ndcg(r, rel, k):
    dcg = sum((1.0 if d in rel else 0.0) / math.log2(i + 2) for i, d in enumerate(r[:k]))
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(k, len(rel))))
    return dcg / ideal if ideal else 0.0


def bootstrap(a, b, n=5000, seed=1996):
    qs = sorted(set(a) & set(b))
    ds = [b[q] - a[q] for q in qs]
    rng = random.Random(seed)
    bs = []
    for _ in range(n):
        bs.append(sum(ds[rng.randrange(len(ds))] for __ in ds) / len(ds))
    bs.sort()
    return (sum(ds) / len(ds), bs[int(.025 * (n - 1))], bs[int(.975 * (n - 1))],
            sum(x > 1e-15 for x in ds), sum(x < -1e-15 for x in ds), sum(abs(x) <= 1e-15 for x in ds))


def infer_labels(paths):
    labels = {}
    for u, p in paths.items():
        q = p.replace("\\", "/")
        for cls in CLASSES:
            if f"/{cls}/misc/" in q:
                labels[u] = cls
                break
    return labels


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    p.add_argument("--out", default="results.tsv")
    a = p.parse_args()

    docs, paths = load_misc(a.root)
    vec, norm, df, inv = build_vectors(docs)
    outlinks, anchors = extract_directed_anchors(docs)
    N = len(docs)

    run_names = ["T0_TEXT", "T1_ANCHOR_ALL", "T2_G97_WEB_V4_GATED"]
    runs = {name: {} for name in run_names}
    gate_stats = []

    # RANKING PHASE: no labels are read here.
    for qi, q in enumerate(sorted(docs)):
        base = lexical_scores(q, vec, norm, inv)
        if not base:
            continue
        seeds = rank(base)[:10]
        mx = max(base.values()) or 1.0
        contributions = []  # (candidate, raw contribution, anchor relevance)
        for s in seeds:
            conf = base[s] / mx
            scarcity = 1.0 / (1.0 + math.log(1.0 + len(outlinks.get(s, ()))))
            for d in outlinks.get(s, ()):
                if d == q or d not in base:
                    continue
                at = " ".join(anchors.get((s, d), ()))
                if not at:
                    continue
                av, an = temp_vector(at, df, N)
                if not av:
                    continue
                ar = cosine_sparse(vec[q], av, norm[q], an)
                if ar > 0:
                    contributions.append((d, conf * ar * scarcity, ar))

        threshold = q90_nearest_rank([x[2] for x in contributions])
        e_all = collections.Counter()
        e_gate = collections.Counter()
        for d, value, ar in contributions:
            e_all[d] += value
            if threshold is not None and ar >= threshold:
                e_gate[d] += value
        gate_stats.append((len(contributions), sum(1 for _, _, ar in contributions if threshold is not None and ar >= threshold)))

        scored = {
            "T0_TEXT": base,
            "T1_ANCHOR_ALL": rerank(base, e_all),
            "T2_G97_WEB_V4_GATED": rerank(base, e_gate),
        }
        for name, x in scored.items():
            runs[name][q] = rank(x)

    # EVALUATION PHASE: labels become visible only after every ranking exists.
    labels = infer_labels(paths)
    byclass = collections.defaultdict(set)
    for d, c in labels.items():
        byclass[c].add(d)

    per = {name: {} for name in run_names}
    avg = {}
    for name, run in runs.items():
        ms = []
        for q, r in run.items():
            if q not in labels:
                continue
            rel = byclass[labels[q]] - {q}
            if not rel:
                continue
            m = {"AP": ap(r, rel), "P10": pat(r, rel, 10), "nDCG10": ndcg(r, rel, 10), "MRR": rr(r, rel)}
            per[name][q] = m
            ms.append(m)
        avg[name] = {k: sum(x[k] for x in ms) / len(ms) for k in ["AP", "P10", "nDCG10", "MRR"]}

    baseap = {q: m["AP"] for q, m in per["T0_TEXT"].items()}
    with open(a.out, "w") as f:
        f.write("variant\tMAP\tP@10\tnDCG@10\tMRR\tAP_delta\tCI95_low\tCI95_high\twins\tlosses\tties\n")
        for name in run_names:
            sig = (0, 0, 0, 0, 0, 0) if name == "T0_TEXT" else bootstrap(baseap, {q: m["AP"] for q, m in per[name].items()})
            r = avg[name]
            f.write(f"{name}\t{r['AP']:.6f}\t{r['P10']:.6f}\t{r['nDCG10']:.6f}\t{r['MRR']:.6f}\t{sig[0]:.6f}\t{sig[1]:.6f}\t{sig[2]:.6f}\t{sig[3]}\t{sig[4]}\t{sig[5]}\n")

    n_edges = sum(len(v) for v in outlinks.values())
    active = sum(x for _, x in gate_stats)
    possible = sum(x for x, _ in gate_stats)
    print("FROZEN HOLDOUT: WebKB misc; no post-result tuning")
    print("RETROSPECTIVE: pages collected Jan 1997; not a design input under 31-Dec-1996 cutoff")
    print("pages", len(docs), "directed_internal_edges", n_edges, "queries", len(runs["T0_TEXT"]))
    print("class_counts", {c: len(byclass[c]) for c in CLASSES})
    print("eligible_anchor_contributions", active, "of", possible,
          "fraction", (active / possible if possible else 0.0))
    print(open(a.out).read())


if __name__ == "__main__":
    main()

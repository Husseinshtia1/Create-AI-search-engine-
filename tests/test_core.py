from g97.controller import FrozenController
from g97.graph import bounded_rerank, query_local_channel
from g97.retrieval import build_tfidf_index, exact_budget_rescue


def test_tfidf_retrieval_excludes_self():
    texts = {
        "a": "distributed database systems",
        "b": "distributed database research",
        "c": "compiler parsing",
    }
    idx = build_tfidf_index(texts)
    ranked = idx.retrieve("a", idx.vectors["a"], k=3)
    assert ranked
    assert ranked[0][0] == "b"
    assert all(doc != "a" for doc, _ in ranked)


def test_graph_cannot_create_zero_text_candidate():
    base = {"a": 2.0, "b": 1.0}
    relation = {"a": {"b": 1.0, "c": 5.0}}
    evidence, _ = query_local_channel(base, ["a"], relation)
    scored = bounded_rerank(base, evidence, lam=0.5)
    assert "c" not in scored
    assert scored["b"] >= base["b"]


def test_exact_rescue_has_fixed_budget_and_unique_ids():
    body = [(f"b{i}", 100 - i) for i in range(40)]
    anchor = [("b0", 1.0)] + [(f"a{i}", 1.0) for i in range(20)]
    out = exact_budget_rescue(body, anchor, body_prefix=20, external_offer=10, budget=30)
    assert len(out) == 30
    assert len(out) == len(set(out))


def test_frozen_controller_shape():
    ctrl = FrozenController(
        means=(0.0, 0.0),
        stds=(1.0, 1.0),
        positive_centroid=(1.0, 1.0),
        negative_centroid=(-1.0, -1.0),
        threshold_tau=0.0,
    )
    assert ctrl.should_intervene([1.0, 1.0])
    assert not ctrl.should_intervene([-1.0, -1.0])

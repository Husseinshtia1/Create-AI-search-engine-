from pathlib import Path

from g97.live.index import LiveSearchIndex
from g97.live.repository import DocumentRepository


def test_old_segment_term_does_not_resurrect_stale_document_version(tmp_path: Path) -> None:
    repo = DocumentRepository(tmp_path / "docs.sqlite3")
    index = LiveSearchIndex(repo, tmp_path / "segments")
    repo.upsert(url="https://a.example/", title="A", text="obsolete quantum phrase", fetched_at="t1")
    index.publish_pending()
    assert index.search("obsolete")

    repo.upsert(url="https://a.example/", title="A", text="replacement content only", fetched_at="t2")
    index.publish_pending()
    assert index.search("obsolete") == []
    replacement = index.search("replacement")
    assert replacement and replacement[0].url == "https://a.example/"


def test_two_index_processes_do_not_duplicate_same_generation_segment(tmp_path: Path) -> None:
    db = tmp_path / "docs.sqlite3"
    repo_a = DocumentRepository(db)
    repo_b = DocumentRepository(db)
    segments = tmp_path / "segments"
    index_a = LiveSearchIndex(repo_a, segments)
    index_b = LiveSearchIndex(repo_b, segments)

    repo_a.upsert(url="https://a.example/", title="A", text="quantum publication", fetched_at="t1")
    assert index_a.publish_pending() is True
    # The second process reloads the manifest under the publication lock and
    # observes that the generation is already published.
    assert index_b.publish_pending() is False
    index_b.segments.reload()
    assert len(index_b.segments.metas) == 1
    assert index_b.segments.indexed_generation == repo_b.generation()

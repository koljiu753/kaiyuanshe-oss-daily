from __future__ import annotations

from pathlib import Path

from osdaily.models import NewsItem
from osdaily.processing import normalize_url, process_items, title_similarity
from osdaily.storage import Store


def test_normalize_url_removes_tracking() -> None:
    assert normalize_url("HTTPS://Example.com/path/?utm_source=x&ok=1#frag") == "https://example.com/path?ok=1"


def test_title_similarity_detects_near_duplicates() -> None:
    assert title_similarity("Kubernetes 1.35 released", "Kubernetes v1.35 released") > 0.8


def test_process_items_filters_and_merges(tmp_path: Path) -> None:
    store = Store(tmp_path / "items.sqlite3")
    try:
        items = [
            NewsItem(title="Open source Kubernetes release", url="https://a.example/1", source_id="a", source_name="A"),
            NewsItem(title="Open-source Kubernetes release", url="https://b.example/1", source_id="b", source_name="B"),
            NewsItem(title="Hiring developers now", url="https://c.example/1", source_id="c", source_name="C"),
            NewsItem(title="Closed product launch", url="https://d.example/1", source_id="d", source_name="D"),
        ]
        rules = {
            "relevance_keywords": ["open source", "open-source", "Kubernetes"],
            "blacklist_keywords": ["hiring"],
            "categories": {"云原生/容器": ["Kubernetes"]},
        }
        accepted, stats = process_items(items, store, rules)
    finally:
        store.close()

    assert len(accepted) == 1
    assert accepted[0].category == "云原生/容器"
    assert accepted[0].related_urls == ["https://b.example/1"]
    assert stats["blacklisted"] == 1
    assert stats["irrelevant"] == 1
    assert stats["similar_merged"] == 1

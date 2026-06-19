from __future__ import annotations

from osdaily.enrichment import enrich_items
from osdaily.models import NewsItem
from osdaily.storage import Store


def test_translate_without_openai_key_is_reported_not_fatal(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    store = Store(tmp_path / "osdaily.sqlite3")
    try:
        result = enrich_items(
            [NewsItem(title="Open source release", url="https://example.com", source_id="x", source_name="X")],
            store,
            provider="openai",
            translate=True,
            rewrite_summary=True,
        )
    finally:
        store.close()

    assert result["translated"] == 0
    assert result["rewritten"] == 0
    assert "OPENAI_API_KEY" in result["error"]

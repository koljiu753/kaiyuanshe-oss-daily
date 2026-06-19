from __future__ import annotations

from osdaily.enrichment import enrich_items
from osdaily.models import NewsItem
from osdaily.storage import Store


def test_translate_without_provider_key_is_reported_not_fatal(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    store = Store(tmp_path / "osdaily.sqlite3")
    try:
        result = enrich_items(
            [NewsItem(title="Open source release", url="https://example.com", source_id="x", source_name="X")],
            store,
            provider="deepseek",
            translate=True,
            rewrite_summary=True,
        )
    finally:
        store.close()

    assert result["translated"] == 0
    assert result["rewritten"] == 0
    assert "DEEPSEEK_API_KEY" in result["error"]

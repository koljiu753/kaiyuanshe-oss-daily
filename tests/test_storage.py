from __future__ import annotations

from pathlib import Path

from osdaily.models import NewsItem
from osdaily.storage import Store


def test_store_insert_list_update_and_select(tmp_path: Path) -> None:
    store = Store(tmp_path / "items.sqlite3")
    try:
        item = NewsItem(
            title="开源发布",
            raw_title="Open source release",
            url="https://example.com/release",
            source_id="src",
            source_name="Source",
            summary="中文摘要",
            raw_summary="English summary",
            category="综合",
            tags=["open source"],
        )
        assert store.insert_item(item)
        assert not store.insert_item(item)
        records = store.list_item_records()
        assert len(records) == 1
        item_id = records[0]["id"]
        assert records[0]["raw_title"] == "Open source release"
        assert records[0]["raw_summary"] == "English summary"
        assert records[0]["curation_status"] == "candidate"
        assert records[0]["editor_note"] == ""
        assert store.update_item(item_id, "Edited", "New summary", "安全", ["CVE"], "accepted", "Lead story")
        updated_records = store.list_item_records()
        assert updated_records[0]["curation_status"] == "accepted"
        assert updated_records[0]["editor_note"] == "Lead story"
        assert updated_records[0]["raw_title"] == "Open source release"
        selected = store.items_by_ids([item_id])
        assert selected[0].title == "Edited"
        assert selected[0].raw_title == "Open source release"
        assert selected[0].category == "安全"
        assert selected[0].tags == ["CVE"]
        assert store.update_curation_status(item_id, "rejected")
        assert store.list_item_records()[0]["curation_status"] == "rejected"
    finally:
        store.close()


def test_backfill_raw_fields_for_existing_url(tmp_path: Path) -> None:
    store = Store(tmp_path / "items.sqlite3")
    try:
        item = NewsItem(
            title="中文标题",
            url="https://example.com/a",
            source_id="src",
            source_name="Source",
            summary="中文摘要",
        )
        assert store.insert_item(item)
        store.conn.execute("UPDATE items SET raw_title = NULL, raw_summary = NULL")
        store.conn.commit()

        assert store.backfill_raw_fields(
            NewsItem(
                title="English title",
                raw_title="English title",
                url="https://example.com/a",
                source_id="src",
                source_name="Source",
                summary="English summary",
                raw_summary="English summary",
            )
        )
        record = store.list_item_records()[0]
        assert record["title"] == "中文标题"
        assert record["raw_title"] == "English title"
        assert record["raw_summary"] == "English summary"
    finally:
        store.close()

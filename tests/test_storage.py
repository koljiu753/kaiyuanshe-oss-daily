from __future__ import annotations

from pathlib import Path

from osdaily.models import NewsItem
from osdaily.storage import Store


def test_store_insert_list_update_and_select(tmp_path: Path) -> None:
    store = Store(tmp_path / "items.sqlite3")
    try:
        item = NewsItem(
            title="Open source release",
            url="https://example.com/release",
            source_id="src",
            source_name="Source",
            summary="Summary",
            category="综合",
            tags=["open source"],
        )
        assert store.insert_item(item)
        assert not store.insert_item(item)
        records = store.list_item_records()
        assert len(records) == 1
        item_id = records[0]["id"]
        assert records[0]["curation_status"] == "candidate"
        assert records[0]["editor_note"] == ""
        assert store.update_item(item_id, "Edited", "New summary", "安全", ["CVE"], "accepted", "Lead story")
        updated_records = store.list_item_records()
        assert updated_records[0]["curation_status"] == "accepted"
        assert updated_records[0]["editor_note"] == "Lead story"
        selected = store.items_by_ids([item_id])
        assert selected[0].title == "Edited"
        assert selected[0].category == "安全"
        assert selected[0].tags == ["CVE"]
        assert store.update_curation_status(item_id, "rejected")
        assert store.list_item_records()[0]["curation_status"] == "rejected"
    finally:
        store.close()

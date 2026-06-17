from __future__ import annotations

from osdaily.runner import build_warnings


def test_build_warnings_for_item_count_and_failed_sources() -> None:
    warnings = build_warnings(
        1,
        {"a": {"ok": 0, "items": 0, "name": "Broken Source"}},
        min_items=5,
        max_items=10,
    )
    assert "日报条目数过少" in warnings[0]
    assert "Broken Source" in warnings[1]

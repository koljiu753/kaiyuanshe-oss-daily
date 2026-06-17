from __future__ import annotations

import json
from pathlib import Path

from osdaily.quality import build_quality_report


def write_summary(path: Path, items: int, source_ok: bool, warnings: list[str] | None = None) -> None:
    path.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-17T07:00:00+08:00",
                "report_items": items,
                "warnings": warnings or [],
                "sources": {
                    "a": {"ok": 1, "items": 3, "name": "A"},
                    "b": {"ok": 1 if source_ok else 0, "items": 0, "name": "B"},
                },
            }
        ),
        encoding="utf-8",
    )


def test_build_quality_report(tmp_path: Path) -> None:
    write_summary(tmp_path / "run-summary-2026-06-17.json", 10, True)
    write_summary(tmp_path / "run-summary-2026-06-16.json", 0, False, ["low items"])
    report = build_quality_report(tmp_path, days=7, fallback_daily=False)
    assert report["runs"] == 2
    assert report["success_rate"] == 0.5
    assert report["average_items"] == 5
    assert report["total_warnings"] == 1
    assert report["failed_sources"][0]["name"] == "B"

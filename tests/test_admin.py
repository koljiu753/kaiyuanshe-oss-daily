from __future__ import annotations

from pathlib import Path

from osdaily.admin import list_reports, load_latest_summary, safe_report_path


def test_report_listing_and_safe_path(tmp_path: Path) -> None:
    report = tmp_path / "open-source-daily-2026-06-17.md"
    report.write_text("# ok", encoding="utf-8")
    reports = list_reports(tmp_path)
    assert reports[0]["name"] == report.name
    assert safe_report_path(tmp_path, report.name) == report
    assert safe_report_path(tmp_path, "../secret.md") is None


def test_load_latest_summary_empty(tmp_path: Path) -> None:
    summary = load_latest_summary(tmp_path, fallback_daily=False)
    assert summary["report_items"] == 0
    assert summary["warnings"] == []

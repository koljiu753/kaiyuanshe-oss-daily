from __future__ import annotations

from pathlib import Path

from osdaily.readiness import build_readiness_report


def test_readiness_report_detects_missing_files(tmp_path: Path) -> None:
    report = build_readiness_report(tmp_path)
    assert not report["ok"]
    assert any(check["name"] == "required_files" and not check["ok"] for check in report["checks"])

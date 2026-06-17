from __future__ import annotations

from datetime import datetime, time

import pytest

from osdaily.scheduler import build_next_run_hint, parse_schedule_time, should_run_now


def test_parse_schedule_time() -> None:
    assert parse_schedule_time("06:00") == time(6, 0)
    assert parse_schedule_time("23:59") == time(23, 59)
    with pytest.raises(ValueError):
        parse_schedule_time("25:00")
    with pytest.raises(ValueError):
        parse_schedule_time("bad")


def test_should_run_now() -> None:
    now = datetime(2026, 6, 18, 6, 0)
    assert should_run_now(now, time(6, 0), None)
    assert not should_run_now(now, time(6, 0), now.date())
    assert not should_run_now(datetime(2026, 6, 18, 5, 59), time(6, 0), None)


def test_next_run_hint() -> None:
    assert build_next_run_hint(datetime(2026, 6, 18, 5, 0), time(6, 0), None) == "2026-06-18 06:00"
    assert "tomorrow" in build_next_run_hint(datetime(2026, 6, 18, 7, 0), time(6, 0), "2026-06-18")

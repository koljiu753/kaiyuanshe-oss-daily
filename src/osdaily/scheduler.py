from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime, time as datetime_time
from typing import Callable

from .runner import RunOptions, run_pipeline

LOG = logging.getLogger(__name__)


def parse_schedule_time(value: str) -> datetime_time:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError("schedule time must use HH:MM")
    hour = int(parts[0])
    minute = int(parts[1])
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("schedule time must use a valid 24-hour HH:MM")
    return datetime_time(hour=hour, minute=minute)


def should_run_now(now: datetime, schedule_at: datetime_time, last_run_date: date | None) -> bool:
    if last_run_date == now.date():
        return False
    return now.time().replace(second=0, microsecond=0) >= schedule_at


@dataclass
class SchedulerState:
    enabled: bool = False
    schedule_time: str = "06:00"
    running: bool = False
    last_run_date: str | None = None
    last_started_at: str | None = None
    last_finished_at: str | None = None
    last_error: str | None = None
    last_result: dict | None = None
    next_run_hint: str | None = None
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "enabled": self.enabled,
                "schedule_time": self.schedule_time,
                "running": self.running,
                "last_run_date": self.last_run_date,
                "last_started_at": self.last_started_at,
                "last_finished_at": self.last_finished_at,
                "last_error": self.last_error,
                "last_result": self.last_result,
                "next_run_hint": self.next_run_hint,
            }


def start_daily_scheduler(
    options: RunOptions,
    schedule_time: str = "06:00",
    poll_seconds: int = 60,
    now_fn: Callable[[], datetime] | None = None,
) -> SchedulerState:
    schedule_at = parse_schedule_time(schedule_time)
    state = SchedulerState(enabled=True, schedule_time=schedule_time)
    clock = now_fn or (lambda: datetime.now().astimezone())

    def loop() -> None:
        while True:
            now = clock()
            with state.lock:
                last_run = date.fromisoformat(state.last_run_date) if state.last_run_date else None
                can_start = not state.running and should_run_now(now, schedule_at, last_run)
                state.next_run_hint = build_next_run_hint(now, schedule_at, state.last_run_date)
                if can_start:
                    state.running = True
                    state.last_started_at = now.isoformat()
                    state.last_error = None
            if can_start:
                try:
                    result = run_pipeline(options)
                    finished = clock()
                    with state.lock:
                        state.last_run_date = now.date().isoformat()
                        state.last_finished_at = finished.isoformat()
                        state.last_result = result
                        state.last_error = None
                except Exception as exc:
                    LOG.exception("Scheduled run failed")
                    finished = clock()
                    with state.lock:
                        state.last_finished_at = finished.isoformat()
                        state.last_error = str(exc)
                finally:
                    with state.lock:
                        state.running = False
            time.sleep(poll_seconds)

    thread = threading.Thread(target=loop, name="osdaily-scheduler", daemon=True)
    thread.start()
    return state


def build_next_run_hint(now: datetime, schedule_at: datetime_time, last_run_date: str | None) -> str:
    if last_run_date == now.date().isoformat() or now.time().replace(second=0, microsecond=0) >= schedule_at:
        return f"{now.date().isoformat()} done; next run tomorrow at {schedule_at.strftime('%H:%M')}"
    return f"{now.date().isoformat()} {schedule_at.strftime('%H:%M')}"

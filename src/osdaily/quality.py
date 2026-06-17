from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_run_summaries(output_dir: Path, days: int = 7, fallback_daily: bool = True) -> list[dict[str, Any]]:
    candidates = sorted(output_dir.glob("run-summary-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if fallback_daily and not candidates and output_dir != Path("output/daily"):
        candidates = sorted(Path("output/daily").glob("run-summary-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    summaries: list[dict[str, Any]] = []
    for path in candidates[:days]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        data["_file"] = path.name
        summaries.append(data)
    return summaries


def build_quality_report(output_dir: Path, days: int = 7, fallback_daily: bool = True) -> dict[str, Any]:
    summaries = load_run_summaries(output_dir, days=days, fallback_daily=fallback_daily)
    if not summaries:
        return {
            "days_requested": days,
            "runs": 0,
            "success_rate": 0.0,
            "average_items": 0.0,
            "total_warnings": 0,
            "failed_sources": [],
            "daily": [],
        }

    failed_counter: Counter[str] = Counter()
    item_counts: list[int] = []
    warning_count = 0
    source_runs: defaultdict[str, int] = defaultdict(int)
    source_failures: defaultdict[str, int] = defaultdict(int)
    daily: list[dict[str, Any]] = []

    for summary in summaries:
        item_count = int(summary.get("report_items") or 0)
        warnings = list(summary.get("warnings") or [])
        sources = dict(summary.get("sources") or {})
        item_counts.append(item_count)
        warning_count += len(warnings)
        failed_names: list[str] = []
        for source_id, source in sources.items():
            name = str(source.get("name") or source_id)
            source_runs[name] += 1
            if not source.get("ok"):
                source_failures[name] += 1
                failed_counter[name] += 1
                failed_names.append(name)
        daily.append(
            {
                "file": summary.get("_file"),
                "generated_at": summary.get("generated_at"),
                "items": item_count,
                "warnings": warnings,
                "failed_sources": failed_names,
            }
        )

    successful_runs = sum(1 for item_count in item_counts if item_count > 0)
    failed_sources = [
        {
            "name": name,
            "failures": failures,
            "runs": source_runs[name],
            "failure_rate": round(failures / source_runs[name], 4) if source_runs[name] else 0.0,
        }
        for name, failures in failed_counter.most_common()
    ]
    return {
        "days_requested": days,
        "runs": len(summaries),
        "success_rate": round(successful_runs / len(summaries), 4),
        "average_items": round(sum(item_counts) / len(item_counts), 2),
        "min_items": min(item_counts),
        "max_items": max(item_counts),
        "total_warnings": warning_count,
        "failed_sources": failed_sources,
        "daily": daily,
    }

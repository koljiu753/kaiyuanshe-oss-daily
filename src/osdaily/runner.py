from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .collectors import collect_all
from .config import load_rules, load_sources
from .enrichment import enrich_items
from .notify import send_webhook
from .processing import process_items
from .report import write_report
from .storage import Store

LOG = logging.getLogger(__name__)


@dataclass(slots=True)
class RunOptions:
    days: int = 1
    sources: Path = Path("configs/sources.yaml")
    rules: Path = Path("configs/keywords.yaml")
    db: Path = Path("data/osdaily.sqlite3")
    output: Path = Path("output/daily")
    notify: bool = False
    translate: bool = False
    translate_provider: str = "deepseek"
    translation_limit: int = 30
    rewrite_summary: bool = False
    min_items: int = 5
    max_items: int = 120


def run_pipeline(options: RunOptions) -> dict:
    now = datetime.now().astimezone()
    since = datetime.now(timezone.utc) - timedelta(days=options.days)
    sources = load_sources(options.sources)
    rules = load_rules(options.rules)

    items, source_stats = collect_all(sources, since)
    store = Store(options.db)
    try:
        processed, process_stats = process_items(items, store, rules)
        enrich_stats = enrich_items(
            processed,
            store,
            provider=options.translate_provider if options.translate or options.rewrite_summary else "off",
            limit=options.translation_limit,
            translate=options.translate,
            rewrite_summary=options.rewrite_summary,
        )
        for item in processed:
            store.insert_item(item)
    finally:
        store.close()

    warning_messages = build_warnings(len(processed), source_stats, options.min_items, options.max_items)
    if enrich_stats.get("error"):
        warning_messages.append(str(enrich_stats["error"]))
    run_stats = {
        "generated_at": now.isoformat(),
        "lookback_days": options.days,
        "report_items": len(processed),
        "process": process_stats,
        "enrichment": enrich_stats,
        "sources": source_stats,
        "warnings": warning_messages,
    }
    report_path = write_report(processed, options.output, now, run_stats)
    summary_path = write_run_summary(options.output, now, run_stats)
    if options.notify:
        send_webhook(report_path, len(processed), warning_messages)

    result = {
        "report_path": str(report_path),
        "summary_path": str(summary_path),
        "stats": run_stats,
    }
    LOG.info("Report written to %s", report_path)
    LOG.info("Run summary written to %s", summary_path)
    LOG.info("Source stats: %s", source_stats)
    LOG.info("Process stats: %s", process_stats)
    LOG.info("Enrichment stats: %s", enrich_stats)
    if warning_messages:
        LOG.warning("Warnings: %s", warning_messages)
    return result


def build_warnings(
    item_count: int,
    source_stats: dict[str, dict[str, int | str]],
    min_items: int,
    max_items: int,
) -> list[str]:
    warnings: list[str] = []
    if item_count < min_items:
        warnings.append(f"日报条目数过少：{item_count}，低于阈值 {min_items}")
    if item_count > max_items:
        warnings.append(f"日报条目数过多：{item_count}，高于阈值 {max_items}")
    failed = [str(stat.get("name", source_id)) for source_id, stat in source_stats.items() if not stat.get("ok")]
    if failed:
        warnings.append(f"采集失败源：{', '.join(failed)}")
    return warnings


def write_run_summary(output_dir: Path, generated_at: datetime, run_stats: dict) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"run-summary-{generated_at.strftime('%Y-%m-%d')}.json"
    path.write_text(json.dumps(run_stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from .admin import serve_admin
from .quality import build_quality_report
from .readiness import build_readiness_report
from .runner import RunOptions, run_pipeline
from .validation import validate_project


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate an open-source news Markdown daily report.")
    parser.add_argument("command", choices=["run", "serve", "validate", "quality", "readiness"], help="Command to execute.")
    parser.add_argument("--days", type=int, default=1, help="Look back this many days.")
    parser.add_argument("--sources", type=Path, default=Path("configs/sources.yaml"))
    parser.add_argument("--rules", type=Path, default=Path("configs/keywords.yaml"))
    parser.add_argument("--db", type=Path, default=Path("data/osdaily.sqlite3"))
    parser.add_argument("--output", type=Path, default=Path("output/daily"))
    parser.add_argument("--notify", action="store_true", help="Send webhook notification if DAILY_WEBHOOK_URL is set.")
    parser.add_argument(
        "--translate",
        action="store_true",
        default=env_flag("TRANSLATE_ENABLED"),
        help="Translate accepted English items into Simplified Chinese.",
    )
    parser.add_argument("--translate-provider", default="openai", choices=["openai"], help="Translation provider.")
    parser.add_argument("--translation-limit", type=int, default=30, help="Maximum items to translate per run.")
    parser.add_argument(
        "--rewrite-summary",
        action="store_true",
        default=env_flag("REWRITE_SUMMARY_ENABLED"),
        help="Rewrite accepted item summaries into concise Chinese digest copy.",
    )
    parser.add_argument("--min-items", type=int, default=5, help="Warn when accepted item count is below this number.")
    parser.add_argument("--max-items", type=int, default=120, help="Warn when accepted item count is above this number.")
    parser.add_argument("--host", default="127.0.0.1", help="Admin server host for the serve command.")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8765")), help="Admin server port for the serve command.")
    parser.add_argument("--schedule", action="store_true", help="Run the collection pipeline daily while serving the admin site.")
    parser.add_argument("--schedule-time", default="06:00", help="Daily schedule time in local HH:MM, used with --schedule.")
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper()), format="%(asctime)s %(levelname)s %(message)s")

    if args.command == "serve":
        serve_admin(
            args.db,
            args.output,
            args.host,
            args.port,
            args.sources,
            args.rules,
            schedule=args.schedule,
            schedule_time=args.schedule_time,
            notify=args.notify,
            translate=args.translate,
            translate_provider=args.translate_provider,
            translation_limit=args.translation_limit,
            rewrite_summary=args.rewrite_summary,
            min_items=args.min_items,
            max_items=args.max_items,
        )
        return 0

    if args.command == "validate":
        result = validate_project(args.sources, args.rules)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1

    if args.command == "quality":
        result = build_quality_report(args.output, days=args.days)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "readiness":
        result = build_readiness_report(Path("."))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1

    run_pipeline(
        RunOptions(
            days=args.days,
            sources=args.sources,
            rules=args.rules,
            db=args.db,
            output=args.output,
            notify=args.notify,
            translate=args.translate,
            translate_provider=args.translate_provider,
            translation_limit=args.translation_limit,
            rewrite_summary=args.rewrite_summary,
            min_items=args.min_items,
            max_items=args.max_items,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from pathlib import Path
from typing import Any

from .validation import validate_project


REQUIRED_FILES = [
    "README.md",
    "pyproject.toml",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.prod.yml",
    "Caddyfile",
    ".env.example",
    ".env.production.example",
    ".github/workflows/open-source-daily.yml",
    "configs/sources.yaml",
    "configs/keywords.yaml",
    "configs/kol_twitter_list.yaml",
    "docs/deployment.md",
    "docs/architecture.md",
    "docs/release-checklist.md",
    "scripts/deploy-prod.sh",
    "scripts/backup-data.sh",
]


def build_readiness_report(root: Path = Path(".")) -> dict[str, Any]:
    root = root.resolve()
    checks: list[dict[str, Any]] = []

    missing_files = [path for path in REQUIRED_FILES if not (root / path).exists()]
    checks.append(check("required_files", not missing_files, {"missing": missing_files}))

    if (root / "configs/sources.yaml").exists() and (root / "configs/keywords.yaml").exists():
        validation = validate_project(root / "configs/sources.yaml", root / "configs/keywords.yaml", root / "configs/kol_twitter_list.yaml")
    else:
        validation = {
            "ok": False,
            "source_count": 0,
            "enabled_source_count": 0,
            "errors": ["missing config files"],
            "warnings": [],
        }
    checks.append(check("config_validation", bool(validation["ok"]), validation))

    test_files = sorted(str(path.relative_to(root)) for path in (root / "tests").glob("test_*.py"))
    checks.append(check("test_suite_present", len(test_files) >= 6, {"test_file_count": len(test_files), "files": test_files}))

    daily_reports = sorted((root / "output/daily").glob("open-source-daily-*.md"))
    run_summaries = sorted((root / "output/daily").glob("run-summary-*.json"))
    checks.append(check("sample_report_present", bool(daily_reports), {"count": len(daily_reports)}))
    checks.append(check("run_summary_present", bool(run_summaries), {"count": len(run_summaries)}))

    source_db = root / "data/osdaily.sqlite3"
    checks.append(check("sqlite_store_present", source_db.exists(), {"path": str(source_db.relative_to(root)), "size": source_db.stat().st_size if source_db.exists() else 0}))

    docs = {
        "readme_size": (root / "README.md").stat().st_size if (root / "README.md").exists() else 0,
        "deployment_size": (root / "docs/deployment.md").stat().st_size if (root / "docs/deployment.md").exists() else 0,
        "architecture_size": (root / "docs/architecture.md").stat().st_size if (root / "docs/architecture.md").exists() else 0,
    }
    checks.append(check("docs_nonempty", all(size > 500 for size in docs.values()), docs))

    passed = sum(1 for item in checks if item["ok"])
    return {
        "ok": passed == len(checks),
        "passed": passed,
        "total": len(checks),
        "checks": checks,
    }


def check(name: str, ok: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "ok": ok, "details": details}

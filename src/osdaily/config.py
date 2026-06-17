from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import Source


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_sources(path: Path) -> list[Source]:
    data = load_yaml(path)
    sources: list[Source] = []
    for row in data.get("sources", []):
        metadata = {k: v for k, v in row.items() if k not in {
            "id", "name", "type", "url", "category", "enabled", "frequency_minutes", "tags"
        }}
        sources.append(
            Source(
                id=str(row["id"]),
                name=str(row["name"]),
                type=str(row["type"]),
                url=row.get("url"),
                category=str(row.get("category", "general")),
                enabled=bool(row.get("enabled", True)),
                frequency_minutes=int(row.get("frequency_minutes", 1440)),
                tags=list(row.get("tags", [])),
                metadata=metadata,
            )
        )
    return sources


def load_rules(path: Path) -> dict[str, Any]:
    return load_yaml(path)

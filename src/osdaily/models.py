from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class Source:
    id: str
    name: str
    type: str
    url: str | None = None
    category: str = "general"
    enabled: bool = True
    frequency_minutes: int = 1440
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass(slots=True)
class NewsItem:
    title: str
    url: str
    source_id: str
    source_name: str
    published_at: datetime | None = None
    summary: str = ""
    author: str = ""
    raw_title: str = ""
    raw_summary: str = ""
    category: str = "未分类"
    tags: list[str] = field(default_factory=list)
    related_urls: list[str] = field(default_factory=list)

    def normalized_url(self) -> str:
        return self.url.split("#", 1)[0].strip()

from __future__ import annotations

from pathlib import Path

from osdaily.validation import validate_project


def test_validate_project_happy_path(tmp_path: Path) -> None:
    sources = tmp_path / "sources.yaml"
    rules = tmp_path / "keywords.yaml"
    kol = tmp_path / "kol.yaml"
    sources.write_text(
        """
sources:
  - id: a
    name: A
    type: rss
    url: https://example.com/feed.xml
    enabled: true
""",
        encoding="utf-8",
    )
    rules.write_text(
        """
relevance_keywords: [open source]
categories:
  综合: [open source]
""",
        encoding="utf-8",
    )
    accounts = "\n".join([f"    - id: user{i}\n      name: User {i}" for i in range(20)])
    kol.write_text(f"kol_twitter_list:\n  accounts:\n{accounts}\n", encoding="utf-8")
    result = validate_project(sources, rules, kol)
    assert result["ok"]
    assert result["source_count"] == 1


def test_validate_project_finds_duplicates(tmp_path: Path) -> None:
    sources = tmp_path / "sources.yaml"
    rules = tmp_path / "keywords.yaml"
    sources.write_text(
        """
sources:
  - id: a
    name: A
    type: rss
    url: https://example.com/feed.xml
  - id: a
    name: B
    type: rss
    url: https://example.com/feed2.xml
""",
        encoding="utf-8",
    )
    rules.write_text("relevance_keywords: []\ncategories: {}\n", encoding="utf-8")
    result = validate_project(sources, rules, tmp_path / "missing.yaml")
    assert not result["ok"]
    assert any("重复 source id" in error for error in result["errors"])

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .models import NewsItem


def zh_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def safe_summary(summary: str) -> str:
    summary = " ".join((summary or "").split())
    if len(summary) > 220:
        return summary[:217].rstrip() + "..."
    return summary or "暂无摘要，建议编辑打开原文确认要点。"


def render_markdown(items: list[NewsItem], generated_at: datetime, stats: dict | None = None) -> str:
    date = zh_date(generated_at)
    lines = [
        f"# 开源资讯日报 {date}",
        "",
        f"> 生成时间：{generated_at.strftime('%Y-%m-%d %H:%M %z')} | 共收录 {len(items)} 条资讯",
        "",
    ]
    if stats:
        process = stats.get("process", stats)
        enrichment = stats.get("enrichment", {})
        warnings = stats.get("warnings", [])
        lines.extend(
            [
                "## 总览统计",
                "",
                f"- 入选：{process.get('accepted', len(items))}",
                f"- URL 已入库跳过：{process.get('seen_url', 0)}",
                f"- 相似标题合并：{process.get('similar_merged', 0)}",
                f"- 相关性过滤：{process.get('irrelevant', 0)}",
                f"- 黑名单过滤：{process.get('blacklisted', 0)}",
                (
                    f"- 翻译：{enrichment.get('translated', 0)}，"
                    f"摘要重写：{enrichment.get('rewritten', 0)}，"
                    f"缓存命中：{enrichment.get('cached', 0)}"
                ),
                "",
            ]
        )
        if warnings:
            lines.extend(["## 运行告警", ""])
            lines.extend([f"- {warning}" for warning in warnings])
            lines.append("")

    groups: dict[str, list[NewsItem]] = defaultdict(list)
    for item in items:
        groups[item.category or "综合"].append(item)

    for category in sorted(groups):
        lines.extend([f"## {category}", ""])
        for idx, item in enumerate(groups[category], start=1):
            english_title = f" ({item.raw_title})" if item.raw_title and item.raw_title != item.title else ""
            tags = ", ".join(item.tags) if item.tags else "待编辑"
            lines.extend(
                [
                    f"{idx}. **{item.title}**{english_title}",
                    f"   摘要：{safe_summary(item.summary)}  ",
                    f"   来源：{item.source_name} | 标签：{tags}  ",
                    f"   链接：{item.url}",
                ]
            )
            if item.raw_summary and item.raw_summary != item.summary:
                lines.append(f"   英文摘要：{safe_summary(item.raw_summary)}")
            if item.related_urls:
                lines.append(f"   相关来源：{', '.join(item.related_urls)}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_report(items: list[NewsItem], output_dir: Path, generated_at: datetime, stats: dict | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"open-source-daily-{generated_at.strftime('%Y-%m-%d')}.md"
    path.write_text(render_markdown(items, generated_at, stats), encoding="utf-8")
    return path

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from osdaily.models import NewsItem
from osdaily.notify import build_payload
from osdaily.report import render_markdown, write_report


def test_render_markdown_groups_items() -> None:
    item = NewsItem(
        title="Kubernetes 发布",
        raw_title="Kubernetes released",
        url="https://example.com/k8s",
        source_id="cncf",
        source_name="CNCF Blog",
        summary="新版本发布。",
        category="云原生/容器",
        tags=["Kubernetes", "release"],
    )
    text = render_markdown([item], datetime(2026, 6, 17))
    assert "# 开源资讯日报 2026-06-17" in text
    assert "## 云原生/容器" in text
    assert "Kubernetes released" in text


def test_render_markdown_includes_china_watch_editorial_hint() -> None:
    item = NewsItem(
        title="China open source AI is watched globally",
        url="https://example.com/china-open-source",
        source_id="nyt_technology_china_watch",
        source_name="New York Times Technology",
        summary="A global media report about Chinese open source AI.",
        category="外媒涉华开源观察",
        tags=["china-watch", "editorial-review"],
    )
    text = render_markdown([item], datetime(2026, 7, 7))
    assert "## 外媒涉华开源观察" in text
    assert "主编提示：外媒涉华开源观察" in text


def test_render_markdown_includes_social_watch_editorial_hint() -> None:
    item = NewsItem(
        title="DeepSeek open-source model discussion trends on HN",
        url="https://news.ycombinator.com/item?id=1",
        source_id="hacker_news",
        source_name="Hacker News",
        summary="Developers discuss China AI and open-source model governance.",
        category="涉外社媒观察",
        tags=["social-watch", "editorial-review"],
    )
    text = render_markdown([item], datetime(2026, 7, 7))
    assert "## 涉外社媒观察" in text
    assert "主编提示：涉外社媒观察" in text


def test_write_report_creates_file(tmp_path: Path) -> None:
    item = NewsItem(title="Open source", url="https://example.com", source_id="x", source_name="X")
    path = write_report([item], tmp_path, datetime(2026, 6, 17))
    assert path.exists()
    assert path.name == "open-source-daily-2026-06-17.md"


def test_webhook_payload_shapes() -> None:
    assert build_payload("generic", "hello") == {"text": "hello"}
    assert build_payload("wecom", "hello")["msgtype"] == "markdown"
    assert build_payload("feishu", "hello")["msg_type"] == "text"
    assert build_payload("dingtalk", "hello")["markdown"]["title"] == "开源资讯日报"

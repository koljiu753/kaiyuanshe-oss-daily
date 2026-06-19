from __future__ import annotations

from datetime import datetime, timezone

import httpx

from osdaily.collectors import collect_web
from osdaily.models import Source


def test_collect_web_extracts_article_links(monkeypatch) -> None:
    html = """
    <html><body>
      <article>
        <a href="/software/open_source/example/">Example open source release</a>
        <p>A short open source summary.</p>
      </article>
      <a href="https://other.example/article">External article</a>
      <a href="/logo.png">Image</a>
    </body></html>
    """

    monkeypatch.setattr("osdaily.collectors.robots_allowed", lambda url, ua: True)
    monkeypatch.setattr(
        "osdaily.collectors.fetch_url",
        lambda url, headers: httpx.Response(200, text=html, request=httpx.Request("GET", url)),
    )

    source = Source(
        id="web",
        name="Web",
        type="web",
        url="https://example.com/software/open_source/",
        category="科技媒体",
        tags=["media"],
        metadata={"max_results": 5},
    )
    items = collect_web(source, datetime.now(timezone.utc))

    assert len(items) == 1
    assert items[0].title == "Example open source release"
    assert items[0].url == "https://example.com/software/open_source/example/"
    assert "open source summary" in items[0].summary

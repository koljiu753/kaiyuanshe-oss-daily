from __future__ import annotations

import logging
import os
import urllib.robotparser
import time
import warnings
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, Iterable
from urllib.parse import urljoin, urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from dateutil import parser as date_parser

from .models import NewsItem, Source

LOG = logging.getLogger(__name__)


def user_agent() -> str:
    contact = os.getenv("CONTACT_EMAIL", "opensource-daily@example.org")
    return f"OpenSourceDailyBot/0.1 (+mailto:{contact})"


def parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = date_parser.parse(value)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None
    return None


def clean_html(value: str | None) -> str:
    if not value:
        return ""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", MarkupResemblesLocatorWarning)
        soup = BeautifulSoup(value, "html.parser")
    return " ".join(soup.get_text(" ", strip=True).split())


def collect_source(source: Source, since: datetime) -> list[NewsItem]:
    if not source.enabled:
        return []
    if source.type in {"rss", "atom"}:
        return collect_feed(source, since)
    if source.type == "reddit_rss":
        return collect_feed(source, since)
    if source.type == "lobsters_rss":
        return collect_feed(source, since)
    if source.type == "mastodon_tag":
        return collect_feed(source, since)
    if source.type == "youtube_rss":
        return collect_feed(source, since)
    if source.type == "twitter_api_list":
        return collect_twitter_list(source, since)
    if source.type == "web":
        return collect_web(source, since)
    if source.type == "api":
        LOG.info("Skipping configured API source %s; collector adapter is not enabled yet.", source.id)
        return []
    LOG.warning("Unknown source type %s for %s", source.type, source.id)
    return []


def collect_feed(source: Source, since: datetime) -> list[NewsItem]:
    if not source.url:
        return []
    headers = {"User-Agent": user_agent()}
    response = fetch_url(source.url, headers=headers)
    parsed = feedparser.parse(response.content)
    items: list[NewsItem] = []
    for entry in parsed.entries:
        published = entry.get("published") or entry.get("updated") or entry.get("created")
        published_at = parse_datetime(published)
        if not published_at and entry.get("published_parsed"):
            try:
                published_at = parsedate_to_datetime(entry.published)
            except Exception:
                published_at = None
        if published_at and published_at.astimezone(timezone.utc) < since.astimezone(timezone.utc):
            continue
        link = entry.get("link")
        title = clean_html(entry.get("title", "")).strip()
        if not link or not title:
            continue
        summary = clean_html(entry.get("summary") or entry.get("description") or "")
        author = clean_html(entry.get("author", ""))
        items.append(
            NewsItem(
                title=title,
                raw_title=title,
                url=link,
                source_id=source.id,
                source_name=source.name,
                published_at=published_at,
                summary=summary[:700],
                raw_summary=summary[:700],
                author=author,
                category=source.category,
                tags=list(source.tags),
            )
        )
    return items


def robots_allowed(url: str, user_agent_value: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
    except Exception as exc:
        LOG.info("Could not read robots.txt for %s: %s", url, exc)
        return True
    return parser.can_fetch(user_agent_value, url)


def collect_web(source: Source, since: datetime) -> list[NewsItem]:
    if not source.url:
        return []
    ua = user_agent()
    if not robots_allowed(source.url, ua):
        LOG.info("Skipping %s; robots.txt disallows %s", source.id, source.url)
        return []

    response = fetch_url(source.url, headers={"User-Agent": ua})
    soup = BeautifulSoup(response.text, "html.parser")
    max_results = int(source.metadata.get("max_results", 20))
    items: list[NewsItem] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        title = clean_html(anchor.get_text(" ", strip=True))
        if len(title) < 12:
            continue
        link = urljoin(source.url, anchor["href"])
        if not is_probable_article_link(source.url, link):
            continue
        normalized = link.split("#", 1)[0]
        if normalized in seen:
            continue
        seen.add(normalized)
        summary = extract_nearby_text(anchor)
        items.append(
            NewsItem(
                title=title[:180],
                raw_title=title[:180],
                url=normalized,
                source_id=source.id,
                source_name=source.name,
                published_at=None,
                summary=summary[:700],
                raw_summary=summary[:700],
                category=source.category,
                tags=list(source.tags),
            )
        )
        if len(items) >= max_results:
            break
    return items


def is_probable_article_link(base_url: str, link: str) -> bool:
    base = urlparse(base_url)
    parsed = urlparse(link)
    if parsed.scheme not in {"http", "https"} or parsed.netloc != base.netloc:
        return False
    path = parsed.path.strip("/")
    if not path or path in {"software", "software/open_source"}:
        return False
    blocked_ext = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".pdf", ".zip")
    return not parsed.path.lower().endswith(blocked_ext)


def extract_nearby_text(anchor) -> str:
    parent = anchor.find_parent(["article", "li", "div"]) or anchor.parent
    if not parent:
        return ""
    text = clean_html(parent.get_text(" ", strip=True))
    return text[:700]


def fetch_url(url: str, headers: dict[str, str], retries: int = 2, backoff_seconds: float = 2.0) -> httpx.Response:
    last_exc: Exception | None = None
    with httpx.Client(headers=headers, follow_redirects=True, timeout=30) as client:
        for attempt in range(retries + 1):
            try:
                response = client.get(url)
                if response.status_code >= 500 and attempt < retries:
                    time.sleep(backoff_seconds * (attempt + 1))
                    continue
                response.raise_for_status()
                return response
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt >= retries:
                    break
                time.sleep(backoff_seconds * (attempt + 1))
    if last_exc:
        raise last_exc
    raise RuntimeError(f"Failed to fetch {url}")


def collect_twitter_list(source: Source, since: datetime) -> list[NewsItem]:
    bearer_token = os.getenv(source.metadata.get("bearer_token_env", "TWITTER_BEARER_TOKEN"))
    list_id = os.getenv(source.metadata.get("list_id_env", "TWITTER_OPEN_SOURCE_KOL_LIST_ID"))
    if not bearer_token or not list_id:
        LOG.info("Skipping %s; TWITTER_BEARER_TOKEN or list id env is not configured.", source.id)
        return []

    params = {
        "max_results": str(source.metadata.get("max_results", 50)),
        "tweet.fields": "author_id,created_at,lang,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    headers = {"Authorization": f"Bearer {bearer_token}", "User-Agent": user_agent()}
    url = f"https://api.twitter.com/2/lists/{list_id}/tweets"
    with httpx.Client(headers=headers, follow_redirects=True, timeout=30) as client:
        response = None
        for attempt in range(3):
            response = client.get(url, params=params)
            if response.status_code < 500 or attempt == 2:
                break
            time.sleep(2.0 * (attempt + 1))
        assert response is not None
        response.raise_for_status()
    payload = response.json()
    users = {
        user["id"]: user
        for user in payload.get("includes", {}).get("users", [])
        if "id" in user
    }
    items: list[NewsItem] = []
    for tweet in payload.get("data", []):
        created_at = parse_datetime(tweet.get("created_at"))
        if created_at and created_at.astimezone(timezone.utc) < since.astimezone(timezone.utc):
            continue
        user = users.get(tweet.get("author_id"), {})
        username = user.get("username", "i")
        tweet_id = tweet.get("id")
        text = clean_html(tweet.get("text", ""))
        if not tweet_id or not text:
            continue
        link = f"https://x.com/{username}/status/{tweet_id}"
        author = user.get("name") or username
        items.append(
            NewsItem(
                title=text[:100],
                raw_title=text[:100],
                url=link,
                source_id=source.id,
                source_name=source.name,
                published_at=created_at,
                summary=text[:700],
                raw_summary=text[:700],
                author=author,
                category=source.category,
                tags=list(source.tags),
            )
        )
    return items


ProgressCallback = Callable[[dict[str, int | str]], None]


def collect_all(
    sources: Iterable[Source],
    since: datetime,
    progress_callback: ProgressCallback | None = None,
) -> tuple[list[NewsItem], dict[str, dict[str, int | str]]]:
    collected: list[NewsItem] = []
    stats: dict[str, dict[str, int | str]] = {}
    enabled_sources = [source for source in sources if source.enabled]
    total = len(enabled_sources)
    for index, source in enumerate(enabled_sources, start=1):
        if progress_callback:
            progress_callback({
                "phase": "collecting",
                "current": index - 1,
                "total": total,
                "source": source.name,
            })
        try:
            items = collect_source(source, since)
            collected.extend(items)
            stats[source.id] = {"ok": 1, "items": len(items), "name": source.name}
            LOG.info("Collected %s items from %s", len(items), source.name)
        except Exception as exc:
            stats[source.id] = {"ok": 0, "items": 0, "name": source.name, "error": str(exc)}
            LOG.warning("Failed collecting %s: %s", source.name, exc)
        if progress_callback:
            progress_callback({
                "phase": "collecting",
                "current": index,
                "total": total,
                "source": source.name,
            })
    return collected, stats

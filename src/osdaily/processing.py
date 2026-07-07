from __future__ import annotations

import re
from collections import defaultdict
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import NewsItem
from .storage import Store


TRACKING_PREFIXES = ("utm_",)
TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.startswith(TRACKING_PREFIXES) and key not in TRACKING_KEYS
    ]
    path = parts.path.rstrip("/") or parts.path
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def contains_any(text: str, keywords: list[str]) -> list[str]:
    haystack = norm_text(text)
    return [keyword for keyword in keywords if keyword.lower() in haystack]


def is_blacklisted(item: NewsItem, blacklist: list[str]) -> bool:
    blob = f"{item.title}\n{item.summary}"
    return bool(contains_any(blob, blacklist))


def is_relevant(item: NewsItem, keywords: list[str]) -> bool:
    blob = f"{item.title}\n{item.summary}\n{' '.join(item.tags)}"
    return bool(contains_any(blob, keywords))


def is_china_watch_candidate(
    item: NewsItem,
    china_keywords: list[str],
    open_source_keywords: list[str],
) -> bool:
    if "china-watch" not in item.tags:
        return False
    if "google-news" in item.tags:
        editorial_text = f"{item.title}\n{item.raw_title}"
    else:
        editorial_text = f"{item.title}\n{item.summary}\n{item.raw_title}\n{item.raw_summary}"
    has_china_signal = bool(contains_any(editorial_text, china_keywords))
    has_open_source_signal = bool(contains_any(editorial_text, open_source_keywords))
    return has_china_signal and has_open_source_signal


def mark_china_watch(item: NewsItem, category: str) -> None:
    item.category = category
    tags = set(item.tags)
    tags.update({"p7-content", "china-watch", "editorial-review", "外媒涉华", "主编点评"})
    item.tags = sorted(tags)


def classify(item: NewsItem, category_rules: dict[str, list[str]]) -> tuple[str, list[str]]:
    blob = f"{item.title}\n{item.summary}\n{' '.join(item.tags)}"
    scores: dict[str, int] = {}
    matched_tags = set(item.tags)
    for category, keywords in category_rules.items():
        matches = contains_any(blob, keywords)
        if matches:
            scores[category] = len(matches)
            matched_tags.update(matches[:5])
    if not scores:
        return item.category or "综合", sorted(matched_tags)
    category = max(scores, key=scores.get)
    return category, sorted(matched_tags)


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, norm_text(a), norm_text(b)).ratio()


def process_items(
    items: list[NewsItem],
    store: Store,
    rules: dict,
    similarity_threshold: float = 0.8,
) -> tuple[list[NewsItem], dict[str, int]]:
    keywords = list(rules.get("relevance_keywords", []))
    blacklist = list(rules.get("blacklist_keywords", []))
    category_rules = dict(rules.get("categories", {}))
    china_watch_keywords = list(rules.get("china_watch_keywords", []))
    china_watch_open_source_keywords = list(rules.get("china_watch_open_source_keywords", []))
    china_watch_category = str(rules.get("china_watch_category", "外媒涉华开源观察"))
    stats = defaultdict(int)
    accepted: list[NewsItem] = []

    for item in items:
        item.url = normalize_url(item.url)
        if store.seen_url(item.normalized_url()):
            store.backfill_raw_fields(item)
            stats["seen_url"] += 1
            continue
        if is_blacklisted(item, blacklist):
            stats["blacklisted"] += 1
            continue
        if keywords and not is_relevant(item, keywords):
            stats["irrelevant"] += 1
            continue
        is_china_watch = is_china_watch_candidate(
            item,
            china_watch_keywords,
            china_watch_open_source_keywords,
        )
        if "china-watch" in item.tags and not is_china_watch:
            stats["china_watch_irrelevant"] += 1
            continue

        merged = False
        for existing in accepted:
            if title_similarity(existing.title, item.title) >= similarity_threshold:
                if item.normalized_url() not in existing.related_urls and item.normalized_url() != existing.normalized_url():
                    existing.related_urls.append(item.normalized_url())
                stats["similar_merged"] += 1
                merged = True
                break
        if merged:
            continue

        if is_china_watch:
            mark_china_watch(item, china_watch_category)
            stats["china_watch"] += 1
        else:
            generic_category_rules = {
                category: values
                for category, values in category_rules.items()
                if category != china_watch_category
            }
            item.category, item.tags = classify(item, generic_category_rules)
        accepted.append(item)
        stats["accepted"] += 1

    return accepted, dict(stats)

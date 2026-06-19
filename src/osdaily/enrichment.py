from __future__ import annotations

import hashlib
import json
import logging
import os
import re

import httpx

from .models import NewsItem
from .storage import Store

LOG = logging.getLogger(__name__)

PROVIDERS = {
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "base_url_env": "OPENAI_BASE_URL",
        "model_env": "OPENAI_MODEL",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4.1-mini",
    },
    "deepseek": {
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "model_env": "DEEPSEEK_MODEL",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
    },
    "moonshot": {
        "api_key_env": "MOONSHOT_API_KEY",
        "base_url_env": "MOONSHOT_BASE_URL",
        "model_env": "MOONSHOT_MODEL",
        "base_url": "https://api.moonshot.ai/v1",
        "model": "kimi-k2.6",
    },
}


def looks_english(text: str) -> bool:
    letters = re.findall(r"[A-Za-z]", text)
    return len(letters) >= 12


def cache_key(item: NewsItem, mode: str) -> str:
    blob = f"{mode}\n{item.title}\n{item.summary}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def enrich_items(
    items: list[NewsItem],
    store: Store,
    provider: str = "off",
    limit: int = 30,
    translate: bool = False,
    rewrite_summary: bool = False,
) -> dict[str, int]:
    if provider in {"", "off", "none"}:
        return {"enriched": 0, "translated": 0, "rewritten": 0, "cached": 0, "skipped": len(items)}
    if provider not in PROVIDERS:
        raise ValueError(f"Unsupported translation provider: {provider}")
    if not translate and not rewrite_summary:
        return {"enriched": 0, "translated": 0, "rewritten": 0, "cached": 0, "skipped": len(items)}
    client_config = resolve_provider(provider)
    if not client_config["api_key"]:
        return {
            "enriched": 0,
            "translated": 0,
            "rewritten": 0,
            "cached": 0,
            "skipped": len(items),
            "error": f"{client_config['api_key_env']} is required for Chinese translation.",
        }

    enriched = 0
    cached = 0
    skipped = 0
    mode = build_mode(translate, rewrite_summary)
    for item in items:
        if enriched >= limit:
            skipped += 1
            continue
        if translate and not looks_english(f"{item.title} {item.summary}"):
            skipped += 1
            continue
        key = cache_key(item, mode)
        cached_value = store.get_translation(key)
        if cached_value:
            apply_translation(item, cached_value[0], cached_value[1])
            cached += 1
            continue
        title, summary = enrich_with_llm(item.title, item.summary, translate, rewrite_summary, client_config)
        store.save_translation(key, title, summary)
        apply_translation(item, title, summary)
        enriched += 1
    return {
        "enriched": enriched,
        "translated": enriched if translate else 0,
        "rewritten": enriched if rewrite_summary else 0,
        "cached": cached,
        "skipped": skipped,
    }


def build_mode(translate: bool, rewrite_summary: bool) -> str:
    parts = []
    if translate:
        parts.append("translate")
    if rewrite_summary:
        parts.append("rewrite-summary")
    return "+".join(parts)


def apply_translation(item: NewsItem, title: str, summary: str) -> None:
    item.raw_title = item.raw_title or item.title
    item.raw_summary = item.raw_summary or item.summary
    item.title = title.strip() or item.title
    item.summary = summary.strip() or item.summary


def resolve_provider(provider: str) -> dict[str, str]:
    defaults = PROVIDERS[provider]
    api_key_env = defaults["api_key_env"]
    base_url = os.getenv("LLM_BASE_URL") or os.getenv(defaults["base_url_env"]) or defaults["base_url"]
    return {
        "provider": provider,
        "api_key_env": api_key_env,
        "api_key": os.getenv("LLM_API_KEY") or os.getenv(api_key_env) or "",
        "base_url": base_url.rstrip("/"),
        "model": os.getenv("LLM_MODEL") or os.getenv(defaults["model_env"]) or defaults["model"],
    }


def enrich_with_llm(
    title: str,
    summary: str,
    translate: bool,
    rewrite_summary: bool,
    client_config: dict[str, str],
) -> tuple[str, str]:
    if translate and rewrite_summary:
        instruction = (
            "Translate title into concise Simplified Chinese and rewrite the summary into 1-2 "
            "publication-ready Simplified Chinese sentences. Preserve technical names."
        )
    elif translate:
        instruction = "Translate title and summary into concise, publication-ready Simplified Chinese. Preserve technical names."
    else:
        instruction = (
            "Keep the title unchanged. Rewrite the summary into 1-2 concise Simplified Chinese "
            "sentences for a WeChat open-source news digest. Preserve technical names."
        )
    prompt = {
        "title": title,
        "summary": summary,
        "instruction": instruction,
    }
    payload = {
        "model": client_config["model"],
        "messages": [
            {
                "role": "system",
                "content": "You edit open-source technology news for a Chinese daily digest. Return strict JSON with keys title and summary.",
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {client_config['api_key']}", "Content-Type": "application/json"}
    url = f"{client_config['base_url']}/chat/completions"
    with httpx.Client(timeout=45) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    data = json.loads(content)
    return str(data.get("title", title)), str(data.get("summary", summary))

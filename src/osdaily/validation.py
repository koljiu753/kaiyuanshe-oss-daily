from __future__ import annotations

from pathlib import Path

from .config import load_rules, load_sources, load_yaml


def validate_project(sources_path: Path, rules_path: Path, kol_path: Path = Path("configs/kol_twitter_list.yaml")) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    sources = load_sources(sources_path)
    ids = [source.id for source in sources]
    duplicates = sorted({source_id for source_id in ids if ids.count(source_id) > 1})
    if duplicates:
        errors.append(f"重复 source id：{', '.join(duplicates)}")
    if not sources:
        errors.append("sources.yaml 没有配置任何资讯源")

    enabled = [source for source in sources if source.enabled]
    if len(enabled) < 10:
        warnings.append(f"启用资讯源较少：{len(enabled)}")
    for source in sources:
        if not source.name:
            errors.append(f"{source.id} 缺少 name")
        if not source.type:
            errors.append(f"{source.id} 缺少 type")
        if source.type not in {"rss", "atom", "reddit_rss", "lobsters_rss", "mastodon_tag", "youtube_rss", "twitter_api_list", "api", "web"}:
            warnings.append(f"{source.id} 使用未知 type：{source.type}")
        if source.type != "twitter_api_list" and not source.url:
            errors.append(f"{source.id} 缺少 url")

    rules = load_rules(rules_path)
    if not rules.get("relevance_keywords"):
        errors.append("keywords.yaml 缺少 relevance_keywords")
    if not rules.get("categories"):
        errors.append("keywords.yaml 缺少 categories")

    if kol_path.exists():
        kol_data = load_yaml(kol_path).get("kol_twitter_list", {})
        accounts = kol_data.get("accounts", [])
        if len(accounts) != 20:
            errors.append(f"Twitter/X KOL 账号数量应为 20，当前为 {len(accounts)}")
        account_ids = [account.get("id") for account in accounts]
        duplicate_accounts = sorted({account_id for account_id in account_ids if account_ids.count(account_id) > 1})
        if duplicate_accounts:
            errors.append(f"重复 KOL id：{', '.join(duplicate_accounts)}")
    else:
        warnings.append(f"未找到 KOL 配置：{kol_path}")

    return {
        "ok": not errors,
        "source_count": len(sources),
        "enabled_source_count": len(enabled),
        "errors": errors,
        "warnings": warnings,
    }

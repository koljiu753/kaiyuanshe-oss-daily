from __future__ import annotations

import os
from pathlib import Path

import httpx


def send_webhook(report_path: Path, item_count: int, warnings: list[str] | None = None) -> bool:
    url = os.getenv("DAILY_WEBHOOK_URL")
    if not url:
        return False
    webhook_type = os.getenv("DAILY_WEBHOOK_TYPE", "generic").strip().lower()
    message = build_message(report_path, item_count, warnings or [])
    payload = build_payload(webhook_type, message)
    response = httpx.post(url, json=payload, timeout=15)
    response.raise_for_status()
    return True


def build_message(report_path: Path, item_count: int, warnings: list[str]) -> str:
    lines = [
        "开源资讯日报已生成",
        f"- 文件：{report_path.name}",
        f"- 条目：{item_count}",
        f"- 路径：{report_path}",
    ]
    if warnings:
        lines.append("- 告警：" + "；".join(warnings))
    return "\n".join(lines)


def build_payload(webhook_type: str, message: str) -> dict:
    if webhook_type in {"wecom", "wechat_work", "enterprise_wechat"}:
        return {
            "msgtype": "markdown",
            "markdown": {"content": message},
        }
    if webhook_type in {"feishu", "lark"}:
        return {
            "msg_type": "text",
            "content": {"text": message},
        }
    if webhook_type in {"dingtalk", "dingding"}:
        return {
            "msgtype": "markdown",
            "markdown": {
                "title": "开源资讯日报",
                "text": message,
            },
        }
    return {"text": message}

# 发布检查清单

发布或交付前运行：

```bash
python -m pytest
python -m osdaily.cli validate
python -m osdaily.cli readiness
python -m osdaily.cli quality --days 7
```

必须满足：

- `pytest` 全部通过。
- `validate` 返回 `ok: true`。
- `readiness` 返回 `ok: true`。
- `output/daily/` 中存在示例 Markdown 日报和运行摘要 JSON。
- `data/osdaily.sqlite3` 存在并可被管理界面读取。
- `Dockerfile` 和 `docker-compose.yml` 存在。
- `docker-compose.prod.yml`、`Caddyfile`、`.env.production.example` 存在。
- `render.yaml` 和 `docs/render-deployment.md` 存在。
- `scripts/deploy-prod.sh` 和 `scripts/backup-data.sh` 存在。
- 管理站点 `/healthz` 返回 `{"ok": true}`。

人工验收建议：

- 打开管理界面，确认条目列表、运行状态、定时调度、质量报告可见。
- 编辑一条资讯的标题、摘要、标签、采纳状态和备注，确认刷新后仍保留。
- 勾选若干条目导出 Markdown，确认 `output/edited/` 产生文件。
- 如启用 Webhook，确认企业微信/飞书/钉钉收到通知。
- 如启用翻译，先设置小的 `--translation-limit` 控制成本。

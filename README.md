# 开源资讯日报自动化工具

这个仓库提供一个可运行的 MVP：从配置化资讯源采集开源相关内容，经过关键词过滤、黑名单过滤、URL 去重、标题相似合并和规则分类后，生成运营可直接编辑的 Markdown 日报。

## 当前能力

- RSS/Atom、Reddit RSS、Lobsters RSS、Mastodon 标签 RSS、YouTube RSS 采集。
- YAML 配置化资讯源，新增源不需要改代码。
- SQLite 记录已采集 URL，避免重复入库。
- 开源相关性关键词过滤和黑名单过滤。
- 标题相似度合并，保留相关来源链接。
- 规则化分类和标签。
- Markdown 日报输出。
- 可选 OpenAI 翻译与摘要重写，带 SQLite 缓存和每日处理条数限制。
- 运行摘要 JSON 输出，记录源成功/失败、过滤、去重、翻译和告警信息。
- GitHub Actions 每日北京时间 06:00 自动运行，并支持手动触发。
- 管理服务支持内置每日定时调度，适合 Docker/服务器常驻部署。
- Webhook 通知，支持 generic、企业微信、飞书/飞书国际版、钉钉 payload。
- Twitter/X 官方 API list timeline 采集器已预留，默认禁用，等待接入有效 API 凭据和列表 ID 后启用。
- 简易 Web 管理界面，支持查看运行状态、手动重新采集、筛选、勾选、编辑标题/摘要/分类/标签、持久化采纳状态，并重新导出 Markdown。
- 管理界面可直接查看最近导出的 Markdown 日报。
- 最近 7 天运行质量报告，包含成功率、平均条目数、告警数和失败源排行。
- pytest 测试覆盖核心处理、存储、渲染、通知、告警和管理辅助逻辑。
- Docker / Docker Compose 部署文件。
- 生产部署配置：Caddy 自动 HTTPS、`docker-compose.prod.yml`、`.env.production.example`、部署和备份脚本。
- Render Blueprint：可从 GitHub 直接部署到 Render。

## 工程文档

- [部署指南](docs/deployment.md)
- [Render 部署指南](docs/render-deployment.md)
- [架构说明](docs/architecture.md)
- [发布检查清单](docs/release-checklist.md)

## 快速开始

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
osdaily run --days 1
```

开发/测试环境：

```bash
python -m pip install -e .[dev]
python -m pytest
python -m osdaily.cli validate
python -m osdaily.cli quality --days 7
python -m osdaily.cli readiness
```

如果当前机器的 `python` 没有 `pip`，请先安装标准 Python 3.11+，或直接指定可用解释器执行：

```bash
python -m pip install -e .
python -m osdaily.cli run --days 1
```

生成文件位于：

```text
output/daily/open-source-daily-YYYY-MM-DD.md
output/daily/run-summary-YYYY-MM-DD.json
```

首次试运行可以回溯 3 天：

```bash
osdaily run --days 3
```

测试时如果不想受正式去重库影响，可以使用临时数据库和临时输出目录：

```bash
python -m osdaily.cli run --days 3 --db data/test.sqlite3 --output output/test
```

## 配置文件

- `configs/sources.yaml`：资讯源配置，包含名称、类型、URL、频率、分类、标签和启用状态。
- `configs/keywords.yaml`：开源相关关键词、黑名单关键词、分类规则。
- `configs/kol_twitter_list.yaml`：OpenSourceKOL 的 20 个 Twitter/X 账号配置。

### 新增 RSS 源

```yaml
- id: example_blog
  name: Example Blog
  type: rss
  url: https://example.com/feed.xml
  category: 基金会/企业博客
  enabled: true
  frequency_minutes: 1440
  tags: [example]
```

## 命令

```bash
osdaily run --days 1 \
  --sources configs/sources.yaml \
  --rules configs/keywords.yaml \
  --db data/osdaily.sqlite3 \
  --output output/daily
```

检查配置：

```bash
python -m osdaily.cli validate
```

查看最近运行质量：

```bash
python -m osdaily.cli quality --days 7
```

交付就绪检查：

```bash
python -m osdaily.cli readiness
```

启动本地管理界面：

```bash
python -m osdaily.cli serve --db data/osdaily.sqlite3 --output output/edited --host 127.0.0.1 --port 8765
```

启动管理界面并开启每日 06:00 自动采集：

```bash
python -m osdaily.cli serve --db data/osdaily.sqlite3 --output output/daily --host 127.0.0.1 --port 8765 --schedule --schedule-time 06:00 --notify
```

打开：

```text
http://127.0.0.1:8765
```

管理界面会读取 SQLite 中已有条目。请先至少运行一次 `run` 命令生成数据，再启动 `serve`。

管理界面能力：

- 查看最近一次运行时间、入选条目数、失败源和告警。
- 手动选择回溯天数并重新采集。
- 查看内置定时调度是否开启、下次运行提示和上次错误。
- 搜索和按分类筛选条目。
- 编辑标题、摘要、分类、标签、采纳状态和编辑备注。
- 勾选采用条目并导出新的 Markdown。

## 环境变量

复制 `.env.example` 并在部署环境中设置：

- `CONTACT_EMAIL`：写入 User-Agent，方便源站联系。
- `DAILY_WEBHOOK_URL`：日报生成后的通知 Webhook。
- `DAILY_WEBHOOK_TYPE`：通知类型，可选 `generic`、`wecom`、`feishu`、`dingtalk`。
- `TWITTER_BEARER_TOKEN`：启用 Twitter/X 官方 API 时使用。
- `TWITTER_OPEN_SOURCE_KOL_LIST_ID`：Twitter/X 的 OpenSourceKOL 列表数字 ID。
- `OPENAI_API_KEY`：运行 `--translate` 时使用。
- `OPENAI_MODEL`：翻译模型，默认 `gpt-4.1-mini`。

## 翻译与摘要重写测试

默认命令不会调用 OpenAI，也不会产生 API 成本。需要翻译时显式加参数：

```bash
python -m osdaily.cli run --days 1 --translate --translation-limit 10
```

只想把摘要改写成更适合公众号日报的中文短摘要：

```bash
python -m osdaily.cli run --days 1 --rewrite-summary --translation-limit 10
```

翻译标题并同时重写摘要：

```bash
python -m osdaily.cli run --days 1 --translate --rewrite-summary --translation-limit 10
```

翻译结果会写入 SQLite 缓存。相同标题和摘要再次出现时会复用缓存，减少重复调用。

## Webhook 通知

设置环境变量后运行 `--notify`：

```bash
$env:DAILY_WEBHOOK_URL="https://example.com/webhook"
$env:DAILY_WEBHOOK_TYPE="wecom"
python -m osdaily.cli run --days 1 --notify
```

`DAILY_WEBHOOK_TYPE` 支持：

- `generic`：发送 `{"text": "..."}`
- `wecom`：企业微信 markdown 消息
- `feishu` / `lark`：飞书 text 消息
- `dingtalk`：钉钉 markdown 消息

## Twitter/X 配置

Twitter/X 源默认禁用。确认已有官方 API 权限、Bearer Token 和列表数字 ID 后：

1. 设置环境变量 `TWITTER_BEARER_TOKEN` 和 `TWITTER_OPEN_SOURCE_KOL_LIST_ID`。
2. 打开 `configs/sources.yaml`。
3. 找到 `twitter_open_source_kol`，把 `enabled: false` 改为 `enabled: true`。
4. 运行：

```bash
python -m osdaily.cli run --days 1
```

采集器只调用官方 API，不做未授权网页抓取。

## GitHub Actions

工作流文件位于 `.github/workflows/open-source-daily.yml`。

- 定时：每日 22:00 UTC，即北京时间次日 06:00。
- 手动：Actions 页面执行 `workflow_dispatch`，可传入 `days`。
- 产物：提交 `output/daily/*.md` 和 SQLite 去重库。

需要在 GitHub Secrets 中配置：

- `CONTACT_EMAIL`
- `DAILY_WEBHOOK_URL`
- `TWITTER_BEARER_TOKEN`
- `TWITTER_OPEN_SOURCE_KOL_LIST_ID`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

## 后续增强计划

1. 增加 DeepL 翻译提供方，与现有 OpenAI 翻译接口并列可选。
2. 为 Web 管理界面增加登录保护和多人协作状态。
3. 为网页源增加 robots.txt 检查和 Playwright 渲染采集器。
4. 为源健康监控增加连续失败自动禁用建议。
5. 增加内容评分和运营采纳反馈闭环。

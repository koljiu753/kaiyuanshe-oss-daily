# 开源资讯日报自动化工具

面向开源社公众号运营的资讯采集与日报生成工具。系统每天从全球科技媒体、基金会/企业博客、社区、Mastodon、YouTube 和可选 Twitter/X KOL 列表采集开源相关资讯，经过过滤、去重、分类、翻译和人工编辑后，导出可直接用于公众号选题的 Markdown 日报。

线上试运行地址：

```text
https://kaiyuanshe-oss-daily.onrender.com
```

## 当前能力

- 配置化资讯源：所有源都在 `configs/sources.yaml` 中管理，新增/停用源无需改代码。
- 多类型采集：RSS/Atom、Reddit RSS、Lobsters RSS、Mastodon 标签 RSS、YouTube RSS、Twitter/X 官方 API 列表、静态网页源。
- 合规抓取：自定义 User-Agent，网页源会先检查 robots.txt；Twitter/X 只使用官方 API。
- 内容处理：URL 精确去重、标题相似度合并、关键词相关性过滤、黑名单过滤。
- 分类与标签：按 `configs/keywords.yaml` 中的规则自动分类和打标签。
- 翻译与摘要改写：支持 DeepSeek、Moonshot/Kimi、OpenAI，以及通用 OpenAI-compatible API。
- Web 编辑台：支持搜索、筛选、编辑标题/摘要/分类/标签、采纳/备选/舍弃、导出 Markdown。
- 输出归档：生成 `open-source-daily-YYYY-MM-DD.md` 和 `run-summary-YYYY-MM-DD.json`。
- 定时执行：GitHub Actions 与内置服务调度均支持每日北京时间 06:00 运行。
- 通知：支持 generic、企业微信、飞书/Lark、钉钉 Webhook。
- P7 内容策划：支持 NYT / FT / The Economist 等外媒涉华开源报道监测，入选条目会标记为「外媒涉华开源观察」并提示主编点评。
- 部署：支持 Render、Docker Compose、生产 Caddy 反向代理。
- 质量审计：提供 7 天质量报告、配置校验和交付就绪检查。

## 快速运行

```bash
python -m pip install -e .[dev]
python -m pytest
python -m osdaily.cli validate
python -m osdaily.cli run --days 1
```

启动本地编辑台：

```bash
python -m osdaily.cli serve --host 127.0.0.1 --port 8765 --db data/osdaily.sqlite3 --output output/daily
```

打开：

```text
http://127.0.0.1:8765
```

## DeepSeek 翻译配置

Render 或服务器环境变量：

```text
TRANSLATION_PROVIDER=deepseek
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_MODEL=deepseek-v4-flash
TRANSLATE_ENABLED=true
REWRITE_SUMMARY_ENABLED=true
```

Moonshot/Kimi 可改为：

```text
TRANSLATION_PROVIDER=moonshot
MOONSHOT_API_KEY=你的 Moonshot API Key
MOONSHOT_MODEL=kimi-k2.6
TRANSLATE_ENABLED=true
REWRITE_SUMMARY_ENABLED=true
```

如果没有配置对应 API Key，系统仍会完成采集和 Markdown 导出，但会跳过翻译并在运行告警里提示。

## 主要命令

生成日报：

```bash
python -m osdaily.cli run --days 1 --translate --rewrite-summary --translation-limit 30
```

配置校验：

```bash
python -m osdaily.cli validate
```

7 天质量报告：

```bash
python -m osdaily.cli quality --days 7
```

交付就绪检查：

```bash
python -m osdaily.cli readiness
```

启动带每日调度的服务：

```bash
python -m osdaily.cli serve --host 0.0.0.0 --port 8765 --schedule --schedule-time 06:00 --notify
```

## 配置文件

- `configs/sources.yaml`：资讯源清单，包含名称、类型、URL、频率、分类、标签、启用状态。
- `configs/keywords.yaml`：相关性关键词、黑名单关键词、分类规则。
- `configs/kol_twitter_list.yaml`：OpenSourceKOL 的 20 个 Twitter/X 账号配置。
- `.env.example`：本地环境变量示例。
- `.env.production.example`：生产环境变量示例。

## 输出格式

日报文件位于：

```text
output/daily/open-source-daily-YYYY-MM-DD.md
```

结构包含：

- 生成时间和总条目数
- 运行统计和告警
- 按分类分组的资讯条目
- 中文标题、原始英文标题、中文摘要、来源、标签、链接
- 相似报道的相关来源链接

## GitHub Actions

工作流文件：

```text
.github/workflows/open-source-daily.yml
```

能力：

- 每天 22:00 UTC 运行，即北京时间次日 06:00。
- 支持手动 `workflow_dispatch`，可传入回溯天数。
- 每次运行会先执行测试、配置校验、交付就绪检查，再生成日报。
- 生成结果会提交回仓库。

建议配置 GitHub Secrets：

```text
CONTACT_EMAIL
DAILY_WEBHOOK_URL
DEEPSEEK_API_KEY
TWITTER_BEARER_TOKEN
TWITTER_OPEN_SOURCE_KOL_LIST_ID
```

## 当前交付状态

当前版本已达到“可试运行交付”状态：核心采集、处理、翻译、编辑、导出、部署和调度链路均已具备。生产验收仍需要连续 7 天实际运行数据，用于确认条目数、相关度、失败源、重复率和翻译质量。

详见：

- [Render 部署指南](docs/render-deployment.md)
- [部署指南](docs/deployment.md)
- [架构说明](docs/architecture.md)
- [发布检查清单](docs/release-checklist.md)

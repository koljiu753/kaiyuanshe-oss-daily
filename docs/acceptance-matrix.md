# v1.0 需求验收矩阵

更新时间：2026-06-19

## 总体结论

当前版本达到“可试运行交付”状态。核心链路已经打通：配置化资讯源、采集、过滤、去重、分类、翻译、Web 编辑、Markdown 导出、定时调度、Webhook、部署和质量审计均已具备。

最终“生产验收通过”仍需要连续 7 天真实运行数据支撑，包括每日条目数、失败源、重复率、人工可用率和翻译质量。

## 功能对照

| 需求项 | 状态 | 说明 |
| --- | --- | --- |
| RSS/Atom 源接入 | 已完成 | 科技媒体、基金会/企业博客、YouTube RSS 等已接入。 |
| Reddit / Lobsters / Hacker News | 已完成 | Reddit 和 HN 可采集；Lobsters 当前源站返回 500 时会进入失败源告警。 |
| Mastodon Feed | 已完成 | 已接入 #opensource、#foss、#linux 标签 RSS。 |
| 静态网页源 | 已完成 | 已实现 web collector，并在抓取前检查 robots.txt。 |
| 动态网页/headless | 部分完成 | 当前未引入 Playwright 采集器；优先使用结构化源，动态页作为后续增强。 |
| Twitter/X 官方 API | 已实现，待配置 | 代码和 20 KOL 配置已完成；需要官方 Bearer Token 和 List ID 后启用。 |
| 源配置化 | 已完成 | `configs/sources.yaml` 管理 25 个源，24 个启用。 |
| 过去 24 小时抓取 | 已完成 | `--days 1` 默认抓取过去 24 小时，首次运行可设置回溯天数。 |
| 关键词过滤/黑名单 | 已完成 | `configs/keywords.yaml` 可配置。 |
| URL 去重 | 已完成 | SQLite 记录 URL hash。 |
| 标题相似度去重 | 已完成 | 相似度阈值默认 0.8，保留相关来源链接。 |
| 中文翻译/摘要改写 | 已完成，待线上持续验证 | 支持 DeepSeek、Moonshot、OpenAI-compatible API。 |
| 自动分类与标签 | 已完成 | 基于关键词规则。 |
| 人工调整 | 已完成 | Web 编辑台可改标题、摘要、分类、标签、采纳状态和备注。 |
| Markdown 日报 | 已完成 | 按日期生成 `open-source-daily-YYYY-MM-DD.md`。 |
| Webhook 通知 | 已完成 | 支持 generic、企业微信、飞书/Lark、钉钉。 |
| 每日 06:00 调度 | 已完成 | GitHub Actions 和服务内置调度均支持。 |
| 手动触发 | 已完成 | CLI、GitHub Actions workflow_dispatch、Web 编辑台均支持。 |
| 监控告警 | 已完成基础版 | 记录失败源、条目数异常、翻译缺 Key 等告警。 |
| 日志 | 已完成基础版 | 记录各源成功/失败与处理统计。 |
| 部署文档 | 已完成 | Render、Docker Compose、生产部署文档已提供。 |
| 连续 7 天稳定验收 | 待运行验证 | 需要真实运行满 7 天后出具质量报告。 |

## 当前验证结果

- 测试：`19 passed`
- 配置校验：`ok=true`
- 交付就绪检查：`9/9 passed`
- 全源冒烟采集：约 95 秒生成 40 条候选资讯
- 已知外部失败源：Lobsters 当前返回 500，系统已记录为失败源告警，不影响整体日报生成

## 生产前建议

1. Render 升级到 Starter 并挂载 Persistent Disk，避免免费实例休眠和本地文件丢失。
2. 配置 DeepSeek API Key 后连续运行 7 天，确认翻译质量和成本。
3. 获取 Twitter/X 官方 API 权限和 OpenSourceKOL List ID 后启用 KOL 源。
4. 建立人工采纳反馈表，记录每日可用条目比例，用于调优关键词和分类规则。

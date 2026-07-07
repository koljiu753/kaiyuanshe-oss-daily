# P7 外媒涉华开源观察

本模块服务于「P7-总 内容策划 / 主编」中的外媒涉华开源报道监测与点评需求。

## 当前范围

系统会从以下外媒入口监测涉华开源相关内容：

- New York Times China/Open Source Monitor：通过 Google News RSS 限定 `site:nytimes.com`。
- Financial Times Technology：FT 官方 Technology RSS。
- The Economist China：The Economist 官方 China RSS。
- Reuters China/Open Source Monitor：通过 Google News RSS 限定 `site:reuters.com`。
- Bloomberg China/Open Source Monitor：通过 Google News RSS 限定 `site:bloomberg.com`。
- MIT Technology Review China/Open Source Monitor：通过 Google News RSS 限定 `site:technologyreview.com`。
- Wired China/Open Source Monitor：通过 Google News RSS 限定 `site:wired.com`。
- The Verge China/Open Source Monitor：通过 Google News RSS 限定 `site:theverge.com`。
- Rest of World China/Open Source Monitor：通过 Google News RSS 限定 `site:restofworld.org`。

采集后只有同时满足以下条件的条目才会进入日报：

- 标题或摘要命中开源专用关键词，例如 `open source`、`GitHub`、`Linux`、`open model`、`open weights`、`license` 等。
- 标题或摘要命中涉华关键词，例如 `China`、`Chinese`、`Huawei`、`Alibaba`、`DeepSeek`、`Gitee`、`OpenHarmony`、`openEuler` 等。
- 来源带有 `china-watch` 标签。

注意：`china-watch` 来源标签本身不会被当作涉华命中信号，避免把泛 AI、泛供应链报道误判为涉华开源观察。

入选条目会被归类到「外媒涉华开源观察」，并自动追加标签：

- `p7-content`
- `china-watch`
- `editorial-review`
- `外媒涉华`
- `主编点评`

Markdown 导出时会追加主编提示，提醒编辑结合华语开源社区视角补充转发语或短评。

## 运营建议

每日查看「外媒涉华开源观察」分类时，建议主编判断：

- 是否代表国际媒体对中国开源的新增叙事。
- 是否存在误读、偏见或值得补充的背景。
- 开源社是否需要转发、短评、约稿或延伸成英文博客。
- 是否需要同步给 P7 社媒运营或 P7 博客负责人。

## 后续可扩展源

可继续在 `configs/sources.yaml` 增加以下来源：

- Reuters Technology / China
- Bloomberg Technology
- MIT Technology Review
- Wired
- The Verge
- Rest of World

新增源只需加上 `china-watch` 和 `p7-content` 标签，即可进入同一套筛选规则。

# Render 部署指南

这是当前项目最简单的公网部署方式，适合试运行和给团队演示。

## 1. 创建服务

1. 打开 `https://dashboard.render.com`
2. 点击 `New`
3. 选择 `Web Service`
4. 选择 GitHub 仓库 `koljiu753/kaiyuanshe-oss-daily`
5. Runtime 保持 `Docker`
6. Branch 选择 `main`
7. Root Directory 留空

## 2. 推荐配置

试运行可以先选 `Free`。如果要稳定保存 SQLite 数据和 Markdown 日报，建议后续升级到 `Starter` 并挂载 Persistent Disk。

如果 Render 页面允许填写 Docker Command，推荐使用：

```text
python -m osdaily.cli serve --host 0.0.0.0 --db /var/data/osdaily.sqlite3 --output /var/data/output --schedule --schedule-time 06:00 --notify
```

如果使用 Persistent Disk：

```text
Mount Path: /var/data
Size: 1 GB
```

## 3. 环境变量

必填：

```text
CONTACT_EMAIL=你的邮箱
ADMIN_TOKEN=一段足够长的随机口令
PORT=8765
```

启用中文翻译和摘要改写：

```text
OPENAI_API_KEY=你的 OpenAI API Key
OPENAI_MODEL=gpt-4.1-mini
TRANSLATE_ENABLED=true
REWRITE_SUMMARY_ENABLED=true
```

可选通知：

```text
DAILY_WEBHOOK_URL=群机器人 Webhook
DAILY_WEBHOOK_TYPE=wecom
```

可选 Twitter/X：

```text
TWITTER_BEARER_TOKEN=你的 Twitter/X Bearer Token
TWITTER_OPEN_SOURCE_KOL_LIST_ID=OpenSourceKOL 列表 ID
```

## 4. 访问方式

部署成功后，Render 会提供类似这样的地址：

```text
https://kaiyuanshe-oss-daily.onrender.com
```

后台访问：

```text
https://kaiyuanshe-oss-daily.onrender.com/?token=你的 ADMIN_TOKEN
```

健康检查：

```text
https://kaiyuanshe-oss-daily.onrender.com/healthz
```

正常返回：

```json
{"ok": true}
```

## 5. 注意事项

- Render 免费实例无人访问后会休眠，首次打开可能需要等待 30-60 秒。
- 免费实例本地文件不保证长期保存，生产建议使用 Persistent Disk。
- 如果没有配置 `OPENAI_API_KEY`，系统仍会采集和导出 Markdown，但会跳过中文翻译并在运行告警里提示。
- 定时任务默认每天 `06:00` 运行，Render 环境通常按 UTC 运行；如果要精确北京时间，可以把时间换算成 UTC，或后续迁移到更可控的调度环境。

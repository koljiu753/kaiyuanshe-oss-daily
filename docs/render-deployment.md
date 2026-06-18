# Render 部署指南

这是最简单的线上部署方式，不需要自己配置服务器、Nginx 或 HTTPS。

## 1. 前置准备

- GitHub 仓库已存在：`koljiu753/kaiyuanshe-oss-daily`
- 一个管理后台口令，例如一段 24 位以上随机字符串
- 一个联系邮箱

## 2. 在 Render 创建服务

打开：

```text
https://dashboard.render.com
```

使用 GitHub 登录，然后选择：

```text
New -> Blueprint
```

选择仓库：

```text
koljiu753/kaiyuanshe-oss-daily
```

Render 会读取仓库根目录的 `render.yaml`。

## 3. 填写环境变量

必填：

```text
CONTACT_EMAIL=你的邮箱
ADMIN_TOKEN=一段足够长的随机口令
```

可选：

```text
DAILY_WEBHOOK_URL=群机器人 Webhook
DAILY_WEBHOOK_TYPE=wecom
OPENAI_API_KEY=你的 OpenAI Key
```

## 4. 部署完成后访问

Render 会给你一个地址，类似：

```text
https://kaiyuanshe-oss-daily.onrender.com
```

访问后台：

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

- Render 免费实例可能会休眠，首次打开会慢一些。
- 项目已配置 1GB 持久磁盘，SQLite 数据和导出日报会保存在 `/var/data`。
- 内置调度默认每天 `06:00` 运行。Render 使用 UTC 环境的可能性较高，如需精确北京时间，建议后续把 `SCHEDULE_TIME` 调整为对应 UTC 时间，或改用服务器部署。
- 后台必须带 `?token=ADMIN_TOKEN` 访问。

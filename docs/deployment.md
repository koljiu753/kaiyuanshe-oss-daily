# 部署指南

## 1. 本地长期运行

```powershell
cd C:\Users\Fengxt\Documents\KAIYUANSHE
python -m pip install -e .[dev]
python -m osdaily.cli run --days 1
python -m osdaily.cli serve --host 127.0.0.1 --port 8765
```

如果希望服务常驻并每天自动采集：

```powershell
python -m osdaily.cli serve --host 127.0.0.1 --port 8765 --schedule --schedule-time 06:00 --notify
```

打开：

```text
http://127.0.0.1:8765
```

## 2. 服务器正式部署

适用于一台 Linux 服务器，已安装 Docker 和 Docker Compose。

### 2.1 准备域名

将域名 A 记录解析到服务器公网 IP，例如：

```text
osdaily.example.org -> 1.2.3.4
```

服务器安全组/防火墙开放：

- `80/tcp`
- `443/tcp`

### 2.2 准备环境变量

```bash
cp .env.production.example .env.production
```

至少修改：

```bash
DOMAIN=osdaily.example.org
ADMIN_TOKEN=一段足够长的随机口令
CONTACT_EMAIL=你的联系邮箱
SCHEDULE_TIME=06:00
```

如果要通知群机器人，配置：

```bash
DAILY_WEBHOOK_URL=...
DAILY_WEBHOOK_TYPE=wecom
```

`DAILY_WEBHOOK_TYPE` 可选：

- `generic`
- `wecom`
- `feishu`
- `dingtalk`

### 2.3 启动生产服务

```bash
bash scripts/deploy-prod.sh
```

或手动执行：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
```

### 2.4 访问

```text
https://你的域名/?token=你的 ADMIN_TOKEN
```

Caddy 会自动申请和续期 HTTPS 证书。

## 3. Docker Compose 本地测试

```bash
cp .env.example .env
docker compose up --build -d
```

打开：

```text
http://localhost:8765
```

## 4. GitHub Actions

`.github/workflows/open-source-daily.yml` 会：

1. 安装依赖。
2. 运行测试。
3. 校验配置。
4. 执行 readiness 检查。
5. 生成日报。
6. 提交 `output/daily/*.md`、`output/daily/*.json` 和 SQLite 去重库。

需要配置的 Secrets：

- `CONTACT_EMAIL`
- `DAILY_WEBHOOK_URL`
- `DAILY_WEBHOOK_TYPE`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `TWITTER_BEARER_TOKEN`
- `TWITTER_OPEN_SOURCE_KOL_LIST_ID`

## 5. 健康检查

```bash
curl https://你的域名/healthz
```

返回：

```json
{"ok": true}
```

## 6. 常见运维动作

手动补采：

```bash
python -m osdaily.cli run --days 3
```

查看最近运行质量：

```bash
python -m osdaily.cli quality --days 7
```

交付就绪检查：

```bash
python -m osdaily.cli readiness
```

查看容器日志：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f
```

备份数据：

```bash
bash scripts/backup-data.sh
```

更新部署：

```bash
git pull
bash scripts/deploy-prod.sh
```

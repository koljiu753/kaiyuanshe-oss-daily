#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env.production ]]; then
  echo "Missing .env.production. Copy .env.production.example and fill DOMAIN / ADMIN_TOKEN / CONTACT_EMAIL." >&2
  exit 1
fi

docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
docker compose --env-file .env.production -f docker-compose.prod.yml ps

#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

stamp="$(date +%Y%m%d-%H%M%S)"
mkdir -p backups
tar -czf "backups/osdaily-${stamp}.tar.gz" data output configs
echo "Backup written to backups/osdaily-${stamp}.tar.gz"

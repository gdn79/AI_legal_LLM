#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${1:-$ROOT_DIR/backups}"
mkdir -p "$BACKUP_DIR"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="$BACKUP_DIR/storage_${STAMP}.tar.gz"

docker compose run --rm --no-deps backend sh -lc "tar -czf - -C /app storage" > "$OUT_FILE"
echo "Storage backup saved to $OUT_FILE"

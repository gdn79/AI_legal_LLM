#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${1:-$ROOT_DIR/backups}"
mkdir -p "$BACKUP_DIR"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="$BACKUP_DIR/postgres_${STAMP}.sql"

docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-legal_ai}" "${POSTGRES_DB:-legal_ai}" > "$OUT_FILE"
echo "PostgreSQL backup saved to $OUT_FILE"

#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup.sql>"
  exit 1
fi

BACKUP_FILE="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 1
fi

docker compose exec -T postgres psql -U "${POSTGRES_USER:-legal_ai}" -d "${POSTGRES_DB:-legal_ai}" < "$BACKUP_FILE"
echo "PostgreSQL restore completed from $BACKUP_FILE"

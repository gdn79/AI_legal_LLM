#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <storage-backup.tar.gz>"
  exit 1
fi

BACKUP_FILE="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 1
fi

docker compose run --rm --no-deps backend sh -lc "rm -rf /app/storage && mkdir -p /app/storage && tar -xzf - -C /app" < "$BACKUP_FILE"
echo "Storage restore completed from $BACKUP_FILE"

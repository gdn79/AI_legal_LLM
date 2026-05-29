#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_NAME="$(basename "$ROOT_DIR")"

echo "Resetting pilot demo data in Docker volumes and local storage..."
docker compose down
docker volume rm "${PROJECT_NAME}_postgres_data" "${PROJECT_NAME}_minio_data" "${PROJECT_NAME}_qdrant_data" "${PROJECT_NAME}_backend_storage" 2>/dev/null || true
rm -f "$ROOT_DIR/backend/legal_ai.db" "$ROOT_DIR/backend/test.db"
rm -rf "$ROOT_DIR/backend/storage"

echo "Recreating demo seed..."
(
  cd "$ROOT_DIR/backend"
  python seed.py
  python seed_demo.py
)

echo "Demo reset completed."

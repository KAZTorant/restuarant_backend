#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/admin-frontend"

if [[ ! -d "${FRONTEND_DIR}" ]]; then
  echo "admin-frontend tapılmadı, build atlanır."
  exit 0
fi

cd "${FRONTEND_DIR}"

if [[ ! -d node_modules ]]; then
  if [[ -f package-lock.json ]]; then
    npm ci
  else
    npm install
  fi
fi

npm run build

echo "admin-frontend build tamamlandı: ${FRONTEND_DIR}/dist"

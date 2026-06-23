#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/admin-frontend"

if [[ ! -d "${FRONTEND_DIR}" ]]; then
  echo "admin-frontend tapılmadı, build atlanır."
  exit 0
fi

cd "${FRONTEND_DIR}"

echo "Node: $(node --version)"
echo "npm: $(npm --version)"

# Always fresh install on deploy — avoids macOS lockfile / Linux native binding mismatch
rm -rf node_modules

if [[ -f package-lock.json ]]; then
  npm ci --include=optional
else
  npm install --include=optional
fi

npm run build

echo "admin-frontend build tamamlandı: ${FRONTEND_DIR}/dist"

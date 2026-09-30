#!/usr/bin/env bash
set -euo pipefail

SINCE="${1:-2h}"

echo "=== whatsapp service (since ${SINCE}) ==="
railway logs --service whatsapp --since "${SINCE}" --lines 200 --filter "WA"

echo
echo "=== django (since ${SINCE}) ==="
railway logs --service restuarant_backend --since "${SINCE}" --lines 200 --filter "WA"

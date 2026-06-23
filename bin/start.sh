#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"

exec daphne -b 0.0.0.0 -p "${PORT}" config.asgi:application

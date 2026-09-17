#!/usr/bin/env bash
# Запуск стенда: API и production-сборка фронтенда с одного origin.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

if [[ -z "${CONTROLS_WEB_DSN:-}" ]]; then
  if [[ -x "$ROOT/tools/pg-stand/pg_stand.sh" ]]; then
    CONTROLS_WEB_DSN="$(bash "$ROOT/tools/pg-stand/pg_stand.sh" dsn)"
  else
    echo "Укажите CONTROLS_WEB_DSN (на сервере — DSN PostgreSQL из пакета ОС)." >&2
    exit 2
  fi
fi

export CONTROLS_WEB_DSN
export CONTROLS_WEB_HOST="${CONTROLS_WEB_HOST:-0.0.0.0}"
export CONTROLS_WEB_PORT="${CONTROLS_WEB_PORT:-8080}"
export CONTROLS_WEB_ENABLE_TEST_ENDPOINTS="${CONTROLS_WEB_ENABLE_TEST_ENDPOINTS:-1}"
export CONTROLS_WEB_DEBUG="${CONTROLS_WEB_DEBUG:-0}"

echo "DSN:  $CONTROLS_WEB_DSN"
echo "Адрес: http://$CONTROLS_WEB_HOST:$CONTROLS_WEB_PORT (dist: $ROOT/frontend/dist)"
echo "Временные стендовые endpoints /api/w01-test/*: $CONTROLS_WEB_ENABLE_TEST_ENDPOINTS"

exec .venv/bin/python -m uvicorn app.main:app \
  --host "$CONTROLS_WEB_HOST" --port "$CONTROLS_WEB_PORT" \
  --log-level "${CONTROLS_WEB_LOG_LEVEL:-info}"

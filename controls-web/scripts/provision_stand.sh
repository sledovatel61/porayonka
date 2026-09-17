#!/usr/bin/env bash
# Развёртывание стенда controls-web W01 в песочнице Arena (вариант B).
#
# Почему не apt: в песочнице недоступны зеркала Debian (http и https) и Docker,
# поэтому настоящий PostgreSQL 16 берётся из npm-пакета @embedded-postgres/linux-x64.
# Это НЕ замена PostgreSQL на что-либо иное: сервер настоящий, протокол настоящий.
#
# На целевом сервере (вариант A/C) шаги 2–3 заменяются установкой PostgreSQL
# пакетом ОС — см. README.md, раздел «Запуск на сервере».
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SEED_COUNT="${W01_SEED_COUNT:-10000}"
SEED_VALUE="${W01_SEED:-20260917}"

step() { printf '\n=== %s ===\n' "$*"; }

step "1/7 Node.js и npm"
node -v
npm -v

step "2/7 бинарники PostgreSQL (npm-пакет, версия зафиксирована в tools/pg-stand/package.json)"
( cd "$ROOT/tools/pg-stand" && npm install --no-audit --no-fund )
bash "$ROOT/tools/pg-stand/pg_stand.sh" version

step "3/7 инициализация кластера, запуск, создание базы"
bash "$ROOT/tools/pg-stand/pg_stand.sh" init
bash "$ROOT/tools/pg-stand/pg_stand.sh" start
bash "$ROOT/tools/pg-stand/pg_stand.sh" createdb
DSN="$(bash "$ROOT/tools/pg-stand/pg_stand.sh" dsn)"
echo "DSN стенда: $DSN"

step "4/7 Python-окружение и установка зависимостей из lock"
python3 -V
( cd "$ROOT/backend" && python3 -m venv .venv )
"$ROOT/backend/.venv/bin/pip" install --upgrade pip
if [[ -f "$ROOT/backend/requirements.lock.txt" ]]; then
  "$ROOT/backend/.venv/bin/pip" install -r "$ROOT/backend/requirements.lock.txt"
else
  "$ROOT/backend/.venv/bin/pip" install -r "$ROOT/backend/requirements-dev.txt"
  "$ROOT/backend/.venv/bin/pip" freeze > "$ROOT/backend/requirements.lock.txt"
fi
"$ROOT/backend/.venv/bin/pip" freeze | wc -l

step "5/7 frontend: установка из lock и production-сборка"
if [[ -f "$ROOT/frontend/package-lock.json" ]]; then
  ( cd "$ROOT/frontend" && npm ci --no-audit --no-fund )
else
  ( cd "$ROOT/frontend" && npm install --no-audit --no-fund )
fi
( cd "$ROOT/frontend" && npm run build )
( cd "$ROOT/frontend" && du -sh dist && find dist -type f | sort )

step "6/7 наполнение $SEED_COUNT синтетических записей (seed $SEED_VALUE)"
( cd "$ROOT/backend" && CONTROLS_WEB_DSN="$DSN" .venv/bin/python -m app.seed --reset --count "$SEED_COUNT" --seed "$SEED_VALUE" )

step "7/7 готово"
echo "Запуск стенда:      bash $ROOT/scripts/run_stand.sh"
echo "Smoke-проверки:     bash $ROOT/scripts/smoke_http.sh"
echo "Тесты backend:      (cd $ROOT/backend && .venv/bin/python -m pytest)"
echo "Измерения (30x):    $ROOT/backend/.venv/bin/python $ROOT/scripts/measure.py --repeats 30"
echo "Остановить СУБД:    bash $ROOT/tools/pg-stand/pg_stand.sh stop"

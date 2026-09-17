#!/usr/bin/env bash
# Временный стенд W01 (вариант B): настоящий PostgreSQL 16 в песочнице Arena.
# Причина: apt-зеркала Debian (http и https) и Docker в песочнице недоступны,
# поэтому бинарники PostgreSQL берутся из npm-пакета @embedded-postgres/linux-x64.
# На целевом сервере (вариант A/C) используется PostgreSQL из пакета ОС — этот
# скрипт тогда не нужен. Данные стенда синтетические.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NATIVE="$HERE/node_modules/@embedded-postgres/linux-x64/native"
PGDATA="${CONTROLS_WEB_PGDATA:-$HERE/../../.pgdata}"
PORT="${CONTROLS_WEB_PGPORT:-5433}"
SOCKDIR="${CONTROLS_WEB_PGSOCK:-/tmp}"
DBNAME="${CONTROLS_WEB_DBNAME:-controls_web_w01}"
DBUSER="${CONTROLS_WEB_DBUSER:-controls_web}"
BACKEND_PY="${CONTROLS_WEB_PYTHON:-$HERE/../../backend/.venv/bin/python}"
export LD_LIBRARY_PATH="$NATIVE/lib:${LD_LIBRARY_PATH:-}"

if [[ ! -x "$NATIVE/bin/postgres" ]]; then
  echo "Бинарники PostgreSQL не найдены. Выполните: (cd $HERE && npm install)" >&2
  exit 2
fi

cmd="${1:-status}"
case "$cmd" in
  version)
    "$NATIVE/bin/postgres" --version
    ;;
  init)
    mkdir -p "$PGDATA"
    if [[ -f "$PGDATA/PG_VERSION" ]]; then
      echo "Кластер уже инициализирован: $PGDATA"
    else
      "$NATIVE/bin/initdb" -D "$PGDATA" -U "$DBUSER" --auth=trust --encoding=UTF8 --locale=C.utf8
    fi
    ;;
  start)
    mkdir -p "$PGDATA" "$SOCKDIR"
    if "$NATIVE/bin/pg_ctl" -D "$PGDATA" status > /dev/null 2>&1; then
      echo "PostgreSQL уже запущен (порт $PORT)"
      exit 0
    fi
    "$NATIVE/bin/pg_ctl" -D "$PGDATA" -l "$PGDATA/pg.log" -w start \
      -o "-p $PORT -k $SOCKDIR -c listen_addresses=127.0.0.1 -c unix_socket_directories=$SOCKDIR -c log_min_messages=warning"
    "$NATIVE/bin/postgres" --version
    ;;
  stop)
    "$NATIVE/bin/pg_ctl" -D "$PGDATA" -m fast -w stop
    ;;
  status)
    "$NATIVE/bin/pg_ctl" -D "$PGDATA" status || true
    ;;
  createdb)
    "$BACKEND_PY" - "$DBUSER" "$DBNAME" "$PORT" <<'PY'
import sys
import psycopg
user, dbname, port = sys.argv[1], sys.argv[2], sys.argv[3]
dsn = f"postgresql://{user}@127.0.0.1:{port}/postgres"
with psycopg.connect(dsn, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
        if cur.fetchone():
            print(f"База {dbname} уже существует")
        else:
            cur.execute(f'CREATE DATABASE "{dbname}" ENCODING \'UTF8\'')
            print(f"База {dbname} создана")
        cur.execute("SHOW server_encoding")
        print("server_encoding:", cur.fetchone()[0])
        cur.execute("SELECT version()")
        print("version:", cur.fetchone()[0])
PY
    ;;
  dsn)
    echo "postgresql://${DBUSER}@127.0.0.1:${PORT}/${DBNAME}"
    ;;
  *)
    echo "Использование: $0 {version|init|start|stop|status|createdb|dsn}" >&2
    exit 64
    ;;
esac

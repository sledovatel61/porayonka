"""Доступ к PostgreSQL (psycopg 3). Пул соединений — задача W07, здесь соединение на запрос."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def connect(dsn: str, *, autocommit: bool = True) -> psycopg.Connection:
    return psycopg.connect(dsn, row_factory=dict_row, autocommit=autocommit)


@contextmanager
def connection(dsn: str) -> Iterator[psycopg.Connection]:
    conn = connect(dsn)
    try:
        yield conn
    finally:
        conn.close()


def apply_schema(conn: psycopg.Connection) -> None:
    """Идемпотентное применение схемы стенда (CREATE ... IF NOT EXISTS)."""
    conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))


def ping(conn: psycopg.Connection) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 AS ok")
        row = cur.fetchone()
    return bool(row and row.get("ok") == 1)


def server_version(conn: psycopg.Connection) -> str:
    with conn.cursor() as cur:
        cur.execute("SHOW server_version")
        row = cur.fetchone()
    value = list(row.values())[0] if isinstance(row, dict) else row[0]
    return str(value)

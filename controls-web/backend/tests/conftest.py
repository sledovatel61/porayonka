"""Фикстуры стенда: отдельная тестовая база на настоящем PostgreSQL (не SQLite).

Тестовая БД создаётся один раз на сессию pytest и очищается TRUNCATE (DROP не
выполняется). Наполнение — детерминированное (seed 20260917, 10 000 записей).
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import db, seed
from app.config import Settings
from app.main import create_app

PGHOST = os.environ.get("CONTROLS_WEB_TEST_PGHOST", "127.0.0.1")
PGPORT = os.environ.get("CONTROLS_WEB_TEST_PGPORT", "5433")
PGUSER = os.environ.get("CONTROLS_WEB_TEST_PGUSER", "controls_web")
TEST_DB = os.environ.get("CONTROLS_WEB_TEST_DB", "controls_web_w01_test")
ADMIN_DSN = f"postgresql://{PGUSER}@{PGHOST}:{PGPORT}/postgres"
TEST_DSN = f"postgresql://{PGUSER}@{PGHOST}:{PGPORT}/{TEST_DB}"
SEED_VALUE = seed.DEFAULT_SEED
SEED_COUNT = 10_000


def _ensure_database() -> None:
    with psycopg.connect(ADMIN_DSN, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{TEST_DB}" ENCODING \'UTF8\'')
    with db.connection(TEST_DSN) as conn:
        db.apply_schema(conn)
        cur = conn.execute("SELECT count(*) AS n FROM controls")
        if int(cur.fetchone()["n"]) != SEED_COUNT:
            seed.load(conn, seed=SEED_VALUE, count=SEED_COUNT, reset=True)
        else:
            conn.execute("TRUNCATE attachments CASCADE")


@pytest.fixture(scope="session")
def test_dsn() -> Iterator[str]:
    _ensure_database()
    yield TEST_DSN


@pytest.fixture(scope="session")
def uploads_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("uploads-w01")


@pytest.fixture(scope="session")
def settings(test_dsn: str, uploads_dir: Path) -> Settings:
    dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    return Settings(
        dsn=test_dsn,
        host="127.0.0.1",
        port=8080,
        frontend_dist=dist if dist.is_dir() else None,
        uploads_dir=uploads_dir,
        enable_test_endpoints=True,
        auto_schema=True,
        debug=False,
    )


@pytest.fixture(scope="session")
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture()
def conn(test_dsn: str) -> Iterator[psycopg.Connection]:
    with db.connection(test_dsn) as connection:
        yield connection


@pytest.fixture(scope="session")
def first_control_id(client: TestClient) -> str:
    response = client.get("/api/controls", params={"page": 1, "page_size": 1, "include_archived": True})
    assert response.status_code == 200, response.text
    return str(response.json()["items"][0]["id"])


@pytest.fixture(scope="session")
def sample_pdf_bytes(client: TestClient) -> bytes:
    response = client.get("/api/w01-test/sample-pdf")
    assert response.status_code == 200, response.text
    return response.content

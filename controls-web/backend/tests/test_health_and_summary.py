"""Живость стенда, настоящая БД, сводные счётчики."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_ok_and_database_is_postgresql(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    version = body["postgres_version"] or ""
    major = int(version.split(".")[0]) if version.split(".")[0].isdigit() else 0
    assert major >= 14, f"ожидается PostgreSQL >= 14, получено: {version!r}"
    assert "SQLite" not in version


def test_health_supports_head_for_monitoring(client: TestClient) -> None:
    response = client.head("/api/health")
    assert response.status_code == 200


def test_summary_counters_consistent(client: TestClient) -> None:
    body = client.get("/api/meta/summary").json()
    assert body["total"] == 10_000
    assert 0 < body["active"] < body["total"]
    assert body["archived"] > 0
    assert body["done"] > 0
    assert body["active"] + body["done"] + body["archived"] <= body["total"] + body["done"]


def test_error_shape_is_russian_and_has_no_traceback(client: TestClient) -> None:
    response = client.get("/api/controls/not-a-uuid")
    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "bad_request"
    assert body["error"]["message"]
    assert "Traceback" not in response.text


def test_timing_header_present(client: TestClient) -> None:
    response = client.get("/api/controls", params={"page": 1, "page_size": 50})
    assert response.status_code == 200
    header = response.headers.get("X-Process-Time-Ms")
    assert header is not None
    assert float(header) >= 0.0

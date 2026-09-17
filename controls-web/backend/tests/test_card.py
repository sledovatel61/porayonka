"""Карточка записи: только чтение, кириллица, пункты, вложения, ошибки."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def has_cyrillic(text: str) -> bool:
    return any("\u0400" <= ch <= "\u04ff" for ch in text)


def test_card_returns_cyrillic_fields(client: TestClient, first_control_id: str, conn) -> None:
    response = client.get(f"/api/controls/{first_control_id}")
    assert response.status_code == 200
    card = response.json()
    assert card["id"] == first_control_id
    assert card["incoming_number"].startswith("СТЕНД-")
    assert has_cyrillic(card["content"])
    assert has_cyrillic(card["executor"])
    assert has_cyrillic(card["initiator"])
    assert card["created_at"] and card["updated_at"]


def test_card_tasks_match_database_and_are_ordered(
    client: TestClient, first_control_id: str, conn
) -> None:
    card = client.get(f"/api/controls/{first_control_id}").json()
    rows = conn.execute(
        "SELECT count(*) AS n FROM control_tasks WHERE control_id = %s", (uuid.UUID(first_control_id),)
    ).fetchone()
    assert len(card["tasks"]) == rows["n"]
    positions = [task["position"] for task in card["tasks"]]
    assert positions == sorted(positions)
    assert positions == list(range(1, len(positions) + 1))


def test_card_is_read_only_no_write_methods(client: TestClient, first_control_id: str) -> None:
    for method in ("post", "put", "patch", "delete"):
        response = getattr(client, method)(f"/api/controls/{first_control_id}")
        assert response.status_code == 405, f"{method.upper()} должен быть запрещён на карточке"


def test_unknown_control_returns_404_with_russian_message(client: TestClient) -> None:
    response = client.get("/api/controls/00000000-0000-5000-8000-000000000000")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert has_cyrillic(body["error"]["message"])


def test_malformed_id_returns_422(client: TestClient) -> None:
    response = client.get("/api/controls/не-uuid")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "bad_request"


def test_archived_control_card_is_readable(client: TestClient, conn) -> None:
    row = conn.execute("SELECT id::text AS id FROM controls WHERE archived = true LIMIT 1").fetchone()
    assert row is not None, "в стендовых данных должны быть архивные записи"
    card = client.get(f"/api/controls/{row['id']}").json()
    assert card["archived"] is True


def test_card_attachments_list_is_present(client: TestClient, first_control_id: str) -> None:
    card = client.get(f"/api/controls/{first_control_id}").json()
    assert isinstance(card["attachments"], list)

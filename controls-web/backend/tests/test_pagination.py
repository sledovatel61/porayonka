"""Корректность серверной пагинации по 50 строк на 10 000 записей."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

PAGE_SIZE = 50


def test_first_page_has_exactly_50_rows(client: TestClient) -> None:
    body = client.get("/api/controls", params={"page": 1, "page_size": PAGE_SIZE, "include_archived": True}).json()
    assert len(body["items"]) == PAGE_SIZE
    assert body["total"] == 10_000
    assert body["pages"] == 200
    assert body["page"] == 1
    assert body["page_size"] == PAGE_SIZE


def test_last_page_full_and_beyond_last_empty(client: TestClient) -> None:
    last = client.get("/api/controls", params={"page": 200, "page_size": PAGE_SIZE, "include_archived": True}).json()
    assert len(last["items"]) == PAGE_SIZE
    beyond = client.get("/api/controls", params={"page": 201, "page_size": PAGE_SIZE, "include_archived": True}).json()
    assert beyond["items"] == []
    assert beyond["total"] == 10_000
    assert beyond["pages"] == 200


def test_pages_do_not_overlap(client: TestClient) -> None:
    seen: set[str] = set()
    for page in range(1, 6):
        body = client.get(
            "/api/controls", params={"page": page, "page_size": PAGE_SIZE, "include_archived": True}
        ).json()
        ids = [item["id"] for item in body["items"]]
        assert len(ids) == PAGE_SIZE
        assert not (seen & set(ids)), f"пересечение на странице {page}"
        seen.update(ids)
    assert len(seen) == 5 * PAGE_SIZE


def test_archived_hidden_by_default(client: TestClient) -> None:
    default = client.get("/api/controls", params={"page": 1, "page_size": PAGE_SIZE}).json()
    full = client.get("/api/controls", params={"page": 1, "page_size": PAGE_SIZE, "include_archived": True}).json()
    assert default["total"] < full["total"]
    assert all(item["archived"] is False for item in default["items"])


@pytest.mark.parametrize("bad_page_size", [0, -1, 10_000, 201])
def test_page_size_limits_rejected(client: TestClient, bad_page_size: int) -> None:
    response = client.get("/api/controls", params={"page": 1, "page_size": bad_page_size})
    assert response.status_code == 422


def test_page_number_limits_rejected(client: TestClient) -> None:
    assert client.get("/api/controls", params={"page": 0}).status_code == 422
    assert client.get("/api/controls", params={"page": -5}).status_code == 422


def test_max_allowed_page_size_does_not_return_all_records(client: TestClient) -> None:
    body = client.get("/api/controls", params={"page": 1, "page_size": 200, "include_archived": True}).json()
    assert len(body["items"]) == 200
    assert body["total"] == 10_000


def test_ordering_is_stable_and_desc_by_receive_date(client: TestClient) -> None:
    body = client.get("/api/controls", params={"page": 1, "page_size": PAGE_SIZE, "include_archived": True}).json()
    dates = [item["receive_date"] for item in body["items"]]
    assert dates == sorted(dates, reverse=True)
    again = client.get("/api/controls", params={"page": 1, "page_size": PAGE_SIZE, "include_archived": True}).json()
    assert [item["id"] for item in again["items"]] == [item["id"] for item in body["items"]]


@pytest.mark.slow
def test_full_sweep_200_pages_returns_all_10000_unique_ids(client: TestClient) -> None:
    collected: list[str] = []
    for page in range(1, 201):
        body = client.get(
            "/api/controls", params={"page": page, "page_size": PAGE_SIZE, "include_archived": True}
        ).json()
        assert len(body["items"]) == PAGE_SIZE, f"страница {page}"
        collected.extend(item["id"] for item in body["items"])
    assert len(collected) == 10_000
    assert len(set(collected)) == 10_000, "пагинация потеряла или повторила записи"

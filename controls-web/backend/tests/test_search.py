"""Поиск по кириллице, экранирование LIKE, согласованность с пагинацией."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_search_by_exact_incoming_number(client: TestClient) -> None:
    body = client.get("/api/controls", params={"search": "СТЕНД-000042", "include_archived": True}).json()
    assert body["total"] == 1
    assert body["items"][0]["incoming_number"] == "СТЕНД-000042"


def test_search_is_case_insensitive(client: TestClient) -> None:
    upper = client.get("/api/controls", params={"search": "СТЕНД-0001", "include_archived": True}).json()
    lower = client.get("/api/controls", params={"search": "стенд-0001", "include_archived": True}).json()
    assert upper["total"] == lower["total"] > 0
    assert [i["id"] for i in upper["items"]] == [i["id"] for i in lower["items"]]


def test_search_by_cyrillic_content_term(client: TestClient, conn) -> None:
    term = "сводку"
    body = client.get("/api/controls", params={"search": term, "page_size": 50, "include_archived": True}).json()
    assert body["total"] > 0
    ids = [item["id"] for item in body["items"]]
    rows = conn.execute(
        "SELECT id::text AS id, content, initiator, executor, controller, department, incoming_number "
        "FROM controls WHERE id = ANY(%s)",
        (ids,),
    ).fetchall()
    assert len(rows) == len(ids)
    for row in rows:
        haystack = " ".join(
            str(row[col]) for col in ("content", "initiator", "executor", "controller", "department", "incoming_number")
        )
        assert term.lower() in haystack.lower(), f"термин не найден в записи {row['id']}"


def test_search_finds_by_executor_surname(client: TestClient, conn) -> None:
    row = conn.execute("SELECT executor FROM controls WHERE executor <> '' LIMIT 1").fetchone()
    surname = row["executor"].split()[0]
    body = client.get("/api/controls", params={"search": surname, "include_archived": True}).json()
    assert body["total"] > 0
    assert any(item["executor"].startswith(surname) for item in body["items"])


def test_percent_and_underscore_are_escaped(client: TestClient) -> None:
    for term in ("%", "_", "%%", "СТЕНД%"):
        body = client.get("/api/controls", params={"search": term, "include_archived": True}).json()
        assert body["total"] == 0, f"термин {term!r} сработал как шаблон LIKE"


def test_search_without_results(client: TestClient) -> None:
    body = client.get("/api/controls", params={"search": "zzz-нет-такого-термина"}).json()
    assert body["total"] == 0
    assert body["items"] == []
    assert body["pages"] == 0


def test_search_pagination_consistent(client: TestClient) -> None:
    term = "СТЕНД-0001"
    first = client.get(
        "/api/controls", params={"search": term, "page": 1, "page_size": 10, "include_archived": True}
    ).json()
    assert first["page_size"] == 10
    assert first["pages"] == -(-first["total"] // 10)
    seen = {item["id"] for item in first["items"]}
    if first["pages"] > 1:
        second = client.get(
            "/api/controls", params={"search": term, "page": 2, "page_size": 10, "include_archived": True}
        ).json()
        assert not (seen & {item["id"] for item in second["items"]})


def test_empty_search_equals_no_search(client: TestClient) -> None:
    with_empty = client.get("/api/controls", params={"search": "   ", "include_archived": True}).json()
    without = client.get("/api/controls", params={"include_archived": True}).json()
    assert with_empty["total"] == without["total"]

"""Синтетический PDF с кириллицей: генерация, выбор/загрузка, скачивание, дубли.

Проверяется через ВРЕМЕННЫЕ стендовые endpoints /api/w01-test/*, которые должны
быть удалены или закрыты до передачи W02.
"""
from __future__ import annotations

import dataclasses
import hashlib
import io
from pathlib import Path
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.main import create_app

CYR_NAME = "синтетический-отчёт-стенда.pdf"


def pdf_text(payload: bytes) -> str:
    return "".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(payload)).pages)


def upload(
    client: TestClient,
    name: str,
    payload: bytes,
    control_id: str | None,
    content_type: str = "application/pdf",
):
    data = {"control_id": control_id} if control_id else {}
    return client.post(
        "/api/w01-test/uploads",
        files={"file": (name, payload, content_type)},
        data=data,
    )


def test_sample_pdf_is_valid_and_contains_cyrillic(sample_pdf_bytes: bytes) -> None:
    assert sample_pdf_bytes[:4] == b"%PDF"
    assert len(sample_pdf_bytes) > 1024
    text = pdf_text(sample_pdf_bytes)
    assert any("\u0400" <= ch <= "\u04ff" for ch in text), f"кириллица не извлекается: {text[:80]!r}"


def test_sample_pdf_header_is_rfc5987_encoded(client: TestClient) -> None:
    response = client.get("/api/w01-test/sample-pdf", params={"file_name": CYR_NAME})
    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    assert "filename*=UTF-8''" in disposition
    encoded = disposition.split("filename*=UTF-8''", 1)[1].strip()
    assert unquote(encoded) == CYR_NAME
    assert all(ord(ch) < 128 for ch in disposition), "в заголовке не должно быть не-ASCII байтов"


def test_upload_download_roundtrip_preserves_bytes_and_name(
    client: TestClient, sample_pdf_bytes: bytes, first_control_id: str, uploads_dir: Path
) -> None:
    response = upload(client, CYR_NAME, sample_pdf_bytes, first_control_id)
    assert response.status_code == 201, response.text
    body = response.json()
    attachment = body["attachment"]
    assert attachment["file_name"] == CYR_NAME
    assert attachment["size_bytes"] == len(sample_pdf_bytes)
    assert attachment["sha256"] == hashlib.sha256(sample_pdf_bytes).hexdigest()
    assert attachment["rel_path"] == f"{first_control_id}/{CYR_NAME}"
    assert body["created"] is True

    stored = uploads_dir / first_control_id / CYR_NAME
    assert stored.is_file()
    assert stored.read_bytes() == sample_pdf_bytes

    download = client.get(f"/api/w01-test/uploads/{attachment['id']}/content")
    assert download.status_code == 200
    assert download.content == sample_pdf_bytes
    disposition = download.headers["content-disposition"]
    assert "filename*=utf-8''" in disposition.lower()
    assert unquote(disposition.split("''", 1)[1].strip()) == CYR_NAME

    # удаление за стендом (чтобы не влиять на другие тесты)
    assert client.delete(f"/api/w01-test/uploads/{attachment['id']}").status_code == 204
    assert not stored.exists()
    assert client.get(f"/api/w01-test/uploads/{attachment['id']}").status_code == 404


def test_same_name_different_content_rejected_with_409(
    client: TestClient, sample_pdf_bytes: bytes, first_control_id: str
) -> None:
    first = upload(client, CYR_NAME, sample_pdf_bytes, first_control_id)
    assert first.status_code == 201, first.text
    attachment_id = first.json()["attachment"]["id"]

    other = upload(client, CYR_NAME, "%PDF-1.4\nдругое синтетическое содержимое\n%%EOF\n".encode("utf-8"), first_control_id)
    assert other.status_code == 409
    message = other.json()["error"]["message"]
    assert any("\u0400" <= ch <= "\u04ff" for ch in message)

    # повторная загрузка идентичного файла идемпотентна
    again = upload(client, CYR_NAME, sample_pdf_bytes, first_control_id)
    assert again.status_code == 201
    assert again.json()["created"] is False
    assert again.json()["attachment"]["id"] == attachment_id

    client.delete(f"/api/w01-test/uploads/{attachment_id}")


def test_upload_validations(client: TestClient, sample_pdf_bytes: bytes, first_control_id: str) -> None:
    text_payload = "не pdf".encode("utf-8")
    # заявлен посторонний тип -> 415
    assert upload(client, "файл.txt", text_payload, first_control_id, "text/plain").status_code == 415
    # заявлен PDF, но содержимое не PDF -> 415 (проверка сигнатуры)
    assert upload(client, "обман.pdf", text_payload, first_control_id).status_code == 415
    assert upload(client, CYR_NAME, b"", first_control_id).status_code == 422
    assert upload(client, CYR_NAME, sample_pdf_bytes, "не-uuid").status_code == 422
    assert upload(
        client, CYR_NAME, sample_pdf_bytes, "00000000-0000-5000-8000-000000000000"
    ).status_code == 404


def test_upload_without_control_is_allowed_for_stand(client: TestClient, sample_pdf_bytes: bytes) -> None:
    response = upload(client, CYR_NAME, sample_pdf_bytes, None)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["attachment"]["control_id"] is None
    assert body["attachment"]["rel_path"].startswith("unassigned/")
    client.delete(f"/api/w01-test/uploads/{body['attachment']['id']}")


def test_oversize_upload_rejected(settings, sample_pdf_bytes: bytes, first_control_id: str) -> None:
    small = dataclasses.replace(settings, upload_max_bytes=len(sample_pdf_bytes) - 1)
    with TestClient(create_app(small)) as limited:
        response = upload(limited, CYR_NAME, sample_pdf_bytes, first_control_id)
    assert response.status_code == 413
    assert "МБ" in response.json()["error"]["message"]


def test_dangerous_file_name_is_sanitized(client: TestClient, sample_pdf_bytes: bytes) -> None:
    response = upload(client, "../../etc/passwd.pdf", sample_pdf_bytes, None)
    assert response.status_code == 201, response.text
    name = response.json()["attachment"]["file_name"]
    assert "/" not in name and "\\" not in name and ".." not in name
    client.delete(f"/api/w01-test/uploads/{response.json()['attachment']['id']}")


def test_uploads_directory_is_not_served_statically(
    client: TestClient, sample_pdf_bytes: bytes, first_control_id: str
) -> None:
    response = upload(client, CYR_NAME, sample_pdf_bytes, first_control_id)
    assert response.status_code == 201
    rel_path = response.json()["attachment"]["rel_path"]
    assert client.get(f"/uploads/{rel_path}").status_code == 404
    assert client.get(f"/{rel_path}").status_code == 404
    client.delete(f"/api/w01-test/uploads/{response.json()['attachment']['id']}")


def test_test_endpoints_are_marked_temporary(client: TestClient) -> None:
    info = client.get("/api/w01-test/info").json()
    assert info["temporary"] is True
    assert "W02" in info["warning"]


def test_attachment_visible_in_card(client: TestClient, sample_pdf_bytes: bytes, first_control_id: str) -> None:
    created = upload(client, CYR_NAME, sample_pdf_bytes, first_control_id)
    assert created.status_code == 201
    attachment_id = created.json()["attachment"]["id"]
    card = client.get(f"/api/controls/{first_control_id}").json()
    assert any(item["id"] == attachment_id for item in card["attachments"])
    client.delete(f"/api/w01-test/uploads/{attachment_id}")


def test_test_endpoints_absent_when_disabled(settings) -> None:
    hardened = dataclasses.replace(settings, enable_test_endpoints=False, auto_schema=False)
    with TestClient(create_app(hardened)) as strict_client:
        assert strict_client.get("/api/w01-test/info").status_code == 404
        assert strict_client.get("/api/openapi.json").status_code == 404
        assert strict_client.get("/api/health").status_code == 200


def test_generated_pdf_is_repeatable(client: TestClient) -> None:
    payloads = [
        client.get("/api/w01-test/sample-pdf", params={"text": "Один и тот же текст"}).content for _ in range(2)
    ]
    assert all(payload[:4] == b"%PDF" and len(payload) > 1024 for payload in payloads)
    assert all(any("\u0400" <= ch <= "\u04ff" for ch in pdf_text(payload)) for payload in payloads)

"""ВРЕМЕННЫЕ стендовые endpoints W01 (загрузка/скачивание синтетического PDF).

Помечены как временные: до передачи W02 их необходимо удалить или закрыть
(см. migration-web/reports/W01.md). Публичной раздачи файлов вне этих
endpoint'ов нет, каталог загрузок не отдаётся статикой.
"""
from __future__ import annotations

import hashlib
import re
import uuid
from urllib.parse import quote
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from . import db, repo
from .config import Settings
from .models import AttachmentOut
from .sample_pdf import build_sample_pdf

WARNING = (
    "Временный стендовый endpoint W01. Не является частью рабочей системы: "
    "должен быть удалён или закрыт до передачи этапа W02."
)
_ALLOWED_CONTENT_TYPES = {"application/pdf"}
_UNASSIGNED = "unassigned"
_FORBIDDEN_IN_NAME = re.compile(r"[\x00-\x1f/\\:*?\"<>|]+")


class UploadResult(BaseModel):
    attachment: AttachmentOut
    created: bool
    w01_test_endpoint: str = WARNING


class TestInfo(BaseModel):
    stage: str = "W01"
    temporary: bool = True
    warning: str = WARNING
    endpoints: list[str]


def safe_file_name(raw: str | None, fallback: str = "без_имени.pdf") -> str:
    name = Path(raw or "").name.strip()
    name = _FORBIDDEN_IN_NAME.sub("_", name).strip(" .")
    if not name:
        return fallback
    return name[:180]


def build_test_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api/w01-test", tags=["w01-test (временные)"])

    @router.get("/info", response_model=TestInfo, summary="Что это за endpoints")
    def info() -> TestInfo:
        return TestInfo(
            endpoints=[
                "GET  /api/w01-test/info",
                "GET  /api/w01-test/sample-pdf",
                "POST /api/w01-test/uploads",
                "GET  /api/w01-test/uploads/{id}",
                "GET  /api/w01-test/uploads/{id}/content",
                "DELETE /api/w01-test/uploads/{id}",
            ]
        )

    @router.get("/sample-pdf", summary="Синтетический PDF с кириллицей")
    def sample_pdf(text: str = "Синтетический документ стенда W01: проверка кириллицы в PDF.",
                   file_name: str = "синтетический-документ-стенда.pdf") -> Response:
        try:
            payload, _font = build_sample_pdf(text)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        name = safe_file_name(file_name)
        # RFC 5987: не-ASCII имя файла в заголовке обязано быть percent-encoded,
        # иначе starlette падает на latin-1 (найдено smoke-проверкой W01)
        encoded = quote(name, safe="")
        return Response(
            content=payload,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="sample.pdf"; filename*=UTF-8\'\'{encoded}'
            },
        )

    @router.post("/uploads", response_model=UploadResult, status_code=201, summary="Загрузка файла на стенд")
    async def upload(file: UploadFile = File(...), control_id: str | None = Form(default=None)) -> UploadResult:
        if (file.content_type or "") not in _ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"Стенд принимает только PDF (получено: {file.content_type or 'не указано'}).",
            )
        owner = _UNASSIGNED
        if control_id:
            try:
                uuid.UUID(control_id)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="control_id должен быть UUID.") from exc
            with db.connection(settings.dsn) as conn:
                if not repo.get_control(conn, control_id):
                    raise HTTPException(status_code=404, detail="Запись с таким control_id не найдена.")
            owner = control_id

        file_name = safe_file_name(file.filename)
        payload = await file.read()
        if not payload:
            raise HTTPException(status_code=422, detail="Пустой файл не принимается.")
        if len(payload) > settings.upload_max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Файл больше ограничения стенда ({settings.upload_max_bytes // (1024 * 1024)} МБ).",
            )
        if not payload.startswith(b"%PDF"):
            # заявленный тип не подтверждён содержимым: на стенде принимаются только настоящие PDF
            raise HTTPException(
                status_code=415,
                detail="Содержимое файла не является PDF (отсутствует сигнатура %PDF).",
            )
        digest = hashlib.sha256(payload).hexdigest()
        rel_path = f"{owner}/{file_name}"

        settings.uploads_dir.mkdir(parents=True, exist_ok=True)
        target_dir = settings.uploads_dir / owner
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / file_name

        with db.connection(settings.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id::text AS id, control_id::text AS control_id, rel_path, file_name, "
                    "size_bytes, sha256, content_type, created_at FROM attachments WHERE rel_path = %s",
                    (rel_path,),
                )
                existing = cur.fetchone()
            if existing:
                if existing["sha256"] != digest or existing["size_bytes"] != len(payload):
                    # правило legacy: тот же путь и другое содержимое отвергается
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Файл с таким именем уже приложен к этой записи и отличается по содержимому. "
                            "Переименуйте файл или замените существующее вложение явно."
                        ),
                    )
                attachment = dict(existing)
                created = False
            else:
                if existing is None and target.exists():
                    raise HTTPException(
                        status_code=409,
                        detail="Файл с таким именем уже есть в хранилище стенда, но отсутствует в базе.",
                    )
                attachment_id = uuid.uuid4()
                target.write_bytes(payload)
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO attachments (id, control_id, rel_path, file_name, size_bytes, sha256, content_type) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                        "RETURNING id::text AS id, control_id::text AS control_id, rel_path, file_name, "
                        "size_bytes, sha256, content_type, created_at",
                        (
                            attachment_id,
                            uuid.UUID(owner) if owner != _UNASSIGNED else None,
                            rel_path,
                            file_name,
                            len(payload),
                            digest,
                            file.content_type or "application/pdf",
                        ),
                    )
                    attachment = dict(cur.fetchone())
                created = True

        attachment["download_url"] = f"/api/w01-test/uploads/{attachment['id']}/content"
        return UploadResult(attachment=AttachmentOut(**attachment), created=created)

    def _fetch(settings_: Settings, attachment_id: str) -> dict[str, Any]:
        try:
            uuid.UUID(attachment_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Идентификатор вложения должен быть UUID.") from exc
        with db.connection(settings_.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id::text AS id, control_id::text AS control_id, rel_path, file_name, "
                    "size_bytes, sha256, content_type, created_at FROM attachments WHERE id = %s",
                    (attachment_id,),
                )
                row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Вложение не найдено.")
        return dict(row)

    @router.get("/uploads/{attachment_id}", response_model=AttachmentOut, summary="Метаданные вложения")
    def upload_meta(attachment_id: str) -> AttachmentOut:
        row = _fetch(settings, attachment_id)
        row["download_url"] = f"/api/w01-test/uploads/{row['id']}/content"
        return AttachmentOut(**row)

    @router.get("/uploads/{attachment_id}/content", summary="Скачивание вложения")
    def upload_content(attachment_id: str) -> FileResponse:
        row = _fetch(settings, attachment_id)
        path = settings.uploads_dir / row["rel_path"]
        if not path.is_file():
            raise HTTPException(status_code=410, detail="Файл отсутствует в хранилище стенда.")
        return FileResponse(path, media_type=row["content_type"], filename=row["file_name"])

    @router.delete("/uploads/{attachment_id}", status_code=204, summary="Удаление вложения (уборка стенда)")
    def upload_delete(attachment_id: str) -> Response:
        row = _fetch(settings, attachment_id)
        path = settings.uploads_dir / row["rel_path"]
        with db.connection(settings.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM attachments WHERE id = %s", (attachment_id,))
        if path.is_file():
            path.unlink()
        return Response(status_code=204)

    return router

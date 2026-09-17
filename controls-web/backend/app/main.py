"""FastAPI-приложение технического стенда controls-web (этап W01).

Сквозной путь: backend -> PostgreSQL -> постраничный список (50 строк) -> карточка чтения.
Production-сборка фронтенда отдаётся с того же origin. Временные стендовые
endpoints /api/w01-test/* должны быть удалены или закрыты до передачи W02.
"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import psycopg
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import db, repo
from .config import Settings, load_settings
from .models import (
    AttachmentOut,
    ControlCard,
    ControlListItem,
    ControlsPage,
    ErrorDetail,
    ErrorOut,
    HealthOut,
    SummaryOut,
    TaskOut,
)
from .w01test import build_test_router

APP_VERSION = "0.1.0-w01"
STAND_NOTE = "Технический стенд W01 на синтетических данных. Не рабочая система."
logger = logging.getLogger("controls_web")

_ERROR_CODES = {
    400: "bad_request",
    404: "not_found",
    409: "conflict",
    410: "gone",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "bad_request",
}


def _error_code(status_code: int) -> str:
    return _ERROR_CODES.get(status_code, "internal" if status_code >= 500 else "error")


def _error_response(status_code: int, message: str, headers: dict[str, str] | None = None) -> JSONResponse:
    body = ErrorOut(error=ErrorDetail(code=_error_code(status_code), message=message)).model_dump()
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or load_settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if cfg.auto_schema:
            try:
                with db.connection(cfg.dsn) as conn:
                    db.apply_schema(conn)
                    logger.info("Схема стенда применена; PostgreSQL %s", db.server_version(conn))
            except psycopg.Error:
                logger.exception("Не удалось применить схему стенда при старте")
        logger.info("Стенд запущен: dist=%s, test-endpoints=%s", cfg.frontend_dist, cfg.enable_test_endpoints)
        yield

    app = FastAPI(
        title="Контроли — технический стенд W01",
        version=APP_VERSION,
        summary=STAND_NOTE,
        debug=cfg.debug,
        lifespan=lifespan,
        docs_url="/api/docs" if cfg.enable_test_endpoints else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if cfg.enable_test_endpoints else None,
    )

    @app.middleware("http")
    async def timing_header(request: Request, call_next: Any) -> Any:
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - started) * 1000:.2f}"
        return response

    @app.exception_handler(HTTPException)
    async def on_http_exception(_request: Request, exc: HTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Запрос отклонён."
        return _error_response(exc.status_code, message, getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def on_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        first = (exc.errors() or [{}])[0]
        field = ".".join(str(part) for part in first.get("loc", ()) if part not in ("query", "body", "path"))
        message = f"Проверьте параметры запроса: {field or 'поля'} — {first.get('msg', 'недопустимое значение')}."
        return _error_response(422, message)

    @app.exception_handler(Exception)
    async def on_unhandled(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Необработанная ошибка стенда")
        return _error_response(500, "Внутренняя ошибка сервера стенда.")

    @app.get("/api/", summary="Справка стенда")
    def api_root() -> dict[str, Any]:
        return {
            "stand": STAND_NOTE,
            "version": APP_VERSION,
            "endpoints": [
                "GET /api/health",
                "GET /api/meta/summary",
                "GET /api/controls?page=1&page_size=50&search=",
                "GET /api/controls/{id}",
                "GET /api/w01-test/info (временный)",
            ],
        }

    # HEAD поддерживается явно: иначе монтированная статика перехватывает HEAD и возвращает 404,
    # что ломает проверки живости внешним мониторингом
    @app.api_route("/api/health", methods=["GET", "HEAD"], response_model=HealthOut,
                   summary="Живость стенда и БД")
    def health() -> HealthOut:
        try:
            with db.connection(cfg.dsn) as conn:
                ok = db.ping(conn)
                version = db.server_version(conn) if ok else None
        except psycopg.Error:
            logger.exception("База данных недоступна")
            return HealthOut(status="degraded", database="unavailable")
        return HealthOut(
            status="ok" if ok else "degraded",
            database="ok" if ok else "unavailable",
            postgres_version=version,
            app_version=APP_VERSION,
            stand=STAND_NOTE,
        )

    @app.get("/api/meta/summary", response_model=SummaryOut, summary="Счётчики для шапки")
    def meta_summary() -> SummaryOut:
        with db.connection(cfg.dsn) as conn:
            return SummaryOut(**repo.summary(conn))

    @app.get("/api/controls", response_model=ControlsPage, summary="Постраничный список")
    def controls_list(
        page: int = Query(1, ge=1, description="номер страницы, начиная с 1"),
        page_size: int = Query(50, ge=1, le=200, description="строк на странице; интерфейс использует 50"),
        search: str | None = Query(None, max_length=200, description="поиск по номеру, инициатору, содержанию, ФИО"),
        include_archived: bool = Query(False, description="включать архивные записи"),
    ) -> ControlsPage:
        term = search.strip() if search else None
        with db.connection(cfg.dsn) as conn:
            total = repo.count_controls(conn, search=term, include_archived=include_archived)
            rows = repo.list_controls(
                conn, page=page, page_size=page_size, search=term, include_archived=include_archived
            )
        pages = (total + page_size - 1) // page_size if total else 0
        return ControlsPage(
            items=[ControlListItem(**row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
            pages=pages,
            search=term or None,
            include_archived=include_archived,
        )

    @app.get("/api/controls/{control_id}", response_model=ControlCard, summary="Карточка (только чтение)")
    def control_card(control_id: str) -> ControlCard:
        try:
            uuid.UUID(control_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Идентификатор записи должен быть UUID.") from exc
        with db.connection(cfg.dsn) as conn:
            row = repo.get_control(conn, control_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Запись не найдена.")
        attachments = [
            AttachmentOut(
                **item,
                download_url=(
                    f"/api/w01-test/uploads/{item['id']}/content" if cfg.enable_test_endpoints else None
                ),
            )
            for item in row.pop("attachments")
        ]
        tasks = [TaskOut(**item) for item in row.pop("tasks")]
        return ControlCard(**row, tasks=tasks, attachments=attachments)

    if cfg.enable_test_endpoints:
        app.include_router(build_test_router(cfg))

    if cfg.frontend_dist and cfg.frontend_dist.is_dir():
        # тот же origin: статика production-сборки монтируется после API-маршрутов
        app.mount("/", StaticFiles(directory=str(cfg.frontend_dist), html=True), name="frontend")
    else:
        logger.warning("Каталог frontend/dist не найден — отдаётся только API (сборка: npm run build)")

    return app


app = create_app()

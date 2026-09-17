"""Pydantic-модели ответов стенда W01 (только чтение + стендовые загрузки)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ControlListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    incoming_number: str
    receive_date: date | None = None
    due_date: date | None = None
    done: bool = False
    archived: bool = False
    control_type: str = ""
    initiator: str = ""
    executor: str = ""
    controller: str = ""
    department: str = ""
    priority: str = "обычный"
    tasks_total: int = 0
    tasks_done: int = 0
    attachments_total: int = 0


class ControlsPage(BaseModel):
    items: list[ControlListItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)
    search: str | None = None
    include_archived: bool = False


class TaskOut(BaseModel):
    id: str
    position: int
    text: str
    due_date: date | None = None
    done: bool = False


class AttachmentOut(BaseModel):
    id: str
    control_id: str | None = None
    rel_path: str
    file_name: str
    size_bytes: int
    sha256: str
    content_type: str = "application/octet-stream"
    created_at: datetime | None = None
    download_url: str | None = None


class ControlCard(BaseModel):
    id: str
    incoming_number: str
    receive_date: date | None = None
    due_date: date | None = None
    done: bool = False
    archived: bool = False
    control_type: str = ""
    initiator: str = ""
    content: str = ""
    executor: str = ""
    controller: str = ""
    department: str = ""
    priority: str = "обычный"
    note: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    tasks: list[TaskOut] = Field(default_factory=list)
    attachments: list[AttachmentOut] = Field(default_factory=list)


class SummaryOut(BaseModel):
    total: int
    active: int
    archived: int
    done: int
    overdue: int
    with_attachments: int


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"] = "ok"
    database: Literal["ok", "unavailable"] = "unavailable"
    postgres_version: str | None = None
    app_version: str = "0.1.0-w01"
    stand: str = "W01 (синтетические данные, не рабочая система)"


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorOut(BaseModel):
    error: ErrorDetail

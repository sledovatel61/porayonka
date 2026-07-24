# core/models.py
# Модели данных: Department (отдел) и Status (статус)

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional

import flet as ft


class Status(Enum):
    """
    Три состояния статуса отдела:
    EMPTY       — не получено
    RECEIVED    — получено
    IN_PROGRESS — в работе
    """
    EMPTY = "empty"
    RECEIVED = "received"
    IN_PROGRESS = "in_progress"


@dataclass
class Department:
    """
    Следственный отдел.
    Атрибуты:
        id         — порядковый номер (1-29)
        name       — полное название отдела
        status     — текущий статус (Status enum)
        updated_at — дата/время последнего изменения статуса
        is_ovd     — True для ОВД-1 и ОВД-2 (без номера, курсив)
    """
    id: int
    name: str
    status: Status = Status.EMPTY
    updated_at: Optional[datetime] = None
    is_ovd: bool = False

    def toggle_status(self) -> Status:
        """
        Циклическое переключение статуса:
        EMPTY → RECEIVED → IN_PROGRESS → EMPTY → ...
        При переключении обновляет updated_at.
        """
        cycle = [Status.EMPTY, Status.RECEIVED, Status.IN_PROGRESS]
        current_idx = cycle.index(self.status)
        self.status = cycle[(current_idx + 1) % len(cycle)]
        self.updated_at = datetime.now()
        return self.status

    def get_status_label(self) -> str:
        """Текстовое описание статуса для интерфейса"""
        labels = {
            Status.EMPTY: "—",
            Status.RECEIVED: "Получено",
            Status.IN_PROGRESS: "В работе",
        }
        return labels[self.status]

    def get_status_icon(self) -> str:
        """Иконка статуса"""
        icons = {
            Status.EMPTY: ft.icons.RADIO_BUTTON_UNCHECKED,
            Status.RECEIVED: ft.icons.CHECK,
            Status.IN_PROGRESS: ft.icons.REFRESH,
        }
        return icons[self.status]

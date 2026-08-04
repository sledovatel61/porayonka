# core/controls_models.py
# Модели данных для вкладки «Контроли»
# Формат дат в моделях — строка ISO «YYYY-MM-DD» для простоты сериализации.
import uuid
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional

ONE_TIME = "once"        # разовый
PERIODIC = "periodic"    # постоянный / периодический

# Коды статуса срока
OVERDUE = "overdue"      # 🔴 просрочено
TODAY = "today"          # 🟡 сегодня
SOON = "soon"            # 🟠 скоро
IN_PROGRESS = "in_progress"  # 🟢 в работе
DONE = "done"            # ⚪ исполнено
NO_DATE = "none"         # срока нет


def parse_date(s: Optional[str]) -> Optional[date]:
    """Безопасно распарсить ISO-строку даты в date."""
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def format_date(d: Optional[date]) -> Optional[str]:
    return d.isoformat() if d else None


@dataclass
class ControlTask:
    """Пункт задания внутри контроля (п.1, п.2, ...)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""                       # название / описание пункта
    assignees: List[str] = field(default_factory=list)  # ответственные (ФИО)
    due_date: Optional[str] = None        # срок исполнения (ISO)
    is_done: bool = False
    done_date: Optional[str] = None
    comment: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "assignees": list(self.assignees),
            "due_date": self.due_date,
            "is_done": self.is_done,
            "done_date": self.done_date,
            "comment": self.comment,
        }

    @staticmethod
    def from_dict(d: dict) -> "ControlTask":
        return ControlTask(
            id=d.get("id") or str(uuid.uuid4()),
            title=d.get("title", ""),
            assignees=list(d.get("assignees", []) or []),
            due_date=d.get("due_date"),
            is_done=d.get("is_done", False),
            done_date=d.get("done_date"),
            comment=d.get("comment", ""),
        )


@dataclass
class Control:
    """Один контроль / распоряжение."""
    id: str
    incoming_number: str = ""             # вх. № ВХСОП (обязательное)
    receive_date: Optional[str] = None    # дата поступления (ISO, обязательная)
    initiator: str = ""                   # СУ, ГУК СК, ГУК ЮФО, СК РФ и т.п.
    content: str = ""                     # содержание (краткое/полное)
    executors: List[str] = field(default_factory=list)   # исполнители (ФИО)
    controller: str = ""                  # за кем контроль
    control_type: str = ONE_TIME
    period_days: int = 7                  # для периодического: интервал в днях
    due_date: Optional[str] = None        # следующая дата исполнения (ISO)
    done: bool = False
    done_date: Optional[str] = None       # исполнено + дата
    comment: str = ""
    tasks: List[ControlTask] = field(default_factory=list)  # пункты задания
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "incoming_number": self.incoming_number,
            "receive_date": self.receive_date,
            "initiator": self.initiator,
            "content": self.content,
            "executors": list(self.executors),
            "controller": self.controller,
            "control_type": self.control_type,
            "period_days": self.period_days,
            "due_date": self.due_date,
            "done": self.done,
            "done_date": self.done_date,
            "comment": self.comment,
            "tasks": [t.to_dict() for t in self.tasks],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(d: dict) -> "Control":
        return Control(
            id=d.get("id") or str(uuid.uuid4()),
            incoming_number=d.get("incoming_number", ""),
            receive_date=d.get("receive_date"),
            initiator=d.get("initiator", ""),
            content=d.get("content", ""),
            executors=list(d.get("executors", []) or []),
            controller=d.get("controller", ""),
            control_type=d.get("control_type", ONE_TIME),
            period_days=d.get("period_days", 7),
            due_date=d.get("due_date"),
            done=d.get("done", False),
            done_date=d.get("done_date"),
            comment=d.get("comment", ""),
            tasks=[ControlTask.from_dict(t) for t in d.get("tasks", []) or []],
            created_at=d.get("created_at") or datetime.now().isoformat(),
            updated_at=d.get("updated_at") or datetime.now().isoformat(),
        )


def effective_due_date(control: Control) -> Optional[date]:
    """Эффективная следующая дата исполнения.

    Если задана собственная due_date — берём её. Иначе считаем минимальную
    дату неисполненных пунктов (задача из мегапромпта).
    """
    dd = parse_date(control.due_date)
    if dd is not None:
        return dd
    dates = [parse_date(t.due_date) for t in control.tasks if not t.is_done]
    dates = [d for d in dates if d is not None]
    return min(dates) if dates else None


def deadline_status(control: Control, soon_days: int = 3) -> str:
    """Вычислить статус срока контроля."""
    if control.done:
        return DONE
    dd = effective_due_date(control)
    if dd is None:
        return NO_DATE
    today = date.today()
    if dd < today:
        return OVERDUE
    if dd == today:
        return TODAY
    if (dd - today).days <= max(0, soon_days):
        return SOON
    return IN_PROGRESS


STATUS_LABELS = {
    OVERDUE: "Просрочено",
    TODAY: "Сегодня",
    SOON: "Скоро",
    IN_PROGRESS: "В работе",
    DONE: "Исполнено",
    NO_DATE: "Без срока",
}

STATUS_COLORS = {
    OVERDUE: "#ef4444",    # красный
    TODAY: "#f59e0b",      # жёлтый/оранжевый
    SOON: "#fb923c",       # оранжевый
    IN_PROGRESS: "#22c55e",# зелёный
    DONE: "#64748b",       # серый
    NO_DATE: "#94a3b8",    # серый
}

STATUS_ICONS = {
    OVERDUE: "EVENT_BUSY",
    TODAY: "NOTIFICATIONS_ACTIVE",
    SOON: "HOURGLASS_BOTTOM",
    IN_PROGRESS: "HOURGLASS_TOP",
    DONE: "CHECK_CIRCLE",
    NO_DATE: "REMOVE",
}

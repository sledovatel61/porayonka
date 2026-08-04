# core/controls_models.py
# Модели данных для вкладки «Контроли» (schema v2)
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
COMPLETED = "completed"  # постоянный, конечная дата истекла («Завершён»)

# Причины архивации
ARCHIVE_DONE = "done"
ARCHIVE_DELETED = "deleted"


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


def short_name(full: str) -> str:
    """Сокращённое ФИО: «Семисенко Иван Юрьевич» → «Семисенко И.Ю.».

    Устойчив к неполным строкам: «Семисенко» → «Семисенко»,
    пустая строка → как есть.
    """
    parts = [p for p in (full or "").split() if p]
    if not parts:
        return full or ""
    surname = parts[0]
    initials = "".join(p[0].upper() + "." for p in parts[1:] if p)
    if not initials:
        return surname
    return f"{surname} {initials}"


def short_names(names: List[str]) -> List[str]:
    return [short_name(n) for n in names]


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
class ControlMilestone:
    """Промежуточная контрольная точка постоянного контроля."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: Optional[str] = None
    note: str = ""
    is_done: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date,
            "note": self.note,
            "is_done": self.is_done,
        }

    @staticmethod
    def from_dict(d: dict) -> "ControlMilestone":
        return ControlMilestone(
            id=d.get("id") or str(uuid.uuid4()),
            date=d.get("date"),
            note=d.get("note", ""),
            is_done=d.get("is_done", False),
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
    end_date: Optional[str] = None        # конечная дата (для постоянных, schema v2)
    done: bool = False
    done_date: Optional[str] = None       # исполнено + дата
    comment: str = ""
    tasks: List[ControlTask] = field(default_factory=list)          # пункты задания
    milestones: List[ControlMilestone] = field(default_factory=list)  # промежуточные точки (v2)
    attachments: List[str] = field(default_factory=list)            # относительные пути (v2)
    archived: bool = False                # в архиве (v2)
    archived_at: Optional[str] = None     # дата архивации (v2)
    archive_reason: str = ""              # "done" | "deleted" (v2)
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
            "end_date": self.end_date,
            "done": self.done,
            "done_date": self.done_date,
            "comment": self.comment,
            "tasks": [t.to_dict() for t in self.tasks],
            "milestones": [m.to_dict() for m in self.milestones],
            "attachments": list(self.attachments),
            "archived": self.archived,
            "archived_at": self.archived_at,
            "archive_reason": self.archive_reason,
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
            end_date=d.get("end_date"),
            done=d.get("done", False),
            done_date=d.get("done_date"),
            comment=d.get("comment", ""),
            tasks=[ControlTask.from_dict(t) for t in d.get("tasks", []) or []],
            milestones=[ControlMilestone.from_dict(m) for m in d.get("milestones", []) or []],
            attachments=list(d.get("attachments", []) or []),
            archived=d.get("archived", False),
            archived_at=d.get("archived_at"),
            archive_reason=d.get("archive_reason", ""),
            created_at=d.get("created_at") or datetime.now().isoformat(),
            updated_at=d.get("updated_at") or datetime.now().isoformat(),
        )


def effective_due_date(control: Control) -> Optional[date]:
    """Эффективная следующая дата исполнения.

    Минимум из:
    - собственной `due_date`;
    - дат неисполненных пунктов (`tasks`);
    - ближайшей неисполненной промежуточной точки (`milestones`).
    """
    dd = parse_date(control.due_date)
    task_dates = [parse_date(t.due_date) for t in control.tasks if not t.is_done]
    task_dates = [d for d in task_dates if d is not None]
    mile_dates = [parse_date(m.date) for m in control.milestones if not m.is_done]
    mile_dates = [d for d in mile_dates if d is not None]
    candidates = [d for d in (dd, *task_dates, *mile_dates) if d is not None]
    return min(candidates) if candidates else None


def next_milestone(control: Control) -> Optional[ControlMilestone]:
    """Ближайшая неисполненная промежуточная точка."""
    pending = [m for m in control.milestones if not m.is_done and parse_date(m.date)]
    pending.sort(key=lambda m: parse_date(m.date))
    return pending[0] if pending else None


def deadline_status(control: Control, soon_days: int = 3) -> str:
    """Вычислить статус срока контроля."""
    if control.done:
        return DONE
    today = date.today()
    if control.control_type == PERIODIC:
        ed = parse_date(control.end_date)
        if ed is not None and ed < today:
            return COMPLETED
    dd = effective_due_date(control)
    if dd is None:
        return NO_DATE
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
    COMPLETED: "Завершён",
    NO_DATE: "Без срока",
}

STATUS_COLORS = {
    OVERDUE: "#ef4444",    # красный
    TODAY: "#f59e0b",      # жёлтый/оранжевый
    SOON: "#fb923c",       # оранжевый
    IN_PROGRESS: "#22c55e",# зелёный
    DONE: "#64748b",       # серый
    COMPLETED: "#3b82f6",  # синий
    NO_DATE: "#94a3b8",    # серый
}

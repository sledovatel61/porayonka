# core/controls_models.py
# Модели данных для вкладки «Контроли» (schema v2)
# Формат дат в моделях — строка ISO «YYYY-MM-DD» для простоты сериализации.
import difflib
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional, Tuple

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

    Идемпотентен: уже-сокращённое «Потемкин С.А.» → «Потемкин С.А.»
    (токены с точкой считаются готовыми инициалами и не режутся).
    Устойчив к неполным строкам: «Семисенко» → «Семисенко»,
    пустая строка → как есть.
    """
    parts = [p for p in (full or "").split() if p]
    if not parts:
        return full or ""
    surname = parts[0]
    initials = ""
    for p in parts[1:]:
        if "." in p:
            initials += p            # готовый инициал(ы): «С.», «С.А.»
        else:
            initials += p[0].upper() + "."
    if not initials:
        return surname
    return f"{surname} {initials}"


def short_names(names: List[str]) -> List[str]:
    return [short_name(n) for n in names]


def _word_similarity(a: str, b: str) -> float:
    """Быстрое приближение степени похожести слов (0..1)."""
    a = a.casefold()
    b = b.casefold()
    if not a or not b:
        return 0.0
    # расстояние Левенштейна, оптимизированное для коротких строк
    if abs(len(a) - len(b)) > max(len(a), len(b)) // 2:
        return 0.0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(cur[-1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = cur
    dist = prev[-1]
    return 1.0 - dist / max(len(a), len(b))


def name_matches(canonical_name: str, raw: str) -> bool:
    """True, если `raw` (строка из данных, возможно кривая) относится к человеку
    `canonical_name` (полное ФИО). Правила:
    - точное совпадение строк (после strip) — True;
    - фамилия (первое слово canonical) встречается в raw как подстрока
      (case-insensitive) — True;
    - фамилия похожа на одно из слов raw с коэффициентом >= 0.80
      (ловим опечатки вроде «Семисеннко», «Гайнутдинов» с лишней буквой);
    - иначе False. Фамилия короче 3 символов не матчится (защита от мусора).
    """
    canon = (canonical_name or "").strip()
    raw_s = (raw or "").strip()
    if not canon or not raw_s:
        return False
    if canon.casefold() == raw_s.casefold():
        return True
    surname = canon.split()[0] if canon.split() else ""
    if len(surname) < 3:
        return False
    if surname.casefold() in raw_s.casefold():
        return True
    # Fuzzy: сравниваем фамилию с каждым словом raw, убирая пунктуацию
    for w in raw_s.replace(",", " ").replace(";", " ").split():
        w = w.strip(".-")
        if len(w) >= 3 and _word_similarity(surname, w) >= 0.80:
            return True
    return False


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


# ────────────────────────────────────────────────────────────────────────────
# Раунд 20 (задача 3): разбор ПУНКТОВ внутри «Содержания» при импорте из Excel.
# Первоисточник («Контроли ОКРИМ.xlsx», колонка «Содержание (если один из
# нескольких пунктов - указать пункт)») хранит пункты текстом, напр. строка 41:
#   «Распоряжение 2/216-р от 15.01.2026 Чашин Э.А. п.3 к 05.05.2026, п. 5 к
#    05.09.2026, п. 7 к 05.10.2026, Миронович Д.В. п. 9.3 к 20.05.2026»
# ФИО владеет цепочкой пунктов до следующего ФИО. Пункт без «к <дата>» задачей
# НЕ считается (иначе «ОПК п. 1» и подобные порождали бы пустые пункты); если
# ни одного пункта со сроком нет — содержание возвращается без изменений.
# ────────────────────────────────────────────────────────────────────────────

# «Фамилия И.О.»; инициалы с точками и опциональными пробелами, фамилия
# может быть двойной (через дефис).
_PERSON_FULL_RE = r"[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?\s+[А-ЯЁ]\s*\.\s*[А-ЯЁ]\s*\.?"

_CONTENT_TOKEN_RE = re.compile(
    r"(?P<name>" + _PERSON_FULL_RE + r")"
    r"|(?P<pmark>[пП]\s*\.\s*(?P<num>\d+(?:\s*\.\s*\d+)*)"
    r"(?:\s*к\s*(?P<date>\d{1,2}\s*\.\s*\d{1,2}\s*\.\s*\d{2,4}))?)"
)


def _norm_person_name(raw: str) -> str:
    """Привести «Чашин Э. А.»/«Чашин Э А» к каноническому «Чашин Э.А.»."""
    s = " ".join((raw or "").split())
    s = re.sub(r"([А-ЯЁ])\s*\.\s*([А-ЯЁ])\s*\.", r"\1.\2.", s)
    s = re.sub(r"([А-ЯЁ])\s*\.", r"\1.", s)
    return s


def _content_item_date(raw: str) -> Optional[str]:
    """«05.09.2026»/«05.09.26» (с пробелами вокруг точек) → ISO или None."""
    dstr = re.sub(r"\s+", "", raw or "")
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(dstr, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_content_tasks(content: str) -> Tuple[str, List[ControlTask]]:
    """Выделить из «Содержания» пункты «п. N к DD.MM.YYYY» с владельцами-ФИО.

    Возвращает (очищенное содержание, список ControlTask). Если пунктов со
    сроками нет — исходное содержание без изменений и пустой список.
    Очищенное содержание = текст до начала региона пунктов + текст после
    региона (напр. префикс «Распоряжение 2/216-р от 15.01.2026»).
    """
    text = (content or "").strip()
    if not text:
        return content, []

    tasks: List[ControlTask] = []
    consumed_spans: List[Tuple[int, int]] = []
    cur_name: Optional[str] = None
    cur_name_span: Optional[Tuple[int, int]] = None

    for m in _CONTENT_TOKEN_RE.finditer(text):
        if m.group("name"):
            cur_name = _norm_person_name(m.group("name"))
            cur_name_span = (m.start("name"), m.end("name"))
            continue
        iso = _content_item_date(m.group("date") or "")
        if iso is None:
            continue  # пункт без срока — игнорируем (не трогаем содержание)
        num = re.sub(r"\s*\.\s*", ".", m.group("num"))
        assignees = [cur_name] if cur_name else []
        if cur_name and cur_name_span:
            consumed_spans.append(cur_name_span)
        consumed_spans.append((m.start("pmark"), m.end()))
        tasks.append(ControlTask(title=f"п. {num}", assignees=assignees, due_date=iso))

    if not tasks:
        return content, []

    region_start = min(s for s, _ in consumed_spans)
    region_end = max(e for _, e in consumed_spans)
    clean = (text[:region_start] + " " + text[region_end:]).strip(" ,;—–-")
    clean = re.sub(r"\s{2,}", " ", clean).strip()
    if not clean:
        clean = text  # страховка: пустое содержание хуже исходного
    return clean, tasks


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

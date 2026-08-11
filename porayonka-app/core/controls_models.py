# core/controls_models.py
# Модели данных для вкладки «Контроли» (schema v2)
# Формат дат в моделях — строка ISO «YYYY-MM-DD» для простоты сериализации.
import difflib
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

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

# «Голая фамилия» (без инициалов) — встречается в inline-формате
# («п. 2 - Миронович 01.05.2026»).
_PERSON_BARE_RE = re.compile(r"^[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?$")

_CONTENT_TOKEN_RE = re.compile(
    r"(?P<name>" + _PERSON_FULL_RE + r")"
    r"|(?P<pmark>[пП]\s*\.\s*(?P<num>\d+(?:\s*\.\s*\d+)*)"
    r"(?:\s*к\s*(?P<date>\d{1,2}\s*\.\s*\d{1,2}\s*\.\s*\d{2,4}))?)"
)

# Раунд 21 (задача 3): маркер пункта. Номер — «9», «9.3», «5б», «5,6»
# (произвольная цифро-точечная цепочка + опциональная СЛИТНАЯ буква —
# буква через пробел запрещена, иначе «п.3 к 05.05.2026» съедало «к»,
# а «п. 6 Семисенко» — «С» фамилии). Отрицательный просмотр — не съедать
# начало даты («п. 8 - 30.07.2026»).
_ITEM_MARK_RE = re.compile(
    r"[пП]\s*\.\s*(?P<num>\d+(?:\s*[.,]\s*\d+)*[а-яА-ЯёЁa-zA-Z]?)(?![\d.])"
)

# Дата DD.MM.YYYY / DD.MM.YY (с пробелами вокруг точек, опц. «г.» хвостом).
_CONTENT_DATE_RE = re.compile(
    r"(?P<date>\d{1,2}\s*\.\s*\d{1,2}\s*\.\s*\d{2,4})\s*г?\.?"
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


def _parse_item_persons(pre: str) -> List[str]:
    """Извлечь ФИО/фамилии из текста между маркером пункта и датой.

    Знает два формата: полные «Фамилия И.О.» и «голые» фамилии («Миронович»),
    перечисленные через запятую/«и» («Семисенко, Чащин - 16.02.2026»).
    Служебные токены («к», тире, мусор) отбрасываются.
    """
    out: List[str] = []
    for chunk in re.split(r"[,;]|\s+и\s+", pre or ""):
        tok = chunk.strip().strip("-–—:;.кК").strip()
        if not tok:
            continue
        m = re.search(_PERSON_FULL_RE, tok)
        if m:
            out.append(_norm_person_name(m.group(0)))
        elif _PERSON_BARE_RE.match(tok):
            out.append(tok)
    return out


def parse_content_tasks(content: str) -> Tuple[str, List[ControlTask]]:
    """Выделить из «Содержания» пункты со сроками в ControlTask.

    Поддерживаются ОБА формата записи в исходной таблице (раунд 21, задача 3):
      1) цепочка: «... Чашин Э.А. п.3 к 05.05.2026, п. 5 к 05.09.2026,
         Миронович Д.В. п. 9.3 к 20.05.2026» — ФИО владеет цепочкой пунктов
         до следующего ФИО («к <дата>» обязательна);
      2) inline: «... п. 2 - Миронович 01.05.2026, п. 6 Семисенко, Чащин -
         16.02.2026, п. 8 - 30.07.2026» — исполнители (в т.ч. голыми
         фамилиями) внутри пункта, «к» необязательна; пункт может быть без
         исполнителя (сохраняется со сроком, без ответственного).
    Пункт БЕЗ даты в своём сегменте задачей не считается вовсе (иначе
    «ОПК п. 1» и подобные порождали бы пустые пункты); если ни одного пункта
    со сроком нет — содержание возвращается без изменений.
    Возвращает (очищенное содержание, список ControlTask): очищенное
    содержание = текст до начала региона пунктов + текст после региона.
    """
    text = (content or "").strip()
    if not text:
        return content, []

    marks = list(_ITEM_MARK_RE.finditer(text))
    if not marks:
        return content, []

    tasks: List[ControlTask] = []
    consumed_spans: List[Tuple[int, int]] = []
    chain_name: Optional[str] = None
    chain_span: Optional[Tuple[int, int]] = None
    prev_date_end: Optional[int] = None

    for i, m in enumerate(marks):
        seg_start = m.end()
        seg_end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        seg = text[seg_start:seg_end]
        dm = _CONTENT_DATE_RE.search(seg)
        if dm is None:
            continue  # пункт без срока — игнорируем (не трогаем содержание)
        iso = _content_item_date(dm.group("date"))
        if iso is None:
            continue
        num = re.sub(r"\s+", "", m.group("num")).replace(",", ".")
        # inline-исполнители — текст сегмента до даты; «голые» фамилии тоже
        names = _parse_item_persons(seg[:dm.start()])
        if not names:
            # цепочка: владелец — ближайшее ФИО ПОЛНОЙ формы в зазоре между
            # предыдущей датой и этим маркером; «голая» фамилия владельцем
            # цепочки не становится (она — inline-исполнитель своего пункта).
            gap_start = prev_date_end if prev_date_end is not None else 0
            gap = text[gap_start:m.start()]
            fulls = list(re.finditer(_PERSON_FULL_RE, gap))
            if fulls:
                last = fulls[-1]
                chain_name = _norm_person_name(last.group(0))
                chain_span = (gap_start + last.start(), gap_start + last.end())
            if chain_name:
                names = [chain_name]
                if chain_span:
                    consumed_spans.append(chain_span)
        consumed_spans.append((m.start(), seg_start + dm.end()))
        prev_date_end = seg_start + dm.end()
        tasks.append(ControlTask(title=f"п. {num}", assignees=names, due_date=iso))

    if not tasks:
        return content, []

    region_start = min(s for s, _ in consumed_spans)
    region_end = max(e for _, e in consumed_spans)
    clean = (text[:region_start] + " " + text[region_end:]).strip(" ,;—–-")
    clean = re.sub(r"\s{2,}", " ", clean).strip()
    if not clean:
        clean = text  # страховка: пустое содержание хуже исходного
    return clean, tasks


def resolve_task_assignees(tasks: List[ControlTask], known_names: List[str]) -> None:
    """Раунд 21 (задача 3): привязать «голые фамилии» пунктов к известным ФИО.

    Inline-формат содержания даёт фамилии без инициалов («Миронович»). Если
    среди известных имён (колонка «Исполнитель» + справочник людей) ровно одно
    с такой фамилией — подставляем его («Миронович Д.В.»), чтобы в карточке и в
    списке исполнителей не плодились дубли «Миронович» / «Миронович Д.В.».
    Формы с инициалами и неоднозначные совпадения не трогаем.
    """
    by_surname: Dict[str, set] = {}
    for kn in known_names or []:
        parts = (kn or "").split()
        if not parts:
            continue
        by_surname.setdefault(parts[0].casefold(), set()).add(kn)
    for t in tasks or []:
        resolved: List[str] = []
        for a in t.assignees:
            parts = (a or "").split()
            if len(parts) == 1 and _PERSON_BARE_RE.match(parts[0]):
                cands = by_surname.get(parts[0].casefold())
                if cands and len(cands) == 1:
                    resolved.append(next(iter(cands)))
                    continue
            resolved.append(a)
        t.assignees = resolved


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

# core/controls_exporter.py
# Экспорт/импорт контролей в Excel:
#  - «как в таблице» — формат пользователя (одна строка = один контроль);
#  - «полный» — то же + скрытый лист для безупречного round-trip.
import json
import re
from datetime import date, datetime
from typing import List, Optional, Tuple

from .controls_models import (
    Control, ControlTask, ControlMilestone, ONE_TIME, PERIODIC,
    effective_due_date, deadline_status, parse_date, short_name,
    parse_content_tasks, resolve_task_assignees,
    OVERDUE, TODAY, SOON, COMPLETED,
    # Раунд 29 (задача 5): разбор «склеек» ФИО при импорте.
    _PERSON_FULL_RE, _norm_person_name,
)

# Заголовки в формате пользователя — 1:1 с эталоном «Контроли ОКРИМ.xlsx»
# (строка 2 листа «текущее»; строка 1 — объединённый заголовок «КОНТРОЛИ ОТДЕЛА
# КРИМИНАЛИСТИКИ»). Импорт устойчив к расположению шапки (ищет строку с заголовками).
# Раунд 18 (задача 3): хвостовые/множественные пробелы убраны — заголовки
# приведены к ТОЧНОМУ виду исходной таблицы; приложение берёт их же (см.
# _rebuild_header в ui/controls/controls_tab.py) — единый источник истины.
TABLE_HEADERS = [
    "№",
    "вх. № ВХСОП-____-__",
    "Дата поступления",
    "Инициатор",
    "Содержание (если один из нескольких пунктов - указать пункт)",
    "Исполнитель (ФИО)",
    # Раунд 21 (задача 6): личные фамилии из подзаголовка убраны — просто
    # «За кем контроль» (запрос пользователя; импорт матчит колонку по
    # подстроке «контроль», поэтому старые файлы читаются как раньше).
    "За кем контроль",
    "Разовый / постоянный",
    "Следующая дата исполнения",
    "Исполнено + дата",
]

# Общий заголовок (строка 1, объединённая A1:J1) — как в эталоне
TABLE_TITLE = "КОНТРОЛИ ОТДЕЛА КРИМИНАЛИСТИКИ"

# Ширины колонок — как в эталоне (лист «текущее»)
TABLE_WIDTHS = [10.3, 34.3, 25.6, 19.7, 72.4, 38.1, 36.6, 64.0, 25.1, 30.3]

# Цвета эталона
ETALON_GREEN = "FF00B050"    # заголовок A1:J1 и «Исполнено + дата»
ETALON_YELLOW = "FFFFFF00"   # «Следующая дата исполнения» при наступившем/близком сроке

# Имя скрытого листа для полного round-trip
FULL_SHEET = "_controls_full"


# ────────────────────────────────────────────────
# УТИЛИТЫ ФОРМАТА
# ────────────────────────────────────────────────

def _fmt(iso: Optional[str]) -> str:
    d = parse_date(iso)
    return d.strftime("%d.%m.%Y") if d else ""


def _months_plural(n: int) -> str:
    """Русская плюрализация «месяц»: 1 месяц, 2-4 месяца, 5+ месяцев."""
    if n % 10 == 1 and n % 100 != 11:
        return "месяц"
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return "месяца"
    return "месяцев"


def _period_label(days: int) -> str:
    """Человекочитаемая периодичность: «еженедельно», «каждые 3 месяца»..."""
    # Раунд 21 (задача 7): полугодовая периодичность (182 дня) — «каждые полгода».
    labels = {1: "ежедневно", 7: "еженедельно", 30: "ежемесячно",
              91: "ежеквартально", 182: "каждые полгода", 365: "ежегодно"}
    if days in labels:
        return labels[days]
    if days > 0 and days % 30 == 0:
        n = days // 30
        return f"каждые {n} {_months_plural(n)}"
    if days > 0 and days % 7 == 0:
        n = days // 7
        return f"каждые {n} нед." if n != 1 else "еженедельно"
    return f"каждые {days} дней"


def control_type_text(ctl: Control) -> str:
    """Раунд 18 (задача 2): текст колонки «Разовый / постоянный» — как в исходной
    таблице Excel:
    - разовый контроль → КОНЕЧНАЯ дата исполнения (end_date, fallback due_date),
      а не слово «разовый» («разовый» — только если дат нет вовсе);
    - периодический → «<end_date> далее <периодичность>», если задана конечная
      дата, иначе просто периодичность («еженедельно», «каждые 3 месяца»...).
    """
    if ctl.control_type != PERIODIC:
        return _fmt(ctl.end_date) or _fmt(ctl.due_date) or "разовый"
    label = _period_label(ctl.period_days)
    end = _fmt(ctl.end_date)
    return f"{end} далее {label}" if end else label


def _type_text(ctl: Control) -> str:
    """Человекочитаемый текст типа для колонки «Разовый/постоянный».

    Раунд 18: делегирует control_type_text() (с конечной датой)."""
    return control_type_text(ctl)


def _done_text(ctl: Control) -> str:
    if ctl.done and ctl.done_date:
        return _fmt(ctl.done_date)
    if ctl.done:
        return "исполнено"
    return ""


# ────────────────────────────────────────────────
# ЭКСПОРТ
# ────────────────────────────────────────────────

class ControlsExcelExporter:
    """Экспорт контролей в .xlsx."""

    def export(self, controls: List[Control], filepath: str, soon_days: int = 3,
               full: bool = False) -> None:
        """Экспорт.

        :param full: True → «полный» режим (добавляет скрытый лист для round-trip)
        """
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Color, Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            raise ImportError("openpyxl не установлена. pip install openpyxl")

        wb = Workbook()
        ws = wb.active
        ws.title = "Контроли"

        # Стили — 1:1 с эталоном «Контроли ОКРИМ.xlsx» (лист «текущее»)
        title_font = Font(name="Times New Roman", size=36)
        title_fill = PatternFill("solid", fgColor=ETALON_GREEN)
        # Шапка: theme dk1 (чёрный) с тинтом −25% — как в оригинале
        header_fill = PatternFill("solid", fgColor=Color(theme=0, tint=-0.249977111117893))
        header_font = Font(name="Times New Roman", size=14)
        data_font = Font(name="Times New Roman", size=14)
        yellow_fill = PatternFill("solid", fgColor=ETALON_YELLOW)
        green_fill = PatternFill("solid", fgColor=ETALON_GREEN)
        thin = Side(style="thin")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        center = Alignment(horizontal="center", vertical="center")
        center_wrap = Alignment(horizontal="center", vertical="center", wrap_text=True)
        date_fmt = "DD.MM.YYYY"

        # Строка 1 — объединённый заголовок
        ws.merge_cells(start_row=1, start_column=1, end_row=1,
                       end_column=len(TABLE_HEADERS))
        tc = ws.cell(row=1, column=1, value=TABLE_TITLE)
        tc.font = title_font
        tc.fill = title_fill
        tc.alignment = center
        ws.row_dimensions[1].height = 45.75

        # Строка 2 — шапка колонок
        for col_i, (h, w) in enumerate(zip(TABLE_HEADERS, TABLE_WIDTHS), 1):
            c = ws.cell(row=2, column=col_i, value=h)
            c.fill = header_fill
            c.font = header_font
            c.alignment = center_wrap if col_i in (5, 7, 8, 9) else center
            c.border = border
            ws.column_dimensions[get_column_letter(col_i)].width = w
        ws.row_dimensions[2].height = 56.25

        active = [c for c in controls if not c.archived]
        row = 3
        for idx, ctl in enumerate(active, 1):
            st = deadline_status(ctl, soon_days)
            due = effective_due_date(ctl)
            due_iso = ctl.due_date or (due.isoformat() if due else None)
            done_txt = _done_text(ctl)
            values = [
                idx,
                ctl.incoming_number or "",
                ctl.receive_date or "",          # ISO → станет датой Excel
                ctl.initiator or "",
                ctl.content or "",
                ", ".join(short_name(x) for x in ctl.executors),
                short_name(ctl.controller) if ctl.controller else "",
                _type_text(ctl),
                due_iso or "",                   # ISO → станет датой Excel
                done_txt,
            ]
            for col_i, v in enumerate(values, 1):
                c = ws.cell(row=row, column=col_i, value=v)
                c.border = border
                c.font = data_font
                c.alignment = center_wrap if col_i in (5, 7, 8) else center
            # Даты — настоящие даты Excel с форматом dd.mm.yyyy (эталон хранит serial)
            for col_i in (3, 9):
                d = parse_date(values[col_i - 1])
                if d:
                    cell = ws.cell(row=row, column=col_i)
                    cell.value = datetime(d.year, d.month, d.day)
                    cell.number_format = date_fmt
            # Жёлтая заливка «Следующая дата исполнения» при наступившем/близком сроке
            if st in (OVERDUE, TODAY, SOON):
                ws.cell(row=row, column=9).fill = yellow_fill
            # Зелёная заливка «Исполнено + дата» при исполнении
            if ctl.done:
                ws.cell(row=row, column=10).fill = green_fill

            content_lines = max(1, -(-len(ctl.content or "") // 46))
            ws.row_dimensions[row].height = max(24, content_lines * 16 + 8)
            row += 1

        # Автофильтр как в эталоне: от шапки (строка 2) до последней строки данных
        ws.auto_filter.ref = f"A2:{get_column_letter(len(TABLE_HEADERS))}{max(2, row - 1)}"
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0

        if full:
            self._write_full_sheet(wb, active)

        wb.save(filepath)
        print(f"[CONTROLS_EXCEL] [OK] File: {filepath} (full={full})")

    def _write_full_sheet(self, wb, active: List[Control]) -> None:
        """Скрытый лист с точными данными для безупречного round-trip."""
        if FULL_SHEET in wb.sheetnames:
            ws = wb[FULL_SHEET]
        else:
            ws = wb.create_sheet(FULL_SHEET)
        ws.sheet_state = "hidden"
        headers = ["id", "incoming", "control_type", "period_days",
                   "end_date", "receive_date", "due_date", "done", "done_date",
                   "initiator", "content", "controller", "executors",
                   "tasks", "milestones", "attachments", "comment",
                   "archived", "archive_reason"]
        for ci, h in enumerate(headers, 1):
            ws.cell(row=1, column=ci, value=h)
        for ri, ctl in enumerate(active, 2):
            ws.cell(row=ri, column=1, value=ctl.id)
            ws.cell(row=ri, column=2, value=ctl.incoming_number)
            ws.cell(row=ri, column=3, value=ctl.control_type)
            ws.cell(row=ri, column=4, value=ctl.period_days)
            ws.cell(row=ri, column=5, value=ctl.end_date or "")
            ws.cell(row=ri, column=6, value=ctl.receive_date or "")
            ws.cell(row=ri, column=7, value=ctl.due_date or "")
            ws.cell(row=ri, column=8, value="1" if ctl.done else "0")
            ws.cell(row=ri, column=9, value=ctl.done_date or "")
            ws.cell(row=ri, column=10, value=ctl.initiator or "")
            ws.cell(row=ri, column=11, value=ctl.content or "")
            ws.cell(row=ri, column=12, value=ctl.controller or "")
            ws.cell(row=ri, column=13, value=json.dumps(ctl.executors, ensure_ascii=False))
            ws.cell(row=ri, column=14,
                    value=json.dumps([t.to_dict() for t in ctl.tasks], ensure_ascii=False))
            ws.cell(row=ri, column=15,
                    value=json.dumps([m.to_dict() for m in ctl.milestones], ensure_ascii=False))
            ws.cell(row=ri, column=16, value=json.dumps(ctl.attachments, ensure_ascii=False))
            ws.cell(row=ri, column=17, value=ctl.comment or "")
            ws.cell(row=ri, column=18, value="1" if ctl.archived else "0")
            ws.cell(row=ri, column=19, value=ctl.archive_reason or "")


# ────────────────────────────────────────────────
# ИМПОРТ
# ────────────────────────────────────────────────

def parse_excel_date(val) -> Optional[str]:
    """Распарсить значение ячейки как дату ISO, или вернуть None."""
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, (int, float)) and val > 0:
        # Excel serial date
        try:
            d = datetime(1899, 12, 30) + __import__("datetime").timedelta(days=float(val))
            return d.strftime("%Y-%m-%d")
        except Exception:
            return None
    s = str(val).strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_periodicity(text: str) -> Tuple[str, int]:
    """Эвристика колонки «Разовый/постоянный».

    Возвращает (control_type, period_days).
    """
    t = (text or "").strip().lower()
    if not t or t in ("разовый", "рази"):
        return ONE_TIME, 0
    rules = [
        # Раунд 21 (задача 7): «каждое полугодие» / «раз в полгода» (182 дн).
        (lambda s: "полугод" in s or "полгода" in s, PERIODIC, 182),
        (lambda s: "ежегод" in s, PERIODIC, 365),
        (lambda s: "ежемес" in s, PERIODIC, 30),
        (lambda s: "ежекварт" in s, PERIODIC, 91),
        (lambda s: "еженед" in s, PERIODIC, 7),
        (lambda s: "ежедн" in s, PERIODIC, 1),
        (lambda s: "постоянн" in s, PERIODIC, 7),
    ]
    for pred, ctype, days in rules:
        if pred(t):
            return ctype, days
    m = re.search(r"раз\s+в\s+(\d+)\s*(мес|мес\.|м)", t)
    if m:
        return PERIODIC, 30 * int(m.group(1))
    m = re.search(r"каждые?\s+(\d+)\s*(мес|месяц|месяца|месяцев)", t)
    if m:
        return PERIODIC, 30 * int(m.group(1))
    m = re.search(r"каждые?\s+(\d+)\s*(дн|день|дн\.|д)", t)
    if m:
        return PERIODIC, int(m.group(1))
    return ONE_TIME, 0


# Раунд 29 (задача 5): «склеенные инициалы» — строка исходного Excel
# «Потемкин С.А., Семисенко И.Ю.» после импорта отображалась как
# «Потемкин С.А.С.И.Ю.» (short_name сшивал вторую фамилию в инициалы первой —
# ровно когда ФИО приходили ОДНИМ элементом: разделитель в ячейке не был
# обычной запятой/;/переносом, либо его не было вообще — просто пробел).
# Теперь: 1) не-ASCII «запятые» (‚ ، ، · • | /) заранее приводятся к
# обычной; 2) кусок без явных разделителей дополнительно разбирается как
# цепочка «Фамилия И.О.» — два и более таких паттерна подряд, не разделённых
# посторонним текстом, считаются отдельными исполнителями.
_GLUE_COMMA_CHARS = "\u201a\u060c\uff0c\u00b7\u2022|/"  # ne-ASCII "zapyatye" iz raznyh raskladok + tochki/palochki
_GLUE_COMMA_TRANS = {ord(c): "," for c in _GLUE_COMMA_CHARS}
_PERSON_SPLIT_RE = re.compile(_PERSON_FULL_RE)
# Допустимый «мусор» между ФИО в склейке: пробелы, знаки, союз «и».
_GLUE_GAP_RE = re.compile(r"^(?:[\s,.;:]|и\b|[-–—])*$")


def _split_glued_fio(part: str) -> List[str]:
    """Разбить кусок без явного разделителя на отдельные «Фамилия И.О.»,
    если их там несколько и весь текст покрывается такими паттернами
    (плюс пробелы/знаки/«и»). Посторонний текст — кусок возвращается как есть."""
    txt = " ".join((part or "").split())
    if not txt:
        return []
    matches = list(_PERSON_SPLIT_RE.finditer(txt))
    if len(matches) < 2:
        # Одиночное полное ФИО — нормализуем инициалы («Чашин Э. А.» ->
        # «Чашин Э.А.»); голая фамилия/прочее — как есть.
        if (len(matches) == 1 and matches[0].start() == 0
                and matches[0].end() == len(txt)):
            return [_norm_person_name(matches[0].group(0))]
        return [txt]
    out: List[str] = []
    pos = 0
    for m in matches:
        gap = txt[pos:m.start()]
        if gap and not _GLUE_GAP_RE.fullmatch(gap):
            return [txt]  # посторонний текст между ФИО — не рискуем резать
        out.append(_norm_person_name(m.group(0)))
        pos = m.end()
    tail = txt[pos:]
    if tail and not _GLUE_GAP_RE.fullmatch(tail):
        return [txt]
    return out


def split_executors(text) -> List[str]:
    """Разбить поле «Исполнитель (ФИО)» по , + ; \\n (+ «склейки» ФИО)."""
    if not text:
        return []
    # NBSP — в обычный пробел: «Потемкин С.А., Семисенко» с NBSP после
    # запятой и так резался, а вот дальнейший разбор склеек и strip()
    # надёжнее над нормальными пробелами.
    raw = str(text).replace(" ", " ").translate(_GLUE_COMMA_TRANS)
    out: List[str] = []
    for part in re.split(r"[,+;]|\s*\n\s*", raw):
        part = part.strip()
        if not part:
            continue
        out.extend(_split_glued_fio(part))
    return out


def import_from_excel(
    filepath: str,
    existing: List[Control],
    skip_duplicates: bool = True,
) -> Tuple[List[Control], dict]:
    """Импорт контролей из .xlsx.

    :param filepath: путь к файлу
    :param existing: текущие контроли (для дедупликации по incoming_number)
    :return: (controls, stats) где stats = {"imported", "skipped", "errors", "full_format"}
    """
    from openpyxl import load_workbook

    stats = {"imported": 0, "skipped": 0, "errors": 0, "full_format": False}
    if not filepath:
        return [], stats

    wb = load_workbook(filepath, data_only=True)
    full_by_incoming = {}
    if FULL_SHEET in wb.sheetnames:
        stats["full_format"] = True
        full_by_incoming = _read_full_sheet(wb[FULL_SHEET])

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], stats

    # Шапка может лежать не в первой строке: раунд 7 — строка 1 объединённый
    # заголовок «КОНТРОЛИ ОТДЕЛА КРИМИНАЛИСТИКИ», шапка — строка 2.
    # Ищем строку с заголовками среди первых 10 непустых строк.
    def _is_header_row(row):
        vals = [str(h or "").strip() for h in row]
        has_in = any(("вх" in v.lower() or "вхсоп" in v.lower() or "иссоп" in v.lower()) for v in vals)
        has_content = any(("Содерж" in v or "Исполнитель" in v) for v in vals)
        return has_in and has_content

    header_row_idx = 0
    for i, row in enumerate(rows[:10]):
        if _is_header_row(row):
            header_row_idx = i
            break

    header = rows[header_row_idx]
    # Ищем индекс колонок по заголовкам (устойчиво к порядку/названию)
    col_idx = {i: None for i in range(len(TABLE_HEADERS))}
    for ci, h in enumerate(header):
        hs = str(h or "").strip()
        if hs.startswith("вх") or "вхсоп" in hs.lower() or "иссоп" in hs.lower():
            col_idx[1] = ci
        elif hs == "Дата поступления":
            col_idx[2] = ci
        elif hs == "Инициатор" or hs == "Инициатор ":
            col_idx[3] = ci
        elif "Содерж" in hs:
            col_idx[4] = ci
        elif "Исполнитель" in hs:
            col_idx[5] = ci
        elif "контроль" in hs.lower():
            col_idx[6] = ci
        elif "разов" in hs.lower() or "постоянн" in hs.lower():
            col_idx[7] = ci
        elif "дата исполн" in hs.lower():
            col_idx[8] = ci
        elif "исполнено" in hs.lower():
            col_idx[9] = ci
    has_full_headers = all(col_idx[i] is not None for i in range(10))
    if not has_full_headers:
        # Упрощённый маппинг: если колонки не распознаны — читать по порядку
        col_idx = {i: i for i in range(min(10, len(header)))}

    existing_incoming = {c.incoming_number for c in existing}
    new_controls: List[Control] = []
    errors = 0
    for ri, row in enumerate(rows[header_row_idx + 1:], header_row_idx + 2):
        if all(v is None or str(v).strip() == "" for v in row):
            continue
        incoming_cell = None
        ci = col_idx.get(1)
        if ci is not None and ci < len(row):
            incoming_cell = row[ci]
        if not incoming_cell or not str(incoming_cell).strip():
            continue  # служебная строка (инфо) без вх. № — не считать
        if str(incoming_cell).strip() in existing_incoming:
            stats["skipped"] += 1
            continue
        try:
            ctl = _row_to_control(row, col_idx, full_by_incoming, existing_incoming)
            if ctl is None:
                stats["skipped"] += 1
                continue
            new_controls.append(ctl)
            stats["imported"] += 1
        except Exception as e:
            errors += 1
            print(f"[CONTROLS_EXCEL] row {ri} error: {e}")
    stats["errors"] = errors
    return new_controls, stats


def _read_full_sheet(ws) -> dict:
    """Прочитать скрытый лист полного round-trip в {incoming_number: data}."""
    result = {}
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return result
    header = [str(h or "").strip() for h in rows[0]]
    for row in rows[1:]:
        d = {}
        for ci, h in enumerate(header):
            if ci < len(row):
                d[h] = row[ci]
        incoming = str(d.get("incoming", "") or "").strip()
        if incoming:
            result[incoming] = d
    return result


def _row_to_control(row, col_idx, full_by_incoming: dict,
                    existing_incoming) -> Optional[Control]:
    def _get(i):
        ci = col_idx.get(i)
        if ci is None or ci >= len(row):
            return None
        return row[ci]

    incoming = str(_get(1) or "").strip()
    if not incoming:
        return None
    if incoming in existing_incoming:
        return None  # дубликат

    # Если есть скрытый лист — берём точные данные оттуда
    if full_by_incoming:
        full_row = full_by_incoming.get(incoming)
        if full_row:
            ctl = _from_full_row(full_row, incoming)
            if ctl is not None:
                return ctl

    receive = parse_excel_date(_get(2))
    initiator = str(_get(3) or "").strip()
    content = str(_get(4) or "").strip()
    # Раунд 20 (задача 3): «п. N к DD.MM.YYYY» с ФИО-владельцем внутри
    # содержания — в ПУНКТЫ карточки (ControlTask со сроком и ответственным),
    # а не мёртвым текстом (пример — строка 41 эталона). Ответственные пунктов
    # добавляются в исполнители контроля, если их нет в колонке «Исполнитель».
    # Раунд 21 (задача 3): поддержан INLINE-формат («п. 2 - Миронович
    # 01.05.2026», несколько фамилий через запятую, пункт без исполнителя —
    # см. parse_content_tasks); «голые» фамилии привязываются к известным ФИО
    # (колонка «Исполнитель» + справочник людей) — иначе в исполнителях
    # плодились дубли «Миронович» / «Миронович Д.В.».
    content_tasks: List[ControlTask] = []
    try:
        content, content_tasks = parse_content_tasks(content)
    except Exception:
        content_tasks = []
    executors = split_executors(_get(5))
    if content_tasks:
        # Привязка «голых» фамилий ДВУМЯ проходами: сначала по колонке
        # «Исполнитель» (её форма канонична для строки — «Миронович Д.В.»),
        # иначе справочник даёт неоднозначность «Миронович Д.В.» vs «Миронович
        # Дмитрий Владимирович» и фамилия остаётся голой (дубли в исполнителях).
        # Остаток (нет в колонке) — по справочнику людей.
        resolve_task_assignees(content_tasks, executors)
        try:
            from .controls_data import load_settings, get_all_people_names
            resolve_task_assignees(content_tasks, list(get_all_people_names(load_settings())))
        except Exception:
            pass
    for _t in content_tasks:
        for _a in _t.assignees:
            if _a and not any((_e or "").strip().casefold() == _a.casefold() for _e in executors):
                executors.append(_a)
    controller = str(_get(6) or "").strip()
    # Раунд 18 (задача 2): колонка H «Разовый / постоянный» используется
    # КОМБИНИРОВАННО (эталон пользователя):
    #   * «01.09.2026» — дата => разовый контроль, это КОНЕЧНАЯ дата исполнения
    #     (end_date); раньше дата молча выбрасывалась parse_periodicity — терялась.
    #   * «10.05.2026 далее каждые 3 месяца» — периодический с конечной датой:
    #     ведущая дата -> end_date, хвост -> period_days (существующая эвристика).
    # due_date — колонка I «Следующая дата исполнения» (для разового без I —
    # fallback на end_date).
    type_raw = _get(7)
    type_text = str(type_raw or "").strip()
    end_date = parse_excel_date(type_raw)
    if end_date is not None:
        ctype, period_days = ONE_TIME, 0
    else:
        ctype, period_days = parse_periodicity(type_text)
        m = re.search(r"\d{1,2}\.\d{1,2}\.\d{4}", type_text)
        if m:
            end_date = parse_excel_date(m.group(0))
    due = parse_excel_date(_get(8)) or end_date
    done_text = _get(9)

    done = False
    done_date = None
    comment = ""
    if done_text is not None and str(done_text).strip() != "":
        done = True
        dd = parse_excel_date(done_text)
        if dd:
            done_date = dd
        else:
            comment = f"исполнено (по импорту): {str(done_text).strip()}"

    if ctype == ONE_TIME:
        period_days = 7
    if ctype == PERIODIC and period_days == 0:
        period_days = 7

    ctl = Control(
        id=None,  # будет сгенерирован
        incoming_number=incoming,
        receive_date=receive,
        initiator=initiator,
        content=content,
        executors=executors,
        controller=controller,
        control_type=ctype,
        period_days=period_days,
        end_date=end_date,   # Раунд 18: конечная дата исполнения больше не теряется
        due_date=due,
        done=done,
        done_date=done_date,
        comment=comment,
    )
    # Раунд 20 (задача 3): пункты задания из текста содержания
    ctl.tasks = content_tasks
    return ctl


def _from_full_row(full: dict, incoming: str) -> Optional[Control]:
    try:
        def _s(k):
            v = full.get(k)
            return str(v).strip() if v is not None else ""

        ctl = Control(
            id=_s("id") or None,
            incoming_number=_s("incoming") or incoming,
            control_type=_s("control_type") or ONE_TIME,
            period_days=int(_s("period_days") or 7) if _s("period_days") else 7,
            end_date=_s("end_date") or None,
            receive_date=_s("receive_date") or None,
            due_date=_s("due_date") or None,
            done=_s("done") == "1",
            done_date=_s("done_date") or None,
            initiator=_s("initiator"),
            content=_s("content"),
            controller=_s("controller"),
            comment=_s("comment"),
            archived=_s("archived") == "1",
            archive_reason=_s("archive_reason"),
            executors=_json_list(full.get("executors")),
        )
        tasks = _json_list(full.get("tasks"))
        ctl.tasks = [ControlTask.from_dict(t) for t in tasks if isinstance(t, dict)]
        milestones = _json_list(full.get("milestones"))
        ctl.milestones = [ControlMilestone.from_dict(m) for m in milestones if isinstance(m, dict)]
        attachments = _json_list(full.get("attachments"))
        ctl.attachments = [a for a in attachments if isinstance(a, str)]
        return ctl
    except Exception as e:
        print(f"[CONTROLS_EXCEL] full row parse error: {e}")
        return None


def _json_list(val) -> list:
    if val is None:
        return []
    if isinstance(val, list):
        return val
    try:
        parsed = json.loads(str(val))
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []

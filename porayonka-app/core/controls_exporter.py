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
    OVERDUE, TODAY, SOON, COMPLETED,
)

# Заголовки в формате пользователя (одна строка = один контроль)
TABLE_HEADERS = [
    "№", "вх. № ВХСОП", "Дата поступления", "Инициатор", "Содержание",
    "Исполнитель (ФИО)", "За кем контроль", "Разовый/постоянный",
    "Следующая дата исполнения", "Исполнено + дата",
]

# Имя скрытого листа для полного round-trip
FULL_SHEET = "_controls_full"


# ────────────────────────────────────────────────
# УТИЛИТЫ ФОРМАТА
# ────────────────────────────────────────────────

def _fmt(iso: Optional[str]) -> str:
    d = parse_date(iso)
    return d.strftime("%d.%m.%Y") if d else ""


def _type_text(ctl: Control) -> str:
    """Человекочитаемый текст типа для колонки «Разовый/постоянный»."""
    if ctl.control_type != PERIODIC:
        return "разовый"
    labels = {1: "ежедневно", 7: "еженедельно", 30: "ежемесячно",
              91: "ежеквартально", 365: "ежегодно"}
    return labels.get(ctl.period_days, f"каждые {ctl.period_days} дней")


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
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            raise ImportError("openpyxl не установлена. pip install openpyxl")

        wb = Workbook()
        ws = wb.active
        ws.title = "Контроли"

        header_fill = PatternFill("solid", fgColor="1E293B")
        header_font = Font(bold=True, color="FFFFFF", size=10)
        yellow_fill = PatternFill("solid", fgColor="FEF9C3")
        green_fill = PatternFill("solid", fgColor="DCFCE7")
        gray_fill = PatternFill("solid", fgColor="F1F5F9")
        thin = Side(style="thin", color="CBD5E1")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        left_wrap = Alignment(horizontal="left", vertical="center", wrap_text=True)

        widths = [4, 16, 15, 18, 46, 24, 20, 22, 14, 16]
        for col_i, (h, w) in enumerate(zip(TABLE_HEADERS, widths), 1):
            c = ws.cell(row=1, column=col_i, value=h)
            c.fill = header_fill
            c.font = header_font
            c.alignment = center
            c.border = border
            ws.column_dimensions[get_column_letter(col_i)].width = w
        ws.row_dimensions[1].height = 24

        active = [c for c in controls if not c.archived]
        st_map = {"overdue": 0, "today": 0, "soon": 0, "in_progress": 0,
                  "done": 0, "completed": 0}
        for ctl in active:
            st_map[deadline_status(ctl, soon_days)] = st_map.get(
                deadline_status(ctl, soon_days), 0) + 1

        row = 2
        info = (f"Всего: {len(active)}  |  Просрочено: {st_map['overdue']}  |  "
                f"Сегодня: {st_map['today']}  |  Скоро: {st_map['soon']}  |  "
                f"В работе: {st_map['in_progress']}  |  Исполнено: {st_map['done']}")
        ws.merge_cells(start_row=row, start_column=1, end_row=row,
                       end_column=len(TABLE_HEADERS))
        ic = ws.cell(row=row, column=1, value=info)
        ic.font = Font(bold=True, size=9, color="FFFFFF")
        ic.fill = PatternFill("solid", fgColor="334155")
        ic.alignment = Alignment(horizontal="center", vertical="center")
        ic.border = border
        ws.row_dimensions[row].height = 18
        row += 1

        for idx, ctl in enumerate(active, 1):
            st = deadline_status(ctl, soon_days)
            due = effective_due_date(ctl)
            values = [
                idx,
                ctl.incoming_number or "—",
                _fmt(ctl.receive_date),
                ctl.initiator or "—",
                ctl.content or "—",
                ", ".join(short_name(x) for x in ctl.executors) or "—",
                short_name(ctl.controller) or "—",
                _type_text(ctl),
                _fmt(ctl.due_date) if ctl.due_date else _fmt(due.isoformat() if due else None),
                _done_text(ctl),
            ]
            for col_i, v in enumerate(values, 1):
                c = ws.cell(row=row, column=col_i, value=v)
                c.border = border
                c.font = Font(size=10, color="334155")
                c.alignment = center if col_i in (1, 2, 3, 7, 8, 9, 10) else left_wrap

            # Жёлтая заливка «Следующая дата» при наступившем/близком сроке
            if st in (OVERDUE, TODAY, SOON):
                ws.cell(row=row, column=9).fill = yellow_fill
            # Зелёная заливка «Исполнено + дата» при done
            if ctl.done:
                ws.cell(row=row, column=10).fill = green_fill
                ws.cell(row=row, column=1).fill = green_fill
            elif st == COMPLETED:
                ws.cell(row=row, column=9).fill = gray_fill

            content_lines = max(1, -(-len(ctl.content or "") // 40))
            row += 1
            ws.row_dimensions[row - 1].height = max(20, content_lines * 14 + 6)

        ws.freeze_panes = "A3"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(TABLE_HEADERS))}{row - 1}"
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


def split_executors(text) -> List[str]:
    """Разбить поле «Исполнитель (ФИО)» по , + ; \n."""
    if not text:
        return []
    parts = re.split(r"[,+;]|\s*\n\s*", str(text))
    return [p.strip() for p in parts if p.strip()]


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

    header = rows[0]
    # Ищем индекс колонок по заголовкам (устойчиво к порядку/названию)
    col_idx = {i: None for i in range(len(TABLE_HEADERS))}
    for ci, h in enumerate(header):
        hs = str(h or "").strip()
        if hs.startswith("вх") or "вхсоп" in hs.lower() or "иссоп" in hs.lower():
            col_idx[1] = ci
        elif hs == "Дата поступления":
            col_idx[2] = ci
        elif hs == "Инициатор":
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
    for ri, row in enumerate(rows[1:], 2):
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
        ctl = _from_full_row(full_by_incoming.get(incoming), incoming)
        if ctl is not None:
            return ctl

    receive = parse_excel_date(_get(2))
    initiator = str(_get(3) or "").strip()
    content = str(_get(4) or "").strip()
    executors = split_executors(_get(5))
    controller = str(_get(6) or "").strip()
    ctype, period_days = parse_periodicity(str(_get(7) or ""))
    due = parse_excel_date(_get(8))
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

    return Control(
        id=None,  # будет сгенерирован
        incoming_number=incoming,
        receive_date=receive,
        initiator=initiator,
        content=content,
        executors=executors,
        controller=controller,
        control_type=ctype,
        period_days=period_days,
        due_date=due,
        done=done,
        done_date=done_date,
        comment=comment,
    )


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

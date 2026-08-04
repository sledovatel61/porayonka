# core/controls_exporter.py
# Экспорт контролей в Excel (аналог зональной вкладки)
from datetime import date
from typing import List

from .controls_models import (
    Control, effective_due_date, deadline_status, parse_date,
    STATUS_LABELS, STATUS_COLORS, PERIODIC,
)


class ControlsExcelExporter:
    """Экспорт списка контролей в .xlsx с цветовой индикацией сроков."""

    def export(self, controls: List[Control], filepath: str, soon_days: int = 3) -> None:
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
        thin = Side(style="thin", color="CBD5E1")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        left_wrap = Alignment(horizontal="left", vertical="center", wrap_text=True)

        headers = [
            "№", "вх. № ВХСОП", "Дата поступления", "Инициатор",
            "Содержание", "Исполнитель (ФИО)", "За кем контроль",
            "Тип", "Следующая дата", "Статус срока", "Исполнено",
        ]
        widths = [4, 16, 13, 16, 42, 22, 18, 12, 13, 13, 13]

        for col_i, (h, w) in enumerate(zip(headers, widths), 1):
            c = ws.cell(row=1, column=col_i, value=h)
            c.fill = header_fill
            c.font = header_font
            c.alignment = center
            c.border = border
            ws.column_dimensions[get_column_letter(col_i)].width = w
        ws.row_dimensions[1].height = 24

        # Заголовок-сводка
        row = 2
        now = date.today()
        st_map = {
            "overdue": 0, "today": 0, "soon": 0, "in_progress": 0, "done": 0,
        }
        for ctl in controls:
            st = deadline_status(ctl, soon_days)
            st_map[st] = st_map.get(st, 0) + 1

        info = (f"Всего: {len(controls)}  |  Просрочено: {st_map['overdue']}  |  "
                f"Сегодня: {st_map['today']}  |  Скоро: {st_map['soon']}  |  "
                f"В работе: {st_map['in_progress']}  |  Исполнено: {st_map['done']}")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=len(headers))
        ic = ws.cell(row=row, column=1, value=info)
        ic.font = Font(bold=True, size=9, color="FFFFFF")
        ic.fill = PatternFill("solid", fgColor="334155")
        ic.alignment = Alignment(horizontal="center", vertical="center")
        ic.border = border
        ws.row_dimensions[row].height = 18
        row += 1

        today = date.today()
        for idx, ctl in enumerate(controls, 1):
            st = deadline_status(ctl, soon_days)
            st_color = STATUS_COLORS.get(st, "94A3B8")

            def _fmt_iso(s):
                d = parse_date(s)
                return d.strftime("%d.%m.%Y") if d else "—"

            values = [
                idx,
                ctl.incoming_number or "—",
                _fmt_iso(ctl.receive_date),
                ctl.initiator or "—",
                ctl.content or "—",
                ", ".join(ctl.executors) or "—",
                ctl.controller or "—",
                "постоянный" if ctl.control_type == PERIODIC else "разовый",
                _fmt_iso(ctl.due_date),
                STATUS_LABELS.get(st, st),
                _fmt_iso(ctl.done_date) if ctl.done else "—",
            ]
            for col_i, v in enumerate(values, 1):
                c = ws.cell(row=row, column=col_i, value=v)
                c.border = border
                c.font = Font(size=10, color="334155")
                c.alignment = center if col_i in (1, 2, 3, 8, 9, 10, 11) else left_wrap

            # Подсветка статуса срока
            sc = ws.cell(row=row, column=10)
            sc.fill = PatternFill("solid", fgColor=_hex_to_rgb_fill(st_color))
            sc.font = Font(size=10, bold=True, color=_font_on_fill(st_color))

            content_lines = max(1, -(-len(ctl.content or "") // 38))
            row += 1
            ws.row_dimensions[row - 1].height = max(20, content_lines * 14 + 6)

        ws.freeze_panes = "A3"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{row - 1}"
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        wb.save(filepath)
        print(f"[CONTROLS_EXCEL] [OK] File: {filepath}")


def _hex_to_rgb_fill(hex_color: str) -> str:
    """Преобразовать #RRGGBB в строку открытого формата openpyxl."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        return hex_color.upper()
    return "FFFFFF"


def _font_on_fill(hex_color: str) -> str:
    """Цвет текста, читаемый на подложке статуса."""
    light = {"#ef4444", "#f59e0b", "#fb923c", "#22c55e"}
    return "FFFFFF" if hex_color.lstrip("#") in {c.lstrip("#") for c in light} else "1E293B"

# ui/controls/russian_calendar.py
# Кастомный русский календарь для вкладки «Контроли» (замена ft.DatePicker).
#
# ТЗ (PROMPT_контроли_дизайн.md §5):
#   - API: create_russian_date_field(page, value, on_change, hint="Дата") -> ft.Control
#   - поле ввода read_only (dd.mm.yyyy) + иконка календаря; клик открывает панель;
#   - панель ИНЛАЙН (под полем, через visible toggle) — не AlertDialog, не второй
#     слой overlay поверх detail_overlay (AGENTS.md §31);
#   - шапка: ‹ «Август 2026» ›, листание по месяцам;
#   - дни недели Пн…Вс, неделя с понедельника;
#   - сетка 6×7, ячейка 34×32, radius 8; дни соседних месяцев приглушены;
#     hover #ffffff12; сегодня — рамка 1px #4f8cff; выбранный — заливка #4f8cff;
#   - клик по дню = мгновенный выбор, без OK/Cancel;
#   - снизу «Сегодня» и «Очистить» (ghost);
#   - только stdlib, без зависимостей; без animate/shadow/gradient/wrap.
import calendar as _cal
from datetime import date
from typing import Callable, Optional

import flet as ft

from .glass_theme import GLASS

_MONTHS_RU = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]
_WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

_CELL_W = 34
_CELL_H = 32


def _parse_iso(value) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def _display(iso) -> str:
    d = _parse_iso(iso)
    return d.strftime("%d.%m.%Y") if d else ""


def _glass_field(**kwargs) -> ft.TextField:
    opts = dict(
        border_radius=10,
        border_color=GLASS["border"],
        focused_border_color=GLASS["accent"],
        bgcolor=GLASS["field"],
        color=GLASS["text"],
        hint_style=ft.TextStyle(size=13, color=GLASS["text_3"]),
        text_style=ft.TextStyle(size=13, color=GLASS["text"]),
        dense=True,
    )
    opts.update(kwargs)
    return ft.TextField(**opts)


def create_russian_date_field(
    page: ft.Page,
    value: Optional[str],
    on_change: Callable[[Optional[str]], None],
    hint: str = "Дата",
    width: int = 150,
    height: int = 40,
) -> ft.Control:
    """Поле даты с инлайн-панелью русского календаря.

    Клик по полю/иконке открывает календарь под полем. Выбор дня — мгновенно:
    on_change("YYYY-MM-DD") + закрытие панели. «Очистить» — on_change(None).
    """

    def _close_panel():
        panel.visible = False
        state["open"] = False
        try:
            panel.update()
        except Exception:
            pass

    def _refresh_field_text():
        field.value = _display(state["value"])
        clear_btn.visible = bool(state["value"])
        try:
            field.update()
            clear_btn.update()
        except Exception:
            pass

    state = {
        "value": value or None,
        "month": None,   # заполняется при первом открытии
        "year": None,
        "open": False,
    }

    field = _glass_field(
        value=_display(value),
        hint_text=hint,
        read_only=True,
        width=width,
        height=height,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
    )
    icon_btn = ft.IconButton(
        icon=ft.icons.CALENDAR_MONTH,
        icon_size=16,
        icon_color=GLASS["accent"],
        tooltip="Открыть календарь",
        width=34,
        height=height,
        on_click=lambda e: _toggle(),
    )
    clear_btn = ft.IconButton(
        icon=ft.icons.CLEAR,
        icon_size=14,
        icon_color=GLASS["text_3"],
        tooltip="Очистить",
        visible=bool(value),
        width=26,
        height=height,
        on_click=lambda e: _clear(),
    )

    field.on_focus = lambda e: _toggle()

    def _open():
        # текущий месяц: из выбранной даты, иначе — сегодня
        d = _parse_iso(state["value"]) or date.today()
        state["month"] = d.month
        state["year"] = d.year
        state["open"] = True
        _rebuild_grid()
        panel.visible = True
        try:
            panel.update()
        except Exception:
            pass

    def _toggle():
        if state["open"]:
            _close_panel()
        else:
            _open()

    # ── Панель ──────────────────────────────────────────────────
    month_label = ft.Text("", size=13, weight=ft.FontWeight.BOLD,
                          color=GLASS["text"], text_align=ft.TextAlign.CENTER)
    grid_col = ft.Column(spacing=2, tight=True,
                         horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def _rebuild_grid():
        m = state["month"] or date.today().month
        y = state["year"] or date.today().year
        month_label.value = f"{_MONTHS_RU[m - 1]} {y}"
        weeks = _cal.Calendar(firstweekday=0).monthdatescalendar(y, m)
        while len(weeks) < 6:
            weeks.append([None] * 7)
        cells = []
        for week in weeks:
            row_ctrls = []
            for d in week:
                if d is None:
                    row_ctrls.append(ft.Container(width=_CELL_W, height=_CELL_H))
                    continue
                in_month = (d.month == m)
                iso = d.isoformat()
                selected = (iso == state["value"])
                is_today = (d == date.today())
                color = GLASS["text"] if in_month else GLASS["text_3"]
                cell = ft.Container(
                    width=_CELL_W,
                    height=_CELL_H,
                    border_radius=8,
                    bgcolor=GLASS["accent"] if selected else "transparent",
                    border=ft.border.all(1, GLASS["accent"]) if (is_today and not selected) else None,
                    content=ft.Text(
                        str(d.day), size=12,
                        color=GLASS["text"] if selected else color,
                        weight=ft.FontWeight.W_600 if (selected or is_today) else None,
                    ),
                    alignment=ft.alignment.center,
                    ink=True,
                    on_click=lambda e, dd=d: _pick(dd),
                )

                def _hover(e, c=cell, sel=selected):
                    if sel:
                        return
                    c.bgcolor = GLASS["hover_strong"] if e.data == "true" else "transparent"
                    try:
                        c.update()
                    except Exception:
                        pass

                cell.on_hover = _hover
                row_ctrls.append(cell)
            cells.append(ft.Row(controls=row_ctrls, spacing=2, tight=True))
        grid_col.controls.clear()
        grid_col.controls.extend(cells)
        try:
            grid_col.update()
            month_label.update()
        except Exception:
            pass

    def _shift_month(delta: int):
        m = (state["month"] or date.today().month) + delta
        y = state["year"] or date.today().year
        if m < 1:
            m, y = 12, y - 1
        elif m > 12:
            m, y = 1, y + 1
        state["month"] = m
        state["year"] = y
        _rebuild_grid()

    def _pick(d: date):
        iso = d.isoformat()
        state["value"] = iso
        _refresh_field_text()
        _close_panel()
        try:
            on_change(iso)
        except Exception:
            pass

    def _today(e=None):
        iso = date.today().isoformat()
        state["value"] = iso
        _refresh_field_text()
        _close_panel()
        try:
            on_change(iso)
        except Exception:
            pass

    def _clear(e=None):
        state["value"] = None
        _refresh_field_text()
        _close_panel()
        try:
            on_change(None)
        except Exception:
            pass

    weekdays_row = ft.Row(controls=[
        ft.Container(width=_CELL_W, alignment=ft.alignment.center,
                     content=ft.Text(w, size=10, weight=ft.FontWeight.BOLD,
                                     color=GLASS["text_3"], text_align=ft.TextAlign.CENTER))
        for w in _WEEKDAYS_RU
    ], spacing=2, tight=True)

    panel = ft.Container(
        width=280,
        visible=False,
        bgcolor=GLASS["surface_solid"],
        border=ft.border.all(1, GLASS["border"]),
        border_radius=12,
        padding=ft.padding.all(10),
        content=ft.Column(controls=[
            ft.Row(controls=[
                ft.IconButton(icon=ft.icons.CHEVRON_LEFT, icon_size=18,
                              icon_color=GLASS["text_2"], tooltip="Предыдущий месяц",
                              width=28, height=28, on_click=lambda e: _shift_month(-1)),
                ft.Container(content=month_label, expand=True, alignment=ft.alignment.center),
                ft.IconButton(icon=ft.icons.CHEVRON_RIGHT, icon_size=18,
                              icon_color=GLASS["text_2"], tooltip="Следующий месяц",
                              width=28, height=28, on_click=lambda e: _shift_month(1)),
            ], spacing=2, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(height=2),
            weekdays_row,
            grid_col,
            ft.Container(height=2),
            ft.Row(controls=[
                ft.TextButton(
                    content=ft.Text("Сегодня", size=11, color=GLASS["accent"], no_wrap=True),
                    on_click=_today,
                    style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=8))),
                ft.Container(expand=True),
                ft.TextButton(
                    content=ft.Text("Очистить", size=11, color=GLASS["text_3"], no_wrap=True),
                    on_click=_clear,
                    style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=8))),
            ], spacing=2, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=4, tight=True),
    )

    composite = ft.Column(
        controls=[
            ft.Row(controls=[field, icon_btn, clear_btn], spacing=4, tight=True,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            panel,
        ],
        spacing=4,
        tight=True,
    )
    composite._get_value = lambda: state["value"]
    composite._set_value = lambda iso: (state.__setitem__("value", iso or None), _refresh_field_text())
    composite._field = field
    return composite

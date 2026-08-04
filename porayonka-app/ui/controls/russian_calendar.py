# ui/controls/russian_calendar.py
# Кастомный русский календарь для вкладки «Контроли» (Glass Dark)
# Заменяет ft.DatePicker во всей вкладке.
# API: create_russian_date_field(page, value: Optional[str], on_change, hint="Дата") -> ft.Control
#  - value: Optional ISO "YYYY-MM-DD"
#  - on_change: callable(iso_or_none: Optional[str])
#  - hint: placeholder
#
# Ограничения движка Flet 0.23.2:
# - никакого animate, shadow, gradient, wrap
# - hover через on_hover + update()
# - инлайн-панель через visible toggle, НЕ AlertDialog
import calendar
from datetime import date, datetime
from typing import Optional, Callable

import flet as ft

from .glass_theme import GLASS

MONTHS_RU = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]
WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

def _parse_iso(v: Optional[str]) -> Optional[date]:
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None

def _format_display(d: Optional[date]) -> str:
    return d.strftime("%d.%m.%Y") if d else ""

def create_russian_date_field(
    page: ft.Page,
    value: Optional[str],
    on_change: Callable[[Optional[str]], None],
    hint: str = "Дата",
    width: Optional[int] = None,
):
    """
    Возвращает ft.Control — поле + выпадающий календарь.
    Поле показывает dd.mm.yyyy или hint/"—".
    Клик по полю открывает календарь.
    Клик по дню = мгновенный выбор + закрытие.
    """
    selected: dict = {"date": _parse_iso(value)}
    today = date.today()
    # current viewed month/year
    cur = selected["date"] or today
    view = {"year": cur.year, "month": cur.month}

    # display text
    def _display_text():
        if selected["date"]:
            return _format_display(selected["date"])
        return hint or "—"

    field_text = ft.Text(
        _display_text(),
        size=13,
        color=GLASS["text"] if selected["date"] else GLASS["text_muted"],
        no_wrap=True,
        weight=ft.FontWeight.W_400,
        tooltip=_display_text(),
    )

    # field container (sunken)
    def _toggle_calendar(e=None):
        cal_panel.visible = not cal_panel.visible
        try:
            cal_panel.update()
        except Exception:
            try:
                outer.update()
            except Exception:
                pass

    input_row = ft.Row(
        controls=[
            field_text,
            ft.Container(expand=True),
            ft.Icon(ft.icons.CALENDAR_MONTH, size=16, color=GLASS["text_secondary"]),
        ],
        spacing=6,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    input_container = ft.Container(
        content=input_row,
        height=40,
        width=width,
        bgcolor=GLASS["surface_alt"],
        border=ft.border.all(1, GLASS["border"]),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=10),
        alignment=ft.alignment.center_left,
        ink=True,
        on_click=_toggle_calendar,
    )

    # month label
    month_label = ft.Text(
        f"{MONTHS_RU[view['month']-1]} {view['year']}",
        size=13,
        weight=ft.FontWeight.BOLD,
        color=GLASS["text"],
        no_wrap=True,
    )

    # weekday header
    weekday_row = ft.Row(
        controls=[
            ft.Container(
                content=ft.Text(wd, size=10, weight=ft.FontWeight.BOLD, color=GLASS["text_muted"], text_align=ft.TextAlign.CENTER),
                width=34, height=20, alignment=ft.alignment.center
            ) for wd in WEEKDAYS_RU
        ],
        spacing=2,
        tight=True,
        alignment=ft.MainAxisAlignment.START,
    )

    grid_col = ft.Column(spacing=2, tight=True)

    # hover handler factory
    def _make_hover_handler(cell_ref, is_sel):
        def _on_hover(e):
            if is_sel:
                return
            try:
                if e.data == "true":
                    cell_ref.bgcolor = GLASS["hover_light"]
                else:
                    cell_ref.bgcolor = "transparent" if not cell_ref._is_today else cell_ref.bgcolor
                    # restore base
                    if not hasattr(cell_ref, "_sel") or not cell_ref._sel:
                        if getattr(cell_ref, "_is_other", False):
                            cell_ref.bgcolor = "transparent"
                        else:
                            # if not today border, keep transparent
                            if not getattr(cell_ref, "_is_today", False):
                                cell_ref.bgcolor = "transparent"
                cell_ref.update()
            except Exception:
                pass
        return _on_hover

    def _select_day(dobj: date):
        selected["date"] = dobj
        field_text.value = _format_display(dobj)
        field_text.color = GLASS["text"]
        field_text.tooltip = _format_display(dobj)
        try:
            field_text.update()
            input_container.update()
        except Exception:
            pass
        cal_panel.visible = False
        try:
            cal_panel.update()
        except Exception:
            pass
        # callback ISO
        try:
            iso = dobj.isoformat()
            on_change(iso)
        except Exception:
            pass
        _rebuild_grid()

    def _clear_date(e=None):
        selected["date"] = None
        field_text.value = hint or "—"
        field_text.color = GLASS["text_muted"]
        field_text.tooltip = hint
        try:
            field_text.update()
        except Exception:
            pass
        cal_panel.visible = False
        try:
            cal_panel.update()
        except Exception:
            pass
        try:
            on_change(None)
        except Exception:
            pass
        _rebuild_grid()

    def _today_date(e=None):
        _select_day(today)
        # also set view to today month
        view["year"] = today.year
        view["month"] = today.month
        month_label.value = f"{MONTHS_RU[view['month']-1]} {view['year']}"
        try:
            month_label.update()
        except Exception:
            pass

    def _prev_month(e=None):
        m = view["month"] - 1
        y = view["year"]
        if m < 1:
            m = 12
            y -= 1
        view["month"] = m
        view["year"] = y
        month_label.value = f"{MONTHS_RU[m-1]} {y}"
        try:
            month_label.update()
        except Exception:
            pass
        _rebuild_grid()

    def _next_month(e=None):
        m = view["month"] + 1
        y = view["year"]
        if m > 12:
            m = 1
            y += 1
        view["month"] = m
        view["year"] = y
        month_label.value = f"{MONTHS_RU[m-1]} {y}"
        try:
            month_label.update()
        except Exception:
            pass
        _rebuild_grid()

    def _rebuild_grid():
        # build 6x7 grid starting Monday
        y = view["year"]
        m = view["month"]
        first_weekday = date(y, m, 1).weekday()  # Mon 0
        # days in current month
        _, dim = calendar.monthrange(y, m)
        # prev month
        pm = m - 1 if m > 1 else 12
        py = y if m > 1 else y - 1
        _, pdim = calendar.monthrange(py, pm)
        # next month start
        # build list of 42 dates
        days = []
        # prev month days
        for i in range(first_weekday):
            d = pdim - first_weekday + 1 + i
            days.append(date(py, pm, d))
        # current
        for d in range(1, dim + 1):
            days.append(date(y, m, d))
        # next
        needed = 42 - len(days)
        nm = m + 1 if m < 12 else 1
        ny = y if m < 12 else y + 1
        for d in range(1, needed + 1):
            days.append(date(ny, nm, d))

        grid_col.controls.clear()
        for week_idx in range(6):
            week_days = days[week_idx * 7: (week_idx + 1) * 7]
            row_cells = []
            for dobj in week_days:
                is_current = (dobj.month == m and dobj.year == y)
                is_today = (dobj == today)
                is_sel = (selected["date"] == dobj) if selected["date"] else False

                bg = GLASS["accent"] if is_sel else "transparent"
                txt_color = "white" if is_sel else (GLASS["text_muted"] if not is_current else GLASS["text"])
                border = None
                if is_today and not is_sel:
                    border = ft.border.all(1, GLASS["accent"])

                cell_text = ft.Text(str(dobj.day), size=12, color=txt_color, text_align=ft.TextAlign.CENTER)

                cell = ft.Container(
                    content=cell_text,
                    width=34,
                    height=32,
                    border_radius=8,
                    bgcolor=bg,
                    border=border,
                    alignment=ft.alignment.center,
                    ink=True,
                )
                # store flags for hover
                cell._is_today = is_today
                cell._is_other = not is_current
                cell._sel = is_sel

                def _make_click(dd):
                    def _click(e=None):
                        _select_day(dd)
                    return _click

                cell.on_click = _make_click(dobj)
                cell.on_hover = _make_hover_handler(cell, is_sel)

                row_cells.append(cell)

            grid_col.controls.append(
                ft.Row(controls=row_cells, spacing=2, tight=True, alignment=ft.MainAxisAlignment.START)
            )
        try:
            grid_col.update()
        except Exception:
            pass

    # header row
    header_row = ft.Row(
        controls=[
            ft.IconButton(icon=ft.icons.CHEVRON_LEFT, icon_size=18, icon_color=GLASS["text_secondary"], on_click=_prev_month, tooltip="Предыдущий месяц"),
            ft.Container(content=month_label, expand=True, alignment=ft.alignment.center),
            ft.IconButton(icon=ft.icons.CHEVRON_RIGHT, icon_size=18, icon_color=GLASS["text_secondary"], on_click=_next_month, tooltip="Следующий месяц"),
        ],
        spacing=4,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    bottom_row = ft.Row(
        controls=[
            ft.Container(
                content=ft.Text("Сегодня", size=11, color=GLASS["text_secondary"], weight=ft.FontWeight.W_600),
                height=28, padding=ft.padding.symmetric(horizontal=10),
                border=ft.border.all(1, GLASS["border"]),
                border_radius=8,
                bgcolor=GLASS["surface_alt"],
                ink=True,
                on_click=_today_date,
                alignment=ft.alignment.center,
            ),
            ft.Container(expand=True),
            ft.Container(
                content=ft.Text("Очистить", size=11, color=GLASS["text_secondary"], weight=ft.FontWeight.W_600),
                height=28, padding=ft.padding.symmetric(horizontal=10),
                border=ft.border.all(1, GLASS["border"]),
                border_radius=8,
                bgcolor=GLASS["surface_alt"],
                ink=True,
                on_click=_clear_date,
                alignment=ft.alignment.center,
            ),
        ],
        spacing=6,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    cal_panel = ft.Container(
        visible=False,
        width=280,
        bgcolor=GLASS["surface"],
        border=ft.border.only(
            top=ft.BorderSide(1, GLASS["border_top"]),
            left=ft.BorderSide(1, GLASS["border"]),
            right=ft.BorderSide(1, GLASS["border"]),
            bottom=ft.BorderSide(1, GLASS["border"]),
        ),
        border_radius=12,
        padding=ft.padding.all(10),
        content=ft.Column(
            controls=[
                header_row,
                ft.Container(height=6),
                weekday_row,
                ft.Container(height=2),
                grid_col,
                ft.Container(height=8),
                bottom_row,
            ],
            spacing=0,
            tight=True,
        ),
    )

    outer = ft.Column(
        controls=[input_container, cal_panel],
        spacing=4,
        tight=True,
    )

    # expose helpers for external reset
    def _set_value(iso_or_none: Optional[str]):
        d = _parse_iso(iso_or_none)
        selected["date"] = d
        if d:
            field_text.value = _format_display(d)
            field_text.color = GLASS["text"]
            field_text.tooltip = _format_display(d)
            view["year"] = d.year
            view["month"] = d.month
            month_label.value = f"{MONTHS_RU[d.month-1]} {d.year}"
        else:
            field_text.value = hint or "—"
            field_text.color = GLASS["text_muted"]
            field_text.tooltip = hint
            # view stays
        try:
            field_text.update()
            month_label.update()
        except Exception:
            pass
        _rebuild_grid()

    def _get_value():
        return selected["date"].isoformat() if selected["date"] else None

    def _show():
        cal_panel.visible = True
        try:
            cal_panel.update()
        except Exception:
            pass

    def _hide():
        cal_panel.visible = False
        try:
            cal_panel.update()
        except Exception:
            pass

    outer._set_value = _set_value
    outer._get_value = _get_value
    outer._show = _show
    outer._hide = _hide
    outer._field_text = field_text
    outer._panel = cal_panel
    outer._toggle = _toggle_calendar

    # initial build
    _rebuild_grid()

    return outer

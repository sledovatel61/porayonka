# ui/controls/russian_calendar.py
# Кастомный русский календарь — инлайн панель, без ft.DatePicker, без overlay
import calendar
from datetime import date, timedelta
from typing import Callable, Optional, Dict

import flet as ft
from .glass_theme import GLASS

MONTHS_RU = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

def _parse_iso(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except Exception:
        return None

def _format_display(iso: Optional[str]) -> str:
    d = _parse_iso(iso)
    return d.strftime("%d.%m.%Y") if d else "—"

def _build_calendar_grid(
    display_year: int,
    display_month: int,
    selected: Optional[date],
    on_select: Callable[[date], None],
):
    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(display_year, display_month)
    while len(weeks) < 6:
        last = weeks[-1][-1]
        base = last + timedelta(days=1)
        new_week = [base + timedelta(days=i) for i in range(7)]
        weeks.append(new_week)

    grid_controls = []
    today = date.today()
    for week in weeks[:6]:
        row = ft.Row(spacing=2, tight=True)
        for d in week:
            is_other = d.month != display_month
            is_today = d == today
            is_sel = (selected is not None and d == selected)
            bg = GLASS["accent"] if is_sel else "transparent"
            txt_color = "#ffffff" if is_sel else (GLASS["text_muted"] if is_other else GLASS["text"])
            border = ft.border.all(1, GLASS["accent"]) if is_today and not is_sel else None
            txt = ft.Text(str(d.day), size=12, color=txt_color, weight=ft.FontWeight.W_500 if is_today else None)

            def _make_click(dd):
                def _click(e=None):
                    on_select(dd)
                return _click

            def _make_hover(cell, orig_bg, sel):
                def _hover(e):
                    if sel:
                        return
                    try:
                        if e.data == "true":
                            cell.bgcolor = GLASS["hover_strong"]
                        else:
                            cell.bgcolor = orig_bg
                        cell.update()
                    except Exception:
                        pass
                return _hover

            cell = ft.Container(
                width=34, height=32, border_radius=8,
                bgcolor=bg, border=border,
                alignment=ft.alignment.center,
                content=txt, ink=True,
            )
            cell.on_click = _make_click(d)
            cell.on_hover = _make_hover(cell, bg, is_sel)
            row.controls.append(cell)
        grid_controls.append(row)
    return grid_controls

def create_russian_date_field(
    page: ft.Page,
    value: Optional[str],
    on_change: Callable[[Optional[str]], None],
    hint: str = "Дата",
    width: int = 160,
) -> ft.Container:
    state: Dict = {
        "selected_iso": value,
        "display_year": None,
        "display_month": None,
        "visible": False,
    }
    init_d = _parse_iso(value) or date.today()
    state["display_year"] = init_d.year
    state["display_month"] = init_d.month

    field_text = ft.Text(
        _format_display(value) if value else hint,
        size=13,
        color=GLASS["text"] if value else GLASS["text_muted"],
        no_wrap=True,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    clear_btn = ft.IconButton(
        icon=ft.icons.CLEAR,
        icon_size=14,
        icon_color=GLASS["text_muted"],
        width=22,
        height=22,
        padding=0,
        visible=bool(value),
        tooltip="Очистить",
    )
    field_icon = ft.Icon(ft.icons.CALENDAR_MONTH, size=18, color=GLASS["text_secondary"])
    field_row = ft.Row(
        controls=[field_text, ft.Container(expand=True), clear_btn, field_icon],
        spacing=4,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    field_box = ft.Container(
        content=field_row,
        width=width,
        height=40,
        bgcolor=GLASS["surface_alt"],
        border=ft.border.all(1, GLASS["border"]),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        alignment=ft.alignment.center_left,
    )

    header_label = ft.Text("", size=13, weight=ft.FontWeight.W_700, color=GLASS["text"])
    grid_col = ft.Column(spacing=2, tight=True)

    cal_panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.IconButton(icon=ft.icons.CHEVRON_LEFT, icon_size=18, icon_color=GLASS["text_secondary"], width=28, height=28, padding=0, on_click=lambda e: _nav(-1)),
                        ft.Container(content=header_label, expand=True, alignment=ft.alignment.center),
                        ft.IconButton(icon=ft.icons.CHEVRON_RIGHT, icon_size=18, icon_color=GLASS["text_secondary"], width=28, height=28, padding=0, on_click=lambda e: _nav(1)),
                    ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=4),
                ft.Row(
                    controls=[ft.Container(width=34, height=20, alignment=ft.alignment.center, content=ft.Text(wd, size=10, weight=ft.FontWeight.W_700, color=GLASS["text_muted"])) for wd in WEEKDAYS],
                    spacing=2, tight=True,
                ),
                grid_col,
                ft.Container(height=6),
                ft.Row(
                    controls=[
                        ft.TextButton("Сегодня", on_click=lambda e: _pick_today(), style=ft.ButtonStyle(color=GLASS["accent"])),
                        ft.Container(expand=True),
                        ft.TextButton("Очистить", on_click=lambda e: _clear(), style=ft.ButtonStyle(color=GLASS["text_muted"])),
                    ], spacing=4, tight=True,
                ),
            ], spacing=2, tight=True,
        ),
        width=280,
        bgcolor=GLASS["surface_solid"],
        border=ft.border.all(1, GLASS["border"]),
        border_radius=12,
        padding=ft.padding.all(10),
        visible=False,
    )

    wrapper = ft.Column(controls=[field_box, cal_panel], spacing=6, tight=True)
    root_width = max(width, 280)
    root = ft.Container(content=wrapper, width=root_width)

    def _close_panel():
        state["visible"] = False
        cal_panel.visible = False
        try:
            cal_panel.update()
        except Exception:
            try:
                root.update()
            except Exception:
                pass

    def _open_panel():
        state["visible"] = True
        cal_panel.visible = True
        _rebuild()
        try:
            cal_panel.update()
        except Exception:
            try:
                root.update()
            except Exception:
                pass

    def _toggle_panel(e=None):
        if state["visible"]:
            _close_panel()
        else:
            sel = _parse_iso(state["selected_iso"])
            if sel:
                state["display_year"] = sel.year
                state["display_month"] = sel.month
            _open_panel()

    field_box.on_click = _toggle_panel

    def _update_field_text():
        iso = state["selected_iso"]
        if iso:
            field_text.value = _format_display(iso)
            field_text.color = GLASS["text"]
        else:
            field_text.value = hint
            field_text.color = GLASS["text_muted"]
        try:
            field_text.update()
        except Exception:
            pass

    def _update_clear_visibility():
        has = bool(state["selected_iso"])
        clear_btn.visible = has
        try:
            clear_btn.update()
        except Exception:
            pass

    def _nav(delta: int):
        y = state["display_year"]
        m = state["display_month"]
        m += delta
        while m > 12:
            m -= 12
            y += 1
        while m < 1:
            m += 12
            y -= 1
        state["display_year"] = y
        state["display_month"] = m
        _rebuild()

    def _pick_today():
        today = date.today()
        state["selected_iso"] = today.isoformat()
        state["display_year"] = today.year
        state["display_month"] = today.month
        _update_field_text()
        _update_clear_visibility()
        _close_panel()
        try:
            on_change(state["selected_iso"])
        except Exception:
            pass
        _rebuild()

    def _clear():
        state["selected_iso"] = None
        _update_field_text()
        _update_clear_visibility()
        _close_panel()
        try:
            on_change(None)
        except Exception:
            pass
        _rebuild()

    def _on_clear_click(e=None):
        _clear()

    def _on_select(dd: date):
        state["selected_iso"] = dd.isoformat()
        _update_field_text()
        _update_clear_visibility()
        _close_panel()
        try:
            on_change(state["selected_iso"])
        except Exception:
            pass
        _rebuild()

    def _rebuild():
        try:
            header_label.value = f"{MONTHS_RU[state['display_month']-1]} {state['display_year']}"
            header_label.update()
        except Exception:
            header_label.value = f"{MONTHS_RU[state['display_month']-1]} {state['display_year']}"
        selected = _parse_iso(state["selected_iso"])
        grid_col.controls = _build_calendar_grid(state["display_year"], state["display_month"], selected, _on_select)
        try:
            grid_col.update()
        except Exception:
            pass
        try:
            header_label.update()
        except Exception:
            pass

    clear_btn.on_click = _on_clear_click

    _rebuild()

    def _set_iso(iso):
        state["selected_iso"] = iso
        if iso:
            d = _parse_iso(iso)
            if d:
                state["display_year"] = d.year
                state["display_month"] = d.month
        _update_field_text()
        _update_clear_visibility()
        _rebuild()

    root._get_iso = lambda: state["selected_iso"]
    root._set_iso = _set_iso
    root._close = _close_panel
    root._open = _open_panel
    root._field_text = field_text
    root._field_box = field_box
    return root

def create_russian_calendar_expanded(
    page: ft.Page,
    value: Optional[str],
    on_change: Callable[[Optional[str]], None],
    width: int = 280,
) -> ft.Container:
    state = {
        "selected_iso": value,
        "display_year": None,
        "display_month": None,
    }
    init_d = _parse_iso(value) or date.today()
    state["display_year"] = init_d.year
    state["display_month"] = init_d.month

    header_label = ft.Text("", size=13, weight=ft.FontWeight.W_700, color=GLASS["text"])
    grid_col = ft.Column(spacing=2, tight=True)

    def _on_select(dd: date):
        state["selected_iso"] = dd.isoformat()
        try:
            on_change(dd.isoformat())
        except Exception:
            pass
        _rebuild()

    def _nav(delta: int):
        y = state["display_year"]
        m = state["display_month"]
        m += delta
        while m > 12:
            m -= 12
            y += 1
        while m < 1:
            m += 12
            y -= 1
        state["display_year"] = y
        state["display_month"] = m
        _rebuild()

    def _pick_today():
        today = date.today()
        state["selected_iso"] = today.isoformat()
        state["display_year"] = today.year
        state["display_month"] = today.month
        try:
            on_change(state["selected_iso"])
        except Exception:
            pass
        _rebuild()

    def _clear():
        state["selected_iso"] = None
        try:
            on_change(None)
        except Exception:
            pass
        _rebuild()

    def _rebuild():
        try:
            header_label.value = f"{MONTHS_RU[state['display_month']-1]} {state['display_year']}"
            header_label.update()
        except Exception:
            header_label.value = f"{MONTHS_RU[state['display_month']-1]} {state['display_year']}"
        selected = _parse_iso(state["selected_iso"])
        grid_col.controls = _build_calendar_grid(state["display_year"], state["display_month"], selected, _on_select)
        try:
            grid_col.update()
        except Exception:
            pass
        try:
            header_label.update()
        except Exception:
            pass

    panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.IconButton(icon=ft.icons.CHEVRON_LEFT, icon_size=18, icon_color=GLASS["text_secondary"], width=28, height=28, padding=0, on_click=lambda e: _nav(-1)),
                        ft.Container(content=header_label, expand=True, alignment=ft.alignment.center),
                        ft.IconButton(icon=ft.icons.CHEVRON_RIGHT, icon_size=18, icon_color=GLASS["text_secondary"], width=28, height=28, padding=0, on_click=lambda e: _nav(1)),
                    ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=4),
                ft.Row(
                    controls=[ft.Container(width=34, height=20, alignment=ft.alignment.center, content=ft.Text(wd, size=10, weight=ft.FontWeight.W_700, color=GLASS["text_muted"])) for wd in WEEKDAYS],
                    spacing=2, tight=True,
                ),
                grid_col,
                ft.Container(height=6),
                ft.Row(
                    controls=[
                        ft.TextButton("Сегодня", on_click=lambda e: _pick_today(), style=ft.ButtonStyle(color=GLASS["accent"])),
                        ft.Container(expand=True),
                        ft.TextButton("Очистить", on_click=lambda e: _clear(), style=ft.ButtonStyle(color=GLASS["text_muted"])),
                    ], spacing=4, tight=True,
                ),
            ], spacing=2, tight=True,
        ),
        width=width,
        bgcolor=GLASS["surface_solid"],
        border=ft.border.all(1, GLASS["border"]),
        border_radius=12,
        padding=ft.padding.all(10),
    )

    _rebuild()

    def _set_iso(iso):
        state["selected_iso"] = iso
        if iso:
            d = _parse_iso(iso)
            if d:
                state["display_year"] = d.year
                state["display_month"] = d.month
        _rebuild()

    panel._get_iso = lambda: state["selected_iso"]
    panel._set_iso = _set_iso
    return panel

def create_russian_date_field_compact(page, value, on_change, hint="Дата", width=110):
    return create_russian_date_field(page, value, on_change, hint=hint, width=width)

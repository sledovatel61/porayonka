# ui/controls/russian_calendar.py
# Custom Russian calendar — replaces ft.DatePicker everywhere in the Controls tab.
# Russian month/day names, week starts Monday, instant click selection (no OK).
# Uses only stdlib: calendar, datetime. No new dependencies.
# Flet 0.23.2 safe: no animate, shadow, gradient, wrap.

import calendar
import datetime
from typing import Callable, Optional

import flet as ft

from .glass_theme import GLASS

# ── Russian names ────────────────────────────────────────────────
_MONTHS_RU = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]
_DAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

calendar.setfirstweekday(calendar.MONDAY)


def _iso_to_date(iso: Optional[str]) -> Optional[datetime.date]:
    if not iso:
        return None
    try:
        return datetime.date.fromisoformat(iso)
    except Exception:
        return None


def _date_to_iso(d: Optional[datetime.date]) -> Optional[str]:
    return d.isoformat() if d else None


# ── Calendar panel builder ──────────────────────────────────────
def _build_calendar_panel(
    value: Optional[str],
    on_select: Callable[[Optional[str]], None],
    close_panel: Callable[[], None],
    today: datetime.date,
) -> ft.Container:
    """Build the inline calendar grid for a given month/year."""

    selected = _iso_to_date(value)
    current = {
        "year": selected.year if selected else today.year,
        "month": selected.month if selected else today.month,
    }
    panel_controls = {"col": None, "header": None}

    def _month_label() -> str:
        return f"{_MONTHS_RU[current['month']]} {current['year']}"

    def _prev_month(e=None):
        if current["month"] == 1:
            current["month"] = 12
            current["year"] -= 1
        else:
            current["month"] -= 1
        _rebuild_grid()

    def _next_month(e=None):
        if current["month"] == 12:
            current["month"] = 1
            current["year"] += 1
        else:
            current["month"] += 1
        _rebuild_grid()

    def _on_day_click(day: int, is_current: bool):
        if not is_current:
            return
        d = datetime.date(current["year"], current["month"], day)
        on_select(_date_to_iso(d))
        close_panel()

    def _go_today(e=None):
        on_select(_date_to_iso(today))
        close_panel()

    def _clear(e=None):
        on_select(None)
        close_panel()

    # Month label
    month_text = ft.Text(_month_label(), size=13, weight=ft.FontWeight.W_700,
                          color=GLASS["text"], no_wrap=True)
    panel_controls["header"] = month_text

    # Day-of-week header row
    dow_row = ft.Row(
        controls=[
            ft.Text(d, size=10, color=GLASS["text_muted"],
                    weight=ft.FontWeight.W_700, width=34, text_align=ft.TextAlign.CENTER,
                    no_wrap=True)
            for d in _DAYS_RU
        ],
        spacing=0, tight=True, alignment=ft.MainAxisAlignment.CENTER,
    )

    # Grid column (6 rows x 7 cells)
    grid_col = ft.Column(spacing=1, tight=True)
    panel_controls["col"] = grid_col

    def _rebuild_grid(e=None):
        month_text.value = _month_label()
        grid_col.controls.clear()
        cal = calendar.monthcalendar(current["year"], current["month"])
        for week in cal:
            row_cells = []
            for day in week:
                if day == 0:
                    row_cells.append(
                        ft.Container(width=34, height=32, border_radius=8)
                    )
                else:
                    is_today = (day == today.day and current["month"] == today.month
                                and current["year"] == today.year)
                    is_selected = (selected and day == selected.day
                                   and current["month"] == selected.month
                                   and current["year"] == selected.year)

                    bg = GLASS["accent"] if is_selected else "transparent"
                    fg = "#ffffff" if is_selected else GLASS["text"]
                    border_today = ft.BorderSide(1, GLASS["accent"]) if (is_today and not is_selected) else None
                    brd = ft.border.all(1, GLASS["accent"]) if (is_today and not is_selected) else None

                    day_num = day
                    cell = ft.Container(
                        content=ft.Text(str(day_num), size=12, color=fg,
                                        weight=ft.FontWeight.W_600 if is_selected else None,
                                        text_align=ft.TextAlign.CENTER),
                        width=34, height=32, border_radius=8,
                        bgcolor=bg,
                        border=brd,
                        alignment=ft.alignment.center,
                        on_click=lambda e, d=day_num: _on_day_click(d, True),
                        on_hover=lambda e, d=day_num, _bg=bg: _hover_cell(e, _bg),
                    )
                    row_cells.append(cell)
            grid_col.controls.append(
                ft.Row(controls=row_cells, spacing=0, tight=True,
                       alignment=ft.MainAxisAlignment.CENTER)
            )
        # Pad to 6 rows
        while len(grid_col.controls) < 6:
            grid_col.controls.append(
                ft.Row(
                    controls=[ft.Container(width=34, height=32)] * 7,
                    spacing=0, tight=True, alignment=ft.MainAxisAlignment.CENTER,
                )
            )
        try:
            grid_col.update()
            month_text.update()
        except Exception:
            pass

    def _hover_cell(e, original_bg):
        """Hover highlight: change bg to semi-white, restore on leave."""
        if e.data == "true":
            e.control.bgcolor = "#ffffff12"
        else:
            e.control.bgcolor = original_bg
        try:
            e.control.update()
        except Exception:
            pass

    _rebuild_grid()

    # Navigation header
    nav_row = ft.Row(
        controls=[
            ft.IconButton(icon=ft.icons.CHEVRON_LEFT, icon_size=18,
                          icon_color=GLASS["text_secondary"],
                          on_click=_prev_month, width=32, height=32, padding=0),
            month_text,
            ft.IconButton(icon=ft.icons.CHEVRON_RIGHT, icon_size=18,
                          icon_color=GLASS["text_secondary"],
                          on_click=_next_month, width=32, height=32, padding=0),
        ],
        spacing=4, tight=True, alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Bottom buttons: Today / Clear
    bottom = ft.Row(
        controls=[
            ft.TextButton("Сегодня", on_click=_go_today,
                          style=ft.ButtonStyle(color=GLASS["accent"], padding=ft.padding.symmetric(horizontal=8))),
            ft.TextButton("Очистить", on_click=_clear,
                          style=ft.ButtonStyle(color=GLASS["text_muted"], padding=ft.padding.symmetric(horizontal=8))),
        ],
        spacing=4, tight=True, alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    panel = ft.Container(
        content=ft.Column(
            controls=[nav_row, dow_row, grid_col, bottom],
            spacing=4, tight=True,
        ),
        width=280,
        bgcolor=GLASS["surface"],
        border=ft.border.all(1, GLASS["border"]),
        border_radius=12,
        padding=ft.padding.all(10),
    )
    return panel


# ── Public API ───────────────────────────────────────────────────
def create_russian_date_field(
    page: ft.Page,
    value: Optional[str],
    on_change: Callable[[Optional[str]], None],
    hint: str = "Дата",
    width: int = 150,
) -> ft.Control:
    """Create a date field with inline Russian calendar.

    Returns a Stack containing the field and a floating calendar panel.
    The panel toggles visible on field click.
    Today's date is highlighted; click selects instantly (no OK/Cancel).
    """
    today = datetime.date.today()
    display_val = ""
    d = _iso_to_date(value)
    if d:
        display_val = d.strftime("%d.%m.%Y")

    show_panel = {"visible": False}
    current_value = {"value": value}

    # The text field showing the date
    field = ft.TextField(
        value=display_val,
        hint_text=hint,
        read_only=True,
        width=width,
        height=40,
        dense=True,
        border_radius=10,
        border_color=GLASS["inset_border"],
        focused_border_color=GLASS["accent"],
        bgcolor=GLASS["inset_bg"],
        color=GLASS["text"],
        hint_style=ft.TextStyle(color=GLASS["text_muted"], size=13),
        text_style=ft.TextStyle(size=13),
        content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
        suffix=ft.Icon(ft.icons.CALENDAR_MONTH, size=16, color=GLASS["accent"]),
    )

    calendar_container = ft.Container(visible=False)

    def _close_panel():
        show_panel["visible"] = False
        calendar_container.visible = False
        try:
            calendar_container.update()
        except Exception:
            pass

    def _on_select(iso: Optional[str]):
        current_value["value"] = iso
        on_change(iso)
        d = _iso_to_date(iso)
        field.value = d.strftime("%d.%m.%Y") if d else ""
        _close_panel()
        try:
            field.update()
        except Exception:
            pass

    def _toggle_panel(e=None):
        show_panel["visible"] = not show_panel["visible"]
        calendar_container.visible = show_panel["visible"]
        if show_panel["visible"]:
            # Rebuild panel with current value
            calendar_container.content = _build_calendar_panel(
                current_value["value"], _on_select, _close_panel, today
            )
        try:
            calendar_container.update()
        except Exception:
            pass

    field.on_click = _toggle_panel

    calendar_container.content = _build_calendar_panel(
        current_value["value"], _on_select, _close_panel, today
    )

    # Return a stack so the calendar floats over other content
    result = ft.Stack(
        controls=[
            ft.Column(controls=[field], spacing=0, tight=True),
            ft.Column(controls=[field, calendar_container], spacing=0, tight=True),
        ],
    )
    # Simplify: just return the column with field + expandable panel
    result = ft.Column(
        controls=[field, calendar_container],
        spacing=0,
        tight=True,
    )

    # Expose value setter for external use
    def _set_value(iso: Optional[str]):
        current_value["value"] = iso
        d = _iso_to_date(iso)
        field.value = d.strftime("%d.%m.%Y") if d else ""
        try:
            field.update()
        except Exception:
            pass

    result._set_value = _set_value
    result._get_value = lambda: current_value["value"]
    return result

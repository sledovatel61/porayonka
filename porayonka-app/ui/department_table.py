import flet as ft
from typing import List, Callable
from core.models import Department, Status
from core.constants import COLORS
from .status_cell import create_status_cell, update_status_cell


def _make_number_badge(dept: Department, index: int) -> ft.Container:
    text = "—" if dept.is_ovd else str(index + 1)
    return ft.Container(
        content=ft.Text(text, size=12, color=COLORS["text_muted"] if dept.is_ovd else COLORS["text_light"],
                        weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
        width=32, height=32,
        bgcolor=COLORS["btn_reset"] if dept.is_ovd else COLORS["primary_light"],
        border_radius=16, alignment=ft.alignment.center,
    )


def _status_colors(dept: Department) -> tuple:
    if dept.status == Status.RECEIVED:
        return COLORS["received"], COLORS["received_bg"]
    if dept.status == Status.IN_PROGRESS:
        return COLORS["in_progress"], COLORS["in_progress_bg"]
    return "#3A3F47", "#202B3B"


def _make_group_header(title: str, group: List[Department]) -> ft.Container:
    active = sum(1 for d in group if d.is_active)
    received = sum(1 for d in group if d.is_active and d.status == Status.RECEIVED)
    ratio = received / active if active else 0
    summary = f"{received} из {active} получено" if active else "нет активных отделов"
    return ft.Container(
        content=ft.Column(controls=[
            ft.Row(controls=[
                ft.Text(title, size=12, weight=ft.FontWeight.BOLD, color=COLORS["text_secondary"]),
                ft.Text(f"{len(group)} отделов · {active} активных", size=11, color=COLORS["text_muted"]),
                ft.Container(expand=True),
                ft.Text(summary, size=11, color=COLORS["received_text"] if received else COLORS["text_muted"]),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.ProgressBar(value=ratio, height=4, bgcolor="#3A3F47",
                           color=COLORS["received"], border_radius=2),
        ], spacing=7, tight=True),
        padding=ft.padding.only(left=12, right=12, top=12, bottom=8),
        bgcolor=COLORS["bg"],
    )


def _make_dept_row(dept: Department, row_index: int, on_status_click: Callable,
                   status_cells: dict) -> ft.Container:
    marker, tint = _status_colors(dept)
    status_cell = create_status_cell(dept, on_status_click)
    status_cell.tooltip = "Клик по статусу — переключить" if dept.is_active else "Отдел отключен"
    status_cell.on_click = lambda e: on_status_click()
    status_cells[dept.id] = status_cell
    row_content = ft.Row(controls=[
        _make_number_badge(dept, row_index),
        ft.Text(dept.name, size=14, color=COLORS["text_muted"] if dept.is_ovd else COLORS["text"],
                italic=dept.is_ovd, overflow=ft.TextOverflow.ELLIPSIS, no_wrap=True),
        status_cell,
        ft.Container(expand=True),
    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)
    row = ft.Container(
        # Физическая статусная полоса надёжнее border в Flet 0.23.2.
        content=ft.Row(controls=[
            ft.Container(width=5, bgcolor=marker),
            ft.Container(content=row_content, expand=True),
        ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.STRETCH),
        # Полноширинная поверхность: тонируется вся строка, а не только текст.
        bgcolor=tint,
        padding=ft.padding.only(right=12, top=8, bottom=8),
        border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
        opacity=1.0 if dept.is_active else 0.45,
    )
    normal_bg = tint
    def on_hover(e: ft.ControlEvent):
        if dept.is_active:
            row.bgcolor = COLORS["card_hover"] if e.data == "true" else normal_bg
            row.update()
    row.on_hover = on_hover
    row.tooltip = "Отдел отключен" if not dept.is_active else "Статус меняется по кнопке справа"
    return row


def create_department_table(page: ft.Page, departments: List[Department],
                            on_status_change: Callable[[Department], None] = None) -> ft.Column:
    status_cells, dept_rows = {}, {}
    rows, all_rows = [], []
    regular = [d for d in departments if not d.is_ovd]
    ovd = [d for d in departments if d.is_ovd]
    groups = [("Следственные отделы", regular), ("ОВД", ovd)]
    number_index = 0

    def handle(dept: Department):
        if not dept.is_active:
            return
        dept.toggle_status()
        update_status_cell(status_cells[dept.id], dept)
        marker, tint = _status_colors(dept)
        row = dept_rows.get(dept.id)
        if row:
            row.bgcolor = tint
            if isinstance(row.content, ft.Row) and row.content.controls:
                row.content.controls[0].bgcolor = marker
            row.update()
        if on_status_change:
            on_status_change(dept)

    for title, group in groups:
        if not group:
            continue
        header = _make_group_header(title, group)
        rows.append(header); all_rows.append(header)
        for dept in group:
            idx = number_index
            if not dept.is_ovd:
                number_index += 1
            row = _make_dept_row(dept, idx, lambda d=dept: handle(d), status_cells)
            dept_rows[dept.id] = row
            rows.append(row); all_rows.append(row)

    rows_column = ft.Column(controls=rows, spacing=0)
    scroll_area = ft.Container(content=rows_column, bgcolor=COLORS["card"],
                               border=ft.border.only(left=ft.BorderSide(1, COLORS["border"]), right=ft.BorderSide(1, COLORS["border"])))
    table_container = ft.Column(controls=[ft.Container(content=ft.Column(controls=[scroll_area], spacing=0),
        border_radius=10, border=ft.border.all(1, COLORS["border"]),
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=12, color="#00000060", offset=ft.Offset(0, 2)))], spacing=0)
    page.status_cells, page.dept_rows = status_cells, dept_rows
    page.rows_column, page.all_departments, page._all_rows = rows_column, departments, all_rows
    page.table_container = table_container
    return table_container


def rebuild_department_table(page: ft.Page, departments: List[Department],
                              on_status_change: Callable[[Department], None] = None) -> None:
    mounted = getattr(page, "table_container", None)
    new = create_department_table(page, departments, on_status_change)
    if mounted is not None:
        mounted.controls = new.controls
        page.table_container = mounted
        mounted.update()
        page.update()


def filter_table(page: ft.Page, query: str) -> None:
    if not hasattr(page, "dept_rows") or not hasattr(page, "all_departments"):
        return
    q = query.strip().lower()
    if not q:
        page.rows_column.controls = page._all_rows
    else:
        matches = [d for d in page.all_departments if q in d.name.lower()]
        controls = []
        for title, group in (("Следственные отделы", [d for d in matches if not d.is_ovd]), ("ОВД", [d for d in matches if d.is_ovd])):
            if group:
                controls.append(_make_group_header(title, group))
                controls.extend(page.dept_rows[d.id] for d in group)
        if not controls:
            controls = [ft.Container(content=ft.Column(controls=[ft.Icon(ft.icons.SEARCH_OFF, size=28, color=COLORS["text_muted"]),
                ft.Text("Отделы не найдены", color=COLORS["text_secondary"], size=14)], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8, tight=True), padding=ft.padding.symmetric(vertical=32), alignment=ft.alignment.center)]
        page.rows_column.controls = controls
    page.rows_column.update()

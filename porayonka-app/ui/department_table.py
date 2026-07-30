# [DARK THEME] Управление отделами вынесено в отдельное модальное окно.
# ui/department_table.py
import flet as ft
from typing import List, Callable, Dict
from core.models import Department
from core.constants import COLORS
from .status_cell import create_status_cell, update_status_cell


def _make_header_row() -> ft.Container:
    """Заголовок таблицы."""
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text("№", size=12, weight=ft.FontWeight.BOLD,
                                    color=COLORS["text_light"]),
                    width=56,
                    alignment=ft.alignment.center,
                ),
                ft.Container(
                    content=ft.Text("СЛЕДСТВЕННЫЙ ОТДЕЛ", size=12,
                                    weight=ft.FontWeight.BOLD, color=COLORS["text_light"]),
                    expand=True,
                    padding=ft.padding.only(left=8),
                ),
                ft.Container(
                    content=ft.Text("СТАТУС", size=12, weight=ft.FontWeight.BOLD,
                                    color=COLORS["text_light"]),
                    width=160,
                    alignment=ft.alignment.center,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
        gradient=ft.LinearGradient(
            begin=ft.alignment.center_left,
            end=ft.alignment.center_right,
            colors=[COLORS["primary"], COLORS["primary_light"]],
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
        border_radius=ft.border_radius.only(top_left=10, top_right=10),
    )


def _make_number_badge(dept: Department, index: int) -> ft.Container:
    """Кружок с номером по текущему порядку в таблице."""
    text  = "—" if dept.is_ovd else str(index + 1)
    bg    = COLORS["btn_reset"] if dept.is_ovd else COLORS["primary_light"]
    color = COLORS["text_muted"] if dept.is_ovd else COLORS["text_light"]
    return ft.Container(
        content=ft.Text(
            text,
            size=12,
            color=color,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        ),
        width=32,
        height=32,
        bgcolor=bg,
        border_radius=16,
        alignment=ft.alignment.center,
    )


def _make_dept_row(
    dept: Department,
    row_index: int,
    on_status_click: Callable,
    status_cells: dict,
) -> ft.Container:
    """Строка таблицы."""
    print(f"[ROW] Создаю строку {dept.id}: {dept.name}")
    row_bg     = COLORS["card"] if row_index % 2 == 0 else COLORS["row_alt"]
    name_color = COLORS["text_muted"] if dept.is_ovd else COLORS["text"]
    opacity    = 1.0 if dept.is_active else 0.45

    status_cell = create_status_cell(dept, on_status_click)
    status_cells[dept.id] = status_cell

    row = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=_make_number_badge(dept, row_index),
                    width=56,
                    alignment=ft.alignment.center,
                ),
                ft.Container(
                    content=ft.Text(
                        dept.name,
                        size=14,
                        color=name_color,
                        italic=dept.is_ovd,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        no_wrap=True,
                    ),
                    expand=True,
                    padding=ft.padding.only(left=8, right=16),
                    alignment=ft.alignment.center_left,
                ),
                status_cell,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
        bgcolor=row_bg,
        padding=ft.padding.only(left=16, right=16),
        border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
        opacity=opacity,
    )

    def on_row_hover(e: ft.ControlEvent):
        if not dept.is_active:
            return
        row.bgcolor = COLORS["card_hover"] if e.data == "true" else row_bg
        row.update()

    row.on_hover = on_row_hover
    row.on_click = lambda e: on_status_click()
    row.tooltip = "Кликните для смены статуса" if dept.is_active else "Отдел отключен"
    return row


def _make_ovd_separator() -> ft.Container:
    return ft.Container(height=4, bgcolor=COLORS["divider"])


def _make_footer(total: int, active: int) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            f"Всего отделов: {total} · активных: {active}",
            size=12,
            color=COLORS["text_muted"],
            text_align=ft.TextAlign.CENTER,
        ),
        alignment=ft.alignment.center,
        padding=ft.padding.symmetric(vertical=12),
        bgcolor=COLORS["card"],
        border_radius=ft.border_radius.only(bottom_left=10, bottom_right=10),
        border=ft.border.only(top=ft.BorderSide(1, COLORS["border"])),
    )


# ─────────────────────────────────────────────────────────────────────────────
# ОСНОВНАЯ ФУНКЦИЯ
# ─────────────────────────────────────────────────────────────────────────────
def create_department_table(
    page: ft.Page,
    departments: List[Department],
    on_status_change: Callable[[Department], None] = None,
) -> ft.Column:
    """Создать таблицу отделов."""
    status_cells: dict = {}
    dept_rows: dict    = {}

    def _handle_status_click(dept: Department) -> None:
        print(f"[DEPT_CLICK] {dept.name} active={dept.is_active}")
        if not dept.is_active:
            print(f"[DEPT_CLICK] blocked (inactive)")
            return
        dept.toggle_status()
        if dept.id in status_cells:
            update_status_cell(status_cells[dept.id], dept)
        if on_status_change:
            on_status_change(dept)

    def make_handler(d: Department) -> Callable:
        def handler():
            _handle_status_click(d)
        return handler

    rows: List[ft.Control] = []
    row_index = 0
    for dept in departments:
        if dept.is_ovd and row_index > 0:
            if not departments[row_index - 1].is_ovd:
                rows.append(_make_ovd_separator())
        dept_row = _make_dept_row(
            dept=dept,
            row_index=row_index,
            on_status_click=make_handler(dept),
            status_cells=status_cells,
        )
        dept_rows[dept.id] = dept_row
        rows.append(dept_row)
        row_index += 1

    print(f"[TABLE] Итого строк: {len(rows)}, отделов: {len(departments)}")

    active_count = sum(1 for d in departments if d.is_active)

    # Вертикальный скролл принадлежит корню вкладки (main.py).
    rows_column = ft.Column(
        controls=rows,
        spacing=0,
    )

    scroll_area = ft.Container(
        content=rows_column,
        bgcolor=COLORS["card"],
        border=ft.border.only(
            left=ft.BorderSide(1, COLORS["border"]),
            right=ft.BorderSide(1, COLORS["border"]),
        ),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )

    table_container = ft.Column(
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        _make_header_row(),
                        scroll_area,
                        _make_footer(len(departments), active_count),
                    ],
                    spacing=0,
                    tight=False,
                ),
                border_radius=10,
                border=ft.border.all(1, COLORS["border"]),
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=12,
                    color="#00000060",
                    offset=ft.Offset(0, 2),
                ),
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            ),
        ],
        spacing=0,
    )

    page.status_cells    = status_cells
    page.dept_rows       = dept_rows
    page.rows_column     = rows_column
    page.all_departments = departments
    page._all_rows       = list(rows)
    page.table_container = table_container
    return table_container


def rebuild_department_table(page: ft.Page,
                             departments: List[Department],
                             on_status_change: Callable[[Department], None] = None) -> None:
    """Полностью перестроить таблицу отделов.

    Важно: create_department_table возвращает новый Column и записывает его в
    page.table_container. Если просто подменить controls, page.table_container
    начнёт ссылаться на отсоединённый виджет, и последующие обновления таблицы
    не будут отображаться. Поэтому после подмены controls восстанавливаем ссылку
    на видимый (смонтированный) контейнер.
    """
    mounted_container = getattr(page, "table_container", None)
    new_table = create_department_table(page, departments, on_status_change)
    if mounted_container is not None:
        mounted_container.controls = new_table.controls
        page.table_container = mounted_container
        try:
            mounted_container.update()
        except Exception:
            pass
        try:
            page.update()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# ФИЛЬТРАЦИЯ
# ─────────────────────────────────────────────────────────────────────────────
def filter_table(page: ft.Page, query: str) -> None:
    """Фильтровать строки по названию."""
    if not hasattr(page, "dept_rows") or not hasattr(page, "all_departments"):
        return
    query_lower  = query.strip().lower()
    departments: List[Department] = page.all_departments
    dept_rows: dict = page.dept_rows

    if not query_lower:
        if hasattr(page, "rows_column") and hasattr(page, "_all_rows"):
            page.rows_column.controls = page._all_rows
            page.rows_column.update()
        return

    filtered = [
        dept_rows[dept.id]
        for dept in departments
        if query_lower in dept.name.lower() and dept.id in dept_rows
    ]
    if hasattr(page, "rows_column"):
        page.rows_column.controls = filtered
        page.rows_column.update()

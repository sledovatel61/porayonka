# [DARK THEME] Обновлено только визуально, логика сохранена.
# ui/status_cell.py
import flet as ft
from core.models import Department, Status
from core.constants import COLORS

# ── Конфигурация статусов ────────────────────────────────────────
_STATUS_CONFIG = {
    Status.RECEIVED: {
        "label":      "Получено",
        "icon":       ft.icons.CHECK,
        "icon_bg":    COLORS["received"],
        "bg":         COLORS["received_bg"],
        "hover_bg":   COLORS["received_hover"],
        "text_color": COLORS["received_text"],
        "icon_color": COLORS["text_light"],
    },
    Status.IN_PROGRESS: {
        "label":      "В работе",
        "icon":       ft.icons.REFRESH,
        "icon_bg":    COLORS["in_progress"],
        "bg":         COLORS["in_progress_bg"],
        "hover_bg":   COLORS["in_progress_hover"],
        "text_color": COLORS["in_progress_text"],
        "icon_color": COLORS["text_light"],
    },
    Status.EMPTY: {
        "label":      "Не получено",
        "icon":       ft.icons.RADIO_BUTTON_UNCHECKED,
        "icon_bg":    COLORS["empty"],
        "bg":         COLORS["empty_bg"],
        "hover_bg":   COLORS["empty_hover"],
        "text_color": COLORS["text_secondary"],
        "icon_color": COLORS["text_light"],
    },
}


def create_status_cell(
    dept: Department,
    on_click_callback,
) -> ft.Container:
    """
    Создать ячейку статуса с красивым дизайном.
    """
    print(f"[CELL] Создаю ячейку для '{dept.name}', статус={dept.status}")
    cfg = _STATUS_CONFIG[dept.status]

    icon_widget = ft.Container(
        content=ft.Text(
            cfg["icon"],
            size=12,
            color=cfg["icon_color"],
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        ),
        width=22,
        height=22,
        bgcolor=cfg["icon_bg"],
        border_radius=11,
        alignment=ft.alignment.center,
    )

    label_widget = ft.Text(
        value=cfg["label"],
        size=12,
        color=cfg["text_color"],
        weight=ft.FontWeight.W_500,
        no_wrap=True,
    )

    inner_row = ft.Row(
        controls=[icon_widget, label_widget],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        tight=True,
    )

    cell = ft.Container(
        content=inner_row,
        bgcolor=cfg["bg"],
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=7),
        alignment=ft.alignment.center,
        width=160,
        height=36,
        animate=ft.animation.Animation(150, ft.AnimationCurve.EASE_IN_OUT),
        on_click=lambda e: _handle_click(e, dept, on_click_callback),
        on_hover=lambda e: _handle_hover(e, cell, cfg["bg"], cfg["hover_bg"]),
        tooltip="Кликните для смены статуса",
    )
    return cell


def _handle_click(e, dept: Department, callback):
    """Обработчик клика — вызывает callback."""
    print(f"[CLICK] '{dept.name}' | {dept.status} → клик!")
    callback()


def _handle_hover(e, cell: ft.Container, normal_bg: str, hover_bg: str):
    """Hover-эффект через смену bgcolor."""
    cell.bgcolor = hover_bg if e.data == "true" else normal_bg
    cell.update()


def update_status_cell(cell: ft.Container, dept: Department) -> None:
    """
    Обновить ячейку после смены статуса.
    """
    print(f"[UPDATE_CELL] '{dept.name}' → {dept.status}")
    cfg = _STATUS_CONFIG[dept.status]

    cell.bgcolor  = cfg["bg"]
    cell.on_hover = lambda e: _handle_hover(e, cell, cfg["bg"], cfg["hover_bg"])

    inner_row = cell.content
    if not isinstance(inner_row, ft.Row) or len(inner_row.controls) < 2:
        print(f"[UPDATE_CELL] [WARN] Неожиданная структура cell.content: {type(inner_row)}")
        cell.update()
        return

    icon_container = inner_row.controls[0]
    if isinstance(icon_container, ft.Container):
        icon_container.bgcolor = cfg["icon_bg"]
        if isinstance(icon_container.content, ft.Text):
            icon_container.content.value = cfg["icon"]
            icon_container.content.color = cfg["icon_color"]

    label_widget = inner_row.controls[1]
    if isinstance(label_widget, ft.Text):
        label_widget.value = cfg["label"]
        label_widget.color = cfg["text_color"]

    cell.update()
    print(f"[UPDATE_CELL] [OK] Ячейка обновлена для '{dept.name}'")
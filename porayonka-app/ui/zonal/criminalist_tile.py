# ui/zonal/criminalist_tile.py
# Компактная плашка криминалиста для сетки (Фаза 2).
#   ФИО, статус активности, закрепленные отделы (кратко), прогресс заполнения.
# Клик по плашке открывает форму; кнопки — редактирование/удаление.
# [DARK THEME] + ft.icons.* + hint_style (Flet 0.23.2)
import flet as ft
from core.zonal_data import get_criminalist_fill
from core.constants import COLORS


_TILE_HEIGHT = 95


def _truncate(text: str, limit: int = 40) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _safe_stop(e):
    try:
        e.stop_propagation()
    except Exception:
        pass


def _build_tile_content(criminalist, collection, dept_map: dict, callbacks: dict):
    """Внутреннее содержимое плашки (для обновления без перерисовки всей сетки)."""

    # ── ФИО + чип активности ──
    name_text = ft.Text(
        criminalist.full_name,
        size=13,
        weight=ft.FontWeight.BOLD,
        color=COLORS["text"],
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

    if criminalist.is_active:
        chip_text = "Участвует"
        chip_color = COLORS.get("received_text", "#22c55e")
        chip_bg = COLORS.get("received_bg", "#14532d")
        chip_icon = ft.icons.CHECK_CIRCLE
    else:
        chip_text = "Не участвует"
        chip_color = COLORS.get("text_muted", "#64748b")
        chip_bg = COLORS.get("empty_bg", "#1e293b")
        chip_icon = ft.icons.CANCEL

    chip = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(chip_icon, size=10, color=chip_color),
                ft.Text(chip_text, size=9, color=chip_color, weight=ft.FontWeight.W_500),
            ],
            spacing=2,
        ),
        bgcolor=chip_bg,
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=5, vertical=1),
        ink=True,
        on_click=lambda e: (_safe_stop(e), callbacks["on_toggle_active"](criminalist)),
        tooltip="Участвует в сборе (нажмите для отключения)" if criminalist.is_active else "Не участвует (нажмите для включения)",
    )

    # ── Закрепленные отделы ──
    zone_names = [dept_map.get(did, f"Отдел {did}") for did in criminalist.zone.department_ids]
    if zone_names:
        full_zone_text = ", ".join(zone_names)
        zone_text = _truncate(full_zone_text, 42)
    else:
        full_zone_text = "Нет закрепленных отделов"
        zone_text = full_zone_text

    zone_row = ft.Row(
        controls=[
            ft.Icon(ft.icons.LOCATION_ON, size=10, color=COLORS.get("text_muted", "#64748b")),
            ft.Text(
                zone_text,
                size=10,
                color=COLORS.get("text_secondary", "#94a3b8"),
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
        ],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ── Прогресс ──
    fill = get_criminalist_fill(collection, criminalist)
    pct = fill["percent"]
    if pct >= 100:
        bar_color = COLORS.get("received", "#22c55e")
        pct_color = COLORS.get("received_text", "#22c55e")
    elif pct > 0:
        bar_color = COLORS.get("in_progress", "#f59e0b")
        pct_color = COLORS.get("in_progress_text", "#f59e0b")
    else:
        bar_color = COLORS.get("empty", "#64748b")
        pct_color = COLORS.get("text_muted", "#64748b")

    progress_bar = ft.ProgressBar(
        value=pct / 100.0,
        height=5,
        color=bar_color,
        bgcolor=COLORS.get("border", "#334155"),
        border_radius=3,
    )
    progress_label = ft.Text(
        f"{pct}%",
        size=10,
        color=pct_color,
        weight=ft.FontWeight.W_500,
    )
    progress_row = ft.Row(
        controls=[progress_bar, progress_label],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ── Кнопки (справа) ──
    edit_btn = ft.IconButton(
        icon=ft.icons.EDIT_OUTLINED,
        icon_size=16,
        icon_color=COLORS.get("btn_save", "#3b82f6"),
        tooltip="Редактировать",
        on_click=lambda e: (_safe_stop(e), callbacks["on_edit"](criminalist)),
        style=ft.ButtonStyle(padding=ft.padding.all(2)),
    )
    delete_btn = ft.IconButton(
        icon=ft.icons.DELETE_OUTLINE,
        icon_size=16,
        icon_color="#ef4444",
        tooltip="Удалить",
        on_click=lambda e: (_safe_stop(e), callbacks["on_delete"](criminalist)),
        style=ft.ButtonStyle(padding=ft.padding.all(2)),
    )

    actions_col = ft.Column(
        controls=[edit_btn, delete_btn],
        spacing=2,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Левая колонка: ФИО+чип, отделы, прогресс
    left_col = ft.Column(
        controls=[
            ft.Row(controls=[name_text, chip], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            zone_row,
            progress_row,
        ],
        spacing=4,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    # Итоговый Row без expand — фиксированные размеры задаёт внешний Container
    return ft.Row(
        controls=[left_col, actions_col],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def create_criminalist_tile(
    criminalist,
    collection,
    dept_map: dict,
    callbacks: dict,
) -> ft.Container:
    """
    Создать плашку криминалиста.
    Возвращает ft.Container фиксированного размера, клик по которому открывает форму.
    """
    print(f"[TILE] Creating tile: {criminalist.id}")

    tile = ft.Container(
        content=_build_tile_content(criminalist, collection, dept_map, callbacks),
        height=_TILE_HEIGHT,
        alignment=ft.alignment.center_left,
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        bgcolor=COLORS.get("card", "#15202e"),
        border=ft.border.all(1, COLORS.get("border", "#334155")),
        border_radius=10,
        ink=True,
        on_click=lambda e: callbacks["on_open_form"](criminalist),
        tooltip="Нажмите для заполнения формы",
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=4,
            color="#00000040",
            offset=ft.Offset(0, 1),
        ),
        animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )
    tile.opacity = 1.0 if criminalist.is_active else 0.5
    return tile


def rebuild_tile_content(tile: ft.Container, criminalist, collection, dept_map: dict, callbacks: dict):
    """Обновить содержимое существующей плашки без перерисовки всей сетки."""
    tile.content = _build_tile_content(criminalist, collection, dept_map, callbacks)
    tile.opacity = 1.0 if criminalist.is_active else 0.5
    try:
        tile.update()
    except Exception:
        pass

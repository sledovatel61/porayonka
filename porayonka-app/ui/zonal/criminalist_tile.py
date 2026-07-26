# ui/zonal/criminalist_tile.py
# Компактная плашка криминалиста для сетки (Фаза 2).
#   ФИО, статус активности, закрепленные отделы (кратко), прогресс заполнения.
# Клик по плашке открывает форму; кнопки — редактирование/удаление.
# [DARK THEME] + ft.icons.* + hint_style (Flet 0.23.2)
import flet as ft
from core.zonal_data import get_criminalist_fill
from core.constants import COLORS


# Адаптивная раскладка ResponsiveRow: 4 в ряд на широких, 3 на средних, 2 на узких.
_TILE_COL = {"sm": 6, "md": 4, "lg": 3, "xl": 3}


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

    # ── ФИО ──
    name_text = ft.Text(
        criminalist.full_name,
        size=13,
        weight=ft.FontWeight.BOLD,
        color=COLORS["text"],
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
        expand=True,
    )

    # Чип активности (быстрый переключатель is_active)
    if criminalist.is_active:
        chip = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.icons.CHECK_CIRCLE, size=11, color=COLORS["received_text"]),
                    ft.Text("Участвует", size=10, color=COLORS["received_text"],
                            weight=ft.FontWeight.W_500),
                ],
                spacing=2,
            ),
            bgcolor=COLORS["received_bg"],
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=6, vertical=2),
            ink=True,
            on_click=lambda e: (_safe_stop(e), callbacks["on_toggle_active"](criminalist)),
            tooltip="Участвует в сборе (нажмите для отключения)",
        )
    else:
        chip = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.icons.CANCEL, size=11, color=COLORS["text_muted"]),
                    ft.Text("Не участвует", size=10, color=COLORS["text_muted"],
                            weight=ft.FontWeight.W_500),
                ],
                spacing=2,
            ),
            bgcolor=COLORS["empty_bg"],
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=6, vertical=2),
            ink=True,
            on_click=lambda e: (_safe_stop(e), callbacks["on_toggle_active"](criminalist)),
            tooltip="Не участвует в сборе (нажмите для включения)",
        )

    # ── Закрепленные отделы (обрезать многоточием, tooltip — полный список) ──
    zone_names = [dept_map.get(did, f"Отдел {did}") for did in criminalist.zone.department_ids]
    if zone_names:
        full_zone_text = ", ".join(zone_names)
        zone_text = _truncate(full_zone_text, 45)
    else:
        full_zone_text = "Нет закрепленных отделов"
        zone_text = full_zone_text

    zone_row = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.icons.LOCATION_ON, size=11, color=COLORS["text_muted"]),
                ft.Text(
                    zone_text,
                    size=10,
                    color=COLORS["text_secondary"],
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    expand=True,
                ),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        tooltip=full_zone_text if len(full_zone_text) > 45 else None,
    )

    # ── Прогресс ──
    fill = get_criminalist_fill(collection, criminalist)
    pct = fill["percent"]
    if pct >= 100:
        bar_color = COLORS["received"]
        pct_color = COLORS["received_text"]
    elif pct > 0:
        bar_color = COLORS["in_progress"]
        pct_color = COLORS["in_progress_text"]
    else:
        bar_color = COLORS["empty"]
        pct_color = COLORS["text_muted"]

    progress_bar = ft.ProgressBar(
        value=pct / 100.0,
        height=6,
        color=bar_color,
        bgcolor=COLORS["border"],
        border_radius=3,
        expand=True,
    )
    progress_label = ft.Text(
        f"{pct}% ({fill['filled_items']}/{fill['total_items']})",
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
        icon_color=COLORS["btn_save"],
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

    actions_row = ft.Row(
        controls=[edit_btn, delete_btn],
        spacing=2,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Левая часть
    left_col = ft.Column(
        controls=[
            ft.Row(
                controls=[name_text, chip],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            zone_row,
            progress_row,
        ],
        spacing=4,
    )

    # Итоговый Row
    main_row = ft.Row(
        controls=[left_col, actions_row],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    return main_row


def create_criminalist_tile(
    criminalist,
    collection,
    dept_map: dict,
    callbacks: dict,
) -> ft.Container:
    """
    Создать плашку криминалиста.
    Возвращает ft.Container (с col для ResponsiveRow), клик по которому открывает форму.
    """
    print(f"[TILE] Creating tile: {criminalist.id}")

    tile = ft.Container(
        content=_build_tile_content(criminalist, collection, dept_map, callbacks),
        col=_TILE_COL,
        height=95,
        expand=False,
        alignment=ft.alignment.top_left,
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        bgcolor=COLORS["card"],
        border=ft.border.all(1, COLORS["border"]),
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
    # Неактивные — приглушены
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

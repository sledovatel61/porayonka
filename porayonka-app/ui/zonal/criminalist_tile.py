# ui/zonal/criminalist_tile.py
# Квадратная плашка криминалиста для сетки (Фаза 2).
# Вместо раскрывающейся карточки — компактная плашка:
#   ФИО, чип активности, закреплённые отделы, прогресс заполнения.
# Клик по плашке открывает форму; кнопки — редактирование/удаление/активность.
# [DARK THEME] + ft.icons.* + hint_style (Flet 0.23.2)
import flet as ft
from core.zonal_data import get_criminalist_fill
from core.constants import COLORS


# Адаптивная раскладка ResponsiveRow: 4 в ряд на широких, 3 на средних, 2 на узких.
_TILE_COL = {"sm": 6, "md": 4, "lg": 3, "xl": 3}


def _truncate(text: str, limit: int = 48) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _safe_stop(e):
    try:
        e.stop_propagation()
    except Exception:
        pass


def _build_tile_content(criminalist, collection, dept_map: dict, callbacks: dict) -> ft.Column:
    """Внутреннее содержимое плашки (для обновления без перерисовки всей сетки)."""

    # ── Заголовок: ФИО + чип активности ────────────────────────
    name_text = ft.Text(
        criminalist.full_name,
        size=14,
        weight=ft.FontWeight.W_600,
        color=COLORS["text"],
        expand=True,
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

    # Чип активности (быстрый переключатель is_active)
    if criminalist.is_active:
        chip = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.icons.CHECK_CIRCLE, size=13, color=COLORS["received_text"]),
                    ft.Text("Участвует", size=11, color=COLORS["received_text"],
                            weight=ft.FontWeight.W_500),
                ],
                spacing=4,
            ),
            bgcolor=COLORS["received_bg"],
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
            ink=True,
            on_click=lambda e: (_safe_stop(e), callbacks["on_toggle_active"](criminalist)),
            tooltip="Участвует в сборе (нажмите для отключения)",
        )
    else:
        chip = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.icons.CANCEL, size=13, color=COLORS["text_muted"]),
                    ft.Text("Не участвует", size=11, color=COLORS["text_muted"],
                            weight=ft.FontWeight.W_500),
                ],
                spacing=4,
            ),
            bgcolor=COLORS["empty_bg"],
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
            ink=True,
            on_click=lambda e: (_safe_stop(e), callbacks["on_toggle_active"](criminalist)),
            tooltip="Не участвует в сборе (нажмите для включения)",
        )

    header = ft.Row(
        controls=[name_text, chip],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.START,
        alignment=ft.MainAxisAlignment.START,
    )

    # ── Примечание ─────────────────────────────────────────────
    note_controls = []
    if criminalist.note:
        note_controls.append(
            ft.Text(
                criminalist.note,
                size=11,
                color=COLORS["text_secondary"],
                italic=True,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
        )

    # ── Закреплённые отделы (обрезать многоточием, tooltip — полный список) ──
    zone_names = [dept_map.get(did, f"Отдел {did}") for did in criminalist.zone.department_ids]
    if zone_names:
        full_zone_text = ", ".join(zone_names)
        zone_text = _truncate(full_zone_text, 48)
    else:
        full_zone_text = "Нет закреплённых отделов"
        zone_text = full_zone_text

    zone_row = ft.Row(
        controls=[
            ft.Icon(ft.icons.LOCATION_ON, size=12, color=COLORS["text_muted"]),
            ft.Text(
                zone_text,
                size=11,
                color=COLORS["text_secondary"],
                expand=True,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    # ── Индикатор заполненности ────────────────────────────────
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
        height=8,
        color=bar_color,
        bgcolor=COLORS["border"],
        border_radius=4,
        expand=True,
    )
    progress_label = ft.Text(
        f"{pct}%  ({fill['filled_items']}/{fill['total_items']})",
        size=11,
        color=pct_color,
        weight=ft.FontWeight.W_500,
    )
    progress_block = ft.Column(
        controls=[
            ft.Row(
                controls=[progress_bar, progress_label],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        spacing=4,
    )

    # ── Нижняя панель кнопок ───────────────────────────────────
    edit_btn = ft.IconButton(
        icon=ft.icons.EDIT,
        icon_size=18,
        icon_color=COLORS["btn_save"],
        tooltip="Редактировать криминалиста и зоны",
        on_click=lambda e: (_safe_stop(e), callbacks["on_edit"](criminalist)),
        style=ft.ButtonStyle(padding=ft.padding.all(4)),
    )
    delete_btn = ft.IconButton(
        icon=ft.icons.DELETE_OUTLINE,
        icon_size=18,
        icon_color="#f87171",
        tooltip="Удалить криминалиста",
        on_click=lambda e: (_safe_stop(e), callbacks["on_delete"](criminalist)),
        style=ft.ButtonStyle(padding=ft.padding.all(4)),
    )
    open_btn = ft.IconButton(
        icon=ft.icons.OPEN_IN_NEW,
        icon_size=18,
        icon_color=COLORS["text_secondary"],
        tooltip="Открыть форму для заполнения",
        on_click=lambda e: (_safe_stop(e), callbacks["on_open_form"](criminalist)),
        style=ft.ButtonStyle(padding=ft.padding.all(4)),
    )
    bottom_row = ft.Row(
        controls=[edit_btn, delete_btn, ft.Container(expand=True), open_btn],
        spacing=2,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ── Сборка колонки ─────────────────────────────────────────
    body = ft.Column(
        controls=[
            header,
            *note_controls,
            ft.Container(height=6),
            zone_row,
            ft.Container(expand=True),  # растягиваем, чтобы кнопки были внизу
            progress_block,
            ft.Container(height=6),
            bottom_row,
        ],
        spacing=4,
        expand=True,
    )

    return body


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
    print(f"[TILE] Sozdayu plashku: {criminalist.full_name}")

    tile = ft.Container(
        content=_build_tile_content(criminalist, collection, dept_map, callbacks),
        col=_TILE_COL,
        height=224,
        padding=ft.padding.all(14),
        bgcolor=COLORS["card"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=12,
        ink=True,
        on_click=lambda e: callbacks["on_open_form"](criminalist),
        tooltip="Нажмите для заполнения формы",
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=6,
            color="#00000060",
            offset=ft.Offset(0, 2),
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

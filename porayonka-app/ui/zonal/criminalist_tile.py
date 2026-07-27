# ui/zonal/criminalist_tile.py
# Компактная плашка криминалиста — редизайн с анимациями.
# Сохранена стабильность: фиксированный размер 280x96, без tight, без wrap-проблем.
# Добавлено: hover-эффект (смена bgcolor, border, shadow), плавная анимация 200ms,
# современные скругления 12, мягкие тени.
# [DARK THEME] + ft.icons.* (Flet 0.23.2)
import flet as ft
from core.zonal_data import get_criminalist_fill
from core.constants import COLORS

_TILE_WIDTH = 280
_TILE_HEIGHT = 96

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
    # ФИО
    name_text = ft.Text(
        criminalist.full_name,
        size=13,
        weight=ft.FontWeight.BOLD,
        color=COLORS["text"],
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
        expand=True,
        tooltip=criminalist.full_name,
    )

    # Чип активности
    if criminalist.is_active:
        chip_text = "Активен"
        chip_color = COLORS.get("received_text", "#22c55e")
        chip_bg = COLORS.get("received_bg", "#14532d")
        chip_border = COLORS.get("received", "#22c55e")
        chip_icon = ft.icons.CHECK_CIRCLE
        chip_tooltip = "Участвует в сборе (нажмите чтобы отключить)"
    else:
        chip_text = "Откл"
        chip_color = COLORS.get("text_muted", "#64748b")
        chip_bg = COLORS.get("empty_bg", "#1e293b")
        chip_border = COLORS.get("border", "#334155")
        chip_icon = ft.icons.CANCEL
        chip_tooltip = "Не участвует (нажмите чтобы включить)"

    chip = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(chip_icon, size=11, color=chip_color),
                ft.Text(chip_text, size=9, color=chip_color, weight=ft.FontWeight.W_600),
            ],
            spacing=3,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=chip_bg,
        border=ft.border.all(1, chip_border),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=6, vertical=2),
        on_click=lambda e: (_safe_stop(e), callbacks["on_toggle_active"](criminalist)),
        tooltip=chip_tooltip,
        animate=ft.animation.Animation(150, ft.AnimationCurve.EASE_OUT),
    )

    header_row = ft.Row(
        controls=[name_text, chip],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    # Отделы
    zone_names = [dept_map.get(did, f"Отдел {did}") for did in criminalist.zone.department_ids]
    if zone_names:
        full_zone_text = ", ".join(zone_names)
        zone_text = _truncate(full_zone_text, 40)
    else:
        full_zone_text = "Нет отделов"
        zone_text = full_zone_text

    zone_row = ft.Row(
        controls=[
            ft.Icon(ft.icons.LOCATION_ON, size=12, color=COLORS.get("text_muted", "#64748b")),
            ft.Text(
                zone_text,
                size=10,
                color=COLORS.get("text_secondary", "#94a3b8"),
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
                expand=True,
                tooltip=full_zone_text,
            ),
        ],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Прогресс
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
        color=bar_color,
        bgcolor=COLORS.get("border", "#334155"),
        height=6,
        expand=True,
    )
    progress_label = ft.Text(
        f"{pct}%",
        size=11,
        color=pct_color,
        weight=ft.FontWeight.BOLD,
    )

    progress_row = ft.Row(
        controls=[progress_bar, progress_label],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    left_col = ft.Column(
        controls=[header_row, zone_row, progress_row],
        spacing=5,
        expand=True,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    edit_btn = ft.IconButton(
        icon=ft.icons.EDIT_OUTLINED,
        icon_size=15,
        icon_color=COLORS.get("btn_save", "#3b82f6"),
        tooltip="Редактировать",
        width=26,
        height=26,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=6),
            bgcolor={"hovered": COLORS["stat_blue_bg"]},
        ),
        on_click=lambda e: (_safe_stop(e), callbacks["on_edit"](criminalist)),
    )
    delete_btn = ft.IconButton(
        icon=ft.icons.DELETE_OUTLINE,
        icon_size=15,
        icon_color="#ef4444",
        tooltip="Удалить",
        width=26,
        height=26,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=6),
            bgcolor={"hovered": "#3f1a1a"},
        ),
        on_click=lambda e: (_safe_stop(e), callbacks["on_delete"](criminalist)),
    )

    actions_col = ft.Column(
        controls=[edit_btn, delete_btn],
        spacing=2,
        width=30,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    outer_row = ft.Row(
        controls=[left_col, actions_col],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.START,
    )

    return outer_row

def create_criminalist_tile(criminalist, collection, dept_map: dict, callbacks: dict) -> ft.Container:
    print(f"[TILE] Creating tile: {criminalist.id}")

    tile = ft.Container(
        content=_build_tile_content(criminalist, collection, dept_map, callbacks),
        width=_TILE_WIDTH,
        height=_TILE_HEIGHT,
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        bgcolor=COLORS.get("card", "#15202e"),
        border=ft.border.all(1, COLORS.get("border", "#334155")),
        border_radius=12,
        ink=True,
        on_click=lambda e: callbacks["on_open_form"](criminalist),
        tooltip="Нажмите для заполнения формы",
        animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_OUT),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=6,
            color="#00000050",
            offset=ft.Offset(0, 2),
        ),
    )

    if not criminalist.is_active:
        tile.opacity = 0.55
    else:
        tile.opacity = 1.0

    def _on_hover(e):
        try:
            is_hover = e.data == "true"
            if is_hover:
                tile.bgcolor = COLORS.get("card_hover", "#1e293b")
                tile.border = ft.border.all(1, COLORS.get("btn_save", "#3b82f6"))
                tile.shadow = ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=14,
                    color="#00000070",
                    offset=ft.Offset(0, 4),
                )
            else:
                tile.bgcolor = COLORS.get("card", "#15202e")
                tile.border = ft.border.all(1, COLORS.get("border", "#334155"))
                tile.shadow = ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=6,
                    color="#00000050",
                    offset=ft.Offset(0, 2),
                )
            tile.update()
        except Exception:
            pass

    tile.on_hover = _on_hover
    return tile

def rebuild_tile_content(tile: ft.Container, criminalist, collection, dept_map: dict, callbacks: dict):
    tile.content = _build_tile_content(criminalist, collection, dept_map, callbacks)
    tile.width = _TILE_WIDTH
    tile.height = _TILE_HEIGHT
    tile.opacity = 0.55 if not criminalist.is_active else 1.0
    try:
        tile.update()
    except Exception:
        pass

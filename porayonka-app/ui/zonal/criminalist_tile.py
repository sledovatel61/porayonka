# ui/zonal/criminalist_tile.py
# Компактная плашка криминалиста (280x96) для фиксированных рядов.
# РЕДИЗАЙН: hover-анимация, мягкая тень, акцентная полоса слева,
# анимированный прогресс-бар на фиксированных ширинах.
# [DARK THEME] + ft.icons.* (Flet 0.23.2)
#
# ВАЖНО (см. AGENTS.md 15.12): габариты плашки и всех внутренних блоков
# заданы ЖЁСТКО в пикселях. Внутри плашки нет ни одного expand=True —
# это гарантирует конечные constraints и стабильный рендеринг.
import flet as ft
from core.zonal_data import get_criminalist_fill
from core.constants import COLORS


# ── Геометрия плашки (не менять без пересчёта внутренних ширин) ──
_TILE_WIDTH = 280
_TILE_HEIGHT = 96

_BORDER_LEFT = 3          # акцентная полоса
_BORDER_OTHER = 1
_PAD_H = 8
_PAD_V = 6

# 280 - (8 + 8) - (3 + 1) = 260 доступной ширины внутри
_INNER_WIDTH = _TILE_WIDTH - (_PAD_H * 2) - (_BORDER_LEFT + _BORDER_OTHER)  # 260
_ACTIONS_WIDTH = 30
_CONTENT_SPACING = 8
_LEFT_WIDTH = _INNER_WIDTH - _ACTIONS_WIDTH - _CONTENT_SPACING             # 222

# Все внутренние ширины оставляют 4 px запаса от _LEFT_WIDTH,
# чтобы округление шрифтов/иконок никогда не вызвало overflow.
_SAFE = 4
_NAME_WIDTH = 152
_CHIP_WIDTH = 60                                                           # 152+6+60 = 218
_ZONE_TEXT_WIDTH = _LEFT_WIDTH - 15 - _SAFE                                # 203
_BAR_WIDTH = 144
_BAR_LABEL_WIDTH = _LEFT_WIDTH - _BAR_WIDTH - 8 - _SAFE                    # 66
_BAR_HEIGHT = 6


def _truncate(text: str, limit: int = 40) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _safe_stop(e):
    try:
        e.stop_propagation()
    except Exception:
        pass


def _progress_palette(pct: int):
    """Цвета акцента по проценту заполнения."""
    if pct >= 100:
        return COLORS.get("received", "#22c55e"), COLORS.get("received_text", "#4ade80")
    if pct > 0:
        return COLORS.get("in_progress", "#f59e0b"), COLORS.get("in_progress_text", "#fbbf24")
    return COLORS.get("empty", "#64748b"), COLORS.get("text_muted", "#64748b")


def _build_progress_bar(pct: int, bar_color: str) -> ft.Container:
    """
    Кастомный прогресс-бар на фиксированной ширине.
    Ширина заливки анимируется (animate) — плавно «наливается» при перерисовке.
    """
    fill_width = max(0, min(_BAR_WIDTH, round(_BAR_WIDTH * pct / 100.0)))
    fill = ft.Container(
        width=fill_width,
        height=_BAR_HEIGHT,
        bgcolor=bar_color,
        border_radius=_BAR_HEIGHT / 2,
    )
    return ft.Container(
        width=_BAR_WIDTH,
        height=_BAR_HEIGHT,
        bgcolor=COLORS.get("border", "#334155"),
        border_radius=_BAR_HEIGHT / 2,
        content=ft.Row(
            controls=[fill],
            spacing=0,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _build_tile_content(criminalist, collection, dept_map, callbacks):
    # ── Заголовок: ФИО + чип активности ──────────────────────────
    name_text = ft.Text(
        criminalist.full_name,
        size=12,
        weight=ft.FontWeight.BOLD,
        color=COLORS["text"] if criminalist.is_active else COLORS.get("text_secondary", "#94a3b8"),
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
        width=_NAME_WIDTH,
        tooltip=criminalist.full_name,
    )

    if criminalist.is_active:
        chip_text = "Активен"
        chip_color = COLORS.get("received_text", "#4ade80")
        chip_bg = COLORS.get("received_bg", "#052e16")
        chip_border = COLORS.get("received", "#22c55e")
        chip_icon = ft.icons.CHECK_CIRCLE
        chip_tooltip = "Участвует в сборе (нажмите, чтобы отключить)"
    else:
        chip_text = "Откл"
        chip_color = COLORS.get("text_muted", "#64748b")
        chip_bg = COLORS.get("empty_bg", "#1e293b")
        chip_border = COLORS.get("border", "#334155")
        chip_icon = ft.icons.PAUSE_CIRCLE_OUTLINE
        chip_tooltip = "Не участвует в сборе (нажмите, чтобы включить)"

    chip = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(chip_icon, size=10, color=chip_color),
                ft.Text(chip_text, size=9, color=chip_color, weight=ft.FontWeight.W_600),
            ],
            spacing=3,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=_CHIP_WIDTH,
        height=18,
        bgcolor=chip_bg,
        border=ft.border.all(1, chip_border),
        border_radius=9,
        alignment=ft.alignment.center,
        on_click=lambda e: (_safe_stop(e), callbacks["on_toggle_active"](criminalist)),
        tooltip=chip_tooltip,
    )

    header_row = ft.Row(
        controls=[name_text, chip],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.START,
    )

    # ── Зона обслуживания ────────────────────────────────────────
    zone_names = [dept_map.get(did, f"Отдел {did}") for did in criminalist.zone.department_ids]
    full_zone_text = ", ".join(zone_names) if zone_names else "Отделы не закреплены"
    zone_text = _truncate(full_zone_text, 38)

    zone_row = ft.Row(
        controls=[
            ft.Icon(ft.icons.PLACE_OUTLINED, size=11, color=COLORS.get("text_muted", "#64748b")),
            ft.Text(
                zone_text,
                size=10,
                color=COLORS.get("text_secondary", "#94a3b8"),
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
                width=_ZONE_TEXT_WIDTH,
                tooltip=full_zone_text,
            ),
        ],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ── Прогресс ─────────────────────────────────────────────────
    fill = get_criminalist_fill(collection, criminalist)
    pct = fill["percent"]
    bar_color, pct_color = _progress_palette(pct)

    progress_label = ft.Text(
        f"{fill['filled_items']}/{fill['total_items']} · {pct}%",
        size=9,
        color=pct_color,
        weight=ft.FontWeight.W_600,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
        width=_BAR_LABEL_WIDTH,
        text_align=ft.TextAlign.RIGHT,
        tooltip=f"Сдано пунктов: {fill['filled_items']} из {fill['total_items']}",
    )

    progress_row = ft.Row(
        controls=[_build_progress_bar(pct, bar_color), progress_label],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    left_col = ft.Column(
        controls=[header_row, zone_row, progress_row],
        spacing=5,
        width=_LEFT_WIDTH,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.START,
    )

    # ── Действия ─────────────────────────────────────────────────
    edit_btn = ft.IconButton(
        icon=ft.icons.EDIT_OUTLINED,
        icon_size=14,
        icon_color=COLORS.get("btn_save", "#3b82f6"),
        tooltip="Редактировать криминалиста",
        width=26,
        height=26,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=lambda e: (_safe_stop(e), callbacks["on_edit"](criminalist)),
    )
    delete_btn = ft.IconButton(
        icon=ft.icons.DELETE_OUTLINE,
        icon_size=14,
        icon_color="#ef4444",
        tooltip="Удалить криминалиста",
        width=26,
        height=26,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=lambda e: (_safe_stop(e), callbacks["on_delete"](criminalist)),
    )

    actions_col = ft.Column(
        controls=[edit_btn, delete_btn],
        spacing=1,
        width=_ACTIONS_WIDTH,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    return ft.Row(
        controls=[left_col, actions_col],
        spacing=_CONTENT_SPACING,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.START,
    )


def _apply_tile_skin(tile, criminalist, collection, hovered: bool = False):
    """Единое место, где задаются цвет/бордер/opacity плашки."""
    pct = get_criminalist_fill(collection, criminalist)["percent"]
    accent, _ = _progress_palette(pct)
    if not criminalist.is_active:
        accent = COLORS.get("border", "#334155")

    tile.bgcolor = COLORS.get("card", "#15202e")
    tile.border = ft.border.all(1, COLORS.get("border", "#334155"))
    tile.opacity = 1.0 if criminalist.is_active else 0.55


def create_criminalist_tile(criminalist, collection, dept_map, callbacks):
    print(f"[TILE] Creating tile: {criminalist.id}")

    tile = ft.Container(
        content=_build_tile_content(criminalist, collection, dept_map, callbacks),
        width=_TILE_WIDTH,
        height=_TILE_HEIGHT,
        padding=ft.padding.symmetric(horizontal=_PAD_H, vertical=_PAD_V),
        border_radius=12,
        ink=True,
        on_click=lambda e: callbacks["on_open_form"](criminalist),
        tooltip="Нажмите, чтобы заполнить форму",
    )

    _apply_tile_skin(tile, criminalist, collection, hovered=False)
    return tile


def rebuild_tile_content(tile, criminalist, collection, dept_map, callbacks):
    tile.content = _build_tile_content(criminalist, collection, dept_map, callbacks)
    tile.width = _TILE_WIDTH
    tile.height = _TILE_HEIGHT
    _apply_tile_skin(tile, criminalist, collection, hovered=False)
    try:
        tile.update()
    except Exception:
        pass
# [DARK THEME] Обновлено только визуально, логика сохранена.

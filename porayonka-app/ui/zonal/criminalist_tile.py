# ui/zonal/criminalist_tile.py
# Увеличенная плашка криминалиста (300x340) с фиксированным безопасным layout.
# Flet 0.23.2: без animate/gradient/shadow/wrap/expand внутри плашки.
import flet as ft

from core.constants import COLORS
from core.zonal_data import get_criminalist_fill, is_item_filled


_TILE_WIDTH = 300
_TILE_HEIGHT = 340
_TILE_RADIUS = 14
_BORDER_LEFT = 4
_BORDER_OTHER = 1
_PAD_H = 14
_PAD_V = 14

# Внешняя рамка всегда равномерная 1 px. Остаток акцентной полосы рисуется
# отдельным слоем: 1 px рамки + 3 px полосы = прежний визуальный акцент 4 px.
_ACCENT_STRIPE_WIDTH = _BORDER_LEFT - _BORDER_OTHER
_LAYER_WIDTH = _TILE_WIDTH - (_BORDER_OTHER * 2)
_LAYER_HEIGHT = _TILE_HEIGHT - (_BORDER_OTHER * 2)
_INNER_WIDTH = _LAYER_WIDTH - (_PAD_H * 2) - _ACCENT_STRIPE_WIDTH

_PROGRESS_NUMBERS_WIDTH = 92
_PROGRESS_BAR_WIDTH = _INNER_WIDTH - _PROGRESS_NUMBERS_WIDTH - 8
_DETAIL_COLUMNS = 2
_DETAIL_SPACING = 4
_DETAIL_WIDTH = (_INNER_WIDTH - _DETAIL_SPACING) // _DETAIL_COLUMNS
_DETAIL_HEIGHT = 42


def _safe_stop(e):
    try:
        e.stop_propagation()
    except Exception:
        pass


def _progress_palette(pct: int):
    if pct >= 100:
        return COLORS.get("received", "#22c55e"), COLORS.get("received_text", "#4ade80")
    if pct > 0:
        return COLORS.get("in_progress", "#f59e0b"), COLORS.get("in_progress_text", "#fbbf24")
    return COLORS.get("empty", "#64748b"), COLORS.get("text_muted", "#64748b")


def _uniform_tile_border(color: str):
    """Равномерная рамка: только она надёжно сочетается с border_radius."""
    return ft.border.all(_BORDER_OTHER, color)


def _tile_content_layer(content_col: ft.Column, accent_color: str) -> ft.Stack:
    """Слой контента и отдельная скруглённая полоса статуса слева."""
    return ft.Stack(
        width=_LAYER_WIDTH,
        height=_LAYER_HEIGHT,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        controls=[
            ft.Container(
                width=_ACCENT_STRIPE_WIDTH,
                height=_LAYER_HEIGHT,
                left=0,
                top=0,
                bgcolor=accent_color,
                border_radius=ft.border_radius.only(
                    top_left=_TILE_RADIUS - _BORDER_OTHER,
                    bottom_left=_TILE_RADIUS - _BORDER_OTHER,
                ),
            ),
            ft.Container(
                content=content_col,
                left=_ACCENT_STRIPE_WIDTH,
                right=0,
                top=0,
                bottom=0,
                padding=ft.padding.symmetric(horizontal=_PAD_H, vertical=_PAD_V),
            ),
        ],
    )


def _build_zone_block(criminalist, dept_map: dict) -> ft.Column:
    """Показать каждый закреплённый отдел отдельной читаемой строкой."""
    zone_names = [
        dept_map.get(department_id, f"Отдел {department_id}")
        for department_id in criminalist.zone.department_ids
    ]
    rows = []
    if not zone_names:
        rows.append(
            ft.Row(
                controls=[
                    ft.Icon(ft.icons.PLACE_OUTLINED, size=13,
                            color=COLORS.get("text_muted", "#64748b")),
                    ft.Text(
                        "Отделы не закреплены",
                        size=10,
                        color=COLORS.get("text_muted", "#64748b"),
                        width=_INNER_WIDTH - 20,
                    ),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
    else:
        for index, department_name in enumerate(zone_names):
            rows.append(
                ft.Row(
                    controls=[
                        ft.Icon(
                            ft.icons.PLACE_OUTLINED if index == 0 else ft.icons.CHEVRON_RIGHT,
                            size=13,
                            color=COLORS.get("text_muted", "#64748b"),
                        ),
                        ft.Text(
                            department_name,
                            size=9,
                            color=COLORS.get("text_secondary", "#94a3b8"),
                            width=_INNER_WIDTH - 20,
                            max_lines=2,
                            overflow=ft.TextOverflow.CLIP,
                            tooltip=department_name,
                        ),
                    ],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
            )
    return ft.Column(
        controls=rows,
        spacing=2,
        width=_INNER_WIDTH,
        horizontal_alignment=ft.CrossAxisAlignment.START,
    )


def _build_detail_card(item, filled: bool) -> ft.Container:
    """Карточка пункта формы: полное название переносится максимум на 2 строки."""
    if filled:
        icon = ft.icons.CHECK_CIRCLE
        icon_color = COLORS.get("received_text", "#4ade80")
        bg = COLORS.get("received_bg", "#052e16")
        border_color = COLORS.get("received", "#22c55e")
        label_color = COLORS.get("received_text", "#4ade80")
    else:
        icon = ft.icons.RADIO_BUTTON_UNCHECKED
        icon_color = COLORS.get("text_muted", "#64748b")
        bg = COLORS.get("empty_bg", "#1e293b")
        border_color = COLORS.get("border", "#334155")
        label_color = COLORS.get("text_secondary", "#94a3b8")

    return ft.Container(
        width=_DETAIL_WIDTH,
        height=_DETAIL_HEIGHT,
        bgcolor=bg,
        border=ft.border.all(1, border_color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=6, vertical=4),
        tooltip=f"{item.name} — {'сдано' if filled else 'не сдано'}",
        content=ft.Row(
            controls=[
                ft.Icon(icon, size=12, color=icon_color),
                ft.Text(
                    item.name,
                    size=9,
                    weight=ft.FontWeight.W_600,
                    color=label_color,
                    width=_DETAIL_WIDTH - 12 - 12 - 6,
                    max_lines=2,
                    overflow=ft.TextOverflow.CLIP,
                ),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _build_details_block(criminalist, collection) -> ft.Column:
    """Разместить до четырёх пунктов по два в строке без wrap=True."""
    items = sorted(collection.template.items, key=lambda item: item.order)
    if not items:
        return ft.Column(
            controls=[
                ft.Text(
                    "Пункты шаблона не заданы",
                    size=10,
                    color=COLORS.get("text_muted", "#64748b"),
                )
            ],
            width=_INNER_WIDTH,
            spacing=0,
        )

    if len(items) > 4:
        filled_count = sum(
            1 for item in items if is_item_filled(collection, criminalist, item)
        )
        return ft.Column(
            controls=[
                ft.Container(
                    width=_INNER_WIDTH,
                    height=34,
                    bgcolor=COLORS.get("primary_light", "#1e293b"),
                    border=ft.border.all(1, COLORS.get("border", "#334155")),
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.icons.LIST_ALT, size=14,
                                    color=COLORS.get("text_secondary", "#94a3b8")),
                            ft.Text(
                                f"Заполнено пунктов: {filled_count} из {len(items)}",
                                size=11,
                                color=COLORS.get("text_secondary", "#94a3b8"),
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            ],
            width=_INNER_WIDTH,
            spacing=0,
        )

    rows = []
    for index in range(0, len(items), _DETAIL_COLUMNS):
        chunk = items[index:index + _DETAIL_COLUMNS]
        rows.append(
            ft.Row(
                controls=[
                    _build_detail_card(
                        item,
                        is_item_filled(collection, criminalist, item),
                    )
                    for item in chunk
                ],
                spacing=_DETAIL_SPACING,
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
    return ft.Column(
        controls=rows,
        spacing=_DETAIL_SPACING,
        width=_INNER_WIDTH,
        horizontal_alignment=ft.CrossAxisAlignment.START,
    )


def _build_content(criminalist, collection, dept_map, callbacks) -> ft.Column:
    fill = get_criminalist_fill(collection, criminalist)
    pct = fill["percent"]
    bar_color, pct_color = _progress_palette(pct)

    name_text = ft.Text(
        criminalist.full_name,
        size=16,
        weight=ft.FontWeight.BOLD,
        color=(COLORS["text"] if criminalist.is_active
               else COLORS.get("text_secondary", "#94a3b8")),
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
        width=_INNER_WIDTH - 76,
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

    activity_chip = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(chip_icon, size=12, color=chip_color),
                ft.Text(chip_text, size=10, color=chip_color,
                        weight=ft.FontWeight.W_600, no_wrap=True),
            ],
            spacing=3,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        width=68,
        height=22,
        bgcolor=chip_bg,
        border=ft.border.all(1, chip_border),
        border_radius=11,
        alignment=ft.alignment.center,
        on_click=lambda e: (_safe_stop(e), callbacks["on_toggle_active"](criminalist)),
        tooltip=chip_tooltip,
    )

    header_row = ft.Row(
        controls=[name_text, activity_chip],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.START,
        alignment=ft.MainAxisAlignment.START,
    )

    progress_numbers = ft.Column(
        controls=[
            ft.Text(
                f"{pct}%",
                size=28,
                weight=ft.FontWeight.BOLD,
                color=pct_color,
            ),
            ft.Text(
                f"сдано {fill['filled_items']} из {fill['total_items']}",
                size=10,
                color=COLORS.get("text_secondary", "#94a3b8"),
                width=_PROGRESS_NUMBERS_WIDTH,
            ),
        ],
        spacing=1,
        width=_PROGRESS_NUMBERS_WIDTH,
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.START,
    )
    bar_fill_px = max(0, min(_PROGRESS_BAR_WIDTH, round(_PROGRESS_BAR_WIDTH * pct / 100.0)))
    progress_bar = ft.Container(
        width=_PROGRESS_BAR_WIDTH,
        height=8,
        bgcolor=COLORS.get("primary_light", "#1e293b"),
        border=ft.border.all(1, COLORS.get("border", "#334155")),
        border_radius=4,
        content=ft.Container(
            width=bar_fill_px,
            height=8,
            bgcolor=bar_color,
            border_radius=4,
        ),
        tooltip=f"Заполнено: {pct}%",
    )
    progress_row = ft.Row(
        controls=[
            progress_numbers,
            ft.Container(
                content=progress_bar,
                width=_PROGRESS_BAR_WIDTH,
                alignment=ft.alignment.center_left,
            ),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.START,
    )

    edit_btn = ft.IconButton(
        icon=ft.icons.EDIT_OUTLINED,
        icon_size=18,
        icon_color=COLORS.get("btn_save", "#3b82f6"),
        tooltip="Редактировать криминалиста",
        width=32,
        height=32,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=lambda e: (_safe_stop(e), callbacks["on_edit"](criminalist)),
    )
    delete_btn = ft.IconButton(
        icon=ft.icons.DELETE_OUTLINE,
        icon_size=18,
        icon_color="#ef4444",
        tooltip="Удалить криминалиста",
        width=32,
        height=32,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=lambda e: (_safe_stop(e), callbacks["on_delete"](criminalist)),
    )
    actions_row = ft.Row(
        controls=[ft.Container(width=28), edit_btn, delete_btn],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.END,
    )

    return ft.Column(
        controls=[
            header_row,
            ft.Container(height=6),
            _build_zone_block(criminalist, dept_map),
            ft.Container(height=6),
            progress_row,
            ft.Container(height=6),
            _build_details_block(criminalist, collection),
            ft.Container(height=8),
            actions_row,
        ],
        spacing=0,
        horizontal_alignment=ft.CrossAxisAlignment.START,
    )


def create_criminalist_drag_placeholder(criminalist):
    """Полупрозрачный placeholder фиксированного размера на месте плашки."""
    return ft.Container(
        width=_TILE_WIDTH,
        height=_TILE_HEIGHT,
        bgcolor=COLORS.get("card", "#15202e"),
        opacity=0.5,
        border=ft.border.all(2, COLORS.get("btn_save", "#3b82f6")),
        border_radius=_TILE_RADIUS,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        alignment=ft.alignment.center,
        content=ft.Column(
            controls=[
                ft.Icon(ft.icons.DRAG_INDICATOR, size=28,
                        color=COLORS.get("btn_save", "#3b82f6")),
                ft.Text("Перемещение", size=12,
                        color=COLORS.get("text_secondary", "#94a3b8")),
            ],
            spacing=6,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        tooltip=f"Перемещение: {criminalist.full_name}",
    )


def create_criminalist_drag_feedback(criminalist):
    """Карточка, следующая за курсором во время drag-and-drop."""
    return ft.Container(
        width=_TILE_WIDTH,
        height=_TILE_HEIGHT,
        bgcolor=COLORS.get("card_hover", "#1e293b"),
        opacity=0.92,
        border=ft.border.all(2, COLORS.get("btn_save", "#3b82f6")),
        border_radius=_TILE_RADIUS,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        padding=ft.padding.all(14),
        content=ft.Column(
            controls=[
                ft.Icon(ft.icons.DRAG_INDICATOR, size=28,
                        color=COLORS.get("btn_save", "#3b82f6")),
                ft.Text(
                    criminalist.full_name,
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=COLORS["text"],
                    text_align=ft.TextAlign.CENTER,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    width=_INNER_WIDTH,
                ),
                ft.Text(
                    "Переместить плашку",
                    size=11,
                    color=COLORS.get("text_secondary", "#94a3b8"),
                    text_align=ft.TextAlign.CENTER,
                    width=_INNER_WIDTH,
                ),
            ],
            spacing=8,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
    )


def create_criminalist_tile(criminalist, collection, dept_map, callbacks):
    """Создать увеличенную плашку; публичный контракт не меняется."""
    print(f"[TILE] Creating tile: {criminalist.id}")
    pct_init = get_criminalist_fill(collection, criminalist)["percent"]
    accent_init, _ = _progress_palette(pct_init)
    if not criminalist.is_active:
        accent_init = COLORS.get("border", "#334155")

    tile = ft.Container(
        content=_tile_content_layer(
            _build_content(criminalist, collection, dept_map, callbacks),
            accent_init,
        ),
        width=_TILE_WIDTH,
        height=_TILE_HEIGHT,
        bgcolor=COLORS.get("card", "#15202e"),
        border=_uniform_tile_border(COLORS.get("border", "#334155")),
        border_radius=_TILE_RADIUS,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        ink=True,
        on_click=lambda e: callbacks["on_open_form"](criminalist),
        tooltip=f"{criminalist.full_name} — нажмите, чтобы заполнить форму",
    )

    def _on_hover(e):
        try:
            pct_h = get_criminalist_fill(collection, criminalist)["percent"]
            accent_h, _ = _progress_palette(pct_h)
            if not criminalist.is_active:
                accent_h = COLORS.get("border", "#334155")
            border_color = accent_h if e.data == "true" else COLORS.get("border", "#334155")
            tile.border = _uniform_tile_border(border_color)
            tile.opacity = 1.0 if criminalist.is_active else 0.6
            tile.update()
        except Exception:
            pass

    tile.on_hover = _on_hover
    tile.opacity = 1.0 if criminalist.is_active else 0.6
    return tile


def rebuild_tile_content(tile, criminalist, collection, dept_map, callbacks):
    """Обновить содержимое без изменения публичного объекта плашки."""
    pct_r = get_criminalist_fill(collection, criminalist)["percent"]
    accent_r, _ = _progress_palette(pct_r)
    if not criminalist.is_active:
        accent_r = COLORS.get("border", "#334155")
    tile.content = _tile_content_layer(
        _build_content(criminalist, collection, dept_map, callbacks),
        accent_r,
    )
    tile.width = _TILE_WIDTH
    tile.height = _TILE_HEIGHT
    tile.bgcolor = COLORS.get("card", "#15202e")
    tile.border = _uniform_tile_border(COLORS.get("border", "#334155"))
    tile.border_radius = _TILE_RADIUS
    tile.clip_behavior = ft.ClipBehavior.HARD_EDGE
    tile.opacity = 1.0 if criminalist.is_active else 0.6
    try:
        tile.update()
    except Exception:
        pass

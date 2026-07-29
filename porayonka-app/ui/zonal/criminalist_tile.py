# ui/zonal/criminalist_tile.py
# Большая квадратная карточка криминалиста (280x260) — кардинальный редизайн.
# [DARK THEME] + ft.icons.* + фиксированные пиксельные размеры (Flet 0.23.2)
#
# ВАЖНО (см. AGENTS.md 15.12 / 22.8): внутри плашки НЕТ expand=True,
# wrap=True, animate, gradient, elevation-словаря, shadow — только
# статичные Container/Text/Row с жёсткими width/height.
#
# Drag-and-drop-оболочка создаётся в zonal_tab.py. Здесь остаются сама
# плашка и безопасные статичные представления для feedback/placeholder.
import flet as ft
from core.zonal_data import get_criminalist_fill, is_item_filled
from core.constants import COLORS

_TILE_WIDTH = 280
_TILE_HEIGHT = 260
_BORDER_LEFT = 4
_BORDER_OTHER = 1
_PAD_H = 14
_PAD_V = 14
_INNER_WIDTH = _TILE_WIDTH - (_PAD_H * 2) - (_BORDER_LEFT + _BORDER_OTHER)  # 247


def _truncate(text: str, limit: int = 30) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


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


def _build_mini_chip(icon_name, label: str, color: str, filled: bool = True) -> ft.Container:
    bg = COLORS.get("received_bg", "#052e16") if filled else COLORS.get("empty_bg", "#1e293b")
    border = COLORS.get("received", "#22c55e") if filled else COLORS.get("border", "#334155")
    icon_color = COLORS.get("received_text", "#4ade80") if filled else COLORS.get("text_muted", "#64748b")
    label_color = COLORS.get("received_text", "#4ade80") if filled else COLORS.get("text_secondary", "#94a3b8")
    return ft.Container(
        width=54,
        height=32,
        bgcolor=bg,
        border=ft.border.all(1, border),
        border_radius=7,
        padding=ft.padding.symmetric(horizontal=4, vertical=2),
        content=ft.Row(
            controls=[
                ft.Icon(icon_name, size=12, color=icon_color),
                ft.Text(
                    label,
                    size=9,
                    color=label_color,
                    weight=ft.FontWeight.W_600,
                    no_wrap=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=2,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        tooltip=f"Пункт: {label}" + (" — сдан" if filled else " — не сдан"),
    )


def _build_content(criminalist, collection, dept_map, callbacks) -> ft.Column:
    fill = get_criminalist_fill(collection, criminalist)
    pct = fill["percent"]
    bar_color, pct_color = _progress_palette(pct)

    # Заголовок: ФИО + чип активности
    name_text = ft.Text(
        criminalist.full_name,
        size=16,
        weight=ft.FontWeight.BOLD,
        color=COLORS["text"] if criminalist.is_active else COLORS.get("text_secondary", "#94a3b8"),
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

    chip = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(chip_icon, size=12, color=chip_color),
                ft.Text(chip_text, size=10, color=chip_color, weight=ft.FontWeight.W_600, no_wrap=True),
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
        controls=[name_text, chip],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.START,
        alignment=ft.MainAxisAlignment.START,
    )

    # Закреплённые отделы
    zone_names = [dept_map.get(did, f"Отдел {did}") for did in criminalist.zone.department_ids]
    full_zone_text = ", ".join(zone_names) if zone_names else "Отделы не закреплены"
    zone_text = _truncate(full_zone_text, 45)

    zone_row = ft.Row(
        controls=[
            ft.Icon(ft.icons.PLACE_OUTLINED, size=13, color=COLORS.get("text_muted", "#64748b")),
            ft.Text(
                zone_text,
                size=11,
                color=COLORS.get("text_secondary", "#94a3b8"),
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
                width=_INNER_WIDTH - 20,
                tooltip=full_zone_text,
            ),
        ],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Прогресс
    progress_pct_text = ft.Text(
        f"{pct}%",
        size=28,
        weight=ft.FontWeight.BOLD,
        color=pct_color,
        text_align=ft.TextAlign.LEFT,
    )
    progress_sub_text = ft.Text(
        f"сдано {fill['filled_items']} из {fill['total_items']}",
        size=10,
        color=COLORS.get("text_secondary", "#94a3b8"),
    )
    progress_numbers_col = ft.Column(
        controls=[progress_pct_text, progress_sub_text],
        spacing=1,
        width=80,
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.START,
    )

    bar_fill_px = max(0, min(140, round(140 * pct / 100.0)))
    progress_bar = ft.Container(
        width=140,
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

    progress_right_col = ft.Column(
        controls=[progress_bar],
        spacing=3,
        width=140,
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.START,
    )

    progress_row = ft.Row(
        controls=[progress_numbers_col, progress_right_col],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.START,
    )

    # Детализация по пунктам
    items = sorted(collection.template.items, key=lambda i: i.order)
    details_row_controls = []
    if items:
        if len(items) <= 4:
            for it in items:
                filled_it = is_item_filled(collection, criminalist, it)
                label_short = _truncate(it.name, 12)
                details_row_controls.append(
                    _build_mini_chip(
                        ft.icons.CHECK_CIRCLE if filled_it else ft.icons.RADIO_BUTTON_UNCHECKED,
                        label_short,
                        COLORS.get("received", "#22c55e") if filled_it else COLORS.get("text_muted", "#64748b"),
                        filled=filled_it,
                    )
                )
        else:
            filled_count = sum(1 for it in items if is_item_filled(collection, criminalist, it))
            details_row_controls.append(
                ft.Container(
                    width=_INNER_WIDTH,
                    height=28,
                    bgcolor=COLORS.get("primary_light", "#1e293b"),
                    border=ft.border.all(1, COLORS.get("border", "#334155")),
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.icons.LIST_ALT, size=14, color=COLORS.get("text_secondary", "#94a3b8")),
                            ft.Text(
                                f"Сдано: {filled_count}/{len(items)} пунктов",
                                size=11,
                                color=COLORS.get("text_secondary", "#94a3b8"),
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        tight=True,
                    ),
                    tooltip=f"Заполнено пунктов: {filled_count} из {len(items)}",
                )
            )
    else:
        details_row_controls.append(
            ft.Container(
                width=_INNER_WIDTH,
                height=28,
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.icons.HELP_OUTLINE, size=14, color=COLORS.get("text_muted", "#64748b")),
                        ft.Text(
                            "Пункты шаблона не заданы",
                            size=10,
                            color=COLORS.get("text_muted", "#64748b"),
                        ),
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                ),
            )
        )

    details_row = ft.Row(
        controls=details_row_controls,
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.START,
    )

    # Кнопки действий
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
        controls=[
            ft.Container(width=28),
            edit_btn,
            delete_btn,
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.END,
    )

    # Сборка
    return ft.Column(
        controls=[
            header_row,
            ft.Container(height=6),
            zone_row,
            ft.Container(height=6),
            progress_row,
            ft.Container(height=6),
            details_row,
            ft.Container(height=6),
            actions_row,
        ],
        spacing=0,
        horizontal_alignment=ft.CrossAxisAlignment.START,
    )


def create_criminalist_drag_placeholder(criminalist):
    """Статичный полупрозрачный placeholder на месте плашки во время drag.

    Нельзя использовать саму плашку одновременно как ``content`` и
    ``content_when_dragging`` у ``ft.Draggable``. Отдельный Container сохраняет
    размер ячейки сетки и не добавляет запрещённые анимации или shadow.
    """
    return ft.Container(
        width=_TILE_WIDTH,
        height=_TILE_HEIGHT,
        bgcolor=COLORS.get("card", "#15202e"),
        opacity=0.5,
        border=ft.border.all(2, COLORS.get("btn_save", "#3b82f6")),
        border_radius=14,
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
    """Компактное визуальное представление плашки, следующее за курсором."""
    return ft.Container(
        width=_TILE_WIDTH,
        height=_TILE_HEIGHT,
        bgcolor=COLORS.get("card_hover", "#1e293b"),
        opacity=0.92,
        border=ft.border.all(2, COLORS.get("btn_save", "#3b82f6")),
        border_radius=14,
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
    print(f"[TILE] Creating tile: {criminalist.id}")
    content_col = _build_content(criminalist, collection, dept_map, callbacks)
    tile = ft.Container(
        content=content_col,
        width=_TILE_WIDTH,
        height=_TILE_HEIGHT,
        padding=ft.padding.symmetric(horizontal=_PAD_H, vertical=_PAD_V),
        border_radius=14,
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
            hovered_val = (e.data == "true")
            side_color = accent_h if hovered_val else COLORS.get("border", "#334155")
            tile.border = ft.border.only(
                left=ft.BorderSide(_BORDER_LEFT, accent_h),
                top=ft.BorderSide(_BORDER_OTHER, side_color),
                right=ft.BorderSide(_BORDER_OTHER, side_color),
                bottom=ft.BorderSide(_BORDER_OTHER, side_color),
            )
            tile.opacity = 1.0 if criminalist.is_active else 0.6
            tile.update()
        except Exception:
            pass

    tile.on_hover = _on_hover

    pct_init = get_criminalist_fill(collection, criminalist)["percent"]
    accent_init, _ = _progress_palette(pct_init)
    if not criminalist.is_active:
        accent_init = COLORS.get("border", "#334155")
    tile.bgcolor = COLORS.get("card", "#15202e")
    tile.border = ft.border.only(
        left=ft.BorderSide(_BORDER_LEFT, accent_init),
        top=ft.BorderSide(_BORDER_OTHER, COLORS.get("border", "#334155")),
        right=ft.BorderSide(_BORDER_OTHER, COLORS.get("border", "#334155")),
        bottom=ft.BorderSide(_BORDER_OTHER, COLORS.get("border", "#334155")),
    )
    tile.opacity = 1.0 if criminalist.is_active else 0.6

    return tile


def rebuild_tile_content(tile, criminalist, collection, dept_map, callbacks):
    new_col = _build_content(criminalist, collection, dept_map, callbacks)
    tile.content = new_col
    tile.width = _TILE_WIDTH
    tile.height = _TILE_HEIGHT
    pct_r = get_criminalist_fill(collection, criminalist)["percent"]
    accent_r, _ = _progress_palette(pct_r)
    if not criminalist.is_active:
        accent_r = COLORS.get("border", "#334155")
    tile.bgcolor = COLORS.get("card", "#15202e")
    tile.border = ft.border.only(
        left=ft.BorderSide(_BORDER_LEFT, accent_r),
        top=ft.BorderSide(_BORDER_OTHER, COLORS.get("border", "#334155")),
        right=ft.BorderSide(_BORDER_OTHER, COLORS.get("border", "#334155")),
        bottom=ft.BorderSide(_BORDER_OTHER, COLORS.get("border", "#334155")),
    )
    tile.opacity = 1.0 if criminalist.is_active else 0.6
    try:
        tile.update()
    except Exception:
        pass

# ui/zonal/criminalist_tile.py
# Компактная плашка криминалиста (редизайн, фаза 3).
#
# ВАЖНО ПРО LAYOUT (Flet 0.23.2):
#   Плашка строится ТОЛЬКО из контролов с фиксированными размерами.
#   Внутри плашки НЕТ ни одного expand=True — ни вертикального, ни горизонтального.
#   Причина: плашки живут внутри Row(wrap=True) (это Flutter Wrap), а Wrap
#   не умеет раздавать Expanded-детям конечные constraints. Любой expand внутри
#   даёт либо «резиновую» высоту на весь экран, либо серый пустой прямоугольник
#   вместо содержимого. Все размеры здесь заданы явно (width/height).
#
# Содержимое плашки: ФИО, статус активности, закреплённые отделы (кратко), процент.
# Клик по плашке -> модальное окно заполнения формы.
# Меню (три точки) -> заполнить / включить-отключить / редактировать / удалить.
# [DARK THEME] + ft.icons.* (Flet 0.23.2)
import flet as ft
from core.zonal_data import get_criminalist_fill
from core.constants import COLORS


# ── Геометрия плашки (всё фиксировано, без expand) ──────────────
TILE_WIDTH = 360
TILE_HEIGHT = 88
TILE_PADDING = 10

_ICON_COL_W = 28                 # колонка статуса слева
_ACTIONS_COL_W = 58              # колонка процента и меню справа
_ROW_SPACING = 10
# Ширина центральной колонки высчитывается, чтобы сумма влезала без переполнения.
_MAIN_COL_W = (
    TILE_WIDTH
    - TILE_PADDING * 2
    - _ICON_COL_W
    - _ACTIONS_COL_W
    - _ROW_SPACING * 2
)                                 # = 360 - 20 - 28 - 58 - 20 = 234

_STATUS_TEXT_W = 62
_ZONE_TEXT_W = _MAIN_COL_W - _STATUS_TEXT_W - 12 - 8   # иконка 12 + spacing


def _fill_colors(pct: int):
    """Цвета прогресса по проценту заполнения."""
    if pct >= 100:
        return COLORS["received"], COLORS["received_text"]
    if pct > 0:
        return COLORS["in_progress"], COLORS["in_progress_text"]
    return COLORS["empty"], COLORS["text_muted"]


def _build_tile_content(criminalist, collection, dept_map: dict, callbacks: dict) -> ft.Row:
    """
    Внутреннее содержимое плашки.
    Возвращает ft.Row с тремя колонками фиксированной ширины.
    """
    fill = get_criminalist_fill(collection, criminalist)
    pct = fill["percent"]
    bar_color, pct_color = _fill_colors(pct)

    # ── Колонка 1: статус активности (иконка-переключатель) ─────
    if criminalist.is_active:
        status_icon = ft.icons.CHECK_CIRCLE
        status_icon_color = COLORS["received_text"]
        status_label = "Активен"
        status_label_color = COLORS["received_text"]
        status_tooltip = "Участвует в сборе. Нажмите, чтобы отключить"
    else:
        status_icon = ft.icons.DO_NOT_DISTURB_ON
        status_icon_color = COLORS["text_muted"]
        status_label = "Отключён"
        status_label_color = COLORS["text_muted"]
        status_tooltip = "Не участвует в сборе. Нажмите, чтобы включить"

    status_button = ft.Container(
        content=ft.Icon(status_icon, size=20, color=status_icon_color),
        width=_ICON_COL_W,
        height=_ICON_COL_W,
        border_radius=14,
        alignment=ft.alignment.center,
        bgcolor=COLORS["received_bg"] if criminalist.is_active else COLORS["empty_bg"],
        ink=True,
        tooltip=status_tooltip,
        on_click=lambda e: callbacks["on_toggle_active"](criminalist),
    )

    # ── Колонка 2: ФИО + статус/отделы + прогресс-бар ────────────
    name_text = ft.Text(
        criminalist.full_name,
        size=13,
        weight=ft.FontWeight.W_600,
        color=COLORS["text"],
        width=_MAIN_COL_W,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
        tooltip=criminalist.full_name,
    )

    zone_names = [dept_map.get(did, f"Отдел {did}") for did in criminalist.zone.department_ids]
    if zone_names:
        zone_full = ", ".join(zone_names)
        zone_short = f"{len(zone_names)} отд.: {zone_full}"
    else:
        zone_full = "Отделы не закреплены"
        zone_short = zone_full
    if criminalist.note:
        zone_full = f"{zone_full}\nПримечание: {criminalist.note}"

    meta_row = ft.Row(
        controls=[
            ft.Text(
                status_label,
                size=10,
                color=status_label_color,
                weight=ft.FontWeight.W_500,
                width=_STATUS_TEXT_W,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            ft.Icon(ft.icons.LOCATION_ON, size=12, color=COLORS["text_muted"]),
            ft.Text(
                zone_short,
                size=10,
                color=COLORS["text_secondary"],
                width=_ZONE_TEXT_W,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
                tooltip=zone_full,
            ),
        ],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    progress_bar = ft.ProgressBar(
        value=pct / 100.0,
        width=_MAIN_COL_W,
        height=6,
        color=bar_color,
        bgcolor=COLORS["border"],
        border_radius=3,
        tooltip=f"Заполнено пунктов: {fill['filled_items']} из {fill['total_items']}",
    )

    main_col = ft.Column(
        controls=[name_text, meta_row, progress_bar],
        width=_MAIN_COL_W,
        spacing=4,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        tight=True,
    )

    # ── Колонка 3: процент + меню действий ───────────────────────
    pct_text = ft.Text(
        f"{pct}%",
        size=14,
        weight=ft.FontWeight.BOLD,
        color=pct_color,
        width=_ACTIONS_COL_W,
        text_align=ft.TextAlign.RIGHT,
        tooltip=f"Заполнено {fill['filled_items']} из {fill['total_items']} пунктов",
    )

    menu_button = ft.PopupMenuButton(
        icon=ft.icons.MORE_VERT,
        icon_size=18,
        icon_color=COLORS["text_secondary"],
        tooltip="Действия",
        bgcolor=COLORS["primary_light"],
        items=[
            ft.PopupMenuItem(
                text="Заполнить форму",
                icon=ft.icons.EDIT_DOCUMENT,
                on_click=lambda e: callbacks["on_open_form"](criminalist),
            ),
            ft.PopupMenuItem(
                text="Отключить от сбора" if criminalist.is_active else "Включить в сбор",
                icon=ft.icons.VISIBILITY_OFF if criminalist.is_active else ft.icons.VISIBILITY,
                on_click=lambda e: callbacks["on_toggle_active"](criminalist),
            ),
            ft.PopupMenuItem(
                text="Редактировать и зоны",
                icon=ft.icons.EDIT,
                on_click=lambda e: callbacks["on_edit"](criminalist),
            ),
            ft.PopupMenuItem(
                text="Удалить",
                icon=ft.icons.DELETE_OUTLINE,
                on_click=lambda e: callbacks["on_delete"](criminalist),
            ),
        ],
    )

    actions_col = ft.Column(
        controls=[
            pct_text,
            ft.Container(content=menu_button, width=_ACTIONS_COL_W, height=30,
                         alignment=ft.alignment.center_right),
        ],
        width=_ACTIONS_COL_W,
        spacing=0,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.END,
        tight=True,
    )

    return ft.Row(
        controls=[status_button, main_col, actions_col],
        spacing=_ROW_SPACING,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.START,
    )


def create_criminalist_tile(
    criminalist,
    collection,
    dept_map: dict,
    callbacks: dict,
) -> ft.Container:
    """
    Создать компактную плашку криминалиста (360x88).
    Клик по плашке открывает модальное окно заполнения формы.
    """
    tile = ft.Container(
        content=_build_tile_content(criminalist, collection, dept_map, callbacks),
        width=TILE_WIDTH,
        height=TILE_HEIGHT,
        padding=ft.padding.all(TILE_PADDING),
        bgcolor=COLORS["card"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=10,
        ink=True,
        on_click=lambda e: callbacks["on_open_form"](criminalist),
        tooltip="Нажмите, чтобы заполнить форму",
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )
    # Неактивные — приглушены
    tile.opacity = 1.0 if criminalist.is_active else 0.55
    return tile


def rebuild_tile_content(tile: ft.Container, criminalist, collection, dept_map: dict, callbacks: dict):
    """Обновить содержимое существующей плашки без перерисовки всей сетки."""
    tile.content = _build_tile_content(criminalist, collection, dept_map, callbacks)
    tile.opacity = 1.0 if criminalist.is_active else 0.55
    try:
        tile.update()
    except Exception:
        pass

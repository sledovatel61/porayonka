# ui/zonal/criminalists_summary_panel.py
# Разворачиваемая сводка по криминалистам и итогам пунктов шаблона.
# Flet 0.23.2: фиксированные размеры, без wrap/expand/gradient/shadow.
import flet as ft
from typing import Callable, Dict, Optional

from core.constants import COLORS
from core.zonal_data import get_criminalist_fill, get_fill_summary, is_item_filled
from core.zonal_models import ReportItemType


_NAME_WIDTH = 260
_BAR_WIDTH = 140
_BAR_HEIGHT = 8
_STATUS_WIDTH = 116
_CHIP_WIDTH = 210
_CHIP_HEIGHT = 76
_CHIP_SPACING = 8
_CHIPS_PER_ROW = 4
_CHIPS_BLOCK_WIDTH = _CHIPS_PER_ROW * _CHIP_WIDTH + (_CHIPS_PER_ROW - 1) * _CHIP_SPACING


def _find_submission(collection, criminalist_id: int, item_id: str):
    """Найти ReportData без создания новой записи."""
    for submission in collection.submissions:
        if (submission.criminalist_id == criminalist_id
                and submission.template_item_id == item_id):
            return submission
    return None


def _progress_palette(pct: int):
    if pct >= 100:
        return COLORS.get("received", "#22c55e"), COLORS.get("received_text", "#4ade80")
    if pct > 0:
        return COLORS.get("in_progress", "#f59e0b"), COLORS.get("in_progress_text", "#fbbf24")
    return COLORS.get("empty", "#64748b"), COLORS.get("text_muted", "#64748b")


def _mini_bar(pct: int, color: str) -> ft.Container:
    fill_width = max(0, min(_BAR_WIDTH, round(_BAR_WIDTH * pct / 100.0)))
    return ft.Container(
        width=_BAR_WIDTH,
        height=_BAR_HEIGHT,
        bgcolor=COLORS.get("border", "#334155"),
        border_radius=_BAR_HEIGHT / 2,
        content=ft.Container(
            width=fill_width,
            height=_BAR_HEIGHT,
            bgcolor=color,
            border_radius=_BAR_HEIGHT / 2,
        ),
    )


def _item_value_text(collection, criminalist, item) -> str:
    """Показать значение одного пункта для одного криминалиста."""
    report_data = _find_submission(collection, criminalist.id, item.id)
    use_department_numbers = (
        item.item_type == ReportItemType.NUMERICAL
        and collection.template.use_departments_mode
        and bool(criminalist.zone.department_ids)
    )

    if item.item_type == ReportItemType.NUMERICAL:
        unit = f" {item.unit}" if item.unit else ""
        if use_department_numbers:
            departments = criminalist.zone.department_ids
            if report_data is None:
                return f"0{unit} · 0/{len(departments)} отд."
            total = sum(
                value for value in (
                    report_data.department_values.get(department_id)
                    for department_id in departments
                ) if value is not None
            )
            done = sum(
                1 for department_id in departments
                if report_data.department_values.get(department_id) is not None
            )
            return f"{total}{unit} · {done}/{len(departments)} отд."
        if report_data is None or report_data.value is None:
            return "Нет данных"
        return f"{report_data.value}{unit}"

    # Факт сдачи не делится по отделам: одна общая галочка для криминалиста.
    return "Сдано" if is_item_filled(collection, criminalist, item) else "Не сдано"


def _status_style(pct: int):
    if pct >= 100:
        return (
            ft.icons.TASK_ALT,
            COLORS.get("received_text", "#4ade80"),
            COLORS.get("received_bg", "#052e16"),
            COLORS.get("received", "#22c55e"),
            "Сдал",
        )
    if pct > 0:
        return (
            ft.icons.HOURGLASS_BOTTOM,
            COLORS.get("in_progress_text", "#fbbf24"),
            COLORS.get("in_progress_bg", "#451a03"),
            COLORS.get("in_progress", "#f59e0b"),
            "Частично",
        )
    return (
        ft.icons.REPORT_GMAILERRORRED,
        COLORS.get("text_muted", "#64748b"),
        COLORS.get("empty_bg", "#1e293b"),
        COLORS.get("border", "#334155"),
        "Не сдал",
    )


def _item_chip(collection, criminalist, item) -> ft.Container:
    """Увеличенная карточка пункта: название видно в две строки."""
    filled = is_item_filled(collection, criminalist, item)
    value_text = _item_value_text(collection, criminalist, item)
    if filled:
        icon = ft.icons.CHECK_CIRCLE
        icon_color = COLORS.get("received_text", "#4ade80")
        bg = COLORS.get("received_bg", "#052e16")
        border_color = COLORS.get("received", "#22c55e")
        value_color = COLORS.get("received_text", "#4ade80")
    else:
        icon = ft.icons.RADIO_BUTTON_UNCHECKED
        icon_color = COLORS.get("text_muted", "#64748b")
        bg = COLORS.get("empty_bg", "#1e293b")
        border_color = COLORS.get("border", "#334155")
        value_color = COLORS.get("text_muted", "#64748b")

    return ft.Container(
        width=_CHIP_WIDTH,
        height=_CHIP_HEIGHT,
        bgcolor=bg,
        border=ft.border.all(1, border_color),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=6),
        tooltip=f"{item.name}: {value_text}",
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(icon, size=16, color=icon_color),
                        ft.Text(
                            item.name,
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color=COLORS.get("text_secondary", "#94a3b8"),
                            width=_CHIP_WIDTH - 16 - 16 - 7,
                            max_lines=2,
                            overflow=ft.TextOverflow.CLIP,
                        ),
                    ],
                    spacing=7,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Text(
                    value_text,
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=value_color,
                    width=_CHIP_WIDTH - 16,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
    )


def _item_rows(items, make_card) -> ft.Column:
    """Разбить карточки на предсказуемые фиксированные ряды без wrap=True."""
    rows = []
    for index in range(0, len(items), _CHIPS_PER_ROW):
        rows.append(
            ft.Row(
                controls=[make_card(item) for item in items[index:index + _CHIPS_PER_ROW]],
                spacing=_CHIP_SPACING,
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
    return ft.Column(
        controls=rows,
        spacing=_CHIP_SPACING,
        width=_CHIPS_BLOCK_WIDTH,
        horizontal_alignment=ft.CrossAxisAlignment.START,
    )


def _criminalist_row(collection, criminalist) -> ft.Container:
    fill = get_criminalist_fill(collection, criminalist)
    pct = fill["percent"]
    bar_color, pct_color = _progress_palette(pct)
    status_icon, status_color, status_bg, status_border, status_label = _status_style(pct)

    name_block = ft.Column(
        controls=[
            ft.Text(
                criminalist.full_name,
                size=15,
                weight=ft.FontWeight.BOLD,
                color=COLORS["text"],
                width=_NAME_WIDTH,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
                tooltip=criminalist.full_name,
            ),
            ft.Text(
                criminalist.note or f"Отделов: {len(criminalist.zone.department_ids)}",
                size=12,
                color=COLORS.get("text_muted", "#64748b"),
                width=_NAME_WIDTH,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
        ],
        spacing=3,
        width=_NAME_WIDTH,
    )

    progress_block = ft.Column(
        controls=[
            _mini_bar(pct, bar_color),
            ft.Text(
                f"{fill['filled_items']}/{fill['total_items']} · {pct}%",
                size=13,
                color=pct_color,
                weight=ft.FontWeight.W_600,
                width=_BAR_WIDTH,
            ),
        ],
        spacing=5,
        width=_BAR_WIDTH,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    status_block = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(status_icon, size=16, color=status_color),
                ft.Text(status_label, size=12, color=status_color,
                        weight=ft.FontWeight.W_600, no_wrap=True),
            ],
            spacing=5,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        width=_STATUS_WIDTH,
        height=28,
        bgcolor=status_bg,
        border=ft.border.all(1, status_border),
        border_radius=14,
        alignment=ft.alignment.center,
        tooltip=f"Статус сдачи: {status_label} ({pct}%)",
    )

    items = sorted(collection.template.items, key=lambda item: item.order)
    if items:
        chips = _item_rows(items, lambda item: _item_chip(collection, criminalist, item))
    else:
        chips = ft.Column(
            controls=[
                ft.Text("Пункты шаблона не заданы", size=11,
                        color=COLORS.get("text_muted", "#64748b")),
            ],
            width=_CHIPS_BLOCK_WIDTH,
        )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[name_block, progress_block, status_block],
                    spacing=16,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=8),
                chips,
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
        bgcolor=COLORS.get("primary_light", "#1e293b"),
        border=ft.border.all(1, status_border),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
    )


def _aggregate_item_card(collection, item, active_criminalists) -> ft.Container:
    """Карточка общего итога по одному пункту шаблона."""
    if item.item_type == ReportItemType.NUMERICAL:
        total = 0
        filled = 0
        for criminalist in active_criminalists:
            report_data = _find_submission(collection, criminalist.id, item.id)
            if report_data is not None:
                if report_data.value is not None:
                    total += report_data.value
                elif report_data.department_values:
                    total += sum(report_data.department_values.values())
            if is_item_filled(collection, criminalist, item):
                filled += 1
        unit = f" {item.unit}" if item.unit else ""
        icon = ft.icons.NUMBERS
        value = f"Всего: {total}{unit}"
        detail = f"Заполнили: {filled}/{len(active_criminalists)}"
    else:
        submitted = sum(
            1 for criminalist in active_criminalists
            if is_item_filled(collection, criminalist, item)
        )
        icon = ft.icons.CHECK_CIRCLE
        value = f"Сдали: {submitted}/{len(active_criminalists)}"
        detail = "Общая отметка сдачи"

    return ft.Container(
        width=_CHIP_WIDTH,
        height=_CHIP_HEIGHT,
        bgcolor=COLORS.get("stat_blue_bg", "#172554"),
        border=ft.border.all(1, COLORS.get("stat_blue_border", "#3b82f6")),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=6),
        tooltip=f"{item.name}: {value}",
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(icon, size=16, color=COLORS.get("stat_blue_text", "#60a5fa")),
                        ft.Text(
                            item.name,
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color=COLORS.get("text_secondary", "#94a3b8"),
                            width=_CHIP_WIDTH - 16 - 16 - 7,
                            max_lines=2,
                            overflow=ft.TextOverflow.CLIP,
                        ),
                    ],
                    spacing=7,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Text(
                    value,
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=COLORS.get("stat_blue_text", "#60a5fa"),
                    width=_CHIP_WIDTH - 16,
                ),
                ft.Text(
                    detail,
                    size=11,
                    color=COLORS.get("text_secondary", "#94a3b8"),
                    width=_CHIP_WIDTH - 16,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=3,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
    )


def _sorted_active_criminalists(collection):
    """Полностью сдавшие идут первыми, затем частично сдавшие и не сдавшие."""
    indexed = list(enumerate(c for c in collection.criminalists if c.is_active))
    return [
        criminalist
        for _, criminalist in sorted(
            indexed,
            key=lambda pair: (
                0 if get_criminalist_fill(collection, pair[1])["percent"] >= 100 else 1,
                -get_criminalist_fill(collection, pair[1])["percent"],
                pair[0],
            ),
        )
    ]


def create_criminalists_summary_panel(
    collection,
    panel_ref: Optional[Dict] = None,
    on_toggle: Optional[Callable] = None,
) -> ft.Column:
    """Создать обновляемую сводку; публичный контракт сохраняется."""
    is_expanded = bool(panel_ref.get("is_expanded", False)) if panel_ref else False
    summary = get_fill_summary(collection)
    active = summary["active"]
    inactive = summary["inactive"]
    submitted = summary["items_submitted"]
    overall = summary["overall_percent"]
    bar_color, _ = _progress_palette(overall)
    active_criminalists = _sorted_active_criminalists(collection)
    done_count = sum(
        1 for criminalist in active_criminalists
        if get_criminalist_fill(collection, criminalist)["percent"] >= 100
    )

    print(
        f"[CRIM_SUMMARY] expanded={is_expanded} active={active} "
        f"submitted={submitted} overall={overall}"
    )

    def _toggle(e):
        if panel_ref is not None:
            panel_ref["is_expanded"] = not panel_ref.get("is_expanded", False)
        if on_toggle is not None:
            on_toggle()

    def _pill(icon, text: str, color: str) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=14, color=color),
                    ft.Text(text, size=12, color=COLORS["text"], weight=ft.FontWeight.W_500),
                ],
                spacing=5,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
            bgcolor=COLORS.get("card", "#15202e"),
            border=ft.border.all(1, COLORS.get("border", "#334155")),
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
        )

    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.icons.GROUPS_2, size=16, color="white"),
                    width=28,
                    height=28,
                    bgcolor=COLORS.get("btn_save", "#3b82f6"),
                    border_radius=8,
                    alignment=ft.alignment.center,
                ),
                ft.Text("Сводка по криминалистам", size=15,
                        weight=ft.FontWeight.BOLD, color="white"),
                _pill(ft.icons.PERSON_OUTLINE, f"Активных: {active}",
                      COLORS.get("received_text", "#4ade80")),
                _pill(ft.icons.CHECK_CIRCLE_OUTLINE, f"Сдали: {done_count}",
                      COLORS.get("stat_blue_text", "#60a5fa")),
                _pill(ft.icons.LIST_ALT, f"Пунктов: {submitted}",
                      COLORS.get("in_progress_text", "#fbbf24")),
                _pill(ft.icons.TRENDING_UP, f"{overall}%",
                      COLORS.get("text_secondary", "#94a3b8")),
                _mini_bar(overall, bar_color),
                ft.Icon(
                    ft.icons.KEYBOARD_ARROW_UP if is_expanded else ft.icons.KEYBOARD_ARROW_DOWN,
                    size=20,
                    color="white",
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=COLORS.get("primary", "#0f172a"),
        border=ft.border.all(1, COLORS.get("border", "#334155")),
        border_radius=ft.border_radius.all(12) if not is_expanded else ft.border_radius.only(
            top_left=12, top_right=12
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        ink=True,
        on_click=_toggle,
        tooltip=("Нажмите, чтобы свернуть детализацию" if is_expanded
                 else "Нажмите, чтобы развернуть детализацию по криминалистам"),
    )

    if not is_expanded:
        return ft.Column(controls=[header], spacing=0)

    rows = []
    if active_criminalists:
        for criminalist in active_criminalists:
            rows.append(_criminalist_row(collection, criminalist))
    else:
        rows.append(
            ft.Container(
                content=ft.Text(
                    "Нет активных криминалистов в текущем сборе",
                    size=13,
                    color=COLORS.get("text_secondary", "#94a3b8"),
                ),
                padding=ft.padding.all(12),
            )
        )

    items = sorted(collection.template.items, key=lambda item: item.order)
    aggregate_controls = [
        ft.Text("Итоги по пунктам", size=13, weight=ft.FontWeight.BOLD,
                color=COLORS.get("stat_blue_text", "#60a5fa"))
    ]
    if items:
        aggregate_controls.append(
            _item_rows(
                items,
                lambda item: _aggregate_item_card(collection, item, active_criminalists),
            )
        )
    else:
        aggregate_controls.append(
            ft.Text("Пункты шаблона не заданы", size=12,
                    color=COLORS.get("text_muted", "#64748b"))
        )

    legend = ft.Row(
        controls=[
            ft.Row(
                controls=[
                    ft.Icon(ft.icons.TASK_ALT, size=14,
                            color=COLORS.get("received_text", "#4ade80")),
                    ft.Text("сначала полностью сдавшие", size=11,
                            color=COLORS.get("text_secondary", "#94a3b8")),
                ],
                spacing=4,
                tight=True,
            ),
            ft.Text(
                f"Показаны активные: {active}; отключено: {inactive}",
                size=11,
                color=COLORS.get("text_muted", "#64748b"),
            ),
        ],
        spacing=16,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    body = ft.Container(
        content=ft.Column(
            controls=[
                legend,
                ft.Container(height=8),
                ft.Column(controls=aggregate_controls, spacing=6),
                ft.Container(height=12),
            ] + rows,
            spacing=8,
            tight=True,
        ),
        bgcolor=COLORS.get("card", "#15202e"),
        border=ft.border.all(1, COLORS.get("border", "#334155")),
        border_radius=ft.border_radius.only(bottom_left=12, bottom_right=12),
        padding=ft.padding.all(12),
    )
    return ft.Column(controls=[header, body], spacing=0)

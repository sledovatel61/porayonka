# ui/zonal/criminalists_summary_panel.py
# НОВАЯ разворачиваемая секция «Сводка по криминалистам».
# Свёрнуто  — одна компактная строка (активные / сдано / общий прогресс).
# Развёрнуто — список активных криминалистов с детализацией ПО КАЖДОМУ
#              пункту шаблона: значение (числовой) или галочка (да/нет).
# [DARK THEME] + ft.icons.* (Flet 0.23.2)
#
# Layout-безопасность: никаких expand=True по вертикали, ширины блоков
# заданы жёстко, горизонтальное переполнение решается Row(scroll=AUTO).
import flet as ft
from typing import Callable, Dict, Optional

from core.constants import COLORS
from core.zonal_models import ReportItemType
from core.zonal_data import get_criminalist_fill, get_fill_summary, is_item_filled


_NAME_WIDTH = 190
_BAR_WIDTH = 110
_BAR_HEIGHT = 6
_PCT_WIDTH = 64
_CHIP_WIDTH = 132
_CHIP_HEIGHT = 44
_CHIP_SPACING = 6
_CHIPS_PER_ROW = 3        # чипы пунктов шаблона: 3 в ряд, фиксированные ряды
_CHIPS_BLOCK_WIDTH = _CHIPS_PER_ROW * _CHIP_WIDTH + (_CHIPS_PER_ROW - 1) * _CHIP_SPACING  # 408


def _find_submission(collection, criminalist_id: int, item_id: str):
    """Найти ReportData без создания новой записи (не мутирует collection)."""
    for sub in collection.submissions:
        if sub.criminalist_id == criminalist_id and sub.template_item_id == item_id:
            return sub
    return None


def _item_value_text(collection, criminalist, item) -> str:
    """Человекочитаемое значение пункта для конкретного криминалиста."""
    rd = _find_submission(collection, criminalist.id, item.id)
    use_dept_mode = (
        collection.template.use_departments_mode
        and bool(criminalist.zone.department_ids)
    )

    if item.item_type == ReportItemType.NUMERICAL:
        if use_dept_mode:
            depts = criminalist.zone.department_ids
            if rd is None:
                return f"0 / {len(depts)} отд."
            total = sum(v for v in (rd.department_values.get(d) for d in depts) if v is not None)
            done = sum(1 for d in depts if rd.department_values.get(d) is not None)
            unit = f" {item.unit}" if item.unit else ""
            return f"{total}{unit}  ({done}/{len(depts)} отд.)"
        if rd is None or rd.value is None:
            return "нет данных"
        unit = f" {item.unit}" if item.unit else ""
        return f"{rd.value}{unit}"

    # DELIVERABLE
    if use_dept_mode:
        depts = criminalist.zone.department_ids
        if rd is None:
            return f"0 / {len(depts)} отд."
        done = sum(1 for d in depts if rd.department_submitted.get(d, False))
        return f"{done} / {len(depts)} отд."
    if rd is not None and rd.is_submitted:
        return "Сдано"
    return "Не сдано"


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
        content=ft.Row(
            controls=[
                ft.Container(
                    width=fill_width,
                    height=_BAR_HEIGHT,
                    bgcolor=color,
                    border_radius=_BAR_HEIGHT / 2,
                )
            ],
            spacing=0,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _item_chip(collection, criminalist, item) -> ft.Container:
    """Мини-карточка одного пункта шаблона для одного криминалиста."""
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
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        tooltip=f"{item.name}: {value_text}",
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(icon, size=11, color=icon_color),
                        ft.Text(
                            item.name,
                            size=9,
                            color=COLORS.get("text_secondary", "#94a3b8"),
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            width=_CHIP_WIDTH - 16 - 15,
                        ),
                    ],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(
                    value_text,
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color=value_color,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    width=_CHIP_WIDTH - 16,
                ),
            ],
            spacing=2,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
    )


def _criminalist_row(collection, criminalist) -> ft.Container:
    fill = get_criminalist_fill(collection, criminalist)
    pct = fill["percent"]
    bar_color, pct_color = _progress_palette(pct)

    name_block = ft.Column(
        controls=[
            ft.Text(
                criminalist.full_name,
                size=12,
                weight=ft.FontWeight.BOLD,
                color=COLORS["text"],
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
                width=_NAME_WIDTH,
                tooltip=criminalist.full_name,
            ),
            ft.Text(
                criminalist.note or f"Отделов: {len(criminalist.zone.department_ids)}",
                size=10,
                color=COLORS.get("text_muted", "#64748b"),
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
                width=_NAME_WIDTH,
            ),
        ],
        spacing=2,
        width=_NAME_WIDTH,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    progress_block = ft.Column(
        controls=[
            _mini_bar(pct, bar_color),
            ft.Text(
                f"{fill['filled_items']}/{fill['total_items']} · {pct}%",
                size=10,
                color=pct_color,
                weight=ft.FontWeight.W_600,
                width=_BAR_WIDTH,
            ),
        ],
        spacing=4,
        width=_BAR_WIDTH,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    if pct >= 100:
        status_icon, status_color, status_label = (
            ft.icons.TASK_ALT, COLORS.get("received_text", "#4ade80"), "Сдал")
    elif pct > 0:
        status_icon, status_color, status_label = (
            ft.icons.HOURGLASS_BOTTOM, COLORS.get("in_progress_text", "#fbbf24"), "Частично")
    else:
        status_icon, status_color, status_label = (
            ft.icons.REPORT_GMAILERRORRED, COLORS.get("text_muted", "#64748b"), "Не сдал")

    status_block = ft.Row(
        controls=[
            ft.Icon(status_icon, size=14, color=status_color),
            ft.Text(status_label, size=10, color=status_color, weight=ft.FontWeight.W_600),
        ],
        spacing=4,
        width=_PCT_WIDTH,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Детализация по пунктам шаблона.
    # ВАЖНО: чипы разбиваются на ФИКСИРОВАННЫЕ ряды по _CHIPS_PER_ROW —
    # без wrap/scroll/expand, чтобы constraints всегда были конечными
    # (тот же приём, что и в сетке плашек, см. AGENTS.md 15.12).
    items = sorted(collection.template.items, key=lambda i: i.order)
    if items:
        chip_rows = []
        for i in range(0, len(items), _CHIPS_PER_ROW):
            chunk = items[i:i + _CHIPS_PER_ROW]
            chip_rows.append(
                ft.Row(
                    controls=[_item_chip(collection, criminalist, it) for it in chunk],
                    spacing=_CHIP_SPACING,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.START,
                )
            )
        chips = ft.Column(
            controls=chip_rows,
            spacing=_CHIP_SPACING,
            width=_CHIPS_BLOCK_WIDTH,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        )
    else:
        chips = ft.Column(
            controls=[
                ft.Text("Пункты шаблона не заданы", size=11,
                        color=COLORS.get("text_muted", "#64748b")),
            ],
            spacing=0,
            width=_CHIPS_BLOCK_WIDTH,
            alignment=ft.MainAxisAlignment.CENTER,
        )

    return ft.Container(
        content=ft.Row(
            controls=[name_block, progress_block, status_block, chips],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=COLORS.get("primary_light", "#1e293b"),
        border=ft.border.all(1, COLORS.get("border", "#334155")),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
    )


def create_criminalists_summary_panel(
    collection,
    panel_ref: Optional[Dict] = None,
    on_toggle: Optional[Callable] = None,
) -> ft.Column:
    """
    Создать секцию «Сводка по криминалистам».
    Возвращает ft.Column (контракт обновления .controls как у summary_panel).
    """
    is_expanded = bool(panel_ref.get("is_expanded", False)) if panel_ref else False

    s = get_fill_summary(collection)
    active = s["active"]
    inactive = s["inactive"]
    submitted = s["items_submitted"]
    overall = s["overall_percent"]
    bar_color, _ = _progress_palette(overall)

    active_criminalists = [c for c in collection.criminalists if c.is_active]
    done_count = sum(
        1 for c in active_criminalists if get_criminalist_fill(collection, c)["percent"] >= 100
    )

    print(f"[CRIM_SUMMARY] expanded={is_expanded} active={active} submitted={submitted} overall={overall}")

    def _toggle(e):
        if panel_ref is not None:
            panel_ref["is_expanded"] = not panel_ref.get("is_expanded", False)
        if on_toggle is not None:
            on_toggle()

    def _pill(icon, text: str, color: str) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=13, color=color),
                    ft.Text(text, size=11, color=COLORS["text"], weight=ft.FontWeight.W_500),
                ],
                spacing=5,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=COLORS.get("card", "#15202e"),
            border=ft.border.all(1, COLORS.get("border", "#334155")),
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
        )

    header_left = ft.Row(
        controls=[
            ft.Container(
                content=ft.Icon(ft.icons.GROUPS_2, size=16, color="white"),
                width=28, height=28,
                bgcolor=COLORS.get("btn_save", "#3b82f6"),
                border_radius=8,
                alignment=ft.alignment.center,
            ),
            ft.Text("Сводка по криминалистам", size=14, weight=ft.FontWeight.BOLD, color="white"),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    header_stats = ft.Row(
        controls=[
            _pill(ft.icons.PERSON_OUTLINE, f"Активных: {active}",
                  COLORS.get("received_text", "#4ade80")),
            _pill(ft.icons.CHECK_CIRCLE_OUTLINE, f"Сдали: {done_count}",
                  COLORS.get("stat_blue_text", "#60a5fa")),
            _pill(ft.icons.LIST_ALT, f"Пунктов: {submitted}",
                  COLORS.get("in_progress_text", "#fbbf24")),
            _pill(ft.icons.TRENDING_UP, f"{overall}%",
                  COLORS.get("text_secondary", "#94a3b8")),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    header = ft.Container(
        content=ft.Row(
            controls=[
                header_left,
                ft.Container(width=10),
                header_stats,
                ft.Container(width=10),
                _mini_bar(overall, bar_color),
                ft.Icon(
                    ft.icons.KEYBOARD_ARROW_UP if is_expanded else ft.icons.KEYBOARD_ARROW_DOWN,
                    size=20, color="white",
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        gradient=ft.LinearGradient(
            begin=ft.alignment.center_left,
            end=ft.alignment.center_right,
            colors=[COLORS["primary"], COLORS["primary_light"]],
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border_radius=ft.border_radius.all(12) if not is_expanded
        else ft.border_radius.only(top_left=12, top_right=12),
        ink=True,
        on_click=_toggle,
        tooltip="Нажмите, чтобы свернуть детализацию" if is_expanded
        else "Нажмите, чтобы развернуть детализацию по криминалистам",
    )

    if not is_expanded:
        card = ft.Container(
            content=header,
            height=56,
            border=ft.border.all(1, COLORS.get("border", "#334155")),
            border_radius=12,
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=8,
                                color="#00000055", offset=ft.Offset(0, 2)),
        )
        return ft.Column(controls=[card], spacing=0)

    # ── Развёрнутый вид ──────────────────────────────────────────
    rows = []
    if not active_criminalists:
        rows.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.icons.INFO_OUTLINE, size=16,
                                color=COLORS.get("text_muted", "#64748b")),
                        ft.Text("Нет активных криминалистов в текущем сборе",
                                size=12, color=COLORS.get("text_secondary", "#94a3b8")),
                    ],
                    spacing=8,
                ),
                padding=ft.padding.all(12),
            )
        )
    else:
        for c in active_criminalists:
            rows.append(_criminalist_row(collection, c))

    legend = ft.Row(
        controls=[
            ft.Row(
                controls=[
                    ft.Icon(ft.icons.CHECK_CIRCLE, size=12,
                            color=COLORS.get("received_text", "#4ade80")),
                    ft.Text("сдано", size=10, color=COLORS.get("text_secondary", "#94a3b8")),
                ],
                spacing=4,
            ),
            ft.Row(
                controls=[
                    ft.Icon(ft.icons.RADIO_BUTTON_UNCHECKED, size=12,
                            color=COLORS.get("text_muted", "#64748b")),
                    ft.Text("не сдано", size=10, color=COLORS.get("text_secondary", "#94a3b8")),
                ],
                spacing=4,
            ),
            ft.Text(f"Показаны только активные криминалисты (отключено: {inactive})",
                    size=10, color=COLORS.get("text_muted", "#64748b")),
        ],
        spacing=16,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    body = ft.Container(
        content=ft.Column(
            controls=[legend, ft.Container(height=6)] + rows,
            spacing=8,
            tight=True,
        ),
        padding=ft.padding.all(12),
        bgcolor=COLORS.get("card", "#15202e"),
        border_radius=ft.border_radius.only(bottom_left=12, bottom_right=12),
    )

    card = ft.Container(
        content=ft.Column(controls=[header, body], spacing=0),
        border=ft.border.all(1, COLORS.get("border", "#334155")),
        border_radius=12,
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=10,
                            color="#00000066", offset=ft.Offset(0, 3)),
    )
    return ft.Column(controls=[card], spacing=0)

# ui/zonal/detailed_summary_panel.py
# Новая разворачиваемая секция "Сводка по криминалистам" с детализацией по пунктам шаблона.
# [DARK THEME] + ft.icons.* (Flet 0.23.2)
import flet as ft
from typing import Callable, Optional, Dict, List
from core.constants import COLORS
from core.zonal_models import ReportItemType
from core.zonal_data import get_criminalist_fill, is_item_filled

def _find_rd(collection, crim_id: int, item_id: str):
    for sub in collection.submissions:
        if sub.criminalist_id == crim_id and sub.template_item_id == item_id:
            return sub
    return None

def _item_display_text(collection, criminalist, item, rd):
    """Сформировать текст значения для пункта."""
    use_dept = collection.template.use_departments_mode and bool(criminalist.zone.department_ids)
    if item.item_type == ReportItemType.NUMERICAL:
        if use_dept:
            if rd is None:
                return "—"
            # посчитать заполненные по отделам
            filled_vals = []
            total = 0
            cnt = 0
            for did in criminalist.zone.department_ids:
                v = rd.department_values.get(did)
                if v is not None:
                    filled_vals.append(str(v))
                    total += v
                    cnt += 1
            if cnt == 0:
                return "—"
            # если все заполнены — показать сумму
            if cnt == len(criminalist.zone.department_ids):
                unit = f" {item.unit}" if item.unit else ""
                return f"{total}{unit} ({cnt}/{len(criminalist.zone.department_ids)} отд.)"
            else:
                unit = f" {item.unit}" if item.unit else ""
                return f"{total}{unit} ({cnt}/{len(criminalist.zone.department_ids)})"
        else:
            if rd and rd.value is not None:
                unit = f" {item.unit}" if item.unit else ""
                return f"{rd.value}{unit}"
            return "—"
    else:  # deliverable
        if use_dept:
            if rd is None:
                return "Не сдано"
            depts = criminalist.zone.department_ids
            filled = sum(1 for did in depts if rd.department_submitted.get(did, False))
            if filled == len(depts) and len(depts) > 0:
                return f"Сдано ({filled}/{len(depts)})"
            elif filled > 0:
                return f"Частично {filled}/{len(depts)}"
            else:
                return "Не сдано"
        else:
            if rd and rd.is_submitted:
                return "Сдано"
            return "Не сдано"

def _make_criminalist_detail_block(collection, criminalist, dept_map: dict) -> ft.Container:
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

    # шапка криминалиста
    name_row = ft.Row(
        controls=[
            ft.Icon(ft.icons.PERSON, size=14, color=COLORS["text_secondary"]),
            ft.Text(criminalist.full_name, size=12, weight=ft.FontWeight.BOLD, color=COLORS["text"], expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, tooltip=criminalist.full_name),
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.ProgressBar(value=pct/100.0, width=80, height=6, color=bar_color, bgcolor=COLORS["border"]),
                        ft.Text(f"{pct}%", size=11, color=pct_color, weight=ft.FontWeight.W_500),
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            ),
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # отделы кратко
    zone_names = [dept_map.get(did, f"Отдел {did}") for did in criminalist.zone.department_ids]
    zone_text = ", ".join(zone_names) if zone_names else "Нет отделов"
    zone_row = ft.Row(
        controls=[
            ft.Icon(ft.icons.LOCATION_ON, size=11, color=COLORS["text_muted"]),
            ft.Text(zone_text, size=10, color=COLORS["text_secondary"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True, tooltip=zone_text),
        ],
        spacing=4,
    )

    # пункты шаблона
    items_controls: List[ft.Control] = []
    if not collection.template.items:
        items_controls.append(
            ft.Text("Нет пунктов в шаблоне", size=11, color=COLORS["text_muted"], italic=True)
        )
    else:
        for item in collection.template.items:
            rd = _find_rd(collection, criminalist.id, item.id)
            filled = is_item_filled(collection, criminalist, item)
            if filled:
                icon = ft.icons.CHECK_CIRCLE
                icon_color = COLORS["received_text"]
            else:
                icon = ft.icons.CANCEL
                icon_color = COLORS["text_muted"]

            display = _item_display_text(collection, criminalist, item, rd)

            # иконка типа пункта
            type_icon = ft.icons.NUMBERS if item.item_type == ReportItemType.NUMERICAL else ft.icons.FACT_CHECK
            row = ft.Row(
                controls=[
                    ft.Icon(icon, size=13, color=icon_color),
                    ft.Icon(type_icon, size=11, color=COLORS["text_muted"]),
                    ft.Text(item.name, size=11, color=COLORS["text"], expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, tooltip=item.name),
                    ft.Text(display, size=11, color=icon_color if filled else COLORS["text_secondary"], weight=ft.FontWeight.W_500 if filled else ft.FontWeight.W_400),
                ],
                spacing=5,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            items_controls.append(row)

    block = ft.Container(
        content=ft.Column(
            controls=[
                name_row,
                zone_row,
                ft.Divider(height=1, color=COLORS["border"]),
                ft.Column(controls=items_controls, spacing=4, tight=False),
            ],
            spacing=6,
        ),
        padding=ft.padding.all(10),
        bgcolor=COLORS["primary_light"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=8,
    )
    return block

def create_detailed_summary_panel(
    collection,
    dept_map: dict,
    detailed_ref: Optional[Dict] = None,
    on_toggle: Optional[Callable] = None,
) -> ft.Column:
    is_expanded = False
    if detailed_ref is not None:
        is_expanded = detailed_ref.get("is_expanded", False)

    print(f"[DETAILED_SUMMARY] Creating panel: expanded={is_expanded}")

    active_criminals = [c for c in collection.criminalists if c.is_active]
    total_active = len(active_criminals)

    # общий прогресс
    total_pct = 0
    for c in active_criminals:
        total_pct += get_criminalist_fill(collection, c)["percent"]
    overall = round(total_pct / total_active) if total_active else 0

    if overall >= 100:
        bar_color = COLORS["received"]
    elif overall > 0:
        bar_color = COLORS["in_progress"]
    else:
        bar_color = COLORS["empty"]

    def _toggle(e):
        if detailed_ref is not None:
            detailed_ref["is_expanded"] = not detailed_ref.get("is_expanded", False)
        if on_toggle is not None:
            on_toggle()

    if not is_expanded:
        progress_bar = ft.ProgressBar(
            value=overall / 100.0,
            height=8,
            color=bar_color,
            bgcolor=COLORS["border"],
            width=140,
        )
        collapsed_row = ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.icons.LIST_ALT, size=18, color="white"),
                        ft.Text("Сводка по криминалистам", size=13, weight=ft.FontWeight.BOLD, color="white"),
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.VerticalDivider(width=1, color=COLORS["border"]),
                ft.Row(
                    controls=[
                        ft.Icon(ft.icons.GROUPS, size=14, color=COLORS["received_text"]),
                        ft.Text(f"Активных: {total_active}", size=12, color=COLORS["text"], weight=ft.FontWeight.W_500),
                    ],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[
                        ft.Text(f"Общий: {overall}%", size=12, color=COLORS["text"], weight=ft.FontWeight.W_500),
                        progress_bar,
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(expand=True),
                ft.Text("детализация по пунктам", size=11, color=COLORS["text_muted"], italic=True),
                ft.Icon(ft.icons.KEYBOARD_ARROW_DOWN, size=18, color="white"),
            ],
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        card = ft.Container(
            content=collapsed_row,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            gradient=ft.LinearGradient(
                begin=ft.alignment.center_left,
                end=ft.alignment.center_right,
                colors=[COLORS["primary"], COLORS["primary_light"]],
            ),
            border=ft.border.all(1, COLORS["border"]),
            border_radius=10,
            ink=True,
            on_click=_toggle,
            tooltip="Нажмите, чтобы развернуть детализацию по криминалистам",
        )
        return ft.Column(controls=[card], spacing=0)

    # Развернутый вид
    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.icons.LIST_ALT, size=18, color="white"),
                ft.Text("Сводка по криминалистам", size=14, weight=ft.FontWeight.BOLD, color="white"),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Text(f"Активных: {total_active}", size=11, color="white"),
                    bgcolor=COLORS["btn_save"],
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                ),
                ft.Icon(ft.icons.KEYBOARD_ARROW_UP, size=18, color="white"),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        gradient=ft.LinearGradient(
            begin=ft.alignment.center_left,
            end=ft.alignment.center_right,
            colors=[COLORS["primary"], COLORS["primary_light"]],
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border_radius=ft.border_radius.only(top_left=10, top_right=10),
        ink=True,
        on_click=_toggle,
        tooltip="Нажмите, чтобы свернуть",
    )

    if total_active == 0:
        body_content = ft.Container(
            content=ft.Text("Нет активных криминалистов", size=12, color=COLORS["text_muted"]),
            padding=ft.padding.all(12),
        )
    elif not collection.template.items:
        body_content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Шаблон пуст — добавьте пункты в «Настройке сбора данных»", size=12, color=COLORS["text_muted"]),
                    ft.Container(height=8),
                    ft.Column(
                        controls=[
                            _make_criminalist_detail_block(collection, c, dept_map) for c in active_criminals
                        ],
                        spacing=8,
                    ),
                ],
                spacing=8,
            ),
            padding=ft.padding.all(10),
        )
    else:
        # сетка деталей: 2 колонки для экономии места, но не используем ResponsiveRow с expand проблемой — используем обычные Row по 2
        detail_blocks = [_make_criminalist_detail_block(collection, c, dept_map) for c in active_criminals]
        # разбить по 2 в ряд, каждый блок ширина ~ 520? Но у нас ширина ограничена. Сделаем вертикальный список для надежности.
        # Чтобы красиво распределить и сохранить компактность, используем Column с spacing.
        # Если хочется 2 колонки — используем Row по 2, каждый внутри Container expand.
        rows = []
        per_row = 2
        for i in range(0, len(detail_blocks), per_row):
            chunk = detail_blocks[i:i+per_row]
            if len(chunk) == 1:
                rows.append(ft.Row(controls=[ft.Container(content=chunk[0], expand=True)], spacing=10))
            else:
                rows.append(
                    ft.Row(
                        controls=[
                            ft.Container(content=chunk[0], expand=True),
                            ft.Container(content=chunk[1], expand=True),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    )
                )
        body_content = ft.Container(
            content=ft.Column(controls=rows, spacing=10),
            padding=ft.padding.all(10),
        )

    body = ft.Container(
        content=body_content,
        bgcolor=COLORS["card"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=ft.border_radius.only(bottom_left=10, bottom_right=10),
        padding=ft.padding.all(4),
    )

    card = ft.Container(
        content=ft.Column(controls=[header, body], spacing=0),
        border=ft.border.all(1, COLORS["border"]),
        border_radius=10,
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#00000060", offset=ft.Offset(0, 2)),
    )

    return ft.Column(controls=[card], spacing=0)

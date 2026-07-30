# ui/zonal/form_fields.py
# Переиспользуемые блоки ввода формы (числовые / да-нет / по отделам).
# Используются в модальном окне заполнения формы (form_input_modal.py).
# [DARK THEME] + ft.icons.* + hint_style (Flet 0.23.2)
import flet as ft
from datetime import datetime
from core.zonal_models import ReportItemType, ReportData
from core.zonal_data import get_report_data
from core.constants import COLORS


def build_item_block(
    item,
    rd: ReportData,
    criminalist,
    collection,
    on_change: callable,
    dept_map: dict,
) -> ft.Container:
    """
    Создать блок одного пункта шаблона для ввода данных.
    Возвращает ft.Container.
    """
    # Детализация по отделам относится только к количественным показателям.
    # «Да/нет» означает факт сдачи всей формы криминалистом, поэтому даже
    # при включенном режиме по отделам для него всегда одна общая галочка.
    use_dept_mode = (
        item.item_type == ReportItemType.NUMERICAL
        and collection.template.use_departments_mode
        and bool(criminalist.zone.department_ids)
    )
    if use_dept_mode:
        return _build_dept_mode_block(item, rd, criminalist, on_change, dept_map)

    submitted_value = rd.is_submitted
    # Совместимость с данными, введёнными до изменения: старые галочки по
    # отделам считаются сданными только когда сданы все закреплённые отделы.
    if (item.item_type == ReportItemType.DELIVERABLE
            and collection.template.use_departments_mode
            and rd.department_submitted
            and criminalist.zone.department_ids):
        submitted_value = all(
            rd.department_submitted.get(department_id, False)
            for department_id in criminalist.zone.department_ids
        )
    return _build_simple_mode_block(item, rd, on_change, submitted_value)


def _build_simple_mode_block(
    item,
    rd: ReportData,
    on_change: callable,
    submitted_value: bool = False,
) -> ft.Container:
    """Блок пункта с общим значением или одной общей галочкой."""
    if item.item_type == ReportItemType.NUMERICAL:
        value_field = ft.TextField(
            value=str(rd.value) if rd.value is not None else "",
            hint_text="0",
            border_radius=8,
            border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"],
            color=COLORS["text"],
            hint_style=ft.TextStyle(color=COLORS["text_muted"]),
            height=38,
            text_size=14,
            width=110,
            keyboard_type=ft.KeyboardType.NUMBER,
            suffix_text=item.unit or "",
            suffix_style=ft.TextStyle(color=COLORS["text_secondary"]),
            on_change=lambda e: _on_numerical_change(e, rd, on_change),
        )
        icon = ft.Icon(ft.icons.NUMBERS, size=16, color=COLORS["stat_blue_text"])
        controls = [
            icon,
            ft.Text(item.name, size=13, color=COLORS["text"], expand=True),
            value_field,
        ]
    else:
        checkbox = ft.Checkbox(
            label="Сдано",
            value=submitted_value,
            active_color=COLORS["received"],
            label_style=ft.TextStyle(size=13, color=COLORS["text"]),
            on_change=lambda e: _on_deliverable_change(e, rd, on_change),
        )
        icon = ft.Icon(ft.icons.CHECK_CIRCLE, size=16, color=COLORS["received_text"])
        controls = [
            icon,
            ft.Text(item.name, size=13, color=COLORS["text"], expand=True),
            checkbox,
        ]

    return ft.Container(
        content=ft.Row(
            controls=controls,
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=COLORS["primary_light"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
    )


def _build_dept_mode_block(
    item, rd: ReportData, criminalist, on_change: callable, dept_map: dict
) -> ft.Container:
    """Блок числового пункта в режиме детализации по отделам."""
    dept_rows = []
    total_ref = {"value": 0}

    total_label = ft.Text(
        f"Итого: {total_ref['value']}{(' ' + item.unit) if item.unit else ''}",
        size=12,
        weight=ft.FontWeight.BOLD,
        color=COLORS["btn_save"],
    )

    def _update_total():
        if item.item_type == ReportItemType.NUMERICAL:
            s = sum(v for v in rd.department_values.values() if v is not None)
            total_label.value = f"Итого: {s}{(' ' + item.unit) if item.unit else ''}"
        try:
            total_label.update()
        except Exception:
            pass

    for dept_id in criminalist.zone.department_ids:
        dept_name = dept_map.get(dept_id, f"Отдел {dept_id}")

        if item.item_type == ReportItemType.NUMERICAL:
            current_val = rd.department_values.get(dept_id)
            dept_field = ft.TextField(
                value=str(current_val) if current_val is not None else "",
                hint_text="0",
                border_radius=6,
                border_color=COLORS["border"],
                focused_border_color=COLORS["btn_save"],
                bgcolor=COLORS["card"],
                color=COLORS["text"],
                hint_style=ft.TextStyle(color=COLORS["text_muted"]),
                height=34,
                text_size=12,
                width=90,
                keyboard_type=ft.KeyboardType.NUMBER,
                on_change=lambda e, did=dept_id: _on_dept_numerical_change(
                    e, rd, did, _update_total, on_change
                ),
            )
            dept_row = ft.Row(
                controls=[
                    ft.Text(dept_name, size=12, color=COLORS["text"], expand=True),
                    dept_field,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        else:
            current_submitted = rd.department_submitted.get(dept_id, False)
            dept_checkbox = ft.Checkbox(
                label=dept_name,
                value=current_submitted,
                active_color=COLORS["received"],
                label_style=ft.TextStyle(size=12, color=COLORS["text"]),
                on_change=lambda e, did=dept_id: _on_dept_deliverable_change(
                    e, rd, did, on_change
                ),
            )
            dept_row = dept_checkbox

        dept_rows.append(dept_row)

    _update_total()

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.icons.NUMBERS, size=14, color=COLORS["stat_blue_text"]),
                        ft.Text(
                            item.name,
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=COLORS["text"],
                            expand=True,
                        ),
                        total_label,
                    ],
                    spacing=8,
                ),
                ft.Container(
                    content=ft.Column(controls=dept_rows, spacing=4),
                    padding=ft.padding.only(left=16),
                ),
            ],
            spacing=6,
        ),
        bgcolor=COLORS["primary_light"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=8,
        padding=ft.padding.all(12),
    )


def build_comment_block(collection, criminalist, on_change: callable) -> ft.Container:
    """Поле общего комментария (привязано к первому пункту шаблона)."""
    comment_val = ""
    if collection.template.items:
        first_item = collection.template.items[0]
        rd = get_report_data(collection, criminalist.id, first_item.id)
        comment_val = rd.comment

    comment_field = ft.TextField(
        value=comment_val,
        hint_text="Комментарий (необязательно)...",
        border_radius=8,
        border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"],
        color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        text_size=13,
        multiline=True,
        min_lines=1,
        max_lines=3,
        expand=True,
        on_change=lambda e: _on_comment_change(e, collection, criminalist, on_change),
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.icons.COMMENT, size=14, color=COLORS["text_secondary"]),
                ft.Text("Комментарий:", size=12, color=COLORS["text_secondary"]),
                comment_field,
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        padding=ft.padding.symmetric(horizontal=4, vertical=4),
    )


# ── Обработчики изменений ──────────────────────────────────────

def _on_numerical_change(e, rd: ReportData, on_change: callable):
    try:
        rd.value = int(e.control.value) if e.control.value.strip() else None
    except ValueError:
        rd.value = None
    rd.updated_at = datetime.now()
    on_change()


def _on_deliverable_change(e, rd: ReportData, on_change: callable):
    # «Да/нет» больше не хранится отдельно по каждому отделу.
    rd.is_submitted = e.control.value
    rd.department_submitted.clear()
    rd.updated_at = datetime.now()
    on_change()


def _on_dept_numerical_change(e, rd: ReportData, dept_id: int,
                               update_total: callable, on_change: callable):
    try:
        val = int(e.control.value) if e.control.value.strip() else None
        if val is not None:
            rd.department_values[dept_id] = val
        else:
            rd.department_values.pop(dept_id, None)
    except ValueError:
        rd.department_values.pop(dept_id, None)
    rd.value = sum(v for v in rd.department_values.values())
    rd.updated_at = datetime.now()
    update_total()
    on_change()


def _on_dept_deliverable_change(e, rd: ReportData, dept_id: int, on_change: callable):
    rd.department_submitted[dept_id] = e.control.value
    rd.is_submitted = any(rd.department_submitted.values())
    rd.updated_at = datetime.now()
    on_change()


def _on_comment_change(e, collection, criminalist, on_change: callable):
    if collection.template.items:
        first_item = collection.template.items[0]
        rd = get_report_data(collection, criminalist.id, first_item.id)
        rd.comment = e.control.value
    on_change()

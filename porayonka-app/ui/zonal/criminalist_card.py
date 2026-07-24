# ui/zonal/criminalist_card.py
# Карточка зонального криминалиста (раскрывающаяся)
# [DARK THEME] Обновлено визуально + исправлено hint_text_color
import flet as ft
from typing import Callable, Dict
from datetime import datetime
from core.zonal_models import (
    ZonalCollection, Criminalist, ReportItemType,
    ReportData, ReportTemplateItem,
)
from core.zonal_data import get_report_data
from core.constants import COLORS, INITIAL_DEPARTMENTS


def create_criminalist_card(
    page: ft.Page,
    criminalist: Criminalist,
    collection: ZonalCollection,
    on_data_change: Callable,
    on_zone_edit: Callable,
    on_delete_criminalist: Callable,
    on_toggle_active: Callable,  # ← НОВЫЙ колбэк
    dept_map: Dict[int, str],
) -> ft.Column:
    """
    Создать раскрывающуюся карточку криминалиста.
    Возвращает ft.Column (чтобы можно было обновить controls).
    """
    print(f"[CRIM_CARD] Создаю карточку: {criminalist.full_name}")

    template = collection.template
    use_dept_mode = template.use_departments_mode

    # ── Состояние раскрытия ──────────────────────────────────────
    is_expanded = {"value": False}

    # ── Зоны обслуживания ────────────────────────────────────────
    zone_names = [dept_map.get(did, f"Отдел {did}") for did in criminalist.zone.department_ids]
    zone_text = ", ".join(zone_names) if zone_names else "Нет закреплённых отделов"

    # ── Содержимое карточки (раскрытое) ─────────────────────────
    body_col = ft.Column(spacing=8, visible=False)

    def _rebuild_body():
        """Перестроить тело карточки"""
        body_col.controls.clear()
        if not template.items:
            body_col.controls.append(
                ft.Container(
                    content=ft.Text(
                        "Нет пунктов шаблона. Добавьте пункты в конструкторе.",
                        size=13,
                        color=COLORS["text_muted"],
                        italic=True,
                    ),
                    padding=ft.padding.all(12),
                )
            )
        else:
            for item in sorted(template.items, key=lambda x: x.order):
                rd = get_report_data(collection, criminalist.id, item.id)
                body_col.controls.append(
                    _make_item_block(item, rd)
                )
        # Поле комментария (общий)
        body_col.controls.append(_make_comment_block())
        try:
            body_col.update()
        except Exception:
            pass

    def _make_item_block(item: ReportTemplateItem, rd: ReportData) -> ft.Container:
        """Создать блок одного пункта отчёта"""
        if use_dept_mode and criminalist.zone.department_ids:
            return _make_dept_mode_block(item, rd)
        else:
            return _make_simple_mode_block(item, rd)

    def _make_simple_mode_block(item: ReportTemplateItem, rd: ReportData) -> ft.Container:
        """Блок пункта в режиме 1 (общие значения)"""
        if item.item_type == ReportItemType.NUMERICAL:
            # Числовое поле
            value_field = ft.TextField(
                value=str(rd.value) if rd.value is not None else "",
                hint_text="0",
                border_radius=8,
                border_color=COLORS["border"],
                focused_border_color=COLORS["btn_save"],
                bgcolor=COLORS["card"],  # ТЁМНЫЙ ФОН
                color=COLORS["text"],    # ТЁМНЫЙ ТЕКСТ
                # ИСПРАВЛЕНИЕ: hint_style вместо hint_text_color
                hint_style=ft.TextStyle(color=COLORS["text_muted"]),
                height=38,
                text_size=14,
                width=100,
                keyboard_type=ft.KeyboardType.NUMBER,
                suffix_text=item.unit or "",
                suffix_style=ft.TextStyle(color=COLORS["text_secondary"]),
                on_change=lambda e, r=rd: _on_numerical_change(e, r),
            )
            icon = ft.Text("📊", size=16)
            controls = [icon, ft.Text(item.name, size=13, color=COLORS["text"], expand=True), value_field]
        else:
            # Чекбокс
            submitted_date = ""
            if rd.is_submitted and rd.updated_at:
                submitted_date = rd.updated_at.strftime("%d.%m.%Y")

            checkbox = ft.Checkbox(
                label=f"Сдано{(' ' + submitted_date) if submitted_date else ''}",
                value=rd.is_submitted,
                active_color=COLORS["received"],
                label_style=ft.TextStyle(size=13, color=COLORS["text"]),
                on_change=lambda e, r=rd: _on_deliverable_change(e, r),
            )
            icon = ft.Text("✅", size=16)
            controls = [icon, ft.Text(item.name, size=13, color=COLORS["text"], expand=True), checkbox]

        return ft.Container(
            content=ft.Row(
                controls=controls,
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=COLORS["primary_light"],  # ТЁМНЫЙ ФОН
            border=ft.border.all(1, COLORS["border"]),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

    def _make_dept_mode_block(item: ReportTemplateItem, rd: ReportData) -> ft.Container:
        """Блок пункта в режиме 2 (по отделам)"""
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
                    bgcolor=COLORS["card"],  # ТЁМНЫЙ ФОН
                    color=COLORS["text"],    # ТЁМНЫЙ ТЕКСТ
                    # ИСПРАВЛЕНИЕ: hint_style вместо hint_text_color
                    hint_style=ft.TextStyle(color=COLORS["text_muted"]),
                    height=34,
                    text_size=12,
                    width=80,
                    keyboard_type=ft.KeyboardType.NUMBER,
                    on_change=lambda e, did=dept_id: _on_dept_numerical_change(e, rd, did, _update_total),
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
                    on_change=lambda e, did=dept_id: _on_dept_deliverable_change(e, rd, did),
                )
                dept_row = dept_checkbox

            dept_rows.append(dept_row)

        # Пересчитать итого при загрузке
        _update_total()

        return ft.Container(
            content=ft.Column(
                controls=[
                    # Заголовок пункта
                    ft.Row(
                        controls=[
                            ft.Text("📊", size=14),
                            ft.Text(
                                item.name,
                                size=13,
                                weight=ft.FontWeight.W_600,
                                color=COLORS["text"],
                                expand=True,
                            ),
                        ],
                        spacing=8,
                    ),
                    # Строки по отделам
                    ft.Container(
                        content=ft.Column(
                            controls=dept_rows,
                            spacing=4,
                        ),
                        padding=ft.padding.only(left=16),
                    ),
                    # Итого
                    ft.Divider(height=1, color=COLORS["border"]),
                    total_label,
                ],
                spacing=6,
            ),
            bgcolor=COLORS["primary_light"],  # ТЁМНЫЙ ФОН
            border=ft.border.all(1, COLORS["border"]),
            border_radius=8,
            padding=ft.padding.all(12),
        )

    def _make_comment_block() -> ft.Container:
        """Поле общего комментария"""
        # Найти первую запись для комментария (или создать)
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
            bgcolor=COLORS["card"],  # ТЁМНЫЙ ФОН
            color=COLORS["text"],    # ТЁМНЫЙ ТЕКСТ
            # ИСПРАВЛЕНИЕ: hint_style вместо hint_text_color
            hint_style=ft.TextStyle(color=COLORS["text_muted"]),
            text_size=13,
            multiline=True,
            min_lines=1,
            max_lines=3,
            expand=True,
            on_change=lambda e: _on_comment_change(e),
        )

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text("💬", size=14),
                    ft.Text("Комментарий:", size=12, color=COLORS["text_secondary"]),
                    comment_field,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=ft.padding.symmetric(horizontal=4, vertical=4),
        )

    # ── Обработчики изменений ────────────────────────────────────

    def _on_numerical_change(e, rd: ReportData):
        try:
            rd.value = int(e.control.value) if e.control.value.strip() else None
        except ValueError:
            rd.value = None
        rd.updated_at = datetime.now()
        on_data_change()

    def _on_deliverable_change(e, rd: ReportData):
        rd.is_submitted = e.control.value
        rd.updated_at = datetime.now()
        on_data_change()

    def _on_dept_numerical_change(e, rd: ReportData, dept_id: int, update_total: Callable):
        try:
            val = int(e.control.value) if e.control.value.strip() else None
            if val is not None:
                rd.department_values[dept_id] = val
            else:
                rd.department_values.pop(dept_id, None)
        except ValueError:
            rd.department_values.pop(dept_id, None)
        # Синхронизировать общее значение
        rd.value = sum(v for v in rd.department_values.values())
        rd.updated_at = datetime.now()
        update_total()
        on_data_change()

    def _on_dept_deliverable_change(e, rd: ReportData, dept_id: int):
        rd.department_submitted[dept_id] = e.control.value
        rd.is_submitted = any(rd.department_submitted.values())
        rd.updated_at = datetime.now()
        on_data_change()

    def _on_comment_change(e):
        if collection.template.items:
            first_item = collection.template.items[0]
            rd = get_report_data(collection, criminalist.id, first_item.id)
            rd.comment = e.control.value
        on_data_change()

    # ── Заголовок карточки (кликабельный) ───────────────────────
    expand_icon = ft.Text("▶", size=12, color=COLORS["text_secondary"])

    def _toggle_expand(e=None):
        is_expanded["value"] = not is_expanded["value"]
        body_col.visible = is_expanded["value"]
        expand_icon.value = "▼" if is_expanded["value"] else "▶"
        if is_expanded["value"]:
            _rebuild_body()
        try:
            expand_icon.update()
            body_col.update()
        except Exception:
            pass

    # Название и примечание
    name_text = ft.Text(
        criminalist.full_name,
        size=14,
        weight=ft.FontWeight.W_600,
        color=COLORS["text"],
        expand=True,
    )
    note_text = ft.Text(
        f"({criminalist.note})" if criminalist.note else "",
        size=12,
        color=COLORS["text_secondary"],
        italic=True,
        visible=bool(criminalist.note),
    )

    # Кнопки управления (активность + зоны + удалить)
    
    # КНОПКА: Активность
    active_icon = ft.Icons.VISIBILITY if criminalist.is_active else ft.Icons.VISIBILITY_OFF
    active_color = COLORS["btn_save"] if criminalist.is_active else "#64748b"
    active_tooltip = "Активен — участвует в сборе" if criminalist.is_active else "Отключён — не участвует в сборе"
    
    toggle_active_btn = ft.IconButton(
        icon=active_icon,
        icon_size=18,
        icon_color=active_color,
        tooltip=active_tooltip,
        on_click=lambda e: on_toggle_active(criminalist),
        style=ft.ButtonStyle(padding=ft.padding.all(4)),
    )
    
    # КНОПКА: Редактировать зоны
    edit_zone_btn = ft.IconButton(
        icon=ft.Icons.EDIT,
        icon_size=18,
        icon_color=COLORS["btn_save"],
        tooltip="Редактировать зоны",
        on_click=lambda e: on_zone_edit(criminalist),
        style=ft.ButtonStyle(padding=ft.padding.all(4)),
    )
    
    # КНОПКА: Удалить
    delete_btn = ft.IconButton(
        icon=ft.Icons.DELETE_OUTLINE,
        icon_size=18,
        icon_color="#f87171",  # ТЁМНЫЙ КРАСНЫЙ
        tooltip="Удалить криминалиста",
        on_click=lambda e: on_delete_criminalist(criminalist),
        style=ft.ButtonStyle(padding=ft.padding.all(4)),
    )

    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.Text("👤", size=16),
                name_text,
                note_text,
                ft.Container(width=4),  # Отступ
                toggle_active_btn,  # Кнопка активности
                edit_zone_btn,
                delete_btn,
                expand_icon,
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        on_click=_toggle_expand,
        bgcolor=COLORS["card"],  # ТЁМНЫЙ ФОН
        border_radius=ft.border_radius.only(top_left=10, top_right=10),
    )

    def _on_header_hover(e):
        header.bgcolor = COLORS["card_hover"] if e.data == "true" else COLORS["card"]
        try:
            header.update()
        except Exception:
            pass

    header.on_hover = _on_header_hover

    # Строка зон обслуживания
    zone_row = ft.Container(
        content=ft.Row(
            controls=[
                ft.Text("📍", size=12),
                ft.Text(
                    f"Закреплено: {zone_text}",
                    size=12,
                    color=COLORS["text_secondary"],
                    italic=True,
                ),
            ],
            spacing=6,
        ),
        padding=ft.padding.only(left=14, right=14, top=4, bottom=8),
        bgcolor=COLORS["card"],  # ТЁМНЫЙ ФОН
    )

    # Тело карточки
    body_container = ft.Container(
        content=body_col,
        padding=ft.padding.all(14),
        bgcolor=COLORS["card"],  # ТЁМНЫЙ ФОН
        border_radius=ft.border_radius.only(bottom_left=10, bottom_right=10),
    )

    # Вся карточка
    card = ft.Container(
        content=ft.Column(
            controls=[header, zone_row, body_container],
            spacing=0,
        ),
        border=ft.border.all(1, COLORS["border"]),
        border_radius=10,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=6,
            color="#00000060",  # ТЁМНАЯ ТЕНЬ
            offset=ft.Offset(0, 2),
        ),
        animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )

    # Возвращаем Column для возможности обновления controls
    result_col = ft.Column(
        controls=[card],
        spacing=0,
    )
    print(f"[CRIM_CARD] Карточка создана: {criminalist.full_name}")
    return result_col
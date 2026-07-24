# ui/zonal/fill_form_modal.py
# Модальное окно заполнения данных формы для криминалиста
# Внутри: список пунктов шаблона с полями ввода
import flet as ft
from typing import Callable, Dict
from datetime import datetime
from core.zonal_models import (
    ZonalCollection, Criminalist, ReportItemType,
    ReportData, ReportTemplateItem,
)
from core.zonal_data import get_report_data
from core.constants import COLORS, INITIAL_DEPARTMENTS


def create_fill_form_modal(
    page: ft.Page,
    criminalist: Criminalist,
    collection: ZonalCollection,
    on_save: Callable,  # on_save() - вызывается после сохранения
    dept_map: Dict[int, str],
) -> ft.AlertDialog:
    """
    Создать модальное окно заполнения данных.
    """
    print(f"[FILL_MODAL] Sozdau formu dlya: {criminalist.full_name}")
    
    template = collection.template
    use_dept_mode = template.use_departments_mode
    
    # Список пунктов ввода
    items_column = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO)
    
    def _build_items():
        items_column.controls.clear()
        
        if not template.items:
            items_column.controls.append(
                ft.Container(
                    content=ft.Text(
                        "Net punktov v shablone. Dobavte ih v konstruktore.",
                        size=13,
                        color=COLORS["text_muted"],
                        italic=True,
                    ),
                    padding=ft.padding.all(16),
                )
            )
            return
        
        for item in sorted(template.items, key=lambda x: x.order):
            rd = get_report_data(collection, criminalist.id, item.id)
            items_column.controls.append(
                _make_item_block(item, rd)
            )
        
        # Поле комментария
        items_column.controls.append(_make_comment_block())
    
    def _make_item_block(item: ReportTemplateItem, rd: ReportData) -> ft.Container:
        """Создать блок одного пункта"""
        if use_dept_mode and criminalist.zone.department_ids:
            return _make_dept_mode_block(item, rd)
        else:
            return _make_simple_mode_block(item, rd)
    
    def _make_simple_mode_block(item: ReportTemplateItem, rd: ReportData) -> ft.Container:
        """Блок пункта в простом режиме"""
        if item.item_type == ReportItemType.NUMERICAL:
            value_field = ft.TextField(
                value=str(rd.value) if rd.value is not None else "",
                hint_text="0",
                border_radius=6,
                border_color=COLORS["border"],
                focused_border_color=COLORS["btn_save"],
                bgcolor=COLORS["card"],
                color=COLORS["text"],
                hint_style=ft.TextStyle(color=COLORS["text_muted"]),
                height=38,
                text_size=14,
                width=100,
                keyboard_type=ft.KeyboardType.NUMBER,
                suffix_text=item.unit or "",
                suffix_style=ft.TextStyle(color=COLORS["text_secondary"]),
                on_change=lambda e, r=rd: _on_numerical_change(e, r),
            )
            controls = [
                ft.Text(item.name, size=13, color=COLORS["text"], expand=True),
                value_field,
            ]
        else:
            submitted_date = ""
            if rd.is_submitted and rd.updated_at:
                submitted_date = " " + rd.updated_at.strftime("%d.%m.%Y")
            
            checkbox = ft.Checkbox(
                label=f"Sdano{submitted_date}",
                value=rd.is_submitted,
                active_color=COLORS["received"],
                label_style=ft.TextStyle(size=13, color=COLORS["text"]),
                on_change=lambda e, r=rd: _on_deliverable_change(e, r),
            )
            controls = [
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
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
        )
    
    def _make_dept_mode_block(item: ReportTemplateItem, rd: ReportData) -> ft.Container:
        """Блок пункта в режиме по отделам"""
        dept_rows = []
        total_ref = {"value": 0}
        
        total_label = ft.Text(
            f"Itogo: {total_ref['value']}{(' ' + item.unit) if item.unit else ''}",
            size=12,
            weight=ft.FontWeight.BOLD,
            color=COLORS["btn_save"],
        )
        
        def _update_total():
            if item.item_type == ReportItemType.NUMERICAL:
                s = sum(v for v in rd.department_values.values() if v is not None)
                total_ref["value"] = s
                total_label.value = f"Itogo: {s}{(' ' + item.unit) if item.unit else ''}"
            try:
                total_label.update()
            except Exception:
                pass
        
        for dept_id in criminalist.zone.department_ids:
            dept_name = dept_map.get(dept_id, f"Otdel {dept_id}")
            
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
        
        _update_total()
        
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(item.name, size=13, weight=ft.FontWeight.W_600, color=COLORS["text"], expand=True),
                            total_label,
                        ],
                        spacing=8,
                    ),
                    ft.Container(
                        content=ft.Column(controls=dept_rows, spacing=4),
                        padding=ft.padding.only(left=16, top=4),
                    ),
                ],
                spacing=6,
            ),
            bgcolor=COLORS["primary_light"],
            border=ft.border.all(1, COLORS["border"]),
            border_radius=8,
            padding=ft.padding.all(12),
        )
    
    def _make_comment_block() -> ft.Container:
        """Поле комментария"""
        comment_val = ""
        if template.items:
            first_item = template.items[0]
            rd = get_report_data(collection, criminalist.id, first_item.id)
            comment_val = rd.comment
        
        comment_field = ft.TextField(
            value=comment_val,
            hint_text="Kommentariy (neobyazatelno)...",
            border_radius=8,
            border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"],
            color=COLORS["text"],
            hint_style=ft.TextStyle(color=COLORS["text_muted"]),
            text_size=13,
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True,
            on_change=lambda e: _on_comment_change(e),
        )
        
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Kommentariy:", size=12, color=COLORS["text_secondary"]),
                    comment_field,
                ],
                spacing=4,
            ),
            padding=ft.padding.symmetric(vertical=4),
        )
    
    # Обработчики изменений
    def _on_numerical_change(e, rd: ReportData):
        try:
            rd.value = int(e.control.value) if e.control.value.strip() else None
        except ValueError:
            rd.value = None
        rd.updated_at = datetime.now()
    
    def _on_deliverable_change(e, rd: ReportData):
        rd.is_submitted = e.control.value
        rd.updated_at = datetime.now()
    
    def _on_dept_numerical_change(e, rd: ReportData, dept_id: int, update_total: Callable):
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
    
    def _on_dept_deliverable_change(e, rd: ReportData, dept_id: int):
        rd.department_submitted[dept_id] = e.control.value
        rd.is_submitted = any(rd.department_submitted.values())
        rd.updated_at = datetime.now()
    
    def _on_comment_change(e):
        if template.items:
            first_item = template.items[0]
            rd = get_report_data(collection, criminalist.id, first_item.id)
            rd.comment = e.control.value
    
    # Построить форму
    _build_items()
    
    # Зоны (кратко)
    zone_names = [dept_map.get(did, f"#{did}") for did in criminalist.zone.department_ids[:5]]
    zones_text = ", ".join(zone_names)
    if len(criminalist.zone.department_ids) > 5:
        zones_text += f" +{len(criminalist.zone.department_ids) - 5}"
    
    # Заголовок
    header = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(criminalist.full_name, size=16, weight=ft.FontWeight.BOLD, color="white"),
                ft.Text(f"({criminalist.note})" if criminalist.note else "", size=12, color=COLORS["text_secondary"]),
                ft.Text(f"Zony: {zones_text}", size=11, color=COLORS["text_muted"]),
            ],
            spacing=2,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        gradient=ft.LinearGradient(
            begin=ft.alignment.center_left,
            end=ft.alignment.center_right,
            colors=[COLORS["primary"], COLORS["primary_light"]],
        ),
        border_radius=ft.border_radius.only(top_left=12, top_right=12),
    )
    
    # Кнопки
    def _close_dialog(e=None):
        dialog.open = False
        page.update()
    
    def _save_and_close(e=None):
        if on_save:
            on_save()
        dialog.open = False
        page.update()
    
    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=COLORS["primary_light"],
        title=header,
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(height=8),
                    items_column,
                    ft.Container(height=8),
                ],
                spacing=0,
            ),
            width=500,
            height=500,
        ),
        actions=[
            ft.TextButton(
                "Otemena",
                style=ft.ButtonStyle(
                    color=COLORS["text_secondary"],
                    bgcolor=COLORS["empty_bg"],
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=20, vertical=10),
                ),
                expand=True,
                on_click=_close_dialog,
            ),
            ft.ElevatedButton(
                "[OK] Sohranit",
                bgcolor=COLORS["btn_save"],
                color="white",
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=20, vertical=10),
                ),
                expand=True,
                on_click=_save_and_close,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        shape=ft.RoundedRectangleBorder(radius=12),
    )
    
    print(f"[FILL_MODAL] Modal sozdana dlya: {criminalist.full_name}")
    return dialog

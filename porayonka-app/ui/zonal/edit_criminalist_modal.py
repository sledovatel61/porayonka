# ui/zonal/edit_criminalist_modal.py
# Модальное окно редактирования криминалиста
# Включает: ФИО, примечание, активность, зоны, удаление
import flet as ft
from typing import Callable, Optional, Dict, List
from core.zonal_models import Criminalist, CriminalistZone
from core.constants import COLORS, INITIAL_DEPARTMENTS


def create_edit_criminalist_modal(
    page: ft.Page,
    criminalist: Optional[Criminalist],
    on_save: Callable,  # on_save(full_name, note, is_active, department_ids)
    on_delete: Callable,  # on_delete()
    existing_ids: Optional[List[int]] = None,
) -> ft.AlertDialog:
    """
    Создать модальное окно редактирования/добавления криминалиста.
    """
    print("[EDIT_MODAL] Создаю модалку редактирования")
    is_new = criminalist is None
    
    # Поле ФИО
    name_field = ft.TextField(
        value=criminalist.full_name if criminalist else "",
        label="FIO kriminalista",
        hint_text="Primer: Ivanov Ivan Ivanovich",
        border_radius=8,
        border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"],
        color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        expand=True,
    )
    
    # Поле примечания
    note_field = ft.TextField(
        value=criminalist.note if criminalist else "",
        label="Primechanie",
        hint_text="Naprimer: Cifrovaya kriminalistika",
        border_radius=8,
        border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"],
        color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        expand=True,
    )
    
    # Переключатель активности
    active_switch = ft.Switch(
        label="Uchastvuet v sbore" if is_new else "Aktiven",
        value=criminalist.is_active if criminalist else True,
        active_color=COLORS["received"],
        label_style=ft.TextStyle(color=COLORS["text"]),
    )
    
    # Выбор отделов
    dept_map = {d["id"]: d["name"] for d in INITIAL_DEPARTMENTS}
    selected_ids: set = set(existing_ids) if existing_ids else set()
    
    if criminalist:
        selected_ids = set(criminalist.zone.department_ids)
    
    checkboxes: dict = {}
    dept_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=250)
    
    def _build_dept_list():
        dept_list.controls.clear()
        for dept_data in INITIAL_DEPARTMENTS:
            did = dept_data["id"]
            dname = dept_data["name"]
            cb = ft.Checkbox(
                label=f"[{did}] {dname}",
                value=(did in selected_ids),
                active_color=COLORS["btn_save"],
                label_style=ft.TextStyle(
                    size=12,
                    italic=dept_data.get("is_ovd", False),
                    color=COLORS["text_secondary"] if dept_data.get("is_ovd", False) else COLORS["text"],
                ),
                on_change=lambda e, d=did: _on_cb_change(e, d),
            )
            checkboxes[did] = cb
            dept_list.controls.append(cb)
    
    def _on_cb_change(e, dept_id: int):
        if e.control.value:
            selected_ids.add(dept_id)
        else:
            selected_ids.discard(dept_id)
    
    def _select_all(e=None):
        for did, cb in checkboxes.items():
            selected_ids.add(did)
            cb.value = True
        try:
            dept_list.update()
        except Exception:
            pass
    
    def _deselect_all(e=None):
        for did, cb in checkboxes.items():
            selected_ids.discard(did)
            cb.value = False
        try:
            dept_list.update()
        except Exception:
            pass
    
    _build_dept_list()
    
    # Обработчики
    def _close_dialog(e=None):
        dialog.open = False
        page.update()
    
    def _save(e=None):
        full_name = name_field.value.strip()
        if not full_name:
            name_field.error_text = "Vvedite FIO"
            name_field.update()
            return
        
        note = note_field.value.strip()
        is_active = active_switch.value
        
        if on_save:
            on_save(full_name, note, is_active, sorted(list(selected_ids)))
        
        dialog.open = False
        page.update()
    
    def _delete(e=None):
        if on_delete:
            on_delete()
        dialog.open = False
        page.update()
    
    # Кнопки
    actions = [
        ft.TextButton(
            "Otmena",
            style=ft.ButtonStyle(
                color=COLORS["text_secondary"],
                bgcolor=COLORS["empty_bg"],
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
            ),
            expand=True,
            on_click=_close_dialog,
        ),
    ]
    
    # Кнопка удаления только при редактировании
    if not is_new:
        actions.insert(0, ft.ElevatedButton(
            "[X] Udalit",
            bgcolor="#dc2626",
            color=COLORS["text_light"],
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
            ),
            on_click=_delete,
        ))
    
    actions.append(ft.ElevatedButton(
        "[OK] Sohranit",
        bgcolor=COLORS["btn_save"],
        color="white",
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
        ),
        expand=True,
        on_click=_save,
    ))
    
    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=COLORS["primary_light"],
        title=ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(">> ", size=18),
                    ft.Text(
                        "Dobavit kriminalista" if is_new else "Redaktirovat",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color="white",
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.icons.CLOSE,
                        icon_color="white",
                        icon_size=18,
                        on_click=_close_dialog,
                        style=ft.ButtonStyle(padding=ft.padding.all(4)),
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            gradient=ft.LinearGradient(
                begin=ft.alignment.center_left,
                end=ft.alignment.center_right,
                colors=[COLORS["primary"], COLORS["primary_light"]],
            ),
            border_radius=ft.border_radius.only(top_left=12, top_right=12),
        ),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(height=8),
                    name_field,
                    ft.Container(height=10),
                    note_field,
                    ft.Container(height=10),
                    active_switch,
                    ft.Container(height=12),
                    ft.Row(
                        controls=[
                            ft.Text(
                                "Zakreplennye otdely:",
                                size=13,
                                weight=ft.FontWeight.W_600,
                                color=COLORS["text"],
                                expand=True,
                            ),
                            ft.TextButton(
                                "Vse",
                                on_click=_select_all,
                                style=ft.ButtonStyle(color=COLORS["btn_save"]),
                            ),
                            ft.TextButton(
                                "Sniat",
                                on_click=_deselect_all,
                                style=ft.ButtonStyle(color="#f87171"),
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Container(
                        content=dept_list,
                        border=ft.border.all(1, COLORS["border"]),
                        border_radius=8,
                        padding=ft.padding.all(8),
                        bgcolor=COLORS["card"],
                    ),
                ],
                spacing=8,
            ),
            width=500,
        ),
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        shape=ft.RoundedRectangleBorder(radius=12),
    )
    
    print("[EDIT_MODAL] Modal sozdana")
    return dialog

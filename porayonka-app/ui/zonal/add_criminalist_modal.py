# ui/zonal/add_criminalist_modal.py
# Модальное окно добавления/редактирования криминалиста.
# В режиме редактирования允许 удаление (on_delete).
# [DARK THEME] + ft.icons.* + hint_style (Flet 0.23.2)
import flet as ft
from typing import Callable, Optional, Dict
from core.zonal_models import Criminalist, CriminalistZone
from core.constants import COLORS, INITIAL_DEPARTMENTS


def create_add_criminalist_modal(
    page: ft.Page,
    criminalist: Optional[Criminalist] = None,
    on_save: Callable[[str, str, list], None] = None,  # full_name, note, department_ids
    existing_ids: set = None,
    on_delete: Callable = None,  # on_delete(criminalist) — только в режиме редактирования
) -> ft.AlertDialog:
    """
    Создать модальное окно добавления/редактирования криминалиста.
    В режиме редактирования (criminalist != None) возможно удаление (on_delete).
    """
    print("[ADD_CRIM_MODAL] Sozdayu dialog dobavleniya/redaktirovaniya kriminalista")
    is_edit = criminalist is not None

    # Поле ФИО
    name_field = ft.TextField(
        value=criminalist.full_name if is_edit else "",
        label="ФИО криминалиста *",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
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
        value=criminalist.note if is_edit else "",
        label="Примечание (например, 'Цифровая криминалистика')",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8,
        border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"],
        color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        expand=True,
    )

    # Выбор отделов
    dept_map = {d["id"]: d["name"] for d in INITIAL_DEPARTMENTS}
    selected_ids = set(existing_ids) if existing_ids else set()

    if is_edit and criminalist:
        selected_ids = set(criminalist.zone.department_ids)

    checkboxes = {}
    dept_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=300)

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

    # Кнопки
    def _close_dialog(e=None):
        dialog.open = False
        page.update()

    def _delete(e=None):
        if on_delete is None or not is_edit:
            return
        dialog.open = False
        page.update()
        on_delete(criminalist)

    def _save(e=None):
        full_name = name_field.value.strip()
        if not full_name:
            name_field.error_text = "Введите ФИО"
            name_field.update()
            return

        note = note_field.value.strip()

        if on_save:
            on_save(full_name, note, sorted(list(selected_ids)))

        dialog.open = False
        page.update()

    # Кнопка удаления (только при редактировании и наличии on_delete)
    delete_action = None
    if is_edit and on_delete is not None:
        delete_action = ft.ElevatedButton(
            "Удалить",
            icon=ft.icons.DELETE_FOREVER,
            bgcolor="#dc2626",
            color="white",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
            ),
            expand=True,
            on_click=_delete,
        )

    dialog_actions = []
    if delete_action is not None:
        dialog_actions.append(delete_action)
    dialog_actions.extend([
        ft.TextButton(
            "Отмена",
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
            "Сохранить",
            icon=ft.icons.SAVE,
            bgcolor=COLORS["btn_save"],
            color="white",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
            ),
            expand=True,
            on_click=_save,
        ),
    ])

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.icons.EDIT if is_edit else ft.icons.ADD, size=20, color="white"),
                    ft.Text(
                        f"{'Редактировать' if is_edit else 'Добавить'} криминалиста",
                        size=14,
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
            gradient=ft.LinearGradient(
                begin=ft.alignment.center_left,
                end=ft.alignment.center_right,
                colors=[COLORS["primary"], COLORS["primary_light"]],
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=ft.border_radius.only(top_left=12, top_right=12),
            margin=ft.margin.only(top=-12, left=-24, right=-24),
        ),
        bgcolor=COLORS["primary_light"],
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(height=8),
                    name_field,
                    ft.Container(height=8),
                    note_field,
                    ft.Container(height=12),
                    ft.Row(
                        controls=[
                            ft.Text(
                                "Закреплённые отделы:",
                                size=13,
                                weight=ft.FontWeight.W_600,
                                color=COLORS["text"],
                                expand=True,
                            ),
                            ft.TextButton(
                                "Все",
                                on_click=_select_all,
                                style=ft.ButtonStyle(color=COLORS["btn_save"]),
                            ),
                            ft.TextButton(
                                "Снять",
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
        actions=dialog_actions,
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        shape=ft.RoundedRectangleBorder(radius=12),
    )

    return dialog

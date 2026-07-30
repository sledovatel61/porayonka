# ui/add_department_modal.py
# Модальное окно добавления/редактирования следственного отдела.
import flet as ft
from typing import Callable, Optional
from core.models import Department
from core.constants import COLORS


def create_add_department_modal(
    page: ft.Page,
    department: Optional[Department] = None,
    on_save: Callable[[str, bool], None] = None,
    on_delete: Callable = None,
) -> ft.AlertDialog:
    """
    Создать модальное окно для добавления/редактирования отдела.
    on_save(name: str, is_ovd: bool)
    on_delete(department)
    """
    is_edit = department is not None

    name_field = ft.TextField(
        value=department.name if is_edit else "",
        label="Название отдела *",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8,
        border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"],
        color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        expand=True,
    )

    ovd_checkbox = ft.Checkbox(
        label="ОВД (без номера, курсив в таблице)",
        value=department.is_ovd if is_edit else False,
        active_color=COLORS["btn_save"],
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
    )

    def _close_dialog(e=None):
        dialog.open = False
        page.update()

    def _delete(e=None):
        if on_delete is None or not is_edit:
            return
        dialog.open = False
        page.update()
        on_delete(department)

    def _save(e=None):
        name = name_field.value.strip()
        if not name:
            name_field.error_text = "Введите название"
            name_field.update()
            return

        if on_save:
            on_save(name, bool(ovd_checkbox.value))

        dialog.open = False
        page.update()

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
                        f"{'Редактировать' if is_edit else 'Добавить'} отдел",
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
                    ovd_checkbox,
                ],
                spacing=8,
            ),
            width=420,
        ),
        actions=dialog_actions,
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        shape=ft.RoundedRectangleBorder(radius=12),
    )

    return dialog

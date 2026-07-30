# ui/edit_departments_modal.py
# Модальное окно управления списком следственных отделов.
import flet as ft
from typing import Callable, List
from core.models import Department
from core.constants import COLORS


def _safe_update(control):
    try:
        control.update()
    except Exception:
        pass


def create_edit_departments_modal(
    page: ft.Page,
    departments: List[Department],
    on_save: Callable = None,          # (departments)
) -> ft.AlertDialog:
    """
    Модальное окно редактирования списка отделов.
    on_save(departments) вызывается при любом изменении.
    """
    list_column = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)

    def _notify():
        print(f"[EDIT_DEPTS] notify: total={len(departments)}, active={sum(1 for d in departments if d.is_active)}")
        if on_save:
            on_save(departments)
        _rebuild_list()

    def _rebuild_list():
        list_column.controls.clear()
        active_count = sum(1 for d in departments if d.is_active)
        total_count = len(departments)

        # Заголовок-статистика
        list_column.controls.append(
            ft.Row(
                controls=[
                    ft.Text(
                        f"Активных: {active_count} / {total_count}",
                        size=12,
                        color=COLORS["text_secondary"],
                        weight=ft.FontWeight.W_600,
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
            )
        )
        list_column.controls.append(ft.Container(height=4))

        if not departments:
            list_column.controls.append(
                ft.Container(
                    content=ft.Text(
                        "Нет отделов. Нажмите «Добавить отдел».",
                        size=13,
                        color=COLORS["text_muted"],
                    ),
                    padding=ft.padding.all(16),
                    alignment=ft.alignment.center,
                )
            )
            _safe_update(list_column)
            return

        for index, dept in enumerate(departments):
            name_text = ft.Text(
                f"{index + 1}. {dept.name}",
                size=13,
                color=COLORS["text"] if dept.is_active else COLORS["text_muted"],
                italic=dept.is_ovd,
                expand=True,
                no_wrap=True,
                tooltip=dept.name,
            )

            def _toggle_active(e, d=dept):
                new_value = bool(e.control.value)
                print(f"[EDIT_DEPTS] toggle {d.name}: {d.is_active} -> {new_value}")
                d.is_active = new_value
                _notify()

            def _move_up(e, idx=index):
                if idx > 0:
                    departments[idx - 1], departments[idx] = departments[idx], departments[idx - 1]
                    print(f"[EDIT_DEPTS] move up: {departments[idx - 1].name}")
                    _notify()

            def _move_down(e, idx=index):
                if idx < len(departments) - 1:
                    departments[idx], departments[idx + 1] = departments[idx + 1], departments[idx]
                    print(f"[EDIT_DEPTS] move down: {departments[idx + 1].name}")
                    _notify()

            active_switch = ft.Switch(
                value=dept.is_active,
                active_color=COLORS["received"],
                inactive_track_color=COLORS["border"],
                scale=0.85,
                tooltip="Активен / неактивен",
                on_change=_toggle_active,
            )

            up_btn = ft.IconButton(
                icon=ft.icons.ARROW_UPWARD,
                icon_size=18,
                icon_color=COLORS["text_secondary"] if index == 0 else COLORS["btn_save"],
                tooltip="Переместить вверх",
                disabled=index == 0,
                on_click=_move_up,
                style=ft.ButtonStyle(padding=ft.padding.all(4)),
            )

            down_btn = ft.IconButton(
                icon=ft.icons.ARROW_DOWNWARD,
                icon_size=18,
                icon_color=COLORS["text_secondary"] if index == len(departments) - 1 else COLORS["btn_save"],
                tooltip="Переместить вниз",
                disabled=index == len(departments) - 1,
                on_click=_move_down,
                style=ft.ButtonStyle(padding=ft.padding.all(4)),
            )

            edit_btn = ft.IconButton(
                icon=ft.icons.EDIT_OUTLINED,
                icon_size=18,
                icon_color=COLORS["btn_save"],
                tooltip="Редактировать",
                on_click=lambda e, d=dept: _open_edit_dialog(d),
            )

            delete_btn = ft.IconButton(
                icon=ft.icons.DELETE_OUTLINE,
                icon_size=18,
                icon_color="#ef4444",
                tooltip="Удалить",
                on_click=lambda e, d=dept: _confirm_delete(d),
            )

            row = ft.Container(
                content=ft.Row(
                    controls=[
                        active_switch,
                        name_text,
                        up_btn,
                        down_btn,
                        edit_btn,
                        delete_btn,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
                bgcolor=COLORS["card"] if index % 2 == 0 else COLORS["primary_light"],
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=8, vertical=6),
                border=ft.border.all(1, COLORS["border"]),
            )
            list_column.controls.append(row)

        _safe_update(list_column)

    def _open_edit_dialog(dept: Department = None):
        is_edit = dept is not None
        name_field = ft.TextField(
            value=dept.name if is_edit else "",
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
            value=dept.is_ovd if is_edit else False,
            active_color=COLORS["btn_save"],
            label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        )

        def _close(e=None):
            edit_dialog.open = False
            page.update()

        def _save(e=None):
            name = name_field.value.strip()
            if not name:
                name_field.error_text = "Введите название"
                name_field.update()
                return

            if is_edit:
                dept.name = name
                dept.is_ovd = bool(ovd_checkbox.value)
                print(f"[EDIT_DEPTS] saved edit: {dept.id} {dept.name} ovd={dept.is_ovd}")
            else:
                max_id = max((d.id for d in departments), default=0)
                new_dept = Department(
                    id=max_id + 1,
                    name=name,
                    is_ovd=bool(ovd_checkbox.value),
                )
                departments.append(new_dept)
                print(f"[EDIT_DEPTS] added: {new_dept.id} {new_dept.name}")

            _close()
            _notify()

        edit_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Редактировать отдел" if is_edit else "Добавить отдел",
                size=16,
                weight=ft.FontWeight.BOLD,
                color=COLORS["text"],
            ),
            bgcolor=COLORS["primary_light"],
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        name_field,
                        ovd_checkbox,
                    ],
                    spacing=8,
                ),
                width=400,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=_close),
                ft.ElevatedButton(
                    "Сохранить",
                    icon=ft.icons.SAVE,
                    bgcolor=COLORS["btn_save"],
                    color="white",
                    on_click=_save,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        page.overlay.append(edit_dialog)
        edit_dialog.open = True
        page.update()

    def _confirm_delete(dept: Department):
        def _delete(e=None):
            print(f"[EDIT_DEPTS] delete: {dept.name}")
            if dept in departments:
                departments.remove(dept)
            confirm_dialog.open = False
            page.update()
            _notify()

        def _close(e=None):
            confirm_dialog.open = False
            page.update()

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Удаление отдела", size=16,
                          weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            content=ft.Text(
                f"Удалить отдел «{dept.name}»?\n\nЭто действие нельзя отменить.",
                size=13,
                color=COLORS["text"],
            ),
            bgcolor=COLORS["primary_light"],
            actions=[
                ft.TextButton("Отмена", on_click=_close),
                ft.ElevatedButton(
                    "Удалить",
                    bgcolor="#dc2626",
                    color="white",
                    on_click=_delete,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        page.update()

    def _close_main(e=None):
        dialog.open = False
        page.update()

    _rebuild_list()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.icons.EDIT_NOTE, size=20, color="white"),
                    ft.Text(
                        "Редактировать отделы",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color="white",
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.icons.CLOSE,
                        icon_color="white",
                        icon_size=18,
                        on_click=_close_main,
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
            content=list_column,
            width=520,
            height=420,
            padding=ft.padding.symmetric(vertical=8),
        ),
        actions=[
            ft.ElevatedButton(
                "Добавить отдел",
                icon=ft.icons.ADD,
                bgcolor=COLORS["btn_export"],
                color="white",
                on_click=lambda e: _open_edit_dialog(None),
            ),
            ft.TextButton("Закрыть", on_click=_close_main),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        shape=ft.RoundedRectangleBorder(radius=12),
    )

    return dialog

# ui/zonal/zone_manager.py
# Модальное окно редактирования зон криминалиста
# [DARK THEME] Обновлено визуально
import flet as ft
from typing import Callable, Dict
from core.zonal_models import Criminalist
from core.constants import COLORS, INITIAL_DEPARTMENTS


def create_zone_manager_dialog(
    page: ft.Page,
    criminalist: Criminalist,
    dept_map: Dict[int, str],
    on_save: Callable,
) -> ft.AlertDialog:
    """
    Создать модальное окно редактирования зон обслуживания.
    """
    print(f"[ZONE_MANAGER] Открываю редактор зон: {criminalist.full_name}")

    # Текущие выбранные отделы
    selected_ids: set = set(criminalist.zone.department_ids)

    # Список чекбоксов
    checkboxes: dict = {}
    dept_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO)

    def _build_list():
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

    def _save_and_close(e=None):
        # Применить изменения
        criminalist.zone.department_ids = sorted(list(selected_ids))
        print(f"[ZONE_MANAGER] Сохранено {len(selected_ids)} отделов для {criminalist.full_name}")
        dialog.open = False
        page.update()
        on_save()

    def _close(e=None):
        dialog.open = False
        page.update()

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

    _build_list()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text("✏️ ", size=20),
                    ft.Text(
                        f"Зоны: {criminalist.full_name}",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color="white",
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_color="white",
                        icon_size=18,
                        on_click=_close,
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
        # ТЁМНЫЙ ФОН КОНТЕНТА
        bgcolor=COLORS["primary_light"],
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(height=8),
                    ft.Row(
                        controls=[
                            ft.Text(
                                "Выберите закреплённые отделы:",
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
                        height=360,
                        border=ft.border.all(1, COLORS["border"]),
                        border_radius=8,
                        padding=ft.padding.all(8),
                        bgcolor=COLORS["card"],  # ТЁМНЫЙ ФОН СПИСКА
                    ),
                ],
                spacing=8,
            ),
            width=440,
        ),
        actions=[
            ft.TextButton(
                "Отмена",
                style=ft.ButtonStyle(
                    color=COLORS["text_secondary"],
                    bgcolor=COLORS["empty_bg"],
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=20, vertical=10),
                ),
                expand=True,
                on_click=_close,
            ),
            ft.ElevatedButton(
                "💾 Сохранить",
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

    print(f"[ZONE_MANAGER] Диалог создан")
    return dialog
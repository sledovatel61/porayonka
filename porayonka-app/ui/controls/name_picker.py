# ui/controls/name_picker.py
# Диалог выбора имён из списка (исполнители, ответственные пунктов).
import flet as ft
from typing import Callable, List
from core.constants import COLORS


def open_name_picker(
    page: ft.Page,
    title: str,
    available: List[str],
    selected: List[str],
    on_confirm: Callable[[List[str]], None],
    allow_custom: bool = True,
) -> None:
    """Открыть диалог мультивыбора имён.

    :param available: список доступных имён (из криминалистов + дефолтные)
    :param selected:  уже выбранные имена
    :param on_confirm: callback(new_selected_list)
    """
    current = list(selected)
    search = ft.TextField(
        label="Поиск",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8,
        border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"],
        color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        prefix_icon=ft.icons.SEARCH,
        height=40,
    )
    list_col = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=260)

    boxes = {}

    def _rebuild(query: str = ""):
        list_col.controls.clear()
        names = [n for n in available if query.lower() in n.lower()]
        # Сначала — уже выбранные (чтобы не потерять при фильтрации)
        names = sorted(set(names + current), key=lambda n: (n not in current, n))
        if not names:
            if allow_custom:
                list_col.controls.append(
                    ft.Text("Ничего не найдено. Введите имя вручную и нажмите «Добавить».",
                            size=11, color=COLORS["text_muted"])
                )
            else:
                list_col.controls.append(
                    ft.Text("Ничего не найдено", size=11, color=COLORS["text_muted"])
                )
        for n in names:
            cb = ft.Checkbox(
                label=n,
                value=(n in current),
                active_color=COLORS["btn_save"],
                label_style=ft.TextStyle(size=12, color=COLORS["text"]),
                on_change=lambda e, name=n: _toggle(name, e.control.value),
            )
            boxes[n] = cb
            list_col.controls.append(cb)
        try:
            list_col.update()
        except Exception:
            pass

    def _toggle(name: str, checked: bool):
        if checked and name not in current:
            current.append(name)
        elif not checked and name in current:
            current.remove(name)

    def _add_custom(e=None):
        val = search.value.strip()
        if not val:
            return
        if val not in current:
            current.append(val)
        if val not in available and allow_custom:
            available.append(val)
        search.value = ""
        _rebuild()
        try:
            search.update()
        except Exception:
            pass

    def _select_all(e=None):
        for n in list(available):
            if n not in current:
                current.append(n)
        _rebuild()

    def _clear(e=None):
        current.clear()
        _rebuild()

    def _close(e=None):
        dialog.open = False
        page.update()

    def _confirm(e=None):
        on_confirm(current)
        dialog.open = False
        page.update()

    def _on_search(e=None):
        _rebuild(search.value or "")

    search.on_change = _on_search
    _rebuild()

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=COLORS["primary_light"],
        title=ft.Row(
            controls=[
                ft.Icon(ft.icons.GROUPS_OUTLINED, size=20, color=COLORS["text"]),
                ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        content=ft.Container(
            width=460,
            content=ft.Column(
                controls=[
                    search,
                    ft.Row(
                        controls=[
                            ft.TextButton("Выбрать все", on_click=_select_all,
                                          style=ft.ButtonStyle(color=COLORS["btn_save"])),
                            ft.TextButton("Снять все", on_click=_clear,
                                          style=ft.ButtonStyle(color="#f87171")),
                            ft.Container(expand=True),
                            ft.Text(f"Выбрано: {len(current)}", size=11,
                                    color=COLORS["text_secondary"]),
                        ],
                        spacing=4,
                        tight=True,
                    ),
                    ft.Container(
                        content=list_col,
                        border=ft.border.all(1, COLORS["border"]),
                        border_radius=8,
                        padding=ft.padding.all(6),
                        bgcolor=COLORS["card"],
                    ),
                    ft.Row(
                        controls=[
                            ft.ElevatedButton("Добавить своё",
                                              icon=ft.icons.ADD,
                                              bgcolor=COLORS["btn_save"],
                                              color=COLORS["text_light"],
                                              height=34,
                                              on_click=_add_custom),
                            ft.Container(expand=True),
                        ],
                        spacing=4,
                        tight=True,
                    ),
                ],
                spacing=8,
                tight=True,
            ),
        ),
        actions=[
            ft.TextButton("Отмена", on_click=_close),
            ft.ElevatedButton("Готово", bgcolor=COLORS["btn_save"],
                              color=COLORS["text_light"], on_click=_confirm),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=12),
    )
    page.overlay.append(dialog)
    dialog.open = True
    page.update()

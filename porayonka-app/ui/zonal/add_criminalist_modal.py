# ui/zonal/add_criminalist_modal.py
# Модальное окно добавления/редактирования криминалиста.
# В режиме редактирования возможно удаление (on_delete).
#
# Фаза 40: добавлена секция «Взаимозаменяемость» — выбор НЕСКОЛЬКИХ других
# криминалистов (по стабильным ID; текущий человек в списке отсутствует).
# Сохранение одним действием пишет ФИО + примечание + зоны + связи.
# [DARK THEME] + ft.icons.* + hint_style (Flet 0.23.2)
import flet as ft
from typing import Callable, Optional, List

from core.zonal_models import Criminalist
from core.constants import COLORS, INITIAL_DEPARTMENTS


def create_add_criminalist_modal(
    page: ft.Page,
    criminalist: Optional[Criminalist] = None,
    on_save: Callable = None,  # on_save(full_name, note, department_ids, replacement_ids)
    existing_ids: set = None,
    on_delete: Callable = None,  # on_delete(criminalist) — только в режиме редактирования
    other_criminalists: Optional[List[Criminalist]] = None,
) -> ft.AlertDialog:
    """
    Создать модальное окно добавления/редактирования криминалиста.
    В режиме редактирования (criminalist != None) возможно удаление (on_delete).

    other_criminalists — полный актуальный справочник: из него строятся
    варианты «Взаимозаменяемость» (кроме самого criminalist). Если не задан,
    секция взаимозаменяемости скрывается (обратная совместимость вызова).
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

    # ── Выбор отделов (как было) ─────────────────────────────────
    dept_map = {d["id"]: d["name"] for d in INITIAL_DEPARTMENTS}
    selected_ids = set(existing_ids) if existing_ids else set()

    if is_edit and criminalist:
        selected_ids = set(criminalist.zone.department_ids)

    checkboxes = {}
    dept_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=240)

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

    # ── Выбор взаимозаменяемости (фаза 40) ───────────────────────
    # Варианты — остальные криминалисты справочника; хранятся стабильные
    # числовые ID (не ФИО). Текущий человек исключается.
    own_id = criminalist.id if is_edit and criminalist else None
    repl_others: List[Criminalist] = []
    if other_criminalists:
        repl_others = [c for c in other_criminalists if c.id != own_id]
    repl_others.sort(key=lambda c: (c.id, c.full_name))

    selected_repl: set = set()
    if is_edit and criminalist:
        known = {c.id for c in repl_others}
        selected_repl = {int(i) for i in (criminalist.replacement_ids or [])
                         if int(i) in known}

    repl_checkboxes = {}
    repl_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=150)

    def _build_repl_list():
        repl_list.controls.clear()
        for c in repl_others:
            cb = ft.Checkbox(
                label=f"({c.id}) {c.full_name}",
                value=(c.id in selected_repl),
                active_color=COLORS["btn_save"],
                label_style=ft.TextStyle(
                    size=12,
                    color=COLORS["text"],
                ),
                on_change=lambda e, rid=c.id: _on_repl_change(e, rid),
            )
            repl_checkboxes[c.id] = cb
            repl_list.controls.append(cb)

    def _on_repl_change(e, repl_id: int):
        if e.control.value:
            selected_repl.add(repl_id)
        else:
            selected_repl.discard(repl_id)

    def _select_all_repl(e=None):
        for rid, cb in repl_checkboxes.items():
            selected_repl.add(rid)
            cb.value = True
        try:
            repl_list.update()
        except Exception:
            pass

    def _deselect_all_repl(e=None):
        for rid, cb in repl_checkboxes.items():
            selected_repl.discard(rid)
            cb.value = False
        try:
            repl_list.update()
        except Exception:
            pass

    _build_dept_list()
    _build_repl_list()

    # ── Адаптивная высота: окна приложения бывают разные ─────────
    try:
        _win_h = page.window.height or 860
    except Exception:
        _win_h = 860
    _content_h = max(380, min(620, int(_win_h) - 170))
    # Фиксированные секции (поля, заголовки, зазоры) ≈ 250 pt → спискам
    # остаётся _content_h - 250, делим 60/40 между отделами и связями.
    _avail = _content_h - 250
    _dept_list_h = max(110, min(240, int(_avail * 0.60)))
    _repl_list_h = max(90, min(170, _avail - _dept_list_h))
    if _repl_list_h < 90:
        _repl_list_h = 90
    dept_list.height = _dept_list_h
    repl_list.height = _repl_list_h

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
            on_save(full_name, note, sorted(list(selected_ids)),
                    sorted(list(selected_repl)))

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

    # Содержимое: bounded Column (scroll на маленьких окнах — секции внутри
    # сами bounded/scrollable, вертикального expand нет).
    content_controls = [
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
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        ),
    ]

    if repl_others:
        content_controls.extend([
            ft.Container(height=10),
            ft.Row(
                controls=[
                    ft.Text(
                        "Взаимозаменяемость:",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=COLORS["text"],
                        expand=True,
                    ),
                    ft.Text(
                        "кто подменяет этого криминалиста",
                        size=10,
                        color=COLORS["text_muted"],
                    ),
                    ft.TextButton(
                        "Все",
                        on_click=_select_all_repl,
                        style=ft.ButtonStyle(color=COLORS["btn_save"]),
                    ),
                    ft.TextButton(
                        "Снять",
                        on_click=_deselect_all_repl,
                        style=ft.ButtonStyle(color="#f87171"),
                    ),
                ],
                spacing=4,
            ),
            ft.Container(
                content=repl_list,
                border=ft.border.all(1, COLORS["border"]),
                border_radius=8,
                padding=ft.padding.all(8),
                bgcolor=COLORS["card"],
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
            ),
        ])
    else:
        content_controls.append(
            ft.Text(
                "Нет других криминалистов для взаимозаменяемости",
                size=11,
                color=COLORS["text_muted"],
            )
        )

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
                controls=content_controls,
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
                height=_content_h,
            ),
            width=500,
        ),
        actions=dialog_actions,
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        shape=ft.RoundedRectangleBorder(radius=12),
    )

    return dialog

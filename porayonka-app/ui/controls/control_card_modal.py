# ui/controls/control_card_modal.py
# Модальное окно карточки контроля: добавление/редактирование + пункты задания,
# промежуточные точки, конечная дата, сканы-вложения.
import os
from datetime import date, datetime, timedelta
from typing import Callable, List, Optional
from uuid import uuid4

import flet as ft

from core.constants import COLORS
from core.controls_models import (
    Control, ControlTask, ControlMilestone, ONE_TIME, PERIODIC,
    parse_date, short_name,
)
from core.controls_data import (
    get_initiators,
    add_custom_initiator,
    copy_attachment_to_local, copy_attachment_to_shared,
    resolve_attachment, delete_attachment, ATTACHMENT_WARN_MB,
)
from .name_picker import open_name_picker

_PERIOD_LABELS = [
    ("daily", "Ежедневно", 1),
    ("weekly", "Еженедельно", 7),
    ("monthly", "Ежемесячно", 30),
    ("quarterly", "Ежеквартально", 91),
    ("yearly", "Ежегодно", 365),
    ("custom", "Свой интервал (дней)", 0),
]
_PERIOD_DAYS = {key: days for key, _label, days in _PERIOD_LABELS}
_ADD_INITIATOR = "__add__"


def _iso_from_datepicker(dt) -> Optional[str]:
    try:
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)
    except Exception:
        return None


def _display_date(iso: Optional[str]) -> str:
    d = parse_date(iso)
    return d.strftime("%d.%m.%Y") if d else "не указана"


def _period_key(days: int) -> str:
    for key, _label, d in _PERIOD_LABELS:
        if d == days and key != "custom":
            return key
    return "custom"


def _attachment_icon(filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return ft.icons.PICTURE_AS_PDF
    if name.endswith((".png", ".jpg", ".jpeg")):
        return ft.icons.IMAGE_OUTLINED
    return ft.icons.DESCRIPTION_OUTLINED


def create_control_card_modal(
    page: ft.Page,
    control: Optional[Control],
    available_names: List[str],
    on_save: Callable[[Control], None],
    on_delete: Optional[Callable[[Control], None]] = None,
    settings: Optional[dict] = None,
    initiators: Optional[List[str]] = None,
    on_cancel: Optional[Callable[[], None]] = None,
) -> ft.AlertDialog:
    """Модальное окно карточки контроля.

    :param control: существующий контроль (редактирование) или None (новый)
    :param on_save: callback(control) после сохранения
    :param on_delete: callback(control) для удаления (только при редактировании)
    :param settings: настройки (для сетевых вложений)
    :param initiators: список инициаторов (встроенные + кастомные)
    :param on_cancel: callback() при отмене/закрытии без сохранения
    """
    print("[CONTROL_MODAL] Sozdayu kartochku kontrolya")
    settings = settings or {}
    is_edit = control is not None
    if initiators is None:
        initiators = get_initiators(settings)
    full_names = list(available_names)

    # ── Адаптивная ширина карточки ──────────────────────────────
    try:
        win_w = page.window.width or 1280
    except Exception:
        win_w = 1280
    card_w = max(560, min(820, int(win_w * 0.62)))
    card_h = max(480, min(660, int((page.window.height or 860) * 0.78)))

    # ── Единый DatePicker (переиспользуется, чистится при закрытии) ──
    date_picker = ft.DatePicker(
        first_date=datetime(2020, 1, 1),
        last_date=datetime(2035, 12, 31),
        on_change=None,
    )
    page.overlay.append(date_picker)
    _date_target = {"setter": None}

    def _pick_date(setter):
        _date_target["setter"] = setter
        date_picker.pick_date()

    def _on_date_change(e):
        setter = _date_target["setter"]
        if setter is not None:
            setter(_iso_from_datepicker(getattr(e.control, "value", None)))
    date_picker.on_change = _on_date_change

    # ── Поля ────────────────────────────────────────────────────
    incoming_field = ft.TextField(
        value=control.incoming_number if is_edit else "",
        label="Входящий № (вх. № ВХСОП) *",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        expand=True,
    )
    receive_date_ref = {"value": control.receive_date if is_edit else date.today().isoformat()}
    receive_date_field = ft.TextField(
        value=_display_date(receive_date_ref["value"]),
        label="Дата поступления *",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        read_only=True, width=150,
    )

    def _set_receive_date(iso):
        receive_date_ref["value"] = iso
        receive_date_field.value = _display_date(iso)
        try:
            receive_date_field.update()
        except Exception:
            pass

    initiator_options = [ft.dropdown.Option(i) for i in initiators]
    initiator_dd = ft.Dropdown(
        label="Инициатор",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        value=control.initiator if (is_edit and control.initiator in initiators) else None,
        options=initiator_options,
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        width=210,
    )

    def _refresh_initiator_options(select: str = None):
        initiator_dd.options = [ft.dropdown.Option(i) for i in get_initiators(settings)]
        initiator_dd.value = select
        try:
            initiator_dd.update()
        except Exception:
            pass

    def _on_initiator_change(e):
        val = e.control.value
        if val == _ADD_INITIATOR:
            _open_add_initiator()

    def _open_add_initiator(e=None):
        name_field = ft.TextField(
            label="Название инициатора/контрагента",
            label_style=ft.TextStyle(color=COLORS["text_secondary"]),
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
            hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        )

        def _save_init(e=None):
            name = name_field.value.strip()
            if name:
                add_custom_initiator(settings, name)
                _refresh_initiator_options(select=name)
            page.close(init_dialog)
            page.overlay.remove(init_dialog) if init_dialog in page.overlay else None

        def _cancel_init(e=None):
            page.close(init_dialog)
            page.overlay.remove(init_dialog) if init_dialog in page.overlay else None

        init_dialog = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["primary_light"],
            title=ft.Text("Добавить инициатора", size=16, weight=ft.FontWeight.BOLD,
                          color=COLORS["text"]),
            content=ft.Container(content=name_field, width=360),
            actions=[
                ft.TextButton("Отмена", on_click=_cancel_init),
                ft.ElevatedButton("Добавить", bgcolor=COLORS["btn_save"],
                                  color=COLORS["text_light"], on_click=_save_init),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        page.open(init_dialog)

    initiator_dd.on_change = _on_initiator_change

    content_field = ft.TextField(
        value=control.content if is_edit else "",
        label="Содержание",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        multiline=True, min_lines=2, max_lines=4,
    )

    # ── Исполнители: выбор, без ручного ввода ───────────────────
    executors_ref = {"value": list(control.executors) if is_edit else []}
    executors_field = ft.TextField(
        value=", ".join(short_name(x) for x in executors_ref["value"]),
        label="Исполнитель(и) (нажмите для выбора)",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        read_only=True, expand=True,
    )

    def _pick_executors(e=None):
        open_name_picker(page, "Исполнители", full_names, executors_ref["value"],
                         lambda names: _set_executors(names))

    executors_field.on_focus = _pick_executors
    executors_btn = ft.IconButton(
        icon=ft.icons.GROUPS_OUTLINED, icon_color=COLORS["btn_save"],
        tooltip="Выбрать исполнителей из списка",
        on_click=_pick_executors,
    )

    def _set_executors(names):
        executors_ref["value"] = list(names)
        executors_field.value = ", ".join(short_name(x) for x in names)
        try:
            executors_field.update()
        except Exception:
            pass

    controller_options = [ft.dropdown.Option(n, short_name(n)) for n in full_names]
    controller_dd = ft.Dropdown(
        label="За кем контроль",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        value=control.controller if (is_edit and control.controller in full_names) else None,
        options=controller_options,
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        width=180,
    )

    # ── Тип / периодичность ────────────────────────────────────
    type_dd = ft.Dropdown(
        label="Тип",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        value=control.control_type if is_edit else ONE_TIME,
        options=[ft.dropdown.Option(ONE_TIME, "Разовый"),
                 ft.dropdown.Option(PERIODIC, "Постоянный")],
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        width=130,
    )
    period_dd = ft.Dropdown(
        label="Периодичность",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        value=_period_key(control.period_days if is_edit else 7),
        options=[ft.dropdown.Option(key, label) for key, label, _ in _PERIOD_LABELS],
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        width=170,
        visible=(control.control_type if is_edit else ONE_TIME) == PERIODIC,
    )
    custom_days_field = ft.TextField(
        value=str(control.period_days) if is_edit else "7",
        label="Интервал (дней)",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        keyboard_type=ft.KeyboardType.NUMBER,
        visible=False, width=130,
    )
    end_ref = {"value": control.end_date if is_edit else None}
    end_field = ft.TextField(
        value=_display_date(end_ref["value"]),
        label="Конечная дата",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        read_only=True, width=130,
        visible=(control.control_type if is_edit else ONE_TIME) == PERIODIC,
    )

    def _set_end_date(iso):
        end_ref["value"] = iso
        end_field.value = _display_date(iso)
        try:
            end_field.update()
        except Exception:
            pass

    def _on_type_change(e):
        is_per = (e.control.value == PERIODIC)
        period_dd.visible = is_per
        end_field.visible = is_per
        milestones_header.visible = is_per
        milestones_column.visible = is_per
        period_dd.update()
        end_field.update()
        milestones_header.update()
        milestones_column.update()

    type_dd.on_change = _on_type_change

    due_ref = {"value": control.due_date if is_edit else None}
    due_field = ft.TextField(
        value=_display_date(due_ref["value"]),
        label="Следующая дата исполнения",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        read_only=True, width=160,
    )

    def _set_due_date(iso):
        due_ref["value"] = iso
        due_field.value = _display_date(iso)
        try:
            due_field.update()
        except Exception:
            pass

    comment_field = ft.TextField(
        value=control.comment if is_edit else "",
        label="Комментарий",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        multiline=True, min_lines=1, max_lines=3,
    )

    # ── Пункты задания ──────────────────────────────────────────
    tasks_ui: List[dict] = []
    tasks_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=150)

    def _init_task_ui(task: Optional[ControlTask]):
        return {
            "title": ft.TextField(
                value=task.title if task else "", label="Пункт (например, п.1)",
                label_style=ft.TextStyle(color=COLORS["text_secondary"]),
                border_radius=8, border_color=COLORS["border"],
                focused_border_color=COLORS["btn_save"],
                bgcolor=COLORS["card"], color=COLORS["text"], height=38,
            ),
            "assignees": list(task.assignees) if task else [],
            "due_ref": {"value": task.due_date if task else None},
            "is_done": task.is_done if task else False,
            "done_ref": {"value": task.done_date if task else None},
        }

    def _remove_task(ui):
        if ui in tasks_ui:
            tasks_ui.remove(ui)
        _rebuild_tasks()

    def _edit_task_assignees(ui):
        open_name_picker(page, "Ответственные за пункт", full_names, ui["assignees"],
                         lambda names: _set_task_assignees(ui, names))

    def _set_task_assignees(ui, names):
        ui["assignees"] = list(names)
        _rebuild_tasks()

    def _pick_task_due(ui):
        _pick_date(lambda iso: _set_task_due(ui, iso))

    def _set_task_due(ui, iso):
        ui["due_ref"]["value"] = iso
        _rebuild_tasks()

    def _add_task():
        tasks_ui.append(_init_task_ui(None))
        _rebuild_tasks()

    def _on_task_done(ui, val):
        ui["is_done"] = bool(val)
        if val and not ui["done_ref"]["value"]:
            ui["done_ref"]["value"] = date.today().isoformat()
        _rebuild_tasks()

    def _build_task_card(ui) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(controls=[
                        ft.Icon(ft.icons.LIST_ALT, size=14, color=COLORS["text_muted"]),
                        ui["title"],
                        ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=16,
                                      icon_color="#f87171", tooltip="Удалить пункт",
                                      on_click=lambda e, u=ui: _remove_task(u)),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       alignment=ft.MainAxisAlignment.START, tight=True),
                    ft.Row(controls=[
                        ft.Text("Ответственные:", size=11, color=COLORS["text_secondary"]),
                        ft.Text(", ".join(short_name(x) for x in ui["assignees"]) or "не выбраны",
                                size=11, color=COLORS["text"], expand=True,
                                tooltip=", ".join(ui["assignees"]),
                                overflow=ft.TextOverflow.ELLIPSIS),
                        ft.IconButton(icon=ft.icons.GROUPS_OUTLINED, icon_size=15,
                                      icon_color=COLORS["btn_save"],
                                      tooltip="Выбрать ответственных",
                                      on_click=lambda e, u=ui: _edit_task_assignees(u)),
                        ft.Text("Срок:", size=11, color=COLORS["text_secondary"]),
                        ft.Text(_display_date(ui["due_ref"]["value"]), size=11,
                                color=COLORS["text"], width=86, no_wrap=True),
                        ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_size=15,
                                      icon_color=COLORS["btn_save"],
                                      on_click=lambda e, u=ui: _pick_task_due(u)),
                    ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       alignment=ft.MainAxisAlignment.START, tight=True),
                    ft.Row(controls=[
                        ft.Switch(value=ui["is_done"], active_color=COLORS["received"],
                                  height=26,
                                  on_change=lambda e, u=ui: _on_task_done(u, e.control.value)),
                        ft.Text("исполнено", size=11, color=COLORS["text_secondary"]),
                        ft.Text(_display_date(ui["done_ref"]["value"]), size=10,
                                color=COLORS["text_secondary"], width=80, no_wrap=True),
                        ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_size=15,
                                      icon_color=COLORS["btn_save"], tooltip="Дата исполнения",
                                      on_click=lambda e, u=ui: _pick_date(
                                          lambda iso: _set_task_done(u, iso))),
                    ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       alignment=ft.MainAxisAlignment.START, tight=True),
                ],
                spacing=2,
                tight=True,
            ),
            bgcolor=COLORS["card"],
            border=ft.border.all(1, COLORS["border"]),
            border_radius=8,
            padding=ft.padding.all(8),
        )

    def _set_task_done(ui, iso):
        ui["done_ref"]["value"] = iso
        _rebuild_tasks()

    def _rebuild_tasks():
        tasks_column.controls.clear()
        for ui in tasks_ui:
            tasks_column.controls.append(_build_task_card(ui))
        try:
            tasks_column.update()
        except Exception:
            pass

    # ── Промежуточные точки (milestones) ────────────────────────
    milestones_ui: List[dict] = []
    milestones_column = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, height=110)

    def _init_milestone_ui(m: Optional[ControlMilestone]):
        return {
            "date_ref": {"value": m.date if m else None},
            "note": m.note if m else "",
            "is_done": m.is_done if m else False,
        }

    def _add_milestone():
        milestones_ui.append(_init_milestone_ui(None))
        _rebuild_milestones()

    def _remove_milestone(ui):
        if ui in milestones_ui:
            milestones_ui.remove(ui)
        _rebuild_milestones()

    def _pick_milestone_date(ui):
        _pick_date(lambda iso: _set_milestone_date(ui, iso))

    def _set_milestone_date(ui, iso):
        ui["date_ref"]["value"] = iso
        _rebuild_milestones()

    def _build_milestone_row(ui) -> ft.Container:
        note_field = ft.TextField(
            value=ui["note"], label="Точка (описание)",
            label_style=ft.TextStyle(color=COLORS["text_secondary"]),
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
            height=34, expand=True,
            on_change=lambda e, u=ui: u.update({"note": e.control.value or ""}),
        )
        return ft.Container(
            content=ft.Row(controls=[
                ft.Text(_display_date(ui["date_ref"]["value"]), size=11,
                        color=COLORS["text"], width=90, no_wrap=True),
                ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_size=15,
                              icon_color=COLORS["btn_save"],
                              on_click=lambda e, u=ui: _pick_milestone_date(u)),
                note_field,
                ft.Switch(value=ui["is_done"], active_color=COLORS["received"], height=26,
                          on_change=lambda e, u=ui: u.update({"is_done": bool(e.control.value)})),
                ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=16,
                              icon_color="#f87171",
                              on_click=lambda e, u=ui: _remove_milestone(u)),
            ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER,
               alignment=ft.MainAxisAlignment.START, tight=True),
            bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]),
            border_radius=8, padding=ft.padding.all(6),
        )

    def _rebuild_milestones():
        milestones_column.controls.clear()
        for ui in milestones_ui:
            milestones_column.controls.append(_build_milestone_row(ui))
        try:
            milestones_column.update()
        except Exception:
            pass

    # Ближайшие даты цикла (подсказка для постоянных)
    def _period_days() -> int:
        key = period_dd.value or "weekly"
        if key == "custom":
            try:
                return max(1, int(custom_days_field.value or "7"))
            except ValueError:
                return 7
        return _PERIOD_DAYS.get(key, 7)

    def _cycle_dates_text() -> str:
        base = parse_date(due_ref["value"]) or date.today()
        days = _period_days()
        if days <= 0:
            days = 7
        dates = [base + timedelta(days=days * i) for i in range(1, 4)]
        return " · ".join(d.strftime("%d.%m.%Y") for d in dates)

    cycle_hint = ft.Text(
        _cycle_dates_text(), size=10, color=COLORS["text_muted"], italic=True,
    )

    def _refresh_cycle_hint():
        cycle_hint.value = _cycle_dates_text()
        try:
            cycle_hint.update()
        except Exception:
            pass

    def _on_period_change(e):
        custom_days_field.visible = (e.control.value == "custom")
        custom_days_field.update()
        _refresh_cycle_hint()

    period_dd.on_change = _on_period_change

    milestones_header = ft.Row(controls=[
        ft.Icon(ft.icons.TIMELINE, size=15, color=COLORS["text"]),
        ft.Text("Промежуточные точки", size=12, weight=ft.FontWeight.BOLD,
                color=COLORS["text"]),
        ft.Container(expand=True),
        ft.ElevatedButton("+ Добавить точку", bgcolor=COLORS["primary_light"],
                          color=COLORS["btn_save"], height=28,
                          on_click=lambda e: _add_milestone()),
    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER,
       alignment=ft.MainAxisAlignment.START, tight=True)

    if is_edit and control.milestones:
        for m in control.milestones:
            milestones_ui.append(_init_milestone_ui(m))
    _rebuild_milestones()

    # ── Сканы задания (вложения) ────────────────────────────────
    attach_ref = {"paths": list(control.attachments) if is_edit else []}
    attach_column = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=90)

    def _attachment_abs(rel: str) -> str:
        return os.path.join(str(rel))

    def _build_attach_row(rel: str) -> ft.Container:
        filename = rel.split("/")[-1] if "/" in rel else rel
        return ft.Container(
            content=ft.Row(controls=[
                ft.Icon(_attachment_icon(filename), size=15, color=COLORS["btn_save"]),
                ft.Text(filename, size=11, color=COLORS["text"], expand=True,
                        no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
                        tooltip=filename),
                ft.IconButton(icon=ft.icons.OPEN_IN_NEW, icon_size=15,
                              icon_color=COLORS["btn_save"], tooltip="Открыть",
                              on_click=lambda e, r=rel: _open_attachment(r)),
                ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=15,
                              icon_color="#f87171", tooltip="Удалить",
                              on_click=lambda e, r=rel: _remove_attachment(r)),
            ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER,
               alignment=ft.MainAxisAlignment.START, tight=True),
            bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]),
            border_radius=8, padding=ft.padding.all(6),
        )

    def _rebuild_attach():
        attach_column.controls.clear()
        for rel in attach_ref["paths"]:
            attach_column.controls.append(_build_attach_row(rel))
        try:
            attach_column.update()
        except Exception:
            pass

    def _open_attachment(rel: str):
        import subprocess, sys
        path = resolve_attachment(_control_id(), rel, settings)
        if not path or not os.path.exists(str(path)):
            from ui.toast import show_error_toast
            show_error_toast(page, "Файл вложения не найден")
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as ex:
            print(f"[CONTROL_MODAL] open attachment error: {ex}")

    def _remove_attachment(rel: str):
        def _confirm(e=None):
            delete_attachment(_control_id(), rel, settings)
            attach_ref["paths"].remove(rel)
            _rebuild_attach()
            page.close(confirm_dialog)
            page.overlay.remove(confirm_dialog) if confirm_dialog in page.overlay else None

        def _cancel(e=None):
            page.close(confirm_dialog)
            page.overlay.remove(confirm_dialog) if confirm_dialog in page.overlay else None

        confirm_dialog = ft.AlertDialog(
            modal=True, bgcolor=COLORS["primary_light"],
            title=ft.Text("Удаление вложения", size=15, weight=ft.FontWeight.BOLD,
                          color=COLORS["text"]),
            content=ft.Text("Удалить файл вложения?", size=13, color=COLORS["text"]),
            actions=[ft.TextButton("Отмена", on_click=_cancel),
                     ft.ElevatedButton("Удалить", bgcolor="#dc2626",
                                       color=COLORS["text_light"], on_click=_confirm)],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        page.open(confirm_dialog)

    def _control_id() -> str:
        return control.id if (is_edit and control and control.id) else f"tmp_{uuid4()}"

    def _on_attach_picked(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        cid = _control_id()
        added = []
        for f in e.files:
            size_mb = 0
            try:
                size_mb = os.path.getsize(f.path) / (1024 * 1024)
            except OSError:
                pass
            if size_mb > ATTACHMENT_WARN_MB:
                from ui.toast import show_toast
                show_toast(page, f"Файл > 20 МБ: {f.name}", icon=ft.icons.WARNING_AMBER)
            rel = None
            if settings.get("network_enabled"):
                rel = copy_attachment_to_shared(cid, f.path, settings)
            if rel is None:
                rel = copy_attachment_to_local(cid, f.path)
            if rel and rel not in attach_ref["paths"]:
                attach_ref["paths"].append(rel)
                added.append(rel)
        if added:
            _rebuild_attach()
            from ui.toast import show_toast
            show_toast(page, f"Прикреплено: {len(added)}", icon=ft.icons.ATTACH_FILE)

    attach_picker = ft.FilePicker(on_result=_on_attach_picked)
    if not hasattr(page, "_controls_attach_picker"):
        page.overlay.append(attach_picker)
        page._controls_attach_picker = attach_picker
    else:
        attach_picker = page._controls_attach_picker

    def _pick_attachments(e=None):
        attach_picker.pick_files(
            dialog_title="Выбрать сканы задания",
            allowed_extensions=["pdf", "png", "jpg", "jpeg"],
            allow_multiple=True,
        )

    if is_edit and control.attachments:
        attach_ref["paths"] = list(control.attachments)
    _rebuild_attach()

    # ── Действия ────────────────────────────────────────────────
    def _close(e=None):
        dialog.open = False
        _cleanup()
        page.update()
        if on_cancel is not None:
            try:
                on_cancel()
            except Exception:
                pass

    def _delete(e=None):
        if on_delete is None or not is_edit:
            return
        dialog.open = False
        _cleanup()
        page.update()
        on_delete(control)

    def _save(e=None):
        incoming = incoming_field.value.strip()
        if not incoming:
            incoming_field.error_text = "Введите входящий номер"
            incoming_field.update()
            return
        if not receive_date_ref["value"]:
            receive_date_field.error_text = "Укажите дату поступления"
            receive_date_field.update()
            return

        initiator = initiator_dd.value or ""
        c = control if is_edit else Control(id=str(uuid4()))
        c.incoming_number = incoming
        c.receive_date = receive_date_ref["value"]
        c.initiator = initiator
        c.content = content_field.value.strip()
        c.executors = list(executors_ref["value"])
        c.controller = controller_dd.value or ""
        c.control_type = type_dd.value or ONE_TIME
        c.period_days = _period_days() if c.control_type == PERIODIC else c.period_days
        c.end_date = end_ref["value"] if c.control_type == PERIODIC else None
        c.due_date = due_ref["value"]
        c.comment = comment_field.value.strip()
        c.updated_at = datetime.now().isoformat()

        # Пункты
        new_tasks = []
        for ui in tasks_ui:
            title = ui["title"].value.strip()
            if not title:
                continue
            new_tasks.append(ControlTask(
                id=str(uuid4()), title=title,
                assignees=list(ui["assignees"]),
                due_date=ui["due_ref"]["value"],
                is_done=ui["is_done"], done_date=ui["done_ref"]["value"],
            ))
        c.tasks = new_tasks

        # Промежуточные точки
        new_milestones = []
        for ui in milestones_ui:
            if not ui["date_ref"]["value"] and not ui["note"]:
                continue
            new_milestones.append(ControlMilestone(
                id=str(uuid4()),
                date=ui["date_ref"]["value"],
                note=ui["note"],
                is_done=ui["is_done"],
            ))
        c.milestones = new_milestones

        # Вложения
        c.attachments = list(attach_ref["paths"])

        # Если своя дата не указана — берём минимальную дату неисполненных
        # пунктов/точек (effective_due_date используется в UI автоматически)
        if not c.due_date:
            from core.controls_models import effective_due_date
            ed = effective_due_date(c)
            if ed:
                c.due_date = ed.isoformat()

        on_save(c)
        dialog.open = False
        _cleanup()
        page.update()

    def _cleanup():
        try:
            if date_picker in page.overlay:
                page.overlay.remove(date_picker)
        except Exception:
            pass

    actions = []
    if is_edit and on_delete is not None:
        actions.append(ft.ElevatedButton("Удалить", icon=ft.icons.DELETE_FOREVER,
                                         bgcolor="#dc2626", color="white",
                                         style=ft.ButtonStyle(
                                             shape=ft.RoundedRectangleBorder(radius=8),
                                             padding=ft.padding.symmetric(horizontal=16, vertical=8)),
                                         on_click=_delete))
    actions.extend([
        ft.TextButton("Отмена", on_click=_close,
                      style=ft.ButtonStyle(color=COLORS["text_secondary"])),
        ft.ElevatedButton("Сохранить", icon=ft.icons.SAVE, bgcolor=COLORS["btn_save"],
                          color=COLORS["text_light"], on_click=_save,
                          style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8),
                                               padding=ft.padding.symmetric(horizontal=20, vertical=8))),
    ])

    period_row = ft.Row(controls=[period_dd, custom_days_field], spacing=6, tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.START)
    periodic_row2 = ft.Row(controls=[
        due_field,
        ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_color=COLORS["btn_save"],
                      tooltip="Следующая дата",
                      on_click=lambda e: _pick_date(lambda iso: _set_due_date(iso))),
        end_field,
        ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_color=COLORS["btn_save"],
                      tooltip="Конечная дата",
                      on_click=lambda e: _pick_date(lambda iso: _set_end_date(iso))),
    ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
       alignment=ft.MainAxisAlignment.START)
    one_time_row2 = ft.Row(controls=[
        due_field,
        ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_color=COLORS["btn_save"],
                      tooltip="Следующая дата",
                      on_click=lambda e: _pick_date(lambda iso: _set_due_date(iso))),
    ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
       alignment=ft.MainAxisAlignment.START)

    is_periodic_init = (control.control_type if is_edit else ONE_TIME) == PERIODIC
    due_row = periodic_row2 if is_periodic_init else one_time_row2

    content_holder = ft.Container(
        width=card_w,
        height=card_h,
        content=ft.Column(
            controls=[
                ft.Row(controls=[incoming_field, receive_date_field,
                                 ft.IconButton(icon=ft.icons.CALENDAR_MONTH,
                                               icon_color=COLORS["btn_save"],
                                               on_click=lambda e: _pick_date(
                                                   lambda iso: _set_receive_date(iso)))],
                       spacing=6, tight=True,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       alignment=ft.MainAxisAlignment.START),
                ft.Row(controls=[initiator_dd], spacing=6, tight=True,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       alignment=ft.MainAxisAlignment.START),
                content_field,
                ft.Row(controls=[executors_field, executors_btn, controller_dd], spacing=6,
                       tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       alignment=ft.MainAxisAlignment.START),
                ft.Row(controls=[type_dd, period_row], spacing=6,
                       tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       alignment=ft.MainAxisAlignment.START),
                due_row,
                cycle_hint,
                comment_field,
                ft.Container(height=2),
                ft.Row(controls=[
                    ft.Icon(ft.icons.FORMAT_LIST_BULLETED, size=16, color=COLORS["text"]),
                    ft.Text("Пункты задания", size=13, weight=ft.FontWeight.BOLD,
                            color=COLORS["text"]),
                    ft.Container(expand=True),
                    ft.ElevatedButton("+ Добавить пункт", bgcolor=COLORS["primary_light"],
                                      color=COLORS["btn_save"], height=30,
                                      on_click=lambda e: _add_task()),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                   alignment=ft.MainAxisAlignment.START, tight=True),
                tasks_column,
                ft.Container(height=2),
                milestones_header,
                milestones_column,
                ft.Container(height=2),
                ft.Row(controls=[
                    ft.Icon(ft.icons.ATTACH_FILE, size=15, color=COLORS["text"]),
                    ft.Text("Скан задания", size=13, weight=ft.FontWeight.BOLD,
                            color=COLORS["text"]),
                    ft.Container(expand=True),
                    ft.ElevatedButton("Прикрепить файл", bgcolor=COLORS["primary_light"],
                                      color=COLORS["btn_save"], height=30,
                                      icon=ft.icons.ATTACH_FILE,
                                      on_click=_pick_attachments),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                   alignment=ft.MainAxisAlignment.START, tight=True),
                attach_column,
            ],
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
            tight=True,
        ),
        bgcolor=COLORS["primary_light"],
    )

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=COLORS["primary_light"],
        title=ft.Container(
            content=ft.Row(controls=[
                ft.Icon(ft.icons.EDIT_DOCUMENT if is_edit else ft.icons.ADD_CIRCLE_OUTLINE,
                        size=20, color="white"),
                ft.Text("Карточка контроля" if is_edit else "Добавить контроль",
                        size=15, weight=ft.FontWeight.BOLD, color="white", expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_color="white", icon_size=18,
                              on_click=_close),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            gradient=ft.LinearGradient(begin=ft.alignment.center_left,
                                       end=ft.alignment.center_right,
                                       colors=[COLORS["primary"], COLORS["primary_light"]]),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=ft.border_radius.only(top_left=12, top_right=12),
            margin=ft.margin.only(top=-12, left=-24, right=-24),
        ),
        content=content_holder,
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        shape=ft.RoundedRectangleBorder(radius=12),
    )

    return dialog

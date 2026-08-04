# ui/controls/control_card_modal.py
# Модальное окно карточки контроля: добавление / редактирование + пункты задания.
import flet as ft
from datetime import date, datetime, timedelta
from typing import Callable, List, Optional

from core.constants import COLORS
from core.controls_models import (
    Control, ControlTask, ONE_TIME, PERIODIC, parse_date, format_date,
)
from core.controls_data import get_criminalist_names, get_initiators
from .name_picker import open_name_picker

_PERIOD_LABELS = [
    ("daily", "Ежедневно", 1),
    ("weekly", "Еженедельно", 7),
    ("monthly", "Ежемесячно", 30),
    ("quarterly", "Ежеквартально", 91),
    ("custom", "Свой интервал (дней)", 0),
]


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


def create_control_card_modal(
    page: ft.Page,
    control: Optional[Control],
    available_names: List[str],
    on_save: Callable[[Control], None],
    on_delete: Optional[Callable[[Control], None]] = None,
) -> ft.AlertDialog:
    """Модальное окно карточки контроля.

    :param control: существующий контроль (редактирование) или None (новый)
    :param on_save: callback(control) после сохранения
    :param on_delete: callback(control) для удаления (только в режиме редактирования)
    """
    print("[CONTROL_MODAL] Sozdayu kartochku kontrolya")
    is_edit = control is not None
    initiators = get_initiators()
    controllers = [c for c in available_names]

    # ── Общий DatePicker для полей дат ─────────────────────────
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
    )
    receive_date_ref = {"value": control.receive_date if is_edit else date.today().isoformat()}
    receive_date_field = ft.TextField(
        value=_display_date(receive_date_ref["value"]),
        label="Дата поступления *",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        read_only=True,
    )
    receive_date_btn = ft.IconButton(
        icon=ft.icons.CALENDAR_MONTH, icon_color=COLORS["btn_save"],
        tooltip="Выбрать дату поступления",
        on_click=lambda e: _pick_date(lambda iso: _set_receive_date(iso)),
    )

    def _set_receive_date(iso):
        receive_date_ref["value"] = iso
        receive_date_field.value = _display_date(iso)
        try:
            receive_date_field.update()
        except Exception:
            pass

    initiator_dd = ft.Dropdown(
        label="Инициатор",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        value=control.initiator if (is_edit and control.initiator in initiators) else None,
        options=[ft.dropdown.Option(i) for i in initiators],
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
    )
    custom_initiator = ft.TextField(
        value=control.initiator if (is_edit and control.initiator not in initiators) else "",
        label="Свой инициатор",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        visible=bool(is_edit and control.initiator not in initiators),
    )

    def _on_initiator_change(e):
        custom_initiator.visible = (e.control.value is None)
        try:
            custom_initiator.update()
        except Exception:
            pass
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

    executors_ref = {"value": list(control.executors) if is_edit else []}
    executors_field = ft.TextField(
        value=", ".join(executors_ref["value"]),
        label="Исполнитель(и)",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        read_only=True,
    )
    executors_btn = ft.IconButton(
        icon=ft.icons.GROUPS_OUTLINED, icon_color=COLORS["btn_save"],
        tooltip="Выбрать исполнителей из списка",
        on_click=lambda e: _pick_executors(),
    )

    def _pick_executors():
        open_name_picker(
            page, "Исполнители", available_names, executors_ref["value"],
            lambda names: _set_executors(names),
        )

    def _set_executors(names):
        executors_ref["value"] = list(names)
        executors_field.value = ", ".join(names)
        try:
            executors_field.update()
        except Exception:
            pass

    controller_dd = ft.Dropdown(
        label="За кем контроль",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        value=control.controller if (is_edit and control.controller in controllers) else None,
        options=[ft.dropdown.Option(c) for c in controllers],
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
    )

    type_dd = ft.Dropdown(
        label="Тип",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        value=control.control_type if is_edit else ONE_TIME,
        options=[
            ft.dropdown.Option(ONE_TIME, "Разовый"),
            ft.dropdown.Option(PERIODIC, "Постоянный"),
        ],
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
    )
    period_dd = ft.Dropdown(
        label="Периодичность",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        value="weekly",
        options=[ft.dropdown.Option(key, label) for key, label, _ in _PERIOD_LABELS],
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
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
        visible=False, width=120,
    )

    def _on_type_change(e):
        is_per = (e.control.value == PERIODIC)
        period_dd.visible = is_per
        period_dd.update()
        custom_days_field.visible = is_per and (period_dd.value == "custom")
        custom_days_field.update()
    type_dd.on_change = _on_type_change

    def _on_period_change(e):
        custom_days_field.visible = (e.control.value == "custom")
        custom_days_field.update()
    period_dd.on_change = _on_period_change

    due_ref = {"value": control.due_date if is_edit else None}
    due_field = ft.TextField(
        value=_display_date(due_ref["value"]),
        label="Следующая дата исполнения",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        read_only=True,
    )
    due_btn = ft.IconButton(
        icon=ft.icons.CALENDAR_MONTH, icon_color=COLORS["btn_save"],
        tooltip="Выбрать дату исполнения",
        on_click=lambda e: _pick_date(lambda iso: _set_due_date(iso)),
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
    tasks_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=170)

    def _init_task_ui(task: Optional[ControlTask]):
        ui = {
            "title": ft.TextField(
                value=task.title if task else "", label="Пункт (например, п.1)",
                label_style=ft.TextStyle(color=COLORS["text_secondary"]),
                border_radius=8, border_color=COLORS["border"],
                focused_border_color=COLORS["btn_save"],
                bgcolor=COLORS["card"], color=COLORS["text"], height=40,
            ),
            "assignees": list(task.assignees) if task else [],
            "due_ref": {"value": task.due_date if task else None},
            "is_done": task.is_done if task else False,
            "done_ref": {"value": task.done_date if task else None},
            "comment": task.comment if task else "",
        }
        return ui

    def _task_due_text(ui) -> str:
        return _display_date(ui["due_ref"]["value"])

    def _remove_task(ui):
        if ui in tasks_ui:
            tasks_ui.remove(ui)
        _rebuild_tasks()

    def _edit_task_assignees(ui):
        open_name_picker(page, "Ответственные за пункт", available_names,
                         ui["assignees"], lambda names: _set_task_assignees(ui, names))

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

    def _build_task_card(ui) -> ft.Container:
        def _set_task_done(ui2, iso):
            ui2["done_ref"]["value"] = iso
            _rebuild_tasks()

        # Контейнер с полями пункта
        inner = ft.Container(
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
                        ft.Text(", ".join(ui["assignees"]) or "не выбраны", size=11,
                                color=COLORS["text"], width=200, no_wrap=True,
                                tooltip=", ".join(ui["assignees"])),
                        ft.IconButton(icon=ft.icons.GROUPS_OUTLINED, icon_size=15,
                                      icon_color=COLORS["btn_save"],
                                      tooltip="Выбрать ответственных",
                                      on_click=lambda e, u=ui: _edit_task_assignees(u)),
                        ft.Text("Срок:", size=11, color=COLORS["text_secondary"]),
                        ft.Text(_task_due_text(ui), size=11, color=COLORS["text"],
                                width=86, no_wrap=True),
                        ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_size=15,
                                      icon_color=COLORS["btn_save"],
                                      on_click=lambda e, u=ui: _pick_task_due(u)),
                    ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       alignment=ft.MainAxisAlignment.START, tight=True),
                    ft.Row(controls=[
                        ft.Switch(
                            value=ui["is_done"], active_color=COLORS["received"],
                            height=28,
                            on_change=lambda e, u=ui: _on_task_done(u, e.control.value),
                        ),
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
        return inner

    def _on_task_done(ui, val):
        ui["is_done"] = bool(val)
        if val and not ui["done_ref"]["value"]:
            ui["done_ref"]["value"] = date.today().isoformat()
        _rebuild_tasks()

    def _rebuild_tasks():
        tasks_column.controls.clear()
        for ui in tasks_ui:
            tasks_column.controls.append(_build_task_card(ui))
        try:
            tasks_column.update()
        except Exception:
            pass

    if is_edit and control.tasks:
        for t in control.tasks:
            tasks_ui.append(_init_task_ui(t))
    _rebuild_tasks()

    # ── Действия ────────────────────────────────────────────────
    def _close(e=None):
        dialog.open = False
        page.update()

    def _delete(e=None):
        if on_delete is None or not is_edit:
            return
        dialog.open = False
        page.update()
        on_delete(control)

    def _period_days() -> int:
        key = period_dd.value or "weekly"
        mapping = {
            "daily": 1,
            "weekly": 7,
            "monthly": 30,
            "quarterly": 91,
            "custom": None,
        }
        days = mapping.get(key, 7)
        if days is not None:
            return days
        try:
            return max(1, int(custom_days_field.value or "7"))
        except ValueError:
            return 7

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

        initiator = initiator_dd.value or custom_initiator.value.strip() or ""

        # Сохраняем все данные из полей в объект
        c = control if is_edit else Control(id=str(uuid4()))
        c.incoming_number = incoming
        c.receive_date = receive_date_ref["value"]
        c.initiator = initiator
        c.content = content_field.value.strip()
        c.executors = list(executors_ref["value"])
        c.controller = controller_dd.value or ""
        c.control_type = type_dd.value or ONE_TIME
        c.period_days = _period_days() if c.control_type == PERIODIC else c.period_days
        c.due_date = due_ref["value"]
        c.comment = comment_field.value.strip()
        c.updated_at = datetime.now().isoformat()

        # Собираем пункты
        new_tasks = []
        for ui in tasks_ui:
            title = ui["title"].value.strip()
            if not title:
                continue
            new_tasks.append(ControlTask(
                id=str(uuid4()),
                title=title,
                assignees=list(ui["assignees"]),
                due_date=ui["due_ref"]["value"],
                is_done=ui["is_done"],
                done_date=ui["done_ref"]["value"],
                comment="",
            ))
        c.tasks = new_tasks

        # Если своя дата не указана — берём минимальную дату неисполненных пунктов
        if not c.due_date:
            dates = [parse_date(t.due_date) for t in c.tasks if not t.is_done]
            dates = [d for d in dates if d is not None]
            if dates:
                c.due_date = min(dates).isoformat()

        on_save(c)
        dialog.open = False
        page.update()

    from uuid import uuid4

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

    content_holder = ft.Container(
        width=760,
        height=520,
        content=ft.Column(
            controls=[
                ft.Row(controls=[incoming_field, receive_date_field, receive_date_btn],
                       spacing=6, tight=True,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       alignment=ft.MainAxisAlignment.START),
                ft.Row(controls=[initiator_dd, custom_initiator], spacing=6, tight=True,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       alignment=ft.MainAxisAlignment.START),
                content_field,
                ft.Row(controls=[executors_field, executors_btn, controller_dd], spacing=6,
                       tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       alignment=ft.MainAxisAlignment.START),
                ft.Row(controls=[type_dd, period_row, due_field, due_btn], spacing=6,
                       tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       alignment=ft.MainAxisAlignment.START),
                comment_field,
                ft.Container(height=2),
                ft.Row(controls=[
                    ft.Icon(ft.icons.FORMAT_LIST_BULLETED, size=16, color=COLORS["text"]),
                    ft.Text("Пункты задания", size=13, weight=ft.FontWeight.BOLD,
                            color=COLORS["text"]),
                    ft.Container(expand=True),
                    ft.ElevatedButton("+ Добавить пункт", bgcolor=COLORS["primary_light"],
                                      color=COLORS["btn_save"], height=32,
                                      on_click=lambda e: _add_task()),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                   alignment=ft.MainAxisAlignment.START, tight=True),
                tasks_column,
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

    # Чистим оверлей от picker при закрытии (небольшая утечка допустима, но
    # лучше убрать повторные пикеры)
    def _cleanup_on_dismiss(e=None):
        try:
            if date_picker in page.overlay:
                page.overlay.remove(date_picker)
        except Exception:
            pass
    date_picker.on_dismiss = _cleanup_on_dismiss

    return dialog

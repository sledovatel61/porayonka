# ui/controls/control_card_modal.py
# Glass Dark версия для совместимости (основной overlay в controls_tab.py)
import os
from datetime import date, datetime, timedelta
from typing import Callable, List, Optional
from uuid import uuid4

import flet as ft

from .glass_theme import GLASS
from .russian_calendar import create_russian_date_field
from core.controls_models import (
    Control, ControlTask, ControlMilestone, ONE_TIME, PERIODIC,
    parse_date, short_name,
)
from core.controls_data import (
    get_initiators, add_custom_initiator,
    copy_attachment_to_local, copy_attachment_to_shared,
    resolve_attachment, delete_attachment,
)

_PERIOD_LABELS = [
    ("daily", "Ежедневно", 1),
    ("weekly", "Еженедельно", 7),
    ("monthly", "Ежемесячно", 30),
    ("quarterly", "Ежеквартально", 91),
    ("yearly", "Ежегодно", 365),
    ("custom", "Свой интервал", 0),
]
_PERIOD_DAYS = {k: d for k, _, d in _PERIOD_LABELS}

def _display(iso: Optional[str]) -> str:
    d = parse_date(iso)
    return d.strftime("%d.%m.%Y") if d else "не указана"

def _period_key(days: int) -> str:
    for k, _, d in _PERIOD_LABELS:
        if d == days and k != "custom":
            return k
    return "custom"

def _ensure_picker(page: ft.Page, attr: str, on_result):
    if not hasattr(page, attr):
        p = ft.FilePicker(on_result=on_result)
        page.overlay.append(p)
        setattr(page, attr, p)
        try:
            page.update()
        except Exception:
            pass
    else:
        try:
            getattr(page, attr).on_result = on_result
        except Exception:
            pass
    return getattr(page, attr)

def _glass_tf(hint, value="", width=None, expand=False, multiline=False, min_lines=1, max_lines=4):
    return ft.TextField(
        value=value,
        hint_text=hint,
        width=width,
        expand=expand,
        multiline=multiline,
        min_lines=min_lines if multiline else None,
        max_lines=max_lines if multiline else 1,
        border_radius=10,
        border_color=GLASS["border"],
        focused_border_color=GLASS["accent"],
        bgcolor=GLASS["surface_alt"],
        color=GLASS["text"],
        hint_style=ft.TextStyle(color=GLASS["text_muted"], size=13),
        text_style=ft.TextStyle(size=13, color=GLASS["text"]),
        dense=True,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
    )

def _glass_dd(hint, value, options, width=None):
    return ft.Dropdown(
        hint_text=hint,
        value=value,
        options=options,
        width=width,
        border_radius=10,
        border_color=GLASS["border"],
        focused_border_color=GLASS["accent"],
        bgcolor=GLASS["surface_alt"],
        color=GLASS["text"],
        hint_style=ft.TextStyle(color=GLASS["text_muted"], size=12),
        text_style=ft.TextStyle(size=12, color=GLASS["text"]),
        dense=True,
    )

def _build_inline_multi(available: List[str], initial: List[str], title: str):
    selected = list(initial)
    expanded = {"value": False}
    search_val = {"value": ""}

    badge = ft.Text(f"Выбрано: {len(selected)}", size=11, color=GLASS["text_secondary"])
    summary = ft.Text(", ".join(short_name(x) for x in selected) or "не выбрано", size=12, color=GLASS["text"], max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, tooltip=", ".join(selected))

    search_field = ft.TextField(
        hint_text=f"Поиск {title.lower()}…",
        prefix_icon=ft.icons.SEARCH,
        height=36, dense=True,
        border_radius=10, border_color=GLASS["border"],
        focused_border_color=GLASS["accent"],
        bgcolor=GLASS["surface_alt"], color=GLASS["text"],
        hint_style=ft.TextStyle(color=GLASS["text_muted"], size=12),
        visible=False,
    )
    list_col = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=140, visible=False)
    wrapper = ft.Container(content=list_col, border=ft.border.all(1, GLASS["border"]), border_radius=10, padding=ft.padding.all(6), bgcolor=GLASS["surface_alt"], visible=False)

    def _rebuild():
        q = search_val["value"].lower()
        filtered = [n for n in available if q in n.lower()] if q else list(available)
        filtered = sorted(set(filtered + selected), key=lambda n: (n not in selected, n.lower()))
        list_col.controls.clear()
        for name in filtered:
            def _mk(n):
                def _chg(e):
                    if e.control.value:
                        if n not in selected:
                            selected.append(n)
                    else:
                        if n in selected:
                            selected.remove(n)
                    badge.value = f"Выбрано: {len(selected)}"
                    summary.value = ", ".join(short_name(x) for x in selected) or "не выбрано"
                    try:
                        badge.update()
                        summary.update()
                    except Exception:
                        pass
                return _chg
            list_col.controls.append(ft.Checkbox(label=short_name(name), value=name in selected, active_color=GLASS["accent"], label_style=ft.TextStyle(size=12, color=GLASS["text"]), tooltip=name, on_change=_mk(name), height=28))
        try:
            list_col.update()
        except Exception:
            pass

    def _on_search(e):
        search_val["value"] = e.control.value or ""
        _rebuild()

    search_field.on_change = _on_search

    def _toggle(e=None):
        expanded["value"] = not expanded["value"]
        search_field.visible = expanded["value"]
        list_col.visible = expanded["value"]
        wrapper.visible = expanded["value"]
        summary.visible = not expanded["value"]
        expand_btn.icon = ft.icons.EXPAND_LESS if expanded["value"] else ft.icons.EXPAND_MORE
        try:
            search_field.update()
            wrapper.update()
            summary.update()
            expand_btn.update()
        except Exception:
            pass
        if expanded["value"]:
            _rebuild()

    def _clear(e=None):
        selected.clear()
        badge.value = "Выбрано: 0"
        summary.value = "не выбрано"
        try:
            badge.update()
            summary.update()
        except Exception:
            pass
        _rebuild()

    expand_btn = ft.IconButton(icon=ft.icons.EXPAND_MORE, icon_size=18, icon_color=GLASS["text_secondary"], on_click=_toggle)
    header = ft.Row(controls=[ft.Text(title, size=12, weight=ft.FontWeight.BOLD, color=GLASS["text"]), ft.Container(width=6), badge, ft.Container(expand=True), ft.TextButton("Очистить", on_click=_clear, style=ft.ButtonStyle(color=GLASS["overdue"])), expand_btn], spacing=4, tight=True)
    _rebuild()
    cont = ft.Container(content=ft.Column(controls=[header, summary, search_field, wrapper], spacing=6, tight=True), bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=10, padding=ft.padding.all(10))
    cont._get_selected = lambda: list(selected)
    return cont

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
    print("[CONTROL_MODAL] create card modal Glass Dark")
    settings = settings or {}
    is_edit = control is not None
    if initiators is None:
        initiators = get_initiators(settings)

    # state for dates
    receive_ref = {"value": control.receive_date if is_edit else date.today().isoformat()}
    due_ref = {"value": control.due_date if is_edit else None}
    end_ref = {"value": control.end_date if is_edit else None}

    def _set_receive(iso):
        receive_ref["value"] = iso
    def _set_due(iso):
        due_ref["value"] = iso
    def _set_end(iso):
        end_ref["value"] = iso

    receive_cal = create_russian_date_field(page, receive_ref["value"], _set_receive, hint="Дата поступления", width=170)
    due_cal = create_russian_date_field(page, due_ref["value"], _set_due, hint="Следующая дата", width=180)
    end_cal = create_russian_date_field(page, end_ref["value"], _set_end, hint="Конечная дата", width=170)
    end_cal.visible = (control.control_type if is_edit else ONE_TIME) == PERIODIC

    incoming_field = _glass_tf("Входящий № ВХСОП *", value=control.incoming_number if is_edit else "", expand=True)
    init_dd = _glass_dd("Инициатор", value=control.initiator if (is_edit and control.initiator in initiators) else None, options=[ft.dropdown.Option(i) for i in initiators], width=220)
    new_init_field = _glass_tf("Новый инициатор", width=180)
    def _add_init(e=None):
        name = (new_init_field.value or "").strip()
        if not name:
            return
        add_custom_initiator(settings, name)
        new_list = get_initiators(settings)
        initiators.clear()
        initiators.extend(new_list)
        init_dd.options = [ft.dropdown.Option(i) for i in initiators]
        init_dd.value = name
        new_init_field.value = ""
        try:
            init_dd.update()
            new_init_field.update()
        except Exception:
            pass
    add_init_btn = ft.Container(content=ft.Text("Добавить", size=12, color=GLASS["text"]), height=36, padding=ft.padding.symmetric(horizontal=12), bgcolor=GLASS["surface"], border=ft.border.all(1, GLASS["border"]), border_radius=10, ink=True, on_click=_add_init, alignment=ft.alignment.center)

    content_field = _glass_tf("Содержание", value=control.content if is_edit else "", multiline=True, min_lines=3, max_lines=5)
    exec_picker = _build_inline_multi(available_names, list(control.executors) if is_edit else [], "Исполнители")
    controller_dd = _glass_dd("За кем контроль", value=control.controller if (is_edit and control.controller in available_names) else None, options=[ft.dropdown.Option(n, short_name(n)) for n in available_names], width=200)
    type_dd = _glass_dd("Тип", value=control.control_type if is_edit else ONE_TIME, options=[ft.dropdown.Option(ONE_TIME, "Разовый"), ft.dropdown.Option(PERIODIC, "Постоянный")], width=140)
    period_dd = _glass_dd("Периодичность", value=_period_key(control.period_days if is_edit else 7), options=[ft.dropdown.Option(k, l) for k, l, _ in _PERIOD_LABELS], width=180)
    period_dd.visible = (control.control_type if is_edit else ONE_TIME) == PERIODIC
    custom_days_field = _glass_tf("Интервал дней", value=str(control.period_days) if is_edit else "7", width=120)
    custom_days_field.visible = _period_key(control.period_days if is_edit else 7) == "custom"
    comment_field = _glass_tf("Комментарий", value=control.comment if is_edit else "", multiline=True, min_lines=1, max_lines=3)

    def _on_type_change(e):
        is_per = (e.control.value == PERIODIC)
        period_dd.visible = is_per
        end_cal.visible = is_per
        try:
            period_dd.update()
            end_cal.update()
        except Exception:
            pass
    def _on_period_change(e):
        custom_days_field.visible = (e.control.value == "custom")
        try:
            custom_days_field.update()
        except Exception:
            pass
    type_dd.on_change = _on_type_change
    period_dd.on_change = _on_period_change

    # Tasks (simplified)
    tasks_state: List[dict] = []
    tasks_col = ft.Column(spacing=6)
    def _rebuild_tasks():
        tasks_col.controls.clear()
        for ui in tasks_state:
            tasks_col.controls.append(_build_task_card(ui))
        try:
            tasks_col.update()
        except Exception:
            pass
    def _build_task_card(ui: dict):
        title_f = ui["title_field"]
        def _set_t_due(iso):
            ui["due_ref"]["value"] = iso
        due_c = create_russian_date_field(page, ui["due_ref"]["value"], _set_t_due, hint="Срок", width=150)
        return ft.Container(
            content=ft.Column(controls=[
                ft.Row(controls=[ft.Icon(ft.icons.LIST_ALT, size=14, color=GLASS["text_muted"]), title_f, ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=16, icon_color=GLASS["overdue"], on_click=lambda e, u=ui: _remove_task(u))], spacing=6, tight=True),
                ft.Row(controls=[ft.Text("Срок:", size=11, color=GLASS["text_secondary"]), due_c], spacing=6, tight=True),
            ], spacing=6, tight=True),
            bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=10, padding=ft.padding.all(8),
        )
    def _remove_task(ui):
        if ui in tasks_state:
            tasks_state.remove(ui)
        _rebuild_tasks()
    def _add_task(e=None):
        tasks_state.append({"title_field": _glass_tf("Пункт", expand=True), "due_ref": {"value": None}})
        _rebuild_tasks()
    if is_edit and control.tasks:
        for t in control.tasks:
            tasks_state.append({"title_field": _glass_tf("Пункт", value=t.title, expand=True), "due_ref": {"value": t.due_date}})
    _rebuild_tasks()

    # Attachments
    attach_ref = {"paths": list(control.attachments) if is_edit else []}
    attach_col = ft.Column(spacing=4)
    def _rebuild_attach():
        attach_col.controls.clear()
        for rel in attach_ref["paths"]:
            fn = rel.split("/")[-1]
            attach_col.controls.append(ft.Container(content=ft.Row(controls=[ft.Icon(ft.icons.ATTACH_FILE, size=14, color=GLASS["accent"]), ft.Text(fn, size=11, expand=True, color=GLASS["text"], tooltip=fn), ft.IconButton(icon=ft.icons.OPEN_IN_NEW, icon_size=14, icon_color=GLASS["accent"], on_click=lambda e, r=rel: _open_att(r)), ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=14, icon_color=GLASS["overdue"], on_click=lambda e, r=rel: _remove_att(r))], spacing=4, tight=True), bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=10, padding=ft.padding.all(6)))
        try:
            attach_col.update()
        except Exception:
            pass
    def _open_att(rel):
        import subprocess, sys
        p = resolve_attachment(control.id if is_edit else f"tmp_{uuid4()}", rel, settings)
        if not p or not os.path.exists(str(p)):
            from ui.toast import show_error_toast
            show_error_toast(page, "Файл не найден")
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(p))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(p)])
            else:
                subprocess.Popen(["xdg-open", str(p)])
        except Exception:
            pass
    def _remove_att(rel):
        def _confirm(e=None):
            try:
                delete_attachment(control.id if is_edit else f"tmp_{uuid4()}", rel, settings)
            except Exception:
                pass
            if rel in attach_ref["paths"]:
                attach_ref["paths"].remove(rel)
            _rebuild_attach()
            try:
                page.close(dlg)
            except Exception:
                pass
        def _cancel(e=None):
            try:
                page.close(dlg)
            except Exception:
                pass
        dlg = ft.AlertDialog(modal=True, bgcolor=GLASS["surface_solid"], title=ft.Text("Удаление вложения", size=14, weight=ft.FontWeight.BOLD, color=GLASS["text"]), content=ft.Text("Удалить файл?", size=12, color=GLASS["text"]), actions=[ft.TextButton("Отмена", on_click=_cancel), ft.ElevatedButton("Удалить", bgcolor=GLASS["overdue"], color="white", on_click=_confirm)], shape=ft.RoundedRectangleBorder(radius=14))
        page.open(dlg)
    def _on_attach_picked(e):
        files = getattr(e, "files", None)
        if not files:
            return
        for fobj in files:
            fpath = getattr(fobj, "path", None)
            if not fpath:
                continue
            cid = control.id if is_edit else f"tmp_{uuid4()}"
            rel = None
            if settings.get("network_enabled"):
                rel = copy_attachment_to_shared(cid, fpath, settings)
            if rel is None:
                rel = copy_attachment_to_local(cid, fpath)
            if rel and rel not in attach_ref["paths"]:
                attach_ref["paths"].append(rel)
        _rebuild_attach()
    _ensure_picker(page, "_controls_attach_picker", _on_attach_picked)
    def _pick_attach(e=None):
        try:
            page._controls_attach_picker.pick_files(dialog_title="Выбрать сканы", allowed_extensions=["pdf","png","jpg","jpeg"], allow_multiple=True)
        except Exception:
            pass
    _rebuild_attach()

    dialog_ref = {"dlg": None}
    def _close(e=None):
        dlg = dialog_ref["dlg"]
        if dlg:
            try:
                page.close(dlg)
            except Exception:
                pass
        if on_cancel:
            try:
                on_cancel()
            except Exception:
                pass
    def _save(e=None):
        inc = (incoming_field.value or "").strip()
        if not inc:
            try:
                incoming_field.error_text = "Введите номер"
                incoming_field.update()
            except Exception:
                pass
            return
        execs = exec_picker._get_selected() if hasattr(exec_picker, "_get_selected") else []
        new_tasks = []
        for ui in tasks_state:
            title = (ui["title_field"].value or "").strip()
            if not title:
                continue
            new_tasks.append(ControlTask(id=str(uuid4()), title=title, due_date=ui["due_ref"]["value"]))
        def _period_days_val():
            k = period_dd.value or "weekly"
            if k == "custom":
                try:
                    return max(1, int(custom_days_field.value or "7"))
                except ValueError:
                    return 7
            return _PERIOD_DAYS.get(k, 7)
        c = control if is_edit else Control(id=str(uuid4()))
        c.incoming_number = inc
        c.receive_date = receive_ref["value"]
        c.initiator = init_dd.value or ""
        c.content = content_field.value.strip()
        c.executors = execs
        c.controller = controller_dd.value or ""
        c.control_type = type_dd.value or ONE_TIME
        c.period_days = _period_days_val() if c.control_type == PERIODIC else c.period_days
        c.end_date = end_ref["value"] if c.control_type == PERIODIC else None
        c.due_date = due_ref["value"]
        c.comment = comment_field.value.strip()
        c.tasks = new_tasks
        c.attachments = list(attach_ref["paths"])
        c.updated_at = datetime.now().isoformat()
        try:
            page.close(dialog_ref["dlg"])
        except Exception:
            pass
        on_save(c)

    def _delete(e=None):
        if on_delete and is_edit:
            try:
                page.close(dialog_ref["dlg"])
            except Exception:
                pass
            on_delete(control)

    content_holder = ft.Container(
        width=820,
        content=ft.Column(controls=[
            ft.Row(controls=[incoming_field, receive_cal], spacing=8, tight=True),
            ft.Row(controls=[init_dd, new_init_field, add_init_btn], spacing=6, tight=True),
            content_field,
            exec_picker,
            ft.Row(controls=[controller_dd, type_dd, period_dd, custom_days_field], spacing=6, tight=True),
            ft.Row(controls=[due_cal, end_cal], spacing=8, tight=True),
            comment_field,
            ft.Row(controls=[ft.Icon(ft.icons.FORMAT_LIST_BULLETED, size=16, color=GLASS["text"]), ft.Text("Пункты задания", size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"]), ft.Container(expand=True), ft.Container(content=ft.Text("+ Добавить пункт", size=12, color=GLASS["accent"]), height=30, padding=ft.padding.symmetric(horizontal=10), bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=8, ink=True, on_click=_add_task, alignment=ft.alignment.center)], spacing=6, tight=True),
            tasks_col,
            ft.Row(controls=[ft.Icon(ft.icons.ATTACH_FILE, size=15, color=GLASS["text"]), ft.Text("Скан задания", size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"]), ft.Container(expand=True), ft.Container(content=ft.Text("Прикрепить файл", size=12, color=GLASS["text"]), height=30, padding=ft.padding.symmetric(horizontal=10), bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=8, ink=True, on_click=_pick_attach, alignment=ft.alignment.center)], spacing=6, tight=True),
            attach_col,
        ], spacing=10, scroll=ft.ScrollMode.AUTO, tight=True),
        bgcolor=GLASS["surface"],
    )

    actions = []
    if is_edit and on_delete:
        actions.append(ft.Container(content=ft.Text("Удалить", color="white", size=13, weight=ft.FontWeight.BOLD), height=40, padding=ft.padding.symmetric(horizontal=16), bgcolor=GLASS["overdue"], border_radius=10, ink=True, on_click=_delete, alignment=ft.alignment.center))
    actions.extend([
        ft.Container(content=ft.Text("Отмена", size=13, color=GLASS["text_secondary"]), height=40, padding=ft.padding.symmetric(horizontal=16), bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=10, ink=True, on_click=_close, alignment=ft.alignment.center),
        ft.Container(content=ft.Row(controls=[ft.Icon(ft.icons.SAVE, size=16, color="white"), ft.Text("Сохранить", size=13, weight=ft.FontWeight.BOLD, color="white")], spacing=6, tight=True, alignment=ft.MainAxisAlignment.CENTER), height=40, padding=ft.padding.symmetric(horizontal=18), bgcolor=GLASS["accent"], border_radius=10, ink=True, on_click=_save, alignment=ft.alignment.center),
    ])

    dlg = ft.AlertDialog(
        modal=True,
        bgcolor=GLASS["surface_solid"],
        title=ft.Row(controls=[ft.Icon(ft.icons.EDIT_DOCUMENT if is_edit else ft.icons.ADD_CIRCLE_OUTLINE, size=20, color=GLASS["text"]), ft.Text("Карточка контроля" if is_edit else "Добавить контроль", size=15, weight=ft.FontWeight.BOLD, color=GLASS["text"], expand=True), ft.IconButton(icon=ft.icons.CLOSE, icon_color=GLASS["text_secondary"], icon_size=18, on_click=_close)], spacing=8, tight=True),
        content=content_holder,
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        shape=ft.RoundedRectangleBorder(radius=14),
    )
    dialog_ref["dlg"] = dlg
    return dlg

# ui/controls/control_card_modal.py
# Карточка контроля (резервный путь; основной таб использует свой overlay).
# Рефактор: inline-выбор исполнителей/ответственных без вложенных диалогов
# (Fix Bug B), Fix Bug F (спам логов и overlay), Fix Bug A (FilePicker mount).
# Скин «Glass Dark»: палитра — glass_theme.py, даты — russian_calendar.py.
# Контракт сохранён: create_control_card_modal(...) -> ft.AlertDialog.
import os
from datetime import date, datetime
from typing import Callable, List, Optional
from uuid import uuid4

import flet as ft

from core.controls_models import (
    Control, ControlTask, ControlMilestone, ONE_TIME, PERIODIC,
    parse_date, short_name,
)
from core.controls_data import (
    get_initiators, add_custom_initiator,
    copy_attachment_to_local, copy_attachment_to_shared,
    resolve_attachment, delete_attachment, ATTACHMENT_WARN_MB,
)
from .glass_theme import GLASS, glass_button, ghost_button
from .russian_calendar import create_russian_date_field

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
    return d.strftime("%d.%m.%Y") if d else ""


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


def _glass_field(**kw):
    opts = dict(
        border_radius=10,
        border_color=GLASS["border"],
        focused_border_color=GLASS["accent"],
        bgcolor=GLASS["field"],
        color=GLASS["text"],
        hint_style=ft.TextStyle(color=GLASS["text_3"], size=13),
        text_style=ft.TextStyle(size=13, color=GLASS["text"]),
    )
    opts.update(kw)
    return ft.TextField(**opts)


def _glass_dd(**kw):
    opts = dict(
        border_radius=10,
        border_color=GLASS["border"],
        focused_border_color=GLASS["accent"],
        bgcolor=GLASS["field"],
        color=GLASS["text"],
        hint_style=ft.TextStyle(color=GLASS["text_3"], size=13),
        text_style=ft.TextStyle(size=13, color=GLASS["text"]),
    )
    opts.update(kw)
    return ft.Dropdown(**opts)


def _build_inline_multi(page: ft.Page, available: List[str], initial: List[str], title: str):
    selected = list(initial)
    expanded = {"value": False}
    search_val = {"value": ""}

    badge = ft.Text(f"Выбрано: {len(selected)}", size=11, color=GLASS["text_2"])
    summary = ft.Text(", ".join(short_name(x) for x in selected) or "не выбрано",
                      size=11, color=GLASS["text_2"], max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
                      tooltip=", ".join(selected))

    search_field = ft.TextField(
        hint_text=f"Поиск {title.lower()}…",
        prefix_icon=ft.icons.SEARCH,
        height=34, dense=True,
        border_radius=8, border_color=GLASS["border"],
        focused_border_color=GLASS["accent"],
        bgcolor=GLASS["field"], color=GLASS["text"],
        hint_style=ft.TextStyle(color=GLASS["text_3"], size=11),
        visible=False,
    )
    list_col = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=140, visible=False)
    wrapper = ft.Container(content=list_col, border=ft.border.all(1, GLASS["border"]),
                           border_radius=8, padding=ft.padding.all(4),
                           bgcolor=GLASS["field_alt"], visible=False)

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
                    summary.tooltip = ", ".join(selected)
                    try:
                        badge.update()
                        summary.update()
                    except Exception:
                        pass
                return _chg
            list_col.controls.append(
                ft.Checkbox(label=short_name(name), value=name in selected,
                            active_color=GLASS["accent"], label_style=ft.TextStyle(size=11, color=GLASS["text"]),
                            tooltip=name, on_change=_mk(name), height=26)
            )
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
        summary.tooltip = None
        try:
            badge.update()
            summary.update()
        except Exception:
            pass
        _rebuild()

    expand_btn = ft.IconButton(icon=ft.icons.EXPAND_MORE, icon_size=18, icon_color=GLASS["text_2"], on_click=_toggle)
    header = ft.Row(controls=[
        ft.Text(title, size=12, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
        ft.Container(width=6), badge, ft.Container(expand=True),
        ft.TextButton(
            content=ft.Text("Очистить", size=11, color=GLASS["danger"], no_wrap=True),
            on_click=_clear, style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=6))),
        expand_btn,
    ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    _rebuild()
    cont = ft.Container(
        content=ft.Column(controls=[header, summary, search_field, wrapper], spacing=4, tight=True),
        bgcolor=GLASS["surface"], border=ft.border.all(1, GLASS["border"]), border_radius=10,
        padding=ft.padding.all(8),
    )
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
    print("[CONTROL_MODAL] create card modal (glass dark)")
    settings = settings or {}
    is_edit = control is not None
    if initiators is None:
        initiators = get_initiators(settings)

    try:
        win_w = page.window.width or 1280
    except Exception:
        win_w = 1280
    card_w = max(560, min(820, int(win_w * 0.62)))
    card_h = max(480, min(680, int((page.window.height or 860) * 0.78)))

    # fields
    incoming_field = _glass_field(
        value=control.incoming_number if is_edit else "",
        hint_text="Входящий № ВХСОП *",
        dense=True, expand=True, height=40,
    )
    receive_ref = {"value": control.receive_date if is_edit else date.today().isoformat()}

    def _set_receive(iso):
        receive_ref["value"] = iso
    receive_composite = create_russian_date_field(
        page, receive_ref["value"], _set_receive, hint="Дата поступления *", width=150, height=40)

    init_dd = _glass_dd(
        hint_text="Инициатор",
        value=control.initiator if (is_edit and control.initiator in initiators) else None,
        options=[ft.dropdown.Option(i) for i in initiators],
        width=220, height=40, dense=True,
    )
    new_init_field = _glass_field(hint_text="Новый инициатор", width=180, height=40, dense=True)

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
    add_init_btn = glass_button("Добавить", height=36, bgcolor=GLASS["field"],
                                color=GLASS["accent"], radius=10, on_click=_add_init)

    content_field = _glass_field(
        value=control.content if is_edit else "",
        hint_text="Содержание",
        multiline=True, min_lines=2, max_lines=4,
    )

    exec_picker = _build_inline_multi(page, available_names, list(control.executors) if is_edit else [], "Исполнители")

    controller_dd = _glass_dd(
        hint_text="За кем контроль",
        value=control.controller if (is_edit and control.controller in available_names) else None,
        options=[ft.dropdown.Option(n, short_name(n)) for n in available_names],
        width=180, height=40, dense=True,
    )

    type_dd = _glass_dd(
        hint_text="Тип",
        value=control.control_type if is_edit else ONE_TIME,
        options=[ft.dropdown.Option(ONE_TIME, "Разовый"), ft.dropdown.Option(PERIODIC, "Постоянный")],
        width=130, height=40, dense=True,
    )
    period_dd = _glass_dd(
        hint_text="Периодичность",
        value=_period_key(control.period_days if is_edit else 7),
        options=[ft.dropdown.Option(k, l) for k, l, _ in _PERIOD_LABELS],
        width=170, height=40, dense=True,
        visible=(control.control_type if is_edit else ONE_TIME) == PERIODIC,
    )
    custom_days_field = _glass_field(
        value=str(control.period_days) if is_edit else "7",
        hint_text="Интервал дней",
        width=110, height=40, dense=True,
        visible=_period_key(control.period_days if is_edit else 7) == "custom",
    )
    due_ref = {"value": control.due_date if is_edit else None}

    def _set_due(iso):
        due_ref["value"] = iso
    due_composite = create_russian_date_field(
        page, due_ref["value"], _set_due, hint="Следующая дата исполнения", width=170, height=40)

    end_ref = {"value": control.end_date if is_edit else None}

    def _set_end(iso):
        end_ref["value"] = iso
    end_composite = create_russian_date_field(
        page, end_ref["value"], _set_end, hint="Конечная дата", width=142, height=40)
    end_composite.visible = (control.control_type if is_edit else ONE_TIME) == PERIODIC

    def _on_type_change(e):
        is_per = (e.control.value == PERIODIC)
        period_dd.visible = is_per
        end_composite.visible = is_per
        milestones_header.visible = is_per
        milestones_col.visible = is_per
        try:
            period_dd.update()
            end_composite.update()
            milestones_header.update()
            milestones_col.update()
        except Exception:
            pass
    type_dd.on_change = _on_type_change

    def _on_period_change(e):
        custom_days_field.visible = (e.control.value == "custom")
        try:
            custom_days_field.update()
        except Exception:
            pass
    period_dd.on_change = _on_period_change

    comment_field = _glass_field(
        value=control.comment if is_edit else "",
        hint_text="Комментарий",
        multiline=True, min_lines=1, max_lines=3,
    )

    # Tasks (simple inline, assignees via inline picker per task)
    tasks_col = ft.Column(spacing=6)
    tasks_state: List[dict] = []

    def _rebuild_tasks():
        tasks_col.controls.clear()
        for ui in tasks_state:
            tasks_col.controls.append(_build_task_card(ui))
        try:
            tasks_col.update()
        except Exception:
            pass

    def _build_task_card(ui: dict) -> ft.Container:
        title_f = ui["title_field"]
        # assignees inline mini
        ass_picker = ui.get("ass_picker")
        if ass_picker is None:
            ass_picker = _build_inline_multi(page, available_names, ui["assignees"], f"Отв. {title_f.value[:10] or 'пункт'}")
            ui["ass_picker"] = ass_picker

        def _set_t_due(iso, u=ui):
            u["due_ref"]["value"] = iso
        due_composite = create_russian_date_field(
            page, ui["due_ref"]["value"], _set_t_due, hint="Срок", width=118, height=34)

        return ft.Container(
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Icon(ft.icons.LIST_ALT, size=14, color=GLASS["text_3"]),
                    title_f,
                    ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=16, icon_color=GLASS["danger"],
                                  on_click=lambda e, u=ui: _remove_task(u)),
                ], spacing=6, tight=True),
                ass_picker,
                due_composite,
            ], spacing=4, tight=True),
            bgcolor=GLASS["surface"], border=ft.border.all(1, GLASS["border_alt"]), border_radius=10, padding=ft.padding.all(8),
        )

    def _remove_task(ui):
        if ui in tasks_state:
            tasks_state.remove(ui)
        _rebuild_tasks()

    def _add_task(e=None):
        new_ui = {
            "title_field": _glass_field(hint_text="Пункт (напр. п.1)", height=36, dense=True, expand=True),
            "assignees": [],
            "due_ref": {"value": None},
            "ass_picker": None,
        }
        tasks_state.append(new_ui)
        _rebuild_tasks()

    if is_edit and control.tasks:
        for t in control.tasks:
            tasks_state.append({
                "title_field": _glass_field(value=t.title, hint_text="Пункт", height=36, dense=True, expand=True),
                "assignees": list(t.assignees),
                "due_ref": {"value": t.due_date},
                "ass_picker": None,
            })
    _rebuild_tasks()

    # Milestones
    milestones_col = ft.Column(spacing=4, visible=(control.control_type if is_edit else ONE_TIME) == PERIODIC)
    miles_state: List[dict] = []

    def _rebuild_miles():
        milestones_col.controls.clear()
        for ui in miles_state:
            def _mk_set(u):
                def _s(iso):
                    u["date_ref"]["value"] = iso
                return _s
            date_composite = create_russian_date_field(
                page, ui["date_ref"]["value"], _mk_set(ui), hint="Дата", width=118, height=34)
            note_f = _glass_field(value=ui["note"], hint_text="Точка", height=34, dense=True, expand=True,
                                  on_change=lambda e, u=ui: u.update({"note": e.control.value or ""}))
            milestones_col.controls.append(
                ft.Container(
                    content=ft.Row(controls=[
                        date_composite,
                        note_f,
                        ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=16, icon_color=GLASS["danger"],
                                      on_click=lambda e, u=ui: _remove_mile(u)),
                    ], spacing=4, tight=True),
                    bgcolor=GLASS["surface"], border=ft.border.all(1, GLASS["border_alt"]), border_radius=10,
                    padding=ft.padding.all(6),
                )
            )
        try:
            milestones_col.update()
        except Exception:
            pass

    def _remove_mile(ui):
        if ui in miles_state:
            miles_state.remove(ui)
        _rebuild_miles()

    def _add_mile(e=None):
        miles_state.append({"date_ref": {"value": None}, "note": ""})
        _rebuild_miles()

    if is_edit and control.milestones:
        for m in control.milestones:
            miles_state.append({"date_ref": {"value": m.date}, "note": m.note})
    _rebuild_miles()

    # Attachments
    attach_ref = {"paths": list(control.attachments) if is_edit else []}
    attach_col = ft.Column(spacing=4)

    def _rebuild_attach():
        attach_col.controls.clear()
        for rel in attach_ref["paths"]:
            fn = rel.split("/")[-1]
            attach_col.controls.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Icon(ft.icons.ATTACH_FILE, size=14, color=GLASS["accent"]),
                        ft.Text(fn, size=11, expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, tooltip=fn, color=GLASS["text"]),
                        ft.IconButton(icon=ft.icons.OPEN_IN_NEW, icon_size=14, icon_color=GLASS["accent"],
                                      on_click=lambda e, r=rel: _open_att(r)),
                        ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=14, icon_color=GLASS["danger"],
                                      on_click=lambda e, r=rel: _remove_att(r)),
                    ], spacing=4, tight=True),
                    bgcolor=GLASS["surface"], border=ft.border.all(1, GLASS["border_alt"]), border_radius=10,
                    padding=ft.padding.all(6),
                )
            )
        try:
            attach_col.update()
        except Exception:
            pass

    def _open_att(rel):
        import subprocess, sys
        p = resolve_attachment(control.id if is_edit else f"tmp_{uuid4()}", rel, settings)
        if not p or not os.path.exists(str(p)):
            from ui.toast import show_error_toast
            show_error_toast(page, "Файл вложения не найден")
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

        dlg = ft.AlertDialog(
            modal=True, bgcolor=GLASS["surface_solid"],
            title=ft.Text("Удаление вложения", size=14, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
            content=ft.Text("Удалить файл?", size=12, color=GLASS["text"]),
            actions=[ft.TextButton("Отмена", on_click=_cancel, style=ft.ButtonStyle(color=GLASS["text_2"])),
                     ft.ElevatedButton("Удалить", bgcolor=GLASS["danger"], color="white", on_click=_confirm)],
            shape=ft.RoundedRectangleBorder(radius=14),
        )
        page.open(dlg)

    def _on_attach_picked(e):
        files = getattr(e, "files", None)
        if not files:
            return
        for fobj in files:
            fpath = getattr(fobj, "path", None)
            if not fpath:
                continue
            try:
                sz = os.path.getsize(fpath) / (1024 * 1024)
                if sz > ATTACHMENT_WARN_MB:
                    from ui.toast import show_toast
                    show_toast(page, f"Файл > 20 МБ: {getattr(fobj, 'name', '')}", icon=ft.icons.WARNING_AMBER)
            except Exception:
                pass
            rel = None
            cid = control.id if is_edit else f"tmp_{uuid4()}"
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
            page._controls_attach_picker.pick_files(
                dialog_title="Выбрать сканы",
                allowed_extensions=["pdf", "png", "jpg", "jpeg"],
                allow_multiple=True,
            )
        except Exception:
            pass

    _rebuild_attach()

    # Save / close
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
        if not receive_ref["value"]:
            return
        execs = exec_picker._get_selected() if hasattr(exec_picker, "_get_selected") else []
        # tasks
        new_tasks = []
        for ui in tasks_state:
            title = (ui["title_field"].value or "").strip()
            if not title:
                continue
            ass = ui["ass_picker"]._get_selected() if ui.get("ass_picker") and hasattr(ui["ass_picker"], "_get_selected") else ui["assignees"]
            new_tasks.append(ControlTask(id=str(uuid4()), title=title, assignees=list(ass), due_date=ui["due_ref"]["value"]))
        new_miles = []
        for ui in miles_state:
            if not ui["date_ref"]["value"] and not ui["note"]:
                continue
            new_miles.append(ControlMilestone(id=str(uuid4()), date=ui["date_ref"]["value"], note=ui["note"]))

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
        c.milestones = new_miles
        c.attachments = list(attach_ref["paths"])
        c.updated_at = datetime.now().isoformat()

        if not c.due_date:
            from core.controls_models import effective_due_date
            eff = effective_due_date(c)
            if eff:
                c.due_date = eff.isoformat()

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

    milestones_header = ft.Row(controls=[
        ft.Icon(ft.icons.TIMELINE, size=15, color=GLASS["text"]),
        ft.Text("Промежуточные точки", size=12, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
        ft.Container(expand=True),
        glass_button("+ Добавить точку", height=28, bgcolor=GLASS["field"], color=GLASS["accent"],
                     radius=10, on_click=_add_mile),
    ], spacing=6, tight=True, visible=(control.control_type if is_edit else ONE_TIME) == PERIODIC)

    tasks_header = ft.Row(controls=[
        ft.Icon(ft.icons.FORMAT_LIST_BULLETED, size=16, color=GLASS["text"]),
        ft.Text("Пункты задания", size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
        ft.Container(expand=True),
        glass_button("+ Добавить пункт", height=30, bgcolor=GLASS["field"], color=GLASS["accent"],
                     radius=10, on_click=_add_task),
    ], spacing=6, tight=True)

    attach_header = ft.Row(controls=[
        ft.Icon(ft.icons.ATTACH_FILE, size=15, color=GLASS["text"]),
        ft.Text("Скан задания", size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
        ft.Container(expand=True),
        glass_button("Прикрепить файл", icon=ft.icons.ATTACH_FILE, height=30, bgcolor=GLASS["field"],
                     color=GLASS["accent"], radius=10, on_click=_pick_attach),
    ], spacing=6, tight=True)

    content_holder = ft.Container(
        width=card_w, height=card_h,
        content=ft.Column(controls=[
            ft.Row(controls=[incoming_field, receive_composite], spacing=6, tight=True),
            ft.Row(controls=[init_dd, new_init_field, add_init_btn], spacing=6, tight=True),
            content_field,
            exec_picker,
            ft.Row(controls=[controller_dd, type_dd, period_dd, custom_days_field], spacing=6, tight=True),
            ft.Row(controls=[due_composite, end_composite], spacing=6, tight=True),
            comment_field,
            ft.Container(height=2),
            tasks_header,
            tasks_col,
            ft.Container(height=2),
            milestones_header,
            milestones_col,
            ft.Container(height=2),
            attach_header,
            attach_col,
        ], spacing=8, scroll=ft.ScrollMode.AUTO, tight=True),
        bgcolor=GLASS["surface_solid"],
    )

    actions = []
    if is_edit and on_delete:
        actions.append(ft.ElevatedButton("Удалить", icon=ft.icons.DELETE_FOREVER, bgcolor=GLASS["danger"], color="white", on_click=_delete))
    actions.extend([
        ghost_button("Отмена", _close, color=GLASS["text_2"], size=13),
        ft.ElevatedButton("Сохранить", icon=ft.icons.SAVE, bgcolor=GLASS["accent"], color="white", on_click=_save,
                          style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                                               padding=ft.padding.symmetric(horizontal=18))),
    ])

    dlg = ft.AlertDialog(
        modal=True,
        bgcolor=GLASS["surface_solid"],
        title=ft.Row(controls=[
            ft.Icon(ft.icons.EDIT_DOCUMENT if is_edit else ft.icons.ADD_CIRCLE_OUTLINE, size=20, color=GLASS["accent"]),
            ft.Text("Карточка контроля" if is_edit else "Добавить контроль", size=17, weight=ft.FontWeight.BOLD,
                    color=GLASS["text"], expand=True),
            ft.IconButton(icon=ft.icons.CLOSE, icon_color=GLASS["text_2"], icon_size=20, on_click=_close),
        ], spacing=8, tight=True),
        content=content_holder,
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        shape=ft.RoundedRectangleBorder(radius=14),
    )
    dialog_ref["dlg"] = dlg
    return dlg

# ui/controls/control_card_modal.py
# Рефактор: inline-выбор исполнителей/ответственных без вложенных диалогов
# Fix Bug B (вложенные модалки), Bug F (спам логов и overlay), Bug A (FilePicker mount)
import os
from datetime import date, datetime, timedelta
from typing import Callable, List, Optional
from uuid import uuid4

import flet as ft

from core.constants import COLORS
from .glass_theme import GLASS, _RADIUS as _GLASS_RADIUS, _RADIUS_CARD
from core.controls_models import (
    Control, ControlTask, ControlMilestone, ONE_TIME, PERIODIC,
    parse_date, short_name,
)
from core.controls_data import (
    get_initiators, add_custom_initiator,
    copy_attachment_to_local, copy_attachment_to_shared,
    resolve_attachment, delete_attachment, ATTACHMENT_WARN_MB,
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

def _iso(v) -> Optional[str]:
    try:
        if v is None:
            return None
        if hasattr(v, "strftime"):
            return v.strftime("%Y-%m-%d")
        return str(v)
    except Exception:
        return None

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

def _build_inline_multi(page: ft.Page, available: List[str], initial: List[str], title: str):
    selected = list(initial)
    expanded = {"value": False}
    search_val = {"value": ""}

    badge = ft.Text(f"Выбрано: {len(selected)}", size=11, color=COLORS["text_secondary"])
    summary = ft.Text(", ".join(short_name(x) for x in selected) or "не выбрано",
                      size=11, color=COLORS["text"], max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
                      tooltip=", ".join(selected))

    search_field = ft.TextField(
        hint_text=f"Поиск {title.lower()}…",
        prefix_icon=ft.icons.SEARCH,
        height=34, dense=True,
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"], size=11),
        visible=False,
    )
    list_col = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=140, visible=False)
    wrapper = ft.Container(content=list_col, border=ft.border.all(1, COLORS["border"]),
                           border_radius=8, padding=ft.padding.all(4),
                           bgcolor=COLORS["primary_light"], visible=False)

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
                            active_color=COLORS["btn_save"], label_style=ft.TextStyle(size=11, color=COLORS["text"]),
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

    expand_btn = ft.IconButton(icon=ft.icons.EXPAND_MORE, icon_size=18, icon_color=COLORS["text_secondary"], on_click=_toggle)
    header = ft.Row(controls=[
        ft.Text(title, size=12, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
        ft.Container(width=6), badge, ft.Container(expand=True),
        ft.TextButton("Очистить", on_click=_clear, style=ft.ButtonStyle(color="#f87171")),
        expand_btn,
    ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    _rebuild()
    cont = ft.Container(
        content=ft.Column(controls=[header, summary, search_field, wrapper], spacing=4, tight=True),
        bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]), border_radius=8,
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
    # fix Bug F: no spam print, single creation log ASCII only
    print("[CONTROL_MODAL] create card modal (rework inline)")
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

    # single DatePicker for modal (mount once)
    _date_target = {"setter": None}
    def _on_date_change(e):
        s = _date_target["setter"]
        if s is None:
            return
        iso = _iso(getattr(e.control, "value", None))
        if iso:
            try:
                s(iso)
            except Exception:
                pass

    date_picker_attr = "_control_card_date_picker"
    if not hasattr(page, date_picker_attr):
        dp = ft.DatePicker(first_date=datetime(2020,1,1), last_date=datetime(2035,12,31), on_change=_on_date_change)
        page.overlay.append(dp)
        setattr(page, date_picker_attr, dp)
        try:
            page.update()
        except Exception:
            pass
    else:
        try:
            getattr(page, date_picker_attr).on_change = _on_date_change
        except Exception:
            pass
        dp = getattr(page, date_picker_attr)

    def _pick_date(setter):
        _date_target["setter"] = setter
        try:
            dp.pick_date()
        except Exception:
            pass

    # fields
    incoming_field = ft.TextField(
        value=control.incoming_number if is_edit else "",
        hint_text="Входящий № ВХСОП *",
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        dense=True, expand=True,
    )
    receive_ref = {"value": control.receive_date if is_edit else date.today().isoformat()}
    receive_field = ft.TextField(
        value=_display(receive_ref["value"]),
        hint_text="Дата поступления *",
        read_only=True, width=150, dense=True,
        border_radius=8, border_color=COLORS["border"],
        bgcolor=COLORS["card"], color=COLORS["text"],
    )
    def _set_receive(iso):
        receive_ref["value"] = iso
        receive_field.value = _display(iso)
        try:
            receive_field.update()
        except Exception:
            pass

    init_dd = ft.Dropdown(
        hint_text="Инициатор",
        value=control.initiator if (is_edit and control.initiator in initiators) else None,
        options=[ft.dropdown.Option(i) for i in initiators],
        width=220, height=38,
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        dense=True,
    )
    new_init_field = ft.TextField(hint_text="Новый инициатор", width=180, height=36, dense=True,
                                  border_radius=8, border_color=COLORS["border"],
                                  bgcolor=COLORS["card"], color=COLORS["text"])
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
    add_init_btn = ft.ElevatedButton("Добавить", height=36, bgcolor=COLORS["primary_light"], color=COLORS["btn_save"], on_click=_add_init)

    content_field = ft.TextField(
        value=control.content if is_edit else "",
        hint_text="Содержание",
        multiline=True, min_lines=2, max_lines=4,
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
    )

    exec_picker = _build_inline_multi(page, available_names, list(control.executors) if is_edit else [], "Исполнители")

    controller_dd = ft.Dropdown(
        hint_text="За кем контроль",
        value=control.controller if (is_edit and control.controller in available_names) else None,
        options=[ft.dropdown.Option(n, short_name(n)) for n in available_names],
        width=180, height=38,
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        dense=True,
    )

    type_dd = ft.Dropdown(
        hint_text="Тип",
        value=control.control_type if is_edit else ONE_TIME,
        options=[ft.dropdown.Option(ONE_TIME, "Разовый"), ft.dropdown.Option(PERIODIC, "Постоянный")],
        width=130, height=38,
        border_radius=8, border_color=COLORS["border"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        dense=True,
    )
    period_dd = ft.Dropdown(
        hint_text="Периодичность",
        value=_period_key(control.period_days if is_edit else 7),
        options=[ft.dropdown.Option(k, l) for k, l, _ in _PERIOD_LABELS],
        width=170, height=38,
        border_radius=8, border_color=COLORS["border"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        dense=True,
        visible=(control.control_type if is_edit else ONE_TIME) == PERIODIC,
    )
    custom_days_field = ft.TextField(
        value=str(control.period_days) if is_edit else "7",
        hint_text="Интервал дней",
        width=110, height=38, dense=True,
        border_radius=8, border_color=COLORS["border"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        visible=_period_key(control.period_days if is_edit else 7) == "custom",
    )
    due_ref = {"value": control.due_date if is_edit else None}
    due_field = ft.TextField(
        value=_display(due_ref["value"]),
        hint_text="Следующая дата исполнения",
        read_only=True, width=160, dense=True,
        border_radius=8, border_color=COLORS["border"],
        bgcolor=COLORS["card"], color=COLORS["text"],
    )
    def _set_due(iso):
        due_ref["value"] = iso
        due_field.value = _display(iso)
        try:
            due_field.update()
        except Exception:
            pass
    end_ref = {"value": control.end_date if is_edit else None}
    end_field = ft.TextField(
        value=_display(end_ref["value"]),
        hint_text="Конечная дата",
        read_only=True, width=130, dense=True,
        border_radius=8, border_color=COLORS["border"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        visible=(control.control_type if is_edit else ONE_TIME) == PERIODIC,
    )
    def _set_end(iso):
        end_ref["value"] = iso
        end_field.value = _display(iso)
        try:
            end_field.update()
        except Exception:
            pass

    def _on_type_change(e):
        is_per = (e.control.value == PERIODIC)
        period_dd.visible = is_per
        end_field.visible = is_per
        milestones_header.visible = is_per
        milestones_col.visible = is_per
        try:
            period_dd.update()
            end_field.update()
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

    comment_field = ft.TextField(
        value=control.comment if is_edit else "",
        hint_text="Комментарий",
        multiline=True, min_lines=1, max_lines=3,
        border_radius=8, border_color=COLORS["border"],
        bgcolor=COLORS["card"], color=COLORS["text"],
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
        due_f = ft.TextField(value=_display(ui["due_ref"]["value"]), read_only=True, width=110, dense=True, height=34,
                             border_radius=8, border_color=COLORS["border"], bgcolor=COLORS["card"], color=COLORS["text"])
        def _set_t_due(iso, u=ui, tf=due_f):
            u["due_ref"]["value"] = iso
            tf.value = _display(iso)
            try:
                tf.update()
            except Exception:
                pass
        return ft.Container(
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Icon(ft.icons.LIST_ALT, size=14, color=COLORS["text_muted"]),
                    title_f,
                    ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=16, icon_color="#f87171",
                                  on_click=lambda e, u=ui: _remove_task(u)),
                ], spacing=6, tight=True),
                ass_picker,
                ft.Row(controls=[
                    ft.Text("Срок:", size=10, color=COLORS["text_secondary"]),
                    due_f,
                    ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_size=14, icon_color=COLORS["btn_save"],
                                  on_click=lambda e, s=_set_t_due: _pick_date(s)),
                ], spacing=4, tight=True),
            ], spacing=4, tight=True),
            bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]), border_radius=8, padding=ft.padding.all(8),
        )

    def _remove_task(ui):
        if ui in tasks_state:
            tasks_state.remove(ui)
        _rebuild_tasks()

    def _add_task(e=None):
        new_ui = {
            "title_field": ft.TextField(hint_text="Пункт (напр. п.1)", height=36, dense=True, expand=True,
                                        border_radius=8, border_color=COLORS["border"],
                                        bgcolor=COLORS["card"], color=COLORS["text"]),
            "assignees": [],
            "due_ref": {"value": None},
            "ass_picker": None,
        }
        tasks_state.append(new_ui)
        _rebuild_tasks()

    if is_edit and control.tasks:
        for t in control.tasks:
            tasks_state.append({
                "title_field": ft.TextField(value=t.title, hint_text="Пункт", height=36, dense=True, expand=True,
                                            border_radius=8, border_color=COLORS["border"],
                                            bgcolor=COLORS["card"], color=COLORS["text"]),
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
            date_f = ft.Text(_display(ui["date_ref"]["value"]), size=11, width=90)
            def _mk_set(u, tf):
                def _s(iso):
                    u["date_ref"]["value"] = iso
                    tf.value = _display(iso)
                    try:
                        tf.update()
                    except Exception:
                        pass
                return _s
            note_f = ft.TextField(value=ui["note"], hint_text="Точка", height=34, dense=True, expand=True,
                                  border_radius=8, border_color=COLORS["border"],
                                  bgcolor=COLORS["card"], color=COLORS["text"],
                                  on_change=lambda e, u=ui: u.update({"note": e.control.value or ""}))
            milestones_col.controls.append(
                ft.Container(
                    content=ft.Row(controls=[
                        date_f,
                        ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_size=14, icon_color=COLORS["btn_save"],
                                      on_click=lambda e, s=_mk_set(ui, date_f): _pick_date(s)),
                        note_f,
                        ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=16, icon_color="#f87171",
                                      on_click=lambda e, u=ui: _remove_mile(u)),
                    ], spacing=4, tight=True),
                    bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]), border_radius=8,
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
                        ft.Icon(ft.icons.ATTACH_FILE, size=14, color=COLORS["btn_save"]),
                        ft.Text(fn, size=11, expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, tooltip=fn, color=COLORS["text"]),
                        ft.IconButton(icon=ft.icons.OPEN_IN_NEW, icon_size=14, icon_color=COLORS["btn_save"],
                                      on_click=lambda e, r=rel: _open_att(r)),
                        ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=14, icon_color="#f87171",
                                      on_click=lambda e, r=rel: _remove_att(r)),
                    ], spacing=4, tight=True),
                    bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]), border_radius=8,
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
            modal=True, bgcolor=COLORS["primary_light"],
            title=ft.Text("Удаление вложения", size=14, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            content=ft.Text("Удалить файл?", size=12, color=COLORS["text"]),
            actions=[ft.TextButton("Отмена", on_click=_cancel),
                     ft.ElevatedButton("Удалить", bgcolor="#dc2626", color="white", on_click=_confirm)],
            shape=ft.RoundedRectangleBorder(radius=10),
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
                allowed_extensions=["pdf","png","jpg","jpeg"],
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
        ft.Icon(ft.icons.TIMELINE, size=15, color=COLORS["text"]),
        ft.Text("Промежуточные точки", size=12, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
        ft.Container(expand=True),
        ft.ElevatedButton("+ Добавить точку", bgcolor=COLORS["primary_light"], color=COLORS["btn_save"], height=28, on_click=_add_mile),
    ], spacing=6, tight=True, visible=(control.control_type if is_edit else ONE_TIME) == PERIODIC)

    tasks_header = ft.Row(controls=[
        ft.Icon(ft.icons.FORMAT_LIST_BULLETED, size=16, color=COLORS["text"]),
        ft.Text("Пункты задания", size=13, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
        ft.Container(expand=True),
        ft.ElevatedButton("+ Добавить пункт", bgcolor=COLORS["primary_light"], color=COLORS["btn_save"], height=30, on_click=_add_task),
    ], spacing=6, tight=True)

    attach_header = ft.Row(controls=[
        ft.Icon(ft.icons.ATTACH_FILE, size=15, color=COLORS["text"]),
        ft.Text("Скан задания", size=13, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
        ft.Container(expand=True),
        ft.ElevatedButton("Прикрепить файл", bgcolor=COLORS["primary_light"], color=COLORS["btn_save"], height=30,
                          icon=ft.icons.ATTACH_FILE, on_click=_pick_attach),
    ], spacing=6, tight=True)

    content_holder = ft.Container(
        width=card_w, height=card_h,
        content=ft.Column(controls=[
            ft.Row(controls=[incoming_field, receive_field,
                             ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_color=COLORS["btn_save"],
                                           on_click=lambda e: _pick_date(lambda iso: _set_receive(iso)))],
                   spacing=6, tight=True),
            ft.Row(controls=[init_dd, new_init_field, add_init_btn], spacing=6, tight=True),
            content_field,
            exec_picker,
            ft.Row(controls=[controller_dd, type_dd, period_dd, custom_days_field], spacing=6, tight=True),
            ft.Row(controls=[due_field,
                             ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_color=COLORS["btn_save"],
                                           on_click=lambda e: _pick_date(lambda iso: _set_due(iso))),
                             end_field,
                             ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_color=COLORS["btn_save"],
                                           on_click=lambda e: _pick_date(lambda iso: _set_end(iso)))],
                   spacing=6, tight=True),
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
        bgcolor=COLORS["primary_light"],
    )

    actions = []
    if is_edit and on_delete:
        actions.append(ft.ElevatedButton("Удалить", icon=ft.icons.DELETE_FOREVER, bgcolor="#dc2626", color="white", on_click=_delete))
    actions.extend([
        ft.TextButton("Отмена", on_click=_close, style=ft.ButtonStyle(color=COLORS["text_secondary"])),
        ft.ElevatedButton("Сохранить", icon=ft.icons.SAVE, bgcolor=COLORS["btn_save"], color="white", on_click=_save),
    ])

    dlg = ft.AlertDialog(
        modal=True,
        bgcolor=GLASS["surface_solid"],
        title=ft.Row(controls=[
            ft.Icon(ft.icons.EDIT_DOCUMENT if is_edit else ft.icons.ADD_CIRCLE_OUTLINE, size=20, color="white"),
            ft.Text("Карточка контроля" if is_edit else "Добавить контроль", size=15, weight=ft.FontWeight.BOLD, color="white", expand=True),
            ft.IconButton(icon=ft.icons.CLOSE, icon_color="white", icon_size=18, on_click=_close),
        ], spacing=8, tight=True),
        content=content_holder,
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        shape=ft.RoundedRectangleBorder(radius=_RADIUS_CARD),
    )
    dialog_ref["dlg"] = dlg
    return dlg

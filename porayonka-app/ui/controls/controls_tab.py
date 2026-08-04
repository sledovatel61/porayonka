# ui/controls/controls_tab.py
# Вкладка «Контроли» — Glass Dark редизайн
# Фон #0a1024, стекло #16213dcc, кастомный русский календарь, мастер-деталь overlay
import threading
import time
import traceback
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict
from uuid import uuid4

import flet as ft

from core.controls_models import (
    Control, ControlTask, ControlMilestone, PERIODIC, ONE_TIME,
    effective_due_date, deadline_status, parse_date, short_name,
    STATUS_LABELS, STATUS_COLORS,
    OVERDUE, TODAY, SOON, IN_PROGRESS, DONE, COMPLETED, NO_DATE,
    ARCHIVE_DONE, ARCHIVE_DELETED,
)
from core.controls_data import (
    load_controls, save_controls, load_settings, save_settings,
    get_criminalist_names, get_initiators,
    archive_control, restore_control,
    delete_all_attachments,
    read_shared_controls, write_shared_controls, get_shared_mtime,
    sync_attachments_from_shared,
    copy_attachment_to_local, copy_attachment_to_shared,
    resolve_attachment, delete_attachment, ATTACHMENT_WARN_MB,
    add_custom_initiator,
)
from core.controls_exporter import ControlsExcelExporter, import_from_excel
from .glass_theme import GLASS, STATUS_COLORS_GLASS, glass_border
from .russian_calendar import create_russian_date_field

# Иконки статусов — берём из Flet
STATUS_ICONS_GLASS = {
    OVERDUE: ft.icons.ERROR_OUTLINE,
    TODAY: ft.icons.TODAY_OUTLINED,
    SOON: ft.icons.HOURGLASS_BOTTOM_ROUNDED,
    IN_PROGRESS: ft.icons.AUTORENEW,
    DONE: ft.icons.CHECK_CIRCLE_OUTLINE,
    COMPLETED: ft.icons.VERIFIED_OUTLINED,
    NO_DATE: ft.icons.REMOVE_CIRCLE_OUTLINE,
}

_FIXED = {
    "bar": 4,
    "num": 40,
    "incoming": 165,  # >=150 по ТЗ
    "receive": 98,
    "initiator": 110,
    "controller": 120,
    "type": 86,
    "due": 110,
    "status": 128,
    "actions": 90,
}
_ROW_HEIGHT = 54
_TAB_HORIZONTAL_PADDING = 32
_PERIOD_LABELS = [
    ("daily", "Ежедневно", 1),
    ("weekly", "Еженедельно", 7),
    ("monthly", "Ежемесячно", 30),
    ("quarterly", "Ежеквартально", 91),
    ("yearly", "Ежегодно", 365),
    ("custom", "Свой интервал", 0),
]
_PERIOD_DAYS = {k: d for k, _, d in _PERIOD_LABELS}

def _display_date(iso: Optional[str]) -> str:
    d = parse_date(iso)
    return d.strftime("%d.%m.%Y") if d else "—"

def _display_date_or_none(iso: Optional[str]) -> str:
    d = parse_date(iso)
    return d.strftime("%d.%m.%Y") if d else "не указана"

def _type_label(ctl: Control) -> str:
    return "постоянный" if ctl.control_type == PERIODIC else "разовый"

def _reason_label(reason: str) -> str:
    return "Исполнен" if reason == ARCHIVE_DONE else ("Удалён" if reason == ARCHIVE_DELETED else "")

def _period_key(days: int) -> str:
    for k, _, d in _PERIOD_LABELS:
        if d == days and k != "custom":
            return k
    return "custom"

def _ensure_file_picker(page: ft.Page, attr: str, on_result):
    if not hasattr(page, attr):
        picker = ft.FilePicker(on_result=on_result)
        page.overlay.append(picker)
        setattr(page, attr, picker)
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

def create_controls_tab(page: ft.Page) -> ft.Column:
    print("[CONTROLS_TAB] Init Glass Dark")
    settings = load_settings()
    soon_days = int(settings.get("soon_days", 3) or 3)
    available_names = get_criminalist_names()
    initiators = get_initiators(settings)
    network_user = settings.get("network_user", "") or ""
    network_role = settings.get("network_role", "admin")

    state = {
        "controls": [],
        "mode": "active",
        "sort_key": "due",
        "sort_reverse": False,
        "search": "",
        "f_status": "all",
        "f_type": "all",
        "f_initiator": "all",
        "f_executor": "all",
        "f_controller": "all",
        "f_from": None,
        "f_to": None,
        "shared_mtime": None,
        "last_overdue": -1,
        "last_sync": None,
        "network_ok": False,
        "editing": False,
    }

    rows_column = ft.Column(spacing=4, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    sync_label = ft.Text("Локально", size=11, color=GLASS["text_secondary"])
    sync_dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=GLASS["text_muted"])

    def _layout_widths(width: Optional[float]) -> Dict[str, int]:
        if not width or width <= 0:
            width = 1280
        available = max(500.0, width - _TAB_HORIZONTAL_PADDING)
        fixed_sum = sum(_FIXED.values())
        flex = max(280.0, available - fixed_sum)
        w = dict(_FIXED)
        # ужать Содержание и Исполнители, а не номер (по ТЗ)
        w["executors"] = int(flex * 0.42)
        w["content"] = int(flex - w["executors"])
        return w

    _W = _layout_widths(page.width)

    # ── Persistence ─────────────────────────────────────────────
    def _persist(controls: List[Control], to_shared: bool = True):
        save_controls(controls)
        state["last_sync"] = datetime.now()
        if settings.get("network_enabled") and to_shared:
            ok = write_shared_controls(controls, settings)
            state["network_ok"] = bool(ok)
            try:
                state["shared_mtime"] = get_shared_mtime(settings)
            except Exception:
                state["shared_mtime"] = None
        _update_sync_ui()

    def _load_initial():
        if settings.get("network_enabled"):
            shared = read_shared_controls(settings)
            if shared:
                state["controls"] = shared
                state["network_ok"] = True
            else:
                state["controls"] = load_controls()
                state["network_ok"] = False
            try:
                state["shared_mtime"] = get_shared_mtime(settings)
            except Exception:
                state["shared_mtime"] = None
            for c in state["controls"]:
                try:
                    sync_attachments_from_shared(c.id, c.attachments, settings)
                except Exception:
                    pass
        else:
            state["controls"] = load_controls()
        _update_sync_ui()

    def _update_sync_ui():
        net = settings.get("network_enabled")
        if not net:
            sync_label.value = "Локально"
            sync_dot.bgcolor = GLASS["text_muted"]
        else:
            role = "админ" if network_role == "admin" else "пользователь"
            sync_label.value = f"Сеть: {role}"
            sync_dot.bgcolor = GLASS["in_work"] if state["network_ok"] else GLASS["overdue"]
            if state["last_sync"]:
                sync_label.value += f" · {state['last_sync'].strftime('%H:%M:%S')}"
        try:
            sync_label.update()
            sync_dot.update()
        except Exception:
            pass

    def _visible_base() -> List[Control]:
        lst = state["controls"]
        if network_role == "user" and network_user:
            def mine(c: Control) -> bool:
                if network_user in c.executors:
                    return True
                for t in c.tasks:
                    if network_user in t.assignees:
                        return True
                return False
            lst = [c for c in lst if mine(c)]
        if state["mode"] == "archive":
            lst = [c for c in lst if c.archived]
        else:
            lst = [c for c in lst if not c.archived]
        return lst

    # ── Filtering ───────────────────────────────────────────────
    def _filtered() -> List[Control]:
        base = _visible_base()
        q = state["search"].lower().strip()

        def _match(ctl: Control) -> bool:
            if state["f_status"] != "all" and deadline_status(ctl, soon_days) != state["f_status"]:
                return False
            if state["f_type"] != "all" and ctl.control_type != state["f_type"]:
                return False
            if state["f_initiator"] != "all" and ctl.initiator != state["f_initiator"]:
                return False
            if state["f_controller"] != "all" and ctl.controller != state["f_controller"]:
                return False
            if state["f_executor"] != "all" and state["f_executor"] not in ctl.executors:
                return False
            if state["f_from"]:
                dd = effective_due_date(ctl)
                if dd is not None:
                    fd = parse_date(state["f_from"])
                    if fd and dd < fd:
                        return False
            if state["f_to"]:
                dd = effective_due_date(ctl)
                if dd is not None:
                    td = parse_date(state["f_to"])
                    if td and dd > td:
                        return False
            if q:
                hay = " ".join([
                    ctl.incoming_number, ctl.content, ctl.initiator, ctl.controller,
                    ctl.due_date or "", " ".join(ctl.executors),
                    " ".join(t.title for t in ctl.tasks),
                ]).lower()
                if q not in hay:
                    return False
            return True

        result = [c for c in base if _match(c)]

        def _sort_val(ctl: Control):
            k = state["sort_key"]
            if k == "num":
                try:
                    return (base.index(ctl),)
                except ValueError:
                    return (0,)
            if k == "incoming":
                return (ctl.incoming_number.lower(),)
            if k == "receive":
                d = parse_date(ctl.receive_date)
                return (d.toordinal() if d else 0,)
            if k == "initiator":
                return (ctl.initiator.lower(),)
            if k == "type":
                return (ctl.control_type,)
            if k == "status":
                order = {OVERDUE: 0, TODAY: 1, SOON: 2, IN_PROGRESS: 3, NO_DATE: 4, DONE: 5, COMPLETED: 6}
                return (order.get(deadline_status(ctl, soon_days), 9),)
            d = effective_due_date(ctl)
            return (d.toordinal() if d else 999999,)

        result.sort(key=_sort_val, reverse=state["sort_reverse"])
        return result

    def _apply_filters():
        _rebuild_table()

    # ── Glass helpers ───────────────────────────────────────────
    def _glass_tf(hint, value="", width=None, expand=False, multiline=False, min_lines=1, max_lines=1, password=False, read_only=False, dense=True):
        # sunken field #0d1830
        return ft.TextField(
            value=value,
            hint_text=hint,
            width=width,
            expand=expand,
            multiline=multiline,
            min_lines=min_lines if multiline else None,
            max_lines=max_lines if multiline else 1,
            password=password,
            read_only=read_only,
            dense=dense,
            border_radius=10,
            border_color=GLASS["border"],
            focused_border_color=GLASS["accent"],
            bgcolor=GLASS["surface_alt"],
            color=GLASS["text"],
            hint_style=ft.TextStyle(color=GLASS["text_muted"], size=13),
            text_style=ft.TextStyle(size=13, color=GLASS["text"]),
            content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        )

    def _glass_dd(hint, width, options, value="all", dense=True):
        return ft.Dropdown(
            hint_text=hint,
            width=width,
            value=value,
            options=options,
            border_radius=10,
            border_color=GLASS["border"],
            focused_border_color=GLASS["accent"],
            bgcolor=GLASS["surface_alt"],
            color=GLASS["text"],
            hint_style=ft.TextStyle(color=GLASS["text_muted"], size=13),
            text_style=ft.TextStyle(size=13, color=GLASS["text"]),
            dense=dense,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

    def _label(text):
        return ft.Text(text, size=11, weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"])

    def _labeled(label_text, control):
        return ft.Column(controls=[_label(label_text), control], spacing=4, tight=True)

    # cell
    def _cell(text: str, width: int, color=GLASS["text"], size=12, bold=False, center=False, tooltip=None, max_lines=1):
        return ft.Container(
            content=ft.Text(
                text, size=size, color=color,
                weight=ft.FontWeight.W_600 if bold else None,
                no_wrap=not center, max_lines=max_lines,
                overflow=ft.TextOverflow.ELLIPSIS,
                tooltip=tooltip or (text if len(text) > 18 else None),
            ),
            width=width,
            padding=ft.padding.only(left=6, right=4),
            alignment=ft.alignment.center if center else ft.alignment.center_left,
        )

    def _action_btn(icon, icon_color, tooltip, handler):
        def _hover(e):
            try:
                e.control.bgcolor = GLASS["hover_light"] if e.data == "true" else "transparent"
                e.control.update()
            except Exception:
                pass
        return ft.Container(
            content=ft.Icon(icon, size=16, color=icon_color),
            width=30, height=30,
            border_radius=8,
            bgcolor="transparent",
            alignment=ft.alignment.center,
            tooltip=tooltip,
            ink=True,
            on_click=handler,
            on_hover=_hover,
        )

    # ── Row building ────────────────────────────────────────────
    def _build_row(ctl: Control, num: int, idx: int) -> ft.Container:
        status = deadline_status(ctl, soon_days)
        color = STATUS_COLORS_GLASS.get(status, GLASS["text_muted"])
        content = ctl.content or ctl.incoming_number
        content_tooltip = ctl.content or ""
        if ctl.tasks:
            task_txt = "; ".join(t.title for t in ctl.tasks if t.title)
            if task_txt:
                content_tooltip = (content_tooltip + "\n" + task_txt).strip()
        # alternating bg
        bg = GLASS["surface_alt_2"] if idx % 2 == 0 else "transparent"

        # due string
        eff_due = effective_due_date(ctl)
        due_str = _display_date(eff_due.isoformat() if eff_due else ctl.due_date)
        due_color = GLASS["text"]
        if status in (OVERDUE, TODAY, SOON):
            due_color = color

        # content + attachment
        content_controls = []
        content_controls.append(_cell(content, _W["content"] - (26 if ctl.attachments else 0), tooltip=content_tooltip, max_lines=2, size=13, color=GLASS["text"]))
        if ctl.attachments:
            content_controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.icons.ATTACH_FILE, size=12, color=GLASS["accent"]),
                            ft.Text(str(len(ctl.attachments)), size=10, color=GLASS["accent"], no_wrap=True),
                        ],
                        spacing=2, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    width=26,
                )
            )

        is_archive = state["mode"] == "archive"
        type_cell = _cell(_type_label(ctl), _W["type"], color=GLASS["text_secondary"], size=11)
        if is_archive:
            reason = ctl.archive_reason or ""
            reason_text = _reason_label(reason)
            if ctl.archived_at:
                reason_text = f"{reason_text} · {_display_date(ctl.archived_at)}"
            type_cell = _cell(reason_text, _W["type"], color=GLASS["text_secondary"], tooltip=reason, size=11)

        actions = []
        if is_archive:
            actions.append(_action_btn(ft.icons.RESTORE, GLASS["in_work"], "Восстановить", lambda e, c=ctl: _restore(c)))
            actions.append(_action_btn(ft.icons.DELETE_FOREVER, GLASS["overdue"], "Удалить навсегда", lambda e, c=ctl: _delete_forever(c)))
        else:
            actions.append(_action_btn(ft.icons.CHECK_CIRCLE_OUTLINE, GLASS["in_work"], "Исполнено", lambda e, c=ctl: _complete(c)))
            actions.append(_action_btn(ft.icons.UPDATE_OUTLINED, GLASS["text_secondary"], "Продлить срок", lambda e, c=ctl: _extend(c)))
            actions.append(_action_btn(ft.icons.DELETE_OUTLINE, GLASS["overdue"], "В архив", lambda e, c=ctl: _confirm_delete(c)))

        # status pill
        status_label = STATUS_LABELS.get(status, status)
        pill = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(STATUS_ICONS_GLASS.get(status, ft.icons.REMOVE_CIRCLE_OUTLINE), size=12, color=color),
                    ft.Text(status_label, size=11, weight=ft.FontWeight.W_600, color=color, no_wrap=True),
                ],
                spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER,
            ),
            width=_W["status"],
            height=24,
            border_radius=12,
            bgcolor=f"{color}22",
            border=ft.border.all(1, color),
            alignment=ft.alignment.center,
            padding=ft.padding.symmetric(horizontal=6),
        )

        row_controls = [
            ft.Container(width=_W["bar"], height=32, bgcolor=color, border_radius=2),
            _cell(str(num), _W["num"], center=True, color=GLASS["text_secondary"], size=11),
            _cell(ctl.incoming_number or "—", _W["incoming"], bold=True, tooltip=ctl.incoming_number, size=13, color=GLASS["text"]),
            _cell(_display_date(ctl.receive_date), _W["receive"], color=GLASS["text_secondary"], size=12),
            _cell(short_name(ctl.initiator) if ctl.initiator else "—", _W["initiator"], tooltip=ctl.initiator, size=12, color=GLASS["text_secondary"]),
            ft.Row(controls=content_controls, spacing=2, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            _cell(", ".join(short_name(x) for x in ctl.executors) or "—", _W["executors"], tooltip=", ".join(ctl.executors), size=12, color=GLASS["text"]),
            _cell(short_name(ctl.controller) if ctl.controller else "—", _W["controller"], tooltip=ctl.controller, size=12, color=GLASS["text_secondary"]),
            type_cell,
            _cell(due_str, _W["due"], bold=True, color=due_color, size=12),
            pill,
        ]
        row_controls.append(ft.Row(controls=actions, spacing=2, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER))

        def _row_hover(e):
            try:
                if e.data == "true":
                    e.control.bgcolor = GLASS["hover"]
                else:
                    e.control.bgcolor = bg
                e.control.update()
            except Exception:
                pass

        return ft.Container(
            content=ft.Row(controls=row_controls, spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=_ROW_HEIGHT,
            bgcolor=bg,
            border=ft.border.all(1, GLASS["border"]),
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=6, vertical=4),
            on_click=lambda e, c=ctl: _open_detail(c),
            on_hover=_row_hover,
        )

    def _rebuild_table():
        rows_column.controls.clear()
        visible = _filtered()
        if not visible:
            label = "В архиве пусто" if state["mode"] == "archive" else "Контролей не найдено"
            rows_column.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.icons.INBOX, size=18, color=GLASS["text_muted"]),
                            ft.Text(label, size=12, color=GLASS["text_secondary"]),
                        ],
                        spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    height=54,
                    bgcolor=GLASS["surface"],
                    border=ft.border.all(1, GLASS["border"]),
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=12),
                )
            )
            try:
                rows_column.update()
            except Exception:
                pass
            return
        for i, ctl in enumerate(visible, 1):
            rows_column.controls.append(_build_row(ctl, i, i-1))
        try:
            rows_column.update()
        except Exception:
            pass

    # ── Counters ────────────────────────────────────────────────
    counter_refs: Dict[str, ft.Container] = {}

    def _counts():
        res = {"all": 0, OVERDUE: 0, TODAY: 0, SOON: 0, IN_PROGRESS: 0, DONE: 0, COMPLETED: 0}
        for ctl in _visible_base():
            res["all"] += 1
            st = deadline_status(ctl, soon_days)
            res[st] = res.get(st, 0) + 1
        return res

    def _set_status_filter(value: str):
        state["f_status"] = value if state["f_status"] != value else "all"
        # sync dropdown if exists
        try:
            status_filter_dd.value = state["f_status"]
            status_filter_dd.update()
        except Exception:
            pass
        _restyle_counters()
        _apply_filters()

    def _restyle_counters():
        for key, btn in counter_refs.items():
            selected = (state["f_status"] == key)
            try:
                # btn content Row: [dot, label, badge]
                dot = btn.content.controls[0]
                label = btn.content.controls[1]
                badge = btn.content.controls[2]
                if selected:
                    col = GLASS["accent"] if key == "all" else STATUS_COLORS_GLASS.get(key, GLASS["accent"])
                    btn.bgcolor = f"{col}22"
                    btn.border = ft.border.all(1, col)
                    label.color = GLASS["text"]
                    badge.bgcolor = GLASS["surface_solid"]
                    badge.content.color = GLASS["text"]
                else:
                    btn.bgcolor = "transparent"
                    btn.border = ft.border.all(1, GLASS["border"])
                    label.color = GLASS["text_secondary"]
                    badge.bgcolor = GLASS["surface_solid"]
                    badge.content.color = GLASS["text_secondary"]
                btn.update()
            except Exception:
                pass

    def _refresh_counters():
        counts = _counts()
        for key, btn in counter_refs.items():
            try:
                badge = btn.content.controls[2]
                badge.content.value = str(counts.get(key, 0))
                badge.update()
            except Exception:
                pass
        _restyle_counters()

    def _mk_counter(key: str, label: str, color: str, icon_char=None):
        counts = _counts()
        # dot 8px
        dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=color if key != "all" else GLASS["accent"])
        badge = ft.Container(
            content=ft.Text(str(counts.get(key, 0)), size=11, weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"]),
            height=20,
            padding=ft.padding.symmetric(horizontal=7),
            border_radius=10,
            bgcolor=GLASS["surface_solid"],
            alignment=ft.alignment.center,
        )
        lbl = ft.Text(label, size=12, color=GLASS["text_secondary"], no_wrap=True)
        row = ft.Row(controls=[dot, lbl, badge], spacing=5, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        cont = ft.Container(
            content=row,
            height=30,
            padding=ft.padding.symmetric(horizontal=10),
            border_radius=15,
            bgcolor="transparent",
            border=ft.border.all(1, GLASS["border"]),
            ink=True,
            on_click=lambda e, v=key: _set_status_filter(v),
        )
        counter_refs[key] = cont
        return cont

    counters_row_content = ft.Row(
        controls=[
            _mk_counter("all", "Все", GLASS["accent"]),
            _mk_counter(OVERDUE, "Просрочено", STATUS_COLORS_GLASS[OVERDUE]),
            _mk_counter(TODAY, "Сегодня", STATUS_COLORS_GLASS[TODAY]),
            _mk_counter(SOON, "Скоро", STATUS_COLORS_GLASS[SOON]),
            _mk_counter(IN_PROGRESS, "В работе", STATUS_COLORS_GLASS[IN_PROGRESS]),
            _mk_counter(DONE, "Исполнено", STATUS_COLORS_GLASS[DONE]),
        ],
        spacing=6,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.START,
    )

    # ── Mode switch ─────────────────────────────────────────────
    def _set_mode(mode: str):
        state["mode"] = mode
        _restyle_mode_buttons()
        _rebuild_table()
        _refresh_counters()
        _rebuild_header()

    mode_buttons: Dict[str, ft.Container] = {}

    def _restyle_mode_buttons():
        for m, btn in mode_buttons.items():
            selected = (state["mode"] == m)
            try:
                fg = GLASS["text"] if selected else GLASS["text_secondary"]
                btn.bgcolor = GLASS["accent"] if selected else "transparent"
                btn.border = ft.border.all(1, GLASS["accent"] if selected else GLASS["border"])
                # update text colors
                for ctl in btn.content.controls:
                    if isinstance(ctl, ft.Text):
                        ctl.color = "white" if selected else GLASS["text_secondary"]
                    elif isinstance(ctl, ft.Icon):
                        ctl.color = "white" if selected else GLASS["text_secondary"]
                btn.update()
            except Exception:
                pass

    def _mk_mode_btn(mode: str, label: str, icon):
        sel = (state["mode"] == mode)
        btn = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=14, color="white" if sel else GLASS["text_secondary"]),
                    ft.Text(label, size=12, weight=ft.FontWeight.W_600, color="white" if sel else GLASS["text_secondary"], no_wrap=True),
                ],
                spacing=5, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=30,
            padding=ft.padding.symmetric(horizontal=12),
            border_radius=8,
            bgcolor=GLASS["accent"] if sel else "transparent",
            border=ft.border.all(1, GLASS["accent"] if sel else GLASS["border"]),
            ink=True,
            on_click=lambda e, m=mode: _set_mode(m),
        )
        mode_buttons[mode] = btn
        return btn

    mode_row = ft.Container(
        content=ft.Row(
            controls=[
                _mk_mode_btn("active", "Активные", ft.icons.PLAYLIST_PLAY),
                _mk_mode_btn("archive", "Архив", ft.icons.ARCHIVE_OUTLINED),
            ],
            spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        height=38,
        bgcolor=GLASS["surface"],
        border=glass_border(True),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=4, vertical=4),
    )

    # chips + mode combined row (glass panel)
    chips_with_mode = ft.Container(
        content=ft.Row(
            controls=[
                counters_row_content,
                ft.Container(expand=True),
                mode_row,
            ],
            spacing=8,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.START,
        ),
        height=48,
        bgcolor=GLASS["surface"],
        border=glass_border(True),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
    )

    # ── Filters ─────────────────────────────────────────────────
    search_field = ft.TextField(
        hint_text="Поиск по содержанию, номеру...",
        prefix_icon=ft.icons.SEARCH,
        border_radius=10,
        border_color=GLASS["border"],
        focused_border_color=GLASS["accent"],
        bgcolor=GLASS["surface_alt"],
        color=GLASS["text"],
        hint_style=ft.TextStyle(color=GLASS["text_muted"], size=13),
        text_style=ft.TextStyle(size=13, color=GLASS["text"]),
        height=40,
        expand=True,
        dense=True,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
    )

    def _on_search(e=None):
        state["search"] = search_field.value or ""
        _apply_filters()

    search_field.on_change = _on_search

    status_filter_dd = _glass_dd(
        "Все статусы", 170,
        [
            ft.dropdown.Option("all", "Все статусы"),
            ft.dropdown.Option(OVERDUE, "Просрочено"),
            ft.dropdown.Option(TODAY, "Сегодня"),
            ft.dropdown.Option(SOON, "Скоро"),
            ft.dropdown.Option(IN_PROGRESS, "В работе"),
            ft.dropdown.Option(DONE, "Исполнено"),
            ft.dropdown.Option(COMPLETED, "Завершён"),
        ],
    )
    type_filter_dd = _glass_dd(
        "Все типы", 150,
        [
            ft.dropdown.Option("all", "Все типы"),
            ft.dropdown.Option(ONE_TIME, "Разовый"),
            ft.dropdown.Option(PERIODIC, "Постоянный"),
        ],
    )
    initiator_filter_dd = _glass_dd(
        "Все инициаторы", 200,
        [ft.dropdown.Option("all", "Все инициаторы")] + [ft.dropdown.Option(i) for i in initiators],
    )
    executor_filter_dd = _glass_dd(
        "Все исполнители", 210,
        [ft.dropdown.Option("all", "Все исполнители")] + [ft.dropdown.Option(n, short_name(n)) for n in available_names],
    )
    controller_filter_dd = _glass_dd(
        "Все контролёры", 200,
        [ft.dropdown.Option("all", "Все контролёры")] + [ft.dropdown.Option(n, short_name(n)) for n in available_names],
    )

    def _on_filter_change(e=None):
        state["f_status"] = status_filter_dd.value or "all"
        state["f_type"] = type_filter_dd.value or "all"
        _restyle_counters()
        _apply_filters()

    def _on_named_filter_change(e=None):
        state["f_initiator"] = initiator_filter_dd.value or "all"
        state["f_executor"] = executor_filter_dd.value or "all"
        state["f_controller"] = controller_filter_dd.value or "all"
        _apply_filters()

    status_filter_dd.on_change = _on_filter_change
    type_filter_dd.on_change = _on_filter_change
    initiator_filter_dd.on_change = _on_named_filter_change
    executor_filter_dd.on_change = _on_named_filter_change
    controller_filter_dd.on_change = _on_named_filter_change

    # Russian calendars for filter dates
    def _set_from_iso(iso):
        state["f_from"] = iso
        _apply_filters()

    def _set_to_iso(iso):
        state["f_to"] = iso
        _apply_filters()

    filter_from_cal = create_russian_date_field(page, state["f_from"], _set_from_iso, hint="С:", width=148)
    filter_to_cal = create_russian_date_field(page, state["f_to"], _set_to_iso, hint="По:", width=148)

    def _reset_filters(e=None):
        search_field.value = ""
        state["search"] = ""
        for dd in (status_filter_dd, type_filter_dd, initiator_filter_dd, executor_filter_dd, controller_filter_dd):
            dd.value = "all"
        state.update(f_status="all", f_type="all", f_initiator="all", f_executor="all", f_controller="all", f_from=None, f_to=None)
        try:
            filter_from_cal._set_value(None)
            filter_to_cal._set_value(None)
        except Exception:
            pass
        _restyle_counters()
        try:
            page.update()
        except Exception:
            pass
        _apply_filters()

    # filters row 1 and 2 as glass panels
    filter_row1 = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(content=search_field, expand=True),
                status_filter_dd,
                type_filter_dd,
            ],
            spacing=8,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        height=56,
        bgcolor=GLASS["surface"],
        border=glass_border(True),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
    )

    filter_row2 = ft.Container(
        content=ft.Row(
            controls=[
                initiator_filter_dd,
                executor_filter_dd,
                controller_filter_dd,
                filter_from_cal,
                filter_to_cal,
                ft.Container(expand=True),
                ft.TextButton("Сброс", on_click=_reset_filters, style=ft.ButtonStyle(color=GLASS["accent"])),
            ],
            spacing=8,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=GLASS["surface"],
        border=glass_border(True),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
    )

    # ── Header ──────────────────────────────────────────────────
    def _header_cell(text: str, width: int, key: str, center=False) -> ft.Container:
        arrow = "▲" if (state["sort_key"] == key and not state["sort_reverse"]) else ("▼" if (state["sort_key"] == key and state["sort_reverse"]) else "")
        return ft.Container(
            content=ft.Text(f"{text} {arrow}".strip(), size=11, weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"], no_wrap=True, tooltip="Сортировка"),
            width=width,
            padding=ft.padding.only(left=6, right=4),
            alignment=ft.alignment.center if center else ft.alignment.center_left,
            on_click=lambda e, k=key: _sort_by(k),
        )

    def _sort_by(key: str):
        if state["sort_key"] == key:
            state["sort_reverse"] = not state["sort_reverse"]
        else:
            state["sort_key"] = key
            state["sort_reverse"] = False
        _rebuild_table()
        _rebuild_header()

    header_row = ft.Container(
        content=ft.Row(controls=[], spacing=2, tight=True),
        height=34,
        bgcolor=GLASS["surface_alt"],
        border=ft.border.all(1, GLASS["border"]),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=4, vertical=2),
    )

    def _rebuild_header():
        is_archive = state["mode"] == "archive"
        controls = [
            ft.Container(width=_W["bar"]),
            _header_cell("№", _W["num"], "num", center=True),
            _header_cell("ВХ. №", _W["incoming"], "incoming"),
            _header_cell("ДАТА ПОСТ.", _W["receive"], "receive"),
            _header_cell("ИНИЦИАТОР", _W["initiator"], "initiator"),
            ft.Container(
                width=_W["content"],
                padding=ft.padding.only(left=6, right=4),
                content=ft.Text("СОДЕРЖАНИЕ", size=11, weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"], no_wrap=True),
            ),
            ft.Container(
                width=_W["executors"],
                padding=ft.padding.only(left=6, right=4),
                content=ft.Text("ИСПОЛНИТЕЛИ", size=11, weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"], no_wrap=True),
            ),
            ft.Container(
                width=_W["controller"],
                padding=ft.padding.only(left=6, right=4),
                content=ft.Text("ЗА КЕМ", size=11, weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"], no_wrap=True),
            ),
            _header_cell("ПРИЧИНА" if is_archive else "ТИП", _W["type"], "type"),
            _header_cell("СРОК ИСПОЛН.", _W["due"], "due"),
            ft.Container(
                width=_W["status"],
                padding=ft.padding.only(left=6, right=4),
                content=ft.Text("СТАТУС", size=11, weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"], no_wrap=True),
            ),
        ]
        controls.append(ft.Container(width=_W["actions"]))
        header_row.content = ft.Row(controls=controls, spacing=2, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        try:
            header_row.update()
        except Exception:
            pass

    # ── Detail overlay (master-detail) ──────────────────────────
    def _build_inline_multi(available: List[str], initial: List[str], title: str, on_change_cb=None):
        selected = list(initial)
        expanded = {"value": False}
        search_val = {"value": ""}

        badge = ft.Text(f"Выбрано: {len(selected)}", size=11, color=GLASS["text_secondary"])
        summary = ft.Text(
            ", ".join(short_name(x) for x in selected) or "не выбрано",
            size=12, color=GLASS["text"], max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
            tooltip=", ".join(selected),
        )

        search_field_ms = ft.TextField(
            hint_text=f"Поиск {title.lower()}…",
            prefix_icon=ft.icons.SEARCH,
            height=36, dense=True,
            border_radius=10, border_color=GLASS["border"],
            focused_border_color=GLASS["accent"],
            bgcolor=GLASS["surface_alt"], color=GLASS["text"],
            hint_style=ft.TextStyle(color=GLASS["text_muted"], size=12),
            text_style=ft.TextStyle(size=12),
            content_padding=ft.padding.symmetric(horizontal=10, vertical=6),
            visible=False,
        )

        list_col = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=160, visible=False)

        def _rebuild_list():
            q = search_val["value"].lower()
            filtered = [n for n in available if q in n.lower()] if q else list(available)
            filtered = sorted(set(filtered + selected), key=lambda n: (n not in selected, n.lower()))
            list_col.controls.clear()
            for name in filtered:
                def _make_toggle(n):
                    def _toggle(e):
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
                        if on_change_cb:
                            try:
                                on_change_cb(list(selected))
                            except Exception:
                                pass
                    return _toggle
                list_col.controls.append(
                    ft.Checkbox(
                        label=short_name(name),
                        value=(name in selected),
                        active_color=GLASS["accent"],
                        label_style=ft.TextStyle(size=12, color=GLASS["text"]),
                        tooltip=name,
                        on_change=_make_toggle(name),
                        height=30,
                    )
                )
            try:
                list_col.update()
            except Exception:
                pass

        def _on_search_change(e):
            search_val["value"] = e.control.value or ""
            _rebuild_list()

        search_field_ms.on_change = _on_search_change

        list_wrapper = ft.Container(
            content=list_col,
            border=ft.border.all(1, GLASS["border"]),
            border_radius=10,
            padding=ft.padding.all(6),
            bgcolor=GLASS["surface_alt"],
            visible=False,
        )

        def _toggle_expand(e=None):
            expanded["value"] = not expanded["value"]
            search_field_ms.visible = expanded["value"]
            list_wrapper.visible = expanded["value"]
            list_col.visible = expanded["value"]
            summary.visible = not expanded["value"]
            expand_btn.icon = ft.icons.EXPAND_LESS if expanded["value"] else ft.icons.EXPAND_MORE
            try:
                search_field_ms.update()
                list_wrapper.update()
                summary.update()
                expand_btn.update()
            except Exception:
                pass
            if expanded["value"]:
                _rebuild_list()

        def _clear_all(e=None):
            selected.clear()
            badge.value = "Выбрано: 0"
            summary.value = "не выбрано"
            summary.tooltip = None
            try:
                badge.update()
                summary.update()
            except Exception:
                pass
            if on_change_cb:
                try:
                    on_change_cb([])
                except Exception:
                    pass
            _rebuild_list()

        expand_btn = ft.IconButton(icon=ft.icons.EXPAND_MORE, icon_size=18, icon_color=GLASS["text_secondary"], tooltip="Развернуть", on_click=_toggle_expand)

        header = ft.Row(
            controls=[
                ft.Text(title, size=12, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
                ft.Container(width=8),
                badge,
                ft.Container(expand=True),
                ft.TextButton("Очистить", on_click=_clear_all, style=ft.ButtonStyle(color=GLASS["overdue"], padding=ft.padding.symmetric(horizontal=6))),
                expand_btn,
            ],
            spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        _rebuild_list()

        container = ft.Container(
            content=ft.Column(controls=[header, summary, search_field_ms, list_wrapper], spacing=6, tight=True),
            bgcolor=GLASS["surface_alt"],
            border=ft.border.all(1, GLASS["border"]),
            border_radius=10,
            padding=ft.padding.all(10),
        )
        container._get_selected = lambda: list(selected)
        return container

    # Detail state
    detail_state: Dict = {
        "control_id": None,
        "is_new": True,
        "executors_picker": None,
        "tasks": [],
        "milestones": [],
        "attachments": [],
        "receive_date": None,
        "due_date": None,
        "end_date": None,
    }

    detail_card = ft.Container(
        width=860,
        height=740,
        bgcolor=GLASS["surface"],
        border=glass_border(True),
        border_radius=14,
        padding=ft.padding.all(16),
        content=ft.Column(controls=[ft.Text("Загрузка…", color=GLASS["text"])], scroll=ft.ScrollMode.AUTO, expand=True),
    )
    detail_overlay = ft.Container(
        visible=False,
        bgcolor=GLASS["overlay_dim"],
        expand=True,
        alignment=ft.alignment.center,
        padding=ft.padding.all(12),
        content=detail_card,
    )

    def _hide_detail(e=None):
        detail_overlay.visible = False
        state["editing"] = False
        try:
            detail_overlay.update()
        except Exception:
            pass

    def _open_detail(ctl: Optional[Control]):
        is_new = ctl is None
        state["editing"] = True
        detail_state["is_new"] = is_new
        detail_state["control_id"] = ctl.id if ctl else str(uuid4())
        detail_state["receive_date"] = (ctl.receive_date if ctl else date.today().isoformat())
        detail_state["due_date"] = (ctl.due_date if ctl else None)
        detail_state["end_date"] = (ctl.end_date if ctl else None)
        detail_state["attachments"] = list(ctl.attachments) if ctl and ctl.attachments else []
        detail_state["tasks"] = []
        detail_state["milestones"] = []

        # Incoming
        incoming_field = _glass_tf("Входящий № ВХСОП *", value=ctl.incoming_number if ctl else "", expand=True)
        # Receive calendar
        def _set_receive(iso):
            detail_state["receive_date"] = iso
        receive_cal = create_russian_date_field(page, detail_state["receive_date"], _set_receive, hint="Дата поступления", width=170)

        # Initiator dropdown + add custom
        init_dd = _glass_dd(
            "Инициатор", 220,
            [ft.dropdown.Option(i) for i in initiators],
            value=ctl.initiator if (ctl and ctl.initiator in initiators) else None,
        )
        new_init_field = _glass_tf("Новый инициатор…", width=200)
        def _add_initiator(e=None):
            name = (new_init_field.value or "").strip()
            if not name:
                return
            add_custom_initiator(settings, name)
            new_inits = get_initiators(settings)
            initiators.clear()
            initiators.extend(new_inits)
            init_dd.options = [ft.dropdown.Option(i) for i in initiators]
            init_dd.value = name
            new_init_field.value = ""
            try:
                init_dd.update()
                new_init_field.update()
            except Exception:
                pass
            try:
                initiator_filter_dd.options = [ft.dropdown.Option("all", "Все инициаторы")] + [ft.dropdown.Option(i) for i in initiators]
                initiator_filter_dd.update()
            except Exception:
                pass
        add_init_btn = ft.Container(
            content=ft.Text("Добавить", size=12, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
            height=36, padding=ft.padding.symmetric(horizontal=12),
            bgcolor=GLASS["surface"], border=ft.border.all(1, GLASS["border"]), border_radius=10,
            ink=True, on_click=_add_initiator, alignment=ft.alignment.center,
        )

        content_field = _glass_tf("Содержание контроля…", value=ctl.content if ctl else "", multiline=True, min_lines=3, max_lines=5, expand=False)
        content_field.width = 820

        exec_container = _build_inline_multi(available_names, list(ctl.executors) if ctl else [], "Исполнители")

        controller_dd = _glass_dd(
            "За кем контроль", 220,
            [ft.dropdown.Option(n, short_name(n)) for n in available_names],
            value=ctl.controller if (ctl and ctl.controller in available_names) else None,
        )

        type_dd = _glass_dd("Тип", 140, [ft.dropdown.Option(ONE_TIME, "Разовый"), ft.dropdown.Option(PERIODIC, "Постоянный")], value=ctl.control_type if ctl else ONE_TIME)
        period_dd = _glass_dd(
            "Периодичность", 180,
            [ft.dropdown.Option(k, l) for k, l, _ in _PERIOD_LABELS],
            value=_period_key(ctl.period_days if ctl else 7),
        )
        period_dd.visible = (ctl.control_type if ctl else ONE_TIME) == PERIODIC

        custom_days_field = _glass_tf("Интервал дней", value=str(ctl.period_days) if ctl else "7", width=120)
        custom_days_field.visible = _period_key(ctl.period_days if ctl else 7) == "custom"

        def _set_due(iso):
            detail_state["due_date"] = iso
            _refresh_cycle_hint()

        def _set_end(iso):
            detail_state["end_date"] = iso
            _refresh_cycle_hint()

        due_cal = create_russian_date_field(page, detail_state["due_date"], _set_due, hint="Следующая дата исполнения", width=200)
        end_cal = create_russian_date_field(page, detail_state["end_date"], _set_end, hint="Конечная дата", width=170)
        end_cal.visible = (ctl.control_type if ctl else ONE_TIME) == PERIODIC
        due_cal.visible = True

        cycle_hint = ft.Text("", size=11, color=GLASS["text_muted"], italic=True)

        def _period_days_val() -> int:
            k = period_dd.value or "weekly"
            if k == "custom":
                try:
                    return max(1, int(custom_days_field.value or "7"))
                except ValueError:
                    return 7
            return _PERIOD_DAYS.get(k, 7)

        def _refresh_cycle_hint():
            try:
                base = parse_date(detail_state["due_date"]) or date.today()
                days = _period_days_val()
                dates = [base + timedelta(days=days*i) for i in range(1,4)]
                cycle_hint.value = "Следующие: " + " · ".join(d.strftime("%d.%m.%Y") for d in dates)
                cycle_hint.update()
            except Exception:
                pass

        def _on_type_change(e):
            is_per = (e.control.value == PERIODIC)
            period_dd.visible = is_per
            end_cal.visible = is_per
            milestones_header.visible = is_per
            milestones_col.visible = is_per
            try:
                period_dd.update()
                end_cal.update()
                milestones_header.update()
                milestones_col.update()
            except Exception:
                pass
            _refresh_cycle_hint()

        def _on_period_change(e):
            custom_days_field.visible = (e.control.value == "custom")
            try:
                custom_days_field.update()
            except Exception:
                pass
            _refresh_cycle_hint()

        type_dd.on_change = _on_type_change
        period_dd.on_change = _on_period_change

        comment_field = _glass_tf("Комментарий…", value=ctl.comment if ctl else "", multiline=True, min_lines=1, max_lines=3)

        # Tasks
        tasks_col = ft.Column(spacing=6)

        def _rebuild_task_cards():
            tasks_col.controls.clear()
            for idx, t_ui in enumerate(detail_state["tasks"]):
                tasks_col.controls.append(_build_single_task_card(t_ui, idx))
            try:
                tasks_col.update()
            except Exception:
                pass

        def _build_single_task_card(t_ui: dict, idx: int) -> ft.Container:
            title_f = t_ui["title_field"]
            # task due calendar
            def _set_task_due(iso):
                t_ui["due_ref"]["value"] = iso

            task_due_cal = create_russian_date_field(page, t_ui["due_ref"]["value"], _set_task_due, hint="Срок", width=160)

            # Assignees inline mini
            ass_selected = t_ui["assignees"]
            ass_badge = ft.Text(f"Отв: {len(ass_selected)}", size=10, color=GLASS["text_secondary"])
            ass_summary = ft.Text(", ".join(short_name(x) for x in ass_selected) or "не выбраны", size=11, color=GLASS["text"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
            ass_search = ft.TextField(hint_text="Поиск…", height=32, dense=True, visible=False, border_radius=10, border_color=GLASS["border"], bgcolor=GLASS["surface_alt"], color=GLASS["text"], text_style=ft.TextStyle(size=11))
            ass_list = ft.Column(spacing=1, scroll=ft.ScrollMode.AUTO, height=120, visible=False)
            ass_expanded = {"value": False}

            def _rebuild_ass_list():
                q = (ass_search.value or "").lower()
                filtered = [n for n in available_names if q in n.lower()] if q else list(available_names)
                filtered = sorted(set(filtered + ass_selected), key=lambda n: (n not in ass_selected, n.lower()))
                ass_list.controls.clear()
                for name in filtered:
                    def _mk(n):
                        def _chg(e):
                            if e.control.value:
                                if n not in t_ui["assignees"]:
                                    t_ui["assignees"].append(n)
                            else:
                                if n in t_ui["assignees"]:
                                    t_ui["assignees"].remove(n)
                            ass_badge.value = f"Отв: {len(t_ui['assignees'])}"
                            ass_summary.value = ", ".join(short_name(x) for x in t_ui["assignees"]) or "не выбраны"
                            try:
                                ass_badge.update()
                                ass_summary.update()
                            except Exception:
                                pass
                        return _chg
                    ass_list.controls.append(
                        ft.Checkbox(label=short_name(name), value=name in t_ui["assignees"], active_color=GLASS["accent"], label_style=ft.TextStyle(size=11, color=GLASS["text"]), tooltip=name, on_change=_mk(name), height=26)
                    )
                try:
                    ass_list.update()
                except Exception:
                    pass

            def _on_ass_search(e):
                _rebuild_ass_list()

            ass_search.on_change = _on_ass_search

            ass_wrapper = ft.Container(content=ass_list, border=ft.border.all(1, GLASS["border"]), border_radius=10, padding=ft.padding.all(6), bgcolor=GLASS["surface_alt"], visible=False)

            def _toggle_ass(e=None):
                ass_expanded["value"] = not ass_expanded["value"]
                ass_search.visible = ass_expanded["value"]
                ass_list.visible = ass_expanded["value"]
                ass_wrapper.visible = ass_expanded["value"]
                ass_summary.visible = not ass_expanded["value"]
                try:
                    ass_search.update()
                    ass_wrapper.update()
                    ass_summary.update()
                    ass_expand_btn.update()
                except Exception:
                    pass
                if ass_expanded["value"]:
                    _rebuild_ass_list()

            ass_expand_btn = ft.IconButton(icon=ft.icons.EXPAND_MORE, icon_size=16, icon_color=GLASS["text_secondary"], on_click=_toggle_ass)
            ass_expand_btn = ft.Container(
                content=ft.Icon(ft.icons.EXPAND_MORE, size=16, color=GLASS["text_secondary"]),
                width=28, height=28, border_radius=8, bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]),
                ink=True, on_click=_toggle_ass, alignment=ft.alignment.center,
            )

            _rebuild_ass_list()

            done_sw = ft.Switch(value=t_ui["is_done"], active_color=GLASS["in_work"], height=26, on_change=lambda e, ui=t_ui: ui.update({"is_done": bool(e.control.value)}))
            done_date_f = ft.Text(_display_date_or_none(t_ui["done_ref"]["value"]), size=11, color=GLASS["text_secondary"], width=90)

            def _set_done_date(iso):
                t_ui["done_ref"]["value"] = iso
                done_date_f.value = _display_date_or_none(iso)
                try:
                    done_date_f.update()
                except Exception:
                    pass

            done_cal = create_russian_date_field(page, t_ui["done_ref"]["value"], _set_done_date, hint="Дата исп.", width=150)

            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(controls=[ft.Icon(ft.icons.LIST_ALT, size=14, color=GLASS["text_muted"]), title_f, ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=16, icon_color=GLASS["overdue"], on_click=lambda e, ui=t_ui: _remove_task(ui))], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Row(controls=[ass_badge, ass_summary, ass_expand_btn], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ass_search,
                        ass_wrapper,
                        ft.Row(
                            controls=[
                                ft.Text("Срок:", size=11, color=GLASS["text_secondary"]),
                                task_due_cal,
                                ft.Container(width=12),
                                done_sw,
                                ft.Text("исполнено", size=11, color=GLASS["text_secondary"]),
                                done_cal,
                            ],
                            spacing=6,
                            tight=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=6,
                    tight=True,
                ),
                bgcolor=GLASS["surface_alt"],
                border=ft.border.all(1, GLASS["border"]),
                border_radius=10,
                padding=ft.padding.all(10),
            )

        def _remove_task(ui):
            if ui in detail_state["tasks"]:
                detail_state["tasks"].remove(ui)
            _rebuild_task_cards()

        def _add_task(e=None):
            new_ui = {
                "title_field": _glass_tf("Пункт (напр. п.1)", expand=True),
                "assignees": [],
                "due_ref": {"value": None},
                "is_done": False,
                "done_ref": {"value": None},
            }
            detail_state["tasks"].append(new_ui)
            _rebuild_task_cards()

        if ctl and ctl.tasks:
            for t in ctl.tasks:
                detail_state["tasks"].append({
                    "title_field": _glass_tf("Пункт", value=t.title, expand=True),
                    "assignees": list(t.assignees),
                    "due_ref": {"value": t.due_date},
                    "is_done": t.is_done,
                    "done_ref": {"value": t.done_date},
                })
        _rebuild_task_cards()

        # Milestones
        milestones_col = ft.Column(spacing=4)

        def _rebuild_milestones():
            milestones_col.controls.clear()
            for m_ui in detail_state["milestones"]:
                milestones_col.controls.append(_build_milestone_card(m_ui))
            try:
                milestones_col.update()
            except Exception:
                pass

        def _build_milestone_card(m_ui: dict) -> ft.Container:
            def _set_m_date(iso):
                m_ui["date_ref"]["value"] = iso

            date_cal = create_russian_date_field(page, m_ui["date_ref"]["value"], _set_m_date, hint="Дата точки", width=150)
            note_f = _glass_tf("Точка (описание)", value=m_ui["note"], expand=True)
            note_f.on_change = lambda e, ui=m_ui: ui.update({"note": e.control.value or ""})
            done_sw = ft.Switch(value=m_ui["is_done"], active_color=GLASS["in_work"], height=26, on_change=lambda e, ui=m_ui: ui.update({"is_done": bool(e.control.value)}))
            return ft.Container(
                content=ft.Row(
                    controls=[
                        date_cal,
                        note_f,
                        done_sw,
                        ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=16, icon_color=GLASS["overdue"], on_click=lambda e, ui=m_ui: _remove_milestone(ui)),
                    ],
                    spacing=6,
                    tight=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=GLASS["surface_alt"],
                border=ft.border.all(1, GLASS["border"]),
                border_radius=10,
                padding=ft.padding.all(8),
            )

        def _remove_milestone(ui):
            if ui in detail_state["milestones"]:
                detail_state["milestones"].remove(ui)
            _rebuild_milestones()

        def _add_milestone(e=None):
            detail_state["milestones"].append({"date_ref": {"value": None}, "note": "", "is_done": False})
            _rebuild_milestones()

        if ctl and ctl.milestones:
            for m in ctl.milestones:
                detail_state["milestones"].append({"date_ref": {"value": m.date}, "note": m.note, "is_done": m.is_done})
        _rebuild_milestones()

        # Attachments
        attach_col = ft.Column(spacing=4)

        def _rebuild_attach():
            attach_col.controls.clear()
            for rel in detail_state["attachments"]:
                filename = rel.split("/")[-1]
                icon = ft.icons.PICTURE_AS_PDF if filename.lower().endswith(".pdf") else ft.icons.IMAGE_OUTLINED if filename.lower().endswith((".png",".jpg",".jpeg")) else ft.icons.DESCRIPTION_OUTLINED
                attach_col.controls.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(icon, size=14, color=GLASS["accent"]),
                                ft.Text(filename, size=11, color=GLASS["text"], expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, tooltip=filename),
                                ft.IconButton(icon=ft.icons.OPEN_IN_NEW, icon_size=14, icon_color=GLASS["accent"], tooltip="Открыть", on_click=lambda e, r=rel: _open_attach(r)),
                                ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=14, icon_color=GLASS["overdue"], tooltip="Удалить", on_click=lambda e, r=rel: _confirm_remove_attach(r)),
                            ],
                            spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=10,
                        padding=ft.padding.all(6),
                    )
                )
            try:
                attach_col.update()
            except Exception:
                pass

        def _open_attach(rel: str):
            import subprocess, sys, os
            path = resolve_attachment(detail_state["control_id"], rel, settings)
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
                print(f"[CONTROLS_TAB] open attach error: {ex}")

        def _confirm_remove_attach(rel: str):
            def _confirm(e=None):
                try:
                    delete_attachment(detail_state["control_id"], rel, settings)
                except Exception:
                    pass
                if rel in detail_state["attachments"]:
                    detail_state["attachments"].remove(rel)
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
                content=ft.Text("Удалить файл вложения?", size=12, color=GLASS["text"]),
                actions=[ft.TextButton("Отмена", on_click=_cancel), ft.ElevatedButton("Удалить", bgcolor=GLASS["overdue"], color="white", on_click=_confirm)],
                shape=ft.RoundedRectangleBorder(radius=14),
            )
            page.open(dlg)

        def _on_attach_picked(e):
            files = getattr(e, "files", None)
            if not files:
                return
            added = []
            for fobj in files:
                try:
                    fpath = fobj.path
                except Exception:
                    continue
                if not fpath:
                    continue
                try:
                    import os
                    sz = os.path.getsize(fpath) / (1024*1024)
                    if sz > ATTACHMENT_WARN_MB:
                        from ui.toast import show_toast
                        show_toast(page, f"Файл > 20 МБ: {fobj.name}", icon=ft.icons.WARNING_AMBER)
                except Exception:
                    pass
                rel = None
                if settings.get("network_enabled"):
                    rel = copy_attachment_to_shared(detail_state["control_id"], fpath, settings)
                if rel is None:
                    rel = copy_attachment_to_local(detail_state["control_id"], fpath)
                if rel and rel not in detail_state["attachments"]:
                    detail_state["attachments"].append(rel)
                    added.append(rel)
            if added:
                _rebuild_attach()
                from ui.toast import show_toast
                show_toast(page, f"Прикреплено: {len(added)}", icon=ft.icons.ATTACH_FILE)

        _ensure_file_picker(page, "_controls_attach_picker", _on_attach_picked)

        def _pick_attach(e=None):
            try:
                page._controls_attach_picker.pick_files(dialog_title="Выбрать сканы задания", allowed_extensions=["pdf","png","jpg","jpeg"], allow_multiple=True)
            except Exception as ex:
                print(f"[CONTROLS_TAB] pick attach error: {ex}")

        _rebuild_attach()

        # Actions save/cancel
        def _save_detail(e=None):
            inc = (incoming_field.value or "").strip()
            if not inc:
                try:
                    incoming_field.error_text = "Введите входящий номер"
                    incoming_field.update()
                except Exception:
                    pass
                return
            if not detail_state["receive_date"]:
                try:
                    receive_cal._field_text.value = "Укажите дату"
                    receive_cal._field_text.color = GLASS["overdue"]
                    receive_cal._field_text.update()
                except Exception:
                    pass
                return
            execs = exec_container._get_selected() if hasattr(exec_container, "_get_selected") else []

            new_tasks = []
            for ui in detail_state["tasks"]:
                title = (ui["title_field"].value or "").strip()
                if not title:
                    continue
                new_tasks.append(ControlTask(id=str(uuid4()), title=title, assignees=list(ui["assignees"]), due_date=ui["due_ref"]["value"], is_done=ui["is_done"], done_date=ui["done_ref"]["value"]))

            new_miles = []
            for ui in detail_state["milestones"]:
                if not ui["date_ref"]["value"] and not ui["note"]:
                    continue
                new_miles.append(ControlMilestone(id=str(uuid4()), date=ui["date_ref"]["value"], note=ui["note"], is_done=ui["is_done"]))

            period_days = _period_days_val() if type_dd.value == PERIODIC else (ctl.period_days if ctl else 7)

            c = ctl if ctl else Control(id=detail_state["control_id"])
            c.incoming_number = inc
            c.receive_date = detail_state["receive_date"]
            c.initiator = init_dd.value or ""
            c.content = content_field.value.strip()
            c.executors = execs
            c.controller = controller_dd.value or ""
            c.control_type = type_dd.value or ONE_TIME
            c.period_days = period_days
            c.end_date = detail_state["end_date"] if c.control_type == PERIODIC else None
            c.due_date = detail_state["due_date"]
            c.comment = comment_field.value.strip()
            c.tasks = new_tasks
            c.milestones = new_miles
            c.attachments = list(detail_state["attachments"])
            c.updated_at = datetime.now().isoformat()
            if not c.receive_date:
                c.receive_date = date.today().isoformat()
            if not c.due_date:
                eff = effective_due_date(c)
                if eff:
                    c.due_date = eff.isoformat()

            if is_new:
                state["controls"].append(c)
            else:
                for idx, x in enumerate(state["controls"]):
                    if x.id == c.id:
                        state["controls"][idx] = c
                        break
            _persist(state["controls"])
            _hide_detail()
            _rebuild_table()
            _refresh_counters()
            from ui.toast import show_toast
            show_toast(page, "Сохранено", icon=ft.icons.SAVE)

        def _delete_detail(e=None):
            if is_new:
                _hide_detail()
                return
            def _confirm(e=None):
                try:
                    archive_control(ctl, ARCHIVE_DELETED)
                    _persist(state["controls"])
                    page.close(dlg)
                    _hide_detail()
                    _rebuild_table()
                    _refresh_counters()
                    from ui.toast import show_toast
                    show_toast(page, f"В архив: {ctl.incoming_number}", icon=ft.icons.ARCHIVE)
                except Exception:
                    traceback.print_exc()
            def _cancel(e=None):
                try:
                    page.close(dlg)
                except Exception:
                    pass
            dlg = ft.AlertDialog(
                modal=True, bgcolor=GLASS["surface_solid"],
                title=ft.Text("Переместить в архив", size=14, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
                content=ft.Text(f"Переместить контроль «{ctl.incoming_number}» в архив?", size=12, color=GLASS["text"]),
                actions=[ft.TextButton("Отмена", on_click=_cancel), ft.ElevatedButton("В архив", bgcolor=GLASS["accent"], color="white", on_click=_confirm)],
                shape=ft.RoundedRectangleBorder(radius=14),
            )
            page.open(dlg)

        tasks_header = ft.Row(
            controls=[
                ft.Icon(ft.icons.FORMAT_LIST_BULLETED, size=16, color=GLASS["text"]),
                ft.Text("Пункты задания", size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Text("+ Добавить пункт", size=12, color=GLASS["accent"]),
                    height=30, padding=ft.padding.symmetric(horizontal=10),
                    bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=8,
                    ink=True, on_click=_add_task, alignment=ft.alignment.center,
                ),
            ],
            spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        milestones_header = ft.Row(
            controls=[
                ft.Icon(ft.icons.TIMELINE, size=15, color=GLASS["text"]),
                ft.Text("Промежуточные точки", size=12, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Text("+ Добавить точку", size=11, color=GLASS["accent"]),
                    height=28, padding=ft.padding.symmetric(horizontal=8),
                    bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=8,
                    ink=True, on_click=_add_milestone, alignment=ft.alignment.center,
                ),
            ],
            spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            visible=(ctl.control_type if ctl else ONE_TIME) == PERIODIC,
        )

        attach_header = ft.Row(
            controls=[
                ft.Icon(ft.icons.ATTACH_FILE, size=15, color=GLASS["text"]),
                ft.Text("Скан задания", size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Row(controls=[ft.Icon(ft.icons.ATTACH_FILE, size=14, color=GLASS["text"]), ft.Text("Прикрепить файл", size=12, color=GLASS["text"])], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    height=30, padding=ft.padding.symmetric(horizontal=10),
                    bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=8,
                    ink=True, on_click=_pick_attach, alignment=ft.alignment.center,
                ),
            ],
            spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        detail_content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.icons.EDIT_DOCUMENT if not is_new else ft.icons.ADD_CIRCLE_OUTLINE, size=20, color=GLASS["text"]),
                        ft.Text("Карточка контроля" if not is_new else "Новый контроль", size=17, weight=ft.FontWeight.BOLD, color=GLASS["text"], expand=True),
                        ft.IconButton(icon=ft.icons.CLOSE, icon_color=GLASS["text_secondary"], icon_size=18, on_click=_hide_detail),
                    ],
                    spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=1, bgcolor=GLASS["border"]),
                _labeled("Входящий № *", ft.Row(controls=[incoming_field, receive_cal], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)),
                ft.Row(controls=[_labeled("Инициатор", init_dd), _labeled("Новый инициатор", ft.Row(controls=[new_init_field, add_init_btn], spacing=6, tight=True))], spacing=12, tight=True),
                _labeled("Содержание", content_field),
                exec_container,
                ft.Row(controls=[_labeled("За кем контроль", controller_dd), _labeled("Тип", type_dd), _labeled("Периодичность", ft.Row(controls=[period_dd, custom_days_field], spacing=6, tight=True)),], spacing=8, tight=True),
                ft.Row(controls=[_labeled("Следующая дата исполнения", due_cal), _labeled("Конечная дата", end_cal)], spacing=12, tight=True),
                cycle_hint,
                _labeled("Комментарий", comment_field),
                ft.Container(height=6),
                tasks_header,
                tasks_col,
                ft.Container(height=6),
                milestones_header,
                milestones_col,
                ft.Container(height=6),
                attach_header,
                attach_col,
                ft.Container(height=16),
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Text("Удалить", color="white", size=13, weight=ft.FontWeight.BOLD),
                            visible=not is_new,
                            height=40, padding=ft.padding.symmetric(horizontal=16),
                            bgcolor=GLASS["overdue"], border_radius=10, ink=True, on_click=_delete_detail, alignment=ft.alignment.center,
                        ) if not is_new else ft.Container(),
                        ft.Container(expand=True),
                        ft.Container(
                            content=ft.Text("Отмена", size=13, color=GLASS["text_secondary"]),
                            height=40, padding=ft.padding.symmetric(horizontal=16),
                            bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=10,
                            ink=True, on_click=_hide_detail, alignment=ft.alignment.center,
                        ),
                        ft.Container(
                            content=ft.Row(controls=[ft.Icon(ft.icons.SAVE, size=16, color="white"), ft.Text("Сохранить", size=13, weight=ft.FontWeight.BOLD, color="white")], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            height=40, padding=ft.padding.symmetric(horizontal=18),
                            bgcolor=GLASS["accent"], border_radius=10, ink=True, on_click=_save_detail, alignment=ft.alignment.center,
                        ),
                    ],
                    spacing=10, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=10,
            tight=True,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        detail_card.content = detail_content
        detail_card.width = 860
        detail_card.height = 740
        detail_overlay.visible = True
        try:
            detail_overlay.update()
        except Exception:
            try:
                page.update()
            except Exception:
                pass
        _refresh_cycle_hint()

    # ── Row actions ───────────────────────────────────────────
    def _complete(ctl: Control):
        try:
            _do_complete(ctl)
        except Exception:
            traceback.print_exc()

    def _do_complete(ctl: Control):
        today = date.today()
        if ctl.control_type == PERIODIC:
            base = parse_date(ctl.due_date) or today
            new_due = base + timedelta(days=ctl.period_days)
            end = parse_date(ctl.end_date)
            if end is not None and new_due > end:
                ctl.done = True
                ctl.done_date = today.isoformat()
                archive_control(ctl, ARCHIVE_DONE)
                ctl.updated_at = datetime.now().isoformat()
                _persist(state["controls"])
                from ui.toast import show_toast
                show_toast(page, "Постоянный контроль завершён (конечная дата)", icon=ft.icons.CHECK_CIRCLE)
            else:
                ctl.due_date = new_due.isoformat()
                ctl.done_date = today.isoformat()
                for t in ctl.tasks:
                    t.is_done = False
                    t.done_date = None
                for m in ctl.milestones:
                    m.is_done = False
                ctl.updated_at = datetime.now().isoformat()
                _persist(state["controls"])
                from ui.toast import show_toast
                show_toast(page, f"Срок продлён до {_display_date(ctl.due_date)}", icon=ft.icons.UPDATE)
        else:
            ctl.done = True
            ctl.done_date = today.isoformat()
            ctl.updated_at = datetime.now().isoformat()
            archive_control(ctl, ARCHIVE_DONE)
            _persist(state["controls"])
            from ui.toast import show_toast
            show_toast(page, "Контроль исполнен и перемещён в архив", icon=ft.icons.CHECK_CIRCLE)
        _rebuild_table()
        _refresh_counters()

    def _extend(ctl: Control):
        try:
            _do_extend(ctl)
        except Exception:
            traceback.print_exc()

    def _do_extend(ctl: Control):
        extend_field = _glass_tf("Продлить на (дней)", value=str(ctl.period_days if ctl.control_type == PERIODIC else 7), width=160)
        extend_field.keyboard_type = ft.KeyboardType.NUMBER

        def _confirm(e=None):
            try:
                try:
                    n = max(1, int(extend_field.value))
                except ValueError:
                    n = 7
                base = parse_date(ctl.due_date) or date.today()
                ctl.due_date = (base + timedelta(days=n)).isoformat()
                ctl.updated_at = datetime.now().isoformat()
                _persist(state["controls"])
                page.close(dialog)
                _rebuild_table()
                _refresh_counters()
                from ui.toast import show_toast
                show_toast(page, f"Срок продлён до {_display_date(ctl.due_date)}", icon=ft.icons.UPDATE)
            except Exception:
                traceback.print_exc()

        def _close(e=None):
            try:
                page.close(dialog)
            except Exception:
                pass

        dialog = ft.AlertDialog(
            modal=True, bgcolor=GLASS["surface_solid"],
            title=ft.Text("Продлить срок", size=16, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
            content=ft.Container(content=extend_field, width=220),
            actions=[ft.TextButton("Отмена", on_click=_close), ft.ElevatedButton("Продлить", bgcolor=GLASS["accent"], color="white", on_click=_confirm)],
            shape=ft.RoundedRectangleBorder(radius=14),
        )
        page.open(dialog)

    def _confirm_delete(ctl: Control):
        def _confirm(e=None):
            try:
                archive_control(ctl, ARCHIVE_DELETED)
                _persist(state["controls"])
                page.close(dialog)
                _rebuild_table()
                _refresh_counters()
                from ui.toast import show_toast
                show_toast(page, f"В архив: {ctl.incoming_number}", icon=ft.icons.ARCHIVE)
            except Exception:
                traceback.print_exc()

        def _close(e=None):
            try:
                page.close(dialog)
            except Exception:
                pass

        dialog = ft.AlertDialog(
            modal=True, bgcolor=GLASS["surface_solid"],
            title=ft.Text("Переместить в архив", size=16, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
            content=ft.Text(f"Переместить контроль «{ctl.incoming_number}» в архив?", size=13, color=GLASS["text"]),
            actions=[ft.TextButton("Отмена", on_click=_close), ft.ElevatedButton("В архив", icon=ft.icons.ARCHIVE, bgcolor=GLASS["accent"], color="white", on_click=_confirm)],
            shape=ft.RoundedRectangleBorder(radius=14),
        )
        page.open(dialog)

    def _restore(ctl: Control):
        try:
            restore_control(ctl)
            _persist(state["controls"])
            _rebuild_table()
            _refresh_counters()
            from ui.toast import show_toast
            show_toast(page, "Контроль восстановлен", icon=ft.icons.RESTORE)
        except Exception:
            traceback.print_exc()

    def _delete_forever(ctl: Control):
        def _confirm(e=None):
            try:
                delete_all_attachments(ctl.id, settings)
                state["controls"] = [c for c in state["controls"] if c.id != ctl.id]
                _persist(state["controls"])
                page.close(dialog)
                _rebuild_table()
                _refresh_counters()
                from ui.toast import show_toast
                show_toast(page, "Удалён навсегда", icon=ft.icons.DELETE_FOREVER)
            except Exception:
                traceback.print_exc()

        def _close(e=None):
            try:
                page.close(dialog)
            except Exception:
                pass

        dialog = ft.AlertDialog(
            modal=True, bgcolor=GLASS["surface_solid"],
            title=ft.Text("Удалить навсегда", size=16, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
            content=ft.Text(f"Удалить «{ctl.incoming_number}» безвозвратно? Вложения также будут удалены.", size=13, color=GLASS["text"]),
            actions=[ft.TextButton("Отмена", on_click=_close), ft.ElevatedButton("Удалить навсегда", icon=ft.icons.DELETE_FOREVER, bgcolor=GLASS["overdue"], color="white", on_click=_confirm)],
            shape=ft.RoundedRectangleBorder(radius=14),
        )
        page.open(dialog)

    # ── Export / Import ───────────────────────────────────────
    export_mode_dd = _glass_dd(
        "Режим", 170,
        [ft.dropdown.Option("table", "Как в таблице"), ft.dropdown.Option("full", "Полный (round-trip)")],
        value="table",
    )

    def _on_export_picked(e: ft.FilePickerResultEvent):
        if not getattr(e, "path", None):
            return
        try:
            mode = (export_mode_dd.value or "table") == "full"
            ControlsExcelExporter().export(_visible_base(), e.path, soon_days, full=mode)
            from ui.toast import show_export_toast
            show_export_toast(page, "Контроли Excel")
        except Exception as ex:
            print(f"[CONTROLS_TAB] Export error: {ex}")
            from ui.toast import show_error_toast
            show_error_toast(page, f"Ошибка экспорта: {ex}")

    def _on_import_picked(e: ft.FilePickerResultEvent):
        path = None
        if getattr(e, "path", None):
            path = e.path
        elif getattr(e, "files", None):
            try:
                path = e.files[0].path
            except Exception:
                path = None
        if not path:
            return
        _preview_import(path)

    _ensure_file_picker(page, "_controls_file_picker", _on_export_picked)
    _ensure_file_picker(page, "_controls_import_picker", _on_import_picked)

    def _export(e=None):
        try:
            page._controls_file_picker.save_file(dialog_title="Сохранить контроли в Excel", file_name=f"controls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", allowed_extensions=["xlsx"])
        except Exception as ex:
            print(f"[CONTROLS_TAB] export trigger error: {ex}")

    def _import(e=None):
        try:
            page._controls_import_picker.pick_files(dialog_title="Выбрать файл Excel для импорта", allowed_extensions=["xlsx"], allow_multiple=False)
        except Exception as ex:
            print(f"[CONTROLS_TAB] import trigger error: {ex}")

    def _preview_import(path: str):
        from ui.toast import show_error_toast
        parsed, stats = import_from_excel(path, state["controls"])
        if not parsed and stats["errors"] == 0:
            show_error_toast(page, "Не найдено ни одного контроля в файле")
            return
        preview_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=300)
        for c in parsed[:20]:
            preview_list.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Text(c.incoming_number or "—", size=11, color=GLASS["text_secondary"], width=90, no_wrap=True),
                            ft.Text(c.content or "—", size=11, color=GLASS["text"], expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, tooltip=c.content),
                            ft.Text(_type_label(c), size=10, color=GLASS["text_secondary"], width=80, no_wrap=True),
                        ],
                        spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=8,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                )
            )
        if len(parsed) > 20:
            preview_list.controls.append(ft.Text(f"… и ещё {len(parsed)-20}", size=10, color=GLASS["text_muted"]))
        summary = ft.Text(f"Найдено: {len(parsed)+stats['skipped']} · Импортируемо: {len(parsed)} · Пропущено: {stats['skipped']} · Ошибок: {stats['errors']} · Формат: {'полный' if stats['full_format'] else 'таблица'}", size=11, color=GLASS["text_secondary"])

        def _confirm(e=None):
            try:
                for c in parsed:
                    state["controls"].append(c)
                _persist(state["controls"])
                page.close(dialog)
                _rebuild_table()
                _refresh_counters()
                from ui.toast import show_toast
                show_toast(page, f"Импортировано: {len(parsed)}", icon=ft.icons.CLOUD_DOWNLOAD)
            except Exception:
                traceback.print_exc()

        def _close(e=None):
            try:
                page.close(dialog)
            except Exception:
                pass

        dialog = ft.AlertDialog(
            modal=True, bgcolor=GLASS["surface_solid"],
            title=ft.Row(
                controls=[ft.Icon(ft.icons.UPLOAD_FILE, size=20, color=GLASS["text"]), ft.Text("Импорт из Excel — предпросмотр", size=15, weight=ft.FontWeight.BOLD, color=GLASS["text"])],
                spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Container(width=560, content=ft.Column(controls=[summary, preview_list], spacing=8, tight=True)),
            actions=[ft.TextButton("Отмена", on_click=_close), ft.ElevatedButton("Импортировать", icon=ft.icons.CLOUD_DOWNLOAD, bgcolor=GLASS["accent"], color="white", on_click=_confirm)],
            shape=ft.RoundedRectangleBorder(radius=14),
        )
        page.open(dialog)

    # ── Settings ──────────────────────────────────────────────
    def _open_settings(e=None):
        from .controls_settings_modal import create_controls_settings_modal
        def on_apply(new_settings):
            nonlocal settings, soon_days, initiators, network_user, network_role
            settings.clear()
            settings.update(new_settings)
            save_settings(new_settings)
            soon_days = int(new_settings.get("soon_days", 3) or 3)
            initiators.clear()
            initiators.extend(get_initiators(settings))
            network_user = new_settings.get("network_user", "") or ""
            network_role = new_settings.get("network_role", "admin")
            try:
                initiator_filter_dd.options = [ft.dropdown.Option("all", "Все инициаторы")] + [ft.dropdown.Option(i) for i in initiators]
                initiator_filter_dd.update()
            except Exception:
                pass
            _update_sync_ui()
            _load_initial()
            _rebuild_table()
            _refresh_counters()
        dialog = create_controls_settings_modal(page, settings, on_apply)
        # restyle dialog to glass if needed
        try:
            dialog.bgcolor = GLASS["surface_solid"]
            dialog.shape = ft.RoundedRectangleBorder(radius=14)
        except Exception:
            pass
        page.open(dialog)

    def _add_control(e=None):
        _open_detail(None)

    # ── Toolbar (Glass Dark) ──────────────────────────────────
    # Buttons
    def _accent_btn(text, icon, on_click):
        return ft.Container(
            content=ft.Row(controls=[ft.Icon(icon, size=18, color="white"), ft.Text(text, size=13, weight=ft.FontWeight.BOLD, color="white", no_wrap=True)], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
            height=40, padding=ft.padding.symmetric(horizontal=16),
            bgcolor=GLASS["accent"], border_radius=10, ink=True, on_click=on_click, alignment=ft.alignment.center,
            tooltip=text,
        )

    def _ghost_btn(text, icon, on_click):
        return ft.Container(
            content=ft.Row(controls=[ft.Icon(icon, size=16, color=GLASS["text"]), ft.Text(text, size=12, weight=ft.FontWeight.W_600, color=GLASS["text"], no_wrap=True)], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
            height=40, padding=ft.padding.symmetric(horizontal=12),
            bgcolor=GLASS["surface"], border=ft.border.all(1, GLASS["border"]), border_radius=10,
            ink=True, on_click=on_click, alignment=ft.alignment.center, tooltip=text,
        )

    def _green_btn(text, icon, on_click):
        return ft.Container(
            content=ft.Row(controls=[ft.Icon(icon, size=16, color=GLASS["export_green_text"]), ft.Text(text, size=12, weight=ft.FontWeight.BOLD, color=GLASS["export_green_text"], no_wrap=True)], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
            height=40, padding=ft.padding.symmetric(horizontal=12),
            bgcolor=GLASS["export_green"], border_radius=10,
            ink=True, on_click=on_click, alignment=ft.alignment.center, tooltip=text,
        )

    add_btn = _accent_btn("Добавить контроль", ft.icons.ADD, _add_control)
    import_btn = _ghost_btn("Импорт Excel", ft.icons.UPLOAD_FILE, _import)
    export_btn = _green_btn("Экспорт Excel", ft.icons.FILE_DOWNLOAD_OUTLINED, _export)

    settings_btn = ft.Container(
        content=ft.Icon(ft.icons.SETTINGS_OUTLINED, size=20, color=GLASS["text_secondary"]),
        width=40, height=40,
        bgcolor=GLASS["surface"], border=ft.border.all(1, GLASS["border"]), border_radius=10,
        ink=True, on_click=_open_settings, alignment=ft.alignment.center, tooltip="Настройки",
    )

    title_row = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.icons.RULE_FOLDER, size=20, color=GLASS["text"]),
                ft.Text("Контроли", size=20, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
                ft.Container(width=12),
                sync_dot, ft.Container(width=6), sync_label,
                ft.Container(expand=True),
                add_btn, import_btn, export_mode_dd, export_btn, settings_btn,
            ],
            spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        height=56,
        bgcolor=GLASS["surface"],
        border=glass_border(True),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
    )

    # main column
    main_column = ft.Column(
        controls=[
            title_row,
            ft.Container(height=6),
            filter_row1,
            ft.Container(height=6),
            filter_row2,
            ft.Container(height=6),
            chips_with_mode,
            ft.Container(height=8),
            header_row,
            ft.Container(height=4),
            rows_column,
            ft.Container(height=40),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Root stack with overlay
    tab_stack = ft.Stack(
        controls=[
            ft.Container(content=main_column, expand=True, padding=ft.padding.only(left=12, right=12, top=8, bottom=8)),
            detail_overlay,
        ],
        expand=True,
    )

    tab_content = ft.Container(
        bgcolor=GLASS["bg"],
        expand=True,
        content=ft.Column(controls=[tab_stack], spacing=0, expand=True),
    )

    # ── Polling ───────────────────────────────────────────────
    _poll_stop = {"flag": False}

    def _background_loop():
        while not _poll_stop["flag"]:
            time.sleep(20)
            try:
                _poll_network()
            except Exception as e:
                print(f"[CONTROLS_TAB] poll error: {e}")
            time.sleep(40)
            try:
                _poll_notifications()
            except Exception as e:
                print(f"[CONTROLS_TAB] notify error: {e}")

    def _poll_network():
        if not settings.get("network_enabled"):
            return
        try:
            mtime = get_shared_mtime(settings)
        except Exception:
            mtime = None
        if mtime is None or mtime == state["shared_mtime"]:
            return
        shared = read_shared_controls(settings)
        if not shared:
            return
        state["controls"] = shared
        state["shared_mtime"] = mtime
        state["last_sync"] = datetime.now()
        state["network_ok"] = True
        if not state["editing"]:
            try:
                _update_sync_ui()
                _rebuild_table()
                _refresh_counters()
            except Exception:
                pass

    def _poll_notifications():
        base = [c for c in _visible_base() if not c.done]
        overdue = [c for c in base if deadline_status(c, soon_days) == OVERDUE]
        today_n = [c for c in base if deadline_status(c, soon_days) == TODAY]
        soon = [c for c in base if deadline_status(c, soon_days) == SOON]
        if not overdue and not today_n and not soon:
            return
        if len(overdue) > state["last_overdue"]:
            state["last_overdue"] = len(overdue)
            try:
                from ui.toast import show_toast
                parts = [f"Просрочено: {len(overdue)}"]
                if today_n:
                    parts.append(f"Сегодня истекает: {len(today_n)}")
                if soon:
                    parts.append(f"Скоро: {len(soon)}")
                show_toast(page, " · ".join(parts), icon=ft.icons.NOTIFICATIONS_ACTIVE)
            except Exception:
                pass

    def _on_page_resize(e=None):
        try:
            new_w = _layout_widths(page.width)
        except Exception:
            return
        if new_w == _W:
            return
        _W.clear()
        _W.update(new_w)
        _rebuild_table()
        _rebuild_header()

    _prev_resize = getattr(page, "on_resize", None)
    def _combined_resize(e=None):
        _on_page_resize(e)
        if _prev_resize is not None and _prev_resize is not _combined_resize:
            try:
                _prev_resize(e)
            except Exception:
                pass
    try:
        page.on_resize = _combined_resize
    except Exception:
        pass

    _load_initial()
    _rebuild_table()
    _rebuild_header()
    _refresh_counters()

    try:
        t = threading.Thread(target=_background_loop, daemon=True)
        t.start()
    except Exception as e:
        print(f"[CONTROLS_TAB] thread start error: {e}")

    try:
        base = [c for c in _visible_base() if not c.done]
        overdue0 = [c for c in base if deadline_status(c, soon_days) == OVERDUE]
        today0 = [c for c in base if deadline_status(c, soon_days) == TODAY]
        soon0 = [c for c in base if deadline_status(c, soon_days) == SOON]
        if overdue0 or today0 or soon0:
            from ui.toast import show_toast
            parts = []
            if overdue0:
                parts.append(f"Просрочено: {len(overdue0)}")
            if today0:
                parts.append(f"Сегодня истекает: {len(today0)}")
            if soon0:
                parts.append(f"Скоро: {len(soon0)}")
            show_toast(page, " · ".join(parts), icon=ft.icons.NOTIFICATIONS_ACTIVE)
        state["last_overdue"] = len(overdue0)
    except Exception:
        pass

    page._controls_poll_stop = _poll_stop
    print("[CONTROLS_TAB] Glass Dark tab created")
    return tab_content

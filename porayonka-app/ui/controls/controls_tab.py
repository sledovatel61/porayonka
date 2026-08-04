# ui/controls/controls_tab.py
# Вкладка «Контроли» — реворк: фикс багов A-F + inline-выбор без вложенных диалогов
# + master-detail overlay (деталь — не AlertDialog, а Container в Stack)
import threading
import time
import traceback
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict
from uuid import uuid4

import flet as ft

from core.constants import COLORS
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

STATUS_ICONS = {
    OVERDUE: ft.icons.EVENT_BUSY,
    TODAY: ft.icons.NOTIFICATIONS_ACTIVE,
    SOON: ft.icons.HOURGLASS_BOTTOM,
    IN_PROGRESS: ft.icons.HOURGLASS_TOP,
    DONE: ft.icons.CHECK_CIRCLE,
    COMPLETED: ft.icons.CHECK_CIRCLE_OUTLINE,
    NO_DATE: ft.icons.REMOVE_CIRCLE_OUTLINE,
}

_FIXED = {
    "bar": 6, "num": 38, "incoming": 108, "receive": 96, "initiator": 138,
    "controller": 140, "type": 96, "due": 104, "status": 118, "actions": 110,
}
_ROW_HEIGHT = 58
_TAB_HORIZONTAL_PADDING = 40
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

def _iso_from_picker_value(v) -> Optional[str]:
    try:
        if v is None:
            return None
        if hasattr(v, "strftime"):
            return v.strftime("%Y-%m-%d")
        return str(v)
    except Exception:
        return None

def _ensure_date_picker(page: ft.Page, on_change):
    if not hasattr(page, "_controls_date_picker"):
        dp = ft.DatePicker(
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2035, 12, 31),
            on_change=on_change,
        )
        page.overlay.append(dp)
        page._controls_date_picker = dp
        try:
            page.update()
        except Exception:
            pass
    return page._controls_date_picker

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
    print("[CONTROLS_TAB] Initializing reworked tab")
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
    sync_label = ft.Text("Локально", size=11, color=COLORS["text_secondary"])
    sync_dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=COLORS["text_muted"])

    def _layout_widths(width: Optional[float]) -> Dict[str, int]:
        if not width or width <= 0:
            width = 1280
        available = max(400.0, width - _TAB_HORIZONTAL_PADDING)
        fixed_sum = sum(_FIXED.values())
        flex = max(260.0, available - fixed_sum)
        w = dict(_FIXED)
        w["executors"] = int(flex * 0.32)
        w["content"] = int(flex - w["executors"])
        return w
    _W = _layout_widths(page.width)

    # ── DatePicker shared ────────────────────────────────────────
    _date_target = {"setter": None}
    def _on_date_change(e):
        setter = _date_target["setter"]
        if setter is None:
            return
        try:
            iso = _iso_from_picker_value(getattr(e.control, "value", None))
        except Exception:
            iso = None
        if iso:
            try:
                setter(iso)
            except Exception:
                traceback.print_exc()

    _ensure_date_picker(page, _on_date_change)

    def _pick_date(setter):
        _date_target["setter"] = setter
        try:
            page._controls_date_picker.pick_date()
        except Exception:
            print("[CONTROLS_TAB] pick_date failed")

    # ── Filter date display ─────────────────────────────────────
    from_text = ft.Text("С: —", size=11, color=COLORS["text_secondary"], width=90, no_wrap=True)
    to_text = ft.Text("По: —", size=11, color=COLORS["text_secondary"], width=90, no_wrap=True)

    def _set_from_iso(iso):
        state["f_from"] = iso
        from_text.value = f"С: {_display_date(iso)}" if iso else "С: —"
        try:
            from_text.update()
        except Exception:
            pass
        _apply_filters()

    def _set_to_iso(iso):
        state["f_to"] = iso
        to_text.value = f"По: {_display_date(iso)}" if iso else "По: —"
        try:
            to_text.update()
        except Exception:
            pass
        _apply_filters()

    def _clear_from(e=None):
        state["f_from"] = None
        from_text.value = "С: —"
        try:
            from_text.update()
        except Exception:
            pass
        _apply_filters()

    def _clear_to(e=None):
        state["f_to"] = None
        to_text.value = "По: —"
        try:
            to_text.update()
        except Exception:
            pass
        _apply_filters()

    # ── Persistence / sync ──────────────────────────────────────
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
            sync_dot.bgcolor = COLORS["text_muted"]
        else:
            role = "админ" if network_role == "admin" else "пользователь"
            sync_label.value = f"Сеть: {role}"
            sync_dot.bgcolor = COLORS["received"] if state["network_ok"] else "#f87171"
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

    # ── Filtering / sorting ─────────────────────────────────────
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
                if dd is None:
                    return True  # без срока — показывать
                fd = parse_date(state["f_from"])
                if fd and dd < fd:
                    return False
            if state["f_to"]:
                dd = effective_due_date(ctl)
                if dd is None:
                    return True
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

    # ── UI helpers ──────────────────────────────────────────────
    def _cell(text: str, width: int, color=COLORS["text"], size=12, bold=False, center=False, tooltip=None, max_lines=1) -> ft.Container:
        return ft.Container(
            content=ft.Text(text, size=size, color=color,
                            weight=ft.FontWeight.W_600 if bold else None,
                            no_wrap=not center, max_lines=max_lines,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            tooltip=tooltip or (text if len(text) > 20 else None)),
            width=width, padding=ft.padding.only(left=6, right=4),
            alignment=ft.alignment.center if center else ft.alignment.center_left,
        )

    def _action_icon(icon, color, tooltip, handler):
        return ft.IconButton(icon=icon, icon_size=16, icon_color=color, tooltip=tooltip,
                             width=26, height=26, padding=0, on_click=handler)

    # ── Row building ────────────────────────────────────────────
    def _build_row(ctl: Control, num: int) -> ft.Container:
        status = deadline_status(ctl, soon_days)
        color = STATUS_COLORS.get(status, "#94a3b8")
        content = ctl.content or ctl.incoming_number
        content_tooltip = ctl.content or ""
        if ctl.tasks:
            task_txt = "; ".join(t.title for t in ctl.tasks if t.title)
            if task_txt:
                content_tooltip = (content_tooltip + "\n" + task_txt).strip()
        content_controls = [_cell(content, _W["content"] - (22 if ctl.attachments else 0),
                                  tooltip=content_tooltip, max_lines=2)]
        if ctl.attachments:
            content_controls.append(ft.Container(
                content=ft.Row(controls=[
                    ft.Icon(ft.icons.ATTACH_FILE, size=12, color=COLORS["btn_save"]),
                    ft.Text(str(len(ctl.attachments)), size=10, color=COLORS["btn_save"], no_wrap=True),
                ], spacing=2, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                width=22,
            ))
        is_archive = state["mode"] == "archive"
        type_cell = _cell(_type_label(ctl), _W["type"], color=COLORS["text_secondary"])
        if is_archive:
            reason = ctl.archive_reason or ""
            reason_text = _reason_label(reason)
            if ctl.archived_at:
                reason_text = f"{reason_text} · {_display_date(ctl.archived_at)}"
            type_cell = _cell(reason_text, _W["type"], color=COLORS["text_secondary"], tooltip=reason)

        actions = []
        if is_archive:
            actions.append(_action_icon(ft.icons.RESTORE, COLORS["received"], "Восстановить", lambda e, c=ctl: _restore(c)))
            actions.append(_action_icon(ft.icons.DELETE_FOREVER, "#f87171", "Удалить навсегда", lambda e, c=ctl: _delete_forever(c)))
        else:
            actions.append(_action_icon(ft.icons.CHECK_CIRCLE_OUTLINE, COLORS["received"], "Исполнено", lambda e, c=ctl: _complete(c)))
            actions.append(_action_icon(ft.icons.UPDATE_OUTLINED, COLORS["in_progress"], "Продлить срок", lambda e, c=ctl: _extend(c)))
            actions.append(_action_icon(ft.icons.DELETE_OUTLINE, "#f87171", "В архив", lambda e, c=ctl: _confirm_delete(c)))

        eff_due = effective_due_date(ctl)
        due_str = _display_date(eff_due.isoformat() if eff_due else ctl.due_date)

        row_controls = [
            ft.Container(width=_W["bar"], height=34, bgcolor=color, border_radius=2),
            _cell(str(num), _W["num"], center=True, color=COLORS["text_secondary"]),
            _cell(ctl.incoming_number or "—", _W["incoming"], bold=True, tooltip=ctl.incoming_number),
            _cell(_display_date(ctl.receive_date), _W["receive"], color=COLORS["text_secondary"]),
            _cell(short_name(ctl.initiator) if ctl.initiator else "—", _W["initiator"], tooltip=ctl.initiator),
            ft.Row(controls=content_controls, spacing=2, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.START),
            _cell(", ".join(short_name(x) for x in ctl.executors) or "—", _W["executors"], tooltip=", ".join(ctl.executors)),
            _cell(short_name(ctl.controller) if ctl.controller else "—", _W["controller"], tooltip=ctl.controller),
            type_cell,
            _cell(due_str, _W["due"], bold=True),
            ft.Container(
                content=ft.Row(controls=[
                    ft.Icon(STATUS_ICONS.get(status, ft.icons.REMOVE_CIRCLE_OUTLINE), size=12, color=color),
                    ft.Text(STATUS_LABELS.get(status, status), size=10, color=color, weight=ft.FontWeight.W_600, no_wrap=True),
                ], spacing=3, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                width=_W["status"], height=24, border_radius=12,
                padding=ft.padding.symmetric(horizontal=6),
                alignment=ft.alignment.center, bgcolor=f"{color}22",
            ),
        ]
        row_controls.append(ft.Row(controls=actions, spacing=0, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER))
        return ft.Container(
            content=ft.Row(controls=row_controls, spacing=2, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=_ROW_HEIGHT, bgcolor=COLORS["card"],
            border=ft.border.all(1, COLORS["border"]), border_radius=8,
            padding=ft.padding.symmetric(horizontal=4, vertical=4),
            on_click=lambda e, c=ctl: _open_detail(c),
        )

    def _rebuild_table():
        rows_column.controls.clear()
        visible = _filtered()
        if not visible:
            label = "В архиве пусто" if state["mode"] == "archive" else "Контролей не найдено"
            rows_column.controls.append(ft.Container(
                content=ft.Row(controls=[
                    ft.Icon(ft.icons.INBOX, size=18, color=COLORS["text_muted"]),
                    ft.Text(label, size=12, color=COLORS["text_secondary"]),
                ], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                height=48, bgcolor=COLORS["card"],
                border=ft.border.all(1, COLORS["border"]), border_radius=10,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            ))
            try:
                rows_column.update()
            except Exception:
                pass
            return
        for i, ctl in enumerate(visible, 1):
            rows_column.controls.append(_build_row(ctl, i))
        try:
            rows_column.update()
        except Exception:
            pass

    # ── Counters ────────────────────────────────────────────────
    counter_refs: Dict[str, ft.Container] = {}
    def _counts() -> dict:
        res = {"all": 0, OVERDUE: 0, TODAY: 0, SOON: 0, IN_PROGRESS: 0, DONE: 0, COMPLETED: 0}
        for ctl in _visible_base():
            res["all"] += 1
            st = deadline_status(ctl, soon_days)
            res[st] = res.get(st, 0) + 1
        return res

    def _set_status_filter(value: str):
        state["f_status"] = value if state["f_status"] != value else "all"
        _restyle_counters()
        _apply_filters()

    def _restyle_counters():
        for key, btn in counter_refs.items():
            selected = (state["f_status"] == key)
            fg = COLORS["text_light"] if selected else COLORS["text_secondary"]
            btn.bgcolor = COLORS["btn_save"] if selected else "transparent"
            try:
                row = btn.content
                row.controls[1].color = fg
                badge = row.controls[2]
                badge.bgcolor = COLORS["card"]
                badge.content.color = COLORS["text_light"]
            except Exception:
                pass
            try:
                btn.update()
            except Exception:
                pass

    def _refresh_counters():
        counts = _counts()
        for key, btn in counter_refs.items():
            try:
                row = btn.content
                badge = row.controls[2]
                badge.content.value = str(counts.get(key, 0))
            except Exception:
                pass
        _restyle_counters()

    def _mk_counter(key: str, label: str, icon) -> ft.Container:
        counts = _counts()
        badge = ft.Container(
            content=ft.Text(str(counts.get(key, 0)), size=11, color=COLORS["text_light"], weight=ft.FontWeight.W_600, no_wrap=True),
            height=20, padding=ft.padding.symmetric(horizontal=7), border_radius=10,
            alignment=ft.alignment.center, bgcolor=COLORS["card"],
        )
        btn = ft.Container(
            content=ft.Row(controls=[
                ft.Icon(icon, size=13, color=COLORS["text_secondary"]),
                ft.Text(label, size=11, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], no_wrap=True),
                badge,
            ], spacing=5, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=30, padding=ft.padding.symmetric(horizontal=10), border_radius=8,
            alignment=ft.alignment.center, bgcolor="transparent", ink=True,
            on_click=lambda e, v=key: _set_status_filter(v),
        )
        counter_refs[key] = btn
        return btn

    counter_statuses = [
        (OVERDUE, "Просрочено", ft.icons.EVENT_BUSY),
        (TODAY, "Сегодня", ft.icons.NOTIFICATIONS_ACTIVE),
        (SOON, "Скоро", ft.icons.HOURGLASS_BOTTOM),
        (IN_PROGRESS, "В работе", ft.icons.HOURGLASS_TOP),
        (DONE, "Исполнено", ft.icons.CHECK_CIRCLE),
    ]
    counters_row = ft.Container(
        content=ft.Row(controls=[
            _mk_counter("all", "Все", ft.icons.GRID_VIEW),
        ] + [_mk_counter(k, label, icon) for k, label, icon in counter_statuses],
            spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.START, scroll=ft.ScrollMode.HIDDEN),
        height=38, bgcolor=COLORS["primary_light"],
        border=ft.border.all(1, COLORS["border"]), border_radius=10,
        padding=ft.padding.symmetric(horizontal=3, vertical=3),
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
            fg = COLORS["text_light"] if selected else COLORS["text_secondary"]
            btn.bgcolor = COLORS["btn_save"] if selected else "transparent"
            try:
                for ctl in btn.content.controls:
                    if isinstance(ctl, ft.Text):
                        ctl.color = fg
                    elif hasattr(ctl, "color"):
                        try:
                            ctl.color = fg
                        except Exception:
                            pass
                btn.update()
            except Exception:
                pass

    def _mk_mode_btn(mode: str, label: str, icon) -> ft.Container:
        btn = ft.Container(
            content=ft.Row(controls=[
                ft.Icon(icon, size=14, color=COLORS["text_light"] if state["mode"]==mode else COLORS["text_secondary"]),
                ft.Text(label, size=12, weight=ft.FontWeight.W_600, color=COLORS["text_light"] if state["mode"]==mode else COLORS["text_secondary"], no_wrap=True),
            ], spacing=5, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=30, padding=ft.padding.symmetric(horizontal=12), border_radius=8,
            alignment=ft.alignment.center,
            bgcolor=COLORS["btn_save"] if state["mode"]==mode else "transparent",
            ink=True, on_click=lambda e, m=mode: _set_mode(m),
        )
        mode_buttons[mode] = btn
        return btn

    mode_row = ft.Container(
        content=ft.Row(controls=[
            _mk_mode_btn("active", "Активные", ft.icons.PLAYLIST_PLAY),
            _mk_mode_btn("archive", "Архив", ft.icons.ARCHIVE_OUTLINED),
        ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.START),
        height=38, bgcolor=COLORS["primary_light"],
        border=ft.border.all(1, COLORS["border"]), border_radius=10,
        padding=ft.padding.symmetric(horizontal=3, vertical=3),
    )

    # ── Filters ─────────────────────────────────────────────────
    def _mk_dd(hint, width, options, default="all"):
        return ft.Dropdown(
            hint_text=hint,
            width=width, height=38, value=default,
            options=options,
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
            hint_style=ft.TextStyle(color=COLORS["text_muted"], size=11),
            text_style=ft.TextStyle(size=12, color=COLORS["text"]),
            dense=True,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=4),
        )

    search_field = ft.TextField(
        hint_text="Поиск по содержанию, номеру…",
        prefix_icon=ft.icons.SEARCH,
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"], size=11),
        text_style=ft.TextStyle(size=12),
        width=260, height=38,
        dense=True,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
    )
    def _on_search(e=None):
        state["search"] = search_field.value or ""
        _apply_filters()
    search_field.on_change = _on_search

    status_filter_dd = _mk_dd("Статус", 160, [
        ft.dropdown.Option("all", "Все статусы"),
        ft.dropdown.Option(OVERDUE, "Просрочено"),
        ft.dropdown.Option(TODAY, "Сегодня"),
        ft.dropdown.Option(SOON, "Скоро"),
        ft.dropdown.Option(IN_PROGRESS, "В работе"),
        ft.dropdown.Option(DONE, "Исполнено"),
        ft.dropdown.Option(COMPLETED, "Завершён"),
    ])
    type_filter_dd = _mk_dd("Тип", 140, [
        ft.dropdown.Option("all", "Все типы"),
        ft.dropdown.Option(ONE_TIME, "Разовый"),
        ft.dropdown.Option(PERIODIC, "Постоянный"),
    ])
    initiator_filter_dd = _mk_dd("Инициатор", 190,
        [ft.dropdown.Option("all", "Все инициаторы")] + [ft.dropdown.Option(i) for i in initiators])
    executor_filter_dd = _mk_dd("Исполнитель", 190,
        [ft.dropdown.Option("all", "Все исполнители")] + [ft.dropdown.Option(n, short_name(n)) for n in available_names])
    controller_filter_dd = _mk_dd("За кем", 180,
        [ft.dropdown.Option("all", "Все контролеры")] + [ft.dropdown.Option(n, short_name(n)) for n in available_names])

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

    def _reset_filters(e=None):
        search_field.value = ""
        state["search"] = ""
        for dd in (status_filter_dd, type_filter_dd, initiator_filter_dd, executor_filter_dd, controller_filter_dd):
            dd.value = "all"
        state.update(f_status="all", f_type="all", f_initiator="all", f_executor="all", f_controller="all", f_from=None, f_to=None)
        from_text.value = "С: —"
        to_text.value = "По: —"
        _restyle_counters()
        try:
            page.update()
        except Exception:
            pass
        _apply_filters()

    filter_row1 = ft.Container(
        content=ft.Row(controls=[
            search_field, status_filter_dd, type_filter_dd,
            ft.Container(expand=True),
            mode_row,
        ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.START),
        height=46, bgcolor=COLORS["card"],
        border=ft.border.all(1, COLORS["border"]), border_radius=12,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
    )
    filter_row2 = ft.Container(
        content=ft.Row(controls=[
            initiator_filter_dd, executor_filter_dd, controller_filter_dd,
            from_text,
            ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_size=16, icon_color=COLORS["btn_save"], tooltip="С даты",
                          on_click=lambda e: _pick_date(_set_from_iso)),
            ft.IconButton(icon=ft.icons.CLEAR, icon_size=14, icon_color=COLORS["text_muted"], tooltip="Очистить С",
                          on_click=_clear_from),
            to_text,
            ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_size=16, icon_color=COLORS["btn_save"], tooltip="По дату",
                          on_click=lambda e: _pick_date(_set_to_iso)),
            ft.IconButton(icon=ft.icons.CLEAR, icon_size=14, icon_color=COLORS["text_muted"], tooltip="Очистить По",
                          on_click=_clear_to),
            ft.Container(expand=True),
            ft.TextButton("Сброс", on_click=_reset_filters, style=ft.ButtonStyle(color=COLORS["btn_save"])),
        ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.START),
        height=46, bgcolor=COLORS["card"],
        border=ft.border.all(1, COLORS["border"]), border_radius=12,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
    )

    # ── Header (fixed bug C) ────────────────────────────────────
    def _header_cell(text: str, width: int, key: str, center=False) -> ft.Container:
        arrow = "▲" if (state["sort_key"]==key and not state["sort_reverse"]) else ("▼" if (state["sort_key"]==key and state["sort_reverse"]) else "")
        return ft.Container(
            content=ft.Text(f"{text} {arrow}".strip(), size=11, weight=ft.FontWeight.BOLD, color=COLORS["text_secondary"], no_wrap=True,
                            tooltip="Сортировка"),
            width=width, padding=ft.padding.only(left=6, right=4),
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
        height=30, bgcolor=COLORS["primary_light"],
        border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
        border_radius=8, padding=ft.padding.symmetric(horizontal=4, vertical=2),
    )

    def _rebuild_header():
        is_archive = state["mode"] == "archive"
        controls = [
            ft.Container(width=_W["bar"]),
            _header_cell("№", _W["num"], "num", center=True),
            _header_cell("вх. №", _W["incoming"], "incoming"),
            _header_cell("Дата пост.", _W["receive"], "receive"),
            _header_cell("Инициатор", _W["initiator"], "initiator"),
            ft.Container(width=_W["content"], padding=ft.padding.only(left=6, right=4),
                         content=ft.Text("Содержание", size=11, weight=ft.FontWeight.BOLD, color=COLORS["text_secondary"], no_wrap=True)),
            ft.Container(width=_W["executors"], padding=ft.padding.only(left=6, right=4),
                         content=ft.Text("Исполнители", size=11, weight=ft.FontWeight.BOLD, color=COLORS["text_secondary"], no_wrap=True)),
            ft.Container(width=_W["controller"], padding=ft.padding.only(left=6, right=4),
                         content=ft.Text("За кем", size=11, weight=ft.FontWeight.BOLD, color=COLORS["text_secondary"], no_wrap=True)),
            _header_cell("Причина" if is_archive else "Тип", _W["type"], "type"),
            _header_cell("Срок исполн.", _W["due"], "due"),
            ft.Container(width=_W["status"], padding=ft.padding.only(left=6, right=4),
                         content=ft.Text("Статус", size=11, weight=ft.FontWeight.BOLD, color=COLORS["text_secondary"], no_wrap=True)),
        ]
        controls.append(ft.Container(width=_W["actions"]))
        # FIX Bug C: use .content, not .controls
        header_row.content = ft.Row(controls=controls, spacing=2, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        try:
            header_row.update()
        except Exception:
            pass

    # ── Detail overlay (master-detail) ──────────────────────────
    # Inline multi-select widget factory
    def _build_inline_multi(available: List[str], initial: List[str], title: str, on_change_cb=None):
        selected = list(initial)
        expanded = {"value": False}
        search_val = {"value": ""}

        badge = ft.Text(f"Выбрано: {len(selected)}", size=11, color=COLORS["text_secondary"])
        summary = ft.Text(", ".join(short_name(x) for x in selected) or "не выбрано",
                          size=11, color=COLORS["text"], max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
                          tooltip=", ".join(selected))

        search_field_ms = ft.TextField(
            hint_text=f"Поиск {title.lower()}…",
            prefix_icon=ft.icons.SEARCH,
            height=34, dense=True,
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
            hint_style=ft.TextStyle(color=COLORS["text_muted"], size=11),
            text_style=ft.TextStyle(size=11),
            content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
            visible=False,
        )

        list_col = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=160, visible=False)

        def _rebuild_list():
            q = search_val["value"].lower()
            filtered = [n for n in available if q in n.lower()] if q else list(available)
            # selected first
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
                        # re-sort after change to keep selected on top (optional)
                        # _rebuild_list()
                    return _toggle
                list_col.controls.append(
                    ft.Checkbox(
                        label=short_name(name),
                        value=(name in selected),
                        active_color=COLORS["btn_save"],
                        label_style=ft.TextStyle(size=11, color=COLORS["text"]),
                        tooltip=name,
                        on_change=_make_toggle(name),
                        height=28,
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

        def _toggle_expand(e=None):
            expanded["value"] = not expanded["value"]
            search_field_ms.visible = expanded["value"]
            list_col.visible = expanded["value"]
            summary.visible = not expanded["value"]
            expand_btn.icon = ft.icons.EXPAND_LESS if expanded["value"] else ft.icons.EXPAND_MORE
            try:
                search_field_ms.update()
                list_col.update()
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

        expand_btn = ft.IconButton(icon=ft.icons.EXPAND_MORE, icon_size=18, icon_color=COLORS["text_secondary"],
                                   tooltip="Развернуть список", on_click=_toggle_expand)

        header = ft.Row(controls=[
            ft.Text(title, size=12, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ft.Container(width=8),
            badge,
            ft.Container(expand=True),
            ft.TextButton("Очистить", on_click=_clear_all, style=ft.ButtonStyle(color="#f87171", padding=ft.padding.symmetric(horizontal=6))),
            expand_btn,
        ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        # initial build of list (hidden)
        _rebuild_list()

        container = ft.Container(
            content=ft.Column(controls=[
                header,
                summary,
                search_field_ms,
                ft.Container(content=list_col, border=ft.border.all(1, COLORS["border"]), border_radius=8,
                             padding=ft.padding.all(4), bgcolor=COLORS["card"], visible=False) if False else list_col,
            ], spacing=4, tight=True),
            bgcolor=COLORS["card"],
            border=ft.border.all(1, COLORS["border"]),
            border_radius=8,
            padding=ft.padding.all(8),
        )
        # fix: list_col already has border container? We'll wrap properly
        # override: put list inside bordered container when expanded
        list_wrapper = ft.Container(
            content=list_col,
            border=ft.border.all(1, COLORS["border"]),
            border_radius=8,
            padding=ft.padding.all(4),
            bgcolor=COLORS["primary_light"],
            visible=False,
        )
        # we need to keep reference to wrapper for visibility toggle
        # adjust _toggle_expand to control wrapper, not list directly
        # Re-define toggle with wrapper reference
        def _toggle_expand2(e=None):
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
        expand_btn.on_click = _toggle_expand2

        container.content = ft.Column(controls=[
            header,
            summary,
            search_field_ms,
            list_wrapper,
        ], spacing=4, tight=True)

        # expose selected list via closure attribute
        container._get_selected = lambda: list(selected)
        container._set_selected = lambda new_list: (selected.clear(), selected.extend(new_list), _rebuild_list(), setattr(badge, 'value', f"Выбрано: {len(selected)}"), setattr(summary, 'value', ", ".join(short_name(x) for x in selected) or "не выбрано"))
        return container

    # Detail overlay containers
    detail_state: Dict = {
        "control_id": None,
        "is_new": True,
        "executors_picker": None,
        "tasks": [],  # list of dicts
        "milestones": [],
        "attachments": [],
        "receive_date": None,
        "due_date": None,
        "end_date": None,
    }

    # We'll build detail UI dynamically in _open_detail
    detail_card = ft.Container(
        width=820,
        height=720,
        bgcolor=COLORS["primary_light"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=12,
        padding=ft.padding.all(14),
        content=ft.Column(controls=[ft.Text("Загрузка…")], scroll=ft.ScrollMode.AUTO, expand=True),
    )
    detail_overlay = ft.Container(
        visible=False,
        bgcolor="#000000AA",
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

        # Fields
        incoming_field = ft.TextField(
            value=ctl.incoming_number if ctl else "",
            hint_text="Входящий № ВХСОП *",
            label_style=ft.TextStyle(color=COLORS["text_secondary"]),
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
            hint_style=ft.TextStyle(color=COLORS["text_muted"]),
            dense=True, expand=True,
        )
        receive_field = ft.TextField(
            value=_display_date_or_none(detail_state["receive_date"]),
            hint_text="Дата поступления",
            read_only=True, width=140, dense=True,
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
        )
        def _set_receive(iso):
            detail_state["receive_date"] = iso
            receive_field.value = _display_date_or_none(iso)
            try:
                receive_field.update()
            except Exception:
                pass
        receive_btn = ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_color=COLORS["btn_save"],
                                    on_click=lambda e: _pick_date(_set_receive))

        # Initiator dropdown + add custom
        init_dd = ft.Dropdown(
            hint_text="Инициатор",
            value=ctl.initiator if (ctl and ctl.initiator in initiators) else None,
            options=[ft.dropdown.Option(i) for i in initiators],
            width=220, height=38,
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
            hint_style=ft.TextStyle(color=COLORS["text_muted"], size=11),
            dense=True, content_padding=ft.padding.symmetric(horizontal=10, vertical=4),
        )
        new_init_field = ft.TextField(
            hint_text="Новый инициатор…",
            width=200, height=36, dense=True,
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
            hint_style=ft.TextStyle(color=COLORS["text_muted"], size=11),
        )
        def _add_initiator(e=None):
            name = (new_init_field.value or "").strip()
            if not name:
                return
            add_custom_initiator(settings, name)
            # refresh initiators list
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
            # also update filter dd
            try:
                initiator_filter_dd.options = [ft.dropdown.Option("all", "Все инициаторы")] + [ft.dropdown.Option(i) for i in initiators]
                initiator_filter_dd.update()
            except Exception:
                pass
        add_init_btn = ft.ElevatedButton("Добавить", height=36, bgcolor=COLORS["primary_light"], color=COLORS["btn_save"],
                                         on_click=_add_initiator)

        content_field = ft.TextField(
            value=ctl.content if ctl else "",
            hint_text="Содержание контроля…",
            multiline=True, min_lines=2, max_lines=4,
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
            hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        )

        # Executors inline picker
        exec_container = _build_inline_multi(available_names, list(ctl.executors) if ctl else [], "Исполнители")

        controller_dd = ft.Dropdown(
            hint_text="За кем контроль",
            value=ctl.controller if (ctl and ctl.controller in available_names) else None,
            options=[ft.dropdown.Option(n, short_name(n)) for n in available_names],
            width=200, height=38,
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
            hint_style=ft.TextStyle(color=COLORS["text_muted"], size=11),
            dense=True,
        )

        type_dd = ft.Dropdown(
            hint_text="Тип",
            value=ctl.control_type if ctl else ONE_TIME,
            options=[ft.dropdown.Option(ONE_TIME, "Разовый"), ft.dropdown.Option(PERIODIC, "Постоянный")],
            width=140, height=38,
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
            dense=True,
        )
        period_dd = ft.Dropdown(
            hint_text="Периодичность",
            value=_period_key(ctl.period_days if ctl else 7),
            options=[ft.dropdown.Option(k, l) for k, l, _ in _PERIOD_LABELS],
            width=170, height=38,
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
            dense=True,
            visible=(ctl.control_type if ctl else ONE_TIME) == PERIODIC,
        )
        custom_days_field = ft.TextField(
            value=str(ctl.period_days) if ctl else "7",
            hint_text="Интервал дней",
            width=110, height=38, dense=True,
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
            visible=_period_key(ctl.period_days if ctl else 7) == "custom",
        )
        due_field = ft.TextField(
            value=_display_date_or_none(detail_state["due_date"]),
            hint_text="Следующая дата исполнения",
            read_only=True, width=160, dense=True,
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
        )
        def _set_due(iso):
            detail_state["due_date"] = iso
            due_field.value = _display_date_or_none(iso)
            try:
                due_field.update()
            except Exception:
                pass
            _refresh_cycle_hint()
        due_btn = ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_color=COLORS["btn_save"],
                                on_click=lambda e: _pick_date(_set_due))

        end_field = ft.TextField(
            value=_display_date_or_none(detail_state["end_date"]),
            hint_text="Конечная дата",
            read_only=True, width=140, dense=True,
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
            visible=(ctl.control_type if ctl else ONE_TIME) == PERIODIC,
        )
        def _set_end(iso):
            detail_state["end_date"] = iso
            end_field.value = _display_date_or_none(iso)
            try:
                end_field.update()
            except Exception:
                pass
            _refresh_cycle_hint()
        end_btn = ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_color=COLORS["btn_save"],
                                visible=end_field.visible,
                                on_click=lambda e: _pick_date(_set_end))

        cycle_hint = ft.Text("", size=10, color=COLORS["text_muted"], italic=True)

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
            end_field.visible = is_per
            end_btn.visible = is_per
            milestones_header.visible = is_per
            milestones_col.visible = is_per
            try:
                period_dd.update()
                end_field.update()
                end_btn.update()
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

        comment_field = ft.TextField(
            value=ctl.comment if ctl else "",
            hint_text="Комментарий…",
            multiline=True, min_lines=1, max_lines=3,
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
            hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        )

        # ── Tasks ────────────────────────────────────────────
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
            due_f = ft.TextField(
                value=_display_date_or_none(t_ui["due_ref"]["value"]),
                read_only=True, width=110, dense=True, height=34,
                border_radius=8, border_color=COLORS["border"],
                bgcolor=COLORS["card"], color=COLORS["text"],
            )
            def _set_task_due(iso, ui=t_ui, field=due_f):
                ui["due_ref"]["value"] = iso
                field.value = _display_date_or_none(iso)
                try:
                    field.update()
                except Exception:
                    pass

            # Assignees inline small picker
            # Build mini multi-select for this task
            ass_selected = t_ui["assignees"]
            ass_badge = ft.Text(f"Отв: {len(ass_selected)}", size=10, color=COLORS["text_secondary"])
            ass_summary = ft.Text(", ".join(short_name(x) for x in ass_selected) or "не выбраны",
                                   size=10, color=COLORS["text"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
            ass_search = ft.TextField(hint_text="Поиск…", height=30, dense=True, visible=False,
                                      border_radius=6, border_color=COLORS["border"],
                                      bgcolor=COLORS["card"], color=COLORS["text"], text_style=ft.TextStyle(size=10))
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
                        ft.Checkbox(label=short_name(name), value=name in t_ui["assignees"],
                                    active_color=COLORS["btn_save"], label_style=ft.TextStyle(size=10, color=COLORS["text"]),
                                    tooltip=name, on_change=_mk(name), height=24)
                    )
                try:
                    ass_list.update()
                except Exception:
                    pass

            def _on_ass_search(e):
                _rebuild_ass_list()

            ass_search.on_change = _on_ass_search

            def _toggle_ass(e=None):
                ass_expanded["value"] = not ass_expanded["value"]
                ass_search.visible = ass_expanded["value"]
                ass_list.visible = ass_expanded["value"]
                ass_wrapper.visible = ass_expanded["value"]
                ass_summary.visible = not ass_expanded["value"]
                try:
                    ass_search.update()
                    ass_list.update()
                    ass_wrapper.update()
                    ass_summary.update()
                except Exception:
                    pass
                if ass_expanded["value"]:
                    _rebuild_ass_list()

            ass_expand_btn = ft.IconButton(icon=ft.icons.EXPAND_MORE, icon_size=16, icon_color=COLORS["text_secondary"],
                                           on_click=_toggle_ass)
            ass_clear_btn = ft.TextButton("Очист.", on_click=lambda e: (t_ui["assignees"].clear(), setattr(ass_badge, 'value', "Отв: 0"), setattr(ass_summary, 'value', "не выбраны"), ass_badge.update() if hasattr(ass_badge, 'update') else None, ass_summary.update() if hasattr(ass_summary, 'update') else None, _rebuild_ass_list()))

            ass_wrapper = ft.Container(content=ass_list, border=ft.border.all(1, COLORS["border"]), border_radius=6,
                                       padding=ft.padding.all(4), bgcolor=COLORS["primary_light"], visible=False)

            _rebuild_ass_list()

            done_sw = ft.Switch(value=t_ui["is_done"], active_color=COLORS["received"], height=26,
                                on_change=lambda e, ui=t_ui: ui.update({"is_done": bool(e.control.value)}))
            done_date_f = ft.Text(_display_date_or_none(t_ui["done_ref"]["value"]), size=10, color=COLORS["text_secondary"], width=80)
            def _set_done_date(iso, ui=t_ui, txt=done_date_f):
                ui["done_ref"]["value"] = iso
                txt.value = _display_date_or_none(iso)
                try:
                    txt.update()
                except Exception:
                    pass

            return ft.Container(
                content=ft.Column(controls=[
                    ft.Row(controls=[
                        ft.Icon(ft.icons.LIST_ALT, size=14, color=COLORS["text_muted"]),
                        title_f,
                        ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=16, icon_color="#f87171",
                                      tooltip="Удалить пункт",
                                      on_click=lambda e, ui=t_ui: _remove_task(ui)),
                    ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row(controls=[
                        ass_badge, ass_summary, ass_expand_btn, ass_clear_btn,
                    ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ass_search,
                    ass_wrapper,
                    ft.Row(controls=[
                        ft.Text("Срок:", size=10, color=COLORS["text_secondary"]),
                        due_f,
                        ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_size=14, icon_color=COLORS["btn_save"],
                                      on_click=lambda e, setter=_set_task_due: _pick_date(setter)),
                        ft.Container(width=12),
                        done_sw,
                        ft.Text("исполнено", size=10, color=COLORS["text_secondary"]),
                        done_date_f,
                        ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_size=14, icon_color=COLORS["btn_save"],
                                      on_click=lambda e, setter=_set_done_date: _pick_date(setter)),
                    ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ], spacing=4, tight=True),
                bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]), border_radius=8,
                padding=ft.padding.all(8),
            )

        def _remove_task(ui):
            if ui in detail_state["tasks"]:
                detail_state["tasks"].remove(ui)
            _rebuild_task_cards()

        def _add_task(e=None):
            new_ui = {
                "title_field": ft.TextField(hint_text="Пункт (напр. п.1)", height=36, dense=True,
                                            border_radius=8, border_color=COLORS["border"],
                                            focused_border_color=COLORS["btn_save"],
                                            bgcolor=COLORS["card"], color=COLORS["text"],
                                            expand=True),
                "assignees": [],
                "due_ref": {"value": None},
                "is_done": False,
                "done_ref": {"value": None},
            }
            detail_state["tasks"].append(new_ui)
            _rebuild_task_cards()

        # init tasks from control
        if ctl and ctl.tasks:
            for t in ctl.tasks:
                detail_state["tasks"].append({
                    "title_field": ft.TextField(value=t.title, hint_text="Пункт", height=36, dense=True,
                                                border_radius=8, border_color=COLORS["border"],
                                                focused_border_color=COLORS["btn_save"],
                                                bgcolor=COLORS["card"], color=COLORS["text"], expand=True),
                    "assignees": list(t.assignees),
                    "due_ref": {"value": t.due_date},
                    "is_done": t.is_done,
                    "done_ref": {"value": t.done_date},
                })
        _rebuild_task_cards()

        # ── Milestones ────────────────────────────────────────
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
            date_f = ft.Text(_display_date_or_none(m_ui["date_ref"]["value"]), size=11, color=COLORS["text"], width=90, no_wrap=True)
            def _set_m_date(iso, ui=m_ui, tf=date_f):
                ui["date_ref"]["value"] = iso
                tf.value = _display_date_or_none(iso)
                try:
                    tf.update()
                except Exception:
                    pass
            note_f = ft.TextField(value=m_ui["note"], hint_text="Точка (описание)", height=34, dense=True, expand=True,
                                  border_radius=8, border_color=COLORS["border"],
                                  focused_border_color=COLORS["btn_save"],
                                  bgcolor=COLORS["card"], color=COLORS["text"],
                                  on_change=lambda e, ui=m_ui: ui.update({"note": e.control.value or ""}))
            done_sw = ft.Switch(value=m_ui["is_done"], active_color=COLORS["received"], height=26,
                                on_change=lambda e, ui=m_ui: ui.update({"is_done": bool(e.control.value)}))
            return ft.Container(
                content=ft.Row(controls=[
                    date_f,
                    ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_size=14, icon_color=COLORS["btn_save"],
                                  on_click=lambda e, s=_set_m_date: _pick_date(s)),
                    note_f,
                    done_sw,
                    ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=16, icon_color="#f87171",
                                  on_click=lambda e, ui=m_ui: _remove_milestone(ui)),
                ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]), border_radius=8,
                padding=ft.padding.all(6),
            )

        def _remove_milestone(ui):
            if ui in detail_state["milestones"]:
                detail_state["milestones"].remove(ui)
            _rebuild_milestones()

        def _add_milestone(e=None):
            detail_state["milestones"].append({
                "date_ref": {"value": None},
                "note": "",
                "is_done": False,
            })
            _rebuild_milestones()

        if ctl and ctl.milestones:
            for m in ctl.milestones:
                detail_state["milestones"].append({
                    "date_ref": {"value": m.date},
                    "note": m.note,
                    "is_done": m.is_done,
                })
        _rebuild_milestones()

        # ── Attachments ───────────────────────────────────────
        attach_col = ft.Column(spacing=4)

        def _rebuild_attach():
            attach_col.controls.clear()
            for rel in detail_state["attachments"]:
                filename = rel.split("/")[-1]
                # icon by ext
                icon = ft.icons.PICTURE_AS_PDF if filename.lower().endswith(".pdf") else ft.icons.IMAGE_OUTLINED if filename.lower().endswith((".png",".jpg",".jpeg")) else ft.icons.DESCRIPTION_OUTLINED
                attach_col.controls.append(
                    ft.Container(
                        content=ft.Row(controls=[
                            ft.Icon(icon, size=14, color=COLORS["btn_save"]),
                            ft.Text(filename, size=11, color=COLORS["text"], expand=True, no_wrap=True,
                                    overflow=ft.TextOverflow.ELLIPSIS, tooltip=filename),
                            ft.IconButton(icon=ft.icons.OPEN_IN_NEW, icon_size=14, icon_color=COLORS["btn_save"],
                                          tooltip="Открыть",
                                          on_click=lambda e, r=rel: _open_attach(r)),
                            ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=14, icon_color="#f87171",
                                          tooltip="Удалить",
                                          on_click=lambda e, r=rel: _confirm_remove_attach(r)),
                        ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]), border_radius=8,
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
                modal=True, bgcolor=COLORS["primary_light"],
                title=ft.Text("Удаление вложения", size=14, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                content=ft.Text("Удалить файл вложения?", size=12, color=COLORS["text"]),
                actions=[
                    ft.TextButton("Отмена", on_click=_cancel),
                    ft.ElevatedButton("Удалить", bgcolor="#dc2626", color="white", on_click=_confirm),
                ],
                shape=ft.RoundedRectangleBorder(radius=10),
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

        # ensure attach picker exists and set handler
        _ensure_file_picker(page, "_controls_attach_picker", _on_attach_picked)

        def _pick_attach(e=None):
            try:
                page._controls_attach_picker.pick_files(
                    dialog_title="Выбрать сканы задания",
                    allowed_extensions=["pdf","png","jpg","jpeg"],
                    allow_multiple=True,
                )
            except Exception as ex:
                print(f"[CONTROLS_TAB] pick attach error: {ex}")

        _rebuild_attach()

        # ── Actions (save/cancel/delete) ──────────────────────
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
                    receive_field.error_text = "Укажите дату поступления"
                    receive_field.update()
                except Exception:
                    pass
                return
            # collect executors from inline picker
            execs = exec_container._get_selected() if hasattr(exec_container, "_get_selected") else []

            # gather tasks
            new_tasks = []
            for ui in detail_state["tasks"]:
                title = (ui["title_field"].value or "").strip()
                if not title:
                    continue
                new_tasks.append(ControlTask(
                    id=str(uuid4()), title=title,
                    assignees=list(ui["assignees"]),
                    due_date=ui["due_ref"]["value"],
                    is_done=ui["is_done"],
                    done_date=ui["done_ref"]["value"],
                ))
            # milestones
            new_miles = []
            for ui in detail_state["milestones"]:
                if not ui["date_ref"]["value"] and not ui["note"]:
                    continue
                new_miles.append(ControlMilestone(
                    id=str(uuid4()),
                    date=ui["date_ref"]["value"],
                    note=ui["note"],
                    is_done=ui["is_done"],
                ))

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
            # if due not set, try effective
            if not c.due_date:
                eff = effective_due_date(c)
                if eff:
                    c.due_date = eff.isoformat()

            # persist
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
            _refresh_cycle_hint()

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
                modal=True, bgcolor=COLORS["primary_light"],
                title=ft.Text("Переместить в архив", size=14, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                content=ft.Text(f"Переместить контроль «{ctl.incoming_number}» в архив?", size=12, color=COLORS["text"]),
                actions=[ft.TextButton("Отмена", on_click=_cancel),
                         ft.ElevatedButton("В архив", bgcolor=COLORS["btn_save"], color="white", on_click=_confirm)],
                shape=ft.RoundedRectangleBorder(radius=10),
            )
            page.open(dlg)

        # Sections headers
        tasks_header = ft.Row(controls=[
            ft.Icon(ft.icons.FORMAT_LIST_BULLETED, size=16, color=COLORS["text"]),
            ft.Text("Пункты задания", size=13, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ft.Container(expand=True),
            ft.ElevatedButton("+ Добавить пункт", bgcolor=COLORS["primary_light"], color=COLORS["btn_save"], height=30,
                              on_click=_add_task),
        ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        milestones_header = ft.Row(controls=[
            ft.Icon(ft.icons.TIMELINE, size=15, color=COLORS["text"]),
            ft.Text("Промежуточные точки", size=12, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ft.Container(expand=True),
            ft.ElevatedButton("+ Добавить точку", bgcolor=COLORS["primary_light"], color=COLORS["btn_save"], height=28,
                              on_click=_add_milestone),
        ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            visible=(ctl.control_type if ctl else ONE_TIME) == PERIODIC)

        attach_header = ft.Row(controls=[
            ft.Icon(ft.icons.ATTACH_FILE, size=15, color=COLORS["text"]),
            ft.Text("Скан задания", size=13, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ft.Container(expand=True),
            ft.ElevatedButton("Прикрепить файл", bgcolor=COLORS["primary_light"], color=COLORS["btn_save"], height=30,
                              icon=ft.icons.ATTACH_FILE, on_click=_pick_attach),
        ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        # Build detail card content
        detail_content = ft.Column(controls=[
            ft.Row(controls=[
                ft.Icon(ft.icons.EDIT_DOCUMENT if not is_new else ft.icons.ADD_CIRCLE_OUTLINE, size=20, color=COLORS["text"]),
                ft.Text("Карточка контроля" if not is_new else "Новый контроль", size=15, weight=ft.FontWeight.BOLD, color=COLORS["text"], expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_color=COLORS["text_secondary"], icon_size=18, on_click=_hide_detail),
            ], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Divider(height=1, color=COLORS["border"]),
            ft.Row(controls=[incoming_field, receive_field, receive_btn], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row(controls=[init_dd, new_init_field, add_init_btn], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            content_field,
            exec_container,
            ft.Row(controls=[controller_dd, type_dd, period_dd, custom_days_field], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row(controls=[due_field, due_btn, end_field, end_btn], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            cycle_hint,
            comment_field,
            ft.Container(height=4),
            tasks_header,
            tasks_col,
            ft.Container(height=4),
            milestones_header,
            milestones_col,
            ft.Container(height=4),
            attach_header,
            attach_col,
            ft.Container(height=12),
            ft.Row(controls=[
                ft.ElevatedButton("Удалить", icon=ft.icons.DELETE_FOREVER, bgcolor="#dc2626", color="white",
                                  visible=not is_new, on_click=_delete_detail) if not is_new else ft.Container(),
                ft.Container(expand=True),
                ft.TextButton("Отмена", on_click=_hide_detail, style=ft.ButtonStyle(color=COLORS["text_secondary"])),
                ft.ElevatedButton("Сохранить", icon=ft.icons.SAVE, bgcolor=COLORS["btn_save"], color="white",
                                  on_click=_save_detail),
            ], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ], spacing=8, tight=True, scroll=ft.ScrollMode.AUTO, expand=True)

        detail_card.content = detail_content
        detail_card.width = 820
        detail_card.height = 720
        detail_overlay.visible = True
        try:
            detail_overlay.update()
        except Exception:
            try:
                page.update()
            except Exception:
                pass
        _refresh_cycle_hint()

    # ── Actions for rows ────────────────────────────────────────
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
        extend_days = {"value": str(ctl.period_days if ctl.control_type == PERIODIC else 7)}
        days_field = ft.TextField(
            value=extend_days["value"], hint_text="Продлить на (дней)",
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
            keyboard_type=ft.KeyboardType.NUMBER, width=160, dense=True,
        )
        def _confirm(e=None):
            try:
                try:
                    n = max(1, int(days_field.value))
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
            modal=True, bgcolor=COLORS["primary_light"],
            title=ft.Text("Продлить срок", size=16, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            content=ft.Container(content=days_field, width=220),
            actions=[ft.TextButton("Отмена", on_click=_close),
                     ft.ElevatedButton("Продлить", bgcolor=COLORS["btn_save"], color="white", on_click=_confirm)],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
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
            modal=True, bgcolor=COLORS["primary_light"],
            title=ft.Text("Переместить в архив", size=16, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            content=ft.Text(f"Переместить контроль «{ctl.incoming_number}» в архив?", size=13, color=COLORS["text"]),
            actions=[ft.TextButton("Отмена", on_click=_close),
                     ft.ElevatedButton("В архив", icon=ft.icons.ARCHIVE, bgcolor=COLORS["btn_save"], color="white", on_click=_confirm)],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
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
            modal=True, bgcolor=COLORS["primary_light"],
            title=ft.Text("Удалить навсегда", size=16, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            content=ft.Text(f"Удалить «{ctl.incoming_number}» безвозвратно? Вложения также будут удалены.", size=13, color=COLORS["text"]),
            actions=[ft.TextButton("Отмена", on_click=_close),
                     ft.ElevatedButton("Удалить навсегда", icon=ft.icons.DELETE_FOREVER, bgcolor="#dc2626", color="white", on_click=_confirm)],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        page.open(dialog)

    # ── Export / Import ─────────────────────────────────────────
    export_mode_dd = ft.Dropdown(
        hint_text="Режим экспорта",
        value="table", width=170, height=38,
        options=[ft.dropdown.Option("table", "Как в таблице"), ft.dropdown.Option("full", "Полный (round-trip)")],
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"], size=11),
        dense=True, content_padding=ft.padding.symmetric(horizontal=10, vertical=4),
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
            page._controls_file_picker.save_file(
                dialog_title="Сохранить контроли в Excel",
                file_name=f"controls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                allowed_extensions=["xlsx"],
            )
        except Exception as ex:
            print(f"[CONTROLS_TAB] export trigger error: {ex}")

    def _import(e=None):
        try:
            page._controls_import_picker.pick_files(
                dialog_title="Выбрать файл Excel для импорта",
                allowed_extensions=["xlsx"],
                allow_multiple=False,
            )
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
                    content=ft.Row(controls=[
                        ft.Text(c.incoming_number or "—", size=11, color=COLORS["text_secondary"], width=90, no_wrap=True),
                        ft.Text(c.content or "—", size=11, color=COLORS["text"], expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, tooltip=c.content),
                        ft.Text(_type_label(c), size=10, color=COLORS["text_secondary"], width=80, no_wrap=True),
                    ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]), border_radius=6,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                )
            )
        if len(parsed) > 20:
            preview_list.controls.append(ft.Text(f"… и ещё {len(parsed)-20}", size=10, color=COLORS["text_muted"]))
        summary = ft.Text(
            f"Найдено: {len(parsed)+stats['skipped']} · Импортируемо: {len(parsed)} · Пропущено: {stats['skipped']} · Ошибок: {stats['errors']} · Формат: {'полный' if stats['full_format'] else 'таблица'}",
            size=11, color=COLORS["text_secondary"],
        )
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
            modal=True, bgcolor=COLORS["primary_light"],
            title=ft.Row(controls=[
                ft.Icon(ft.icons.UPLOAD_FILE, size=20, color=COLORS["text"]),
                ft.Text("Импорт из Excel — предпросмотр", size=15, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            content=ft.Container(width=560, content=ft.Column(controls=[summary, preview_list], spacing=8, tight=True)),
            actions=[ft.TextButton("Отмена", on_click=_close),
                     ft.ElevatedButton("Импортировать", icon=ft.icons.CLOUD_DOWNLOAD, bgcolor=COLORS["btn_save"], color="white", on_click=_confirm)],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        page.open(dialog)

    # ── Settings ────────────────────────────────────────────────
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
        page.open(dialog)

    def _add_control(e=None):
        _open_detail(None)

    # ── Toolbar ─────────────────────────────────────────────────
    add_btn = ft.ElevatedButton(
        text="Добавить контроль", icon=ft.icons.ADD_CIRCLE_OUTLINE,
        bgcolor=COLORS["btn_save"], color="white", height=38,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=ft.padding.symmetric(horizontal=12)),
        on_click=_add_control,
    )
    import_btn = ft.ElevatedButton(
        text="Импорт Excel", icon=ft.icons.UPLOAD_FILE,
        bgcolor=COLORS["btn_save_hover"], color="white", height=38,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=ft.padding.symmetric(horizontal=12)),
        on_click=_import,
    )
    export_btn = ft.ElevatedButton(
        text="Экспорт Excel", icon=ft.icons.FILE_DOWNLOAD_OUTLINED,
        bgcolor=COLORS["btn_export"], color="white", height=38,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=ft.padding.symmetric(horizontal=12)),
        on_click=_export,
    )
    settings_btn = ft.IconButton(
        icon=ft.icons.SETTINGS_OUTLINED, icon_size=20, icon_color=COLORS["text_secondary"],
        tooltip="Настройки контролей",
        style=ft.ButtonStyle(bgcolor=COLORS["primary_light"], shape=ft.RoundedRectangleBorder(radius=10), padding=ft.padding.all(8)),
        on_click=_open_settings,
    )

    title_row = ft.Container(
        content=ft.Row(controls=[
            ft.Icon(ft.icons.RULE_FOLDER, size=18, color=COLORS["text"]),
            ft.Text("Контроли", size=15, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ft.Container(width=8),
            sync_dot, ft.Container(width=4), sync_label,
            ft.Container(expand=True),
            add_btn, import_btn, export_mode_dd, export_btn, settings_btn,
        ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.START),
        height=46,
    )

    main_column = ft.Column(
        controls=[
            title_row,
            ft.Container(height=6),
            filter_row1,
            ft.Container(height=6),
            filter_row2,
            ft.Container(height=6),
            counters_row,
            ft.Container(height=6),
            header_row,
            ft.Container(height=2),
            rows_column,
            ft.Container(height=30),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Root stack
    tab_stack = ft.Stack(
        controls=[
            ft.Container(content=main_column, expand=True, padding=ft.padding.only(left=12, right=12, top=8, bottom=8)),
            detail_overlay,
        ],
        expand=True,
    )

    tab_content = ft.Column(
        controls=[tab_stack],
        spacing=0,
        expand=True,
    )

    # ── Background polling ──────────────────────────────────────
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
    print("[CONTROLS_TAB] Controls tab created (rework)")
    return tab_content

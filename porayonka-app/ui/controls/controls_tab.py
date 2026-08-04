# ui/controls/controls_tab.py
# Glass Dark redesign: semi-transparent panels, Russian calendar, larger incoming column,
# proper two-row filters, chip counters, status pills.
# All logic (filters, sort, archive, network, polling, Excel, attachments) preserved.
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
    STATUS_LABELS,
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

from .glass_theme import (
    GLASS, status_color, glass_panel, status_pill,
    glass_button, ghost_button, chip, _RADIUS, _RADIUS_PANEL, _RADIUS_CARD,
)
from .russian_calendar import create_russian_date_field

# ── Status icon mapping (ft.icons.*) ────────────────────────────
STATUS_ICONS = {
    OVERDUE: ft.icons.EVENT_BUSY,
    TODAY: ft.icons.NOTIFICATIONS_ACTIVE,
    SOON: ft.icons.HOURGLASS_BOTTOM,
    IN_PROGRESS: ft.icons.HOURGLASS_TOP,
    DONE: ft.icons.CHECK_CIRCLE,
    COMPLETED: ft.icons.CHECK_CIRCLE_OUTLINE,
    NO_DATE: ft.icons.REMOVE_CIRCLE_OUTLINE,
}

# ── Column widths (incoming >= 150, shrink content/executors) ───
_FIXED = {
    "bar": 6, "num": 38, "incoming": 150, "receive": 96, "initiator": 138,
    "controller": 140, "type": 96, "due": 104, "status": 120, "actions": 110,
}
_ROW_HEIGHT = 54
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


# ── Utilities ────────────────────────────────────────────────────
def _display_date(iso: Optional[str]) -> str:
    d = parse_date(iso)
    return d.strftime("%d.%m.%Y") if d else "\u2014"

def _display_date_or_none(iso: Optional[str]) -> str:
    d = parse_date(iso)
    return d.strftime("%d.%m.%Y") if d else "\u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u0430"

def _type_label(ctl: Control) -> str:
    return "\u043f\u043e\u0441\u0442\u043e\u044f\u043d\u043d\u044b\u0439" if ctl.control_type == PERIODIC else "\u0440\u0430\u0437\u043e\u0432\u044b\u0439"

def _reason_label(reason: str) -> str:
    return "\u0418\u0441\u043f\u043e\u043b\u043d\u0435\u043d" if reason == ARCHIVE_DONE else ("\u0423\u0434\u0430\u043b\u0451\u043d" if reason == ARCHIVE_DELETED else "")

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


# ── Glass-styled inset dropdown ─────────────────────────────────
def _mk_glass_dd(hint, width, options, default="all"):
    return ft.Dropdown(
        hint_text=hint,
        width=width, height=40, value=default,
        options=options,
        border_radius=_RADIUS, border_color=GLASS["inset_border"],
        focused_border_color=GLASS["accent"],
        bgcolor=GLASS["inset_bg"], color=GLASS["text"],
        hint_style=ft.TextStyle(color=GLASS["text_muted"], size=13),
        text_style=ft.TextStyle(size=13, color=GLASS["text"]),
        dense=True,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=6),
    )


# ══════════════════════════════════════════════════════════════════
# CREATE CONTROLS TAB
# ══════════════════════════════════════════════════════════════════
def create_controls_tab(page: ft.Page) -> ft.Column:
    print("[CONTROLS_TAB] Initializing Glass Dark redesign")
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
    sync_label = ft.Text("\u041b\u043e\u043a\u0430\u043b\u044c\u043d\u043e", size=11, color=GLASS["text_muted"])
    sync_dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=GLASS["text_muted"])

    def _layout_widths(width: Optional[float]) -> Dict[str, int]:
        if not width or width <= 0:
            width = 1280
        available = max(400.0, width - _TAB_HORIZONTAL_PADDING)
        fixed_sum = sum(_FIXED.values())
        flex = max(260.0, available - fixed_sum)
        w = dict(_FIXED)
        w["executors"] = int(flex * 0.30)
        w["content"] = int(flex - w["executors"])
        return w

    _W = _layout_widths(page.width)

    # ── Russian Calendar replacement for DatePicker ──────────────
    # Date pickers for filter row (S:/Po:)
    _filter_from_ref = {"value": None}
    _filter_to_ref = {"value": None}

    # We keep a lightweight date-target system for detail card inline calendars
    _date_target = {"setter": None}

    # Ensure FilePickers are mounted
    def _noop_date(e):
        pass

    def _ensure_file_picker_mounted():
        for attr in ("_controls_file_picker", "_controls_import_picker", "_controls_attach_picker"):
            _ensure_file_picker(page, attr, _noop_date)

    _ensure_file_picker_mounted()

    # ── Filter date calendars ────────────────────────────────────
    from_label = ft.Text("\u0421: \u2014", size=13, color=GLASS["text_secondary"], width=110, no_wrap=True)
    to_label = ft.Text("\u041f\u043e: \u2014", size=13, color=GLASS["text_secondary"], width=110, no_wrap=True)

    def _set_from_iso(iso):
        state["f_from"] = iso
        from_label.value = f"\u0421: {_display_date(iso)}" if iso else "\u0421: \u2014"
        try:
            from_label.update()
        except Exception:
            pass
        _apply_filters()

    def _set_to_iso(iso):
        state["f_to"] = iso
        to_label.value = f"\u041f\u043e: {_display_date(iso)}" if iso else "\u041f\u043e: \u2014"
        try:
            to_label.update()
        except Exception:
            pass
        _apply_filters()

    from_cal = create_russian_date_field(page, None, _set_from_iso,
                                          hint="\u041d\u0430\u0447\u0430\u043b\u043e", width=140)
    to_cal = create_russian_date_field(page, None, _set_to_iso,
                                        hint="\u041a\u043e\u043d\u0435\u0446", width=140)

    def _clear_from(e=None):
        state["f_from"] = None
        from_label.value = "\u0421: \u2014"
        from_cal._set_value(None)
        try:
            from_label.update()
        except Exception:
            pass
        _apply_filters()

    def _clear_to(e=None):
        state["f_to"] = None
        to_label.value = "\u041f\u043e: \u2014"
        to_cal._set_value(None)
        try:
            to_label.update()
        except Exception:
            pass
        _apply_filters()

    # ── Persistence / sync ───────────────────────────────────────
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
            sync_label.value = "\u041b\u043e\u043a\u0430\u043b\u044c\u043d\u043e"
            sync_dot.bgcolor = GLASS["text_muted"]
        else:
            role = "\u0430\u0434\u043c\u0438\u043d" if network_role == "admin" else "\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c"
            sync_label.value = f"\u0421\u0435\u0442\u044c: {role}"
            sync_dot.bgcolor = GLASS["in_progress"] if state["network_ok"] else GLASS["overdue"]
            if state["last_sync"]:
                sync_label.value += f" \u00b7 {state['last_sync'].strftime('%H:%M:%S')}"
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

    # ── Filtering / sorting ──────────────────────────────────────
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
                    return True
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

    # ── UI helpers ───────────────────────────────────────────────
    def _cell(text: str, width: int, color=GLASS["text"], size=13, bold=False,
              center=False, tooltip=None, max_lines=1) -> ft.Container:
        return ft.Container(
            content=ft.Text(text, size=size, color=color,
                            weight=ft.FontWeight.W_600 if bold else None,
                            no_wrap=True, max_lines=max_lines,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            tooltip=tooltip or (text if len(text) > 20 else None)),
            width=width, padding=ft.padding.only(left=6, right=4),
            alignment=ft.alignment.center if center else ft.alignment.center_left,
        )

    def _action_icon(icon, color, tooltip, handler):
        return ft.IconButton(
            icon=icon, icon_size=16, icon_color=color, tooltip=tooltip,
            width=30, height=30, padding=0,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
            on_click=handler,
        )

    # ── Row building ─────────────────────────────────────────────
    def _build_row(ctl: Control, num: int, idx: int) -> ft.Container:
        st = deadline_status(ctl, soon_days)
        st_color = status_color(st)
        content = ctl.content or ctl.incoming_number
        content_tooltip = ctl.content or ""
        if ctl.tasks:
            task_txt = "; ".join(t.title for t in ctl.tasks if t.title)
            if task_txt:
                content_tooltip = (content_tooltip + "\n" + task_txt).strip()

        content_controls = [
            _cell(content, _W["content"] - (22 if ctl.attachments else 0),
                  tooltip=content_tooltip, max_lines=2)
        ]
        if ctl.attachments:
            content_controls.append(ft.Container(
                content=ft.Row(controls=[
                    ft.Icon(ft.icons.ATTACH_FILE, size=12, color=GLASS["accent"]),
                    ft.Text(str(len(ctl.attachments)), size=10, color=GLASS["accent"], no_wrap=True),
                ], spacing=2, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                width=22,
            ))

        is_archive = state["mode"] == "archive"
        type_cell = _cell(_type_label(ctl), _W["type"], color=GLASS["text_secondary"])
        if is_archive:
            reason = ctl.archive_reason or ""
            reason_text = _reason_label(reason)
            if ctl.archived_at:
                reason_text = f"{reason_text} \u00b7 {_display_date(ctl.archived_at)}"
            type_cell = _cell(reason_text, _W["type"], color=GLASS["text_secondary"], tooltip=reason)

        actions = []
        if is_archive:
            actions.append(_action_icon(ft.icons.RESTORE, GLASS["in_progress"], "\u0412\u043e\u0441\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c", lambda e, c=ctl: _restore(c)))
            actions.append(_action_icon(ft.icons.DELETE_FOREVER, GLASS["overdue"], "\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u043d\u0430\u0432\u0441\u0435\u0433\u0434\u0430", lambda e, c=ctl: _delete_forever(c)))
        else:
            actions.append(_action_icon(ft.icons.CHECK_CIRCLE_OUTLINE, GLASS["in_progress"], "\u0418\u0441\u043f\u043e\u043b\u043d\u0435\u043d\u043e", lambda e, c=ctl: _complete(c)))
            actions.append(_action_icon(ft.icons.UPDATE_OUTLINED, GLASS["today"], "\u041f\u0440\u043e\u0434\u043b\u0438\u0442\u044c \u0441\u0440\u043e\u043a", lambda e, c=ctl: _extend(c)))
            actions.append(_action_icon(ft.icons.DELETE_OUTLINE, GLASS["overdue"], "\u0412 \u0430\u0440\u0445\u0438\u0432", lambda e, c=ctl: _confirm_delete(c)))

        eff_due = effective_due_date(ctl)
        due_str = _display_date(eff_due.isoformat() if eff_due else ctl.due_date)
        # Color due date if urgent
        due_color = GLASS["text"]
        if st in (OVERDUE, TODAY, SOON):
            due_color = st_color

        # Alternating row background
        row_bg = f"{GLASS['surface_solid']}66" if idx % 2 == 0 else "transparent"

        row_controls = [
            ft.Container(width=_W["bar"], height=34, bgcolor=st_color,
                         border_radius=2),
            _cell(str(num), _W["num"], center=True, color=GLASS["text_secondary"]),
            _cell(ctl.incoming_number or "\u2014", _W["incoming"], bold=True,
                  tooltip=ctl.incoming_number),
            _cell(_display_date(ctl.receive_date), _W["receive"],
                  color=GLASS["text_secondary"]),
            _cell(short_name(ctl.initiator) if ctl.initiator else "\u2014",
                  _W["initiator"], tooltip=ctl.initiator),
            ft.Row(controls=content_controls, spacing=2, tight=True,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER,
                   alignment=ft.MainAxisAlignment.START),
            _cell(", ".join(short_name(x) for x in ctl.executors) or "\u2014",
                  _W["executors"], tooltip=", ".join(ctl.executors)),
            _cell(short_name(ctl.controller) if ctl.controller else "\u2014",
                  _W["controller"], tooltip=ctl.controller),
            type_cell,
            _cell(due_str, _W["due"], bold=True, color=due_color),
            # Status pill
            ft.Container(
                content=ft.Row(controls=[
                    ft.Icon(STATUS_ICONS.get(st, ft.icons.REMOVE_CIRCLE_OUTLINE),
                            size=12, color=st_color),
                    ft.Text(STATUS_LABELS.get(st, st), size=11, color=st_color,
                            weight=ft.FontWeight.W_600, no_wrap=True),
                ], spacing=3, tight=True,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
                width=_W["status"], height=24, border_radius=12,
                padding=ft.padding.symmetric(horizontal=6),
                alignment=ft.alignment.center,
                bgcolor=f"{st_color}22",
                border=ft.border.all(1, st_color),
            ),
        ]
        row_controls.append(ft.Row(controls=actions, spacing=0, tight=True,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER))

        row = ft.Container(
            content=ft.Row(controls=row_controls, spacing=2, tight=True,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=_ROW_HEIGHT,
            bgcolor=row_bg,
            border=ft.border.all(1, GLASS["border"]),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=4, vertical=4),
            on_click=lambda e, c=ctl: _open_detail(c),
        )

        # Hover effect
        def _on_hover(e):
            if e.data == "true":
                row.bgcolor = "#ffffff08"
            else:
                row.bgcolor = row_bg
            try:
                row.update()
            except Exception:
                pass

        row.on_hover = _on_hover
        return row

    def _rebuild_table():
        rows_column.controls.clear()
        visible = _filtered()
        if not visible:
            label = ("\u0412 \u0430\u0440\u0445\u0438\u0432\u0435 \u043f\u0443\u0441\u0442\u043e" if state["mode"] == "archive"
                     else "\u041a\u043e\u043d\u0442\u0440\u043e\u043b\u0435\u0439 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e")
            rows_column.controls.append(ft.Container(
                content=ft.Row(controls=[
                    ft.Icon(ft.icons.INBOX, size=18, color=GLASS["text_muted"]),
                    ft.Text(label, size=13, color=GLASS["text_secondary"]),
                ], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                height=54, bgcolor=GLASS["surface"],
                border=ft.border.all(1, GLASS["border"]),
                border_radius=_RADIUS,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            ))
            try:
                rows_column.update()
            except Exception:
                pass
            return
        for i, ctl in enumerate(visible, 1):
            rows_column.controls.append(_build_row(ctl, i, i - 1))
        try:
            rows_column.update()
        except Exception:
            pass

    # ── Counters (chips) ─────────────────────────────────────────
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
            if key == "all":
                c = GLASS["accent"]
            else:
                c = status_color(key)
            btn.bgcolor = f"{c}22" if selected else "transparent"
            btn.border = ft.border.all(1, c) if selected else ft.border.all(1, "transparent")
            try:
                btn.update()
            except Exception:
                pass

    def _refresh_counters():
        counts = _counts()
        for key, btn in counter_refs.items():
            try:
                row = btn.content
                # Find the badge (3rd control in row: dot, label, badge)
                badge = row.controls[2]
                badge.value = str(counts.get(key, 0))
            except Exception:
                pass
        _restyle_counters()

    def _mk_counter(key: str, label: str, color: str) -> ft.Container:
        counts = _counts()
        dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=color)
        lbl = ft.Text(label, size=12, color=GLASS["text_secondary"],
                      weight=ft.FontWeight.W_500, no_wrap=True)
        badge = ft.Text(str(counts.get(key, 0)), size=11, color=GLASS["text"],
                        weight=ft.FontWeight.W_700, no_wrap=True)
        btn = ft.Container(
            content=ft.Row(controls=[dot, lbl, badge], spacing=5, tight=True,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=30, border_radius=15,
            padding=ft.padding.symmetric(horizontal=10),
            alignment=ft.alignment.center, bgcolor="transparent",
            border=ft.border.all(1, "transparent"),
            ink=True,
            on_click=lambda e, v=key: _set_status_filter(v),
        )
        counter_refs[key] = btn
        return btn

    counters_row = ft.Container(
        content=ft.Row(controls=[
            _mk_counter("all", "\u0412\u0441\u0435", GLASS["accent"]),
            _mk_counter(OVERDUE, "\u041f\u0440\u043e\u0441\u0440\u043e\u0447\u0435\u043d\u043e", GLASS["overdue"]),
            _mk_counter(TODAY, "\u0421\u0435\u0433\u043e\u0434\u043d\u044f", GLASS["today"]),
            _mk_counter(SOON, "\u0421\u043a\u043e\u0440\u043e", GLASS["soon"]),
            _mk_counter(IN_PROGRESS, "\u0412 \u0440\u0430\u0431\u043e\u0442\u0435", GLASS["in_progress"]),
            _mk_counter(DONE, "\u0418\u0441\u043f\u043e\u043b\u043d\u0435\u043d\u043e", GLASS["done"]),
        ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.START, scroll=ft.ScrollMode.HIDDEN),
        height=38,
    )

    # ── Mode switch (Active / Archive) ───────────────────────────
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
            btn.bgcolor = GLASS["accent"] if selected else "transparent"
            btn.border = ft.border.all(1, GLASS["accent"] if selected else GLASS["border"])
            try:
                for ctl in btn.content.controls:
                    if isinstance(ctl, ft.Text):
                        ctl.color = GLASS["text"] if selected else GLASS["text_secondary"]
                    elif hasattr(ctl, "color"):
                        try:
                            ctl.color = GLASS["text"] if selected else GLASS["text_secondary"]
                        except Exception:
                            pass
                btn.update()
            except Exception:
                pass

    def _mk_mode_btn(mode: str, label: str, icon) -> ft.Container:
        selected = state["mode"] == mode
        btn = ft.Container(
            content=ft.Row(controls=[
                ft.Icon(icon, size=14, color=GLASS["text"] if selected else GLASS["text_secondary"]),
                ft.Text(label, size=12, weight=ft.FontWeight.W_600,
                        color=GLASS["text"] if selected else GLASS["text_secondary"], no_wrap=True),
            ], spacing=5, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=30, padding=ft.padding.symmetric(horizontal=12), border_radius=8,
            alignment=ft.alignment.center,
            bgcolor=GLASS["accent"] if selected else "transparent",
            border=ft.border.all(1, GLASS["accent"] if selected else GLASS["border"]),
            ink=True, on_click=lambda e, m=mode: _set_mode(m),
        )
        mode_buttons[mode] = btn
        return btn

    mode_row = ft.Container(
        content=ft.Row(controls=[
            _mk_mode_btn("active", "\u0410\u043a\u0442\u0438\u0432\u043d\u044b\u0435", ft.icons.PLAYLIST_PLAY),
            _mk_mode_btn("archive", "\u0410\u0440\u0445\u0438\u0432", ft.icons.ARCHIVE_OUTLINED),
        ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.START),
        height=38,
    )

    # ── Filters ──────────────────────────────────────────────────
    search_field = ft.TextField(
        hint_text="\u041f\u043e\u0438\u0441\u043a \u043f\u043e \u0441\u043e\u0434\u0435\u0440\u0436\u0430\u043d\u0438\u044e, \u043d\u043e\u043c\u0435\u0440\u0443\u2026",
        prefix_icon=ft.icons.SEARCH,
        border_radius=_RADIUS, border_color=GLASS["inset_border"],
        focused_border_color=GLASS["accent"],
        bgcolor=GLASS["inset_bg"], color=GLASS["text"],
        hint_style=ft.TextStyle(color=GLASS["text_muted"], size=13),
        text_style=ft.TextStyle(size=13),
        height=40, dense=True,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
    )

    def _on_search(e=None):
        state["search"] = search_field.value or ""
        _apply_filters()

    search_field.on_change = _on_search

    status_filter_dd = _mk_glass_dd("\u0412\u0441\u0435 \u0441\u0442\u0430\u0442\u0443\u0441\u044b", 170, [
        ft.dropdown.Option("all", "\u0412\u0441\u0435 \u0441\u0442\u0430\u0442\u0443\u0441\u044b"),
        ft.dropdown.Option(OVERDUE, "\u041f\u0440\u043e\u0441\u0440\u043e\u0447\u0435\u043d\u043e"),
        ft.dropdown.Option(TODAY, "\u0421\u0435\u0433\u043e\u0434\u043d\u044f"),
        ft.dropdown.Option(SOON, "\u0421\u043a\u043e\u0440\u043e"),
        ft.dropdown.Option(IN_PROGRESS, "\u0412 \u0440\u0430\u0431\u043e\u0442\u0435"),
        ft.dropdown.Option(DONE, "\u0418\u0441\u043f\u043e\u043b\u043d\u0435\u043d\u043e"),
        ft.dropdown.Option(COMPLETED, "\u0417\u0430\u0432\u0435\u0440\u0448\u0451\u043d"),
    ])
    type_filter_dd = _mk_glass_dd("\u0412\u0441\u0435 \u0442\u0438\u043f\u044b", 150, [
        ft.dropdown.Option("all", "\u0412\u0441\u0435 \u0442\u0438\u043f\u044b"),
        ft.dropdown.Option(ONE_TIME, "\u0420\u0430\u0437\u043e\u0432\u044b\u0439"),
        ft.dropdown.Option(PERIODIC, "\u041f\u043e\u0441\u0442\u043e\u044f\u043d\u043d\u044b\u0439"),
    ])
    initiator_filter_dd = _mk_glass_dd("\u0412\u0441\u0435 \u0438\u043d\u0438\u0446\u0438\u0430\u0442\u043e\u0440\u044b", 200,
        [ft.dropdown.Option("all", "\u0412\u0441\u0435 \u0438\u043d\u0438\u0446\u0438\u0430\u0442\u043e\u0440\u044b")] + [ft.dropdown.Option(i) for i in initiators])
    executor_filter_dd = _mk_glass_dd("\u0412\u0441\u0435 \u0438\u0441\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u0438", 200,
        [ft.dropdown.Option("all", "\u0412\u0441\u0435 \u0438\u0441\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u0438")] + [ft.dropdown.Option(n, short_name(n)) for n in available_names])
    controller_filter_dd = _mk_glass_dd("\u0412\u0441\u0435 \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u0451\u0440\u044b", 200,
        [ft.dropdown.Option("all", "\u0412\u0441\u0435 \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u0451\u0440\u044b")] + [ft.dropdown.Option(n, short_name(n)) for n in available_names])

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
        state.update(f_status="all", f_type="all", f_initiator="all", f_executor="all",
                     f_controller="all", f_from=None, f_to=None)
        from_cal._set_value(None)
        to_cal._set_value(None)
        _restyle_counters()
        try:
            page.update()
        except Exception:
            pass
        _apply_filters()

    # Two neat filter rows
    filter_row1 = glass_panel(
        ft.Row(controls=[
            search_field, status_filter_dd, type_filter_dd,
        ], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.START),
        padding=6, radius=_RADIUS_PANEL,
    )
    filter_row1.height = 50

    filter_row2 = glass_panel(
        ft.Row(controls=[
            initiator_filter_dd, executor_filter_dd, controller_filter_dd,
            from_cal,
            ft.IconButton(icon=ft.icons.CLEAR, icon_size=14,
                          icon_color=GLASS["text_muted"], tooltip="\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u0421",
                          on_click=_clear_from, width=28, height=28, padding=0),
            to_cal,
            ft.IconButton(icon=ft.icons.CLEAR, icon_size=14,
                          icon_color=GLASS["text_muted"], tooltip="\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u041f\u043e",
                          on_click=_clear_to, width=28, height=28, padding=0),
            ft.Container(expand=True),
            ghost_button("\u0421\u0431\u0440\u043e\u0441", _reset_filters, compact=True),
        ], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.START),
        padding=6, radius=_RADIUS_PANEL,
    )
    filter_row2.height = 50

    # ── Header row (column labels) ───────────────────────────────
    def _header_cell(text: str, width: int, key: str, center=False) -> ft.Container:
        arrow = ("\u25b2" if (state["sort_key"] == key and not state["sort_reverse"])
                 else ("\u25bc" if state["sort_key"] == key and state["sort_reverse"] else ""))
        return ft.Container(
            content=ft.Text(f"{text} {arrow}".strip(), size=11,
                            weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"],
                            no_wrap=True, tooltip="\u0421\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u043a\u0430"),
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
        height=34, bgcolor="#0d1830",
        border=ft.border.only(bottom=ft.BorderSide(1, GLASS["border"])),
        border_radius=8, padding=ft.padding.symmetric(horizontal=4, vertical=2),
    )

    def _rebuild_header():
        is_archive = state["mode"] == "archive"
        col_labels = [
            ft.Container(width=_W["bar"]),
            _header_cell("\u2116", _W["num"], "num", center=True),
            _header_cell("\u0412\u0425. \u2116", _W["incoming"], "incoming"),
            _header_cell("\u0414\u0410\u0422\u0410 \u041f\u041e\u0421\u0422.", _W["receive"], "receive"),
            _header_cell("\u0418\u041d\u0418\u0426\u0418\u0410\u0422\u041e\u0420", _W["initiator"], "initiator"),
            ft.Container(width=_W["content"], padding=ft.padding.only(left=6, right=4),
                         content=ft.Text("\u0421\u041e\u0414\u0415\u0420\u0416\u0410\u041d\u0418\u0415", size=11,
                                         weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"], no_wrap=True)),
            ft.Container(width=_W["executors"], padding=ft.padding.only(left=6, right=4),
                         content=ft.Text("\u0418\u0421\u041f\u041e\u041b\u041d\u0418\u0422\u0415\u041b\u0418", size=11,
                                         weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"], no_wrap=True)),
            ft.Container(width=_W["controller"], padding=ft.padding.only(left=6, right=4),
                         content=ft.Text("\u0417\u0410 \u041a\u0415\u041c", size=11,
                                         weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"], no_wrap=True)),
            _header_cell("\u041f\u0420\u0418\u0427\u0418\u041d\u0410" if is_archive else "\u0422\u0418\u041f",
                         _W["type"], "type"),
            _header_cell("\u0421\u0420\u041e\u041a \u0418\u0421\u041f\u041e\u041b\u041d.", _W["due"], "due"),
            ft.Container(width=_W["status"], padding=ft.padding.only(left=6, right=4),
                         content=ft.Text("\u0421\u0422\u0410\u0422\u0423\u0421", size=11,
                                         weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"], no_wrap=True)),
        ]
        col_labels.append(ft.Container(width=_W["actions"]))
        header_row.content = ft.Row(controls=col_labels, spacing=2, tight=True,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER)
        try:
            header_row.update()
        except Exception:
            pass

    # ── Detail overlay (master-detail, glass styled) ─────────────
    def _build_inline_multi(available: List[str], initial: List[str], title: str, on_change_cb=None):
        selected = list(initial)
        expanded = {"value": False}
        search_val = {"value": ""}

        badge = ft.Text(f"\u0412\u044b\u0431\u0440\u0430\u043d\u043e: {len(selected)}", size=11, color=GLASS["text_secondary"])
        summary = ft.Text(", ".join(short_name(x) for x in selected) or "\u043d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d\u043e",
                          size=11, color=GLASS["text"], max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
                          tooltip=", ".join(selected))

        search_field_ms = ft.TextField(
            hint_text=f"\u041f\u043e\u0438\u0441\u043a {title.lower()}\u2026",
            prefix_icon=ft.icons.SEARCH,
            height=34, dense=True,
            border_radius=_RADIUS, border_color=GLASS["inset_border"],
            focused_border_color=GLASS["accent"],
            bgcolor=GLASS["inset_bg"], color=GLASS["text"],
            hint_style=ft.TextStyle(color=GLASS["text_muted"], size=11),
            text_style=ft.TextStyle(size=11),
            content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
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
                        badge.value = f"\u0412\u044b\u0431\u0440\u0430\u043d\u043e: {len(selected)}"
                        summary.value = ", ".join(short_name(x) for x in selected) or "\u043d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d\u043e"
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
                        label_style=ft.TextStyle(size=11, color=GLASS["text"]),
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

        list_wrapper = ft.Container(
            content=list_col,
            border=ft.border.all(1, GLASS["border"]), border_radius=8,
            padding=ft.padding.all(4), bgcolor=GLASS["surface_solid"],
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
            badge.value = "\u0412\u044b\u0431\u0440\u0430\u043d\u043e: 0"
            summary.value = "\u043d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d\u043e"
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

        expand_btn = ft.IconButton(icon=ft.icons.EXPAND_MORE, icon_size=18,
                                   icon_color=GLASS["text_secondary"],
                                   tooltip="\u0420\u0430\u0437\u0432\u0435\u0440\u043d\u0443\u0442\u044c \u0441\u043f\u0438\u0441\u043e\u043a",
                                   on_click=_toggle_expand)

        header = ft.Row(controls=[
            ft.Text(title, size=12, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
            ft.Container(width=8), badge,
            ft.Container(expand=True),
            ft.TextButton("\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c", on_click=_clear_all,
                          style=ft.ButtonStyle(color=GLASS["overdue"], padding=ft.padding.symmetric(horizontal=6))),
            expand_btn,
        ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        _rebuild_list()

        container = ft.Container(
            content=ft.Column(controls=[header, summary, search_field_ms, list_wrapper],
                              spacing=4, tight=True),
            bgcolor=GLASS["surface"],
            border=ft.border.only(
                top=ft.BorderSide(1, GLASS["top_edge"]),
                left=ft.BorderSide(1, GLASS["border"]),
                right=ft.BorderSide(1, GLASS["border"]),
                bottom=ft.BorderSide(1, GLASS["border"]),
            ),
            border_radius=_RADIUS,
            padding=ft.padding.all(8),
        )
        container._get_selected = lambda: list(selected)
        container._set_selected = lambda new_list: (
            selected.clear(), selected.extend(new_list), _rebuild_list(),
            setattr(badge, 'value', f"\u0412\u044b\u0431\u0440\u0430\u043d\u043e: {len(selected)}"),
            setattr(summary, 'value', ", ".join(short_name(x) for x in selected) or "\u043d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d\u043e"),
        )
        return container

    # Detail overlay state
    detail_state: Dict = {
        "control_id": None, "is_new": True, "executors_picker": None,
        "tasks": [], "milestones": [], "attachments": [],
        "receive_date": None, "due_date": None, "end_date": None,
    }

    detail_card = ft.Container(
        width=860, height=740,
        bgcolor=GLASS["surface"],
        border=ft.border.only(
            top=ft.BorderSide(1, GLASS["top_edge"]),
            left=ft.BorderSide(1, GLASS["border"]),
            right=ft.BorderSide(1, GLASS["border"]),
            bottom=ft.BorderSide(1, GLASS["border"]),
        ),
        border_radius=_RADIUS_CARD,
        padding=ft.padding.all(14),
        content=ft.Column(controls=[ft.Text("\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430\u2026")],
                          scroll=ft.ScrollMode.AUTO, expand=True),
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

    # Glass-styled inset field helper for the detail card
    def _inset_field(value="", hint="", read_only=False, width=None, dense=True,
                     multiline=False, min_lines=None, max_lines=None, expand=False,
                     height=40, on_change=None):
        return ft.TextField(
            value=value, hint_text=hint, read_only=read_only,
            width=width, height=height, dense=dense,
            multiline=multiline, min_lines=min_lines, max_lines=max_lines,
            expand=expand,
            border_radius=_RADIUS, border_color=GLASS["inset_border"],
            focused_border_color=GLASS["accent"],
            bgcolor=GLASS["inset_bg"], color=GLASS["text"],
            hint_style=ft.TextStyle(color=GLASS["text_muted"], size=13),
            text_style=ft.TextStyle(size=13),
            content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
            on_change=on_change,
        )

    def _inset_dd(hint, options, value=None, width=200, visible=True):
        return ft.Dropdown(
            hint_text=hint, value=value, options=options,
            width=width, height=40,
            border_radius=_RADIUS, border_color=GLASS["inset_border"],
            focused_border_color=GLASS["accent"],
            bgcolor=GLASS["inset_bg"], color=GLASS["text"],
            hint_style=ft.TextStyle(color=GLASS["text_muted"], size=13),
            text_style=ft.TextStyle(size=13),
            dense=True,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=6),
            visible=visible,
        )

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
        incoming_field = _inset_field(
            value=ctl.incoming_number if ctl else "",
            hint="\u0412\u0445\u043e\u0434\u044f\u0449\u0438\u0439 \u2116 \u0412\u0425\u0421\u041e\u041f *", expand=True)
        receive_cal = create_russian_date_field(page, detail_state["receive_date"],
                                                 lambda iso: _set_receive(iso),
                                                 hint="\u0414\u0430\u0442\u0430 \u043f\u043e\u0441\u0442\u0443\u043f\u043b\u0435\u043d\u0438\u044f", width=140)

        def _set_receive(iso):
            detail_state["receive_date"] = iso
            receive_cal._set_value(iso)

        init_dd = _inset_dd(
            "\u0418\u043d\u0438\u0446\u0438\u0430\u0442\u043e\u0440",
            [ft.dropdown.Option(i) for i in initiators],
            value=ctl.initiator if (ctl and ctl.initiator in initiators) else None,
            width=220)
        new_init_field = _inset_field(hint="\u041d\u043e\u0432\u044b\u0439 \u0438\u043d\u0438\u0446\u0438\u0430\u0442\u043e\u0440\u2026", width=200, height=36)

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
                initiator_filter_dd.options = [ft.dropdown.Option("all", "\u0412\u0441\u0435 \u0438\u043d\u0438\u0446\u0438\u0430\u0442\u043e\u0440\u044b")] + [ft.dropdown.Option(i) for i in initiators]
                initiator_filter_dd.update()
            except Exception:
                pass

        add_init_btn = glass_button("\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c", _add_initiator, compact=True,
                                     bgcolor=GLASS["surface_solid"], fgcolor=GLASS["accent"], height=36)

        content_field = _inset_field(
            value=ctl.content if ctl else "",
            hint="\u0421\u043e\u0434\u0435\u0440\u0436\u0430\u043d\u0438\u0435 \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u044f\u2026",
            multiline=True, min_lines=3, max_lines=5)

        exec_container = _build_inline_multi(available_names, list(ctl.executors) if ctl else [], "\u0418\u0441\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u0438")

        controller_dd = _inset_dd(
            "\u0417\u0430 \u043a\u0435\u043c \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u044c",
            [ft.dropdown.Option(n, short_name(n)) for n in available_names],
            value=ctl.controller if (ctl and ctl.controller in available_names) else None,
            width=200)

        type_dd = _inset_dd(
            "\u0422\u0438\u043f",
            [ft.dropdown.Option(ONE_TIME, "\u0420\u0430\u0437\u043e\u0432\u044b\u0439"), ft.dropdown.Option(PERIODIC, "\u041f\u043e\u0441\u0442\u043e\u044f\u043d\u043d\u044b\u0439")],
            value=ctl.control_type if ctl else ONE_TIME, width=140)
        period_dd = _inset_dd(
            "\u041f\u0435\u0440\u0438\u043e\u0434\u0438\u0447\u043d\u043e\u0441\u0442\u044c",
            [ft.dropdown.Option(k, l) for k, l, _ in _PERIOD_LABELS],
            value=_period_key(ctl.period_days if ctl else 7), width=170,
            visible=(ctl.control_type if ctl else ONE_TIME) == PERIODIC)
        custom_days_field = _inset_field(
            value=str(ctl.period_days) if ctl else "7",
            hint="\u0418\u043d\u0442\u0435\u0440\u0432\u0430\u043b \u0434\u043d\u0435\u0439", width=110, height=40,
            visible=_period_key(ctl.period_days if ctl else 7) == "custom")

        due_cal = create_russian_date_field(page, detail_state["due_date"],
                                             lambda iso: _set_due(iso),
                                             hint="\u0421\u043b\u0435\u0434\u0443\u044e\u0449\u0430\u044f \u0434\u0430\u0442\u0430", width=160)

        def _set_due(iso):
            detail_state["due_date"] = iso
            due_cal._set_value(iso)
            _refresh_cycle_hint()

        end_cal = create_russian_date_field(page, detail_state["end_date"],
                                             lambda iso: _set_end(iso),
                                             hint="\u041a\u043e\u043d\u0435\u0447\u043d\u0430\u044f \u0434\u0430\u0442\u0430", width=140)

        def _set_end(iso):
            detail_state["end_date"] = iso
            end_cal._set_value(iso)
            _refresh_cycle_hint()

        # Cycle hint
        cycle_hint = ft.Text("", size=10, color=GLASS["text_muted"], italic=True)

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
                dates = [base + timedelta(days=days * i) for i in range(1, 4)]
                cycle_hint.value = "\u0421\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0435: " + " \u00b7 ".join(d.strftime("%d.%m.%Y") for d in dates)
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

        comment_field = _inset_field(
            value=ctl.comment if ctl else "",
            hint="\u041a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0439\u2026",
            multiline=True, min_lines=1, max_lines=3)

        # ── Tasks ────────────────────────────────────────────────
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
            task_due_cal = create_russian_date_field(
                page, t_ui["due_ref"]["value"],
                lambda iso, ui=t_ui: (ui["due_ref"].update({"value": iso}), None),
                hint="\u0421\u0440\u043e\u043a", width=110)

            ass_selected = t_ui["assignees"]
            ass_badge = ft.Text(f"\u041e\u0442\u0432: {len(ass_selected)}", size=10, color=GLASS["text_secondary"])
            ass_summary = ft.Text(", ".join(short_name(x) for x in ass_selected) or "\u043d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d\u044b",
                                   size=10, color=GLASS["text"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
            ass_search = ft.TextField(hint_text="\u041f\u043e\u0438\u0441\u043a\u2026", height=30, dense=True, visible=False,
                                      border_radius=6, border_color=GLASS["inset_border"],
                                      bgcolor=GLASS["inset_bg"], color=GLASS["text"],
                                      text_style=ft.TextStyle(size=10))
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
                            ass_badge.value = f"\u041e\u0442\u0432: {len(t_ui['assignees'])}"
                            ass_summary.value = ", ".join(short_name(x) for x in t_ui["assignees"]) or "\u043d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d\u044b"
                            try:
                                ass_badge.update()
                                ass_summary.update()
                            except Exception:
                                pass
                        return _chg
                    ass_list.controls.append(
                        ft.Checkbox(label=short_name(name), value=name in t_ui["assignees"],
                                    active_color=GLASS["accent"],
                                    label_style=ft.TextStyle(size=10, color=GLASS["text"]),
                                    tooltip=name, on_change=_mk(name), height=24)
                    )
                try:
                    ass_list.update()
                except Exception:
                    pass

            ass_search.on_change = lambda e: _rebuild_ass_list()

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

            ass_expand_btn = ft.IconButton(icon=ft.icons.EXPAND_MORE, icon_size=16,
                                            icon_color=GLASS["text_secondary"],
                                            on_click=_toggle_ass)
            ass_clear_btn = ft.TextButton(
                "\u041e\u0447\u0438\u0441\u0442.",
                on_click=lambda e: (t_ui["assignees"].clear(), setattr(ass_badge, 'value', "\u041e\u0442\u0432: 0"), setattr(ass_summary, 'value', "\u043d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d\u044b"), ass_badge.update() if hasattr(ass_badge, 'update') else None, ass_summary.update() if hasattr(ass_summary, 'update') else None, _rebuild_ass_list()))

            ass_wrapper = ft.Container(content=ass_list, border=ft.border.all(1, GLASS["border"]),
                                       border_radius=6, padding=ft.padding.all(4),
                                       bgcolor=GLASS["surface_solid"], visible=False)

            _rebuild_ass_list()

            done_sw = ft.Switch(value=t_ui["is_done"], active_color=GLASS["in_progress"], height=26,
                                on_change=lambda e, ui=t_ui: ui.update({"is_done": bool(e.control.value)}))
            done_date_f = ft.Text(_display_date_or_none(t_ui["done_ref"]["value"]), size=10,
                                   color=GLASS["text_secondary"], width=80)

            return ft.Container(
                content=ft.Column(controls=[
                    ft.Row(controls=[
                        ft.Icon(ft.icons.LIST_ALT, size=14, color=GLASS["text_muted"]),
                        title_f,
                        ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=16, icon_color=GLASS["overdue"],
                                      tooltip="\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u043f\u0443\u043d\u043a\u0442",
                                      on_click=lambda e, ui=t_ui: _remove_task(ui)),
                    ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row(controls=[ass_badge, ass_summary, ass_expand_btn, ass_clear_btn],
                           spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ass_search, ass_wrapper,
                    ft.Row(controls=[
                        ft.Text("\u0421\u0440\u043e\u043a:", size=10, color=GLASS["text_secondary"]),
                        task_due_cal,
                        ft.Container(width=12),
                        done_sw,
                        ft.Text("\u0438\u0441\u043f\u043e\u043b\u043d\u0435\u043d\u043e", size=10, color=GLASS["text_secondary"]),
                        done_date_f,
                    ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ], spacing=4, tight=True),
                bgcolor=GLASS["surface"],
                border=ft.border.only(
                    top=ft.BorderSide(1, GLASS["top_edge"]),
                    left=ft.BorderSide(1, GLASS["border"]),
                    right=ft.BorderSide(1, GLASS["border"]),
                    bottom=ft.BorderSide(1, GLASS["border"]),
                ),
                border_radius=_RADIUS,
                padding=ft.padding.all(8),
            )

        def _remove_task(ui):
            if ui in detail_state["tasks"]:
                detail_state["tasks"].remove(ui)
            _rebuild_task_cards()

        def _add_task(e=None):
            new_ui = {
                "title_field": _inset_field(hint="\u041f\u0443\u043d\u043a\u0442 (\u043d\u0430\u043f\u0440. \u043f.1)", height=36, expand=True),
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
                    "title_field": _inset_field(value=t.title, hint="\u041f\u0443\u043d\u043a\u0442", height=36, expand=True),
                    "assignees": list(t.assignees),
                    "due_ref": {"value": t.due_date},
                    "is_done": t.is_done,
                    "done_ref": {"value": t.done_date},
                })
        _rebuild_task_cards()

        # ── Milestones ───────────────────────────────────────────
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
            m_date_cal = create_russian_date_field(
                page, m_ui["date_ref"]["value"],
                lambda iso, ui=m_ui: ui["date_ref"].update({"value": iso}),
                hint="\u0414\u0430\u0442\u0430", width=140)
            note_f = _inset_field(value=m_ui["note"], hint="\u0422\u043e\u0447\u043a\u0430 (\u043e\u043f\u0438\u0441\u0430\u043d\u0438\u0435)", height=34, expand=True,
                                   on_change=lambda e, ui=m_ui: ui.update({"note": e.control.value or ""}))
            done_sw = ft.Switch(value=m_ui["is_done"], active_color=GLASS["in_progress"], height=26,
                                on_change=lambda e, ui=m_ui: ui.update({"is_done": bool(e.control.value)}))
            return ft.Container(
                content=ft.Row(controls=[
                    m_date_cal, note_f, done_sw,
                    ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=16, icon_color=GLASS["overdue"],
                                  on_click=lambda e, ui=m_ui: _remove_milestone(ui)),
                ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=GLASS["surface"],
                border=ft.border.all(1, GLASS["border"]), border_radius=_RADIUS,
                padding=ft.padding.all(6),
            )

        def _remove_milestone(ui):
            if ui in detail_state["milestones"]:
                detail_state["milestones"].remove(ui)
            _rebuild_milestones()

        def _add_milestone(e=None):
            detail_state["milestones"].append({
                "date_ref": {"value": None}, "note": "", "is_done": False,
            })
            _rebuild_milestones()

        if ctl and ctl.milestones:
            for m in ctl.milestones:
                detail_state["milestones"].append({
                    "date_ref": {"value": m.date}, "note": m.note, "is_done": m.is_done,
                })
        _rebuild_milestones()

        # ── Attachments ──────────────────────────────────────────
        attach_col = ft.Column(spacing=4)

        def _rebuild_attach():
            attach_col.controls.clear()
            for rel in detail_state["attachments"]:
                filename = rel.split("/")[-1]
                icon = (ft.icons.PICTURE_AS_PDF if filename.lower().endswith(".pdf")
                        else ft.icons.IMAGE_OUTLINED if filename.lower().endswith((".png", ".jpg", ".jpeg"))
                        else ft.icons.DESCRIPTION_OUTLINED)
                attach_col.controls.append(
                    ft.Container(
                        content=ft.Row(controls=[
                            ft.Icon(icon, size=14, color=GLASS["accent"]),
                            ft.Text(filename, size=11, color=GLASS["text"], expand=True, no_wrap=True,
                                    overflow=ft.TextOverflow.ELLIPSIS, tooltip=filename),
                            ft.IconButton(icon=ft.icons.OPEN_IN_NEW, icon_size=14, icon_color=GLASS["accent"],
                                          tooltip="\u041e\u0442\u043a\u0440\u044b\u0442\u044c",
                                          on_click=lambda e, r=rel: _open_attach(r)),
                            ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=14, icon_color=GLASS["overdue"],
                                          tooltip="\u0423\u0434\u0430\u043b\u0438\u0442\u044c",
                                          on_click=lambda e, r=rel: _confirm_remove_attach(r)),
                        ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor=GLASS["surface"],
                        border=ft.border.all(1, GLASS["border"]), border_radius=_RADIUS,
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
                show_error_toast(page, "\u0424\u0430\u0439\u043b \u0432\u043b\u043e\u0436\u0435\u043d\u0438\u044f \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d")
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
                title=ft.Text("\u0423\u0434\u0430\u043b\u0435\u043d\u0438\u0435 \u0432\u043b\u043e\u0436\u0435\u043d\u0438\u044f", size=14, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
                content=ft.Text("\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u0444\u0430\u0439\u043b \u0432\u043b\u043e\u0436\u0435\u043d\u0438\u044f?", size=12, color=GLASS["text"]),
                actions=[
                    ft.TextButton("\u041e\u0442\u043c\u0435\u043d\u0430", on_click=_cancel),
                    ft.ElevatedButton("\u0423\u0434\u0430\u043b\u0438\u0442\u044c", bgcolor=GLASS["overdue"], color="white", on_click=_confirm),
                ],
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
                    sz = os.path.getsize(fpath) / (1024 * 1024)
                    if sz > ATTACHMENT_WARN_MB:
                        from ui.toast import show_toast
                        show_toast(page, f"\u0424\u0430\u0439\u043b > 20 \u041c\u0411: {fobj.name}", icon=ft.icons.WARNING_AMBER)
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
                show_toast(page, f"\u041f\u0440\u0438\u043a\u0440\u0435\u043f\u043b\u0435\u043d\u043e: {len(added)}", icon=ft.icons.ATTACH_FILE)

        try:
            page._controls_attach_picker.on_result = _on_attach_picked
        except Exception:
            pass

        def _pick_attach(e=None):
            try:
                page._controls_attach_picker.pick_files(
                    dialog_title="\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u0441\u043a\u0430\u043d\u044b \u0437\u0430\u0434\u0430\u043d\u0438\u044f",
                    allowed_extensions=["pdf", "png", "jpg", "jpeg"],
                    allow_multiple=True,
                )
            except Exception as ex:
                print(f"[CONTROLS_TAB] pick attach error: {ex}")

        _rebuild_attach()

        # ── Save / Delete actions ────────────────────────────────
        def _save_detail(e=None):
            inc = (incoming_field.value or "").strip()
            if not inc:
                try:
                    incoming_field.error_text = "\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u0432\u0445\u043e\u0434\u044f\u0449\u0438\u0439 \u043d\u043e\u043c\u0435\u0440"
                    incoming_field.update()
                except Exception:
                    pass
                return
            if not detail_state["receive_date"]:
                return
            execs = exec_container._get_selected() if hasattr(exec_container, "_get_selected") else []

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
            show_toast(page, "\u0421\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043e", icon=ft.icons.SAVE)
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
                    show_toast(page, f"\u0412 \u0430\u0440\u0445\u0438\u0432: {ctl.incoming_number}", icon=ft.icons.ARCHIVE)
                except Exception:
                    traceback.print_exc()

            def _cancel(e=None):
                try:
                    page.close(dlg)
                except Exception:
                    pass

            dlg = ft.AlertDialog(
                modal=True, bgcolor=GLASS["surface_solid"],
                title=ft.Text("\u041f\u0435\u0440\u0435\u043c\u0435\u0441\u0442\u0438\u0442\u044c \u0432 \u0430\u0440\u0445\u0438\u0432", size=14, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
                content=ft.Text(f"\u041f\u0435\u0440\u0435\u043c\u0435\u0441\u0442\u0438\u0442\u044c \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u044c \u00ab{ctl.incoming_number}\u00bb \u0432 \u0430\u0440\u0445\u0438\u0432?", size=12, color=GLASS["text"]),
                actions=[ft.TextButton("\u041e\u0442\u043c\u0435\u043d\u0430", on_click=_cancel),
                         ft.ElevatedButton("\u0412 \u0430\u0440\u0445\u0438\u0432", bgcolor=GLASS["accent"], color="white", on_click=_confirm)],
                shape=ft.RoundedRectangleBorder(radius=14),
            )
            page.open(dlg)

        # Section headers (glass-styled)
        def _section_header(title, icon, btn_text=None, btn_handler=None):
            controls = [
                ft.Icon(icon, size=16, color=GLASS["text"]),
                ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
                ft.Container(expand=True),
            ]
            if btn_text:
                controls.append(ghost_button(btn_text, btn_handler, compact=True, height=30))
            return ft.Row(controls=controls, spacing=6, tight=True,
                         vertical_alignment=ft.CrossAxisAlignment.CENTER)

        tasks_header = _section_header("\u041f\u0443\u043d\u043a\u0442\u044b \u0437\u0430\u0434\u0430\u043d\u0438\u044f", ft.icons.FORMAT_LIST_BULLETED,
                                       "+ \u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043f\u0443\u043d\u043a\u0442", _add_task)
        milestones_header = _section_header("\u041f\u0440\u043e\u043c\u0435\u0436\u0443\u0442\u043e\u0447\u043d\u044b\u0435 \u0442\u043e\u0447\u043a\u0438", ft.icons.TIMELINE,
                                            "+ \u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0442\u043e\u0447\u043a\u0443", _add_milestone)
        milestones_header.visible = (ctl.control_type if ctl else ONE_TIME) == PERIODIC
        attach_header = _section_header("\u0421\u043a\u0430\u043d \u0437\u0430\u0434\u0430\u043d\u0438\u044f", ft.icons.ATTACH_FILE,
                                        "\u041f\u0440\u0438\u043a\u0440\u0435\u043f\u0438\u0442\u044c \u0444\u0430\u0439\u043b", _pick_attach)

        detail_content = ft.Column(controls=[
            # Title row
            ft.Row(controls=[
                ft.Icon(ft.icons.EDIT_DOCUMENT if not is_new else ft.icons.ADD_CIRCLE_OUTLINE,
                        size=20, color=GLASS["text"]),
                ft.Text("\u041a\u0430\u0440\u0442\u043e\u0447\u043a\u0430 \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u044f" if not is_new else "\u041d\u043e\u0432\u044b\u0439 \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u044c",
                        size=17, weight=ft.FontWeight.BOLD, color=GLASS["text"], expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_color=GLASS["text_secondary"],
                              icon_size=18, on_click=_hide_detail),
            ], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Divider(height=1, color=GLASS["border"]),
            # Row 1: incoming + receive
            ft.Row(controls=[incoming_field, receive_cal],
                   spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            # Row 2: initiator + add custom
            ft.Row(controls=[init_dd, new_init_field, add_init_btn],
                   spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            content_field,
            exec_container,
            # Row 3: controller, type, period
            ft.Row(controls=[controller_dd, type_dd, period_dd, custom_days_field],
                   spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            # Row 4: due + end
            ft.Row(controls=[due_cal, end_cal],
                   spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            cycle_hint,
            comment_field,
            ft.Container(height=4),
            tasks_header, tasks_col,
            ft.Container(height=4),
            milestones_header, milestones_col,
            ft.Container(height=4),
            attach_header, attach_col,
            ft.Container(height=12),
            # Bottom buttons
            ft.Row(controls=[
                ft.ElevatedButton("\u0423\u0434\u0430\u043b\u0438\u0442\u044c", icon=ft.icons.DELETE_FOREVER,
                                  bgcolor=GLASS["overdue"], color="white",
                                  visible=not is_new, on_click=_delete_detail) if not is_new else ft.Container(),
                ft.Container(expand=True),
                ghost_button("\u041e\u0442\u043c\u0435\u043d\u0430", _hide_detail),
                glass_button("\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c", _save_detail,
                              icon=ft.icons.SAVE),
            ], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
               alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ], spacing=8, tight=True, scroll=ft.ScrollMode.AUTO, expand=True)

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

    # ── Actions for rows ─────────────────────────────────────────
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
                show_toast(page, "\u041f\u043e\u0441\u0442\u043e\u044f\u043d\u043d\u044b\u0439 \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u044c \u0437\u0430\u0432\u0435\u0440\u0448\u0451\u043d (\u043a\u043e\u043d\u0435\u0447\u043d\u0430\u044f \u0434\u0430\u0442\u0430)", icon=ft.icons.CHECK_CIRCLE)
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
                show_toast(page, f"\u0421\u0440\u043e\u043a \u043f\u0440\u043e\u0434\u043b\u0451\u043d \u0434\u043e {_display_date(ctl.due_date)}", icon=ft.icons.UPDATE)
        else:
            ctl.done = True
            ctl.done_date = today.isoformat()
            ctl.updated_at = datetime.now().isoformat()
            archive_control(ctl, ARCHIVE_DONE)
            _persist(state["controls"])
            from ui.toast import show_toast
            show_toast(page, "\u041a\u043e\u043d\u0442\u0440\u043e\u043b\u044c \u0438\u0441\u043f\u043e\u043b\u043d\u0435\u043d \u0438 \u043f\u0435\u0440\u0435\u043c\u0435\u0449\u0451\u043d \u0432 \u0430\u0440\u0445\u0438\u0432", icon=ft.icons.CHECK_CIRCLE)
        _rebuild_table()
        _refresh_counters()

    def _extend(ctl: Control):
        try:
            _do_extend(ctl)
        except Exception:
            traceback.print_exc()

    def _do_extend(ctl: Control):
        extend_days = {"value": str(ctl.period_days if ctl.control_type == PERIODIC else 7)}
        days_field = _inset_field(
            value=extend_days["value"], hint="\u041f\u0440\u043e\u0434\u043b\u0438\u0442\u044c \u043d\u0430 (\u0434\u043d\u0435\u0439)",
            width=160, height=40)

        def _confirm(e=None):
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
            show_toast(page, f"\u0421\u0440\u043e\u043a \u043f\u0440\u043e\u0434\u043b\u0451\u043d \u0434\u043e {_display_date(ctl.due_date)}", icon=ft.icons.UPDATE)

        def _close(e=None):
            try:
                page.close(dialog)
            except Exception:
                pass

        dialog = ft.AlertDialog(
            modal=True, bgcolor=GLASS["surface_solid"],
            title=ft.Text("\u041f\u0440\u043e\u0434\u043b\u0438\u0442\u044c \u0441\u0440\u043e\u043a", size=16, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
            content=ft.Container(content=days_field, width=220),
            actions=[ft.TextButton("\u041e\u0442\u043c\u0435\u043d\u0430", on_click=_close),
                     glass_button("\u041f\u0440\u043e\u0434\u043b\u0438\u0442\u044c", _confirm)],
            actions_alignment=ft.MainAxisAlignment.END,
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
                show_toast(page, f"\u0412 \u0430\u0440\u0445\u0438\u0432: {ctl.incoming_number}", icon=ft.icons.ARCHIVE)
            except Exception:
                traceback.print_exc()
        def _close(e=None):
            try:
                page.close(dialog)
            except Exception:
                pass
        dialog = ft.AlertDialog(
            modal=True, bgcolor=GLASS["surface_solid"],
            title=ft.Text("\u041f\u0435\u0440\u0435\u043c\u0435\u0441\u0442\u0438\u0442\u044c \u0432 \u0430\u0440\u0445\u0438\u0432", size=16, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
            content=ft.Text(f"\u041f\u0435\u0440\u0435\u043c\u0435\u0441\u0442\u0438\u0442\u044c \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u044c \u00ab{ctl.incoming_number}\u00bb \u0432 \u0430\u0440\u0445\u0438\u0432?", size=13, color=GLASS["text"]),
            actions=[ft.TextButton("\u041e\u0442\u043c\u0435\u043d\u0430", on_click=_close),
                     ft.ElevatedButton("\u0412 \u0430\u0440\u0445\u0438\u0432", icon=ft.icons.ARCHIVE, bgcolor=GLASS["accent"], color="white", on_click=_confirm)],
            actions_alignment=ft.MainAxisAlignment.END,
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
            show_toast(page, "\u041a\u043e\u043d\u0442\u0440\u043e\u043b\u044c \u0432\u043e\u0441\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d", icon=ft.icons.RESTORE)
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
                show_toast(page, "\u0423\u0434\u0430\u043b\u0451\u043d \u043d\u0430\u0432\u0441\u0435\u0433\u0434\u0430", icon=ft.icons.DELETE_FOREVER)
            except Exception:
                traceback.print_exc()
        def _close(e=None):
            try:
                page.close(dialog)
            except Exception:
                pass
        dialog = ft.AlertDialog(
            modal=True, bgcolor=GLASS["surface_solid"],
            title=ft.Text("\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u043d\u0430\u0432\u0441\u0435\u0433\u0434\u0430", size=16, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
            content=ft.Text(f"\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u00ab{ctl.incoming_number}\u00bb \u0431\u0435\u0437\u0432\u043e\u0437\u0432\u0440\u0430\u0442\u043d\u043e? \u0412\u043b\u043e\u0436\u0435\u043d\u0438\u044f \u0442\u0430\u043a\u0436\u0435 \u0431\u0443\u0434\u0443\u0442 \u0443\u0434\u0430\u043b\u0435\u043d\u044b.", size=13, color=GLASS["text"]),
            actions=[ft.TextButton("\u041e\u0442\u043c\u0435\u043d\u0430", on_click=_close),
                     ft.ElevatedButton("\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u043d\u0430\u0432\u0441\u0435\u0433\u0434\u0430", icon=ft.icons.DELETE_FOREVER, bgcolor=GLASS["overdue"], color="white", on_click=_confirm)],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=14),
        )
        page.open(dialog)

    # ── Export / Import ───────────────────────────────────────────
    export_mode_dd = _mk_glass_dd("\u0420\u0435\u0436\u0438\u043c \u044d\u043a\u0441\u043f\u043e\u0440\u0442\u0430", 170, [
        ft.dropdown.Option("table", "\u041a\u0430\u043a \u0432 \u0442\u0430\u0431\u043b\u0438\u0446\u0435"),
        ft.dropdown.Option("full", "\u041f\u043e\u043b\u043d\u044b\u0439 (round-trip)"),
    ])

    def _on_export_picked(e: ft.FilePickerResultEvent):
        if not getattr(e, "path", None):
            return
        try:
            mode = (export_mode_dd.value or "table") == "full"
            ControlsExcelExporter().export(_visible_base(), e.path, soon_days, full=mode)
            from ui.toast import show_export_toast
            show_export_toast(page, "\u041a\u043e\u043d\u0442\u0440\u043e\u043b\u0438 Excel")
        except Exception as ex:
            print(f"[CONTROLS_TAB] Export error: {ex}")
            from ui.toast import show_error_toast
            show_error_toast(page, f"\u041e\u0448\u0438\u0431\u043a\u0430 \u044d\u043a\u0441\u043f\u043e\u0440\u0442\u0430: {ex}")

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

    try:
        page._controls_file_picker.on_result = _on_export_picked
    except Exception:
        pass
    try:
        page._controls_import_picker.on_result = _on_import_picked
    except Exception:
        pass

    def _export(e=None):
        try:
            page._controls_file_picker.save_file(
                dialog_title="\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u0438 \u0432 Excel",
                file_name=f"controls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                allowed_extensions=["xlsx"],
            )
        except Exception as ex:
            print(f"[CONTROLS_TAB] export trigger error: {ex}")

    def _import(e=None):
        try:
            page._controls_import_picker.pick_files(
                dialog_title="\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u0444\u0430\u0439\u043b Excel \u0434\u043b\u044f \u0438\u043c\u043f\u043e\u0440\u0442\u0430",
                allowed_extensions=["xlsx"],
                allow_multiple=False,
            )
        except Exception as ex:
            print(f"[CONTROLS_TAB] import trigger error: {ex}")

    def _preview_import(path: str):
        from ui.toast import show_error_toast
        parsed, stats = import_from_excel(path, state["controls"])
        if not parsed and stats["errors"] == 0:
            show_error_toast(page, "\u041d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e \u043d\u0438 \u043e\u0434\u043d\u043e\u0433\u043e \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u044f \u0432 \u0444\u0430\u0439\u043b\u0435")
            return
        preview_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=300)
        for c in parsed[:20]:
            preview_list.controls.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Text(c.incoming_number or "\u2014", size=11, color=GLASS["text_secondary"], width=90, no_wrap=True),
                        ft.Text(c.content or "\u2014", size=11, color=GLASS["text"], expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, tooltip=c.content),
                        ft.Text(_type_label(c), size=10, color=GLASS["text_secondary"], width=80, no_wrap=True),
                    ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=GLASS["surface"], border=ft.border.all(1, GLASS["border"]), border_radius=6,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                )
            )
        if len(parsed) > 20:
            preview_list.controls.append(ft.Text(f"\u2026 \u0438 \u0435\u0449\u0451 {len(parsed) - 20}", size=10, color=GLASS["text_muted"]))
        summary = ft.Text(
            f"\u041d\u0430\u0439\u0434\u0435\u043d\u043e: {len(parsed) + stats['skipped']} \u00b7 \u0418\u043c\u043f\u043e\u0440\u0442\u0438\u0440\u0443\u0435\u043c\u043e: {len(parsed)} \u00b7 \u041f\u0440\u043e\u043f\u0443\u0449\u0435\u043d\u043e: {stats['skipped']} \u00b7 \u041e\u0448\u0438\u0431\u043e\u043a: {stats['errors']}",
            size=11, color=GLASS["text_secondary"])

        def _confirm(e=None):
            try:
                for c in parsed:
                    state["controls"].append(c)
                _persist(state["controls"])
                page.close(dialog)
                _rebuild_table()
                _refresh_counters()
                from ui.toast import show_toast
                show_toast(page, f"\u0418\u043c\u043f\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u043e: {len(parsed)}", icon=ft.icons.CLOUD_DOWNLOAD)
            except Exception:
                traceback.print_exc()

        def _close(e=None):
            try:
                page.close(dialog)
            except Exception:
                pass

        dialog = ft.AlertDialog(
            modal=True, bgcolor=GLASS["surface_solid"],
            title=ft.Row(controls=[
                ft.Icon(ft.icons.UPLOAD_FILE, size=20, color=GLASS["text"]),
                ft.Text("\u0418\u043c\u043f\u043e\u0440\u0442 \u0438\u0437 Excel \u2014 \u043f\u0440\u0435\u0434\u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440", size=15, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            content=ft.Container(width=560, content=ft.Column(controls=[summary, preview_list], spacing=8, tight=True)),
            actions=[ft.TextButton("\u041e\u0442\u043c\u0435\u043d\u0430", on_click=_close),
                     glass_button("\u0418\u043c\u043f\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c", _confirm, icon=ft.icons.CLOUD_DOWNLOAD)],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=14),
        )
        page.open(dialog)

    # ── Settings ─────────────────────────────────────────────────
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
                initiator_filter_dd.options = [ft.dropdown.Option("all", "\u0412\u0441\u0435 \u0438\u043d\u0438\u0446\u0438\u0430\u0442\u043e\u0440\u044b")] + [ft.dropdown.Option(i) for i in initiators]
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

    # ── Toolbar (Glass Dark) ─────────────────────────────────────
    add_btn = glass_button("\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u044c", _add_control,
                            icon=ft.icons.ADD_CIRCLE_OUTLINE)
    import_btn = ghost_button("\u0418\u043c\u043f\u043e\u0440\u0442 Excel", _import, icon=ft.icons.UPLOAD_FILE)
    export_btn = ft.ElevatedButton(
        text="\u042d\u043a\u0441\u043f\u043e\u0440\u0442 Excel", icon=ft.icons.FILE_DOWNLOAD_OUTLINED,
        bgcolor=GLASS["btn_green"], color=GLASS["btn_green_text"], height=40,
        icon_color=GLASS["btn_green_text"],
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=_RADIUS),
            padding=ft.padding.symmetric(horizontal=16)),
        on_click=_export,
    )
    settings_btn = ft.IconButton(
        icon=ft.icons.SETTINGS_OUTLINED, icon_size=20, icon_color=GLASS["text_secondary"],
        tooltip="\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u0435\u0439",
        style=ft.ButtonStyle(bgcolor=GLASS["surface"], shape=ft.RoundedRectangleBorder(radius=_RADIUS),
                             padding=ft.padding.all(8)),
        on_click=_open_settings,
    )

    # ── Title row (glass panel) ──────────────────────────────────
    title_row = glass_panel(
        ft.Row(controls=[
            ft.Icon(ft.icons.RULE_FOLDER, size=18, color=GLASS["text"]),
            ft.Text("\u041a\u043e\u043d\u0442\u0440\u043e\u043b\u0438", size=20, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
            ft.Container(width=8), sync_dot, ft.Container(width=4), sync_label,
            ft.Container(expand=True),
            add_btn, import_btn, export_mode_dd, export_btn, settings_btn,
        ], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.START),
        padding=10, radius=_RADIUS_PANEL,
    )
    title_row.height = 54

    # ── Main Column ──────────────────────────────────────────────
    main_column = ft.Column(
        controls=[
            title_row,
            ft.Container(height=6),
            filter_row1,
            ft.Container(height=6),
            filter_row2,
            ft.Container(height=6),
            # Counters + Mode switch row
            glass_panel(
                ft.Row(controls=[
                    counters_row,
                    ft.Container(expand=True),
                    mode_row,
                ], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=6, radius=_RADIUS_PANEL,
            ),
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
            ft.Container(content=main_column, expand=True,
                         padding=ft.padding.only(left=12, right=12, top=8, bottom=8)),
            detail_overlay,
        ],
        expand=True,
    )

    tab_content = ft.Column(
        controls=[
            ft.Container(content=tab_stack, expand=True, bgcolor=GLASS["bg_tab"]),
        ],
        spacing=0,
        expand=True,
    )

    # ── Background polling ───────────────────────────────────────
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
                parts = [f"\u041f\u0440\u043e\u0441\u0440\u043e\u0447\u0435\u043d\u043e: {len(overdue)}"]
                if today_n:
                    parts.append(f"\u0421\u0435\u0433\u043e\u0434\u043d\u044f \u0438\u0441\u0442\u0435\u043a\u0430\u0435\u0442: {len(today_n)}")
                if soon:
                    parts.append(f"\u0421\u043a\u043e\u0440\u043e: {len(soon)}")
                show_toast(page, " \u00b7 ".join(parts), icon=ft.icons.NOTIFICATIONS_ACTIVE)
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
                parts.append(f"\u041f\u0440\u043e\u0441\u0440\u043e\u0447\u0435\u043d\u043e: {len(overdue0)}")
            if today0:
                parts.append(f"\u0421\u0435\u0433\u043e\u0434\u043d\u044f \u0438\u0441\u0442\u0435\u043a\u0430\u0435\u0442: {len(today0)}")
            if soon0:
                parts.append(f"\u0421\u043a\u043e\u0440\u043e: {len(soon0)}")
            show_toast(page, " \u00b7 ".join(parts), icon=ft.icons.NOTIFICATIONS_ACTIVE)
        state["last_overdue"] = len(overdue0)
    except Exception:
        pass

    page._controls_poll_stop = _poll_stop
    print("[CONTROLS_TAB] Controls tab created (Glass Dark redesign)")
    return tab_content

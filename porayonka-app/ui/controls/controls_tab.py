# ui/controls/controls_tab.py
# Glass Dark redesign — доработка таблицы + ПОЛНЫЙ редизайн карточки (2 колонки, календарь без клипа)
import threading
import time
import traceback
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict
from uuid import uuid4
import calendar as cal_module

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
from .glass_theme import GLASS, with_alpha, glass_panel
from .russian_calendar import create_russian_date_field, create_russian_calendar_expanded

STATUS_ICONS = {
    OVERDUE: ft.icons.EVENT_BUSY,
    TODAY: ft.icons.STAR,
    SOON: ft.icons.HOURGLASS_BOTTOM,
    IN_PROGRESS: ft.icons.HOURGLASS_TOP,
    DONE: ft.icons.CHECK_CIRCLE,
    COMPLETED: ft.icons.CHECK_CIRCLE_OUTLINE,
    NO_DATE: ft.icons.REMOVE_CIRCLE_OUTLINE,
}

def _safe_update(control):
    """Вызвать control.update() только если контрол смонтирован в page.
    Убирает шум 'AssertionError: Control must be added to the page first.'
    при инициализации, когда контролы ещё не добавлены в дерево page."""
    try:
        if control is not None and getattr(control, "page", None) is not None:
            control.update()
    except Exception:
        traceback.print_exc()


_FIXED = {
    "bar": 4,
    "num": 36,
    "incoming": 165,
    "receive": 90,
    "initiator": 120,
    "controller": 120,
    "type": 80,
    "due": 100,
    "status": 120,
    "actions": 110,  # 2 иконки + воздух, фикс 110 чтобы ДЕЙСТВИЯ помещалось
}
_ROW_HEIGHT = 56
_TAB_HORIZONTAL_PADDING = 40
_ROW_SPACING = 6
_ROW_EXTRA = 30  # spacing 2*11 + padding 8 for total row width calc

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
            traceback.print_exc()
    else:
        try:
            getattr(page, attr).on_result = on_result
        except Exception:
            traceback.print_exc()
    return getattr(page, attr)

def _glass_textfield(value="", hint="", width=None, expand=False, multiline=False, min_lines=1, max_lines=4, read_only=False, dense=True):
    return ft.TextField(
        value=value,
        hint_text=hint,
        width=width,
        expand=expand,
        multiline=multiline,
        min_lines=min_lines if multiline else None,
        max_lines=max_lines if multiline else None,
        read_only=read_only,
        dense=dense,
        border_radius=10,
        border_color=GLASS["border"],
        focused_border_color=GLASS["accent"],
        bgcolor=GLASS["surface_alt"],
        color=GLASS["text"],
        hint_style=ft.TextStyle(color=GLASS["text_muted"], size=12),
        text_style=ft.TextStyle(size=13, color=GLASS["text"]),
        content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
    )

def _glass_dropdown(hint, width, options, value="all"):
    return ft.Dropdown(
        hint_text=hint,
        width=width,
        height=38,
        value=value,
        options=options,
        border_radius=10,
        border_color=GLASS["border"],
        focused_border_color=GLASS["accent"],
        bgcolor=GLASS["surface_alt"],
        color=GLASS["text"],
        hint_style=ft.TextStyle(color=GLASS["text_muted"], size=12),
        text_style=ft.TextStyle(size=13, color=GLASS["text"]),
        dense=True,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=6),
    )

def _field_with_label(label: str, control):
    return ft.Column(
        controls=[
            ft.Text(label, size=11, color=GLASS["text_secondary"], weight=ft.FontWeight.W_500),
            control,
        ],
        spacing=4,
        tight=True,
    )

def create_controls_tab(page: ft.Page) -> ft.Column:
    print("[CONTROLS_TAB] Glass Dark v2 - init")
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

    rows_column = ft.Column(spacing=6, tight=True)  # Bug 2: gap 6px между плашками
    sync_label = ft.Text("Локально", size=11, color=GLASS["text_secondary"])
    sync_dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=GLASS["text_muted"])

    def _layout_widths(width: Optional[float]) -> Dict[str, int]:
        # Fix Bug 1: сумма ширин не должна превышать доступную, учитывать spacing+padding строки
        if not width or width <= 0:
            width = 1280
        available = max(400.0, width - _TAB_HORIZONTAL_PADDING)
        available_for_controls = max(300.0, available - _ROW_EXTRA)  # вычитаем spacing+padding строки
        fixed_sum = sum(_FIXED.values())
        flex = max(200.0, available_for_controls - fixed_sum)
        w = dict(_FIXED)
        w["executors"] = int(flex * 0.35)
        w["content"] = int(flex - w["executors"])
        # Проверка что заголовок ДЕЙСТВИЯ помещается: actions >=110 должен вместить 8 букв size11 bold
        return w
    _W = _layout_widths(page.width)
    # Bug 2.6: подхватить сохраненные ширины колонок из settings
    try:
        saved_widths = settings.get("col_widths") or {}
        for k, v in saved_widths.items():
            if k in _W:
                _W[k] = max(60, int(v))
    except Exception:
        traceback.print_exc()

    def _save_col_widths():
        try:
            settings["col_widths"] = dict(_W)
            save_settings(settings)
        except Exception:
            traceback.print_exc()

    # Persistence
    def _persist(controls: List[Control], to_shared: bool = True):
        save_controls(controls)
        state["last_sync"] = datetime.now()
        if settings.get("network_enabled") and to_shared:
            ok = write_shared_controls(controls, settings)
            state["network_ok"] = bool(ok)
            try:
                state["shared_mtime"] = get_shared_mtime(settings)
            except Exception:
                traceback.print_exc()
        _update_sync_ui()
        _refresh_filter_options()

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
                traceback.print_exc()
            for c in state["controls"]:
                try:
                    sync_attachments_from_shared(c.id, c.attachments, settings)
                except Exception:
                    traceback.print_exc()
        else:
            state["controls"] = load_controls()
        _update_sync_ui()
        _refresh_filter_options()

    def _update_sync_ui():
        net = settings.get("network_enabled")
        if not net:
            sync_label.value = "Локально"
            sync_dot.bgcolor = GLASS["text_muted"]
        else:
            role = "админ" if network_role == "admin" else "пользователь"
            sync_label.value = f"Сеть: {role}"
            sync_dot.bgcolor = GLASS["in_progress"] if state["network_ok"] else GLASS["overdue"]
            if state["last_sync"]:
                sync_label.value += f" · {state['last_sync'].strftime('%H:%M:%S')}"
        try:
            _safe_update(sync_label)
            _safe_update(sync_dot)
        except Exception:
            traceback.print_exc()

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

    def _norm(s: str) -> str:
        return (s or "").strip().casefold()

    def _filtered() -> List[Control]:
        base = _visible_base()
        q = state["search"].lower().strip()
        def _match(ctl: Control) -> bool:
            if state["f_status"] != "all" and deadline_status(ctl, soon_days) != state["f_status"]:
                return False
            if state["f_type"] != "all" and ctl.control_type != state["f_type"]:
                return False
            # Bug 5: нормализация ФИО (пробелы/ё/регистр)
            if state["f_initiator"] != "all" and _norm(state["f_initiator"]) != _norm(ctl.initiator):
                # allow exact normalized match
                if _norm(state["f_initiator"]) != _norm(ctl.initiator):
                    return False
            if state["f_controller"] != "all":
                if not any(_norm(state["f_controller"]) == _norm(c) for c in [ctl.controller]):
                    return False
            if state["f_executor"] != "all":
                norm_filter = _norm(state["f_executor"])
                if not any(_norm(ex) == norm_filter for ex in ctl.executors):
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
                hay = " ".join([ctl.incoming_number, ctl.content, ctl.initiator, ctl.controller, ctl.due_date or "", " ".join(ctl.executors), " ".join(t.title for t in ctl.tasks)]).lower()
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
                order = {OVERDUE:0, TODAY:1, SOON:2, IN_PROGRESS:3, NO_DATE:4, DONE:5, COMPLETED:6}
                return (order.get(deadline_status(ctl, soon_days),9),)
            d = effective_due_date(ctl)
            return (d.toordinal() if d else 999999,)
        result.sort(key=_sort_val, reverse=state["sort_reverse"])
        # Bug 2.5: исполненные вниз — стабильное разбиение: сначала не исполненные, потом исполненные
        if state["mode"] != "archive":
            not_done = [c for c in result if not c.done]
            done = [c for c in result if c.done]
            result = not_done + done
        return result

    def _apply_filters():
        _rebuild_table()

    # UI helpers — Bug 2.4: max_lines=2, LEFT, padding vertical 8, height по контенту min 56
    def _cell(text: str, width: int, color=GLASS["text"], size=13, bold=False, center=False, tooltip=None, max_lines=2):
        return ft.Container(
            content=ft.Text(text, size=size, color=color, weight=ft.FontWeight.W_600 if bold else None, no_wrap=not center, max_lines=max_lines, overflow=ft.TextOverflow.ELLIPSIS, tooltip=tooltip or (text if len(text)>20 else None)),
            width=width, padding=ft.padding.only(left=6, right=4),
            alignment=ft.alignment.center if center else ft.alignment.center_left,
        )

    def _action_icon(icon, color, tooltip, handler, size=18):
        return ft.IconButton(icon=icon, icon_size=size, icon_color=color, tooltip=tooltip, width=30, height=30, padding=0, on_click=handler)

    # Header
    header_row = ft.Container(
        content=ft.Row(controls=[], spacing=2, tight=True),
        height=34,
        bgcolor="transparent",
        border=ft.border.only(bottom=ft.BorderSide(1, GLASS["border_divider"])),
        padding=ft.padding.symmetric(horizontal=4, vertical=2),
    )

    def _header_cell(text: str, width: int, key: str, center=False):
        arrow = "▲" if (state["sort_key"]==key and not state["sort_reverse"]) else ("▼" if (state["sort_key"]==key and state["sort_reverse"]) else "")
        lbl = f"{text} {arrow}".strip().upper()
        # Text part
        text_cont = ft.Container(
            content=ft.Text(lbl, size=11, weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"], no_wrap=True, tooltip="Сортировка"),
            width=max(20, width-10),
            padding=ft.padding.only(left=6, right=4),
            alignment=ft.alignment.center if center else ft.alignment.center_left,
            on_click=lambda e, k=key: _sort_by(k),
        )
        # Drag handle Bug 2.6: GestureDetector 8px width, hover #4f8cff
        def _make_drag(k):
            def _on_drag(e):
                try:
                    # e.delta_x may not exist, try primary_delta or local
                    delta = 0
                    try:
                        delta = int(getattr(e, 'delta_x', 0) or getattr(e, 'primary_delta', 0) or getattr(e, 'dx', 0) or 0)
                    except Exception:
                        delta = 0
                    # If delta is 0, try to estimate from local? fallback small step
                    if delta == 0:
                        # no delta info, ignore
                        return
                    old = _W.get(k, width)
                    new = max(60, old + delta)
                    # Rubber content logic
                    if k not in ("content", "executors", "actions"):
                        delta_actual = new - old
                        content_old = _W.get("content", 100)
                        content_new = max(60, content_old - delta_actual)
                        if content_new < 60:
                            # clamp
                            delta_actual = content_old - 60
                            new = old + delta_actual
                            content_new = 60
                        _W[k] = new
                        _W["content"] = content_new
                    else:
                        _W[k] = new
                    _rebuild_header()
                    _rebuild_table()
                    _save_col_widths()
                except Exception:
                    traceback.print_exc()
            return _on_drag

        drag_handle = ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.RESIZE_LEFT_RIGHT,
            on_horizontal_drag_update=_make_drag(key),
            content=ft.Container(
                width=8,
                height=34,
                bgcolor="transparent",
                border_radius=2,
            ),
        )
        # Hover highlight for handle
        def _on_hover(e):
            try:
                cont = e.control.content
                if e.data == "true":
                    cont.bgcolor = with_alpha(GLASS["accent"], "44")
                else:
                    cont.bgcolor = "transparent"
                _safe_update(cont)
            except Exception:
                traceback.print_exc()

        drag_handle.on_hover = _on_hover

        # Combine text + handle in Row tight
        return ft.Container(
            width=width,
            content=ft.Row(
                controls=[text_cont, drag_handle],
                spacing=0,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _sort_by(key: str):
        if state["sort_key"] == key:
            state["sort_reverse"] = not state["sort_reverse"]
        else:
            state["sort_key"] = key
            state["sort_reverse"] = False
        _rebuild_table()
        _rebuild_header()

    def _rebuild_header():
        is_archive = state["mode"] == "archive"
        controls = [
            ft.Container(width=_W["bar"]),
            _header_cell("№", _W["num"], "num", center=True),
            _header_cell("вх. №", _W["incoming"], "incoming"),
            _header_cell("Дата пост.", _W["receive"], "receive"),
            _header_cell("Инициатор", _W["initiator"], "initiator"),
            ft.Container(width=_W["content"], padding=ft.padding.only(left=6, right=4), content=ft.Text("СОДЕРЖАНИЕ", size=11, weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"], no_wrap=True)),
            ft.Container(width=_W["executors"], padding=ft.padding.only(left=6, right=4), content=ft.Text("ИСПОЛНИТЕЛИ", size=11, weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"], no_wrap=True)),
            ft.Container(width=_W["controller"], padding=ft.padding.only(left=6, right=4), content=ft.Text("ЗА КЕМ", size=11, weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"], no_wrap=True)),
            _header_cell("Причина" if is_archive else "Тип", _W["type"], "type"),
            _header_cell("Срок исполн.", _W["due"], "due"),
            ft.Container(width=_W["status"], padding=ft.padding.only(left=6, right=4), content=ft.Text("СТАТУС", size=11, weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"], no_wrap=True)),
            _header_cell("Действия", _W["actions"], "actions", center=True),
        ]
        header_row.content = ft.Row(controls=controls, spacing=2, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        try:
            _safe_update(header_row)
        except Exception:
            traceback.print_exc()

    # Row building — Bug 2: плашки, Bug 3: hover, Bug 4: 2 кнопки
    def _build_row(ctl: Control, num: int, index: int) -> ft.Container:
        status = deadline_status(ctl, soon_days)
        color = {
            OVERDUE: GLASS["overdue"],
            TODAY: GLASS["today"],
            SOON: GLASS["soon"],
            IN_PROGRESS: GLASS["in_progress"],
            DONE: GLASS["done"],
            COMPLETED: GLASS["completed"],
            NO_DATE: GLASS["text_muted"],
        }.get(status, GLASS["text_muted"])

        # Bug 2 exact: плашка #2a3247 (нейтральный графит, светлее фона #0a1024), border #0dffffff, gap 6
        # Раунд 6: «Содержание» = content + пункты задания (п.1 Название — Ответственные — дата),
        # перенос до 2 строк, tooltip — полный текст.
        content = ctl.content or ctl.incoming_number
        content_lines = [content]
        if ctl.tasks:
            for t in ctl.tasks:
                line = (t.title or "").strip()
                if not line:
                    continue
                ass = ", ".join(short_name(x) for x in t.assignees) if t.assignees else ""
                if ass:
                    line += " — " + ass
                if t.due_date:
                    line += " — " + _display_date(t.due_date)
                if t.is_done:
                    line += " (исполнено)"
                content_lines.append(line)
        content_text = "\n".join(content_lines)
        content_tooltip = content_text

        content_controls = [_cell(content_text, _W["content"] - (22 if ctl.attachments else 0), tooltip=content_tooltip, max_lines=2, color=GLASS["text"], size=13)]
        if ctl.attachments:
            content_controls.append(ft.Container(
                content=ft.Row(controls=[ft.Icon(ft.icons.ATTACH_FILE, size=12, color=GLASS["accent"]), ft.Text(str(len(ctl.attachments)), size=10, color=GLASS["accent"], no_wrap=True)], spacing=2, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                width=22,
            ))

        is_archive = state["mode"] == "archive"
        type_cell = _cell(_type_label(ctl), _W["type"], color=GLASS["text_secondary"], size=12)
        if is_archive:
            reason = ctl.archive_reason or ""
            reason_text = _reason_label(reason)
            if ctl.archived_at:
                reason_text = f"{reason_text} · {_display_date(ctl.archived_at)}"
            type_cell = _cell(reason_text, _W["type"], color=GLASS["text_secondary"], size=12, tooltip=reason)

        # Bug 4: только 2 кнопки — Редактировать и Удалить (в архив). Галку Исполнено убрать — вводила в заблуждение (выглядела отмеченной у всех)
        actions = []
        if is_archive:
            actions.append(_action_icon(ft.icons.RESTORE, GLASS["in_progress"], "Восстановить", lambda e, c=ctl: _restore(c), size=18))
            actions.append(_action_icon(ft.icons.DELETE_FOREVER, GLASS["overdue"], "Удалить навсегда", lambda e, c=ctl: _delete_forever(c), size=18))
        else:
            actions.append(_action_icon(ft.icons.EDIT_OUTLINED, GLASS["accent"], "Редактировать", lambda e, c=ctl: _open_detail(c), size=18))
            actions.append(_action_icon(ft.icons.DELETE_OUTLINE, GLASS["overdue"], "Удалить (в архив)", lambda e, c=ctl: _confirm_delete(c), size=18))

        eff_due = effective_due_date(ctl)
        due_str = _display_date(eff_due.isoformat() if eff_due else ctl.due_date)
        due_color = color if status in (OVERDUE, TODAY, SOON) else GLASS["text"]
        # Раунд 6: под основной датой — ближайшие неисполненные промежуточные точки (до 2)
        due_tooltip = due_str
        due_controls = [ft.Text(due_str, size=12, color=due_color, weight=ft.FontWeight.W_700, no_wrap=True)]
        if ctl.milestones:
            try:
                pending = [m for m in ctl.milestones if not m.is_done and m.date]
                pending.sort(key=lambda m: parse_date(m.date).toordinal() if parse_date(m.date) else 999999)
            except Exception:
                pending = [m for m in ctl.milestones if not m.is_done and m.date]
            for m in pending[:2]:
                mline = f"точка {_display_date(m.date)}"
                due_controls.append(ft.Text(mline, size=10, color=GLASS["text_secondary"], no_wrap=False,
                                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, tooltip=mline))
                due_tooltip += "\n" + mline
        due_cell = ft.Container(
            content=ft.Column(controls=due_controls, spacing=2, tight=True, alignment=ft.MainAxisAlignment.CENTER),
            width=_W["due"], padding=ft.padding.only(left=6, right=4),
            alignment=ft.alignment.center_left,
            tooltip=due_tooltip,
        )

        row_controls = [
            ft.Container(width=_W["bar"], height=28, bgcolor=color, border_radius=2),
            _cell(str(num), _W["num"], center=True, color=GLASS["text_secondary"], size=12),
            _cell(ctl.incoming_number or "—", _W["incoming"], bold=True, tooltip=ctl.incoming_number, color=GLASS["text"], size=13),
            _cell(_display_date(ctl.receive_date), _W["receive"], color=GLASS["text_secondary"], size=12),
            _cell(short_name(ctl.initiator) if ctl.initiator else "—", _W["initiator"], tooltip=ctl.initiator, color=GLASS["text"], size=12),
            ft.Row(controls=content_controls, spacing=2, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            _cell(", ".join(short_name(x) for x in ctl.executors) or "—", _W["executors"], tooltip=", ".join(ctl.executors), color=GLASS["text"], size=12, max_lines=2),
            _cell(short_name(ctl.controller) if ctl.controller else "—", _W["controller"], tooltip=ctl.controller, color=GLASS["text"], size=12),
            type_cell,
            due_cell,
            ft.Container(
                content=ft.Row(controls=[
                    ft.Icon(STATUS_ICONS.get(status, ft.icons.REMOVE_CIRCLE_OUTLINE), size=12, color=color),
                    ft.Text(STATUS_LABELS.get(status, status), size=11, color=color, weight=ft.FontWeight.W_600, no_wrap=True),
                ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                width=_W["status"], height=26, border_radius=13, padding=ft.padding.symmetric(horizontal=8),
                alignment=ft.alignment.center, bgcolor=with_alpha(color, "22"), border=ft.border.all(1, color),
            ),
            ft.Row(controls=actions, spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
        ]

        # Плашка строки: Bug 2 exact colors — #2a3247, border #0dffffff or none, radius 10, gap 6
        # Bug 2.4: height по контенту min 56, padding vertical 8, max_lines 2
        row = ft.Container(
            content=ft.Row(controls=row_controls, spacing=2, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            # height None — по контенту, min 56 via padding
            bgcolor=GLASS["card"],  # #2a3247
            border=ft.border.all(1, GLASS["border"]),  # #0dffffff
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            on_click=lambda e, c=ctl: _open_detail(c),
            ink=False,
        )
        row.mouse_cursor = ft.MouseCursor.CLICK

        # Раунд 6: hover ВОЗВРАЩЁН и сделан БЫСТРЫМ. Причина лагов раунда 5 — traceback.print_exc()
        # в горячем обработчике (печать traceback в консоль Windows очень медленная -> «через одну»).
        # Теперь абсолютный минимум: рамка акцентная #4f8cff + фон чуть светлее #2c3650.
        # БЕЗ try/except и БЕЗ traceback.print_exc() в этом обработчике (см. AGENTS).
        def _make_hover(cont, orig_bg, orig_border):
            def _hover(e):
                if e.data == "true":
                    cont.bgcolor = GLASS["hover_bg"]          # #2c3650
                    cont.border = ft.border.all(1, GLASS["accent"])  # #4f8cff, 1px та же толщина
                else:
                    cont.bgcolor = orig_bg
                    cont.border = orig_border
                _safe_update(cont)  # молча пропускает немонтированный контрол
            return _hover
        row.on_hover = _make_hover(row, GLASS["card"], ft.border.all(1, GLASS["border"]))
        return row

    def _rebuild_table():
        rows_column.controls.clear()
        visible = _filtered()
        if not visible:
            label = "В архиве пусто" if state["mode"] == "archive" else "Контролей не найдено"
            rows_column.controls.append(ft.Container(
                content=ft.Row(controls=[ft.Icon(ft.icons.INBOX, size=18, color=GLASS["text_muted"]), ft.Text(label, size=12, color=GLASS["text_secondary"])], spacing=8, tight=True),
                height=48, padding=ft.padding.symmetric(horizontal=12, vertical=8),
            ))
            try:
                _safe_update(rows_column)
            except Exception:
                traceback.print_exc()
            return
        for i, ctl in enumerate(visible, 1):
            rows_column.controls.append(_build_row(ctl, i, i-1))
            # Bug 2: gap 6px между плашками, без разделителей-линий — промежуток реализуем spacing колонки
        try:
            _safe_update(rows_column)
        except Exception:
            traceback.print_exc()

    # Counters
    counter_refs: Dict[str, ft.Container] = {}
    def _counts() -> dict:
        res = {"all":0, OVERDUE:0, TODAY:0, SOON:0, IN_PROGRESS:0, DONE:0, COMPLETED:0}
        for ctl in _visible_base():
            res["all"]+=1
            st = deadline_status(ctl, soon_days)
            res[st]=res.get(st,0)+1
        return res

    def _set_status_filter(value: str):
        state["f_status"] = value if state["f_status"] != value else "all"
        _restyle_counters()
        _apply_filters()

    def _restyle_counters():
        for key, btn in counter_refs.items():
            selected = (state["f_status"] == key)
            col = GLASS["accent"] if key=="all" else {OVERDUE:GLASS["overdue"], TODAY:GLASS["today"], SOON:GLASS["soon"], IN_PROGRESS:GLASS["in_progress"], DONE:GLASS["done"]}.get(key, GLASS["text_muted"])
            bg = with_alpha(col, "33") if selected else with_alpha(col, "22")
            border = ft.border.all(1, col if selected else with_alpha(col, "44"))
            btn.bgcolor = bg
            btn.border = border
            try:
                _safe_update(btn)
            except Exception:
                traceback.print_exc()

    def _refresh_counters():
        counts = _counts()
        for key, btn in counter_refs.items():
            try:
                row = btn.content
                row.controls[2].value = str(counts.get(key,0))
            except Exception:
                traceback.print_exc()
        _restyle_counters()

    def _refresh_filter_options():
        # Bug 2.2 & 2.3: options from real data, not справочник
        try:
            real_executors = sorted({e for c in state["controls"] for e in c.executors if e})
            real_controllers = sorted({c.controller for c in state["controls"] if c.controller})
            # initiators = distinct from data + custom from settings
            real_initiators = sorted({c.initiator for c in state["controls"] if c.initiator} | set(initiators))
            executor_filter_dd.options = [ft.dropdown.Option("all", "Все исполнители")] + [ft.dropdown.Option(n, short_name(n)) for n in real_executors]
            controller_filter_dd.options = [ft.dropdown.Option("all", "Все контролеры")] + [ft.dropdown.Option(n, short_name(n)) for n in real_controllers]
            initiator_filter_dd.options = [ft.dropdown.Option("all", "Все инициаторы")] + [ft.dropdown.Option(i) for i in real_initiators]
            try:
                _safe_update(executor_filter_dd)
                _safe_update(controller_filter_dd)
                _safe_update(initiator_filter_dd)
            except Exception:
                traceback.print_exc()
        except Exception:
            traceback.print_exc()

    def _mk_counter(key: str, label: str, color: str) -> ft.Container:
        counts = _counts()
        dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=color)
        row = ft.Row(controls=[dot, ft.Text(label, size=12, color=GLASS["text_secondary"], no_wrap=True), ft.Text(str(counts.get(key,0)), size=12, weight=ft.FontWeight.W_700, color=GLASS["text"], no_wrap=True)], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        btn = ft.Container(content=row, height=30, padding=ft.padding.symmetric(horizontal=12), border_radius=15, bgcolor=with_alpha(color, "22"), border=ft.border.all(1, with_alpha(color, "44")), alignment=ft.alignment.center, ink=True, on_click=lambda e, v=key: _set_status_filter(v))
        counter_refs[key] = btn
        return btn

    counter_defs = [
        ("all", "Все", GLASS["accent"]),
        (OVERDUE, "Просрочено", GLASS["overdue"]),
        (TODAY, "Сегодня", GLASS["today"]),
        (SOON, "Скоро", GLASS["soon"]),
        (IN_PROGRESS, "В работе", GLASS["in_progress"]),
        (DONE, "Исполнено", GLASS["done"]),
    ]
    counters_row = ft.Container(
        content=ft.Row(controls=[_mk_counter(k,l,c) for k,l,c in counter_defs], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.HIDDEN),
        height=36,
        padding=ft.padding.symmetric(horizontal=2, vertical=3),
    )

    # Mode switch
    def _set_mode(mode: str):
        state["mode"] = mode
        _restyle_mode_buttons()
        _rebuild_table()
        _refresh_counters()
        _rebuild_header()

    mode_buttons: Dict[str, ft.Container] = {}
    def _restyle_mode_buttons():
        for m, btn in mode_buttons.items():
            sel = state["mode"] == m
            btn.bgcolor = GLASS["accent"] if sel else GLASS["surface"]
            btn.border = None if sel else ft.border.all(1, GLASS["border"])
            try:
                for ctl in btn.content.controls:
                    if isinstance(ctl, ft.Text):
                        ctl.color = "#ffffff" if sel else GLASS["text_secondary"]
                    elif isinstance(ctl, ft.Icon):
                        ctl.color = "#ffffff" if sel else GLASS["text_secondary"]
                _safe_update(btn)
            except Exception:
                traceback.print_exc()

    def _mk_mode_btn(mode: str, label: str, icon) -> ft.Container:
        sel = state["mode"] == mode
        btn = ft.Container(
            content=ft.Row(controls=[ft.Icon(icon, size=14, color="#ffffff" if sel else GLASS["text_secondary"]), ft.Text(label, size=12, weight=ft.FontWeight.W_600, color="#ffffff" if sel else GLASS["text_secondary"], no_wrap=True)], spacing=5, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=30, padding=ft.padding.symmetric(horizontal=12), border_radius=8, alignment=ft.alignment.center,
            bgcolor=GLASS["accent"] if sel else GLASS["surface"], border=None if sel else ft.border.all(1, GLASS["border"]), ink=True,
            on_click=lambda e, m=mode: _set_mode(m),
        )
        mode_buttons[mode] = btn
        return btn

    mode_row = ft.Container(
        content=ft.Row(controls=[_mk_mode_btn("active", "Активные", ft.icons.PLAYLIST_PLAY), _mk_mode_btn("archive", "Архив", ft.icons.ARCHIVE_OUTLINED)], spacing=4, tight=True),
        height=38, bgcolor=GLASS["surface"], border=ft.border.all(1, GLASS["border"]), border_radius=10, padding=ft.padding.symmetric(horizontal=3, vertical=3),
    )

    # Filters
    search_field = _glass_textfield(hint="Поиск по содержанию, номеру…", width=320, expand=True)
    search_field.prefix_icon = ft.icons.SEARCH
    def _on_search(e=None):
        state["search"] = search_field.value or ""
        _apply_filters()
    search_field.on_change = _on_search

    status_filter_dd = _glass_dropdown("Все статусы", 160, [ft.dropdown.Option("all", "Все статусы"), ft.dropdown.Option(OVERDUE, "Просрочено"), ft.dropdown.Option(TODAY, "Сегодня"), ft.dropdown.Option(SOON, "Скоро"), ft.dropdown.Option(IN_PROGRESS, "В работе"), ft.dropdown.Option(DONE, "Исполнено"), ft.dropdown.Option(COMPLETED, "Завершён")])
    type_filter_dd = _glass_dropdown("Все типы", 140, [ft.dropdown.Option("all", "Все типы"), ft.dropdown.Option(ONE_TIME, "Разовый"), ft.dropdown.Option(PERIODIC, "Постоянный")])
    initiator_filter_dd = _glass_dropdown("Все инициаторы", 190, [ft.dropdown.Option("all", "Все инициаторы")] + [ft.dropdown.Option(i) for i in initiators])
    executor_filter_dd = _glass_dropdown("Все исполнители", 190, [ft.dropdown.Option("all", "Все исполнители")] + [ft.dropdown.Option(n, short_name(n)) for n in available_names])
    controller_filter_dd = _glass_dropdown("Все контролеры", 190, [ft.dropdown.Option("all", "Все контролеры")] + [ft.dropdown.Option(n, short_name(n)) for n in available_names])

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

    # ── Filter dates — shared calendar overlay at tab level (Bug 6 & 7 fix) ──
    # Simple date fields with clear inside, open shared calendar (no clipping)
    filter_from_text = ft.Text("С: —", size=12, color=GLASS["text_secondary"], no_wrap=True)
    filter_to_text = ft.Text("По: —", size=12, color=GLASS["text_secondary"], no_wrap=True)

    filter_from_clear = ft.IconButton(icon=ft.icons.CLEAR, icon_size=14, icon_color=GLASS["text_muted"], width=22, height=22, padding=0, visible=False, tooltip="Очистить")
    filter_to_clear = ft.IconButton(icon=ft.icons.CLEAR, icon_size=14, icon_color=GLASS["text_muted"], width=22, height=22, padding=0, visible=False, tooltip="Очистить")

    def _update_filter_from_display():
        iso = state["f_from"]
        if iso:
            d = parse_date(iso)
            filter_from_text.value = f"С: {d.strftime('%d.%m.%Y')}" if d else "С: —"
            filter_from_text.color = GLASS["text"]
            filter_from_clear.visible = True
        else:
            filter_from_text.value = "С: —"
            filter_from_text.color = GLASS["text_secondary"]
            filter_from_clear.visible = False
        try:
            _safe_update(filter_from_text)
            _safe_update(filter_from_clear)
        except Exception:
            traceback.print_exc()

    def _update_filter_to_display():
        iso = state["f_to"]
        if iso:
            d = parse_date(iso)
            filter_to_text.value = f"По: {d.strftime('%d.%m.%Y')}" if d else "По: —"
            filter_to_text.color = GLASS["text"]
            filter_to_clear.visible = True
        else:
            filter_to_text.value = "По: —"
            filter_to_text.color = GLASS["text_secondary"]
            filter_to_clear.visible = False
        try:
            _safe_update(filter_to_text)
            _safe_update(filter_to_clear)
        except Exception:
            traceback.print_exc()

    def _set_from_iso(iso):
        state["f_from"] = iso
        _update_filter_from_display()
        _apply_filters()

    def _set_to_iso(iso):
        state["f_to"] = iso
        _update_filter_to_display()
        _apply_filters()

    def _clear_from(e=None):
        state["f_from"] = None
        _update_filter_from_display()
        _apply_filters()
        _close_filter_cal()

    def _clear_to(e=None):
        state["f_to"] = None
        _update_filter_to_display()
        _apply_filters()
        _close_filter_cal()

    def _reset_filters(e=None):
        search_field.value = ""
        state["search"] = ""
        for dd in (status_filter_dd, type_filter_dd, initiator_filter_dd, executor_filter_dd, controller_filter_dd):
            dd.value = "all"
        state.update(f_status="all", f_type="all", f_initiator="all", f_executor="all", f_controller="all", f_from=None, f_to=None)
        _update_filter_from_display()
        _update_filter_to_display()
        _restyle_counters()
        try:
            page.update()
        except Exception:
            traceback.print_exc()
        _apply_filters()

    # Shared filter calendar overlay (tab level Stack, position near field)
    filter_cal_state = {"setter": None, "is_from": True, "visible": False}
    filter_cal_header = ft.Text("", size=13, weight=ft.FontWeight.W_700, color=GLASS["text"])
    filter_cal_grid = ft.Column(spacing=2, tight=True)
    filter_cal_root = ft.Container(
        visible=False,
        width=280,
        bgcolor=GLASS["surface_solid"],
        border=ft.border.all(1, GLASS["border"]),
        border_radius=12,
        padding=ft.padding.all(10),
        top=150,
        left=700,
    )

    def _close_filter_cal(e=None):
        filter_cal_root.visible = False
        filter_cal_state["visible"] = False
        try:
            _safe_update(filter_cal_root)
        except Exception:
            traceback.print_exc()

    def _open_filter_cal(is_from: bool, current_iso: Optional[str] = None):
        filter_cal_state["is_from"] = is_from
        filter_cal_state["setter"] = _set_from_iso if is_from else _set_to_iso
        # Position near field: S ~ left 650, Po ~ 800
        filter_cal_root.left = 650 if is_from else 800
        filter_cal_root.top = 150
        if current_iso:
            try:
                d = date.fromisoformat(current_iso)
                filter_cal_display["year"] = d.year
                filter_cal_display["month"] = d.month
                filter_cal_display["selected"] = d
            except Exception:
                filter_cal_display["selected"] = None
        else:
            filter_cal_display["selected"] = None
        _rebuild_filter_cal()
        filter_cal_root.visible = True
        filter_cal_state["visible"] = True
        try:
            _safe_update(filter_cal_root)
        except Exception:
            traceback.print_exc()

    def _filter_cal_nav(delta):
        y = filter_cal_display["year"]
        m = filter_cal_display["month"]
        m += delta
        while m > 12:
            m -= 12
            y += 1
        while m < 1:
            m += 12
            y -= 1
        filter_cal_display["year"] = y
        filter_cal_display["month"] = m
        _rebuild_filter_cal()

    def _filter_cal_today():
        today = date.today()
        filter_cal_display["year"] = today.year
        filter_cal_display["month"] = today.month
        filter_cal_display["selected"] = today
        if filter_cal_state["setter"]:
            try:
                filter_cal_state["setter"](today.isoformat())
            except Exception:
                traceback.print_exc()
        _close_filter_cal()

    def _rebuild_filter_cal():
        try:
            header = f"{['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'][filter_cal_display['month']-1]} {filter_cal_display['year']}"
            filter_cal_header.value = header
        except Exception:
            traceback.print_exc()
        cal = cal_module.Calendar(firstweekday=0)
        weeks = cal.monthdatescalendar(filter_cal_display["year"], filter_cal_display["month"])
        while len(weeks) < 6:
            last = weeks[-1][-1]
            base = last + timedelta(days=1)
            new_week = [base + timedelta(days=i) for i in range(7)]
            weeks.append(new_week)
        filter_cal_grid.controls.clear()
        today = date.today()
        selected = filter_cal_display["selected"]
        for week in weeks[:6]:
            row = ft.Row(spacing=2, tight=True)
            for d in week:
                is_other = d.month != filter_cal_display["month"]
                is_today = d == today
                is_sel = (selected is not None and d == selected)
                bg = GLASS["accent"] if is_sel else "transparent"
                txt_color = "#ffffff" if is_sel else (GLASS["text_muted"] if is_other else GLASS["text"])
                border = ft.border.all(1, GLASS["accent"]) if is_today and not is_sel else None
                txt = ft.Text(str(d.day), size=12, color=txt_color, weight=ft.FontWeight.W_500 if is_today else None)
                def _make_click(dd):
                    def _click(e=None):
                        filter_cal_display["selected"] = dd
                        if filter_cal_state["setter"]:
                            try:
                                filter_cal_state["setter"](dd.isoformat())
                            except Exception:
                                traceback.print_exc()
                        _close_filter_cal()
                    return _click
                def _make_hover(cell, orig_bg, sel):
                    def _hover(e):
                        if sel:
                            return
                        try:
                            cell.bgcolor = GLASS["hover_strong"] if e.data == "true" else orig_bg
                            _safe_update(cell)
                        except Exception:
                            traceback.print_exc()
                    return _hover
                cell = ft.Container(width=34, height=32, border_radius=8, bgcolor=bg, border=border, alignment=ft.alignment.center, content=txt, ink=True)
                cell.on_click = _make_click(d)
                cell.on_hover = _make_hover(cell, bg, is_sel)
                row.controls.append(cell)
            filter_cal_grid.controls.append(row)
        try:
            _safe_update(filter_cal_grid)
            _safe_update(filter_cal_header)
        except Exception:
            traceback.print_exc()

    filter_cal_display = {"year": date.today().year, "month": date.today().month, "selected": None}
    filter_cal_root.content = ft.Column(
        controls=[
            ft.Row(controls=[ft.IconButton(icon=ft.icons.CHEVRON_LEFT, icon_size=18, icon_color=GLASS["text_secondary"], width=28, height=28, padding=0, on_click=lambda e: _filter_cal_nav(-1)), ft.Container(content=filter_cal_header, expand=True, alignment=ft.alignment.center), ft.IconButton(icon=ft.icons.CHEVRON_RIGHT, icon_size=18, icon_color=GLASS["text_secondary"], width=28, height=28, padding=0, on_click=lambda e: _filter_cal_nav(1))], spacing=4, tight=True),
            ft.Container(height=4),
            ft.Row(controls=[ft.Container(width=34, height=20, alignment=ft.alignment.center, content=ft.Text(wd, size=10, weight=ft.FontWeight.W_700, color=GLASS["text_muted"])) for wd in ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]], spacing=2, tight=True),
            filter_cal_grid,
            ft.Container(height=6),
            ft.Row(controls=[ft.TextButton("Сегодня", on_click=lambda e: _filter_cal_today(), style=ft.ButtonStyle(color=GLASS["accent"])), ft.Container(expand=True), ft.TextButton("Закрыть", on_click=lambda e: _close_filter_cal(), style=ft.ButtonStyle(color=GLASS["text_muted"]))], spacing=4, tight=True),
        ], spacing=2, tight=True,
    )
    _rebuild_filter_cal()

    # Filter date field containers with clear inside (Bug 7)
    filter_from_container = ft.Container(
        content=ft.Row(controls=[filter_from_text, filter_from_clear, ft.Icon(ft.icons.CALENDAR_MONTH, size=16, color=GLASS["text_secondary"])], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        width=120, height=38, bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=10,
        padding=ft.padding.symmetric(horizontal=10, vertical=6), alignment=ft.alignment.center_left,
        on_click=lambda e: _open_filter_cal(True, state["f_from"]),
    )
    filter_to_container = ft.Container(
        content=ft.Row(controls=[filter_to_text, filter_to_clear, ft.Icon(ft.icons.CALENDAR_MONTH, size=16, color=GLASS["text_secondary"])], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        width=120, height=38, bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=10,
        padding=ft.padding.symmetric(horizontal=10, vertical=6), alignment=ft.alignment.center_left,
        on_click=lambda e: _open_filter_cal(False, state["f_to"]),
    )
    filter_from_clear.on_click = _clear_from
    filter_to_clear.on_click = _clear_to

    filter_row1 = glass_panel(
        content=ft.Row(controls=[search_field, status_filter_dd, type_filter_dd, ft.Container(expand=True), mode_row], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=52, radius=12, padding=ft.padding.symmetric(horizontal=12, vertical=8),
    )
    # Bug 7: крестики очистки встроены внутрь поля даты (suffix), убрать отдельные кнопки из ряда
    filter_row2 = glass_panel(
        content=ft.Row(controls=[initiator_filter_dd, executor_filter_dd, controller_filter_dd, filter_from_container, filter_to_container, ft.Container(expand=True), ft.TextButton("Сброс", on_click=_reset_filters, style=ft.ButtonStyle(color=GLASS["accent"]))], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=52, radius=12, padding=ft.padding.symmetric(horizontal=12, vertical=8),
    )

    table_inner = ft.Column(controls=[header_row, rows_column], spacing=0, tight=True)
    table_container = glass_panel(content=table_inner, radius=12, padding=ft.padding.all(0), bgcolor=GLASS["surface"], border_color=GLASS["border"], top_border_color=GLASS["border_light"])

    # ── Detail overlay with global calendar dropdown ──────────
    # Global calendar for task dates etc to avoid clipping
    global_cal_state = {"setter": None, "visible": False}
    global_cal_panel = ft.Container(visible=False, width=280, bgcolor=GLASS["surface_solid"], border=ft.border.all(1, GLASS["border"]), border_radius=12, padding=ft.padding.all(10))
    # will be filled later per open

    # Inline multi
    def _build_inline_multi(available: List[str], initial: List[str], title: str, on_change_cb=None, compact=False):
        selected = list(initial)
        expanded = {"value": False}
        search_val = {"value": ""}
        badge = ft.Text(f"Выбрано: {len(selected)}", size=11, color=GLASS["text_secondary"])
        summary = ft.Text(", ".join(short_name(x) for x in selected) or "не выбрано", size=12, color=GLASS["text"], max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, tooltip=", ".join(selected))
        search_field_ms = _glass_textfield(hint=f"Поиск {title.lower()}…")
        search_field_ms.height = 34
        search_field_ms.visible = False
        list_col = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=140 if not compact else 120, visible=False)
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
                            _safe_update(badge)
                            _safe_update(summary)
                        except Exception:
                            traceback.print_exc()
                        if on_change_cb:
                            try:
                                on_change_cb(list(selected))
                            except Exception:
                                traceback.print_exc()
                    return _toggle
                list_col.controls.append(ft.Checkbox(label=short_name(name), value=(name in selected), active_color=GLASS["accent"], label_style=ft.TextStyle(size=11 if compact else 12, color=GLASS["text"]), tooltip=name, on_change=_make_toggle(name), height=24 if compact else 28))
            try:
                _safe_update(list_col)
            except Exception:
                traceback.print_exc()
        def _on_search_change(e):
            search_val["value"] = e.control.value or ""
            _rebuild_list()
        search_field_ms.on_change = _on_search_change
        list_wrapper = ft.Container(content=list_col, border=ft.border.all(1, GLASS["border"]), border_radius=10, padding=ft.padding.all(6), bgcolor=GLASS["surface_alt"], visible=False)
        def _toggle_expand(e=None):
            expanded["value"] = not expanded["value"]
            search_field_ms.visible = expanded["value"]
            list_wrapper.visible = expanded["value"]
            list_col.visible = expanded["value"]
            summary.visible = not expanded["value"]
            expand_btn.icon = ft.icons.EXPAND_LESS if expanded["value"] else ft.icons.EXPAND_MORE
            try:
                _safe_update(search_field_ms)
                _safe_update(list_wrapper)
                _safe_update(summary)
                _safe_update(expand_btn)
            except Exception:
                traceback.print_exc()
            if expanded["value"]:
                _rebuild_list()
        def _clear_all(e=None):
            selected.clear()
            badge.value = "Выбрано: 0"
            summary.value = "не выбрано"
            summary.tooltip = None
            try:
                _safe_update(badge)
                _safe_update(summary)
            except Exception:
                traceback.print_exc()
            if on_change_cb:
                try:
                    on_change_cb([])
                except Exception:
                    traceback.print_exc()
            _rebuild_list()
        expand_btn = ft.IconButton(icon=ft.icons.EXPAND_MORE, icon_size=18, icon_color=GLASS["text_secondary"], on_click=_toggle_expand)
        header = ft.Row(controls=[ft.Text(title, size=12 if compact else 12, weight=ft.FontWeight.BOLD, color=GLASS["text"]), ft.Container(width=8), badge, ft.Container(expand=True), ft.TextButton("Очистить", on_click=_clear_all, style=ft.ButtonStyle(color=GLASS["overdue"])), expand_btn], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        _rebuild_list()
        container = ft.Container(
            content=ft.Column(controls=[header, summary, search_field_ms, list_wrapper], spacing=6, tight=True),
            bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=10, padding=ft.padding.all(8),
        )
        container._get_selected = lambda: list(selected)
        return container

    detail_state: Dict = {"control_id": None, "is_new": True, "tasks": [], "milestones": [], "attachments": [], "receive_date": None, "due_date": None, "end_date": None}

    # Global calendar overlay for task dates
    global_cal_root = ft.Container(visible=False, width=300, height=340, bgcolor=GLASS["surface_solid"], border=ft.border.all(1, GLASS["border"]), border_radius=12, padding=ft.padding.all(10), top=200, left=300)
    global_cal_header = ft.Text("", size=13, weight=ft.FontWeight.W_700, color=GLASS["text"])
    global_cal_grid = ft.Column(spacing=2, tight=True)
    global_cal_panel_content = ft.Column(
        controls=[
            ft.Row(controls=[ft.IconButton(icon=ft.icons.CHEVRON_LEFT, icon_size=18, icon_color=GLASS["text_secondary"], width=28, height=28, padding=0, on_click=lambda e: _global_cal_nav(-1)), ft.Container(content=global_cal_header, expand=True, alignment=ft.alignment.center), ft.IconButton(icon=ft.icons.CHEVRON_RIGHT, icon_size=18, icon_color=GLASS["text_secondary"], width=28, height=28, padding=0, on_click=lambda e: _global_cal_nav(1))], spacing=4, tight=True),
            ft.Container(height=4),
            ft.Row(controls=[ft.Container(width=34, height=20, alignment=ft.alignment.center, content=ft.Text(wd, size=10, weight=ft.FontWeight.W_700, color=GLASS["text_muted"])) for wd in ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]], spacing=2, tight=True),
            global_cal_grid,
            ft.Container(height=6),
            ft.Row(controls=[ft.TextButton("Сегодня", on_click=lambda e: _global_cal_today(), style=ft.ButtonStyle(color=GLASS["accent"])), ft.Container(expand=True), ft.TextButton("Закрыть", on_click=lambda e: _close_global_cal(), style=ft.ButtonStyle(color=GLASS["text_muted"]))], spacing=4, tight=True),
        ], spacing=2, tight=True,
    )
    global_cal_root.content = global_cal_panel_content

    global_cal_display = {"year": date.today().year, "month": date.today().month, "selected": None}

    def _close_global_cal(e=None):
        global_cal_root.visible = False
        global_cal_state["visible"] = False
        try:
            _safe_update(global_cal_root)
        except Exception:
            traceback.print_exc()

    def _open_global_cal(setter, current_iso=None):
        global_cal_state["setter"] = setter
        sel = None
        if current_iso:
            try:
                sel = date.fromisoformat(current_iso)
            except Exception:
                sel = None
        if sel:
            global_cal_display["year"] = sel.year
            global_cal_display["month"] = sel.month
            global_cal_display["selected"] = sel
        else:
            global_cal_display["selected"] = date.today() if current_iso is None else sel
        _rebuild_global_cal()
        global_cal_root.visible = True
        global_cal_state["visible"] = True
        try:
            _safe_update(global_cal_root)
        except Exception:
            traceback.print_exc()

    def _global_cal_nav(delta):
        y = global_cal_display["year"]
        m = global_cal_display["month"]
        m += delta
        while m > 12:
            m -= 12
            y += 1
        while m < 1:
            m += 12
            y -= 1
        global_cal_display["year"] = y
        global_cal_display["month"] = m
        _rebuild_global_cal()

    def _global_cal_today():
        today = date.today()
        global_cal_display["year"] = today.year
        global_cal_display["month"] = today.month
        global_cal_display["selected"] = today
        if global_cal_state["setter"]:
            try:
                global_cal_state["setter"](today.isoformat())
            except Exception:
                traceback.print_exc()
        _close_global_cal()

    def _rebuild_global_cal():
        try:
            header = f"{['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'][global_cal_display['month']-1]} {global_cal_display['year']}"
            global_cal_header.value = header
        except Exception:
            traceback.print_exc()
        cal = cal_module.Calendar(firstweekday=0)
        weeks = cal.monthdatescalendar(global_cal_display["year"], global_cal_display["month"])
        while len(weeks) < 6:
            last = weeks[-1][-1]
            base = last + timedelta(days=1)
            new_week = [base + timedelta(days=i) for i in range(7)]
            weeks.append(new_week)
        global_cal_grid.controls.clear()
        today = date.today()
        selected = global_cal_display["selected"]
        for week in weeks[:6]:
            row = ft.Row(spacing=2, tight=True)
            for d in week:
                is_other = d.month != global_cal_display["month"]
                is_today = d == today
                is_sel = (selected is not None and d == selected)
                bg = GLASS["accent"] if is_sel else "transparent"
                txt_color = "#ffffff" if is_sel else (GLASS["text_muted"] if is_other else GLASS["text"])
                border = ft.border.all(1, GLASS["accent"]) if is_today and not is_sel else None
                txt = ft.Text(str(d.day), size=12, color=txt_color, weight=ft.FontWeight.W_500 if is_today else None)
                def _make_click(dd):
                    def _click(e=None):
                        global_cal_display["selected"] = dd
                        if global_cal_state["setter"]:
                            try:
                                global_cal_state["setter"](dd.isoformat())
                            except Exception:
                                traceback.print_exc()
                        _close_global_cal()
                    return _click
                def _make_hover(cell, orig_bg, sel):
                    def _hover(e):
                        if sel:
                            return
                        try:
                            cell.bgcolor = GLASS["hover_strong"] if e.data == "true" else orig_bg
                            _safe_update(cell)
                        except Exception:
                            traceback.print_exc()
                    return _hover
                cell = ft.Container(width=34, height=32, border_radius=8, bgcolor=bg, border=border, alignment=ft.alignment.center, content=txt, ink=True)
                cell.on_click = _make_click(d)
                cell.on_hover = _make_hover(cell, bg, is_sel)
                row.controls.append(cell)
            global_cal_grid.controls.append(row)
        try:
            _safe_update(global_cal_grid)
            _safe_update(global_cal_header)
        except Exception:
            traceback.print_exc()

    _rebuild_global_cal()

    # Detail card — раунд 6: серый графит #242a3e (не синий), рамки #1affffff, кромка сверху #2effffff
    detail_card = ft.Container(
        width=920,
        height=780,
        bgcolor=GLASS["card_panel"],
        border=ft.border.only(top=ft.BorderSide(1, GLASS["border_light"]), left=ft.BorderSide(1, GLASS["border_divider"]), right=ft.BorderSide(1, GLASS["border_divider"]), bottom=ft.BorderSide(1, GLASS["border_divider"])),
        border_radius=16,
        padding=ft.padding.all(16),
        content=ft.Column(controls=[ft.Text("Загрузка…")], scroll=ft.ScrollMode.AUTO, expand=True),
    )

    # Detail overlay Stack: card + global calendar dropdown (top layer to avoid clipping)
    detail_overlay = ft.Stack(
        controls=[detail_card, global_cal_root],
    )

    # Overlay container: dim background covering the whole tab, card centred at top.
    # NB: NO inner Column(scroll=AUTO, expand=True) — that combination collapses to zero
    # height in Flet 0.23.2 (AGENTS 15.11/22) and was the reason the card did not render
    # while the dim background still showed. The card itself has a fixed height and
    # scrolls internally (like control_card_modal).
    detail_overlay_container = ft.Container(
        visible=False,
        bgcolor=GLASS["overlay_bg"],
        expand=True,
        padding=ft.padding.all(12),
        alignment=ft.alignment.top_center,
        content=detail_overlay,
    )

    def _hide_detail(e=None):
        detail_overlay_container.visible = False
        state["editing"] = False
        _close_global_cal()
        try:
            _safe_update(detail_overlay_container)
        except Exception:
            traceback.print_exc()

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

        # Fields helpers
        # Раунд 5: НЕ используем expand=True у полей карточки — внутри scroll-колонки
        # (middle_scroll) это схлопывает левую колонку до нулевой высоты (AGENTS 15.11).
        # Ширины задаём явные, где поле в Row.
        incoming_field = _glass_textfield(value=ctl.incoming_number if ctl else "", hint="Входящий № ВХСОП *", width=300)
        receive_field_text = ft.Text(_display_date(detail_state["receive_date"]), size=13, color=GLASS["text"])
        receive_box = ft.Container(
            content=ft.Row(controls=[receive_field_text, ft.Container(expand=True), ft.Icon(ft.icons.CALENDAR_MONTH, size=18, color=GLASS["text_secondary"])], spacing=6, tight=True),
            width=160, height=40, bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=10,
            padding=ft.padding.symmetric(horizontal=12, vertical=6), alignment=ft.alignment.center_left,
        )
        def _set_receive(iso):
            detail_state["receive_date"] = iso
            receive_field_text.value = _display_date(iso)
            try:
                _safe_update(receive_field_text)
            except Exception:
                traceback.print_exc()
        def _open_receive_cal(e=None):
            _open_global_cal(_set_receive, detail_state["receive_date"])
        receive_box.on_click = _open_receive_cal

        init_dd = _glass_dropdown("Инициатор", 260, [ft.dropdown.Option(i) for i in initiators], value=ctl.initiator if (ctl and ctl.initiator in initiators) else None)
        # New initiator inline: hidden field that appears on + click
        new_init_field = _glass_textfield(hint="Новый инициатор…", width=180)
        new_init_field.visible = False
        add_init_confirm = ft.ElevatedButton("Добавить", height=36, bgcolor=GLASS["surface_alt"], color=GLASS["accent"], style=ft.ButtonStyle(side=ft.BorderSide(1, GLASS["border"]), shape=ft.RoundedRectangleBorder(radius=8)), on_click=lambda e: _add_initiator())
        new_init_row = ft.Row(controls=[new_init_field, add_init_confirm], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        new_init_container = ft.Container(content=new_init_row, visible=False)
        def _show_new_init(e=None):
            new_init_container.visible = not new_init_container.visible
            new_init_field.visible = new_init_container.visible
            try:
                _safe_update(new_init_container)
                _safe_update(new_init_field)
            except Exception:
                traceback.print_exc()
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
            new_init_container.visible = False
            new_init_field.visible = False
            try:
                _safe_update(init_dd)
                _safe_update(new_init_container)
                initiator_filter_dd.options = [ft.dropdown.Option("all", "Все инициаторы")] + [ft.dropdown.Option(i) for i in initiators]
                _safe_update(initiator_filter_dd)
            except Exception:
                traceback.print_exc()
        add_init_btn = ft.IconButton(icon=ft.icons.ADD, icon_size=18, icon_color=GLASS["accent"], tooltip="Добавить нового", on_click=_show_new_init, width=36, height=36)

        content_field = _glass_textfield(value=ctl.content if ctl else "", hint="Содержание контроля…", multiline=True, min_lines=3, max_lines=5)
        exec_container = _build_inline_multi(available_names, list(ctl.executors) if ctl else [], "Исполнители")

        # Раунд 5: ширины подогнаны под левую панель (500 - padding*2 ≈ 476), чтобы строка
        # «За кем контроль / Тип / Периодичность» не переполнялась и не клипировалась.
        controller_dd = _glass_dropdown("За кем контроль", 180, [ft.dropdown.Option(n, short_name(n)) for n in available_names], value=ctl.controller if (ctl and ctl.controller in available_names) else None)
        type_dd = _glass_dropdown("Тип", 120, [ft.dropdown.Option(ONE_TIME, "Разовый"), ft.dropdown.Option(PERIODIC, "Постоянный")], value=ctl.control_type if ctl else ONE_TIME)
        period_dd = _glass_dropdown("Периодичность", 140, [ft.dropdown.Option(k, l) for k, l, _ in _PERIOD_LABELS], value=_period_key(ctl.period_days if ctl else 7))
        period_dd.visible = (ctl.control_type if ctl else ONE_TIME) == PERIODIC
        custom_days_field = _glass_textfield(value=str(ctl.period_days) if ctl else "7", hint="Интервал дней", width=110)
        custom_days_field.visible = _period_key(ctl.period_days if ctl else 7) == "custom"

        # Due date field - uses global calendar for tasks, but for main due we will use expanded calendar in right column
        due_field_text = ft.Text(_display_date(detail_state["due_date"]), size=13, color=GLASS["text"] if detail_state["due_date"] else GLASS["text_muted"])
        due_box = ft.Container(
            content=ft.Row(controls=[due_field_text, ft.Container(expand=True), ft.Icon(ft.icons.CALENDAR_MONTH, size=18, color=GLASS["text_secondary"])], spacing=6, tight=True),
            width=200, height=40, bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=10,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
        )
        def _set_due(iso):
            detail_state["due_date"] = iso
            due_field_text.value = _display_date(iso)
            try:
                _safe_update(due_field_text)
            except Exception:
                traceback.print_exc()
            _refresh_cycle_hint()
        due_box.on_click = lambda e: _open_global_cal(_set_due, detail_state["due_date"])

        # End date
        end_field_text = ft.Text(_display_date(detail_state["end_date"]), size=13, color=GLASS["text"] if detail_state["end_date"] else GLASS["text_muted"])
        end_box = ft.Container(
            content=ft.Row(controls=[end_field_text, ft.Container(expand=True), ft.Icon(ft.icons.CALENDAR_MONTH, size=18, color=GLASS["text_secondary"])], spacing=6, tight=True),
            width=160, height=40, bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=10,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
        )
        end_box.visible = (ctl.control_type if ctl else ONE_TIME) == PERIODIC
        def _set_end(iso):
            detail_state["end_date"] = iso
            end_field_text.value = _display_date(iso)
            try:
                _safe_update(end_field_text)
            except Exception:
                traceback.print_exc()
            _refresh_cycle_hint()
        end_box.on_click = lambda e: _open_global_cal(_set_end, detail_state["end_date"])

        cycle_hint = ft.Text("", size=11, color=GLASS["text_secondary"], italic=True)
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
                _safe_update(cycle_hint)
            except Exception:
                traceback.print_exc()
        def _on_type_change(e):
            is_per = (e.control.value == PERIODIC)
            period_dd.visible = is_per
            end_box.visible = is_per
            # Раунд 5: «Промежуточные точки» показываем всегда (секция добавлена всегда),
            # а не прячем — иначе «+ Добавить точку» добавлял точку в скрытую колонку и
            # «ничего не происходило». milestones_header удалён (нет такого контрола).
            try:
                _safe_update(period_dd)
                _safe_update(end_box)
                _safe_update(milestones_col)
            except Exception:
                traceback.print_exc()
            _refresh_cycle_hint()
        def _on_period_change(e):
            custom_days_field.visible = (e.control.value == "custom")
            try:
                _safe_update(custom_days_field)
            except Exception:
                traceback.print_exc()
            _refresh_cycle_hint()
        type_dd.on_change = _on_type_change
        period_dd.on_change = _on_period_change

        comment_field = _glass_textfield(value=ctl.comment if ctl else "", hint="Комментарий…", multiline=True, min_lines=1, max_lines=3)

        # Tasks — no always open calendar (Bug 9 fix: nowhere always open)
        tasks_col = ft.Column(spacing=8, tight=True)
        def _rebuild_task_cards():
            tasks_col.controls.clear()
            for idx, t_ui in enumerate(detail_state["tasks"]):
                tasks_col.controls.append(_build_single_task_card(t_ui, idx))
            try:
                _safe_update(tasks_col)
            except Exception:
                traceback.print_exc()

        def _build_single_task_card(t_ui: dict, idx: int) -> ft.Container:
            title_f = t_ui["title_field"]
            # Due for task uses global calendar
            task_due_text = ft.Text(_display_date(t_ui["due_ref"]["value"]), size=12, color=GLASS["text"] if t_ui["due_ref"]["value"] else GLASS["text_muted"])
            task_due_box = ft.Container(
                content=ft.Row(controls=[ft.Text("Срок:", size=11, color=GLASS["text_secondary"]), ft.Container(width=6), task_due_text, ft.Container(expand=True), ft.Icon(ft.icons.CALENDAR_MONTH, size=16, color=GLASS["text_secondary"])], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                width=160, height=34, bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=8,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
            )
            def _set_task_due(iso, ui=t_ui, txt=task_due_text):
                ui["due_ref"]["value"] = iso
                txt.value = _display_date(iso)
                try:
                    _safe_update(txt)
                except Exception:
                    traceback.print_exc()
            task_due_box.on_click = lambda e, s=_set_task_due: _open_global_cal(lambda iso: s(iso), t_ui["due_ref"]["value"])

            ass_container = _build_inline_multi(available_names, t_ui.get("assignees", []), f"Отв. {title_f.value[:10] or 'пункт'}", compact=True)
            t_ui["_ass_container"] = ass_container

            # Checkbox for done - normal size checkbox
            is_done_check = ft.Checkbox(label="исполнено", value=t_ui["is_done"], active_color=GLASS["in_progress"], label_style=ft.TextStyle(size=11, color=GLASS["text_secondary"]), on_change=lambda e, ui=t_ui: ui.update({"is_done": bool(e.control.value)}), height=28)

            comment_f = _glass_textfield(value=t_ui.get("comment",""), hint="Комментарий…")
            comment_f.height = 32
            t_ui["comment_field"] = comment_f

            return glass_panel(
                content=ft.Column(controls=[
                    ft.Row(controls=[ft.Icon(ft.icons.DRAG_INDICATOR, size=14, color=GLASS["text_muted"]), title_f, ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=16, icon_color=GLASS["overdue"], on_click=lambda e, ui=t_ui: _remove_task(ui))], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ass_container,
                    ft.Row(controls=[task_due_box, is_done_check], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    comment_f,
                ], spacing=6, tight=True),
                radius=10, padding=ft.padding.all(10), bgcolor=GLASS["card"],  # раунд 6: как строка таблицы #2a3247
            )

        def _remove_task(ui):
            if ui in detail_state["tasks"]:
                detail_state["tasks"].remove(ui)
            _rebuild_task_cards()
        def _add_task(e=None):
            new_ui = {
                # Раунд 5: без expand=True (схлопывает scroll-колонку карточки), ширина
                # заполняет правую панель в Row [иконка, поле, удалить].
                "title_field": _glass_textfield(hint="Пункт (напр. п.1)", width=300),
                "assignees": [],
                "due_ref": {"value": None},
                "is_done": False,
                "comment": "",
            }
            detail_state["tasks"].append(new_ui)
            _rebuild_task_cards()

        if ctl and ctl.tasks:
            for t in ctl.tasks:
                detail_state["tasks"].append({
                    "title_field": _glass_textfield(value=t.title, hint="Пункт", width=300),
                    "assignees": list(t.assignees),
                    "due_ref": {"value": t.due_date},
                    "is_done": t.is_done,
                    "comment": getattr(t, "comment", ""),
                })
        _rebuild_task_cards()

        # Milestones
        milestones_col = ft.Column(spacing=8, tight=True)
        milestones_col.visible = True  # Раунд 5: всегда видим, чтобы точки можно было добавлять
        def _rebuild_milestones():
            milestones_col.controls.clear()
            for m_ui in detail_state["milestones"]:
                milestones_col.controls.append(_build_milestone_card(m_ui))
            try:
                _safe_update(milestones_col)
            except Exception:
                traceback.print_exc()

        def _build_milestone_card(m_ui: dict) -> ft.Container:
            date_text = ft.Text(_display_date(m_ui["date_ref"]["value"]), size=12, color=GLASS["text"] if m_ui["date_ref"]["value"] else GLASS["text_muted"])
            date_box = ft.Container(
                content=ft.Row(controls=[date_text, ft.Container(expand=True), ft.Icon(ft.icons.CALENDAR_MONTH, size=16, color=GLASS["text_secondary"])], spacing=4, tight=True),
                width=130, height=34, bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=8,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
            )
            def _set_m_date(iso, ui=m_ui, txt=date_text):
                ui["date_ref"]["value"] = iso
                txt.value = _display_date(iso)
                try:
                    _safe_update(txt)
                except Exception:
                    traceback.print_exc()
            date_box.on_click = lambda e, s=_set_m_date: _open_global_cal(lambda iso: s(iso), m_ui["date_ref"]["value"])
            # Раунд 5: без expand=True; note_f на отдельной строке (не в тесном Row), тянется по ширине панели
            note_f = _glass_textfield(value=m_ui["note"], hint="Точка (описание)")
            note_f.height = 34
            note_f.on_change = lambda e, ui=m_ui: ui.update({"note": e.control.value or ""})
            done_check = ft.Checkbox(label="готово", value=m_ui["is_done"], active_color=GLASS["in_progress"], label_style=ft.TextStyle(size=11, color=GLASS["text_secondary"]), on_change=lambda e, ui=m_ui: ui.update({"is_done": bool(e.control.value)}), height=28)
            return glass_panel(
                content=ft.Column(controls=[
                    ft.Row(controls=[date_box, done_check, ft.Container(expand=True), ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=16, icon_color=GLASS["overdue"], on_click=lambda e, ui=m_ui: _remove_mile(ui))], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    note_f,
                ], spacing=6, tight=True),
                radius=10, padding=ft.padding.all(8), bgcolor=GLASS["card"],  # раунд 6: как строка таблицы #2a3247
            )

        def _remove_mile(ui):
            if ui in detail_state["milestones"]:
                detail_state["milestones"].remove(ui)
            _rebuild_milestones()
        def _add_mile(e=None):
            detail_state["milestones"].append({"date_ref": {"value": None}, "note": "", "is_done": False})
            _rebuild_milestones()

        if ctl and ctl.milestones:
            for m in ctl.milestones:
                detail_state["milestones"].append({"date_ref": {"value": m.date}, "note": m.note, "is_done": m.is_done})
        _rebuild_milestones()

        # Attachments
        attach_col = ft.Column(spacing=6, tight=True)
        def _rebuild_attach():
            attach_col.controls.clear()
            for rel in detail_state["attachments"]:
                fn = rel.split("/")[-1]
                icon = ft.icons.PICTURE_AS_PDF if fn.lower().endswith(".pdf") else ft.icons.IMAGE_OUTLINED if fn.lower().endswith((".png",".jpg",".jpeg")) else ft.icons.DESCRIPTION_OUTLINED
                attach_col.controls.append(
                    glass_panel(
                        content=ft.Row(controls=[
                            ft.Icon(icon, size=14, color=GLASS["accent"]),
                            ft.Text(fn, size=11, color=GLASS["text"], expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, tooltip=fn),
                            ft.IconButton(icon=ft.icons.OPEN_IN_NEW, icon_size=14, icon_color=GLASS["accent"], tooltip="Открыть", on_click=lambda e, r=rel: _open_attach(r)),
                            ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=14, icon_color=GLASS["overdue"], tooltip="Удалить", on_click=lambda e, r=rel: _confirm_remove_attach(r)),
                        ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        radius=8, padding=ft.padding.all(8), bgcolor=GLASS["surface_alt"],
                    )
                )
            try:
                _safe_update(attach_col)
            except Exception:
                traceback.print_exc()

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
                    traceback.print_exc()
                if rel in detail_state["attachments"]:
                    detail_state["attachments"].remove(rel)
                _rebuild_attach()
                try:
                    page.close(dlg)
                except Exception:
                    traceback.print_exc()
            def _cancel(e=None):
                try:
                    page.close(dlg)
                except Exception:
                    traceback.print_exc()
            dlg = ft.AlertDialog(modal=True, bgcolor=GLASS["surface_solid"], title=ft.Text("Удаление вложения", size=14, weight=ft.FontWeight.BOLD, color=GLASS["text"]), content=ft.Text("Удалить файл вложения?", size=12, color=GLASS["text"]), actions=[ft.TextButton("Отмена", on_click=_cancel), ft.ElevatedButton("Удалить", bgcolor=GLASS["overdue"], color="#ffffff", on_click=_confirm)], shape=ft.RoundedRectangleBorder(radius=12))
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
                    traceback.print_exc()
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

        def _save_detail(e=None):
            inc = (incoming_field.value or "").strip()
            if not inc:
                try:
                    incoming_field.error_text = "Введите номер"
                    _safe_update(incoming_field)
                except Exception:
                    traceback.print_exc()
                return
            if not detail_state["receive_date"]:
                return
            execs = exec_container._get_selected() if hasattr(exec_container, "_get_selected") else []
            new_tasks = []
            for ui in detail_state["tasks"]:
                title = (ui["title_field"].value or "").strip()
                if not title:
                    continue
                ass = ui.get("assignees", [])
                if "_ass_container" in ui and hasattr(ui["_ass_container"], "_get_selected"):
                    try:
                        ass = ui["_ass_container"]._get_selected()
                    except Exception:
                        traceback.print_exc()
                new_tasks.append(ControlTask(id=str(uuid4()), title=title, assignees=list(ass), due_date=ui["due_ref"]["value"], is_done=ui["is_done"], comment=ui.get("comment_field", ft.TextField()).value if "comment_field" in ui else ""))
            new_miles = []
            for ui in detail_state["milestones"]:
                if not ui["date_ref"]["value"] and not ui["note"]:
                    continue
                new_miles.append(ControlMilestone(id=str(uuid4()), date=ui["date_ref"]["value"], note=ui["note"], is_done=ui["is_done"]))

            def _period_days_val_inner():
                k = period_dd.value or "weekly"
                if k == "custom":
                    try:
                        return max(1, int(custom_days_field.value or "7"))
                    except ValueError:
                        return 7
                return _PERIOD_DAYS.get(k, 7)

            c = ctl if ctl else Control(id=detail_state["control_id"])
            c.incoming_number = inc
            c.receive_date = detail_state["receive_date"]
            c.initiator = init_dd.value or ""
            c.content = content_field.value.strip()
            c.executors = execs
            c.controller = controller_dd.value or ""
            c.control_type = type_dd.value or ONE_TIME
            c.period_days = _period_days_val_inner() if c.control_type == PERIODIC else (ctl.period_days if ctl else 7)
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
                    traceback.print_exc()
            dlg = ft.AlertDialog(modal=True, bgcolor=GLASS["surface_solid"], title=ft.Text("Переместить в архив", size=14, weight=ft.FontWeight.BOLD, color=GLASS["text"]), content=ft.Text(f"Переместить «{ctl.incoming_number}» в архив?", size=12, color=GLASS["text"]), actions=[ft.TextButton("Отмена", on_click=_cancel), ft.ElevatedButton("В архив", bgcolor=GLASS["accent"], color="#ffffff", on_click=_confirm)], shape=ft.RoundedRectangleBorder(radius=12))
            page.open(dlg)

        # ── Build two-column layout ─────────────────────────────
        # Left column - Bug 8 fix: remove expand=True inside scroll column (classic collapse AGENTS 15.11), use fixed widths
        left_col = ft.Column(spacing=14, tight=True)
        # Section Реквизиты
        rekv_content = ft.Column(controls=[
            ft.Row(controls=[
                _field_with_label("Входящий № (ВХСОП) *", incoming_field),
                _field_with_label("Дата поступления *", receive_box),
            ], spacing=12, tight=True),
            ft.Column(controls=[
                ft.Text("Инициатор", size=11, color=GLASS["text_secondary"]),
                ft.Row(controls=[init_dd, add_init_btn], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                new_init_container,
            ], spacing=4, tight=True),
            _field_with_label("Содержание", content_field),
        ], spacing=12, tight=True)

        # Раунд 6: секции карточки — серый графит #2a3045, отступ 14
        left_col.controls.append(glass_panel(content=rekv_content, radius=12, padding=ft.padding.all(14), bgcolor=GLASS["card_section"]))

        # Section Исполнение

        ispol_content = ft.Column(controls=[
            exec_container,
            ft.Row(controls=[
                _field_with_label("За кем контроль", controller_dd),
                _field_with_label("Тип", type_dd),
                _field_with_label("Периодичность", ft.Column(controls=[period_dd, custom_days_field], spacing=4, tight=True)),
            ], spacing=12, tight=True),
        ], spacing=12, tight=True)
        left_col.controls.append(glass_panel(content=ft.Column(controls=[ft.Text("Исполнение", size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"]), ispol_content], spacing=8, tight=True), radius=12, padding=ft.padding.all(14), bgcolor=GLASS["card_section"]))

        # Comment
        left_col.controls.append(glass_panel(content=_field_with_label("Комментарий", comment_field), radius=12, padding=ft.padding.all(14), bgcolor=GLASS["card_section"]))

        # Right column - Bug 8 fix: no expand
        right_col = ft.Column(spacing=14, tight=True)

        # Section Сроки — no always open calendar (Bug 9 fix), only fields that open shared global calendar
        sroki_content = ft.Column(controls=[
            ft.Text("Сроки", size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
            _field_with_label("Следующая дата исполнения", due_box),
            cycle_hint,
            _field_with_label("Конечная дата", end_box),
        ], spacing=8, tight=True)
        right_col.controls.append(glass_panel(content=sroki_content, radius=12, padding=ft.padding.all(14), bgcolor=GLASS["card_section"]))

        # Pункты задания
        tasks_section = ft.Column(controls=[
            ft.Row(controls=[ft.Icon(ft.icons.FORMAT_LIST_BULLETED, size=16, color=GLASS["text"]), ft.Text("Пункты задания", size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"]), ft.Container(expand=True), ft.ElevatedButton("+ Добавить пункт", bgcolor=GLASS["surface_alt"], color=GLASS["accent"], height=32, style=ft.ButtonStyle(side=ft.BorderSide(1, GLASS["border"]), shape=ft.RoundedRectangleBorder(radius=8)), on_click=_add_task)], spacing=6, tight=True),
            tasks_col,
        ], spacing=8, tight=True)
        right_col.controls.append(glass_panel(content=tasks_section, radius=12, padding=ft.padding.all(14), bgcolor=GLASS["card_section"]))

        # Milestones
        if (ctl.control_type if ctl else ONE_TIME) == PERIODIC or True:
            miles_section = ft.Column(controls=[
                ft.Row(controls=[ft.Icon(ft.icons.TIMELINE, size=15, color=GLASS["text"]), ft.Text("Промежуточные точки", size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"]), ft.Container(expand=True), ft.ElevatedButton("+ Добавить точку", bgcolor=GLASS["surface_alt"], color=GLASS["accent"], height=28, style=ft.ButtonStyle(side=ft.BorderSide(1, GLASS["border"]), shape=ft.RoundedRectangleBorder(radius=8)), on_click=_add_mile)], spacing=6, tight=True),
                milestones_col,
            ], spacing=8, tight=True)
            right_col.controls.append(glass_panel(content=miles_section, radius=12, padding=ft.padding.all(14), bgcolor=GLASS["card_section"]))

        # Scan
        scan_section = ft.Column(controls=[
            ft.Row(controls=[ft.Icon(ft.icons.ATTACH_FILE, size=15, color=GLASS["text"]), ft.Text("Скан задания", size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"]), ft.Container(expand=True), ft.ElevatedButton("Прикрепить файл", bgcolor=GLASS["surface_alt"], color=GLASS["accent"], height=32, style=ft.ButtonStyle(side=ft.BorderSide(1, GLASS["border"]), shape=ft.RoundedRectangleBorder(radius=8)), icon=ft.icons.ATTACH_FILE, on_click=_pick_attach)], spacing=6, tight=True),
            attach_col,
        ], spacing=8, tight=True)
        right_col.controls.append(glass_panel(content=scan_section, radius=12, padding=ft.padding.all(14), bgcolor=GLASS["card_section"]))

        # Decide layout based on page width
        # Bug 8 fix: no expand inside scroll, fixed widths
        try:
            is_narrow = (page.width or 1280) < 1100
        except Exception:
            is_narrow = False

        # Left ~500 (55% of 920 panel inner ~888), right ~374 (45%)
        if is_narrow:
            middle_content = ft.Column(controls=[left_col, right_col], spacing=14, tight=True)
        else:
            middle_content = ft.Row(controls=[
                ft.Container(content=left_col, width=500, alignment=ft.alignment.top_left),
                ft.Container(content=right_col, width=374, alignment=ft.alignment.top_left),
            ], spacing=14, tight=True, vertical_alignment=ft.CrossAxisAlignment.START)

        # Middle scroll: bounded by the card's fixed height (via expand in the bounded
        # card Column), so its inner scroll column scrolls internally instead of growing
        # unbounded / collapsing. Matches the control_card_modal pattern.
        middle_scroll = ft.Container(
            content=ft.Column(controls=[middle_content], spacing=0, tight=True, scroll=ft.ScrollMode.AUTO),
            expand=True,
        )

        # Header and footer fixed
        header = ft.Container(
            content=ft.Row(controls=[
                ft.Icon(ft.icons.EDIT_DOCUMENT if not is_new else ft.icons.ADD_CIRCLE_OUTLINE, size=20, color=GLASS["text"]),
                ft.Text("Карточка контроля", size=17, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
                ft.Container(expand=True),
                ft.Text(ctl.incoming_number if ctl and not is_new else "", size=16, weight=ft.FontWeight.W_600, color=GLASS["text_secondary"]),
                ft.IconButton(icon=ft.icons.CLOSE, icon_color=GLASS["text_secondary"], icon_size=18, on_click=_hide_detail),
            ], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.only(bottom=12),
            border=ft.border.only(bottom=ft.BorderSide(1, GLASS["border_divider"])),
        )

        footer = ft.Container(
            content=ft.Row(controls=[
                ft.ElevatedButton("Удалить", icon=ft.icons.DELETE_FOREVER, bgcolor=with_alpha(GLASS["overdue"], "22"), color=GLASS["overdue"], style=ft.ButtonStyle(side=ft.BorderSide(1, GLASS["overdue"]), shape=ft.RoundedRectangleBorder(radius=10)), visible=not is_new, on_click=_delete_detail) if not is_new else ft.Container(),
                ft.Container(expand=True),
                ft.TextButton("Отмена", on_click=_hide_detail, style=ft.ButtonStyle(color=GLASS["text_secondary"])),
                ft.ElevatedButton("Сохранить", icon=ft.icons.SAVE, bgcolor=GLASS["accent"], color="#ffffff", style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)), on_click=_save_detail, height=40),
            ], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.only(top=12),
            border=ft.border.only(top=ft.BorderSide(1, GLASS["border_divider"])),
        )

        # Root column fills the fixed-height card; middle_scroll (expand=True) takes the
        # remaining space between header and footer and scrolls internally.
        detail_content = ft.Column(controls=[header, middle_scroll, footer], spacing=0, tight=True, expand=True)

        detail_card.content = detail_content
        try:
            win_h = page.window.height or 860
        except Exception:
            win_h = 860
        card_max_h = min(780, int(win_h * 0.9))
        detail_card.width = 920
        detail_card.height = card_max_h
        detail_overlay_container.visible = True
        try:
            _safe_update(detail_overlay_container)
        except Exception:
            try:
                page.update()
            except Exception:
                traceback.print_exc()
        _refresh_cycle_hint()

    # Actions
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
                show_toast(page, "Постоянный контроль завершён", icon=ft.icons.CHECK_CIRCLE)
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
            show_toast(page, "Контроль исполнен и в архив", icon=ft.icons.CHECK_CIRCLE)
        _rebuild_table()
        _refresh_counters()

    def _extend(ctl: Control):
        try:
            _do_extend(ctl)
        except Exception:
            traceback.print_exc()

    def _do_extend(ctl: Control):
        days_field = _glass_textfield(value=str(ctl.period_days if ctl.control_type == PERIODIC else 7), hint="Продлить на (дней)", width=160)
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
                traceback.print_exc()
        dialog = ft.AlertDialog(modal=True, bgcolor=GLASS["surface_solid"], title=ft.Text("Продлить срок", size=16, weight=ft.FontWeight.BOLD, color=GLASS["text"]), content=ft.Container(content=days_field, width=220), actions=[ft.TextButton("Отмена", on_click=_close), ft.ElevatedButton("Продлить", bgcolor=GLASS["accent"], color="#ffffff", on_click=_confirm)], shape=ft.RoundedRectangleBorder(radius=12))
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
                traceback.print_exc()
        dialog = ft.AlertDialog(modal=True, bgcolor=GLASS["surface_solid"], title=ft.Text("Переместить в архив", size=16, weight=ft.FontWeight.BOLD, color=GLASS["text"]), content=ft.Text(f"Переместить «{ctl.incoming_number}» в архив?", size=13, color=GLASS["text"]), actions=[ft.TextButton("Отмена", on_click=_close), ft.ElevatedButton("В архив", bgcolor=GLASS["accent"], color="#ffffff", on_click=_confirm)], shape=ft.RoundedRectangleBorder(radius=12))
        page.open(dialog)

    def _restore(ctl: Control):
        try:
            restore_control(ctl)
            _persist(state["controls"])
            _rebuild_table()
            _refresh_counters()
            from ui.toast import show_toast
            show_toast(page, "Восстановлен", icon=ft.icons.RESTORE)
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
                traceback.print_exc()
        dialog = ft.AlertDialog(modal=True, bgcolor=GLASS["surface_solid"], title=ft.Text("Удалить навсегда", size=16, weight=ft.FontWeight.BOLD, color=GLASS["text"]), content=ft.Text(f"Удалить «{ctl.incoming_number}» безвозвратно?", size=13, color=GLASS["text"]), actions=[ft.TextButton("Отмена", on_click=_close), ft.ElevatedButton("Удалить", bgcolor=GLASS["overdue"], color="#ffffff", on_click=_confirm)], shape=ft.RoundedRectangleBorder(radius=12))
        page.open(dialog)

    # Export / Import
    export_mode_dd = _glass_dropdown("Как в таблице", 170, [ft.dropdown.Option("table", "Как в таблице"), ft.dropdown.Option("full", "Полный (round-trip)")], value="table")

    def _on_export_picked(e):
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
            show_error_toast(page, f"Ошибка: {ex}")

    def _on_import_picked(e):
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
            page._controls_import_picker.pick_files(dialog_title="Выбрать Excel для импорта", allowed_extensions=["xlsx"], allow_multiple=False)
        except Exception as ex:
            print(f"[CONTROLS_TAB] import trigger error: {ex}")

    def _preview_import(path: str):
        from ui.toast import show_error_toast
        parsed, stats = import_from_excel(path, state["controls"])
        if not parsed and stats["errors"] == 0:
            show_error_toast(page, "Не найдено ни одного контроля")
            return
        preview_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=300)
        for c in parsed[:20]:
            preview_list.controls.append(
                glass_panel(
                    content=ft.Row(controls=[ft.Text(c.incoming_number or "—", size=11, color=GLASS["text_secondary"], width=90, no_wrap=True), ft.Text(c.content or "—", size=11, color=GLASS["text"], expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, tooltip=c.content), ft.Text(_type_label(c), size=10, color=GLASS["text_secondary"], width=80, no_wrap=True)], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    radius=8, padding=ft.padding.symmetric(horizontal=8, vertical=6), bgcolor=GLASS["surface_alt"],
                )
            )
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
                traceback.print_exc()
        dialog = ft.AlertDialog(modal=True, bgcolor=GLASS["surface_solid"], title=ft.Row(controls=[ft.Icon(ft.icons.UPLOAD_FILE, size=20, color=GLASS["text"]), ft.Text("Импорт — предпросмотр", size=15, weight=ft.FontWeight.BOLD, color=GLASS["text"])], spacing=8, tight=True), content=ft.Container(width=560, content=ft.Column(controls=[summary, preview_list], spacing=8, tight=True)), actions=[ft.TextButton("Отмена", on_click=_close), ft.ElevatedButton("Импортировать", bgcolor=GLASS["accent"], color="#ffffff", on_click=_confirm)], shape=ft.RoundedRectangleBorder(radius=12))
        page.open(dialog)

    # Settings
    def _open_settings(e=None):
        from .controls_settings_modal import create_controls_settings_modal
        def on_apply_inner(new_settings):
            nonlocal soon_days
            settings.clear()
            settings.update(new_settings)
            save_settings(new_settings)
            soon_days = int(new_settings.get("soon_days", 3) or 3)
            initiators.clear()
            initiators.extend(get_initiators(settings))
            try:
                initiator_filter_dd.options = [ft.dropdown.Option("all", "Все инициаторы")] + [ft.dropdown.Option(i) for i in initiators]
                _safe_update(initiator_filter_dd)
            except Exception:
                traceback.print_exc()
            _update_sync_ui()
            _load_initial()
            _rebuild_table()
            _refresh_counters()
        dialog = create_controls_settings_modal(page, settings, on_apply_inner)
        page.open(dialog)

    def _add_control(e=None):
        _open_detail(None)

    # Title row
    add_btn = ft.ElevatedButton(text="Добавить контроль", icon=ft.icons.ADD_CIRCLE_OUTLINE, bgcolor=GLASS["accent"], color="#ffffff", height=40, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=ft.padding.symmetric(horizontal=16)), on_click=_add_control)
    import_btn = ft.ElevatedButton(text="Импорт Excel", icon=ft.icons.UPLOAD_FILE, bgcolor=GLASS["surface"], color=GLASS["text"], height=40, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), side=ft.BorderSide(1, GLASS["border"]), padding=ft.padding.symmetric(horizontal=12)), on_click=_import)
    export_btn = ft.ElevatedButton(text="Экспорт Excel", icon=ft.icons.FILE_DOWNLOAD_OUTLINED, bgcolor=GLASS["in_progress"], color=GLASS["surface_solid"], height=40, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=ft.padding.symmetric(horizontal=14)), on_click=_export)
    settings_btn = ft.IconButton(icon=ft.icons.SETTINGS_OUTLINED, icon_size=20, icon_color=GLASS["text_secondary"], tooltip="Настройки", style=ft.ButtonStyle(bgcolor=GLASS["surface"], shape=ft.RoundedRectangleBorder(radius=10), side=ft.BorderSide(1, GLASS["border"])), on_click=_open_settings)

    title_content = ft.Row(controls=[
        ft.Icon(ft.icons.RULE_FOLDER, size=20, color=GLASS["text"]),
        ft.Text("Контроли", size=20, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
        ft.Container(width=10),
        sync_dot, ft.Container(width=4), sync_label,
        ft.Container(expand=True),
        add_btn, import_btn, export_mode_dd, export_btn, settings_btn,
    ], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    title_row = glass_panel(content=title_content, height=60, radius=12, padding=ft.padding.symmetric(horizontal=16, vertical=8))

    # Main column
    main_column = ft.Column(
        controls=[
            title_row,
            ft.Container(height=4),
            filter_row1,
            ft.Container(height=4),
            filter_row2,
            ft.Container(height=8),
            counters_row,
            ft.Container(height=8),
            table_container,
            ft.Container(height=30),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
    tab_bg = ft.Container(content=main_column, bgcolor=GLASS["bg"], expand=True, padding=ft.padding.only(left=12, right=12, top=8, bottom=8))
    # Filter calendar overlay at tab level (Bug 6 fix: shared calendar over all, not clipped inside 120px field)
    tab_stack = ft.Stack(controls=[tab_bg, filter_cal_root, detail_overlay_container], expand=True)
    tab_content = ft.Column(controls=[tab_stack], spacing=0, expand=True)

    # Background polling
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
                traceback.print_exc()

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
                    parts.append(f"Сегодня: {len(today_n)}")
                if soon:
                    parts.append(f"Скоро: {len(soon)}")
                show_toast(page, " · ".join(parts), icon=ft.icons.NOTIFICATIONS_ACTIVE)
            except Exception:
                traceback.print_exc()

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
                traceback.print_exc()
    try:
        page.on_resize = _combined_resize
    except Exception:
            traceback.print_exc()

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
                parts.append(f"Сегодня: {len(today0)}")
            if soon0:
                parts.append(f"Скоро: {len(soon0)}")
            show_toast(page, " · ".join(parts), icon=ft.icons.NOTIFICATIONS_ACTIVE)
        state["last_overdue"] = len(overdue0)
    except Exception:
            traceback.print_exc()

    page._controls_poll_stop = _poll_stop
    print("[CONTROLS_TAB] Glass Dark v2 ready")
    return tab_content

# ui/controls/controls_tab.py
# Вкладка «Контроли» (фаза 2): список, фильтры, поиск, сортировка,
# активные/архив, импорт/экспорт Excel, уведомления, сетевая синхронизация.
import threading
import time
import traceback
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict

import flet as ft

from core.constants import COLORS
from core.controls_models import (
    Control, PERIODIC, ONE_TIME,
    effective_due_date, deadline_status, parse_date, short_name,
    STATUS_LABELS, STATUS_COLORS,
    OVERDUE, TODAY, SOON, IN_PROGRESS, DONE, COMPLETED, NO_DATE,
    ARCHIVE_DONE, ARCHIVE_DELETED,
)
from core.controls_data import (
    load_controls, save_controls, load_settings,
    get_criminalist_names, get_initiators,
    archive_control, restore_control,
    delete_all_attachments,
    read_shared_controls, write_shared_controls, get_shared_mtime,
    sync_attachments_from_shared,
)
from core.controls_exporter import ControlsExcelExporter, import_from_excel
from .control_card_modal import create_control_card_modal

# Иконки статусов (реальные ft.icons.*; в модели только ключи)
STATUS_ICONS = {
    OVERDUE: ft.icons.EVENT_BUSY,
    TODAY: ft.icons.NOTIFICATIONS_ACTIVE,
    SOON: ft.icons.HOURGLASS_BOTTOM,
    IN_PROGRESS: ft.icons.HOURGLASS_TOP,
    DONE: ft.icons.CHECK_CIRCLE,
    COMPLETED: ft.icons.CHECK_CIRCLE_OUTLINE,
    NO_DATE: ft.icons.REMOVE_CIRCLE_OUTLINE,
}

# Минимальные фиксированные ширины служебных колонок
_FIXED = {
    "bar": 6, "num": 38, "incoming": 108, "receive": 96, "initiator": 138,
    "controller": 140, "type": 96, "due": 96, "status": 112, "actions": 110,
}
_ROW_HEIGHT = 58
_TAB_HORIZONTAL_PADDING = 40  # main.py padding 20+20


def _display_date(iso: Optional[str]) -> str:
    d = parse_date(iso)
    return d.strftime("%d.%m.%Y") if d else "—"


def _type_label(ctl: Control) -> str:
    return "постоянный" if ctl.control_type == PERIODIC else "разовый"


def _reason_label(reason: str) -> str:
    return "Исполнен" if reason == ARCHIVE_DONE else ("Удалён" if reason == ARCHIVE_DELETED else "")


def create_controls_tab(page: ft.Page) -> ft.Column:
    """Создать вкладку «Контроли». Возвращает ft.Column."""
    print("[CONTROLS_TAB] Initializing controls tab (phase 2)")

    settings = load_settings()
    soon_days = int(settings.get("soon_days", 3) or 3)
    available_names = get_criminalist_names()
    initiators = get_initiators(settings)
    network_user = settings.get("network_user", "") or ""
    network_role = settings.get("network_role", "admin")

    # ── Состояние ────────────────────────────────────────────────
    state = {
        "controls": [],
        "mode": "active",          # active | archive
        "sort_key": "due_date",
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
        "editing": False,          # открыта карточка → не трогать таблицу из потока
    }

    rows_column = ft.Column(spacing=4, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    sync_label = ft.Text("Локально", size=11, color=COLORS["text_secondary"])
    sync_dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=COLORS["text_muted"])

    # ── Геометрия колонок от ширины окна ─────────────────────────
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

    # ── Дата-пикер фильтров ─────────────────────────────────────
    filter_date_picker = ft.DatePicker(
        first_date=datetime(2020, 1, 1), last_date=datetime(2035, 12, 31), on_change=None,
    )
    page.overlay.append(filter_date_picker)
    _fd_target = {"setter": None}

    def _pick_filter_date(setter):
        _fd_target["setter"] = setter
        filter_date_picker.pick_date()

    def _on_filter_date(e):
        setter = _fd_target["setter"]
        if setter is not None:
            try:
                iso = e.control.value.strftime("%Y-%m-%d")
            except Exception:
                iso = None
            setter(iso)
    filter_date_picker.on_change = _on_filter_date

    from_field = ft.Text("С: —", size=11, color=COLORS["text_secondary"], width=56, no_wrap=True)
    to_field = ft.Text("По: —", size=11, color=COLORS["text_secondary"], width=56, no_wrap=True)

    def _clear_from(e=None):
        state["f_from"] = None
        from_field.value = "С: —"
        from_field.update()
        _apply_filters()

    def _clear_to(e=None):
        state["f_to"] = None
        to_field.value = "По: —"
        to_field.update()
        _apply_filters()

    def _set_from(iso):
        state["f_from"] = iso
        from_field.value = f"С: {_display_date(iso)}"
        from_field.update()
        _apply_filters()

    def _set_to(iso):
        state["f_to"] = iso
        to_field.value = f"По: {_display_date(iso)}"
        to_field.update()
        _apply_filters()

    # ── Синхронизация ───────────────────────────────────────────
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
            # Подтянуть недостающие вложения из общей папки
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

    # ── Роль «пользователь»: только свои контроли ───────────────
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

    # ── Фильтрация / сортировка ─────────────────────────────────
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
                fd = parse_date(state["f_from"])
                if dd is not None and dd < fd:
                    return False
            if state["f_to"]:
                dd = effective_due_date(ctl)
                td = parse_date(state["f_to"])
                if dd is not None and dd > td:
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
                return (base.index(ctl) if ctl in base else 0,)
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
                order = {OVERDUE: 0, TODAY: 1, SOON: 2, IN_PROGRESS: 3,
                         NO_DATE: 4, DONE: 5, COMPLETED: 6}
                return (order.get(deadline_status(ctl, soon_days), 9),)
            d = effective_due_date(ctl)
            return (d.toordinal() if d else 999999,)

        result.sort(key=_sort_val, reverse=state["sort_reverse"])
        return result

    def _apply_filters():
        _rebuild_table()

    # ── Построение строки ───────────────────────────────────────
    def _cell(text: str, width: int, color=COLORS["text"], size=12,
              bold=False, center=False, tooltip=None, max_lines=1) -> ft.Container:
        return ft.Container(
            content=ft.Text(text, size=size, color=color,
                            weight=ft.FontWeight.W_600 if bold else None,
                            no_wrap=not center, max_lines=max_lines,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            tooltip=tooltip or (text if len(text) > 12 else None)),
            width=width, padding=ft.padding.only(left=6, right=4),
            alignment=ft.alignment.center if center else ft.alignment.center_left,
        )

    def _action_icon(icon, color, tooltip, handler):
        return ft.IconButton(icon=icon, icon_size=16, icon_color=color, tooltip=tooltip,
                             width=26, height=26, padding=0, on_click=handler)

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
                    ft.Text(str(len(ctl.attachments)), size=10, color=COLORS["btn_save"],
                            no_wrap=True),
                ], spacing=2, tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER),
                width=22,
            ))

        is_archive = state["mode"] == "archive"
        type_cell = _cell(_type_label(ctl), _W["type"], color=COLORS["text_secondary"])
        if is_archive:
            reason = ctl.archive_reason or ""
            reason_text = _reason_label(reason)
            if ctl.archived_at:
                reason_text = f"{reason_text} · {_display_date(ctl.archived_at)}"
            type_cell = _cell(reason_text, _W["type"], color=COLORS["text_secondary"],
                              tooltip=reason)
        actions = []
        if is_archive:
            actions.append(_action_icon(ft.icons.RESTORE, COLORS["received"],
                                        "Восстановить", lambda e, c=ctl: _restore(c)))
            actions.append(_action_icon(ft.icons.DELETE_FOREVER, "#f87171",
                                        "Удалить навсегда", lambda e, c=ctl: _delete_forever(c)))
        else:
            actions.append(_action_icon(ft.icons.CHECK_CIRCLE_OUTLINE, COLORS["received"],
                                        "Отметить исполненным", lambda e, c=ctl: _complete(c)))
            actions.append(_action_icon(ft.icons.UPDATE_OUTLINED, COLORS["in_progress"],
                                        "Продлить срок", lambda e, c=ctl: _extend(c)))
            actions.append(_action_icon(ft.icons.DELETE_OUTLINE, "#f87171", "В архив",
                                        lambda e, c=ctl: _confirm_delete(c)))

        row_controls = [
            ft.Container(width=_W["bar"], height=34, bgcolor=color, border_radius=2),
            _cell(str(num), _W["num"], center=True, color=COLORS["text_secondary"]),
            _cell(ctl.incoming_number or "—", _W["incoming"], bold=True,
                  tooltip=ctl.incoming_number),
            _cell(_display_date(ctl.receive_date), _W["receive"],
                  color=COLORS["text_secondary"]),
            _cell(short_name(ctl.initiator) if ctl.initiator else "—", _W["initiator"],
                  tooltip=ctl.initiator),
            ft.Row(controls=content_controls, spacing=2, tight=True,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER,
                   alignment=ft.MainAxisAlignment.START),
            _cell(", ".join(short_name(x) for x in ctl.executors) or "—", _W["executors"],
                  tooltip=", ".join(ctl.executors)),
            _cell(short_name(ctl.controller) if ctl.controller else "—", _W["controller"],
                  tooltip=ctl.controller),
            type_cell,
            _cell(_display_date(effective_due_date(ctl)), _W["due"], bold=True),
            ft.Container(
                content=ft.Row(controls=[
                    ft.Icon(STATUS_ICONS.get(status, ft.icons.REMOVE_CIRCLE_OUTLINE),
                            size=12, color=color),
                    ft.Text(STATUS_LABELS.get(status, status), size=10, color=color,
                            weight=ft.FontWeight.W_600, no_wrap=True),
                ], spacing=3, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                width=_W["status"], height=24, border_radius=12,
                padding=ft.padding.symmetric(horizontal=6),
                alignment=ft.alignment.center, bgcolor=f"{color}22",
            ),
        ]
        row_controls.append(ft.Row(controls=actions, spacing=0, tight=True,
                                   vertical_alignment=ft.CrossAxisAlignment.CENTER))

        return ft.Container(
            content=ft.Row(controls=row_controls, spacing=2, tight=True,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=_ROW_HEIGHT, bgcolor=COLORS["card"],
            border=ft.border.all(1, COLORS["border"]), border_radius=8,
            padding=ft.padding.symmetric(horizontal=4, vertical=4),
            on_click=lambda e, c=ctl: _open_card(c),
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

    # ── Действия ────────────────────────────────────────────────
    def _open_card(ctl: Optional[Control]):
        state["editing"] = True

        def on_save(c: Control):
            if ctl is None:
                state["controls"].append(c)
            else:
                for idx, x in enumerate(state["controls"]):
                    if x.id == c.id:
                        state["controls"][idx] = c
                        break
            _persist(state["controls"])
            state["editing"] = False
            _rebuild_table()
            _refresh_counters()

        def on_delete(c: Control):
            archive_control(c, ARCHIVE_DELETED)
            _persist(state["controls"])
            state["editing"] = False
            _rebuild_table()
            _refresh_counters()

        dialog = create_control_card_modal(
            page, ctl, available_names, on_save,
            on_delete=on_delete if ctl is not None else None,
            settings=settings, initiators=initiators,
            on_cancel=lambda: state.update(editing=False),
        )
        page.open(dialog)

    def _complete(ctl: Control):
        try:
            _do_complete(ctl)
        except Exception:
            print("[CONTROLS_TAB] _complete error:")
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
                show_toast(page, "Постоянный контроль завершён (конечная дата)",
                           icon=ft.icons.CHECK_CIRCLE)
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
                show_toast(page, f"Срок продлён до {_display_date(ctl.due_date)}",
                           icon=ft.icons.UPDATE)
        else:
            ctl.done = True
            ctl.done_date = today.isoformat()
            ctl.updated_at = datetime.now().isoformat()
            archive_control(ctl, ARCHIVE_DONE)
            _persist(state["controls"])
            from ui.toast import show_toast
            show_toast(page, "Контроль исполнен и перемещён в архив",
                       icon=ft.icons.CHECK_CIRCLE)
        _rebuild_table()
        _refresh_counters()

    def _extend(ctl: Control):
        try:
            _do_extend(ctl)
        except Exception:
            print("[CONTROLS_TAB] _extend error:")
            traceback.print_exc()

    def _do_extend(ctl: Control):
        extend_days = {"value": str(ctl.period_days if ctl.control_type == PERIODIC else 7)}
        days_field = ft.TextField(
            value=extend_days["value"], label="Продлить на (дней)",
            label_style=ft.TextStyle(color=COLORS["text_secondary"]),
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
            keyboard_type=ft.KeyboardType.NUMBER, width=160,
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
                _cleanup_dialog(dialog)
                _rebuild_table()
                _refresh_counters()
                from ui.toast import show_toast
                show_toast(page, f"Срок продлён до {_display_date(ctl.due_date)}",
                           icon=ft.icons.UPDATE)
            except Exception:
                print("[CONTROLS_TAB] _extend confirm error:")
                traceback.print_exc()

        def _close(e=None):
            try:
                page.close(dialog)
                _cleanup_dialog(dialog)
            except Exception:
                print("[CONTROLS_TAB] close error:")
                traceback.print_exc()

        dialog = ft.AlertDialog(
            modal=True, bgcolor=COLORS["primary_light"],
            title=ft.Text("Продлить срок", size=16, weight=ft.FontWeight.BOLD,
                          color=COLORS["text"]),
            content=ft.Container(content=days_field, width=220),
            actions=[
                ft.TextButton("Отмена", on_click=_close),
                ft.ElevatedButton("Продлить", bgcolor=COLORS["btn_save"],
                                  color=COLORS["text_light"], on_click=_confirm),
            ],
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
                _cleanup_dialog(dialog)
                _rebuild_table()
                _refresh_counters()
                from ui.toast import show_toast
                show_toast(page, f"В архив: {ctl.incoming_number}", icon=ft.icons.ARCHIVE)
            except Exception:
                print("[CONTROLS_TAB] _confirm_delete error:")
                traceback.print_exc()

        def _close(e=None):
            try:
                page.close(dialog)
                _cleanup_dialog(dialog)
            except Exception:
                print("[CONTROLS_TAB] close error:")
                traceback.print_exc()

        dialog = ft.AlertDialog(
            modal=True, bgcolor=COLORS["primary_light"],
            title=ft.Text("Переместить в архив", size=16, weight=ft.FontWeight.BOLD,
                          color=COLORS["text"]),
            content=ft.Text(f"Переместить контроль «{ctl.incoming_number}» в архив?",
                            size=13, color=COLORS["text"]),
            actions=[
                ft.TextButton("Отмена", on_click=_close),
                ft.ElevatedButton("В архив", icon=ft.icons.ARCHIVE,
                                  bgcolor=COLORS["btn_save"], color=COLORS["text_light"],
                                  on_click=_confirm),
            ],
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
            print("[CONTROLS_TAB] _restore error:")
            traceback.print_exc()

    def _delete_forever(ctl: Control):
        def _confirm(e=None):
            try:
                delete_all_attachments(ctl.id, settings)
                state["controls"] = [c for c in state["controls"] if c.id != ctl.id]
                _persist(state["controls"])
                page.close(dialog)
                _cleanup_dialog(dialog)
                _rebuild_table()
                _refresh_counters()
                from ui.toast import show_toast
                show_toast(page, "Удалён навсегда", icon=ft.icons.DELETE_FOREVER)
            except Exception:
                print("[CONTROLS_TAB] _delete_forever error:")
                traceback.print_exc()

        def _close(e=None):
            try:
                page.close(dialog)
                _cleanup_dialog(dialog)
            except Exception:
                print("[CONTROLS_TAB] close error:")
                traceback.print_exc()

        dialog = ft.AlertDialog(
            modal=True, bgcolor=COLORS["primary_light"],
            title=ft.Text("Удалить навсегда", size=16, weight=ft.FontWeight.BOLD,
                          color=COLORS["text"]),
            content=ft.Text(
                f"Удалить «{ctl.incoming_number}» безвозвратно? Вложения также будут удалены.",
                size=13, color=COLORS["text"]),
            actions=[
                ft.TextButton("Отмена", on_click=_close),
                ft.ElevatedButton("Удалить навсегда", icon=ft.icons.DELETE_FOREVER,
                                  bgcolor="#dc2626", color=COLORS["text_light"],
                                  on_click=_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        page.open(dialog)

    def _cleanup_dialog(dlg):
        try:
            if dlg in page.overlay:
                page.overlay.remove(dlg)
        except Exception:
            pass

    # ── Счётчики ────────────────────────────────────────────────
    counter_refs: Dict[str, ft.Container] = {}

    def _counts() -> dict:
        res = {"all": 0, OVERDUE: 0, TODAY: 0, SOON: 0, IN_PROGRESS: 0,
               DONE: 0, COMPLETED: 0}
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
            row = btn.content
            try:
                row.controls[1].color = fg
                badge = row.controls[2]
                # Бейдж всегда тёмный с читаемым светлым числом — чтобы не было
                # «жёлтого пятна» при выбранном состоянии.
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
            row = btn.content
            try:
                badge = row.controls[2]
                badge.content.value = str(counts.get(key, 0))
            except Exception:
                pass
        _restyle_counters()

    def _mk_counter(key: str, label: str, icon) -> ft.Container:
        counts = _counts()
        fg = COLORS["text_secondary"]
        badge = ft.Container(
            content=ft.Text(str(counts.get(key, 0)), size=11, color=COLORS["text_light"],
                            weight=ft.FontWeight.W_600, no_wrap=True),
            height=20, padding=ft.padding.symmetric(horizontal=7), border_radius=10,
            alignment=ft.alignment.center, bgcolor=COLORS["card"],
        )
        btn = ft.Container(
            content=ft.Row(controls=[
                ft.Icon(icon, size=13, color=fg),
                ft.Text(label, size=11, weight=ft.FontWeight.W_600, color=fg, no_wrap=True),
                badge,
            ], spacing=5, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=30, padding=ft.padding.symmetric(horizontal=10), border_radius=8,
            alignment=ft.alignment.center, bgcolor="transparent", ink=True,
            on_click=lambda e, v=key: _set_status_filter(v),
        )
        counter_refs[key] = btn
        return btn

    counter_statuses = [(OVERDUE, "Просрочено", ft.icons.EVENT_BUSY),
                        (TODAY, "Сегодня", ft.icons.NOTIFICATIONS_ACTIVE),
                        (SOON, "Скоро", ft.icons.HOURGLASS_BOTTOM),
                        (IN_PROGRESS, "В работе", ft.icons.HOURGLASS_TOP),
                        (DONE, "Исполнено", ft.icons.CHECK_CIRCLE)]
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

    # ── Переключатель Активные | Архив ──────────────────────────
    def _set_mode(mode: str):
        state["mode"] = mode
        _restyle_mode_buttons()
        _rebuild_table()
        _refresh_counters()

    mode_buttons: Dict[str, ft.Container] = {}

    def _restyle_mode_buttons():
        for m, btn in mode_buttons.items():
            selected = (state["mode"] == m)
            fg = COLORS["text_light"] if selected else COLORS["text_secondary"]
            btn.bgcolor = COLORS["btn_save"] if selected else "transparent"
            for ctl in btn.content.controls:
                if isinstance(ctl, ft.Text):
                    ctl.color = fg
                elif hasattr(ctl, "color"):
                    ctl.color = fg
            try:
                btn.update()
            except Exception:
                pass

    def _mk_mode_btn(mode: str, label: str, icon) -> ft.Container:
        btn = ft.Container(
            content=ft.Row(controls=[
                ft.Icon(icon, size=14,
                        color=COLORS["text_secondary"] if state["mode"] != mode
                        else COLORS["text_light"]),
                ft.Text(label, size=12, weight=ft.FontWeight.W_600,
                        color=COLORS["text_secondary"] if state["mode"] != mode
                        else COLORS["text_light"], no_wrap=True),
            ], spacing=5, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=30, padding=ft.padding.symmetric(horizontal=12), border_radius=8,
            alignment=ft.alignment.center,
            bgcolor=COLORS["btn_save"] if state["mode"] == mode else "transparent",
            ink=True, on_click=lambda e, m=mode: _set_mode(m),
        )
        mode_buttons[mode] = btn
        return btn

    mode_row = ft.Container(
        content=ft.Row(controls=[
            _mk_mode_btn("active", "Активные", ft.icons.PLAYLIST_PLAY),
            _mk_mode_btn("archive", "Архив", ft.icons.ARCHIVE_OUTLINED),
        ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.START),
        height=38, bgcolor=COLORS["primary_light"],
        border=ft.border.all(1, COLORS["border"]), border_radius=10,
        padding=ft.padding.symmetric(horizontal=3, vertical=3),
    )

    # ── Фильтры (два ряда) ──────────────────────────────────────
    search_field = ft.TextField(
        label="Поиск", prefix_icon=ft.icons.SEARCH,
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        width=230, height=38,
    )

    def _on_search(e=None):
        state["search"] = search_field.value or ""
        _apply_filters()
    search_field.on_change = _on_search

    def _mk_filter_dd(label, width, options, default="all"):
        return ft.Dropdown(
            label=label, width=width, height=38, value=default,
            options=options,
            label_style=ft.TextStyle(color=COLORS["text_secondary"]),
            border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"], color=COLORS["text"],
        )

    status_filter_dd = _mk_filter_dd("Статус", 170, [
        ft.dropdown.Option("all", "Все"), ft.dropdown.Option(OVERDUE, "Просрочено"),
        ft.dropdown.Option(TODAY, "Сегодня"), ft.dropdown.Option(SOON, "Скоро"),
        ft.dropdown.Option(IN_PROGRESS, "В работе"), ft.dropdown.Option(DONE, "Исполнено"),
        ft.dropdown.Option(COMPLETED, "Завершён"),
    ])
    type_filter_dd = _mk_filter_dd("Тип", 150, [
        ft.dropdown.Option("all", "Все"), ft.dropdown.Option(ONE_TIME, "Разовый"),
        ft.dropdown.Option(PERIODIC, "Постоянный"),
    ])
    initiator_filter_dd = _mk_filter_dd("Инициатор", 200,
                                        [ft.dropdown.Option("all", "Все")]
                                        + [ft.dropdown.Option(i) for i in initiators])
    executor_filter_dd = _mk_filter_dd(
        "Исполнитель", 200,
        [ft.dropdown.Option("all", "Все")]
        + [ft.dropdown.Option(n, short_name(n)) for n in available_names])
    controller_filter_dd = _mk_filter_dd(
        "За кем", 190,
        [ft.dropdown.Option("all", "Все")]
        + [ft.dropdown.Option(n, short_name(n)) for n in available_names])

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
        for dd in (status_filter_dd, type_filter_dd, initiator_filter_dd,
                   executor_filter_dd, controller_filter_dd):
            dd.value = "all"
        state.update(f_status="all", f_type="all", f_initiator="all",
                     f_executor="all", f_controller="all", f_from=None, f_to=None)
        from_field.value = "С: —"
        to_field.value = "По: —"
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
        ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.START),
        height=46, bgcolor=COLORS["card"],
        border=ft.border.all(1, COLORS["border"]), border_radius=12,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
    )
    filter_row2 = ft.Container(
        content=ft.Row(controls=[
            initiator_filter_dd, executor_filter_dd, controller_filter_dd,
            from_field,
            ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_size=16,
                          icon_color=COLORS["btn_save"], tooltip="С даты",
                          on_click=lambda e: _pick_filter_date(_set_from)),
            to_field,
            ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_size=16,
                          icon_color=COLORS["btn_save"], tooltip="По дату",
                          on_click=lambda e: _pick_filter_date(_set_to)),
            ft.Container(expand=True),
            ft.TextButton("Сброс", on_click=_reset_filters,
                          style=ft.ButtonStyle(color=COLORS["btn_save"])),
        ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.START),
        height=46, bgcolor=COLORS["card"],
        border=ft.border.all(1, COLORS["border"]), border_radius=12,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
    )

    # ── Шапка таблицы (сортировка) ──────────────────────────────
    header_row_ref = {"control": None}

    def _header_cell(text: str, width: int, key: str, center=False) -> ft.Container:
        arrow = "▲" if (state["sort_key"] == key and not state["sort_reverse"]) else \
                ("▼" if (state["sort_key"] == key and state["sort_reverse"]) else "")
        return ft.Container(
            content=ft.Text(f"{text} {arrow}".strip(), size=11,
                            weight=ft.FontWeight.BOLD, color=COLORS["text_secondary"],
                            no_wrap=True),
            width=width, padding=ft.padding.only(left=6, right=4),
            alignment=ft.alignment.center if center else ft.alignment.center_left,
            on_click=lambda e, k=key: _sort_by(k), tooltip="Сортировка",
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
            _header_cell("вх. № ВХСОП", _W["incoming"], "incoming"),
            _header_cell("Дата пост.", _W["receive"], "receive"),
            _header_cell("Инициатор", _W["initiator"], "initiator"),
            ft.Container(width=_W["content"], padding=ft.padding.only(left=6, right=4),
                         content=ft.Text("Содержание", size=11, weight=ft.FontWeight.BOLD,
                                         color=COLORS["text_secondary"], no_wrap=True)),
            ft.Container(width=_W["executors"], padding=ft.padding.only(left=6, right=4),
                         content=ft.Text("Исполнители", size=11, weight=ft.FontWeight.BOLD,
                                         color=COLORS["text_secondary"], no_wrap=True)),
            ft.Container(width=_W["controller"], padding=ft.padding.only(left=6, right=4),
                         content=ft.Text("За кем", size=11, weight=ft.FontWeight.BOLD,
                                         color=COLORS["text_secondary"], no_wrap=True)),
            _header_cell("Причина" if is_archive else "Тип", _W["type"], "type"),
            _header_cell("Дата исполн.", _W["due"], "due"),
            ft.Container(width=_W["status"], padding=ft.padding.only(left=6, right=4),
                         content=ft.Text("Статус", size=11, weight=ft.FontWeight.BOLD,
                                         color=COLORS["text_secondary"], no_wrap=True)),
        ]
        controls.append(ft.Container(width=_W["actions"]))
        header_row_ref["control"].controls = [ft.Row(
            controls=controls, spacing=2, tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER)]
        try:
            header_row_ref["control"].update()
        except Exception:
            pass

    header_row = ft.Container(
        content=ft.Row(controls=[], spacing=0, tight=True),
        height=30, bgcolor=COLORS["primary_light"],
        border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
        border_radius=8, padding=ft.padding.symmetric(horizontal=4, vertical=2),
    )
    header_row_ref["control"] = header_row

    # ── Импорт / экспорт ────────────────────────────────────────
    export_mode_dd = ft.Dropdown(
        value="table", width=180, height=38,
        options=[
            ft.dropdown.Option("table", "Как в таблице"),
            ft.dropdown.Option("full", "Полный (round-trip)"),
        ],
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
    )

    def _export(e=None):
        from ui.toast import show_export_toast, show_error_toast

        def _on_file_picked(res):
            if not res.path:
                return
            try:
                mode = (export_mode_dd.value or "table") == "full"
                ControlsExcelExporter().export(
                    _visible_base(), res.path, soon_days, full=mode)
                show_export_toast(page, "Контроли Excel")
            except Exception as ex:
                print(f"[CONTROLS_TAB] Export error: {ex}")
                show_error_toast(page, f"Ошибка экспорта: {ex}")

        if not hasattr(page, "_controls_file_picker"):
            picker = ft.FilePicker(on_result=_on_file_picked)
            page.overlay.append(picker)
            page._controls_file_picker = picker
        page._controls_file_picker.save_file(
            dialog_title="Сохранить контроли в Excel",
            file_name=f"controls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            allowed_extensions=["xlsx"],
        )

    def _import(e=None):
        def _on_file_picked(res):
            if not res.path:
                return
            _preview_import(res.path)

        if not hasattr(page, "_controls_import_picker"):
            picker = ft.FilePicker(on_result=_on_file_picked)
            page.overlay.append(picker)
            page._controls_import_picker = picker
        page._controls_import_picker.pick_files(
            dialog_title="Выбрать файл Excel для импорта",
            allowed_extensions=["xlsx"],
            allow_multiple=False,
        )

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
                        ft.Text(c.incoming_number or "—", size=11,
                                color=COLORS["text_secondary"], width=90, no_wrap=True),
                        ft.Text(c.content or "—", size=11, color=COLORS["text"],
                                expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
                                tooltip=c.content),
                        ft.Text(_type_label(c), size=10, color=COLORS["text_secondary"],
                                width=80, no_wrap=True),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       alignment=ft.MainAxisAlignment.START, tight=True),
                    bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]),
                    border_radius=6, padding=ft.padding.symmetric(horizontal=8, vertical=4),
                )
            )
        if len(parsed) > 20:
            preview_list.controls.append(ft.Text(f"… и ещё {len(parsed)-20}",
                                                 size=10, color=COLORS["text_muted"]))

        summary = ft.Text(
            f"Найдено: {len(parsed) + stats['skipped']}  ·  Импортируемо: {len(parsed)}  ·  "
            f"Пропущено дубликатов: {stats['skipped']}  ·  Ошибок: {stats['errors']}  ·  "
            f"Формат: {'полный' if stats['full_format'] else 'таблица'}",
            size=11, color=COLORS["text_secondary"],
        )

        def _confirm(e=None):
            try:
                for c in parsed:
                    state["controls"].append(c)
                _persist(state["controls"])
                page.close(dialog)
                _cleanup_dialog(dialog)
                _rebuild_table()
                _refresh_counters()
                from ui.toast import show_toast
                show_toast(page, f"Импортировано: {len(parsed)}",
                           icon=ft.icons.CLOUD_DOWNLOAD)
            except Exception:
                print("[CONTROLS_TAB] import confirm error:")
                traceback.print_exc()

        def _close(e=None):
            try:
                page.close(dialog)
                _cleanup_dialog(dialog)
            except Exception:
                print("[CONTROLS_TAB] close error:")
                traceback.print_exc()

        dialog = ft.AlertDialog(
            modal=True, bgcolor=COLORS["primary_light"],
            title=ft.Row(controls=[
                ft.Icon(ft.icons.UPLOAD_FILE, size=20, color=COLORS["text"]),
                ft.Text("Импорт из Excel — предпросмотр", size=15,
                        weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            content=ft.Container(
                width=560,
                content=ft.Column(controls=[
                    summary,
                    preview_list,
                ], spacing=8, tight=True),
            ),
            actions=[
                ft.TextButton("Отмена", on_click=_close),
                ft.ElevatedButton("Импортировать", icon=ft.icons.CLOUD_DOWNLOAD,
                                  bgcolor=COLORS["btn_save"], color=COLORS["text_light"],
                                  on_click=_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        page.open(dialog)

    # ── Настройки ───────────────────────────────────────────────
    def _open_settings(e=None):
        from .controls_settings_modal import create_controls_settings_modal

        def on_apply(new_settings):
            nonlocal settings, soon_days, initiators, network_user, network_role
            settings = new_settings
            soon_days = int(new_settings.get("soon_days", 3) or 3)
            initiators = get_initiators(settings)
            network_user = settings.get("network_user", "") or ""
            network_role = settings.get("network_role", "admin")
            # Обновить dropdown'ы инициатора/фильтров
            initiator_filter_dd.options = (
                [ft.dropdown.Option("all", "Все")]
                + [ft.dropdown.Option(i) for i in initiators])
            _update_sync_ui()
            _load_initial()
            _rebuild_table()
            _refresh_counters()
            try:
                initiator_filter_dd.update()
            except Exception:
                pass

        dialog = create_controls_settings_modal(page, settings, on_apply)
        page.open(dialog)

    def _add_control(e=None):
        _open_card(None)

    # ── Тулбар ──────────────────────────────────────────────────
    add_btn = ft.ElevatedButton(
        text="Добавить контроль", icon=ft.icons.ADD_CIRCLE_OUTLINE,
        bgcolor=COLORS["btn_save"], color=COLORS["text_light"], height=38,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                             padding=ft.padding.symmetric(horizontal=12)),
        on_click=_add_control,
    )
    import_btn = ft.ElevatedButton(
        text="Импорт Excel", icon=ft.icons.UPLOAD_FILE,
        bgcolor=COLORS["btn_save_hover"], color=COLORS["text_light"], height=38,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                             padding=ft.padding.symmetric(horizontal=12)),
        on_click=_import,
    )
    export_btn = ft.ElevatedButton(
        text="Экспорт Excel", icon=ft.icons.FILE_DOWNLOAD_OUTLINED,
        bgcolor=COLORS["btn_export"], color=COLORS["text_light"], height=38,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                             padding=ft.padding.symmetric(horizontal=12)),
        on_click=_export,
    )
    settings_btn = ft.IconButton(
        icon=ft.icons.SETTINGS_OUTLINED, icon_size=20, icon_color=COLORS["text_secondary"],
        tooltip="Настройки контролей (сроки, сеть)",
        style=ft.ButtonStyle(bgcolor=COLORS["primary_light"],
                             shape=ft.RoundedRectangleBorder(radius=10),
                             padding=ft.padding.all(8)),
        on_click=_open_settings,
    )

    title_row = ft.Container(
        content=ft.Row(controls=[
            ft.Icon(ft.icons.RULE_FOLDER, size=18, color=COLORS["text"]),
            ft.Text("Контроли", size=15, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ft.Container(width=8),
            sync_dot,
            ft.Container(width=4),
            sync_label,
            ft.Container(expand=True),
            add_btn,
            import_btn,
            export_mode_dd,
            export_btn,
            settings_btn,
        ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.START),
        height=46,
    )

    tab_content = ft.Column(
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
    )

    # ── Фоновый polling (сеть + уведомления) ────────────────────
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
        # При открытой карточке не перестраиваем таблицу из фонового потока
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

    # ── on_resize: пересчёт ширины колонок ──────────────────────
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

    # ── Инициализация ───────────────────────────────────────────
    _load_initial()
    _rebuild_table()
    _rebuild_header()
    _refresh_counters()

    # Фоновый поток: уведомления всегда, сетевой sync при включённой сети
    try:
        t = threading.Thread(target=_background_loop, daemon=True)
        t.start()
    except Exception as e:
        print(f"[CONTROLS_TAB] thread start error: {e}")

    # Первичное уведомление
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

    print("[CONTROLS_TAB] Controls tab created (phase 2)")
    return tab_content

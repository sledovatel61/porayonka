# ui/controls/controls_tab.py
# Вкладка «Контроли» — список контролей, фильтры, поиск, быстрые действия,
# уведомления о сроках и сетевая синхронизация (shared JSON + polling).
import threading
import time
import uuid
from datetime import date, datetime, timedelta
from typing import Callable, List, Optional, Dict

import flet as ft

from core.constants import COLORS
from core.controls_models import (
    Control, ControlTask, PERIODIC, ONE_TIME,
    effective_due_date, deadline_status, parse_date,
    STATUS_LABELS, STATUS_COLORS, STATUS_ICONS,
    OVERDUE, TODAY, SOON, IN_PROGRESS, DONE, NO_DATE,
)
from core.controls_data import (
    load_controls, save_controls, load_settings, save_settings,
    get_criminalist_names, get_initiators,
    read_shared_controls, write_shared_controls, get_shared_mtime,
    shared_file_exists,
)
from core.controls_exporter import ControlsExcelExporter
from .control_card_modal import create_control_card_modal

# Геометрия колонок таблицы (фиксированные ширины — безопасно в Flet 0.23.2)
_COL = {
    "bar": 6,
    "num": 38,
    "incoming": 104,
    "receive": 94,
    "initiator": 116,
    "content": 200,
    "executors": 138,
    "controller": 120,
    "type": 84,
    "due": 92,
    "status": 96,
    "actions": 104,
}
_ROW_HEIGHT = 46


def _display_date(iso: Optional[str]) -> str:
    d = parse_date(iso)
    return d.strftime("%d.%m.%Y") if d else "—"


def _type_label(ctl: Control) -> str:
    return "постоянный" if ctl.control_type == PERIODIC else "разовый"


def create_controls_tab(page: ft.Page) -> ft.Column:
    """Создать вкладку «Контроли». Возвращает ft.Column."""
    print("[CONTROLS_TAB] Initializing controls tab")

    settings = load_settings()
    soon_days = int(settings.get("soon_days", 3) or 3)
    available_names = get_criminalist_names()
    initiators = get_initiators()

    # ── Состояние ────────────────────────────────────────────────
    state = {
        "controls": [],
        "sort_key": "due_date",   # num | incoming | receive | initiator | due | status
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
        "notified_ids": set(),
        "last_sync": None,
        "network_ok": False,
    }

    rows_column = ft.Column(spacing=4, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    # ── Ссылки на шапку/индикатор ────────────────────────────────
    sync_label = ft.Text("Локально", size=11, color=COLORS["text_secondary"])
    sync_dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=COLORS["text_muted"])

    # ── Дата-пикер для фильтров дат ─────────────────────────────
    filter_date_picker = ft.DatePicker(
        first_date=datetime(2020, 1, 1), last_date=datetime(2035, 12, 31), on_change=None,
    )
    page.overlay.append(filter_date_picker)
    _filter_date_target = {"setter": None}

    def _pick_filter_date(setter):
        _filter_date_target["setter"] = setter
        filter_date_picker.pick_date()

    def _on_filter_date(e):
        setter = _filter_date_target["setter"]
        if setter is not None:
            try:
                iso = e.control.value.strftime("%Y-%m-%d")
            except Exception:
                iso = None
            setter(iso)
    filter_date_picker.on_change = _on_filter_date

    from_field = ft.Text("С: —", size=11, color=COLORS["text_secondary"], width=52, no_wrap=True)
    to_field = ft.Text("По: —", size=11, color=COLORS["text_secondary"], width=52, no_wrap=True)

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
        """Сохранить локально (+ в общий файл при сетевом режиме)."""
        save_controls(controls)
        state["last_sync"] = datetime.now()
        if settings.get("network_enabled") and to_shared:
            ok = write_shared_controls(controls, settings)
            state["network_ok"] = bool(ok)
            try:
                state["shared_mtime"] = get_shared_mtime(settings)
            except Exception:
                state["shared_mtime"] = None

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
        else:
            state["controls"] = load_controls()
        _update_sync_ui()

    def _update_sync_ui():
        net = settings.get("network_enabled")
        if not net:
            sync_label.value = "Локально"
            sync_dot.bgcolor = COLORS["text_muted"]
        else:
            role = "админ" if settings.get("network_role", "admin") == "admin" else "пользователь"
            sync_label.value = f"Сеть: {role}"
            sync_dot.bgcolor = COLORS["received"] if state["network_ok"] else "#f87171"
            if state["last_sync"]:
                sync_label.value += f" · {state['last_sync'].strftime('%H:%M:%S')}"
        try:
            sync_label.update()
            sync_dot.update()
        except Exception:
            pass

    # ── Уведомления о сроках ────────────────────────────────────
    def _notify_schedule():
        overdue = [c for c in state["controls"] if deadline_status(c, soon_days) == OVERDUE]
        today_n = [c for c in state["controls"] if deadline_status(c, soon_days) == TODAY]
        soon = [c for c in state["controls"] if deadline_status(c, soon_days) == SOON]
        if not overdue and not today_n and not soon:
            return
        parts = []
        if overdue:
            parts.append(f"Просрочено: {len(overdue)}")
        if today_n:
            parts.append(f"Сегодня истекает: {len(today_n)}")
        if soon:
            parts.append(f"Скоро: {len(soon)}")
        from ui.toast import show_toast
        show_toast(page, " · ".join(parts), icon=ft.icons.NOTIFICATIONS_ACTIVE)

    # ── Сетевой polling + периодические уведомления ─────────────
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
        # Файл изменился — перечитываем (last-write-wins)
        shared = read_shared_controls(settings)
        if shared:
            state["controls"] = shared
            state["shared_mtime"] = mtime
            state["last_sync"] = datetime.now()
            state["network_ok"] = True
            _update_sync_ui()
            _rebuild_table()
            _refresh_counters()
        else:
            state["network_ok"] = False
            _update_sync_ui()

    def _poll_notifications():
        overdue = [c for c in state["controls"] if deadline_status(c, soon_days) == OVERDUE]
        if len(overdue) > state["last_overdue"]:
            state["last_overdue"] = len(overdue)
            if overdue:
                from ui.toast import show_toast
                show_toast(page, f"Просрочено: {len(overdue)} контролей",
                           icon=ft.icons.NOTIFICATIONS_ACTIVE)

    # ── Фильтрация / сортировка ─────────────────────────────────
    def _filtered() -> List[Control]:
        ctl_list = state["controls"]
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
                    ctl.incoming_number, ctl.content, ctl.initiator,
                    ctl.controller, ctl.due_date or "",
                    " ".join(ctl.executors), " ".join(t.title for t in ctl.tasks),
                ]).lower()
                if q not in hay:
                    return False
            return True

        result = [c for c in ctl_list if _match(c)]

        def _sort_val(ctl: Control):
            k = state["sort_key"]
            if k == "num":
                return (ctl_list.index(ctl) if ctl in ctl_list else 0,)
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
                order = {OVERDUE: 0, TODAY: 1, SOON: 2, IN_PROGRESS: 3, NO_DATE: 4, DONE: 5}
                return (order.get(deadline_status(ctl, soon_days), 9),)
            # due_date (по умолчанию)
            d = effective_due_date(ctl)
            return (d.toordinal() if d else 999999,)

        result.sort(key=_sort_val, reverse=state["sort_reverse"])
        return result

    def _apply_filters():
        _rebuild_table()

    # ── Построение строки таблицы ───────────────────────────────
    def _cell(text: str, width: int, color=COLORS["text"], size=11,
              bold=False, center=False, tooltip=None, max_lines=1) -> ft.Container:
        return ft.Container(
            content=ft.Text(
                text, size=size, color=color, weight=ft.FontWeight.W_600 if bold else None,
                no_wrap=not center,
                max_lines=max_lines,
                overflow=ft.TextOverflow.ELLIPSIS,
                tooltip=tooltip or (text if len(text) > 12 else None),
            ),
            width=width,
            padding=ft.padding.only(left=6, right=4),
            alignment=ft.alignment.center if center else ft.alignment.center_left,
        )

    def _action_icon(icon, color, tooltip, handler):
        return ft.IconButton(
            icon=icon, icon_size=15, icon_color=color, tooltip=tooltip,
            width=26, height=26, padding=0, on_click=handler,
        )

    def _build_row(ctl: Control, num: int, selected_status: str) -> ft.Container:
        status = deadline_status(ctl, soon_days)
        color = STATUS_COLORS.get(status, "#94a3b8")
        content = ctl.content or ctl.incoming_number
        content_tooltip = ctl.content or ""
        if ctl.tasks:
            task_txt = "; ".join(t.title for t in ctl.tasks if t.title)
            if task_txt:
                content_tooltip = (content_tooltip + "\n" + task_txt).strip()

        row = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(width=_COL["bar"], height=30, bgcolor=color, border_radius=2),
                    _cell(str(num), _COL["num"], center=True, color=COLORS["text_secondary"]),
                    _cell(ctl.incoming_number or "—", _COL["incoming"], bold=True,
                          tooltip=ctl.incoming_number),
                    _cell(_display_date(ctl.receive_date), _COL["receive"],
                          color=COLORS["text_secondary"]),
                    _cell(ctl.initiator or "—", _COL["initiator"], tooltip=ctl.initiator),
                    _cell(content, _COL["content"], tooltip=content_tooltip, max_lines=2),
                    _cell(", ".join(ctl.executors) or "—", _COL["executors"],
                          tooltip=", ".join(ctl.executors)),
                    _cell(ctl.controller or "—", _COL["controller"], tooltip=ctl.controller),
                    _cell(_type_label(ctl), _COL["type"], color=COLORS["text_secondary"]),
                    _cell(_display_date(effective_due_date(ctl)), _COL["due"], bold=True),
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(STATUS_ICONS.get(status, "REMOVE"), size=11,
                                        color=color),
                                ft.Text(STATUS_LABELS.get(status, status), size=10,
                                        color=color, weight=ft.FontWeight.W_600, no_wrap=True),
                            ],
                            spacing=3, tight=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        width=_COL["status"], height=22,
                        border_radius=11,
                        padding=ft.padding.symmetric(horizontal=6),
                        alignment=ft.alignment.center,
                        bgcolor=f"{color}22",
                    ),
                    ft.Row(
                        controls=[
                            _action_icon(ft.icons.CHECK_CIRCLE_OUTLINE, COLORS["received"],
                                         "Отметить исполненным",
                                         lambda e, c=ctl: _complete(c)),
                            _action_icon(ft.icons.UPDATE_OUTLINED, COLORS["in_progress"],
                                         "Продлить срок",
                                         lambda e, c=ctl: _extend(c)),
                            _action_icon(ft.icons.DELETE_OUTLINE, "#f87171", "Удалить",
                                         lambda e, c=ctl: _confirm_delete(c)),
                        ],
                        spacing=0, tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=2,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=_ROW_HEIGHT,
            bgcolor=COLORS["card"],
            border=ft.border.all(1, COLORS["border"]),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=4, vertical=4),
            on_click=lambda e, c=ctl: _open_card(c),
        )
        return row

    def _rebuild_table():
        rows_column.controls.clear()
        visible = _filtered()
        if not visible:
            rows_column.controls.append(ft.Container(
                content=ft.Row(controls=[
                    ft.Icon(ft.icons.INBOX, size=18, color=COLORS["text_muted"]),
                    ft.Text("Контролей не найдено", size=12, color=COLORS["text_secondary"]),
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
            rows_column.controls.append(_build_row(ctl, i, None))
        try:
            rows_column.update()
        except Exception:
            pass

    # ── Действия ────────────────────────────────────────────────
    def _open_card(ctl: Optional[Control]):
        def on_save(c: Control):
            if ctl is None:
                state["controls"].append(c)
            else:
                for idx, x in enumerate(state["controls"]):
                    if x.id == c.id:
                        state["controls"][idx] = c
                        break
            _persist(state["controls"])
            _rebuild_table()
            _refresh_counters()

        def on_delete(c: Control):
            state["controls"] = [x for x in state["controls"] if x.id != c.id]
            _persist(state["controls"])
            _rebuild_table()
            _refresh_counters()

        dialog = create_control_card_modal(
            page, ctl, available_names, on_save,
            on_delete=on_delete if ctl is not None else None,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _complete(ctl: Control):
        today = date.today()
        if ctl.control_type == PERIODIC:
            ctl.done_date = today.isoformat()
            base = parse_date(ctl.due_date) or today
            ctl.due_date = (base + timedelta(days=ctl.period_days)).isoformat()
            for t in ctl.tasks:
                t.is_done = False
                t.done_date = None
            ctl.updated_at = datetime.now().isoformat()
            _persist(state["controls"])
            from ui.toast import show_toast
            show_toast(page, f"Срок продлён до {_display_date(ctl.due_date)}",
                       icon=ft.icons.UPDATE)
        else:
            ctl.done = True
            ctl.done_date = today.isoformat()
            ctl.updated_at = datetime.now().isoformat()
            _persist(state["controls"])
            from ui.toast import show_toast
            show_toast(page, "Контроль исполнен", icon=ft.icons.CHECK_CIRCLE)
        _rebuild_table()
        _refresh_counters()

    def _extend(ctl: Control):
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
                n = max(1, int(days_field.value))
            except ValueError:
                n = 7
            base = parse_date(ctl.due_date) or date.today()
            ctl.due_date = (base + timedelta(days=n)).isoformat()
            ctl.updated_at = datetime.now().isoformat()
            _persist(state["controls"])
            from ui.toast import show_toast
            show_toast(page, f"Срок продлён до {_display_date(ctl.due_date)}",
                       icon=ft.icons.UPDATE)
            dialog.open = False
            page.update()
            _rebuild_table()
            _refresh_counters()

        def _close(e=None):
            dialog.open = False
            page.update()

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
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _confirm_delete(ctl: Control):
        def _confirm(e=None):
            state["controls"] = [x for x in state["controls"] if x.id != ctl.id]
            _persist(state["controls"])
            dialog.open = False
            page.update()
            from ui.toast import show_toast
            show_toast(page, f"Удалён: {ctl.incoming_number}", icon=ft.icons.DELETE)
            _rebuild_table()
            _refresh_counters()

        def _close(e=None):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True, bgcolor=COLORS["primary_light"],
            title=ft.Text("Удаление контроля", size=16, weight=ft.FontWeight.BOLD,
                          color=COLORS["text"]),
            content=ft.Text(
                f"Удалить контроль «{ctl.incoming_number}»?",
                size=13, color=COLORS["text"],
            ),
            actions=[
                ft.TextButton("Отмена", on_click=_close),
                ft.ElevatedButton("Удалить", bgcolor="#dc2626", color=COLORS["text_light"],
                                  on_click=_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    # ── Счётчики ────────────────────────────────────────────────
    counter_refs: Dict[str, ft.Container] = {}

    def _counts() -> dict:
        res = {"all": 0, OVERDUE: 0, TODAY: 0, SOON: 0, IN_PROGRESS: 0, DONE: 0}
        for ctl in state["controls"]:
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
                badge.bgcolor = "#ffffff22" if selected else COLORS["card"]
                badge.content.color = fg
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
            content=ft.Text(str(counts.get(key, 0)), size=10, color=fg,
                            weight=ft.FontWeight.W_600, no_wrap=True),
            height=18, padding=ft.padding.symmetric(horizontal=6), border_radius=9,
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

    counters_row = ft.Container(
        content=ft.Row(controls=[
            _mk_counter("all", "Все", ft.icons.GRID_VIEW),
            _mk_counter(OVERDUE, "Просрочено", ft.icons.EVENT_BUSY),
            _mk_counter(TODAY, "Сегодня", ft.icons.NOTIFICATIONS_ACTIVE),
            _mk_counter(SOON, "Скоро", ft.icons.HOURGLASS_BOTTOM),
            _mk_counter(IN_PROGRESS, "В работе", ft.icons.HOURGLASS_TOP),
            _mk_counter(DONE, "Исполнено", ft.icons.CHECK_CIRCLE),
        ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.START),
        height=38, bgcolor=COLORS["primary_light"],
        border=ft.border.all(1, COLORS["border"]), border_radius=10,
        padding=ft.padding.symmetric(horizontal=3, vertical=3),
    )

    # ── Фильтры ─────────────────────────────────────────────────
    search_field = ft.TextField(
        label="Поиск", prefix_icon=ft.icons.SEARCH,
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        width=210, height=38,
    )

    def _on_search(e=None):
        state["search"] = search_field.value or ""
        _apply_filters()
    search_field.on_change = _on_search

    status_filter_dd = ft.Dropdown(
        label="Статус", width=120, height=38,
        value="all",
        options=[
            ft.dropdown.Option("all", "Все"),
            ft.dropdown.Option(OVERDUE, "Просрочено"),
            ft.dropdown.Option(TODAY, "Сегодня"),
            ft.dropdown.Option(SOON, "Скоро"),
            ft.dropdown.Option(IN_PROGRESS, "В работе"),
            ft.dropdown.Option(DONE, "Исполнено"),
        ],
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
    )
    type_filter_dd = ft.Dropdown(
        label="Тип", width=110, height=38, value="all",
        options=[ft.dropdown.Option("all", "Все"), ft.dropdown.Option(ONE_TIME, "Разовый"),
                 ft.dropdown.Option(PERIODIC, "Постоянный")],
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
    )

    def _on_filter_change(e=None):
        state["f_status"] = status_filter_dd.value or "all"
        state["f_type"] = type_filter_dd.value or "all"
        _restyle_counters()
        _apply_filters()

    status_filter_dd.on_change = _on_filter_change
    type_filter_dd.on_change = _on_filter_change

    initiator_filter_dd = ft.Dropdown(
        label="Инициатор", width=150, height=38, value="all",
        options=[ft.dropdown.Option("all", "Все")] + [ft.dropdown.Option(i) for i in initiators],
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
    )
    executor_filter_dd = ft.Dropdown(
        label="Исполнитель", width=160, height=38, value="all",
        options=[ft.dropdown.Option("all", "Все")] +
                [ft.dropdown.Option(n) for n in available_names],
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
    )
    controller_filter_dd = ft.Dropdown(
        label="За кем", width=140, height=38, value="all",
        options=[ft.dropdown.Option("all", "Все")] +
                [ft.dropdown.Option(n) for n in available_names],
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
    )

    def _on_named_filter_change(e=None):
        state["f_initiator"] = initiator_filter_dd.value or "all"
        state["f_executor"] = executor_filter_dd.value or "all"
        state["f_controller"] = controller_filter_dd.value or "all"
        _apply_filters()

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

    filter_row = ft.Container(
        content=ft.Row(controls=[
            search_field,
            status_filter_dd,
            type_filter_dd,
            initiator_filter_dd,
            executor_filter_dd,
            controller_filter_dd,
            from_field,
            to_field,
            ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_size=16,
                          icon_color=COLORS["btn_save"], tooltip="С даты",
                          on_click=lambda e: _pick_filter_date(_set_from)),
            ft.IconButton(icon=ft.icons.CALENDAR_MONTH, icon_size=16,
                          icon_color=COLORS["btn_save"], tooltip="По дату",
                          on_click=lambda e: _pick_filter_date(_set_to)),
            ft.TextButton("Сброс", on_click=_reset_filters,
                          style=ft.ButtonStyle(color=COLORS["btn_save"])),
        ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.START, scroll=ft.ScrollMode.HIDDEN),
        height=46, bgcolor=COLORS["card"],
        border=ft.border.all(1, COLORS["border"]), border_radius=12,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
    )

    # ── Шапка таблицы (кликабельная сортировка) ─────────────────
    def _header_cell(text: str, width: int, key: str, center=False) -> ft.Container:
        arrow = "▲" if (state["sort_key"] == key and not state["sort_reverse"]) else \
                ("▼" if (state["sort_key"] == key and state["sort_reverse"]) else "")
        return ft.Container(
            content=ft.Text(f"{text} {arrow}".strip(), size=11,
                            weight=ft.FontWeight.BOLD, color=COLORS["text_secondary"],
                            no_wrap=True),
            width=width,
            padding=ft.padding.only(left=6, right=4),
            alignment=ft.alignment.center if center else ft.alignment.center_left,
            on_click=lambda e, k=key: _sort_by(k),
            tooltip="Сортировка",
        )

    def _sort_by(key: str):
        if state["sort_key"] == key:
            state["sort_reverse"] = not state["sort_reverse"]
        else:
            state["sort_key"] = key
            state["sort_reverse"] = False
        _rebuild_table()
        _rebuild_header()

    header_row_ref = {"control": None}

    def _rebuild_header():
        hdr = ft.Row(controls=[
            ft.Container(width=_COL["bar"]),
            _header_cell("№", _COL["num"], "num", center=True),
            _header_cell("вх. № ВХСОП", _COL["incoming"], "incoming"),
            _header_cell("Дата пост.", _COL["receive"], "receive"),
            _header_cell("Инициатор", _COL["initiator"], "initiator"),
            ft.Container(width=_COL["content"], padding=ft.padding.only(left=6, right=4),
                         content=ft.Text("Содержание", size=11, weight=ft.FontWeight.BOLD,
                                         color=COLORS["text_secondary"], no_wrap=True)),
            ft.Container(width=_COL["executors"], padding=ft.padding.only(left=6, right=4),
                         content=ft.Text("Исполнители", size=11, weight=ft.FontWeight.BOLD,
                                         color=COLORS["text_secondary"], no_wrap=True)),
            ft.Container(width=_COL["controller"], padding=ft.padding.only(left=6, right=4),
                         content=ft.Text("За кем", size=11, weight=ft.FontWeight.BOLD,
                                         color=COLORS["text_secondary"], no_wrap=True)),
            ft.Container(width=_COL["type"], padding=ft.padding.only(left=6, right=4),
                         content=ft.Text("Тип", size=11, weight=ft.FontWeight.BOLD,
                                         color=COLORS["text_secondary"], no_wrap=True)),
            _header_cell("Дата исполн.", _COL["due"], "due"),
            ft.Container(width=_COL["status"], padding=ft.padding.only(left=6, right=4),
                         content=ft.Text("Статус", size=11, weight=ft.FontWeight.BOLD,
                                         color=COLORS["text_secondary"], no_wrap=True)),
            ft.Container(width=_COL["actions"]),
        ], spacing=2, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        header_row_ref["control"].controls = [hdr]
        try:
            header_row_ref["control"].update()
        except Exception:
            pass

    header_row = ft.Container(
        content=ft.Row(controls=[], spacing=0, tight=True),
        height=30, bgcolor=COLORS["primary_light"],
        border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=4, vertical=2),
    )
    header_row_ref["control"] = header_row

    # ── Тулбар ──────────────────────────────────────────────────
    def _open_settings(e=None):
        from .controls_settings_modal import create_controls_settings_modal

        def on_apply(new_settings):
            nonlocal settings, soon_days
            settings = new_settings
            soon_days = int(new_settings.get("soon_days", 3) or 3)
            _update_sync_ui()
            # Перезагрузить данные при смене сетевого режима
            _load_initial()
            _rebuild_table()
            _refresh_counters()

        dialog = create_controls_settings_modal(page, settings, on_apply)
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _add_control(e=None):
        _open_card(None)

    def _export(e=None):
        from ui.toast import show_export_toast, show_error_toast

        def _on_file_picked(res):
            if not res.path:
                return
            try:
                ControlsExcelExporter().export(state["controls"], res.path, soon_days)
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

    add_btn = ft.ElevatedButton(
        text="Добавить контроль", icon=ft.icons.ADD_CIRCLE_OUTLINE,
        bgcolor=COLORS["btn_save"], color=COLORS["text_light"], height=38,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                             padding=ft.padding.symmetric(horizontal=14)),
        on_click=_add_control,
    )
    export_btn = ft.ElevatedButton(
        text="Экспорт Excel", icon=ft.icons.FILE_DOWNLOAD_OUTLINED,
        bgcolor=COLORS["btn_export"], color=COLORS["text_light"], height=38,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                             padding=ft.padding.symmetric(horizontal=14)),
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
            export_btn,
            settings_btn,
        ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.START),
        height=46,
    )

    tab_content = ft.Column(
        controls=[
            title_row,
            ft.Container(height=6),
            counters_row,
            ft.Container(height=6),
            filter_row,
            ft.Container(height=6),
            header_row,
            ft.Container(height=2),
            rows_column,
            ft.Container(height=30),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
    )

    # Инициализация
    _load_initial()
    _rebuild_table()
    _refresh_counters()

    # Запуск фонового polling (сетевой синк + уведомления)
    if settings.get("network_enabled"):
        try:
            t = threading.Thread(target=_background_loop, daemon=True)
            t.start()
        except Exception as e:
            print(f"[CONTROLS_TAB] thread start error: {e}")

    # Первичное уведомление о сроках (не дублируется бесконечно — по is_edit)
    _notify_schedule()
    state["last_overdue"] = sum(1 for c in state["controls"]
                                if deadline_status(c, soon_days) == OVERDUE)

    # Регистрируем cleanup при закрытии окна
    page._controls_poll_stop = _poll_stop

    print("[CONTROLS_TAB] Controls tab created")
    return tab_content

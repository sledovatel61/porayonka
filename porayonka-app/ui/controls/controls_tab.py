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
    name_matches,
    STATUS_LABELS,
    OVERDUE, TODAY, SOON, IN_PROGRESS, DONE, COMPLETED, NO_DATE,
    ARCHIVE_DONE, ARCHIVE_DELETED,
)
from core.controls_data import (
    load_controls, save_controls, load_settings, save_settings,
    get_criminalist_names, get_controller_names,
    get_initiators, canonical_initiator_group, initiator_filter_options,
    initiator_filter_group,
    archive_control, restore_control,
    delete_all_attachments,
    read_shared_controls, write_shared_controls, get_shared_mtime,
    sync_attachments_from_shared,
    copy_attachment_to_local, copy_attachment_to_shared,
    resolve_attachment, delete_attachment, ATTACHMENT_WARN_MB,
    add_custom_initiator,
    merge_controls, _should_notify,
)

FILTER_OTHER = "__other__"  # пункт «Прочие» в фильтрах исполнителей/контролёров
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


def _quiet_update(control):
    """Раунд 14 (задача 1): update для ГОРЯЧИХ hover-обработчиков — без печати
    ошибок (print/traceback в горячем пути запрещены: AGENTS мангуст.md §hover)."""
    try:
        if control is not None and getattr(control, "page", None) is not None:
            control.update()
    except Exception:
        pass


def _make_row_scroller(col, row_h=32):
    """Раунд 14 (задача 3): колесо мыши листает 1–2 строки за щелчок.

    Нативный delta колеса (~100 px) компенсируется до фиксированного шага
    (2 строки) через scroll_to(offset=...) — «перехват on_scroll и ручная
    прокрутка на небольшое значение». Короткая блокировка игнорирует on_scroll,
    порождённые собственным программным скроллом. Без print/traceback.
    """
    st = {"lock": 0.0}
    step = float(row_h) * 2

    def _on_scroll(e):
        now = time.time()
        if now < st["lock"]:
            return
        try:
            d = float(getattr(e, "delta", 0.0) or 0.0)
            px = float(getattr(e, "pixels", 0.0) or 0.0)
        except Exception:
            return
        if not d:
            return
        s = step if d > 0 else -step
        corr = d - s
        if abs(corr) < 1.0:
            return
        off = max(0.0, px - corr)
        col._row_scroll_last = off  # фиксируем для headless-тестов
        st["lock"] = now + 0.15
        try:
            col.scroll_to(offset=off, duration=0)
        except Exception:
            pass

    return _on_scroll


def _play_notify_sound():
    """Системный звук уведомления (winsound, stdlib). Не Windows / нет схемы — молча."""
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception:
        pass


# Раунд 14 (задача 2): ширины чуть шире раунда 13, но сумма + отступы всё ещё
# <= 1240 при окне 1280 (точную раскладку см. в _ROW_EXTRA).
_FIXED = {
    "bar": 4,
    "num": 32,
    "incoming": 160,
    "receive": 88,
    "initiator": 116,
    "controller": 112,
    "type": 82,
    "due": 100,
    "status": 116,
    "actions": 90,  # 2 иконки 30+30+spacing 4 = 64; заголовок «ДЕЙСТВИЯ» ~68
}
_ROW_HEIGHT = 56
# Раунд 15 (задача 2): РЕАЛЬНЫЕ внешние отступы контента вкладки: обёртка в main.py
# (tab3_content) даёт padding 20+20, tab_bg внутри вкладки — 12+12, итого 64.
# Раньше считали 40 — отсюда пустое место справа (на широком окне) и клип «Действий»
# (на ровно 1280).
_TAB_OUTER_PADDING = 64
_ROW_SPACING = 6
# Раунд 15 (задача 2): «не-колоночные» пиксели панели/строки таблицы:
#   рамка панели 2 + рамка строки 2 + padding строки 2*6=12 + spacing 21*1=21 +
#   10 разделителей*1=10 + запас 1 => 48. Скроллбар ширины НЕ занимает — во Flutter
#   Scrollbar это overlay поверх контента (см. scrollable_control.dart Flet 0.23.2).
_ROW_EXTRA = 48
# Раунд 15 (задача 2): верхние кэпы гибких колонок (480/220) УБРАНЫ — они и давали
# пустое место справа: теперь «Содержание»/«Исполнители» растягиваются на широком
# окне (промпт раунда 15, §2.2).

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
    # Раунд 7-8 (задачи 1/1): фильтры «Исполнители»/«Контролёры» используют ПОЛНЫЙ
    # канонический справочник людей — криминалисты + дефолтные контролёры +
    # доп. ФИО из настроек (`extra_people`, редактируется в модалке настроек).
    executor_canonical = get_controller_names(settings)
    controller_canonical = get_controller_names(settings)
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
        "pending_shared": None,          # {controls, mtime} — сетевые изменения при открытой карточке
        "pending_dialog_shown": False,   # диалог «Данные изменились» показан (1 раз на открытие карточки)
        "known_ids": set(),              # снимок id для персональных уведомлений (задача 2)
        "my_status_map": {},             # id -> deadline_status для моих контролей (задача 2)
        "known_attachments": {},         # id -> tuple(attachments) для синка вложений (задача 5)
        "card_w": int(settings.get("card_width", 0) or 920),
        "card_h": int(settings.get("card_height", 0) or 780),
    }

    rows_column = ft.Column(spacing=6, tight=True)  # Bug 2: gap 6px между плашками
    # Раунд 15 (задача 1): Python-hover (on_hover + _hover_active) УДАЛЁН ПОЛНОСТЬЮ.
    # Причина лагов/«хвостов» (подтверждено исходниками Flet 0.23.2, container.dart):
    # on_hover на Container — это MouseRegion, который на КАЖДЫЙ enter/exit шлёт
    # событие в Python (triggerControlEvent по локальному каналу) и ждёт update()
    # обратно. При быстром движении курсора по ~130 строкам — десятки round-trip
    # в секунду, очередь событий не успевает. Вместо этого — нативный hover:
    # ink=True даёт Material + InkWell, который рисует hoverColor сам, без Python.
    sync_label = ft.Text("Локально", size=11, color=GLASS["text_secondary"])
    sync_dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=GLASS["text_muted"])

    def _table_width_for(width: Optional[float]) -> int:
        """Раунд 15 (задача 2): полная ширина ПАНЕЛИ таблицы для данной ширины окна —
        ровно до правого края контента вкладки (без пустого места справа)."""
        if not width or width <= 0:
            width = 1280
        return max(400, int(width) - _TAB_OUTER_PADDING)

    def _table_width() -> int:
        try:
            w = page.width or 1280
        except Exception:
            w = 1280
        return _table_width_for(w)

    def _width_budget() -> float:
        """Раунд 13/15 (задача 2): бюджет СУММЫ ширин колонок для текущего окна
        (панель минус рамки/padding/spacing/разделители). При 1280 — без
        горизонтального скролла, «Действия» не уезжают за экран."""
        return max(300.0, _table_width() - _ROW_EXTRA)

    def _layout_widths(width: Optional[float]) -> Dict[str, int]:
        """Раунд 15 (задача 2): дефолтные ширины, ТОЧНО заполняющие ширину окна.
        Фиксированные колонки компактные (_FIXED); весь остаток бюджета уходит в
        гибкие «Содержание»/«Исполнители» (~65/35) — никаких кэпов 480/220,
        иначе на широком окне справа пустота."""
        w = dict(_FIXED)
        budget = max(300.0, _table_width_for(width) - _ROW_EXTRA)
        flex = budget - sum(_FIXED.values())
        if flex < 150:
            # очень узкое окно — минимумы; дальше подожмёт _clamp_widths()
            w["content"] = 60
            w["executors"] = 60
            return w
        ex = max(90, int(flex * 0.35))
        w["executors"] = ex
        w["content"] = max(60, int(flex - ex))
        return w

    def _clamp_widths():
        """Раунд 13/15 (задача 2): не дать сумме колонок (в т.ч. сохранённым из
        настроек после ручного resize) превысить бюджет окна. Сначала жмём
        гибкие колонки (до 60), затем фиксированные (до 40). Верхних кэпов нет."""
        _W["content"] = max(60, int(_W["content"]))
        _W["executors"] = max(60, int(_W["executors"]))
        budget = _width_budget()
        need = int(sum(_W.values()) - budget)
        if need <= 0:
            return
        for k in ("content", "executors"):
            cut = min(need, _W[k] - 60)
            if cut > 0:
                _W[k] -= cut
                need -= cut
            if need <= 0:
                return
        for k in [k for k in _W if k not in ("content", "executors", "bar")]:
            if need <= 0:
                break
            cut = min(need, _W[k] - 40)
            if cut > 0:
                _W[k] -= cut
                need -= cut

    def _fit_widths():
        """Раунд 15 (задача 2): привести _W ровно к бюджету окна. Переполнение —
        кламп (сохранённые «раздутые» ширины, узкое окно); остаток — ЗАПОЛНЕНИЕ
        гибких колонок: таблица всегда занимает всю доступную ширину, «Действия»
        прижаты к правому краю, пустого места справа нет."""
        budget = int(_width_budget())
        total = int(sum(int(v) for v in _W.values()))
        if total > budget:
            _clamp_widths()
            return
        extra = budget - total
        if extra > 0:
            c_add = int(extra * 0.65)
            _W["content"] = int(_W["content"]) + c_add
            _W["executors"] = int(_W["executors"]) + (extra - c_add)

    _W = _layout_widths(page.width)
    # Bug 2.6: подхватить сохраненные ширины колонок из settings
    try:
        saved_widths = settings.get("col_widths") or {}
        for k, v in saved_widths.items():
            if k in _W:
                _W[k] = max(40, int(v))
    except Exception:
        traceback.print_exc()
    # Раунд 15 (задача 2): кламп сохранённых «раздутых» ширин (не шире бюджета
    # окна) + заполнение при недоборе — применяется ВСЕГДА (и при старте, и при
    # resize окна).
    _fit_widths()

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
            # Задача 1: если кто-то писал в shared, пока мы работали — merge перед записью
            try:
                cur_mtime = get_shared_mtime(settings)
            except Exception:
                cur_mtime = None
            if cur_mtime is not None and cur_mtime != state["shared_mtime"]:
                shared = read_shared_controls(settings)
                if shared:
                    merged = merge_controls(controls, shared)
                    print(f"[CONTROLS_TAB] merge: {len(shared)} controls from shared")
                    controls = merged
                    state["controls"] = merged
                    state["pending_shared"] = None  # сетевые изменения уже применены
                    _sync_attachments(merged)
            ok = write_shared_controls(controls, settings)
            state["network_ok"] = bool(ok)
            try:
                state["shared_mtime"] = get_shared_mtime(settings)
            except Exception:
                traceback.print_exc()
        _update_sync_ui()
        _refresh_filter_options()

    def _sync_attachments(controls: List[Control]):
        """Задача 5: подтянуть вложения из shared только для новых/изменившихся списков."""
        try:
            ids = {c.id for c in controls}
            for cid in [k for k in state["known_attachments"] if k not in ids]:
                del state["known_attachments"][cid]
            for c in controls:
                atts = tuple(c.attachments or [])
                if not atts:
                    continue
                if state["known_attachments"].get(c.id) == atts:
                    continue
                try:
                    sync_attachments_from_shared(c.id, c.attachments, settings)
                except Exception:
                    print("[CONTROLS_TAB] attachment sync error")
                state["known_attachments"][c.id] = atts
        except Exception:
            traceback.print_exc()

    def _load_initial():
        state["known_attachments"] = {}
        if settings.get("network_enabled"):
            shared = read_shared_controls(settings)
            if shared:
                state["controls"] = shared
                state["network_ok"] = True
            else:
                # shared пуст/не существует — грузим локальные и засеваем shared
                state["controls"] = load_controls()
                try:
                    ok = write_shared_controls(state["controls"], settings)
                    state["network_ok"] = bool(ok)
                    if ok:
                        print(f"[CONTROLS_TAB] seeded shared with {len(state['controls'])} controls")
                except Exception:
                    state["network_ok"] = False
            try:
                state["shared_mtime"] = get_shared_mtime(settings)
            except Exception:
                traceback.print_exc()
            _sync_attachments(state["controls"])
        else:
            state["controls"] = load_controls()
        # снимки для персональных уведомлений (задача 2): текущие контроли считаем «известными»
        state["known_ids"] = {c.id for c in state["controls"]}
        state["my_status_map"] = {c.id: deadline_status(c, soon_days) for c in state["controls"]}
        _update_sync_ui()
        _refresh_filter_options()

    def _update_sync_ui():
        # Задача 4: три состояния — «Локально» / «Сеть: роль» / «Сеть: нет связи»
        net = settings.get("network_enabled")
        if not net:
            sync_label.value = "Локально"
            sync_dot.bgcolor = GLASS["text_muted"]
        elif state["network_ok"]:
            role = "админ" if network_role == "admin" else "пользователь"
            sync_label.value = f"Сеть: {role}"
            sync_dot.bgcolor = GLASS["in_progress"]
            if state["last_sync"]:
                sync_label.value += f" · {state['last_sync'].strftime('%H:%M:%S')}"
        else:
            sync_label.value = "Сеть: нет связи"
            sync_dot.bgcolor = GLASS["overdue"]
        try:
            _safe_update(sync_label)
            _safe_update(sync_dot)
        except Exception:
            traceback.print_exc()

    def _mine(c: Control) -> bool:
        """Контроль пользователя: он исполнитель или ответственный по пункту.
        Фамильное сопоставление через общий хелпер name_matches()."""
        if any(name_matches(network_user, ex) for ex in c.executors):
            return True
        for t in c.tasks:
            if any(name_matches(network_user, a) for a in t.assignees):
                return True
        parts = network_user.strip().split()
        if not parts:
            return False
        surname = parts[0].lower()
        if len(surname) < 3:
            return False
        for e in c.executors:
            if surname in (e or "").lower():
                return True
        for t in c.tasks:
            for a in t.assignees:
                if surname in (a or "").lower():
                    return True
        return False

    def _visible_base() -> List[Control]:
        lst = state["controls"]
        if network_role == "user" and network_user:
            lst = [c for c in lst if _mine(c)]
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
            # Раунд 7 (задача 2): канонический фильтр инициаторов — сравниваем группы.
            # Раунд 13: переименованный в справочнике кластер матчится по канону исходного.
            if state["f_initiator"] != "all":
                sel_group = initiator_filter_group(state["f_initiator"], settings)
                if not sel_group or canonical_initiator_group(ctl.initiator) != sel_group:
                    return False
            if state["f_controller"] != "all":
                if state["f_controller"] == FILTER_OTHER:
                    # «Прочие»: контролёр не матчится ни с одним каноническим
                    if any(name_matches(cn, ctl.controller) for cn in controller_canonical):
                        return False
                elif not name_matches(state["f_controller"], ctl.controller):
                    return False
            if state["f_executor"] != "all":
                names = list(ctl.executors)
                for t in ctl.tasks:
                    names.extend(t.assignees)
                if state["f_executor"] == FILTER_OTHER:
                    # «Прочие»: ни один исполнитель/ответственный не матчится с каноническими
                    if any(name_matches(cn, nm) for cn in executor_canonical for nm in names if nm):
                        return False
                elif not any(name_matches(state["f_executor"], nm) for nm in names):
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
        content=ft.Row(controls=[], spacing=1, tight=True),
        height=34,
        bgcolor="transparent",
        border=ft.border.only(bottom=ft.BorderSide(1, GLASS["border_divider"])),
        # Раунд 9 (БАГ 2): padding заголовка = padding строк, чтобы разделители
        # колонок стояли строго на одних X-координатах. Раунд 14: spacing 1,
        # padding 6 — экономия ~25 px в бюджете строки.
        padding=ft.padding.symmetric(horizontal=6, vertical=2),
    )

    # Раунд 7 (задача 5): ссылки на контейнеры заголовков для resize без пересоздания
    header_cell_refs: Dict[str, ft.Container] = {}

    def _header_cell(text: str, width: int, key: str, center=False):
        arrow = "▲" if (state["sort_key"]==key and not state["sort_reverse"]) else ("▼" if (state["sort_key"]==key and state["sort_reverse"]) else "")
        lbl = f"{text} {arrow}".strip().upper()
        # Раунд 9 (БАГ 2): ячейка заголовка — Stack: текст (ширина W) + drag-хэндл
        # поверх правого края. Разделители добавляются в _rebuild_header ОТДЕЛЬНЫМИ
        # контролами между ячейками — точно как в строках, поэтому X-координаты
        # линий заголовка и строк совпадают 1-в-1.
        text_cont = ft.Container(
            content=ft.Text(lbl, size=11, weight=ft.FontWeight.BOLD, color=GLASS["text_secondary"], no_wrap=True, tooltip="Сортировка"),
            width=width,
            padding=ft.padding.only(left=6, right=4),
            alignment=ft.alignment.center if center else ft.alignment.center_left,
            on_click=lambda e, k=key: _sort_by(k),
        )
        def _make_drag(k):
            def _on_drag_start(e):
                pass

            def _on_drag_update(e):
                try:
                    delta = 0
                    try:
                        delta = int(getattr(e, 'delta_x', 0) or getattr(e, 'primary_delta', 0) or getattr(e, 'dx', 0) or 0)
                    except Exception:
                        delta = 0
                    if delta == 0:
                        return
                    old = _W.get(k, width)
                    new = max(60, old + delta)
                    prev = dict(_W)
                    # Rubber content logic: увеличение фиксированных колонок
                    # компенсируется сжатием «Содержания» (min 60)
                    if k not in ("content", "executors", "actions"):
                        delta_actual = new - old
                        content_old = _W.get("content", 100)
                        content_new = max(60, content_old - delta_actual)
                        if content_new < 60:
                            delta_actual = content_old - 60
                            new = old + delta_actual
                            content_new = 60
                        _W[k] = new
                        _W["content"] = content_new
                    else:
                        _W[k] = new
                    # Раунд 13 (задача 2): drag не должен распирать таблицу
                    # шире окна — при переполнении жмём гибкую колонку или откат.
                    over = int(sum(_W.values()) - _width_budget())
                    if over > 0:
                        if k in ("content", "executors"):
                            _W[k] = max(60, _W[k] - over)
                        elif _W.get("content", 60) - over >= 60:
                            _W["content"] -= over
                        else:
                            _W.clear()
                            _W.update(prev)
                    # применяем ширину к живым контролам заголовка (без rebuild)
                    refs = header_cell_refs.get(k)
                    if refs is not None:
                        cell, tcont = refs
                        cell.width = _W[k]
                        tcont.width = _W[k]
                        _safe_update(cell)
                except Exception:
                    traceback.print_exc()

            def _on_drag_end(e):
                try:
                    _rebuild_header()
                    _rebuild_table()
                    _save_col_widths()
                except Exception:
                    traceback.print_exc()
            return _on_drag_start, _on_drag_update, _on_drag_end

        _ds, _du, _de = _make_drag(key)
        drag_handle = ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.RESIZE_LEFT_RIGHT,
            on_horizontal_drag_start=_ds,
            on_horizontal_drag_update=_du,
            on_horizontal_drag_end=_de,
            content=ft.Container(
                width=10,
                height=34,
                bgcolor="transparent",
                border_radius=2,
            ),
        )
        # Раунд 13 (задача 1): hover на хэндле убран полностью — только
        # курсор resize, без update() и задержек.

        # Stack: текст на всю ширину, хэндл прижат к правому краю (поверх границы)
        cell = ft.Stack(
            controls=[text_cont, drag_handle],
            width=width,
        )
        cell.alignment = ft.alignment.center_right
        header_cell_refs[key] = (cell, text_cont)
        return cell

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
        # Раунд 9 (БАГ 2): та же последовательность контролов, что и в строках —
        # [bar][ячейка][разделитель][ячейка][разделитель]... с одинаковым spacing,
        # поэтому вертикальные линии заголовка и строк стоят на одних X.
        _hsep = ft.Container(width=1, height=30, bgcolor="#26ffffff")
        controls = [
            ft.Container(width=_W["bar"]),
            _header_cell("№", _W["num"], "num", center=True),
            _hsep,
            _header_cell("вх. №", _W["incoming"], "incoming"),
            _hsep,
            _header_cell("Дата пост.", _W["receive"], "receive"),
            _hsep,
            _header_cell("Инициатор", _W["initiator"], "initiator"),
            _hsep,
            _header_cell("Содержание", _W["content"], "content"),
            _hsep,
            _header_cell("Исполнители", _W["executors"], "executors"),
            _hsep,
            _header_cell("За кем", _W["controller"], "controller"),
            _hsep,
            _header_cell("Причина" if is_archive else "Тип", _W["type"], "type"),
            _hsep,
            _header_cell("Срок исполн.", _W["due"], "due"),
            _hsep,
            _header_cell("Статус", _W["status"], "status"),
            _hsep,
            _header_cell("Действия", _W["actions"], "actions", center=True),
        ]
        header_row.content = ft.Row(controls=controls, spacing=1, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)
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

        # Раунд 14 (задача 2): кегль возвращён к 12–13 (в раунде 13 было 11 — мелко)
        content_controls = [_cell(content_text, _W["content"] - (22 if ctl.attachments else 0) - 2, tooltip=content_tooltip, max_lines=2, color=GLASS["text"], size=13)]
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

        # Раунд 8 (задача 3): видимые вертикальные разделители между колонками строк
        _vsep = ft.Container(width=1, height=24, bgcolor="#12ffffff")
        row_controls = [
            ft.Container(width=_W["bar"], height=28, bgcolor=color, border_radius=2),
            _cell(str(num), _W["num"], center=True, color=GLASS["text_secondary"], size=12),
            _vsep,
            _cell(ctl.incoming_number or "—", _W["incoming"], bold=True, tooltip=ctl.incoming_number, color=GLASS["text"], size=13),
            _vsep,
            _cell(_display_date(ctl.receive_date), _W["receive"], color=GLASS["text_secondary"], size=12),
            _vsep,
            _cell(short_name(ctl.initiator) if ctl.initiator else "—", _W["initiator"], tooltip=ctl.initiator, color=GLASS["text"], size=12),
            _vsep,
            ft.Row(controls=content_controls, spacing=2, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            _vsep,
            _cell(", ".join(short_name(x) for x in ctl.executors) or "—", _W["executors"], tooltip=", ".join(ctl.executors), color=GLASS["text"], size=12, max_lines=2),
            _vsep,
            _cell(short_name(ctl.controller) if ctl.controller else "—", _W["controller"], tooltip=ctl.controller, color=GLASS["text"], size=12),
            _vsep,
            type_cell,
            _vsep,
            due_cell,
            _vsep,
            ft.Container(
                content=ft.Row(controls=[
                    ft.Icon(STATUS_ICONS.get(status, ft.icons.REMOVE_CIRCLE_OUTLINE), size=12, color=color),
                    ft.Text(STATUS_LABELS.get(status, status), size=11, color=color, weight=ft.FontWeight.W_600, no_wrap=True),
                ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                width=_W["status"], height=26, border_radius=13, padding=ft.padding.symmetric(horizontal=8),
                alignment=ft.alignment.center, bgcolor=with_alpha(color, "22"), border=ft.border.all(1, color),
            ),
            _vsep,
            # Раунд 10 (задача 2): иконки действий прижаты к ПРАВОМУ краю ячейки
            # (аналог левой статусной полосы, упирающейся в левый край)
            ft.Row(controls=actions, spacing=4, tight=True, width=_W["actions"],
                   vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.END),
        ]

        # Плашка строки: Bug 2 exact colors — #2a3247, border #0dffffff or none, radius 10, gap 6
        # Bug 2.4: height по контенту min 56, padding vertical 8, max_lines 2
        row = ft.Container(
            content=ft.Row(controls=row_controls, spacing=1, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            # height None — по контенту, min 56 via padding
            # Раунд 15 (задача 2): ЯВНАЯ ширина строки до правого края панели —
            # иначе вся цепочка (панель -> колонка -> строка) shrink-wrap'ится по
            # содержимому и справа от таблицы остаётся пустое место.
            width=_table_width() - 2,
            bgcolor=GLASS["card"],  # #2a3247
            border=ft.border.all(1, GLASS["border"]),  # #0dffffff
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=6, vertical=8),
            on_click=lambda e, c=ctl: _open_detail(c),
            # Раунд 15 (задача 1): hover — НАТИВНЫЙ (Flutter InkWell), БЕЗ Python-
            # событий. В Flet 0.23.2 Container(on_click, ink=True) рендерится как
            # Material(transparent, borderRadius) + InkWell (container.dart):
            # InkWell сам рисует подсветку наведения (hoverColor из темы) и splash
            # при клике — мгновенно, в UI-потоке, без triggerControlEvent в Python.
            # Цвет подсветки задаётся локальной темой table_container (hover_color),
            # поэтому наследуется всеми строками таблицы. Курсор CLICK InkWell
            # показывает сам (MaterialStateMouseCursor.clickable при onTap != null).
            ink=True,
            ink_color=GLASS["hover_strong"],  # тонкий белый splash при клике
        )
        row.mouse_cursor = ft.MouseCursor.CLICK
        return row

    def _rebuild_table():
        # Раунд 15: состояния подсветки больше нет (hover — нативный InkWell),
        # сбрасывать нечего.
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
        # Фильтры «Исполнители»/«Контролёры» — полный канонический список людей
        # (криминалисты + дефолтные контролёры), без мусора из данных; в конце «Прочие».
        # Инициаторы — каноническая кластеризация вариантов («ГУК СК» → «ГУК» и т.п.).
        try:
            raw_initiators = {c.initiator for c in state["controls"] if c.initiator} | set(initiators)
            # Раунд 13: опции учитывают правки справочника (rename/hide кластеров)
            canon_initiators = initiator_filter_options(raw_initiators, settings)
            executor_filter_dd.options = ([ft.dropdown.Option("all", "Все исполнители")]
                                          + [ft.dropdown.Option(n, short_name(n)) for n in executor_canonical]
                                          + [ft.dropdown.Option(FILTER_OTHER, "Прочие")])
            controller_filter_dd.options = ([ft.dropdown.Option("all", "Все контролеры")]
                                            + [ft.dropdown.Option(n, short_name(n)) for n in controller_canonical]
                                            + [ft.dropdown.Option(FILTER_OTHER, "Прочие")])
            initiator_filter_dd.options = [ft.dropdown.Option("all", "Все инициаторы")] + [ft.dropdown.Option(i) for i in canon_initiators]
            # Ранее выбранное значение сохраняем, только если оно каноническое;
            # мусорная строка из старых данных — молча сброс на «Все».
            if state["f_executor"] not in ("all", FILTER_OTHER) and state["f_executor"] not in executor_canonical:
                state["f_executor"] = "all"
                executor_filter_dd.value = "all"
            if state["f_controller"] not in ("all", FILTER_OTHER) and state["f_controller"] not in controller_canonical:
                state["f_controller"] = "all"
                controller_filter_dd.value = "all"
            if state["f_initiator"] != "all":
                sel = state["f_initiator"]
                if sel not in canon_initiators:
                    # Раунд 13: кластер переименован — выбор следует за новым именем
                    ren = (settings.get("init_renames") or {}).get(sel)
                    sel_group = initiator_filter_group(sel, settings)
                    new_val = " ".join(t.upper() for t in sel_group.split()) if sel_group else ""
                    if ren and ren in canon_initiators:
                        state["f_initiator"] = ren
                        initiator_filter_dd.value = ren
                    elif new_val in canon_initiators:
                        state["f_initiator"] = new_val
                        initiator_filter_dd.value = new_val
                    else:
                        state["f_initiator"] = "all"
                        initiator_filter_dd.value = "all"
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
    initiator_filter_dd = _glass_dropdown("Все инициаторы", 190, [ft.dropdown.Option("all", "Все инициаторы")] + [ft.dropdown.Option(i) for i in initiator_filter_options(initiators, settings)])
    executor_filter_dd = _glass_dropdown("Все исполнители", 190, [ft.dropdown.Option("all", "Все исполнители")] + [ft.dropdown.Option(n, short_name(n)) for n in executor_canonical] + [ft.dropdown.Option(FILTER_OTHER, "Прочие")])
    controller_filter_dd = _glass_dropdown("Все контролеры", 190, [ft.dropdown.Option("all", "Все контролеры")] + [ft.dropdown.Option(n, short_name(n)) for n in controller_canonical] + [ft.dropdown.Option(FILTER_OTHER, "Прочие")])

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
                # Раунд 13 (задача 1): hover на ячейках календаря убран (без update — без лага)
                cell = ft.Container(width=34, height=32, border_radius=8, bgcolor=bg, border=border, alignment=ft.alignment.center, content=txt, ink=True)
                cell.on_click = _make_click(d)
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
    # Раунд 15 (задача 1): ЛОКАЛЬНАЯ тема таблицы с явным hover_color. В Flet 0.23.2
    # любой контрол с атрибутом theme оборачивается клиентом в Theme(...) поверх
    # родительской темы (create_control.dart), а theme.dart парсит ключ hover_color
    # в ThemeData.hoverColor. Поля hover_color нет в Python-датаклассе ft.Theme
    # 0.23.2, но Theme — dataclass без __slots__, поэтому атрибут сериализуется
    # в JSON через __dict__ (EmbedJsonEncoder). Итог: все ink-строки внутри таблицы
    # получают тонкую белую нативную подсветку наведения — без единого события
    # в Python. Глобальная page.theme не трогается (эффект только внутри таблицы).
    _table_theme = ft.Theme(use_material3=True)
    _table_theme.hover_color = GLASS["hover_strong"]  # #12ffffff — стеклянный белый 7%
    table_container.theme = _table_theme

    def _apply_table_geometry():
        """Раунд 15 (задача 2): применить текущий бюджет окна к таблице.
        Раньше ширина зависела только от суммы колонок, а сама панель/строки были
        shrink-wrap -> пустота справа. Теперь сумма колонок подгоняется под окно
        (_fit_widths), а панель и заголовок получают ЯВНУЮ ширину до правого края."""
        _fit_widths()
        tw = _table_width()
        try:
            table_container.width = tw
            header_row.width = tw - 2
            _safe_update(table_container)
            _safe_update(header_row)
        except Exception:
            traceback.print_exc()
        _rebuild_header()
        _rebuild_table()
        try:
            _safe_update(table_container)
            _safe_update(header_row)
        except Exception:
            traceback.print_exc()

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
                # Раунд 13 (задача 1): hover на ячейках календаря убран (без update — без лага)
                cell = ft.Container(width=34, height=32, border_radius=8, bgcolor=bg, border=border, alignment=ft.alignment.center, content=txt, ink=True)
                cell.on_click = _make_click(d)
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
        # Раунд 14 (задача 4): РАВНОМЕРНАЯ рамка border.all (border.only с разной
        # толщиной сторон давал прозрачные углы) + radius 16 + клип по границе.
        border=ft.border.all(1, GLASS["border"]),
        border_radius=16,
        # Раунд 10 (задача 4): клип по границе, чтобы скругление сохранялось
        # по всему периметру (иначе контент перекрывал нижние углы)
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        padding=ft.padding.all(16),
        content=ft.Column(controls=[ft.Text("Загрузка…")], scroll=ft.ScrollMode.AUTO, expand=True),
    )

    # Раунд 9 (задача 4): resize карточки — уголок в правом нижнем углу.
    # Раунд 15 (задача 3): хэндл больше НЕ позиционируется пиксельно (left/top):
    # при drag менялась ширина/высота карточки, а left/top хэндла пересчитывались
    # только при открытии — отсюда «хэндл остался на старом месте». Теперь хэндл
    # пришит к углу через right=0/bottom=0 (Positioned от краёв Stack, см.
    # constrained_control.dart): стек растёт вместе с карточкой, хэндл ВСЕГДА
    # следует за новым углом автоматически, без ручного пересчёта и update().
    def _make_card_resize():
        def _on_drag_update(e):
            try:
                delta_x = int(getattr(e, "delta_x", 0) or 0)
                delta_y = int(getattr(e, "delta_y", 0) or 0)
                if delta_x == 0 and delta_y == 0:
                    return
                try:
                    win_h = page.window.height or 860
                except Exception:
                    win_h = 860
                try:
                    win_w = page.width or 1280
                except Exception:
                    win_w = 1280
                cw = max(600, min(int(win_w * 0.95), state.get("card_w", 920) + delta_x))
                ch = max(400, min(int(win_h * 0.92), state.get("card_h", 780) + delta_y))
                state["card_w"] = cw
                state["card_h"] = ch
                detail_card.width = cw
                detail_card.height = ch
                try:
                    _safe_update(detail_card)
                except Exception:
                    traceback.print_exc()
            except Exception:
                traceback.print_exc()

        def _on_drag_end(e=None):
            # сохранить размеры в настройки
            try:
                settings["card_width"] = state.get("card_w", 920)
                settings["card_height"] = state.get("card_h", 780)
                save_settings(settings)
            except Exception:
                traceback.print_exc()

        handle = ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.RESIZE_DOWN_RIGHT,
            on_pan_update=_on_drag_update,
            on_pan_end=_on_drag_end,
            content=ft.Container(
                width=22,
                height=22,
                bgcolor="transparent",
                # Раунд 15 (задача 3): видимый «уголок»-глиф, чтобы было видно,
                # за что тянуть (уголок из двух линий в правом нижнем углу).
                alignment=ft.alignment.bottom_right,
                padding=ft.padding.only(right=2, bottom=2),
                content=ft.Container(
                    width=14,
                    height=14,
                    border=ft.border.only(
                        right=ft.BorderSide(2, GLASS["text_muted"]),
                        bottom=ft.BorderSide(2, GLASS["text_muted"]),
                    ),
                ),
            ),
        )
        # Раунд 15 (задача 3): пришит к правому нижнему углу стека карточки.
        handle.right = 0
        handle.bottom = 0
        # Раунд 13 (задача 1): hover на хэндле убран (ранее был no-op)
        return handle

    card_resize_handle = _make_card_resize()

    # Раунд 9 (задача 5): полноразмерный предпросмотр вложений (поверх карточки)
    preview_root = ft.Container(
        visible=False,
        expand=True,
        bgcolor="#e604070f",
        alignment=ft.alignment.center,
        padding=ft.padding.all(24),
    )
    preview_body = ft.Container(
        width=800,
        height=560,
        bgcolor=GLASS["surface_solid"],
        border=ft.border.all(1, GLASS["border"]),
        border_radius=12,
        padding=ft.padding.all(12),
        content=ft.Column(controls=[ft.Text("Загрузка…")], spacing=8, tight=True),
    )
    preview_root.content = preview_body

    # Detail overlay Stack: card + global calendar dropdown + preview (top layer)
    detail_overlay = ft.Stack(
        controls=[detail_card, global_cal_root, card_resize_handle, preview_root],
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

    # Раунд 14 (задача 3): «Справочники» — overlay-Container (НЕ AlertDialog),
    # с resize за правый нижний угол и построчным скроллом списков.
    refs_overlay = ft.Container(
        visible=False,
        bgcolor=GLASS["overlay_bg"],
        expand=True,
        padding=ft.padding.all(16),
        alignment=ft.alignment.center,
    )

    def _apply_pending_on_close():
        """Задача 3: при закрытии карточки применить накопленные сетевые изменения (merge)."""
        pending = state["pending_shared"]
        state["pending_shared"] = None
        try:
            if pending is None:
                return
            merged = merge_controls(state["controls"], pending["controls"])
            state["controls"] = merged
            state["shared_mtime"] = pending["mtime"]
            state["last_sync"] = datetime.now()
            state["network_ok"] = True
            _sync_attachments(merged)
            _persist(state["controls"])
            _rebuild_table()
            _refresh_counters()
        except Exception:
            traceback.print_exc()

    def _hide_detail(e=None):
        detail_overlay_container.visible = False
        state["editing"] = False
        _close_global_cal()
        # раунд 9: закрыть предпросмотр вложений вместе с карточкой
        try:
            if preview_root.visible:
                preview_root.visible = False
        except Exception:
            traceback.print_exc()
        if state["pending_shared"] is not None:
            _apply_pending_on_close()
        else:
            # фон мог поменяться из-за «сети вернулась» при открытой карточке — перестроим
            try:
                _rebuild_table()
                _refresh_counters()
            except Exception:
                traceback.print_exc()
        state["pending_dialog_shown"] = False
        try:
            _safe_update(detail_overlay_container)
        except Exception:
            traceback.print_exc()

    def _open_detail(ctl: Optional[Control]):
        is_new = ctl is None
        state["editing"] = True
        state["pending_dialog_shown"] = False
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
        # Раунд 15 (задача 3): STRETCH — карточки пунктов на всю ширину секции.
        tasks_col = ft.Column(spacing=8, tight=True,
                              horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
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
        milestones_col = ft.Column(spacing=8, tight=True,
                                   horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
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

        # Attachments — раунд 9 (задача 5): миниатюра для изображений/PDF,
        # клик по миниатюре/имени — полноразмерный предпросмотр в overlay
        # (preview_root/preview_body объявлены на уровне detail_overlay)
        attach_col = ft.Column(spacing=6, tight=True,
                               horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        def _resolve_abs(rel: str):
            import os as _os
            try:
                path = resolve_attachment(detail_state["control_id"], rel, settings)
                return str(path) if (path and _os.path.exists(str(path))) else None
            except Exception:
                return None

        def _close_preview(e=None):
            preview_root.visible = False
            try:
                _safe_update(preview_root)
            except Exception:
                traceback.print_exc()

        def _open_preview(rel: str):
            abs_path = _resolve_abs(rel)
            if not abs_path:
                from ui.toast import show_error_toast
                show_error_toast(page, "Файл вложения не найден")
                return
            fn = rel.split("/")[-1]
            low = fn.lower()
            is_img = low.endswith((".png", ".jpg", ".jpeg"))
            # Раунд 10 (задача 5): предпросмотр ~90% ширины и ~85% высоты окна
            try:
                win_w = page.width or 1280
            except Exception:
                win_w = 1280
            try:
                win_h = page.window.height or 860
            except Exception:
                win_h = 860
            body_w = max(640, int(win_w * 0.9))
            body_h = max(480, int(win_h * 0.85))
            preview_body.width = body_w
            preview_body.height = body_h
            img_w = max(560, body_w - 48)
            img_h = max(380, body_h - 110)
            controls = []
            header_row = ft.Row(controls=[
                ft.Icon(ft.icons.IMAGE if is_img else ft.icons.PICTURE_AS_PDF, size=18, color=GLASS["accent"]),
                ft.Text(fn, size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"], expand=True,
                        no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, tooltip=fn),
                ft.IconButton(icon=ft.icons.OPEN_IN_NEW, icon_size=16, icon_color=GLASS["accent"],
                              tooltip="Открыть в программе", on_click=lambda e: _open_attach(rel)),
                ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=16, icon_color=GLASS["overdue"],
                              tooltip="Удалить", on_click=lambda e: (_close_preview(), _confirm_remove_attach(rel))),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=16, icon_color=GLASS["text_secondary"],
                              tooltip="Закрыть", on_click=_close_preview),
            ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            controls.append(header_row)
            if is_img:
                try:
                    img = ft.Image(src=abs_path, fit=ft.ImageFit.CONTAIN,
                                   width=img_w, height=img_h, border_radius=8)
                    controls.append(img)
                except Exception:
                    traceback.print_exc()
                    controls.append(ft.Text("Не удалось загрузить изображение", size=12, color=GLASS["text_secondary"]))
            else:
                controls.append(ft.Container(
                    content=ft.Column(controls=[
                        ft.Icon(ft.icons.PICTURE_AS_PDF, size=96, color=GLASS["text_muted"]),
                        ft.Text("PDF — предпросмотр недоступен, откройте в программе", size=14,
                                color=GLASS["text_secondary"]),
                    ], spacing=10, tight=True, alignment=ft.MainAxisAlignment.CENTER,
                       horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    expand=True,
                ))
            preview_body.content = ft.Column(controls=controls, spacing=10, tight=True)
            preview_root.visible = True
            try:
                _safe_update(preview_root)
                _safe_update(preview_body)
            except Exception:
                traceback.print_exc()

        def _thumb_for(rel: str):
            """Миниатюра 44x44: изображение — ft.Image, PDF — иконка."""
            abs_path = _resolve_abs(rel)
            fn = rel.split("/")[-1]
            low = fn.lower()
            if low.endswith((".png", ".jpg", ".jpeg")):
                if abs_path:
                    try:
                        return ft.Container(
                            content=ft.Image(src=abs_path, width=44, height=44,
                                             fit=ft.ImageFit.COVER, border_radius=6),
                            width=44, height=44, border_radius=6,
                            border=ft.border.all(1, GLASS["border"]),
                        )
                    except Exception:
                        traceback.print_exc()
            if low.endswith(".pdf"):
                return ft.Container(
                    content=ft.Icon(ft.icons.PICTURE_AS_PDF, size=26, color=GLASS["overdue"]),
                    width=44, height=44, border_radius=6, bgcolor=with_alpha(GLASS["overdue"], "18"),
                    alignment=ft.alignment.center,
                )
            return ft.Container(
                content=ft.Icon(ft.icons.DESCRIPTION_OUTLINED, size=22, color=GLASS["text_muted"]),
                width=44, height=44, border_radius=6, bgcolor=GLASS["surface_alt"],
                alignment=ft.alignment.center,
            )

        def _rebuild_attach():
            attach_col.controls.clear()
            for rel in detail_state["attachments"]:
                fn = rel.split("/")[-1]
                attach_col.controls.append(
                    glass_panel(
                        content=ft.Row(controls=[
                            _thumb_for(rel),
                            ft.Text(fn, size=11, color=GLASS["text"], expand=True, no_wrap=True,
                                    overflow=ft.TextOverflow.ELLIPSIS, tooltip=fn),
                            ft.IconButton(icon=ft.icons.ZOOM_IN, icon_size=16, icon_color=GLASS["accent"],
                                          tooltip="Предпросмотр", on_click=lambda e, r=rel: _open_preview(r)),
                            ft.IconButton(icon=ft.icons.OPEN_IN_NEW, icon_size=14, icon_color=GLASS["text_secondary"],
                                          tooltip="Открыть", on_click=lambda e, r=rel: _open_attach(r)),
                            ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_size=14, icon_color=GLASS["overdue"],
                                          tooltip="Удалить", on_click=lambda e, r=rel: _confirm_remove_attach(r)),
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
            # Раунд 13 (задача 5): у новой карточки control_id уже uuid (см.
            # _open_detail), но страховка на краевых случаях — генерируем, если
            # вдруг None/пусто. Иначе shared_dir / ... / None -> TypeError.
            cid = detail_state.get("control_id")
            if not cid:
                cid = str(uuid4())
                detail_state["control_id"] = cid
            added = []
            failed = 0
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
                    try:
                        rel = copy_attachment_to_shared(cid, fpath, settings)
                    except Exception:
                        # сеть отключена/недоступна — падаем в локальное копирование
                        traceback.print_exc()
                        rel = None
                if not rel:
                    # Раунд 13 (задача 5): локальное копирование как фолбэк
                    rel = copy_attachment_to_local(cid, fpath)
                if rel and rel not in detail_state["attachments"]:
                    detail_state["attachments"].append(rel)
                    added.append(rel)
                elif not rel:
                    failed += 1
            if added:
                # файлы видны сразу: перестроить список вложений
                _rebuild_attach()
                if not detail_state["is_new"]:
                    for x in state["controls"]:
                        if x.id == cid:
                            x.attachments = list(detail_state["attachments"])
                            break
                    try:
                        _persist(state["controls"])
                    except Exception:
                        traceback.print_exc()
                try:
                    page.update()
                except Exception:
                    traceback.print_exc()
                # toast только после успешного копирования
                from ui.toast import show_toast
                show_toast(page, f"Файл прикреплён: {len(added)}", icon=ft.icons.ATTACH_FILE)
            if failed:
                from ui.toast import show_error_toast
                show_error_toast(page, "Не удалось прикрепить файл")

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
        # Раунд 15 (задача 3): horizontal_alignment=STRETCH у колонок карточки —
        # секции-панели и поля (content_field/comment_field без явной ширины)
        # растягиваются на всю ширину гибкой колонки и ПЕРЕРИСОВЫВАЮТСЯ вместе с
        # resize карточки (раньше вся внутренняя раскладка была shrink-wrap и
        # оставалась шириной 500/374 px при растянутой карточке). STRETCH действует
        # только по горизонтали (поперечная ось вертикального скролла ограничена),
        # поэтому запрет expand-вертикали §15.11/22 не нарушается.
        left_col = ft.Column(spacing=14, tight=True,
                             horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
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
        ], spacing=12, tight=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

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
        ], spacing=12, tight=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        left_col.controls.append(glass_panel(content=ft.Column(controls=[ft.Text("Исполнение", size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"]), ispol_content], spacing=8, tight=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH), radius=12, padding=ft.padding.all(14), bgcolor=GLASS["card_section"]))

        # Comment
        left_col.controls.append(glass_panel(content=_field_with_label("Комментарий", comment_field), radius=12, padding=ft.padding.all(14), bgcolor=GLASS["card_section"]))

        # Right column - Bug 8 fix: no expand
        right_col = ft.Column(spacing=14, tight=True,
                              horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        # Section Сроки — no always open calendar (Bug 9 fix), only fields that open shared global calendar
        sroki_content = ft.Column(controls=[
            ft.Text("Сроки", size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
            _field_with_label("Следующая дата исполнения", due_box),
            cycle_hint,
            _field_with_label("Конечная дата", end_box),
        ], spacing=8, tight=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        right_col.controls.append(glass_panel(content=sroki_content, radius=12, padding=ft.padding.all(14), bgcolor=GLASS["card_section"]))

        # Pункты задания
        tasks_section = ft.Column(controls=[
            ft.Row(controls=[ft.Icon(ft.icons.FORMAT_LIST_BULLETED, size=16, color=GLASS["text"]), ft.Text("Пункты задания", size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"]), ft.Container(expand=True), ft.ElevatedButton("+ Добавить пункт", bgcolor=GLASS["surface_alt"], color=GLASS["accent"], height=32, style=ft.ButtonStyle(side=ft.BorderSide(1, GLASS["border"]), shape=ft.RoundedRectangleBorder(radius=8)), on_click=_add_task)], spacing=6, tight=True),
            tasks_col,
        ], spacing=8, tight=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        right_col.controls.append(glass_panel(content=tasks_section, radius=12, padding=ft.padding.all(14), bgcolor=GLASS["card_section"]))

        # Milestones
        if (ctl.control_type if ctl else ONE_TIME) == PERIODIC or True:
            miles_section = ft.Column(controls=[
                ft.Row(controls=[ft.Icon(ft.icons.TIMELINE, size=15, color=GLASS["text"]), ft.Text("Промежуточные точки", size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"]), ft.Container(expand=True), ft.ElevatedButton("+ Добавить точку", bgcolor=GLASS["surface_alt"], color=GLASS["accent"], height=28, style=ft.ButtonStyle(side=ft.BorderSide(1, GLASS["border"]), shape=ft.RoundedRectangleBorder(radius=8)), on_click=_add_mile)], spacing=6, tight=True),
                milestones_col,
            ], spacing=8, tight=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
            right_col.controls.append(glass_panel(content=miles_section, radius=12, padding=ft.padding.all(14), bgcolor=GLASS["card_section"]))

        # Scan
        scan_section = ft.Column(controls=[
            ft.Row(controls=[ft.Icon(ft.icons.ATTACH_FILE, size=15, color=GLASS["text"]), ft.Text("Скан задания", size=13, weight=ft.FontWeight.BOLD, color=GLASS["text"]), ft.Container(expand=True), ft.ElevatedButton("Прикрепить файл", bgcolor=GLASS["surface_alt"], color=GLASS["accent"], height=32, style=ft.ButtonStyle(side=ft.BorderSide(1, GLASS["border"]), shape=ft.RoundedRectangleBorder(radius=8)), icon=ft.icons.ATTACH_FILE, on_click=_pick_attach)], spacing=6, tight=True),
            attach_col,
        ], spacing=8, tight=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        right_col.controls.append(glass_panel(content=scan_section, radius=12, padding=ft.padding.all(14), bgcolor=GLASS["card_section"]))

        # Decide layout based on page width
        # Bug 8 fix: no expand inside scroll, fixed widths
        try:
            is_narrow = (page.width or 1280) < 1100
        except Exception:
            is_narrow = False

        # Раунд 15 (задача 3): колонки ГИБКИЕ — flex 11/8 вместо фиксированных
        # 500/374 px. Row БЕЗ tight (MainAxisSize.max): внутри вертикального
        # скролла карточки (SingleChildScrollView) поперечная ось ограничена
        # шириной viewport'а, поэтому Row занимает всю внутреннюю ширину карточки,
        # а expand-обёртки делят её ~58%/~42%. При растягивании карточки колонки
        # и поля (TextField на всю ширину) тянутся вместе с ней. Вертикальный expand
        # внутри scroll-КОЛОНКИ по-прежнему не используется (AGENTS §15.11/22) —
        # здесь expand только горизонтальный (внутри Row), что разрешено.
        if is_narrow:
            middle_content = ft.Column(controls=[left_col, right_col], spacing=14, tight=True,
                                       horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        else:
            middle_content = ft.Row(controls=[
                ft.Container(content=left_col, expand=11, alignment=ft.alignment.top_left),
                ft.Container(content=right_col, expand=8, alignment=ft.alignment.top_left),
            ], spacing=14, vertical_alignment=ft.CrossAxisAlignment.START)

        # Middle scroll: bounded by the card's fixed height (via expand in the bounded
        # card Column), so its inner scroll column scrolls internally instead of growing
        # unbounded / collapsing. Matches the control_card_modal pattern.
        # Раунд 15 (задача 3): STRETCH — middle_content занимает всю внутреннюю
        # ширину карточки (поперечная ось скролла ограничена — это легально).
        middle_scroll = ft.Container(
            content=ft.Column(controls=[middle_content], spacing=0, tight=True,
                              scroll=ft.ScrollMode.AUTO,
                              horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
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
        # Раунд 9 (задача 4): размеры из настроек (сохранённые пользователем),
        # с ограничениями по окну
        cw = max(600, min(int(win_h * 1.6), state.get("card_w", 920)))
        ch = max(400, min(card_max_h, state.get("card_h", 780)))
        detail_card.width = cw
        detail_card.height = ch
        state["card_w"] = cw
        state["card_h"] = ch
        # Раунд 15 (задача 3): resize-хэндл пришит к углу через right=0/bottom=0 —
        # позиционировать его при открытии/resize больше не нужно, он следует
        # за правым нижним углом карточки автоматически (Positioned от краёв Stack).
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
    def _open_references(e=None):
        """Раунд 9 (задача 3): редактор справочников — исполнители, контролёры, инициаторы."""
        from core.controls_data import (
            add_extra_person,
            rename_person, remove_person,
            rename_initiator, remove_initiator,
        )

        def _build_list_col(source_getter, on_add, on_remove, on_edit, empty_text):
            # Раунд 10 (задача 3): поле добавления растянуто на всю ширину,
            # редактирование записи — инлайн (карандаш → поле + галочка/крестик),
            # без вложенных диалогов.
            # Раунд 13 (задача 3): компактные строки (~30 px) и маленькие кнопки —
            # одно движение колеса прокручивает меньше, скролл построчный и плавный.
            # Раунд 15 (задача 4): список растягивается вместе с окном — expand=True
            # ВМЕСТО фиксированной высоты 180. Это легально: родительская колонка
            # секции НЕ скроллится и её высота ограничена refs_card (паттерн
            # «bounded column + scroll inside»), запрет AGENTS §15.11 касается
            # expand ВНУТРИ Column(scroll=AUTO).
            col = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
            # Раунд 14 (задача 3): колесо — 1–2 строки за щелчок
            col.on_scroll = _make_row_scroller(col, 32)
            field = _glass_textfield(hint="Новое значение…", expand=True)
            field.height = 32
            edit_state = {"idx": None}

            def _rebuild():
                col.controls.clear()
                items = source_getter()
                if not items:
                    col.controls.append(ft.Text(empty_text, size=11, color=GLASS["text_muted"]))
                for i, it in enumerate(items):
                    if edit_state["idx"] == i:
                        # инлайн-редактирование текущей записи
                        edit_field = _glass_textfield(value=it, expand=True)
                        edit_field.height = 30

                        def _save(e=None, old=it, idx=i):
                            new_val = (edit_field.value or "").strip()
                            # Раунд 13 (задача 3): сохраняем и при переименовании
                            # базовой записи (rename_* сам разруливает extra/hidden)
                            if new_val:
                                on_edit(old, new_val)
                            edit_state["idx"] = None
                            _rebuild()

                        def _cancel(e=None):
                            edit_state["idx"] = None
                            _rebuild()

                        col.controls.append(ft.Container(
                            content=ft.Row(controls=[
                                edit_field,
                                ft.IconButton(icon=ft.icons.CHECK, icon_size=16, width=26, height=26, padding=0,
                                              icon_color=GLASS["in_progress"], tooltip="Сохранить",
                                              on_click=_save),
                                ft.IconButton(icon=ft.icons.CLOSE, icon_size=16, width=26, height=26, padding=0,
                                              icon_color=GLASS["text_secondary"], tooltip="Отмена",
                                              on_click=_cancel),
                            ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]),
                            border_radius=6, padding=ft.padding.symmetric(horizontal=6, vertical=1),
                        ))
                    else:
                        col.controls.append(ft.Container(
                            content=ft.Row(controls=[
                                ft.Text(it, size=12, color=GLASS["text"], expand=True,
                                       no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, tooltip=it),
                                ft.IconButton(icon=ft.icons.EDIT_OUTLINED, icon_size=14, width=26, height=26, padding=0,
                                              icon_color=GLASS["text_secondary"], tooltip="Переименовать",
                                              on_click=lambda e, idx=i: _edit(idx)),
                                ft.IconButton(icon=ft.icons.CLOSE, icon_size=14, width=26, height=26, padding=0,
                                              icon_color=GLASS["overdue"], tooltip="Удалить",
                                              on_click=lambda e, n=it: _del(n)),
                            ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]),
                            border_radius=6, padding=ft.padding.symmetric(horizontal=6, vertical=1),
                        ))
                try:
                    _safe_update(col)
                except Exception:
                    traceback.print_exc()

            def _edit(idx):
                edit_state["idx"] = idx
                _rebuild()

            def _add(e=None):
                val = (field.value or "").strip()
                if val:
                    on_add(val)
                    field.value = ""
                    try:
                        _safe_update(field)
                    except Exception:
                        traceback.print_exc()
                    _rebuild()

            def _del(name):
                on_remove(name)
                _rebuild()

            add_btn = ft.ElevatedButton("Добавить", bgcolor=GLASS["surface_alt"], color=GLASS["accent"],
                                        height=34, style=ft.ButtonStyle(side=ft.BorderSide(1, GLASS["border"]),
                                        shape=ft.RoundedRectangleBorder(radius=8)), on_click=_add)
            col._rebuild = _rebuild
            col._get_items = source_getter
            return col, field, add_btn

        # Источники: базовые (криминалисты/контролёры — read-only) + extra_people (редактируемое)
        def _people_items():
            return list(get_controller_names(settings))

        def _people_add(name):
            add_extra_person(settings, name)

        def _people_remove(name):
            # Раунд 13 (задача 3): удаляется и базовое ФИО (через hidden_people),
            # изменение сохраняется в controls_settings.json
            remove_person(settings, name)

        def _people_edit(old, new):
            # Раунд 13 (задача 3): сохранение редактирования ЛЮБОЙ записи —
            # доп. ФИО заменяется в extra_people, базовое — new в extra_people
            # + old в hidden_people; settings пишутся сразу.
            rename_person(settings, old, new)

        def _init_items():
            # Раунд 13: список с учётом переименований/скрытий из справочника
            return initiator_filter_options(set(initiators) | {c.initiator for c in state["controls"] if c.initiator}, settings)

        def _init_add(name):
            cur = list(settings.get("custom_initiators", []) or [])
            if name not in cur:
                cur.append(name)
            settings["custom_initiators"] = cur
            save_settings(settings)
            initiators.clear()
            initiators.extend(get_initiators(settings))

        def _init_remove(name):
            # Раунд 13 (задача 3): убирается и производный кластер (hidden_init_groups)
            remove_initiator(settings, name)
            initiators.clear()
            initiators.extend(get_initiators(settings))

        def _init_edit(old, new):
            # Раунд 13 (задача 3): редактирование сохраняется для любой записи:
            # пользовательский заменяется в custom_initiators, производный
            # кластер — через init_renames (new вместо old в опциях фильтра)
            rename_initiator(settings, old, new)
            initiators.clear()
            initiators.extend(get_initiators(settings))

        people_col, people_field, people_add = _build_list_col(
            _people_items, _people_add, _people_remove, _people_edit,
            "Нет доп. ФИО (базовые — криминалисты и контролёры)")
        init_col, init_field, init_add = _build_list_col(
            _init_items, _init_add, _init_remove, _init_edit, "Нет инициаторов")
        # сразу наполнить списки (иначе модалка откроется пустой)
        people_col._rebuild()
        init_col._rebuild()

        def _apply(e=None):
            nonlocal executor_canonical, controller_canonical
            _close_refs()
            # пересобрать каноны и фильтры
            executor_canonical = get_controller_names(settings)
            controller_canonical = get_controller_names(settings)
            _refresh_filter_options()
            _rebuild_table()
            _refresh_counters()

        def _close_refs(e=None):
            refs_overlay.visible = False
            try:
                _safe_update(refs_overlay)
            except Exception:
                traceback.print_exc()

        # Раунд 14 (задача 3): карточка справочников — фикс-размер с resize за
        # правый нижний угол; равномерная рамка + скругление + клип (как карточка).
        refs_card = ft.Container(
            width=680,
            height=560,
            bgcolor=GLASS["card_panel"],
            border=ft.border.all(1, GLASS["border"]),
            border_radius=16,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            padding=ft.padding.all(16),
        )

        def _refs_on_pan_update(e):
            try:
                dx = int(getattr(e, "delta_x", 0) or 0)
                dy = int(getattr(e, "delta_y", 0) or 0)
            except Exception:
                return
            if dx == 0 and dy == 0:
                return
            try:
                win_w = page.width or 1280
            except Exception:
                win_w = 1280
            try:
                win_h = page.window.height or 860
            except Exception:
                win_h = 860
            nw = max(480, min(int(win_w * 0.95), refs_card.width + dx))
            # Раунд 15 (задача 4): min-высота 420 — футер «Применить» виден всегда
            # (при 360 он проваливался за нижний край карточки).
            nh = max(420, min(int(win_h * 0.92), refs_card.height + dy))
            refs_card.width = nw
            refs_card.height = nh
            # Раунд 15 (задача 4): refs_handle больше НЕ позиционируется пиксельно
            # (left/top) — он пришит к углу через right=0/bottom=0 (см. ниже), поэтому
            # следует за углом карточки автоматически; ручной пересчёт здесь не нужен
            # и был причиной «хэндл замер на месте».
            _quiet_update(refs_card)

        refs_handle = ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.RESIZE_DOWN_RIGHT,
            on_pan_update=_refs_on_pan_update,
            on_pan_end=lambda e: None,
            content=ft.Container(
                width=22,
                height=22,
                bgcolor="transparent",
                # видимый «уголок»-глиф (как у карточки контроля)
                alignment=ft.alignment.bottom_right,
                padding=ft.padding.only(right=2, bottom=2),
                content=ft.Container(
                    width=14,
                    height=14,
                    border=ft.border.only(
                        right=ft.BorderSide(2, GLASS["text_muted"]),
                        bottom=ft.BorderSide(2, GLASS["text_muted"]),
                    ),
                ),
            ),
        )
        # Раунд 15 (задача 4): пришит к правому нижнему углу стека (Positioned от
        # краёв). Стек размером с refs_card, поэтому хэндл ВСЕГДА в углу карточки —
        # и при открытии, и при любом resize.
        refs_handle.right = 0
        refs_handle.bottom = 0

        # Раунд 15 (задача 4): корневая колонка БЕЗ scroll — иначе футер «Применить»
        # уезжал за нижний край при исходном размере карточки (scroll-колонка не
        # расталкивает детей по высоте). Теперь refs_card даёт колонке ограниченную
        # высоту (width/height + padding), поэтому:
        #   * header и footer ВНЕ скролла — футер прибит к низу и виден всегда;
        #   * две секции-Container с expand=1 делят середину пополам и РАСТУТ
        #     вместе с карточкой при resize;
        #   * внутри секции колонка НЕ tight (MainAxisSize.max): список
        #     (scroll=AUTO, expand=True) занимает весь остаток секции и скроллится
        #     внутри — паттерн «bounded column + scroll inside» (AGENTS §15.11
        #     запрещает expand только ВНУТРИ скроллящейся колонки — здесь секция
        #     не скроллится).
        refs_body = ft.Column(
            controls=[
                ft.Row(controls=[ft.Icon(ft.icons.BOOK_OUTLINED, size=20, color=GLASS["text"]),
                                 ft.Text("Справочники", size=16, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
                                 ft.Container(expand=True),
                                 ft.IconButton(icon=ft.icons.CLOSE, icon_size=18, icon_color=GLASS["text_secondary"],
                                               tooltip="Закрыть", on_click=_close_refs)],
                      spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Text("Исполнители / контролёры (канонические ФИО для фильтров)", size=12,
                                weight=ft.FontWeight.BOLD, color=GLASS["text"]),
                        # Раунд 10 (задача 3): поле растянуто на всю ширину
                        ft.Row(controls=[people_field, people_add], spacing=6,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        people_col,
                    ], spacing=6),
                    bgcolor=GLASS["surface"], border=ft.border.all(1, GLASS["border"]),
                    border_radius=10, padding=ft.padding.all(10),
                    expand=1,
                ),
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Text("Инициаторы (канонические названия для фильтра)", size=12,
                                weight=ft.FontWeight.BOLD, color=GLASS["text"]),
                        ft.Row(controls=[init_field, init_add], spacing=6,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        init_col,
                    ], spacing=6),
                    bgcolor=GLASS["surface"], border=ft.border.all(1, GLASS["border"]),
                    border_radius=10, padding=ft.padding.all(10),
                    expand=1,
                ),
                ft.Row(controls=[ft.Container(expand=True),
                                 ft.TextButton("Отмена", on_click=_close_refs,
                                               style=ft.ButtonStyle(color=GLASS["text_secondary"])),
                                 ft.ElevatedButton("Применить", bgcolor=GLASS["accent"],
                                                   color="#ffffff", on_click=_apply)],
                      spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ],
            spacing=10,
            expand=True,
        )
        refs_card.content = refs_body
        refs_overlay.content = ft.Stack(controls=[refs_card, refs_handle])
        refs_overlay.visible = True
        try:
            _safe_update(refs_overlay)
        except Exception:
            print("[CONTROLS_TAB] references overlay error")

    def _open_settings(e=None):
        from .controls_settings_modal import create_controls_settings_modal
        def on_apply_inner(new_settings):
            nonlocal soon_days, network_role, network_user, executor_canonical, controller_canonical
            settings.clear()
            settings.update(new_settings)
            save_settings(new_settings)
            soon_days = int(new_settings.get("soon_days", 3) or 3)
            network_role = new_settings.get("network_role", "admin") or "admin"
            network_user = new_settings.get("network_user", "") or ""
            # Раунд 8: справочник людей мог измениться — пересобираем каноны фильтров
            executor_canonical = get_controller_names(settings)
            controller_canonical = get_controller_names(settings)
            initiators.clear()
            initiators.extend(get_initiators(settings))
            try:
                initiator_filter_dd.options = [ft.dropdown.Option("all", "Все инициаторы")] + [ft.dropdown.Option(i) for i in initiator_filter_options(initiators, settings)]
                _safe_update(initiator_filter_dd)
            except Exception:
                traceback.print_exc()
            # «Удалить все» — только админ
            try:
                delete_all_btn.visible = (network_role == "admin")
                _safe_update(delete_all_btn)
            except Exception:
                traceback.print_exc()
            _update_sync_ui()
            _load_initial()
            _rebuild_table()
            _refresh_counters()
        dialog = create_controls_settings_modal(page, settings, on_apply_inner)
        page.open(dialog)

    def _delete_all(e=None):
        """Раунд 7 (задача 3): удалить ВСЕ контроли (локально + shared). Только админ."""
        if network_role != "admin":
            return
        confirm_field = _glass_textfield(hint="Введите слово УДАЛИТЬ", width=220)
        err_text = ft.Text("", size=11, color=GLASS["overdue"])
        def _check(e=None):
            ok = ((confirm_field.value or "").strip().upper() == "УДАЛИТЬ")
            confirm_btn.disabled = not ok
            err_text.value = "" if ok else "Введите слово УДАЛИТЬ для подтверждения"
            try:
                _safe_update(confirm_btn)
                _safe_update(err_text)
            except Exception:
                traceback.print_exc()
        def _do(e=None):
            try:
                if ((confirm_field.value or "").strip().upper() != "УДАЛИТЬ"):
                    return
                page.close(dlg)
                state["controls"] = []
                save_controls([])
                if settings.get("network_enabled"):
                    try:
                        write_shared_controls([], settings)
                    except Exception:
                        print("[CONTROLS_TAB] delete all shared write error")
                    try:
                        state["shared_mtime"] = get_shared_mtime(settings)
                    except Exception:
                        traceback.print_exc()
                settings["notify_log"] = {}
                save_settings(settings)
                state["known_ids"] = set()
                state["my_status_map"] = {}
                state["known_attachments"] = {}
                state["pending_shared"] = None
                state["last_overdue"] = -1
                _rebuild_table()
                _refresh_counters()
                _refresh_filter_options()
                from ui.toast import show_toast
                show_toast(page, "Все контроли удалены", icon=ft.icons.DELETE_FOREVER)
            except Exception:
                traceback.print_exc()
        def _cancel(e=None):
            try:
                page.close(dlg)
            except Exception:
                traceback.print_exc()
        confirm_btn = ft.ElevatedButton("Удалить всё", icon=ft.icons.DELETE_FOREVER, bgcolor=GLASS["overdue"], color="#ffffff", disabled=True, on_click=_do)
        confirm_field.on_change = _check
        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=GLASS["surface_solid"],
            title=ft.Text("Удаление всех контролей", size=15, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
            content=ft.Column(controls=[
                ft.Text("Уверены, что хотите удалить ВСЕ контроли? Это действие нельзя отменить.",
                        size=12, color=GLASS["text"]),
                ft.Container(height=4),
                confirm_field,
                err_text,
            ], spacing=6, tight=True),
            actions=[
                ft.TextButton("Отмена", on_click=_cancel, style=ft.ButtonStyle(color=GLASS["text_secondary"])),
                confirm_btn,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        try:
            page.open(dlg)
        except Exception:
            print("[CONTROLS_TAB] delete all dialog error")

    def _add_control(e=None):
        _open_detail(None)

    # Title row
    add_btn = ft.ElevatedButton(text="Добавить контроль", icon=ft.icons.ADD_CIRCLE_OUTLINE, bgcolor=GLASS["accent"], color="#ffffff", height=40, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=ft.padding.symmetric(horizontal=16)), on_click=_add_control)
    import_btn = ft.ElevatedButton(text="Импорт Excel", icon=ft.icons.UPLOAD_FILE, bgcolor=GLASS["surface"], color=GLASS["text"], height=40, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), side=ft.BorderSide(1, GLASS["border"]), padding=ft.padding.symmetric(horizontal=12)), on_click=_import)
    export_btn = ft.ElevatedButton(text="Экспорт Excel", icon=ft.icons.FILE_DOWNLOAD_OUTLINED, bgcolor=GLASS["in_progress"], color=GLASS["surface_solid"], height=40, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=ft.padding.symmetric(horizontal=14)), on_click=_export)
    delete_all_btn = ft.ElevatedButton(text="Удалить все", icon=ft.icons.DELETE_FOREVER, bgcolor=with_alpha(GLASS["overdue"], "22"), color=GLASS["overdue"], height=40, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), side=ft.BorderSide(1, GLASS["overdue"]), padding=ft.padding.symmetric(horizontal=12)), on_click=_delete_all, visible=(network_role == "admin"))
    settings_btn = ft.IconButton(icon=ft.icons.SETTINGS_OUTLINED, icon_size=20, icon_color=GLASS["text_secondary"], tooltip="Настройки", style=ft.ButtonStyle(bgcolor=GLASS["surface"], shape=ft.RoundedRectangleBorder(radius=10), side=ft.BorderSide(1, GLASS["border"])), on_click=_open_settings)
    refs_btn = ft.ElevatedButton(text="Справочники", icon=ft.icons.BOOK_OUTLINED, bgcolor=GLASS["surface"], color=GLASS["text"], height=40, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), side=ft.BorderSide(1, GLASS["border"]), padding=ft.padding.symmetric(horizontal=12)), on_click=_open_references)

    title_content = ft.Row(controls=[
        ft.Icon(ft.icons.RULE_FOLDER, size=20, color=GLASS["text"]),
        ft.Text("Контроли", size=20, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
        ft.Container(width=10),
        sync_dot, ft.Container(width=4), sync_label,
        ft.Container(expand=True),
        add_btn, import_btn, export_mode_dd, export_btn, delete_all_btn, refs_btn, settings_btn,
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
    # Раунд 14: refs_overlay поверх всего (после detail, чтобы хэндл resize
    # карточки оставался первым GestureDetector с on_pan_update в обходе тестов)
    tab_stack = ft.Stack(controls=[tab_bg, filter_cal_root, detail_overlay_container, refs_overlay], expand=True)
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
            try:
                _check_my_notifications()
            except Exception as e:
                print(f"[CONTROLS_TAB] my notify error: {e}")

    def _notify_user(message: str):
        """Персональное уведомление: звук + toast (вызовы из фонового потока — в try/except)."""
        if settings.get("notify_sound", True):
            try:
                _play_notify_sound()
            except Exception:
                pass
        try:
            from ui.toast import show_toast
            show_toast(page, message, icon=ft.icons.NOTIFICATIONS_ACTIVE)
        except Exception:
            print("[CONTROLS_TAB] my notification toast error")

    def _show_shared_conflict_dialog():
        """Задача 3: диалог «Данные на сервере изменились» (1 раз на открытие карточки)."""
        def _update(e=None):
            try:
                page.close(dlg)
            except Exception:
                traceback.print_exc()
            _hide_detail()  # закрыть карточку без сохранения + применить pending_shared
            try:
                from ui.toast import show_toast
                show_toast(page, "Данные обновлены из сети", icon=ft.icons.CLOUD_SYNC)
            except Exception:
                traceback.print_exc()
        def _later(e=None):
            try:
                page.close(dlg)
            except Exception:
                traceback.print_exc()
        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=GLASS["surface_solid"],
            title=ft.Text("Данные на сервере изменились", size=15, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
            content=ft.Text("Обновить сейчас? Открытая карточка будет закрыта без сохранения.",
                            size=12, color=GLASS["text"]),
            actions=[
                ft.TextButton("Позже", on_click=_later, style=ft.ButtonStyle(color=GLASS["text_secondary"])),
                ft.ElevatedButton("Обновить", bgcolor=GLASS["accent"], color="#ffffff", on_click=_update),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        try:
            page.open(dlg)
        except Exception:
            print("[CONTROLS_TAB] conflict dialog error")

    def _apply_shared_update(shared: List[Control], mtime: float, toast: bool = True):
        """Подхват сетевых изменений без открытой карточки (replace + ненавязчивый toast)."""
        state["controls"] = shared
        state["shared_mtime"] = mtime
        state["last_sync"] = datetime.now()
        state["network_ok"] = True
        _sync_attachments(shared)
        try:
            _update_sync_ui()
            _rebuild_table()
            _refresh_counters()
        except Exception:
            traceback.print_exc()
        if toast:
            try:
                from ui.toast import show_toast
                show_toast(page, "Данные обновлены из сети", icon=ft.icons.CLOUD_SYNC)
            except Exception:
                print("[CONTROLS_TAB] update toast error")

    def _on_network_back(mtime: float):
        """Задача 4: сеть вернулась после офлайна — merge (НЕ подмена), локальные правки дороже."""
        try:
            shared = read_shared_controls(settings)
        except Exception:
            shared = []
        if not shared:
            state["shared_mtime"] = mtime
            state["network_ok"] = True
            try:
                _update_sync_ui()
            except Exception:
                traceback.print_exc()
            return
        merged = merge_controls(state["controls"], shared)
        print(f"[CONTROLS_TAB] merge: {len(shared)} controls from shared")
        state["controls"] = merged
        state["shared_mtime"] = mtime
        state["last_sync"] = datetime.now()
        state["network_ok"] = True
        # отдать свои офлайн-правки обратно в shared
        try:
            write_shared_controls(merged, settings)
        except Exception:
            print("[CONTROLS_TAB] write shared error after reconnect")
        _sync_attachments(merged)
        if not state["editing"]:
            try:
                _update_sync_ui()
                _rebuild_table()
                _refresh_counters()
            except Exception:
                traceback.print_exc()
        try:
            from ui.toast import show_toast
            show_toast(page, "Сеть восстановлена, данные синхронизированы", icon=ft.icons.CLOUD_SYNC)
        except Exception:
            print("[CONTROLS_TAB] network back toast error")

    def _poll_network():
        if not settings.get("network_enabled"):
            return
        try:
            mtime = get_shared_mtime(settings)
        except Exception:
            mtime = None
        if mtime is None:
            # Задача 4: shared недоступен — красный индикатор
            if state["network_ok"]:
                state["network_ok"] = False
                try:
                    _update_sync_ui()
                except Exception:
                    traceback.print_exc()
            return
        if not state["network_ok"]:
            # сеть вернулась после офлайна
            try:
                _on_network_back(mtime)
            except Exception:
                traceback.print_exc()
            return
        if mtime == state["shared_mtime"]:
            return
        shared = read_shared_controls(settings)
        if not shared:
            return
        if state["editing"]:
            # Задача 3: карточка открыта — не трогаем state, копим в pending_shared
            state["pending_shared"] = {"controls": shared, "mtime": mtime}
            if not state["pending_dialog_shown"]:
                state["pending_dialog_shown"] = True
                try:
                    _show_shared_conflict_dialog()
                except Exception:
                    traceback.print_exc()
            return
        _apply_shared_update(shared, mtime)

    def _check_my_notifications():
        """Задача 2: персональные уведомления исполнителю (a — новый контроль, b — срок)."""
        if not settings.get("network_enabled"):
            return
        if network_role != "user" or not network_user:
            return
        try:
            today = date.today().isoformat()
            log = dict(settings.get("notify_log") or {})
            known = set(state["known_ids"] or set())
            changed = False
            # (a) новый контроль для меня
            for c in state["controls"]:
                if c.id in known:
                    continue
                if _mine(c) and _should_notify(log, c.id, "new", today):
                    log[f"{c.id}:new"] = today
                    changed = True
                    _notify_user(f"Новый контроль для вас: вх.№ {c.incoming_number or c.id}")
            # (b) срок по моему контролю (статус изменился + антиспам-журнал)
            status_map = dict(state["my_status_map"] or {})
            for c in state["controls"]:
                if not _mine(c) or c.done:
                    status_map.pop(c.id, None)
                    continue
                st = deadline_status(c, soon_days)
                prev = status_map.get(c.id)
                if prev != st and st in (OVERDUE, TODAY, SOON):
                    if _should_notify(log, c.id, st, today):
                        label = {OVERDUE: "просрочен", TODAY: "сегодня", SOON: "скоро"}.get(st, st)
                        log[f"{c.id}:{st}"] = today
                        changed = True
                        _notify_user(f"Срок по контролю вх.№ {c.incoming_number or c.id}: {label}")
                status_map[c.id] = st
            state["known_ids"] = {c.id for c in state["controls"]}
            state["my_status_map"] = status_map
            if changed:
                settings["notify_log"] = log
                save_settings(settings)
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
        # Раунд 15 (задача 2): при resize окна НЕ пересоздаём раскладку с нуля
        # (_layout_widths затирал ручные ширины колонок), а ВЫРАВНИВАЕМ текущие
        # ширины под новый бюджет (_fit_widths: переполнение — кламп, остаток —
        # в гибкие колонки) и применяем геометрию панели/заголовка/строк.
        try:
            prev = dict(_W)
            prev_w = int(table_container.width or 0)
            _fit_widths()
            tw = _table_width()
            if prev == _W and prev_w == tw:
                return  # размер таблицы не изменился — rebuild не нужен
            _apply_table_geometry()
        except Exception:
            traceback.print_exc()

    _prev_resize = getattr(page, "on_resize", None)
    def _combined_resize(e=None):
        _on_page_resize(e)
        # page.on_resize в Flet 0.23.2 возвращает EventHandler, а не функцию — не вызываем напрямую
        if _prev_resize is not None and callable(_prev_resize) and _prev_resize is not _combined_resize:
            try:
                _prev_resize(e)
            except Exception:
                traceback.print_exc()
    try:
        page.on_resize = _combined_resize
    except Exception:
            traceback.print_exc()

    _load_initial()
    # Раунд 15 (задача 2): начальная геометрия — явная ширина панели/заголовка/
    # строк до правого края + выравнивание колонок под бюджет окна (внутри
    # _apply_table_geometry вызываются _rebuild_header/_rebuild_table).
    _apply_table_geometry()
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

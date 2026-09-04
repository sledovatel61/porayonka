# -*- coding: utf-8 -*-
"""Раунд 39 (задача 1): конечная дата — очистка, persistence, Excel round-trip.

Проверяется ЧЕРЕЗ реальный обработчик UI (клик по крестику / «Очистить» в
едином глобальном календаре) и реальное сохранение в модель, а не ручным
присваиванием ожидаемого результата."""
import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import types
from datetime import date

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)
sys.path.insert(0, _HERE)

# ── изоляция данных ДО импорта core-модулей (реальные данные не трогаем) ──
_TEST_APPDATA = tempfile.mkdtemp(prefix="r39_appdata_")
os.environ["APPDATA"] = _TEST_APPDATA
_UPLOAD_DIR = tempfile.mkdtemp(prefix="r39_uploads_")
os.environ["FLET_UPLOAD_DIR"] = _UPLOAD_DIR
os.environ["PORAYONKA_LAZY_TAB_DIAG"] = "1"

import flet as ft                                            # noqa: E402
from page_stub import PageStub                               # noqa: E402
from r39_harness import (                                    # noqa: E402
    check, check_no_thread_errors, click as _click, find as _find,
    install_thread_guard, read_src, report, texts as _texts, walk,
)
from core.controls_data import (                             # noqa: E402
    get_controls_file, load_controls, load_settings, save_settings,
)
from core.controls_models import Control                     # noqa: E402
from core.controls_exporter import (                         # noqa: E402
    ControlsExcelExporter, import_from_excel, TABLE_HEADERS,
)
from ui.controls.controls_tab import create_controls_tab     # noqa: E402
from ui.lazy_tabs import LazyTabHost                         # noqa: E402

ROOT = _ROOT
MAIN_PY = os.path.join(ROOT, "main.py")
MAIN_WEB_PY = os.path.join(ROOT, "main_web.py")
START_BAT = os.path.join(ROOT, "start_web_win7.bat")
TILE_BG = "#2a3247"


def _seed_controls():
    """База: периодический контроль с end_date + разовый с end_date из Excel."""
    controls = [
        {
            "id": "per1",
            "incoming_number": "ВХСОП-455-2026",
            "receive_date": "2026-08-01",
            "initiator": "СУ",
            "content": "Ежемесячный контроль предоставления статистики",
            "executors": ["Чашин Эдуард Анатольевич"],
            "controller": "Потемкин С.А.",
            "control_type": "periodic", "period_days": 30,
            "due_date": "2026-08-10", "end_date": "2026-12-31",
            "done": False, "done_date": None, "comment": "постоянный",
            "tasks": [{"id": "t1", "title": "п.1 Доложить",
                       "assignees": ["Чашин Эдуард Анатольевич"],
                       "due_date": "2026-08-05", "is_done": False,
                       "done_date": None, "comment": ""}],
            "milestones": [{"id": "m1", "date": "2026-08-03",
                            "note": "точка1", "is_done": False}],
            "attachments": [], "archived": False, "archived_at": None,
            "archive_reason": "",
            "created_at": "2026-08-01T09:00:00",
            "updated_at": "2026-08-01T09:00:00",
        },
        {
            # Раунд 22: end_date РАЗОВОГО контроля = «срок разового контроля»
            # (колонка H Excel). НЕ должен стираться при сохранении карточки.
            "id": "once1",
            "incoming_number": "ЭКС-РАЗОВЫЙ-1",
            "receive_date": "2026-07-20",
            "initiator": "ГУК СК",
            "content": "Разовый контроль со сроком из Excel",
            "executors": ["Семисенко Иван Юрьевич"],
            "controller": "Потемкин С.А.",
            "control_type": "once", "period_days": 7,
            "due_date": "2026-08-10", "end_date": "2026-09-01",
            "done": False, "done_date": None, "comment": "",
            "tasks": [], "milestones": [], "attachments": [],
            "archived": False, "archived_at": None, "archive_reason": "",
            "created_at": "2026-07-20T10:00:00",
            "updated_at": "2026-07-20T10:00:00",
        },
    ]
    data = {"schema_version": 2, "last_saved": "2026-08-05T12:00:00",
            "controls": controls}
    with open(get_controls_file(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _settings_off():
    d = dict(load_settings())
    d["network_enabled"] = False
    save_settings(d)


def build(width=1280, height=860):
    page = PageStub(width=width, height=height)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        tab = create_controls_tab(page)
    return page, tab, buf.getvalue()


def _open_card_by_number(tab, number):
    """Открыть карточку контроля по входящему номеру (клик по строке)."""
    rows = [c for c in walk(tab) if isinstance(c, ft.Container)
            and getattr(c, "bgcolor", None) == TILE_BG
            and getattr(c, "on_click", None)]
    for r in rows:
        if any(number in t for t in _texts(r)):
            r.on_click(None)
            return True
    return False


def _end_field_of(tab):
    """(поле-текст конечной даты, крестик очистки) открытой карточки."""
    clears = [c for c in walk(tab) if isinstance(c, ft.IconButton)
              and getattr(c, "tooltip", None)
              and "Очистить конечную дату" in str(c.tooltip)]
    if not clears:
        return None, None
    btn = clears[0]
    # поле-текст — сосед по Row с крестиком
    for row in walk(tab):
        if isinstance(row, ft.Row) and btn in (row.controls or []):
            for ctl in row.controls:
                if isinstance(ctl, ft.Text):
                    return ctl, btn
    return None, btn


def _fire_picker(picker, ev):
    eh = getattr(picker, "on_result", None)
    if eh is None:
        return False
    if callable(eh) and not hasattr(eh, "_EventHandler__handlers"):
        eh(ev)
        return True
    hs = getattr(eh, "_EventHandler__handlers", {})
    for fn in hs.keys():
        fn(ev)
        return True
    return False


def _upload_handler_count(picker):
    eh = getattr(picker, "on_upload", None)
    if eh is None:
        return 0
    return len(getattr(eh, "_EventHandler__handlers", {}) or {})


def _fire_upload(picker, ev):
    eh = getattr(picker, "on_upload", None)
    if eh is None:
        return False
    hs = getattr(eh, "_EventHandler__handlers", {})
    n = 0
    for fn in hs.keys():
        fn(ev)
        n += 1
    return n > 0


class _UpEvent:
    def __init__(self, file_name, progress, error=None):
        self.file_name = file_name
        self.progress = progress
        self.error = error


class _ResEvent:
    """FilePickerResultEvent-подобное событие выбора файла."""
    def __init__(self, path=None, files=None):
        self.path = path
        self.files = files


def _F(name, path=None, size=100):
    return types.SimpleNamespace(name=name, path=path, size=size)


def _make_xlsx(path, rows):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["КОНТРОЛИ ОТДЕЛА КРИМИНАЛИСТИКИ"] + [None] * 9)
    ws.append(TABLE_HEADERS)
    for r in rows:
        ws.append(r)
    wb.save(path)
    return path



def test_end_date():
    print("\n=== 1. Конечная дата (очистка) ===")

    # 1.0 Контракт единого календаря не сломан и ВТОРОГО календаря нет.
    from ui.controls import russian_calendar as rc
    got = []
    fld = rc.create_russian_date_field(PageStub(), "2026-05-10",
                                       lambda iso: got.append(iso),
                                       hint="Дата")
    check("r39-1.0a: create_russian_date_field строится", fld is not None)
    clr = [c for c in walk(fld) if isinstance(c, ft.IconButton)
           and getattr(c, "tooltip", None) == "Очистить"]
    check("r39-1.0b: крестик «Очистить» в поле даты есть", bool(clr))
    if clr:
        clr[0].on_click(None)
    check("r39-1.0c: контракт on_change(Optional[str]) — очистка даёт None",
          got == [None], str(got))
    # «Очистить» внутри панели календаря — тот же контракт
    got2 = []
    fld2 = rc.create_russian_date_field(PageStub(), "2026-05-10",
                                        lambda iso: got2.append(iso))
    panel_clear = [c for c in walk(fld2) if isinstance(c, ft.TextButton)
                   and getattr(c, "text", None) == "Очистить"]
    if panel_clear:
        panel_clear[0].on_click(None)
    check("r39-1.0d: «Очистить» в панели календаря — тоже None",
          got2 == [None], str(got2))

    # 1.1 Открыть периодический контроль: крестик очистки конечной даты есть.
    _seed_controls()
    _settings_off()
    page, tab, _log = build()
    check("r39-1.1a: вкладка «Контроли» построена", tab is not None)
    opened = _open_card_by_number(tab, "ВХСОП-455-2026")
    check("r39-1.1b: карточка периодического контроля открылась", opened)
    end_txt, end_btn = _end_field_of(tab)
    check("r39-1.1c: ЯВНАЯ команда очистки конечной даты существует",
          end_btn is not None)
    check("r39-1.1d: у команды очистки понятный tooltip",
          end_btn is not None and "конечную дату" in str(end_btn.tooltip),
          str(getattr(end_btn, "tooltip", None)))
    check("r39-1.1e: крестик виден, пока дата задана",
          end_btn is not None and end_btn.visible is True)
    check("r39-1.1f: поле показывает исходную дату 31.12.2026",
          end_txt is not None and end_txt.value == "31.12.2026",
          str(getattr(end_txt, "value", None)))

    # 1.2 До очистки фиксируем то, что очистка НЕ должна трогать.
    before = {c.id: c for c in load_controls()}
    b_due = before["per1"].due_date
    b_per = before["per1"].period_days
    b_tasks = len(before["per1"].tasks)
    b_miles = len(before["per1"].milestones)

    # 1.3 Клик по крестику -> UI пустое состояние.
    end_btn.on_click(None)
    check("r39-1.3a: после очистки поле показывает пустое состояние «—»",
          end_txt.value == "—", str(end_txt.value))
    check("r39-1.3b: после очистки крестик скрыт", end_btn.visible is False)

    # 1.4 Очистка не меняет due_date / period_days / tasks / milestones.
    #     (проверяем по сохранённой модели — другой наблюдаемый путь)
    check("r39-1.4a: Сохранить карточку удалось", _click(tab, ft.ElevatedButton, text="Сохранить"))
    after = {c.id: c for c in load_controls()}
    a = after.get("per1")
    check("r39-1.4b: сохранение записало end_date=None",
          a is not None and a.end_date is None, str(getattr(a, "end_date", "MISSING")))
    check("r39-1.4c: due_date НЕ изменился",
          a is not None and a.due_date == b_due,
          f"{b_due} -> {getattr(a, 'due_date', None)}")
    check("r39-1.4d: period_days НЕ изменился",
          a is not None and a.period_days == b_per,
          f"{b_per} -> {getattr(a, 'period_days', None)}")
    check("r39-1.4e: tasks НЕ изменились",
          a is not None and len(a.tasks) == b_tasks,
          f"{b_tasks} -> {len(getattr(a, 'tasks', []) or [])}")
    check("r39-1.4f: milestones НЕ изменились",
          a is not None and len(a.milestones) == b_miles,
          f"{b_miles} -> {len(getattr(a, 'milestones', []) or [])}")

    # 1.5 Повторное открытие НЕ возвращает старую дату.
    _click(tab, ft.IconButton, tooltip="Закрыть")
    page2, tab2, _ = build()
    _open_card_by_number(tab2, "ВХСОП-455-2026")
    end_txt2, end_btn2 = _end_field_of(tab2)
    check("r39-1.5a: повторное открытие — дата осталась пустой",
          end_txt2 is not None and end_txt2.value == "—",
          str(getattr(end_txt2, "value", None)))
    check("r39-1.5b: крестик скрыт (даты нет)",
          end_btn2 is not None and end_btn2.visible is False)

    # 1.6 После очистки можно выбрать НОВУЮ дату и сохранить её.
    ok_cal = _open_cal_for_end(tab2)
    check("r39-1.6a: календарь конечной даты открывается", ok_cal)
    picked = _pick_calendar_day(tab2, 2027, 1, 15)
    check("r39-1.6b: дата выбрана в ЕДИНОМ глобальном календаре", picked)
    check("r39-1.6c: поле показывает новую дату 15.01.2027",
          end_txt2 is not None and end_txt2.value == "15.01.2027",
          str(getattr(end_txt2, "value", None)))
    check("r39-1.6d: крестик снова виден", end_btn2 is not None and end_btn2.visible is True)
    _click(tab2, ft.ElevatedButton, text="Сохранить")
    a2 = {c.id: c for c in load_controls()}.get("per1")
    check("r39-1.6e: новая конечная дата сохранена",
          a2 is not None and a2.end_date == "2027-01-15",
          str(getattr(a2, "end_date", None)))

    # 1.7 «Очистить» есть и ВНУТРИ единого календаря (can_clear).
    page3, tab3, _ = build()
    _open_card_by_number(tab3, "ВХСОП-455-2026")
    _open_cal_for_end(tab3)
    _g3 = _global_cal_root(tab3)
    cal_clear = [c for c in walk(_g3) if isinstance(c, ft.TextButton)
                 and getattr(c, "text", None) == "Очистить"
                 and getattr(c, "visible", None) is True]
    check("r39-1.7a: в календаре конечной даты видна команда «Очистить»",
          bool(cal_clear))
    if cal_clear:
        cal_clear[0].on_click(None)
    et3, _ = _end_field_of(tab3)
    check("r39-1.7b: «Очистить» в календаре обнулило поле",
          et3 is not None and et3.value == "—", str(getattr(et3, "value", None)))

    # 1.8 Второй независимый календарь НЕ создан: календарных панелей в
    #     карточке не больше, чем было до правки (одна глобальная).
    check("r39-1.8: глобальный календарь один (нет дубля)",
          _count_cal_panels(tab3) <= 1, str(_count_cal_panels(tab3)))

    # 1.9 У полей, которым очистка не разрешена, «Очистить» НЕ появляется.
    page4, tab4, _ = build()
    _open_card_by_number(tab4, "ВХСОП-455-2026")
    opened_due = _open_cal_for_due(tab4)
    check("r39-1.9a: календарь для «Срок» (due) открылся", opened_due)
    _g4 = _global_cal_root(tab4)
    due_clear = [c for c in walk(_g4) if isinstance(c, ft.TextButton)
                 and getattr(c, "text", None) == "Очистить"
                 and getattr(c, "visible", None) is True]
    check("r39-1.9b: у «Срок» (due) команды «Очистить» в календаре НЕТ "
          "(can_clear=False — семантика прочих полей не меняется)",
          not due_clear, str(len(due_clear)))

    # 1.10 Переход periodic -> one-time обнуляет скрытое значение end_date.
    page5, tab5, _ = build()
    _open_card_by_number(tab5, "ВХСОП-455-2026")
    et5, _ = _end_field_of(tab5)
    type_dd = None
    for d in walk(tab5):
        if isinstance(d, ft.Dropdown) and getattr(d, "hint_text", None) == "Тип":
            type_dd = d
            break
    check("r39-1.10a: дропдаун «Тип» найден", type_dd is not None)
    if type_dd is not None:
        type_dd.value = "once"
        type_dd.on_change(types.SimpleNamespace(control=type_dd))
        _click(tab5, ft.ElevatedButton, text="Сохранить")
        a5 = {c.id: c for c in load_controls()}.get("per1")
        check("r39-1.10b: periodic -> one-time обнулил end_date",
              a5 is not None and a5.end_date is None,
              str(getattr(a5, "end_date", "MISSING")))
        check("r39-1.10c: тип стал разовым",
              a5 is not None and a5.control_type == "once",
              str(getattr(a5, "control_type", None)))

    # 1.11 Раунд 22 НЕ откачен: end_date РАЗОВОГО контроля из Excel
    #      сохраняется при открытии+сохранении карточки без смены типа.
    _seed_controls()
    page6, tab6, _ = build()
    _open_card_by_number(tab6, "ЭКС-РАЗОВЫЙ-1")
    _click(tab6, ft.ElevatedButton, text="Сохранить")
    a6 = {c.id: c for c in load_controls()}.get("once1")
    check("r39-1.11: end_date разового контроля из Excel НЕ стёрт (раунд 22)",
          a6 is not None and a6.end_date == "2026-09-01",
          str(getattr(a6, "end_date", "MISSING")))

    # 1.12 Excel round-trip: заданная и пустая конечная дата.
    _seed_controls()
    ctrls = load_controls()
    xlsx = os.path.join(tempfile.mkdtemp(prefix="r39_xl_"), "rt39.xlsx")
    ControlsExcelExporter().export(ctrls, xlsx, 7, full=True)
    back, _stats = import_from_excel(xlsx, [])
    by_num = {c.incoming_number: c for c in back}
    p = by_num.get("ВХСОП-455-2026")
    o = by_num.get("ЭКС-РАЗОВЫЙ-1")
    check("r39-1.12a: Excel round-trip — заданная конечная дата сохранена",
          p is not None and p.end_date == "2026-12-31",
          str(getattr(p, "end_date", "MISSING")))
    check("r39-1.12b: Excel round-trip — разовый срок сохранён",
          o is not None and o.end_date == "2026-09-01",
          str(getattr(o, "end_date", "MISSING")))
    # теперь обнулим end_date периодического и прогоним round-trip ещё раз
    for c in ctrls:
        if c.id == "per1":
            c.end_date = None
    xlsx2 = os.path.join(tempfile.mkdtemp(prefix="r39_xl2_"), "rt39b.xlsx")
    ControlsExcelExporter().export(ctrls, xlsx2, 7, full=True)
    back2 = {c.incoming_number: c
             for c in import_from_excel(xlsx2, [])[0]}
    p2 = back2.get("ВХСОП-455-2026")
    check("r39-1.12c: Excel round-trip — ПУСТАЯ конечная дата остаётся пустой",
          p2 is not None and not p2.end_date,
          str(getattr(p2, "end_date", "MISSING")))


def _global_cal_root(tab):
    """Единственный ГЛОБАЛЬНЫЙ календарь вкладки (Container 300x340)."""
    for c in walk(tab):
        if isinstance(c, ft.Container) and getattr(c, "width", None) == 300 \
                and getattr(c, "height", None) == 340:
            return c
    return None


def _count_cal_panels(tab):
    """Сколько глобальных календарей в дереве (должен быть ровно один —
    второй независимый календарь для конечной даты создавать запрещено)."""
    return sum(1 for c in walk(tab)
               if isinstance(c, ft.Container)
               and getattr(c, "width", None) == 300
               and getattr(c, "height", None) == 340)


def _open_cal_for_end(tab):
    """Открыть глобальный календарь кликом по полю конечной даты."""
    for c in walk(tab):
        if isinstance(c, ft.Container) and getattr(c, "on_click", None):
            kids = c.content.controls if isinstance(c.content, ft.Row) else None
            if not kids:
                continue
            has_clear = any(isinstance(k, ft.IconButton)
                            and getattr(k, "tooltip", None)
                            and "Очистить конечную дату" in str(k.tooltip)
                            for k in kids)
            if has_clear:
                c.on_click(None)
                return True
    return False


def _open_cal_for_due(tab):
    """Открыть глобальный календарь для «Срок» (due).

    due_box — единственное поле даты шириной 200 (receive=160, end=160)."""
    for c in walk(tab):
        if isinstance(c, ft.Container) and getattr(c, "on_click", None) \
                and getattr(c, "width", None) == 200 \
                and isinstance(c.content, ft.Row):
            c.on_click(None)
            return True
    return False


def _pick_calendar_day(tab, year, month, day):
    """В открытом глобальном календаре перейти на year/month и кликнуть day."""
    _groot = _global_cal_root(tab)
    hdr = [c for c in walk(_groot if _groot is not None else tab)
           if isinstance(c, ft.Text)
           and getattr(c, "weight", None) == ft.FontWeight.W_700
           and getattr(c, "value", None)
           and any(m in str(c.value) for m in
                   ("Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"))]
    if not hdr:
        return False
    MONTHS = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
              "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    root = _global_cal_root(tab)
    if root is None:
        return False
    txt = str(hdr[0].value)
    try:
        cur_m = MONTHS.index(txt.split()[0]) + 1
        cur_y = int(txt.split()[1])
    except Exception:
        return False
    # кнопки навигации — Chevron LEFT/RIGHT ВНУТРИ глобального календаря
    navs = [c for c in walk(root) if isinstance(c, ft.IconButton)
            and getattr(c, "icon", None) in (ft.icons.CHEVRON_LEFT,
                                             ft.icons.CHEVRON_RIGHT)]
    left = [c for c in navs if c.icon == ft.icons.CHEVRON_LEFT]
    right = [c for c in navs if c.icon == ft.icons.CHEVRON_RIGHT]
    guard = 0
    while (cur_y, cur_m) != (year, month) and guard < 400:
        guard += 1
        if (cur_y, cur_m) < (year, month):
            right[0].on_click(None)
            cur_m += 1
            if cur_m > 12:
                cur_m = 1
                cur_y += 1
        else:
            left[0].on_click(None)
            cur_m -= 1
            if cur_m < 1:
                cur_m = 12
                cur_y -= 1
    # клик по дню: ячейка Container с Text(str(day)) ВНУТРИ глоб. календаря
    for c in walk(root):
        if isinstance(c, ft.Container) and getattr(c, "on_click", None) \
                and isinstance(c.content, ft.Text) \
                and str(c.content.value) == str(day):
            c.on_click(None)
            return True
    return False



def _global_cal_root(tab):
    """Единственный ГЛОБАЛЬНЫЙ календарь вкладки (Container 300x340)."""
    for c in walk(tab):
        if isinstance(c, ft.Container) and getattr(c, "width", None) == 300 \
                and getattr(c, "height", None) == 340:
            return c
    return None


def _count_cal_panels(tab):
    """Сколько глобальных календарей в дереве (должен быть ровно один —
    второй независимый календарь для конечной даты создавать запрещено)."""
    return sum(1 for c in walk(tab)
               if isinstance(c, ft.Container)
               and getattr(c, "width", None) == 300
               and getattr(c, "height", None) == 340)


def _open_cal_for_end(tab):
    """Открыть глобальный календарь кликом по полю конечной даты."""
    for c in walk(tab):
        if isinstance(c, ft.Container) and getattr(c, "on_click", None):
            kids = c.content.controls if isinstance(c.content, ft.Row) else None
            if not kids:
                continue
            has_clear = any(isinstance(k, ft.IconButton)
                            and getattr(k, "tooltip", None)
                            and "Очистить конечную дату" in str(k.tooltip)
                            for k in kids)
            if has_clear:
                c.on_click(None)
                return True
    return False


def _open_cal_for_due(tab):
    """Открыть глобальный календарь для «Срок» (due).

    due_box — единственное поле даты шириной 200 (receive=160, end=160)."""
    for c in walk(tab):
        if isinstance(c, ft.Container) and getattr(c, "on_click", None) \
                and getattr(c, "width", None) == 200 \
                and isinstance(c.content, ft.Row):
            c.on_click(None)
            return True
    return False


def _pick_calendar_day(tab, year, month, day):
    """В открытом глобальном календаре перейти на year/month и кликнуть day."""
    _groot = _global_cal_root(tab)
    hdr = [c for c in walk(_groot if _groot is not None else tab)
           if isinstance(c, ft.Text)
           and getattr(c, "weight", None) == ft.FontWeight.W_700
           and getattr(c, "value", None)
           and any(m in str(c.value) for m in
                   ("Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"))]
    if not hdr:
        return False
    MONTHS = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
              "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    root = _global_cal_root(tab)
    if root is None:
        return False
    txt = str(hdr[0].value)
    try:
        cur_m = MONTHS.index(txt.split()[0]) + 1
        cur_y = int(txt.split()[1])
    except Exception:
        return False
    # кнопки навигации — Chevron LEFT/RIGHT ВНУТРИ глобального календаря
    navs = [c for c in walk(root) if isinstance(c, ft.IconButton)
            and getattr(c, "icon", None) in (ft.icons.CHEVRON_LEFT,
                                             ft.icons.CHEVRON_RIGHT)]
    left = [c for c in navs if c.icon == ft.icons.CHEVRON_LEFT]
    right = [c for c in navs if c.icon == ft.icons.CHEVRON_RIGHT]
    guard = 0
    while (cur_y, cur_m) != (year, month) and guard < 400:
        guard += 1
        if (cur_y, cur_m) < (year, month):
            right[0].on_click(None)
            cur_m += 1
            if cur_m > 12:
                cur_m = 1
                cur_y += 1
        else:
            left[0].on_click(None)
            cur_m -= 1
            if cur_m < 1:
                cur_m = 12
                cur_y -= 1
    # клик по дню: ячейка Container с Text(str(day)) ВНУТРИ глоб. календаря
    for c in walk(root):
        if isinstance(c, ft.Container) and getattr(c, "on_click", None) \
                and isinstance(c.content, ft.Text) \
                and str(c.content.value) == str(day):
            c.on_click(None)
            return True
    return False




def main():
    install_thread_guard()
    for fn in (test_end_date,):
        print("\n" + "=" * 70)
        try:
            fn()
        except Exception:
            import traceback
            check(fn.__name__ + " [exception]", False)
            traceback.print_exc()
    check_no_thread_errors('Раунд 39 (задача 1): конечная дата — очи')
    sys.exit(report('Раунд 39 (задача 1): конечная дата — очистка, persistence, E'))


if __name__ == "__main__":
    main()

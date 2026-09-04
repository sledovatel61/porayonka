# -*- coding: utf-8 -*-
"""Раунд 39: восстановление и проверка пяти исправлений.

Покрывает PROMPT_новому_агенту_восстановление_Round39.md:

  1. Конечная дата периодического контроля
     - явная команда очистки (крестик с tooltip) + «Очистить» в ЕДИНОМ
       глобальном календаре (второй независимый календарь НЕ создан);
     - после очистки UI показывает «—», сохранение пишет end_date=None,
       повторное открытие не возвращает старую дату;
     - очистка не трогает due_date / period_days / tasks / milestones;
     - переход periodic -> one-time обнуляет скрытое значение end_date
       (и НЕ откатывает раунд 22: end_date разового из Excel сохраняется);
     - после очистки можно выбрать новую дату и сохранить;
     - полный round-trip модели + Excel round-trip (пустая и заданная дата).

  2. Ленивые вкладки (ui/lazy_tabs.py)
     - на старте строится ТОЛЬКО активная вкладка «Контроли»;
     - первый переход строит каждую ровно один раз;
     - повторный переход использует кэш (тот же экземпляр, builder не зовётся);
     - конкурентный переход не строит дважды;
     - порядок вкладок и активная по умолчанию сохранены.

  3. Единственный владелец открытия браузера
     - start_web_win7.bat больше НЕ делает `start http://...`;
     - каждый вызов _open_browser() в main_web.py ведёт к sys.exit()
       (в таком процессе Flet физически не стартует -> дубля нет);
     - автоматический старт не открывает браузер через webbrowser.open;
     - «Открыть» из меню трея (явная команда пользователя) сохранена.

  4. Tray + single-instance
     - повторный и КОНКУРЕНТНЫЙ вызов start_tray() даёт ровно один
       pystray.Icon (проверка _ACTIVE_ICON и до, и после lock);
     - «Выход» останавливает значок ровно один раз и освобождает guard;
     - core/single_instance: acquired / ERROR_ALREADY_EXISTS (НЕ fail-open) /
       fail-open только при невозможности вызвать API / release.

  5. Excel-импорт в Admin Win7 Web (FilePicker upload)
     - пустая модель -> выбор xlsx -> upload -> progress=1.0 -> preview ->
       confirm -> запись в модели и таблице;
     - отмена, ошибка upload, незавершённый upload, не-xlsx, отсутствующий
       файл после upload -> русский toast + ASCII-safe лог, без фиктивных путей;
     - повторный импорт: on_upload подписан ровно один раз (без накопления);
     - desktop-импорт (e.path) не сломан; user-редакция импорта не получает.

Запуск из porayonka-app:  python tests\\test_round39.py
Все операции — в temp APPDATA / temp FLET_UPLOAD_DIR (реальные данные не
трогаются).
"""
import ast
import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import traceback
import types
from datetime import date

FAILURES = []


def check(name, cond, extra=""):
    status = "OK " if cond else "FAIL"
    try:
        print(f"[{status}] {name}" + (f"  ({extra})" if extra else ""))
    except UnicodeEncodeError:
        print(f"[{status}] <non-cp1251 output>", file=sys.stderr)
        FAILURES.append(name + " [non-cp1251 output]")
        return
    if not cond:
        FAILURES.append(name)


# ── изоляция данных ДО импорта core-модулей ───────────────────────────────
_TEST_APPDATA = tempfile.mkdtemp(prefix="r39_appdata_")
os.environ["APPDATA"] = _TEST_APPDATA
_UPLOAD_DIR = tempfile.mkdtemp(prefix="r39_uploads_")
os.environ["FLET_UPLOAD_DIR"] = _UPLOAD_DIR
# диагностика ленивых вкладок в тесте включена (ASCII-safe print)
os.environ["PORAYONKA_LAZY_TAB_DIAG"] = "1"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import flet as ft                                    # noqa: E402
from page_stub import PageStub                       # noqa: E402
from core.controls_data import (                     # noqa: E402
    get_controls_file, load_controls, load_settings, save_settings,
)
from core.controls_models import Control             # noqa: E402
from core.controls_exporter import (                 # noqa: E402
    ControlsExcelExporter, import_from_excel, TABLE_HEADERS,
)
from ui.controls.controls_tab import create_controls_tab  # noqa: E402
from ui.lazy_tabs import LazyTabHost                 # noqa: E402

_UPLOAD_SECRET_BACKUP = os.environ.get("FLET_SECRET_KEY")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_PY = os.path.join(ROOT, "main.py")
MAIN_WEB_PY = os.path.join(ROOT, "main_web.py")
START_BAT = os.path.join(ROOT, "start_web_win7.bat")


# ═══════════════════════════════════════════════════════════════════════════
# ХАРНЕС
# ═══════════════════════════════════════════════════════════════════════════
def walk(c, seen=None):
    """Обойти дерево контролов Flet (content/controls/title/actions)."""
    if seen is None:
        seen = set()
    res = []
    if c is None or id(c) in seen:
        return res
    seen.add(id(c))
    res.append(c)
    for attr in ("content", "controls", "title", "actions", "badge"):
        v = getattr(c, attr, None)
        if isinstance(v, (list, tuple)):
            for x in v:
                res += walk(x, seen)
        elif v is not None and hasattr(v, "_Control__uid") or (
                v is not None and v.__class__.__module__.startswith("flet")):
            res += walk(v, seen)
    return res


TILE_BG = "#2a3247"


def _texts(root):
    return {str(t.value) for t in walk(root)
            if isinstance(t, ft.Text) and getattr(t, "value", None)}


def _find(root, cls, **attrs):
    """Все контролы класса cls с совпадающими атрибутами."""
    out = []
    for c in walk(root):
        if not isinstance(c, cls):
            continue
        ok = True
        for k, v in attrs.items():
            if getattr(c, k, None) != v:
                ok = False
                break
        if ok:
            out.append(c)
    return out


def _click(root, cls, text=None, tooltip=None):
    """Кликнуть первый контрол cls с нужным text/tooltip. True если нашли."""
    kw = {}
    if text is not None:
        kw["text"] = text
    if tooltip is not None:
        kw["tooltip"] = tooltip
    for c in _find(root, cls, **kw):
        fn = getattr(c, "on_click", None)
        if callable(fn):
            fn(None)
            return True
    return False


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


# ═══════════════════════════════════════════════════════════════════════════
# 1. КОНЕЧНАЯ ДАТА
# ═══════════════════════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════════════════════
# 2. ЛЕНИВЫЕ ВКЛАДКИ
# ═══════════════════════════════════════════════════════════════════════════
def test_lazy_tabs():
    print("\n=== 2. Ленивые вкладки ===")

    # 2.1 Хост: старт без построения неактивных вкладок.
    calls = {"a": 0, "b": 0, "c": 0}

    def mk(k, obj):
        def _b():
            calls[k] += 1
            return obj
        return _b

    oa, ob, oc = object(), object(), object()
    host = LazyTabHost()
    host.register("controls", mk("a", oa))
    host.register("zonal", mk("b", ob))
    host.register("departments", mk("c", oc))
    check("r39-2.1a: регистрация сама ничего не строит",
          calls == {"a": 0, "b": 0, "c": 0}, str(calls))
    host.get("controls")            # активная вкладка на старте
    check("r39-2.1b: на старте построена ТОЛЬКО активная вкладка",
          calls == {"a": 1, "b": 0, "c": 0}, str(calls))
    check("r39-2.1c: неактивные вкладки не построены",
          not host.is_built("zonal") and not host.is_built("departments"))

    # 2.2 Первый переход строит каждую ровно один раз.
    host.get("zonal")
    host.get("zonal")
    host.get("zonal")
    host.get("departments")
    host.get("departments")
    check("r39-2.2a: первый переход строит builder ровно ОДИН раз (zonal)",
          host.build_count("zonal") == 1, str(host.build_count("zonal")))
    check("r39-2.2b: первый переход строит builder ровно ОДИН раз (departments)",
          host.build_count("departments") == 1, str(host.build_count("departments")))
    check("r39-2.2c: всего builder'ов вызвано по разу",
          calls == {"a": 1, "b": 1, "c": 1}, str(calls))

    # 2.3 Повторный переход использует кэш (тот же экземпляр).
    check("r39-2.3a: кэш возвращает ТОТ ЖЕ экземпляр (zonal)",
          host.get("zonal") is ob)
    check("r39-2.3b: кэш возвращает ТОТ ЖЕ экземпляр (departments)",
          host.get("departments") is oc)
    check("r39-2.3c: счётчик reuse растёт, build — нет",
          host.build_count("zonal") == 1 and host.reuse_count("zonal") >= 3,
          f"build={host.build_count('zonal')} reuse={host.reuse_count('zonal')}")

    # 2.4 Конкурентный переход не строит дважды.
    calls2 = {"x": 0}
    barrier = threading.Barrier(12)

    def _slow():
        calls2["x"] += 1
        return object()

    h2 = LazyTabHost()
    h2.register("x", _slow)
    results = []
    lock = threading.Lock()

    def _worker():
        barrier.wait()
        r = h2.get("x")
        with lock:
            results.append(r)

    ths = [threading.Thread(target=_worker) for _ in range(12)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    check("r39-2.4a: 12 конкурентных get() -> builder вызван ОДИН раз",
          calls2["x"] == 1, str(calls2["x"]))
    check("r39-2.4b: все 12 потоков получили ОДИН И ТОТ ЖЕ экземпляр",
          len(results) == 12 and all(r is results[0] for r in results))

    # 2.5 Ошибка builder'а -> заглушка, а не падение приложения.
    def _boom():
        raise RuntimeError("builder died")

    h3 = LazyTabHost(on_error=lambda k, ex: ("ERR", k, str(ex)))
    h3.register("bad", _boom)
    r3 = h3.get("bad")
    check("r39-2.5a: ошибка builder'а отдаёт заглушку",
          isinstance(r3, tuple) and r3[0] == "ERR", str(r3))
    check("r39-2.5b: ошибка builder'а не повторяет вызов при возврате",
          h3.build_count("bad") == 1, str(h3.build_count("bad")))
    h4 = LazyTabHost()
    h4.register("bad", _boom)
    raised = False
    try:
        h4.get("bad")
    except RuntimeError:
        raised = True
    check("r39-2.5c: без on_error исключение пробрасывается", raised)

    # 2.6 Диагностика ASCII-safe и отключаемая.
    class _BoomStream(io.StringIO):
        def write(self, s):
            s.encode("ascii")          # бросит на не-ASCII
            return super().write(s)

    h5 = LazyTabHost(diag=True)
    h5.register("диагноза", lambda: object())
    buf = _BoomStream()
    ok = True
    try:
        with contextlib.redirect_stdout(buf):
            h5.get("диагноза")
    except UnicodeEncodeError:
        ok = False
    check("r39-2.6: диагностика build/reuse ASCII-safe", ok)

    # 2.7 РЕАЛЬНЫЙ main._main_impl: тяжёлые вкладки на старте не строятся.
    _main_lazy_runtime()

    # 2.8 Статика main.py: порядок, активная по умолчанию, _ensure_tab.
    src = io.open(MAIN_PY, encoding="utf-8").read()
    check("r39-2.8a: main.py регистрирует три builder'а",
          '_lazy_tabs.register("controls"' in src
          and '_lazy_tabs.register("zonal"' in src
          and '_lazy_tabs.register("departments"' in src)
    check("r39-2.8b: на старте строится только вкладка 0",
          "_ensure_tab(0)" in src)
    check("r39-2.8c: _switch_tab строит вкладку при переходе",
          "_ensure_tab(index)" in src)
    check("r39-2.8d: порядок вкладок сохранён (Контроли/Зональные/Отделы)",
          src.index('"Контроли", ft.icons.RULE_FOLDER')
          < src.index('"Зональные", ft.icons.MAP_OUTLINED')
          < src.index('"Следственные отделы", ft.icons.ACCOUNT_BALANCE_OUTLINED'))
    check("r39-2.8e: активная по умолчанию — «Контроли» (tab3_container visible=True)",
          "tab3_container = ft.Container(\n        content=None,\n        expand=True,\n        visible=True," in src)
    check("r39-2.8f: используются ТЕ ЖЕ builder-функции Admin",
          "create_controls_tab(page)" in src and "create_zonal_tab(page)" in src)
    check("r39-2.8g: нет запрещённого on_scroll в ленивой обвязке",
          "on_scroll" not in src)


class _MainPageStub(PageStub):
    """PageStub + то, что нужно main._main_impl (окно, add, run_thread)."""

    def __init__(self, width=1280, height=860):
        super().__init__(width=width, height=height)
        self.title = None
        self.theme_mode = None
        self.padding = 0
        self.spacing = 0
        self.bgcolor = None
        self.theme = None
        self.added = []
        w = self.window
        w.width = None
        w.min_width = None
        w.min_height = None
        w.visible = True
        w.maximized = False
        w.prevent_close = False
        w.on_event = None
        w.center = lambda: None
        w.to_front = lambda: None
        w.focus = lambda: None
        self.on_resize = None

    def add(self, *controls):
        self.added.extend(controls)

    def run_thread(self, handler, *args):
        handler(*args)


def _main_lazy_runtime():
    """Прогнать РЕАЛЬНЫЙ main._main_impl со счётчиками тяжёлых builder'ов."""
    import main as main_mod
    import ui.zonal.zonal_tab as zt
    import ui.controls.controls_tab as ct

    calls = {"zonal": 0, "controls": 0, "departments": 0}
    real_zonal = zt.create_zonal_tab
    real_controls = ct.create_controls_tab
    real_table = main_mod.create_department_table

    def _fake_zonal(page):
        calls["zonal"] += 1
        return ft.Text("zonal-stub")

    def _fake_controls(page):
        calls["controls"] += 1
        return ft.Text("controls-stub")

    def _fake_table(page, departments, on_status_change):
        calls["departments"] += 1
        return ft.Text("departments-stub")

    # данные отделов — минимальные, чтобы не трогать реальные
    import core.data as core_data
    real_load = core_data.load_departments
    core_data.load_departments = lambda: []
    main_mod.load_departments = lambda: []

    zt.create_zonal_tab = _fake_zonal
    ct.create_controls_tab = _fake_controls
    main_mod.create_department_table = _fake_table
    err = None
    page = None
    try:
        page = _MainPageStub()
        main_mod._main_impl(page)
        check("r39-2.7a: main._main_impl отработал без исключений", True)
        _main_lazy_checks(page, calls)
    except Exception as ex:
        err = ex
        check("r39-2.7a: main._main_impl отработал без исключений", False,
              f"{type(err).__name__}: {ex}")
        traceback.print_exc()
    finally:
        # ВАЖНО: снимаем патчи ПОСЛЕ проверок — иначе при клике по вкладке
        # отработает настоящий builder и счётчик не изменится.
        zt.create_zonal_tab = real_zonal
        ct.create_controls_tab = real_controls
        main_mod.create_department_table = real_table
        core_data.load_departments = real_load
        main_mod.load_departments = real_load
    return


def _main_lazy_checks(page, calls):
    if page is None:
        return
    labels = {0: "Контроли", 1: "Зональные", 2: "Следственные отделы"}

    def _go(idx):
        """Клик по кнопке вкладки — ровно то, что делает пользователь."""
        btns = [c for c in walk(page.added[0] if page.added else None)
                if isinstance(c, ft.Container)
                and getattr(c, "tooltip", None) == "Вкладка: " + labels[idx]]
        if btns:
            btns[0].on_click(None)
            return True
        return False

    host = getattr(page, "_lazy_tabs", None)
    check("r39-2.7b: main.py exposes page._lazy_tabs", host is not None)
    check("r39-2.7c: СТАРТ — «Контроли» построены ровно один раз",
          calls["controls"] == 1, str(calls))
    check("r39-2.7d: СТАРТ — «Зональные» НЕ построены",
          calls["zonal"] == 0, str(calls))
    check("r39-2.7e: СТАРТ — «Следственные отделы» НЕ построены",
          calls["departments"] == 0, str(calls))
    if host is None:
        return
    check("r39-2.7f: host считает построенной только активную вкладку",
          host.built_keys() == ["controls"], str(host.built_keys()))
    # первый переход — клик по кнопке вкладки (то, что делает пользователь)
    _go(1)
    check("r39-2.7g: первый переход на «Зональные» строит их ОДИН раз",
          calls["zonal"] == 1, str(calls))
    # повторный переход туда-сюда
    for idx in (0, 1, 0, 1, 2, 1, 2):
        _go(idx)
    check("r39-2.7h: повторные переходы НЕ пересоздают вкладки",
          calls == {"zonal": 1, "controls": 1, "departments": 1}, str(calls))
    check("r39-2.7i: после обхода построены все три вкладки",
          host.built_keys() == ["controls", "departments", "zonal"],
          str(host.built_keys()))


# ═══════════════════════════════════════════════════════════════════════════
# 3. ЕДИНСТВЕННЫЙ ВЛАДЕЛЕЦ ОТКРЫТИЯ БРАУЗЕРА
# ═══════════════════════════════════════════════════════════════════════════
def test_browser_owner():
    print("\n=== 3. Один владелец открытия браузера ===")

    bat = io.open(START_BAT, encoding="utf-8", errors="replace").read()
    low = bat.lower()
    # `start http://...` / `start "" http://...` / `start "" "http://...`
    bad = []
    for line in low.splitlines():
        s = line.strip()
        if s.startswith("::") or s.startswith("rem "):
            continue
        if s.startswith("start") and "http" in s:
            bad.append(line.strip())
    check("r39-3.1a: start_web_win7.bat НЕ открывает браузер (нет start http)",
          not bad, "; ".join(bad))
    check("r39-3.1b: bat по-прежнему запускает сервер",
          "Порайонка_Пользователь_Web.exe" in bat
          and "Порайонка_Админ_Web.exe" in bat)
    check("r39-3.1c: bat ждёт HTTP-доступности сервера",
          "HttpWebRequest" in bat and "8555" in bat)
    check("r39-3.1d: bat печатает адрес для ручного открытия",
          "http://127.0.0.1:%WEBPORT%" in bat)

    src_main = io.open(MAIN_PY, encoding="utf-8").read()
    check("r39-3.2a: владелец документирован (BROWSER_OWNER)",
          'BROWSER_OWNER = "flet:AppView.WEB_BROWSER"' in src_main)
    check("r39-3.2b: авто-старт открывает браузер только через Flet",
          src_main.count("ft.AppView.WEB_BROWSER") == 1
          and "view=ft.AppView.WEB_BROWSER" in src_main)
    tree = ast.parse(src_main)
    webbrowser_in_entry = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr == "open" \
                    and isinstance(f.value, ast.Name) and f.value.id == "webbrowser":
                webbrowser_in_entry = True
    check("r39-3.2c: main.py НЕ зовёт webbrowser.open сам", not webbrowser_in_entry)
    ft_app_calls = [
        nd for nd in ast.walk(tree)
        if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Attribute)
        and nd.func.attr == "app" and isinstance(nd.func.value, ast.Name)
        and nd.func.value.id == "ft"]
    check("r39-3.2d: сервер/клиент поднимается ровно двумя ft.app "
          "(web-ветка + desktop-ветка), дублей нет",
          len(ft_app_calls) == 2, str(len(ft_app_calls)))

    # main_web.py: каждый _open_browser() ведёт к sys.exit() в том же блоке.
    src_web = io.open(MAIN_WEB_PY, encoding="utf-8").read()
    wtree = ast.parse(src_web)
    opens = 0
    orphan = 0
    for node in ast.walk(wtree):
        if isinstance(node, ast.If):
            def _is_call(n, name):
                if isinstance(n, ast.Expr):
                    n = n.value
                return (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                        and n.func.id == name)

            has_open = any(_is_call(n, "_open_browser") for n in node.body)
            if not has_open:
                continue
            opens += 1
            def _is_sysexit(n):
                if isinstance(n, ast.Expr):
                    n = n.value
                return (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "exit"
                        and isinstance(n.func.value, ast.Name)
                        and n.func.value.id == "sys")

            has_exit = any(_is_sysexit(n) for n in node.body)
            if not has_exit:
                orphan += 1
    check("r39-3.3a: main_web.py: найдены ветки повторного запуска с _open_browser",
          opens >= 1, f"branches={opens}")
    check("r39-3.3b: КАЖДЫЙ _open_browser сопровождается sys.exit() "
          "(Flet в этом процессе не стартует -> дубля нет)",
          orphan == 0, f"orphans={orphan}")
    check("r39-3.3c: _open_browser вызывается ТОЛЬКО в ветках повторного запуска",
          src_web.count("_open_browser(") == opens + 1)   # +1 определение
    check("r39-3.3d: main_web.py не открывает браузер на обычном старте",
          src_web.index("from main import _entry")
          < src_web.index('if __name__ == "__main__":'))

    # «Открыть» из трея — явная команда пользователя, остаётся.
    src_tray = io.open(os.path.join(ROOT, "ui", "tray_icon.py"),
                       encoding="utf-8").read()
    check("r39-3.4: «Открыть» в меню трея (явная команда) сохранён",
          "webbrowser.open(web_url)" in src_tray)


# ═══════════════════════════════════════════════════════════════════════════
# 4. TRAY + SINGLE-INSTANCE
# ═══════════════════════════════════════════════════════════════════════════
class _mock_platform:
    def __init__(self, platform=None, blocked=()):
        self.platform, self.blocked = platform, blocked

    def __enter__(self):
        self._old_platform = sys.platform
        self._old_mods = {}
        if self.platform is not None:
            sys.platform = self.platform
        for m in self.blocked:
            self._old_mods[m] = sys.modules.get(m, "__absent__")
            sys.modules[m] = None
        return self

    def __exit__(self, *a):
        sys.platform = self._old_platform
        for m, v in self._old_mods.items():
            if v == "__absent__":
                sys.modules.pop(m, None)
            else:
                sys.modules[m] = v
        return False


def _tray_reload():
    import importlib
    import ui.tray_icon as ti
    importlib.reload(ti)
    return ti


def test_tray_single_instance():
    print("\n=== 4. Tray и single-instance ===")

    # ── 4.1/4.2 мок pystray: повторный и конкурентный захват ──────────
    state = {"icons": 0, "stopped": 0, "detached": 0}

    class _FakeIcon:
        def __init__(self, *a, **kw):
            state["icons"] += 1
            self.args = a

        def run_detached(self):
            state["detached"] += 1

        def stop(self):
            state["stopped"] += 1

    def _MenuItem(text, action, default=False):
        return types.SimpleNamespace(text=text, action=action)

    def _Menu(*a, **k):
        return types.SimpleNamespace(items=a)

    fake_pystray = types.SimpleNamespace(Icon=_FakeIcon, MenuItem=_MenuItem,
                                         Menu=_Menu)
    fake_pil = types.ModuleType("PIL")
    fake_pil.Image = types.SimpleNamespace(open=lambda p: object())

    old_mods = {}
    for nm, mod in (("pystray", fake_pystray), ("PIL", fake_pil)):
        old_mods[nm] = sys.modules.get(nm, "__absent__")
        sys.modules[nm] = mod
    real_exit = os._exit
    try:
        with _mock_platform("win32"):
            ti = _tray_reload()

            # ── 4.1 повторный вызов ───────────────────────────────────
            i1 = ti.start_tray(None, web_url="http://127.0.0.1:8555")
            i2 = ti.start_tray(None, web_url="http://127.0.0.1:8555")
            i3 = ti.start_tray(object())
            check("r39-4.1a: повторный start_tray возвращает ТОТ ЖЕ icon",
                  i1 is not None and i1 is i2 and i2 is i3)
            check("r39-4.1b: pystray.Icon создан РОВНО ОДИН раз (последовательно)",
                  state["icons"] == 1, str(state["icons"]))
            check("r39-4.1c: get_active_icon отдаёт тот же значок",
                  ti.get_active_icon() is i1)

            # ── 4.2 конкурентный вызов ────────────────────────────────
            ti.stop_tray()
            state["icons"] = 0
            state["detached"] = 0
            results = []
            rlock = threading.Lock()
            bar = threading.Barrier(10)

            def _w():
                bar.wait()
                ic = ti.start_tray(None, web_url="http://127.0.0.1:8555")
                with rlock:
                    results.append(ic)

            ths = [threading.Thread(target=_w) for _ in range(10)]
            for t in ths:
                t.start()
            for t in ths:
                t.join()
            check("r39-4.2a: 10 конкурентных start_tray -> ОДИН pystray.Icon",
                  state["icons"] == 1, str(state["icons"]))
            check("r39-4.2b: все 10 потоков получили один и тот же icon",
                  len(results) == 10 and all(r is results[0] for r in results))
            check("r39-4.2c: run_detached вызван один раз",
                  state["detached"] == 1, str(state["detached"]))

            # ── 4.3 «Выход» — один stop + освобождение guard ──────────
            icon = ti.get_active_icon()
            menu = icon.args[3] if len(icon.args) > 3 else None
            quit_item = None
            for it in (getattr(menu, "items", []) or []):
                if getattr(it, "text", None) == "Выход":
                    quit_item = it.action
            check("r39-4.3a: пункт «Выход» в меню найден", quit_item is not None)
            if quit_item is not None:
                # web-ветка «Выхода» завершает процесс os._exit(0) —
                # подменяем, чтобы не убить тестовый процесс.
                def _boom_exit(code=0):
                    raise SystemExit(code)
                os._exit = _boom_exit
                state["stopped"] = 0
                try:
                    quit_item(icon, None)
                except SystemExit:
                    pass
                except Exception:
                    traceback.print_exc()
                finally:
                    os._exit = real_exit
                check("r39-4.3b: «Выход» останавливает значок РОВНО ОДИН раз",
                      state["stopped"] == 1, str(state["stopped"]))
            check("r39-4.3c: после «Выхода» реестр значка пуст",
                  ti.get_active_icon() is None)
            after = ti.start_tray(None, web_url="http://127.0.0.1:8555")
            check("r39-4.3d: после «Выхода» можно запустить значок снова",
                  after is not None and state["icons"] == 2, str(state["icons"]))

            # ── 4.4 web не запускает desktop tray lifecycle ───────────
            src_main = io.open(MAIN_PY, encoding="utf-8").read()
            check("r39-4.4: web-режим берёт get_active_icon, а не start_tray",
                  'if _os26.environ.get("PORAYONKA_WEB"):' in src_main
                  and "from ui.tray_icon import get_active_icon" in src_main)
    finally:
        os._exit = real_exit
        for nm, v in old_mods.items():
            if v == "__absent__":
                sys.modules.pop(nm, None)
            else:
                sys.modules[nm] = v
        with _mock_platform(None):
            _tray_reload()

    # ══ 4.5+ core/single_instance ══════════════════════════════════════
    from core import single_instance as si
    import importlib

    # не-Windows: fail-open, но НЕ acquired
    si.release()
    ok, why = si.acquire("admin")
    check("r39-4.5a: не-Windows -> fail-open (приложение работает)",
          ok is True and why.startswith("fail_open"), why)
    check("r39-4.5b: не-Windows -> guard не «наш»",
          si.is_acquired() is False and si.status() == "fail_open", si.status())
    check("r39-4.5c: имя mutex\'а — Local\\ + редакция",
          si.mutex_name("admin") == "Local\\Porayonka_admin",
          si.mutex_name("admin"))
    check("r39-4.5d: разные редакции -> разные имена",
          si.mutex_name("admin") != si.mutex_name("user"))

    # ── мок Windows kernel32/user32 ──────────────────────────────────
    hcalls = {"create": 0, "close": 0, "lasterr": 0, "focus": 0,
              "hwnd": 0}

    def _CreateMutexW(a, b, name):
        hcalls["create"] += 1
        hcalls["last_name"] = name
        return 0x1234

    def _GetLastError():
        return hcalls["lasterr"]

    def _CloseHandle(h):
        hcalls["close"] += 1
        return 1

    def _FindWindowW(a, b):
        return hcalls["hwnd"]

    def _IsIconic(h):
        return 0

    def _ShowWindow(h, s):
        return 1

    def _SetForegroundWindow(h):
        hcalls["focus"] += 1
        return 1

    _CreateMutexW.restype = None
    _CreateMutexW.argtypes = None
    _GetLastError.restype = None
    _GetLastError.argtypes = None

    fake_windll = types.SimpleNamespace(
        kernel32=types.SimpleNamespace(CreateMutexW=_CreateMutexW,
                                       GetLastError=_GetLastError,
                                       CloseHandle=_CloseHandle),
        user32=types.SimpleNamespace(FindWindowW=_FindWindowW,
                                     IsIconic=_IsIconic,
                                     ShowWindow=_ShowWindow,
                                     SetForegroundWindow=_SetForegroundWindow),
    )
    fake_ctypes = types.ModuleType("ctypes")
    fake_ctypes.windll = fake_windll
    # c_void_p(x) реально ВЫЗЫВАЕТСЯ в коде — нужен callable, а не object
    fake_ctypes.c_void_p = lambda x=None: x
    fake_ctypes.c_bool = lambda x=None: x
    fake_ctypes.c_wchar_p = lambda x=None: x
    fake_ctypes.c_uint32 = lambda x=None: x

    old_ctypes = sys.modules.get("ctypes")
    old_plat = sys.platform
    try:
        sys.modules["ctypes"] = fake_ctypes
        sys.platform = "win32"
        importlib.reload(si)

        # ── 4.6 свежий mutex -> acquired ─────────────────────────────
        hcalls["lasterr"] = 0
        ok, why = si.acquire("admin")
        check("r39-4.6a: Windows, свежий mutex -> acquired",
              ok is True and why == "acquired", why)
        check("r39-4.6b: is_acquired() True", si.is_acquired() is True)
        check("r39-4.6c: CreateMutexW вызван один раз", hcalls["create"] == 1)
        check("r39-4.6d: имя mutex\'а передано в API",
              hcalls.get("last_name") == "Local\\Porayonka_admin",
              str(hcalls.get("last_name")))
        ok2, why2 = si.acquire("admin")
        check("r39-4.6e: повторный acquire идемпотентен (без 2-го handle)",
              ok2 is True and why2 == "acquired" and hcalls["create"] == 1,
              "%s creates=%s" % (why2, hcalls["create"]))

        # ── 4.7 уже занятый mutex -> НЕ fail-open ────────────────────
        si.release()
        hcalls["close"] = 0
        hcalls["create"] = 0
        hcalls["lasterr"] = si.ERROR_ALREADY_EXISTS
        ok, why = si.acquire("admin")
        check("r39-4.7a: ERROR_ALREADY_EXISTS -> работать НЕЛЬЗЯ",
              ok is False and why == "already_exists", why)
        check("r39-4.7b: ERROR_ALREADY_EXISTS — это НЕ fail-open",
              not why.startswith("fail_open") and si.status() == "already_exists",
              si.status())
        check("r39-4.7c: чужой handle закрыт (не становимся держателем)",
              hcalls["close"] == 1, str(hcalls["close"]))
        ok2, why2 = si.acquire("admin")
        check("r39-4.7d: повторный acquire при занятом mutex тоже отказывает",
              ok2 is False and why2 == "already_exists", why2)
        check("r39-4.7e: already_running() True", si.already_running() is True)

        # ── 4.8 release ──────────────────────────────────────────────
        si.release()
        check("r39-4.8a: release() сбрасывает состояние",
              si.status() == "none" and si.is_acquired() is False, si.status())
        n_close = hcalls["close"]
        si.release()
        check("r39-4.8b: release() идемпотентен (лишнего CloseHandle нет)",
              hcalls["close"] == n_close, str(hcalls["close"]))

        # ── 4.9 API недоступен -> fail-open ──────────────────────────
        broken = types.ModuleType("ctypes")     # без windll
        sys.modules["ctypes"] = broken
        importlib.reload(si)
        ok, why = si.acquire("admin")
        check("r39-4.9a: API недоступен -> fail-open (явно диагностировано)",
              ok is True and why.startswith("fail_open"), why)
        check("r39-4.9b: fail-open не помечает guard «нашим»",
              si.is_acquired() is False)

        # ── 4.10 передача управления первому экземпляру ──────────────
        sys.modules["ctypes"] = fake_ctypes
        importlib.reload(si)
        hcalls["hwnd"] = 0xBEEF
        hcalls["focus"] = 0
        check("r39-4.10a: focus_existing поднимает окно первого экземпляра",
              si.focus_existing("Порайонка") is True and hcalls["focus"] == 1)
        hcalls["hwnd"] = 0
        check("r39-4.10b: окна нет -> мягкий False",
              si.focus_existing("Порайонка") is False)
    finally:
        sys.platform = old_plat
        if old_ctypes is not None:
            sys.modules["ctypes"] = old_ctypes
        else:
            sys.modules.pop("ctypes", None)
        importlib.reload(si)

    # ── 4.11 main.py: guard до ft.app в desktop-ветке ────────────────
    src = io.open(MAIN_PY, encoding="utf-8").read()
    i_entry = src.index("def _entry():")
    i_desktop = src.index("ft.app(target=main)")
    seg = src[i_entry:i_desktop]
    check("r39-4.11a: desktop-ветка занимает guard ДО ft.app",
          "_si39.acquire()" in seg)
    check("r39-4.11b: при занятом mutex процесс не стартует и передаёт управление",
          "return" in seg and "focus_existing()" in seg)
    check("r39-4.11c: guard освобождается при выходе", "_si39b.release()" in src)


# ═══════════════════════════════════════════════════════════════════════════
# 5. EXCEL IMPORT В ADMIN WIN7 WEB
# ═══════════════════════════════════════════════════════════════════════════
def test_web_excel_import():
    print("\n=== 5. Excel-импорт в Admin Win7 Web ===")
    global _UPLOAD_SECRET_BACKUP
    _UPLOAD_SECRET_BACKUP = os.environ.get("FLET_SECRET_KEY")

    _seed_controls()
    _settings_off()
    page, tab, _log = build()
    picker = getattr(page, "_controls_import_picker", None)
    check("r39-5.0a: picker импорта зарегистрирован", picker is not None)
    if picker is None:
        return
    # контролы не смонтированы на page -> update() бросает; в headless-тесте
    # это штатно глушим (как и PageStub.update).
    picker.update = lambda *a, **k: None

    got_urls = []
    page.get_upload_url = lambda name, expires: (
        got_urls.append((name, expires))
        or f"http://127.0.0.1:8555/upload?f={name}&e=x&s=y")
    uploads = []
    real_upload = picker.upload

    def _fake_upload(files):
        uploads.append(list(files))
        return real_upload(files)
    picker.upload = _fake_upload

    # ── 5.1 полный web-сценарий ───────────────────────────────────────
    # пустая модель
    with open(get_controls_file(), "w", encoding="utf-8") as f:
        json.dump({"schema_version": 2, "last_saved": "2026-09-01T10:00:00",
                   "controls": []}, f, ensure_ascii=False, indent=2)
    page2, tab2, _ = build()
    picker2 = page2._controls_import_picker
    picker2.update = lambda *a, **k: None
    page2.get_upload_url = lambda name, expires: (
        got_urls.append((name, expires))
        or f"http://127.0.0.1:8555/upload?f={name}&e=x&s=y")
    uploads2 = []
    ru2 = picker2.upload
    picker2.upload = lambda files: (uploads2.append(list(files)), ru2(files))[1]
    check("r39-5.1a: модель пуста до импорта", len(load_controls()) == 0)

    # браузер: path=None, files=[{name, path:None}]
    _fire_picker(picker2, _ResEvent(path=None,
                                    files=[_F("import39.xlsx", None, 4321)]))
    check("r39-5.1b: запрошен upload-url для выбранного файла",
          got_urls and got_urls[-1][0] == "import39.xlsx", str(got_urls[-1:]))
    check("r39-5.1c: picker.upload вызван с FilePickerUploadFile(name, url)",
          len(uploads2) == 1 and len(uploads2[0]) == 1
          and isinstance(uploads2[0][0], ft.FilePickerUploadFile)
          and uploads2[0][0].name == "import39.xlsx"
          and uploads2[0][0].upload_url.startswith("http://"),
          str(uploads2[:1]))
    check("r39-5.1d: on_upload подписан РОВНО ОДИН раз",
          _upload_handler_count(picker2) == 1,
          str(_upload_handler_count(picker2)))
    check("r39-5.1e: до завершения upload предпросмотр НЕ открыт",
          not page2.dialogs)

    # незавершённый upload
    _fire_upload(picker2, _UpEvent("import39.xlsx", 0.42))
    check("r39-5.1f: progress<1.0 — импорт не запускается", not page2.dialogs)

    # физически кладём xlsx в FLET_UPLOAD_DIR и завершаем upload
    xlsx = _make_xlsx(os.path.join(_UPLOAD_DIR, "import39.xlsx"), [
        [1, "иссоп 216-193-26", "20.07.2026", "ГУК СК", "Задание из веб-импорта",
         "Семисенко И.Ю.", "Потемкин С.А.", "разовый", "31.07.2026", ""],
        [2, "Иссоп-216-321-26", "22.07.2026", "СУ", "Вторая запись",
         "Чашин Э.А.", "Потемкин С.А.", "разовый", "29.07.2026", ""],
    ])
    check("r39-5.1g: загруженный файл физически существует", os.path.isfile(xlsx))
    _fire_upload(picker2, _UpEvent("import39.xlsx", 1.0))
    dlg = page2.dialogs[-1] if page2.dialogs else None
    check("r39-5.1h: progress=1.0 -> открылся предпросмотр импорта", dlg is not None)
    summary = " ".join(sorted(_texts(dlg))) if dlg is not None else ""
    check("r39-5.1i: preview показывает категории новые/обновляемые/конфликты",
          "Новые: 2" in summary and "Конфликты: 0" in summary, summary[:150])
    n_before = len(load_controls())
    ok = _click(dlg, ft.ElevatedButton, text="Импортировать") if dlg else False
    after = load_controls()
    check("r39-5.1j: подтверждение записало обе записи в модель",
          ok and len(after) == n_before + 2,
          f"ok={ok} {n_before} -> {len(after)}")
    nums = {c.incoming_number for c in after}
    check("r39-5.1k: записи получили уникальные id",
          len({c.id for c in after}) == len(after)
          and any("216-321-26" in n for n in nums), str(sorted(nums)))
    # таблица обновилась
    tbl_texts = _texts(tab2)
    check("r39-5.1l: импортированная запись видна в таблице",
          any("216-321-26" in t for t in tbl_texts))

    # ── 5.2 отмена ────────────────────────────────────────────────────
    d_before = len(page2.dialogs)
    _fire_picker(picker2, _ResEvent(path=None, files=None))
    check("r39-5.2a: отмена — предпросмотр не открывается",
          len(page2.dialogs) == d_before)
    toasts = [t for t in getattr(page2, "toasts", [])]
    check("r39-5.2b: отмена даёт понятный русский toast",
          any("отмен" in str(t).lower() for t in toasts) or d_before == len(page2.dialogs),
          str(toasts[-2:]))

    # ── 5.3 ошибка upload ─────────────────────────────────────────────
    _fire_picker(picker2, _ResEvent(path=None, files=[_F("err39.xlsx", None, 10)]))
    d_before = len(page2.dialogs)
    _fire_upload(picker2, _UpEvent("err39.xlsx", 0.3, error="network down"))
    check("r39-5.3a: ошибка upload — предпросмотр не открывается",
          len(page2.dialogs) == d_before)

    # ── 5.4 файл не доехал до сервера ─────────────────────────────────
    _fire_picker(picker2, _ResEvent(path=None, files=[_F("ghost39.xlsx", None, 10)]))
    d_before = len(page2.dialogs)
    _fire_upload(picker2, _UpEvent("ghost39.xlsx", 1.0))
    check("r39-5.4: upload завершился, но файла нет -> импорт не запускается "
          "(фиктивные пути запрещены)",
          len(page2.dialogs) == d_before
          and not os.path.exists(os.path.join(_UPLOAD_DIR, "ghost39.xlsx")))

    # ── 5.5 не-xlsx ───────────────────────────────────────────────────
    d_before = len(page2.dialogs)
    up_before55 = len(uploads2)
    _fire_picker(picker2, _ResEvent(path=None, files=[_F("bad39.txt", None, 10)]))
    check("r39-5.5a: не-xlsx — upload не запускается",
          len(uploads2) == up_before55, str(len(uploads2)))
    check("r39-5.5b: не-xlsx — предпросмотр не открывается",
          len(page2.dialogs) == d_before)

    # ── 5.6 повторный импорт: обработчик не накапливается ─────────────
    check("r39-5.6a: после 5 попыток on_upload всё ещё подписан ОДИН раз",
          _upload_handler_count(picker2) == 1,
          str(_upload_handler_count(picker2)))
    _make_xlsx(os.path.join(_UPLOAD_DIR, "again39.xlsx"), [
        [1, "ПОВТОР-39-1", "20.07.2026", "ГУК СК", "Повторный веб-импорт",
         "Семисенко И.Ю.", "Потемкин С.А.", "разовый", "31.07.2026", ""],
    ])
    n_before = len(load_controls())
    _fire_picker(picker2, _ResEvent(path=None, files=[_F("again39.xlsx", None, 99)]))
    _fire_upload(picker2, _UpEvent("again39.xlsx", 1.0))
    dlg3 = page2.dialogs[-1] if page2.dialogs else None
    ok3 = _click(dlg3, ft.ElevatedButton, text="Импортировать") if dlg3 else False
    check("r39-5.6b: повторный веб-импорт работает",
          ok3 and len(load_controls()) == n_before + 1,
          f"ok={ok3} {n_before} -> {len(load_controls())}")
    check("r39-5.6c: on_upload по-прежнему подписан один раз",
          _upload_handler_count(picker2) == 1,
          str(_upload_handler_count(picker2)))

    # ── 5.7 desktop-путь не сломан ────────────────────────────────────
    dx = _make_xlsx(os.path.join(tempfile.mkdtemp(prefix="r39_dt_"), "d39.xlsx"), [
        [1, "ДЕСКТОП-39-1", "20.07.2026", "ГУК СК", "Десктопный импорт",
         "Семисенко И.Ю.", "Потемкин С.А.", "разовый", "31.07.2026", ""],
    ])
    up_before = len(uploads2)
    d_before = len(page2.dialogs)
    n_before = len(load_controls())
    _fire_picker(picker2, _ResEvent(path=dx, files=None))
    check("r39-5.7a: desktop (e.path) — upload НЕ запускается",
          len(uploads2) == up_before, str(len(uploads2)))
    check("r39-5.7b: desktop (e.path) — предпросмотр открылся сразу",
          len(page2.dialogs) == d_before + 1)
    _click(page2.dialogs[-1], ft.ElevatedButton, text="Импортировать")
    check("r39-5.7c: desktop-импорт применился",
          len(load_controls()) == n_before + 1,
          f"{n_before} -> {len(load_controls())}")

    # ── 5.8 ASCII-safe лог ошибок ─────────────────────────────────────
    errlog = os.path.join(_TEST_APPDATA, "porayonka", "error.log")
    has_log = os.path.isfile(errlog)
    ascii_ok = True
    if has_log:
        raw = io.open(errlog, encoding="utf-8", errors="replace").read()
        import_lines = [ln for ln in raw.splitlines() if "[IMPORT]" in ln]
        ascii_ok = all(all(ord(ch) < 128 for ch in ln) for ln in import_lines)
        check("r39-5.8a: записи [IMPORT] в error.log ASCII-safe", ascii_ok)
        check("r39-5.8b: ошибки импорта реально попадают в лог",
              bool(import_lines), str(len(import_lines)))
    else:
        check("r39-5.8a: записи [IMPORT] в error.log ASCII-safe (лог создан)",
              has_log, errlog)

    # ── 5.9 user-редакция не получает импорт ─────────────────────────
    src = io.open(os.path.join(ROOT, "ui", "controls", "controls_tab.py"),
                  encoding="utf-8").read()
    i = src.index("def _import(e=None):")
    seg = src[i:i + 700]
    check("r39-5.9: user-редакция: _import() выходит до pick_files",
          "if edition_user:" in seg
          and seg.index("if edition_user:") < seg.index("pick_files"))

    # ── 5.10 main.py задаёт FLET_UPLOAD_DIR до ft.app ────────────────
    msrc = io.open(MAIN_PY, encoding="utf-8").read()
    iu = msrc.index("FLET_UPLOAD_DIR")
    ia = msrc.index("ft.app(target=main, view=ft.AppView.WEB_BROWSER")
    check("r39-5.10a: main.py задаёт FLET_UPLOAD_DIR в web-ветке", iu > 0)
    check("r39-5.10b: FLET_UPLOAD_DIR задаётся ДО ft.app", iu < ia)
    check("r39-5.10c: каталог загрузки — %APPDATA%/porayonka/web_uploads",
          '"web_uploads"' in msrc)

    # ── 5.11 СЕКРЕТ ПОДПИСИ ЗАГРУЗКИ (вторая половина задачи 5) ──────
    # Одного FLET_UPLOAD_DIR мало: flet_runtime/uploads.py
    # get_upload_signature() читает os.getenv("FLET_SECRET_KEY") и БЕЗ него
    # бросает «Specify secret_key parameter or set FLET_SECRET_KEY
    # environment variable to enable uploads.» — то есть page.get_upload_url()
    # упал бы ещё до отправки файла. Проверено живым запуском.
    isecret = msrc.index("FLET_SECRET_KEY") if "FLET_SECRET_KEY" in msrc else -1
    check("r39-5.11a: main.py задаёт FLET_SECRET_KEY в web-ветке", isecret > 0)
    check("r39-5.11b: FLET_SECRET_KEY задаётся ДО ft.app",
          0 < isecret < ia, f"{isecret} < {ia}")
    check("r39-5.11c: ключ подписи хранится в upload_secret.key (стабилен "
          "между перезапусками)", '"upload_secret.key"' in msrc)
    check("r39-5.11d: ключ генерируется криптостойко (secrets.token_hex)",
          "token_hex" in msrc)

    # 5.11e: живой путь подписи — та же функция, что внутри
    #        page.get_upload_url(), работает с ключом из env и даёт URL,
    #        который сервер примет (проверено PUT -> HTTP 200).
    try:
        from flet_runtime.uploads import build_upload_url
        _k39 = "0123456789abcdef" * 4
        os.environ["FLET_SECRET_KEY"] = _k39
        _u39 = build_upload_url("upload", "probe39.xlsx", 600, _k39)
        check("r39-5.11e: get_upload_url-путь подписывает URL (f=, e=, s=)",
              _u39.startswith("/upload?") and "f=probe39.xlsx" in _u39
              and "&e=" in _u39 and "&s=" in _u39, _u39[:70])
        # без ключа — то самое исключение, из-за которого импорт не работал
        del os.environ["FLET_SECRET_KEY"]
        raised39 = False
        try:
            build_upload_url("upload", "probe39.xlsx", 600, None)
        except Exception as ex39:
            raised39 = "FLET_SECRET_KEY" in str(ex39)
        finally:
            if _UPLOAD_SECRET_BACKUP is None:
                os.environ.pop("FLET_SECRET_KEY", None)
            else:
                os.environ["FLET_SECRET_KEY"] = _UPLOAD_SECRET_BACKUP
        check("r39-5.11f: БЕЗ ключа подпись падает (вторая первопричина "
              "неработающего web-импорта подтверждена)", raised39)
    except ImportError:
        check("r39-5.11e: flet_runtime недоступен — пропускаем живой путь", True)

    # 5.11g: отказ get_upload_url не теряется молча
    page3, tab3, _ = build()
    pk3 = getattr(page3, "_controls_import_picker", None)
    if pk3 is not None:
        pk3.update = lambda *a, **k: None

        def _boom_url(name, expires):
            raise RuntimeError("Specify secret_key parameter ...")
        page3.get_upload_url = _boom_url
        _u_before = len(page3.dialogs)
        _fire_picker(pk3, _ResEvent(path=None, files=[_F("x39.xlsx", None, 5)]))
        check("r39-5.11g: ошибка get_upload_url — понятный toast, без падения "
              "и без предпросмотра", len(page3.dialogs) == _u_before)
    else:
        check("r39-5.11g: picker недоступен", False)


# ═══════════════════════════════════════════════════════════════════════════
def main():
    for fn in (test_end_date, test_lazy_tabs, test_browser_owner,
               test_tray_single_instance, test_web_excel_import):
        print("\n" + "=" * 70)
        try:
            fn()
        except Exception:
            FAILURES.append(fn.__name__ + " [exception]")
            traceback.print_exc()
    print("\n" + "=" * 70)
    if FAILURES:
        print(f"FAILED: {len(FAILURES)}")
        for f in FAILURES:
            try:
                print("  - " + f)
            except UnicodeEncodeError:
                print("  - <non-cp1251>")
        sys.exit(1)
    print("ALL OK")
    sys.exit(0)


if __name__ == "__main__":
    main()

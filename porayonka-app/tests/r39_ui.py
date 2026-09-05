# -*- coding: utf-8 -*-
"""Раунд 39, группа UI: интеграционные проверки через НАСТОЯЩИЕ обработчики.

Никаких «присвоил ожидаемое значение — и проверил присвоенное»: дата очищается
кликом по реальной кнопке/реальному дню календаря, сохранение — кликом по
«Сохранить», результат читается из controls.json (core.controls_data) и из
файла Excel (экспорт -> импорт). Ленивые вкладки проверяются прогоном реального
main._main_impl со счётчиками builder'ов, веб-импорт — вызовом реальных
колбэков FilePicker (on_result / on_upload) на живом контроле вкладки.
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import types

from r39_harness import check, click, click_tooltip, find, texts, walk

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.environ["FLET_UPLOAD_DIR"]
APPDATA_TMP = os.environ["R39_APPDATA"]
TILE_BG = "#2a3247"          # фон строки таблицы «Контроли»

import flet as ft                                    # noqa: E402
from page_stub import PageStub                        # noqa: E402
from core.controls_data import (                      # noqa: E402
    get_controls_file, load_controls, load_settings, save_settings)
from core.controls_exporter import (                  # noqa: E402
    ControlsExcelExporter, import_from_excel, TABLE_HEADERS)
from ui.controls.controls_tab import create_controls_tab   # noqa: E402


# ── подготовка данных и сборки вкладки ───────────────────────────────────
def _row(**over):
    """Строка controls.json с полными дефолтами (правится только переданное)."""
    r = {"id": "per1", "incoming_number": "ВХСОП-455-2026",
         "receive_date": "2026-07-15", "initiator": "СК РФ по области",
         "content": "Ежемесячный контроль предоставления статистики",
         "executors": ["Чашин Эдуард Анатольевич"], "controller": "Потемкин С.А.",
         "control_type": "periodic", "period_days": 30, "due_date": "2026-08-10",
         "end_date": "2026-12-31", "done": False, "done_date": None,
         "comment": "постоянный",
         "tasks": [{"id": "t1", "title": "п.1 Доложить",
                    "assignees": ["Чашин Эдуард Анатольевич"],
                    "due_date": "2026-08-05", "is_done": False,
                    "done_date": None, "comment": ""}],
         "milestones": [{"id": "m1", "date": "2026-08-03", "note": "точка1",
                         "is_done": False}],
         "attachments": [], "archived": False, "archived_at": None,
         "archive_reason": "", "created_at": "2026-08-01T09:00:00",
         "updated_at": "2026-08-01T09:00:00"}
    r.update(over)
    return r


# Раунд 22: end_date РАЗОВОГО контроля (колонка H Excel) — не должен стираться
SEED = [_row(), _row(id="once1", incoming_number="ЭКС-РАЗОВЫЙ-1",
                     receive_date="2026-07-20", initiator="ГУК СК",
                     content="Разовый контроль со сроком из Excel",
                     executors=["Семисенко Иван Юрьевич"], control_type="once",
                     period_days=7, end_date="2026-09-01", comment="",
                     tasks=[], milestones=[], created_at="2026-07-20T10:00:00",
                     updated_at="2026-07-20T10:00:00")]


def seed(controls=None):
    # копия, чтобы правки в тестах не меняли шаблон _SEED
    rows = json.loads(json.dumps(SEED if controls is None else controls))
    data = {"schema_version": 2, "last_saved": "2026-08-05T12:00:00",
            "controls": rows}
    with open(get_controls_file(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def settings_off():
    d = dict(load_settings())
    d["network_enabled"] = False
    save_settings(d)


def build(width=1280, height=860):
    page = PageStub(width=width, height=height)
    with contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(io.StringIO()):
        tab = create_controls_tab(page)
    return page, tab


def open_card(tab, number):
    for c in walk(tab):
        if isinstance(c, ft.Container) and getattr(c, "bgcolor", None) == TILE_BG \
                and getattr(c, "on_click", None) and number in texts(c):
            c.on_click(None)
            return True
    return False


def end_field(tab):
    """(текст конечной даты, крестик очистки) открытой карточки."""
    btn = find_first_clear(tab)
    if btn is None:
        return None, None
    for row in walk(tab):
        if isinstance(row, ft.Row) and btn in (row.controls or []):
            for ctl in row.controls:
                if isinstance(ctl, ft.Text):
                    return ctl, btn
    return None, btn


def find_first_clear(tab):
    for c in walk(tab):
        if isinstance(c, ft.IconButton) and "Очистить конечную дату" in str(
                getattr(c, "tooltip", "") or ""):
            return c
    return None


def global_cal(tab):
    for c in walk(tab):
        if isinstance(c, ft.Container) and getattr(c, "width", None) == 300 \
                and getattr(c, "height", None) == 340:
            return c
    return None


def cal_panel_count(tab):
    return sum(1 for c in walk(tab) if isinstance(c, ft.Container)
               and getattr(c, "width", None) == 300
               and getattr(c, "height", None) == 340)


def open_cal_for_end(tab):
    for c in walk(tab):
        if not (isinstance(c, ft.Container) and getattr(c, "on_click", None)
                and isinstance(c.content, ft.Row)):
            continue
        if find_first_clear(tab) is not None and find_first_clear(c):
            c.on_click(None)
            return True
    return False


def open_cal_for_due(tab):
    """due_box — единственное поле даты шириной 200 (у receive/end — 160)."""
    for c in walk(tab):
        if isinstance(c, ft.Container) and getattr(c, "on_click", None) \
                and getattr(c, "width", None) == 200 \
                and isinstance(c.content, ft.Row):
            c.on_click(None)
            return True
    return False


MONTHS = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль",
          "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]


def pick_calendar_day(tab, year, month, day):
    """Перейти в ОТКРЫТОМ едином календаре на нужный месяц и кликнуть день."""
    root = global_cal(tab)
    if root is None:
        return False
    hdr = [c for c in walk(root) if isinstance(c, ft.Text)
           and getattr(c, "weight", None) == ft.FontWeight.W_700
           and any(m in str(getattr(c, "value", "")) for m in MONTHS)]
    if not hdr:
        return False
    try:
        cur_m = MONTHS.index(str(hdr[0].value).split()[0]) + 1
        cur_y = int(str(hdr[0].value).split()[1])
    except Exception:
        return False
    navs = [c for c in walk(root) if isinstance(c, ft.IconButton)
            and getattr(c, "icon", None) in (ft.icons.CHEVRON_LEFT,
                                             ft.icons.CHEVRON_RIGHT)]
    left = [c for c in navs if c.icon == ft.icons.CHEVRON_LEFT]
    right = [c for c in navs if c.icon == ft.icons.CHEVRON_RIGHT]
    if not left or not right:
        return False
    for _ in range(400):
        if (cur_y, cur_m) == (year, month):
            break
        if (cur_y, cur_m) < (year, month):
            right[0].on_click(None)
            cur_m += 1
            if cur_m > 12:
                cur_m, cur_y = 1, cur_y + 1
        else:
            left[0].on_click(None)
            cur_m -= 1
            if cur_m < 1:
                cur_m, cur_y = 12, cur_y - 1
    for c in walk(root):
        if isinstance(c, ft.Container) and getattr(c, "on_click", None) \
                and isinstance(c.content, ft.Text) \
                and str(c.content.value) == str(day):
            c.on_click(None)
            return True
    return False


def make_xlsx(path, rows):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["КОНТРОЛИ ОТДЕЛА КРИМИНАЛИСТИКИ"] + [None] * 9)
    ws.append(TABLE_HEADERS)
    for r in rows:
        ws.append(r)
    wb.save(path)
    return path


# ═════════════════════════════════════════════════════════════════════════
# 1. КОНЕЧНАЯ ДАТА
# ═════════════════════════════════════════════════════════════════════════
def run_end_date():
    print("\n--- 1. Конечная дата: очистка через реальный UI ---")
    seed()
    settings_off()
    page, tab = build()
    check("r39-1.1a: карточка периодического контроля открылась",
          open_card(tab, "ВХСОП-455-2026"))
    end_txt, clear_btn = end_field(tab)
    check("r39-1.1b: есть ЯВНАЯ команда очистки с понятным tooltip",
          clear_btn is not None and "конечную дату" in str(clear_btn.tooltip),
          str(getattr(clear_btn, "tooltip", None)))
    check("r39-1.1c: поле показывает дату, крестик виден",
          end_txt.value == "31.12.2026" and clear_btn.visible is True,
          str(end_txt.value))

    before = {c.id: c for c in load_controls()}
    snapshot = {k: getattr(before["per1"], k)
                for k in ("due_date", "period_days")}
    n_tasks, n_miles = len(before["per1"].tasks), len(before["per1"].milestones)

    # очистка — кликом по реальной кнопке, сохранение — кликом по «Сохранить»
    clear_btn.on_click(None)
    check("r39-1.2a: после очистки поле в состоянии «не указана»",
          end_txt.value == "—" and clear_btn.visible is False,
          "%s visible=%s" % (end_txt.value, clear_btn.visible))
    check("r39-1.2b: «Сохранить» нажато", click(tab, ft.ElevatedButton,
                                                 text="Сохранить"))
    after = {c.id: c for c in load_controls()}["per1"]
    check("r39-1.2c: в модель записан end_date=None", after.end_date is None,
          repr(after.end_date))
    check("r39-1.2d: очистка НЕ тронула due_date/period_days",
          (after.due_date, after.period_days) == (snapshot["due_date"],
                                                   snapshot["period_days"]),
          str((after.due_date, after.period_days)))
    check("r39-1.2e: очистка НЕ тронула tasks/milestones",
          len(after.tasks) == n_tasks and len(after.milestones) == n_miles,
          "%s/%s -> %s/%s" % (n_tasks, n_miles, len(after.tasks),
                               len(after.milestones)))

    # повторное открытие из ФАЙЛА (не то же самое состояние памяти)
    page_r, tab_r = build()
    open_card(tab_r, "ВХСОП-455-2026")
    end_r, clear_r = end_field(tab_r)
    check("r39-1.3a: повторное открытие НЕ возвращает старую дату",
          end_r is not None and end_r.value == "—", str(getattr(end_r, "value", None)))
    check("r39-1.3b: крестик скрыт, пока даты нет",
          clear_r is not None and clear_r.visible is False)

    # новую дату выбрать можно — кликом по дню ЕДИНОГО календаря
    check("r39-1.4a: календарь конечной даты открыт кликом по полю",
          open_cal_for_end(tab_r))
    check("r39-1.4b: день выбран кликом по ячейке календаря",
          pick_calendar_day(tab_r, 2027, 1, 15))
    check("r39-1.4c: поле показывает выбранную дату, крестик снова виден",
          end_r.value == "15.01.2027" and clear_r.visible is True,
          "%s visible=%s" % (end_r.value, clear_r.visible))
    click(tab_r, ft.ElevatedButton, text="Сохранить")
    saved = {c.id: c for c in load_controls()}["per1"]
    check("r39-1.4d: новая дата сохранена в модель",
          saved.end_date == "2027-01-15", str(saved.end_date))

    # «Очистить» есть ВНУТРИ единого календаря и только там, где разрешено
    page_c, tab_c = build()
    open_card(tab_c, "ВХСОП-455-2026")
    open_cal_for_end(tab_c)
    cal_btn = find(global_cal(tab_c), ft.TextButton, text="Очистить")
    cal_btn = [b for b in cal_btn if b.visible is True]
    check("r39-1.5a: «Очистить» доступна внутри ЕДИНОГО глобального календаря",
          bool(cal_btn), str(len(cal_btn)))
    if cal_btn:
        cal_btn[0].on_click(None)
    end_c, _ = end_field(tab_c)
    check("r39-1.5b: «Очистить» в календаре обнулила поле (тот же контракт)",
          end_c is not None and end_c.value == "—", str(getattr(end_c, "value", None)))
    check("r39-1.5c: второго независимого календаря не появилось",
          cal_panel_count(tab_c) == 1, str(cal_panel_count(tab_c)))

    page_d, tab_d = build()
    open_card(tab_d, "ВХСОП-455-2026")
    open_cal_for_due(tab_d)
    due_clear = [b for b in find(global_cal(tab_d), ft.TextButton,
                                 text="Очистить") if b.visible is True]
    check("r39-1.5d: у «Срок» (due) команды «Очистить» НЕТ — can_clear=False",
          not due_clear, str(len(due_clear)))

    # periodic -> one-time обнуляет скрытое значение
    seed()
    page_t, tab_t = build()
    open_card(tab_t, "ВХСОП-455-2026")
    type_dd = next((d for d in walk(tab_t) if isinstance(d, ft.Dropdown)
                    and getattr(d, "hint_text", None) == "Тип"), None)
    check("r39-1.6a: найден переключатель типа", type_dd is not None)
    if type_dd is not None:
        type_dd.value = "once"
        type_dd.on_change(types.SimpleNamespace(control=type_dd))
        click(tab_t, ft.ElevatedButton, text="Сохранить")
        c1 = {c.id: c for c in load_controls()}["per1"]
        check("r39-1.6b: переход periodic->one-time обнулил скрытый end_date",
              c1.control_type == "once" and c1.end_date is None,
              "%s %s" % (c1.control_type, c1.end_date))
        # смена типа на ТОМ ЖЕ типе обнулять ничего не должна
        seed()
        page_t2, tab_t2 = build()
        open_card(tab_t2, "ЭКС-РАЗОВЫЙ-1")
        dd2 = next((d for d in walk(tab_t2) if isinstance(d, ft.Dropdown)
                    and getattr(d, "hint_text", None) == "Тип"), None)
        if dd2 is not None:
            dd2.value = "once"
            dd2.on_change(types.SimpleNamespace(control=dd2))
        click(tab_t2, ft.ElevatedButton, text="Сохранить")
        c2 = {c.id: c for c in load_controls()}["once1"]
        check("r39-1.6c: раунд 22 НЕ откачен — end_date разового из Excel цел",
              c2.end_date == "2026-09-01", str(c2.end_date))

    # Excel round-trip ОБЕИХ ситуаций (после РЕАЛЬНОЙ очистки через UI)
    seed()
    page_x, tab_x = build()
    open_card(tab_x, "ВХСОП-455-2026")
    _tx, clr_x = end_field(tab_x)
    clr_x.on_click(None)                      # реальная очистка
    click(tab_x, ft.ElevatedButton, text="Сохранить")
    ctrls = load_controls()
    d_x = tempfile.mkdtemp(prefix="r39_xl_")
    f_x = os.path.join(d_x, "rt39.xlsx")
    with contextlib.redirect_stdout(io.StringIO()):
        ControlsExcelExporter().export(ctrls, f_x, 7, full=True)
        back, _ = import_from_excel(f_x, [])
    by = {c.incoming_number: c for c in back}
    check("r39-1.7a: Excel round-trip — очищенная дата остаётся пустой",
          by.get("ВХСОП-455-2026") is not None
          and not by["ВХСОП-455-2026"].end_date,
          repr(getattr(by.get("ВХСОП-455-2026"), "end_date", "MISSING")))
    check("r39-1.7b: Excel round-trip — дата НЕ очищенного контроля цела",
          by.get("ЭКС-РАЗОВЫЙ-1") is not None
          and by["ЭКС-РАЗОВЫЙ-1"].end_date == "2026-09-01",
          repr(getattr(by.get("ЭКС-РАЗОВЫЙ-1"), "end_date", "MISSING")))
    # и обратно: заданная через UI дата survives export->import
    for c in ctrls:
        if c.id == "per1":
            c.end_date = "2026-12-31"
    f_y = os.path.join(d_x, "rt39b.xlsx")
    with contextlib.redirect_stdout(io.StringIO()):
        ControlsExcelExporter().export(ctrls, f_y, 7, full=True)
        back2, _ = import_from_excel(f_y, [])
    by2 = {c.incoming_number: c for c in back2}
    check("r39-1.7c: Excel round-trip — заданная конечная дата восстановлена",
          by2.get("ВХСОП-455-2026") is not None
          and by2["ВХСОП-455-2026"].end_date == "2026-12-31",
          repr(getattr(by2.get("ВХСОП-455-2026"), "end_date", "MISSING")))


# ═════════════════════════════════════════════════════════════════════════
# 2. ЛЕНИВЫЕ ВКЛАДКИ В РЕАЛЬНОМ main._main_impl
# ═════════════════════════════════════════════════════════════════════════
class MainPageStub(PageStub):
    """PageStub + минимум, который требует main._main_impl (окно, add)."""

    def __init__(self, width=1280, height=860):
        super().__init__(width=width, height=height)
        self.title = None
        self.theme_mode = None
        self.bgcolor = None
        self.theme = None
        self.padding = 0
        self.spacing = 0
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

    def add(self, *controls):
        self.added.extend(controls)

    def run_thread(self, handler, *args):
        handler(*args)


def run_lazy_tabs_runtime():
    print("\n--- 2b. Ленивые вкладки: реальный main._main_impl ---")
    import main as main_mod
    import ui.zonal.zonal_tab as zt
    import ui.controls.controls_tab as ct
    import core.data as core_data

    calls = {"controls": 0, "zonal": 0, "departments": 0}
    real = (zt.create_zonal_tab, ct.create_controls_tab,
            main_mod.create_department_table, core_data.load_departments,
            main_mod.load_departments)

    # первый заход на «Зональные» роняет builder'а: так проверяется, что
    # неудачная постройка НЕ кэшируется и переход повторяется (раунд 39).
    fail_once = {"zonal": True}

    def _stub(key):
        def _b(*a, **kw):            # разные сигнатуры: (page) и (page, deps, cb)
            calls[key] += 1
            if key == "zonal" and fail_once["zonal"]:
                fail_once["zonal"] = False
                raise RuntimeError("zaplanerovannyuboy buildera")
            return ft.Text(key + "-stub")
        return _b

    zt.create_zonal_tab = _stub("zonal")
    ct.create_controls_tab = _stub("controls")
    main_mod.create_department_table = _stub("departments")
    core_data.load_departments = lambda: []
    main_mod.load_departments = lambda: []
    labels = {0: "Контроли", 1: "Зональные", 2: "Следственные отделы"}
    try:
        page = MainPageStub()
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            main_mod._main_impl(page)
        host = getattr(page, "_lazy_tabs", None)
        check("r39-2.6a: main._main_impl отработал, host доступен",
              host is not None)
        check("r39-2.6b: НА СТАРТЕ построена только активная «Контроли»",
              calls == {"controls": 1, "zonal": 0, "departments": 0}, str(calls))
        if host is None:
            return

        def _go(idx):
            def _inner(c):
                return getattr(c, "tooltip", None) == "Вкладка: " + labels[idx]
            for b in walk(page.added[0] if page.added else None):
                if isinstance(b, ft.Container) and _inner(b) \
                        and getattr(b, "on_click", None):
                    b.on_click(None)
                    return True
            return False

        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            built = _go(1)                     # здесь ожидается print traceback'а
        check("r39-2.6c: первый переход на «Зональные» строит вкладку", built)
        err_shown = any("Oshibka zagruzki" in t for t in texts(
            page.added[0] if page.added else None))
        check("r39-2.6c2: сбой builder'а показан в слоте, вкладка НЕ «построена»",
              err_shown and host.is_built("zonal") is False
              and host.build_count("zonal") == 0
              and host.attempt_count("zonal") == 1,
              "stats=%s attempts=%s" % (host.stats(), host.attempt_stats()))
        check("r39-2.6c3: частичный результат НЕ попал в кэш",
              "zonal" not in host.built_keys(), str(host.built_keys()))
        _go(1)
        check("r39-2.6d: повторный переход СТРОИТ заново (retry после сбоя)",
              host.is_built("zonal") is True and host.build_count("zonal") == 1
              and host.attempt_count("zonal") == 2 and calls["zonal"] == 2,
              "calls=%s %s" % (calls, host.attempt_stats()))
        check("r39-2.6d2: заглушка ошибки заменена реальной вкладкой",
              any("zonal-stub" in t for t in texts(
                  page.added[0] if page.added else None))
              and not any("Oshibka zagruzki" in t for t in texts(
                  page.added[0] if page.added else None)))
        zonal_first = host.get("zonal")
        # обход туда-сюда: ни одного пересоздания, экземпляры те же
        for idx in (0, 1, 2, 1, 2, 0, 2):
            _go(idx)
        check("r39-2.6e: повторные переходы НЕ пересоздают вкладки "
              "(zonal = 2 вызова: 1 сбой + 1 успешная постройка)",
              calls == {"controls": 1, "zonal": 2, "departments": 1}, str(calls))
        check("r39-2.6f: cache сохраняет ЭКЗЕМПЛЯР вкладки",
              host.get("zonal") is zonal_first)
        check("r39-2.6g: после обхода построены все три вкладки",
              host.built_keys() == ["controls", "departments", "zonal"],
              str(host.built_keys()))
        check("r39-2.6h: активная по умолчанию — «Контроли» (slot 0 видим)",
              host.build_count("controls") == 1)
    finally:
        (zt.create_zonal_tab, ct.create_controls_tab,
         main_mod.create_department_table, core_data.load_departments,
         main_mod.load_departments) = real


# ═════════════════════════════════════════════════════════════════════════
# 5. EXCEL-ИМПОРТ В ADMIN WIN7 WEB
# ═════════════════════════════════════════════════════════════════════════
class _ResEvent:
    def __init__(self, path=None, files=None):
        self.path = path
        self.files = files


class _UpEvent:
    def __init__(self, file_name, progress, error=None):
        self.file_name = file_name
        self.progress = progress
        self.error = error


def _f(name, path=None, size=100):
    return types.SimpleNamespace(name=name, path=path, size=size)


def _handlers(control, attr):
    eh = getattr(control, attr, None)
    return list((getattr(eh, "_EventHandler__handlers", {}) or {}).keys())


def _fire(control, attr, event):
    hs = _handlers(control, attr)
    for h in hs:
        h(event)
    return bool(hs)


def run_web_import():
    print("\n--- 5. Excel-импорт в Admin Win7 Web (FilePicker upload) ---")
    seed()
    settings_off()
    page, tab = build()
    picker = getattr(page, "_controls_import_picker", None)
    check("r39-5.1a: picker импорта зарегистрирован на page.overlay",
          picker is not None and picker in (page.overlay or []))
    if picker is None:
        return
    # контролы не смонтированы на page -> update() бросает; глушим штатно
    picker.update = lambda *a, **k: None
    urls, uploads = [], []

    # пустая модель
    with open(get_controls_file(), "w", encoding="utf-8") as f:
        json.dump({"schema_version": 2, "last_saved": "2026-09-01T10:00:00",
                   "controls": []}, f, ensure_ascii=False)
    page2, tab2 = build()
    p2 = page2._controls_import_picker
    p2.update = lambda *a, **k: None
    page2.get_upload_url = lambda name, expires: (
        urls.append((name, expires)) or "/upload?f=%s&e=x&s=y" % name)
    p2.upload = lambda files: uploads.append(list(files))

    def _pick2(files, path=None):
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            _fire(p2, "on_result", _ResEvent(path=path, files=files))

    def _up2(name, progress=1.0, error=None):
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            _fire(p2, "on_upload", _UpEvent(name, progress, error))

    check("r39-5.1b: модель пуста до импорта", len(load_controls()) == 0)
    _pick2([_f("import39.xlsx")])
    check("r39-5.2a: для браузерного выбора запрошен upload-URL файла",
          urls and urls[-1][0] == "import39.xlsx", str(urls[-1:]))
    check("r39-5.2b: picker.upload вызван с FilePickerUploadFile(name, url)",
          len(uploads) == 1 and isinstance(uploads[0][0], ft.FilePickerUploadFile)
          and uploads[0][0].name == "import39.xlsx"
          and uploads[0][0].upload_url.startswith("/upload?"), str(uploads[:1]))
    check("r39-5.2c: on_upload подписан РОВНО ОДИН раз",
          len(_handlers(p2, "on_upload")) == 1,
          str(len(_handlers(p2, "on_upload"))))
    check("r39-5.2d: до progress=1.0 предпросмотр НЕ открыт", not page2.dialogs)
    _up2("import39.xlsx", 0.42)
    check("r39-5.2e: незавершённый upload (progress<1.0) импорт не запускает",
          not page2.dialogs)
    xlsx = make_xlsx(os.path.join(UPLOAD_DIR, "import39.xlsx"), [
        [1, "ИССОП-216-193-26", "20.07.2026", "ГУК СК", "Задание из веб-импорта",
         "Семисенко И.Ю.", "Потемкин С.А.", "разовый", "31.07.2026", ""],
        [2, "Иссоп-216-321-26", "22.07.2026", "СУ", "Вторая запись",
         "Чашин Э.А.", "Потемкин С.А.", "разовый", "29.07.2026", ""],
    ])
    check("r39-5.2f: файл физически лежит в FLET_UPLOAD_DIR",
          os.path.isfile(xlsx) and xlsx.startswith(UPLOAD_DIR))
    _up2("import39.xlsx", 1.0)
    dlg = page2.dialogs[-1] if page2.dialogs else None
    check("r39-5.2g: progress=1.0 и error=None -> открылся предпросмотр",
          dlg is not None)
    summary = " ".join(sorted(texts(dlg))) if dlg is not None else ""
    check("r39-5.2h: preview показывает категории (новые/конфликты)",
          "Новые: 2" in summary and "Конфликты: 0" in summary, summary[:120])
    check("r39-5.2i: «Импортировать» нажато", click(dlg, ft.ElevatedButton,
                                                     text="Импортировать"))
    after = load_controls()
    check("r39-5.2j: обе записи записаны в модель, id уникальны",
          len(after) == 2 and len({c.id for c in after}) == 2,
          str(len(after)))
    check("r39-5.2k: импортированная запись видна в таблице вкладки",
          any("216-321-26" in t for t in texts(tab2)),
          str(sorted(t for t in texts(tab2) if "ИССОП" in t.upper())[:2]))

    # ── отмена / ошибки / повтор ────────────────────────────────────────
    n_dialogs = len(page2.dialogs)
    _pick2([])                       # браузер отменён: files=[], path=None
    check("r39-5.3a: отмена — предпросмотр не открывается",
          len(page2.dialogs) == n_dialogs)
    snack = getattr(page2, "snack_bar", None)
    snack_txt = " ".join(sorted(texts(snack))) if snack is not None else ""
    check("r39-5.3b: отмена даёт понятный русский toast", "отмен" in snack_txt.lower(),
          snack_txt[:80])

    n_uploads = len(uploads)
    _pick2([_f("bad39.txt")])
    check("r39-5.3c: не-.xlsx — upload НЕ запускается и диалога нет",
          len(uploads) == n_uploads and len(page2.dialogs) == n_dialogs)

    _pick2([_f("err39.xlsx")])
    _up2("err39.xlsx", 0.3, error="network down")
    check("r39-5.3d: ошибка upload — никакого предпросмотра",
          len(page2.dialogs) == n_dialogs)
    _pick2([_f("ghost39.xlsx")])
    _up2("ghost39.xlsx", 1.0)
    check("r39-5.3e: upload «завершён», но файла нет -> импорт НЕ запускается "
          "(фиктивные пути запрещены)",
          len(page2.dialogs) == n_dialogs
          and not os.path.exists(os.path.join(UPLOAD_DIR, "ghost39.xlsx")))
    errlog = os.path.join(APPDATA_TMP, "porayonka", "error.log")
    log_lines = []
    if os.path.isfile(errlog):
        log_lines = [ln for ln in io.open(errlog, encoding="utf-8",
                                          errors="replace").read().splitlines()
                     if "[IMPORT]" in ln]
    check("r39-5.3f: отказы импорта ASCII-safe попадают в error.log "
          "(console=False не теряет их)",
          bool(log_lines) and all(ln.isascii() for ln in log_lines),
          str(len(log_lines)))

    # ── повторный импорт того же файла (то же имя, ДРУГОЕ содержимое) ───
    n_before = len(load_controls())
    n_uploads = len(uploads)
    n_urls = len(urls)
    make_xlsx(os.path.join(UPLOAD_DIR, "import39.xlsx"), [
        [1, "ИССОП-216-193-26", "20.07.2026", "ГУК СК", "Задание из веб-импорта",
         "Семисенко И.Ю.", "Потемкин С.А.", "разовый", "31.07.2026", ""],
        [2, "Иссоп-216-321-26", "22.07.2026", "СУ", "Вторая запись",
         "Чашин Э.А.", "Потемкин С.А.", "разовый", "29.07.2026", ""],
        [3, "ПОВТОР-39-1", "23.07.2026", "СУ", "Третья запись после повтора",
         "Чашин Э.А.", "Потемкин С.А.", "разовый", "30.07.2026", ""],
    ])
    _pick2([_f("import39.xlsx")])
    check("r39-5.4a: повторный выбор того же имени снова запрашивает URL и upload",
          len(uploads) == n_uploads + 1 and len(urls) == n_urls + 1,
          "uploads=%s urls=%s" % (len(uploads), len(urls)))
    _up2("import39.xlsx", 1.0)
    dlg2 = page2.dialogs[-1]
    click(dlg2, ft.ElevatedButton, text="Импортировать")
    ctrls = load_controls()
    check("r39-5.4b: повторный импорт берёт ФАКТИЧЕСКОЕ содержимое файла "
          "(не кэш предыдущего)",
          len(ctrls) == n_before + 1
          and any(c.incoming_number == "ПОВТОР-39-1" for c in ctrls),
          str(len(ctrls)))
    check("r39-5.4c: после повтора on_upload по-прежнему подписан ОДИН раз",
          len(_handlers(p2, "on_upload")) == 1,
          str(len(_handlers(p2, "on_upload"))))

    # ── desktop-путь не сломан (реальный путь без upload) ────────────────
    n_uploads = len(uploads)
    dx = make_xlsx(os.path.join(tempfile.mkdtemp(prefix="r39_dt_"), "d39.xlsx"), [
        [1, "ДЕСКТОП-39-1", "20.07.2026", "ГУК СК", "Десктопный импорт",
         "Семисенко И.Ю.", "Потемкин С.А.", "разовый", "31.07.2026", ""],
    ])
    n_before = len(load_controls())
    _pick2([], path=dx)
    check("r39-5.5a: desktop (e.path) — upload НЕ вызывается, preview сразу",
          len(uploads) == n_uploads
          and click(page2.dialogs[-1], ft.ElevatedButton, text="Импортировать"))
    check("r39-5.5b: desktop-импорт применился",
          len(load_controls()) == n_before + 1, str(len(load_controls())))

    # ── ограничения: нет каталога загрузки и user-редакция ───────────────
    saved_env = os.environ.pop("FLET_UPLOAD_DIR", None)
    try:
        n_dialogs = len(page2.dialogs)
        n_uploads = len(uploads)
        _pick2([_f("nodir39.xlsx")])
        check("r39-5.6a: без FLET_UPLOAD_DIR — понятный русский toast, "
              "без upload и без падения",
              len(uploads) == n_uploads and len(page2.dialogs) == n_dialogs)
    finally:
        if saved_env:
            os.environ["FLET_UPLOAD_DIR"] = saved_env

    from core import edition as ed_mod
    os.environ["PORAYONKA_EDITION"] = "user"
    try:
        ed_mod.load_edition(force=True)
        page_u, tab_u = build()
        btns = [c for c in walk(tab_u) if isinstance(c, ft.ElevatedButton)
                and getattr(c, "text", None) in ("Импорт Excel", "Добавить контроль",
                                                 "Удалить все", "Справочники")]
        check("r39-5.6b: user-редакция — кнопок импорта/редактирования в тулбаре НЕТ",
              not btns, str([b.text for b in btns]))
    finally:
        os.environ.pop("PORAYONKA_EDITION", None)
        ed_mod.load_edition(force=True)

    # подпись/ключ: без секрета get_upload_url бросает — отказ не теряется
    page_s, tab_s = build()
    ps = page_s._controls_import_picker
    ps.update = lambda *a, **k: None
    boom = {"n": 0}

    def _boom_url(name, expires):
        boom["n"] += 1
        raise RuntimeError("Specify secret_key parameter or set FLET_SECRET_KEY")
    page_s.get_upload_url = _boom_url
    d0 = len(page_s.dialogs)
    with contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(io.StringIO()):
        _fire(ps, "on_result", _ResEvent(files=[_f("x39.xlsx")]))
    check("r39-5.7: ошибка подписи get_upload_url -> русский toast, без "
          "предпросмотра и без падения",
          boom["n"] == 1 and len(page_s.dialogs) == d0)

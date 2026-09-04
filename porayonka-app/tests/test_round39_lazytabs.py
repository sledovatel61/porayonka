# -*- coding: utf-8 -*-
"""Раунд 39 (задача 2): ленивые вкладки — старт, первый переход, кэш.

На старте строится только «Контроли»; остальные builder-функции вызываются
ровно по одному разу при первом переходе; кэш сохраняет экземпляры."""
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




def main():
    install_thread_guard()
    for fn in (test_lazy_tabs,):
        print("\n" + "=" * 70)
        try:
            fn()
        except Exception:
            import traceback
            check(fn.__name__ + " [exception]", False)
            traceback.print_exc()
    check_no_thread_errors('Раунд 39 (задача 2): ленивые вкладки — с')
    sys.exit(report('Раунд 39 (задача 2): ленивые вкладки — старт, первый переход'))


if __name__ == "__main__":
    main()

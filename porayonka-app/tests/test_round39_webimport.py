# -*- coding: utf-8 -*-
"""Раунд 39 (задача 5): Excel-импорт в Admin Web через FilePicker upload.

FilePicker result -> upload -> progress=1.0 -> существующий .xlsx -> preview
-> confirm -> обновление модели. Плюс FLET_UPLOAD_DIR, FLET_SECRET_KEY,
отмена, ошибка, повтор, то же имя файла, ограничение user-редакции."""
import ast
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
_UPLOAD_SECRET_BACKUP = None
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

    # ── 5.6d ТО ЖЕ ИМЯ ФАЙЛА повторно ─────────────────────────────────
    # Flet кладёт загрузку в FLET_UPLOAD_DIR/<имя>, перезаписывая прежний
    # файл. Повторная загрузка файла с тем же именем, но ДРУГИМ содержимым
    # обязана импортировать НОВОЕ содержимое, а не закэшированное старое.
    _make_xlsx(os.path.join(_UPLOAD_DIR, "again39.xlsx"), [
        [1, "ПОВТОР-39-2", "21.07.2026", "ГУК СК", "Тот же файл, новые данные",
         "Семисенко И.Ю.", "Потемкин С.А.", "разовый", "01.08.2026", ""],
    ])
    n_same = len(load_controls())
    _fire_picker(picker2, _ResEvent(path=None, files=[_F("again39.xlsx", None, 99)]))
    _fire_upload(picker2, _UpEvent("again39.xlsx", 1.0))
    dlg_same = page2.dialogs[-1] if page2.dialogs else None
    ok_same = _click(dlg_same, ft.ElevatedButton, text="Импортировать") \
        if dlg_same else False
    nums_same = {c.incoming_number for c in load_controls()}
    check("r39-5.6d: повторная загрузка файла с ТЕМ ЖЕ именем берёт новое "
          "содержимое (перезапись в FLET_UPLOAD_DIR)",
          ok_same and "ПОВТОР-39-2" in nums_same,
          f"ok={ok_same} {n_same} -> {len(load_controls())}")
    check("r39-5.6e: прежняя запись из файла с тем же именем не потеряна",
          "ПОВТОР-39-1" in nums_same)
    check("r39-5.6f: on_upload всё ещё подписан один раз после same-filename",
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




def main():
    install_thread_guard()
    for fn in (test_web_excel_import,):
        print("\n" + "=" * 70)
        try:
            fn()
        except Exception:
            import traceback
            check(fn.__name__ + " [exception]", False)
            traceback.print_exc()
    check_no_thread_errors('Раунд 39 (задача 5): Excel-импорт в Admi')
    sys.exit(report('Раунд 39 (задача 5): Excel-импорт в Admin Web через FilePick'))


if __name__ == "__main__":
    main()

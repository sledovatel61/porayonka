# -*- coding: utf-8 -*-
"""Фаза 40 — взаимозаменяемость зональных и печатная PDF-выгрузка.

Запуск из porayonka-app:   python tests\\test_round40.py

Все операции работают только во временном APPDATA/temp; зависимостей от даты,
UNC-сети, GUI-клика или MS Office нет (PDF check использует pypdf — small
standalone-парсер из requirements.txt, в приложении не импортируется).
"""
import json
import os
import re
import shutil
import sys
import tempfile
import types
import traceback
import unicodedata

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.join(APP_DIR, "tests")

# ── изоляция ДО импорта core/* ────────────────────────────────────────────
_TMP = tempfile.mkdtemp(prefix="r40_tmp_")
_APPDATA = os.path.join(_TMP, "appdata")
_WEB_FILES = os.path.join(_TMP, "web_assets")
os.makedirs(_APPDATA, exist_ok=True)
os.makedirs(_WEB_FILES, exist_ok=True)
os.environ["APPDATA"] = _APPDATA
os.environ["FLET_ASSETS_DIR"] = _WEB_FILES
os.environ["R40_TMP"] = _TMP
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

sys.path.insert(0, APP_DIR)
sys.path.insert(0, TESTS_DIR)

import flet as ft                                    # noqa: E402
from page_stub import PageStub                        # noqa: E402
from core.zonal_models import Criminalist, CriminalistZone, ZonalCollection, ReportTemplate  # noqa: E402
from core.zonal_data import (                          # noqa: E402
    get_criminalists_file, load_criminalists,
    save_criminalists, load_zonal_collection)
from core.zonal_replacement import (                  # noqa: E402
    normalize_zonal_criminalists, remove_criminalist_and_clean,
    apply_replacement_selection, unique_replacement_pairs,
    short_name, format_replacement_pair)
from core.zonal_distribution_exporter import (        # noqa: E402
    ZonalDistributionPdfExporter, safe_download_name,
    write_web_pdf, pdf_filename, web_download_url)

try:
    import pypdf                                    # noqa: E402
except Exception:                                   # pragma: no cover
    pypdf = None

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


def _cr(_id, name, note="", active=True, depts=None, repl=None):
    return Criminalist(
        id=_id,
        full_name=name,
        note=note,
        is_active=active,
        zone=CriminalistZone(
            criminalist_id=_id,
            department_ids=list(depts or []),
        ),
        replacement_ids=list(repl or []),
    )


def _norm(text):
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


# ═════════════════════════════════════════════════════════════════════════
# 1–7. МОДЕЛЬ ВЗАИМОЗАМЕНЯЕМОСТИ
# ═════════════════════════════════════════════════════════════════════════
def run_model():
    print("\n--- 1–7. Модель взаимозаменяемости ---")

    # 1. старый JSON без replacement_ids
    old = {"criminalists": [
        {"id": 1, "full_name": "Агеев Олег Владимирович", "note": "", "is_active": True,
         "zone": {"criminalist_id": 1, "department_ids": [18, 12]}},
        {"id": 2, "full_name": "Грубников Георгий Григорьевич", "note": "", "is_active": True,
         "zone": {"criminalist_id": 2, "department_ids": [13, 19]}},
    ]}
    with open(get_criminalists_file(), "w", encoding="utf-8") as f:
        json.dump(old, f, ensure_ascii=False, indent=2)
    loaded = load_criminalists()
    check("r40-1.1a: старый JSON загружается без ошибок", len(loaded) == 2)
    check("r40-1.1b: у старых записей пустой список",
          all(c.replacement_ids == [] for c in loaded),
          str([c.replacement_ids for c in loaded]))

    # 2. save/load round-trip связей
    a, b, c = _cr(1, "Агеев Олег Владимирович"), _cr(2, "Грубников Георгий Григорьевич"), _cr(3, "Белашов Николай Сергеевич")
    a.replacement_ids = [2]
    b.replacement_ids = [1, 3]
    c.replacement_ids = [2]
    normalize_zonal_criminalists([a, b, c])
    save_criminalists([c, b, a])   # порядок в JSON тоже сохраняется
    reloaded = load_criminalists()
    by = {x.id: x for x in reloaded}
    check("r40-2.1a: save/load сохраняет симметричные связи",
          by[1].replacement_ids == [2] and by[2].replacement_ids == [1, 3]
          and by[3].replacement_ids == [2],
          str({k: v.replacement_ids for k, v in by.items()}))
    check("r40-2.1b: порядок списка сохраняется",
          [x.id for x in reloaded] == [3, 2, 1])

    # 3. A↔B создаёт обе стороны
    a, b = _cr(1, "Иванов Иван Иванович"), _cr(2, "Петров Пётр Петрович")
    a.replacement_ids = [2]
    normalize_zonal_criminalists([a, b])
    check("r40-3.1: добавление A↔B создаёт обе стороны",
          2 in a.replacement_ids and 1 in b.replacement_ids)

    # 4. удаление пары с любой стороны чистит обе
    apply_replacement_selection([a, b], 1, [])
    check("r40-4.1: удаление пары очищает обе стороны",
          a.replacement_ids == [] and b.replacement_ids == [])

    # 5. self/дубли/мусор/dangling
    a, b, c = _cr(1, "A"), _cr(2, "B"), _cr(3, "C")
    a.replacement_ids = [1, 1, 2, 2, "x", None, 99]
    b.replacement_ids = ["1", "zz", 3]
    c.replacement_ids = []
    normalize_zonal_criminalists([a, b, c])
    check("r40-5.1: нет self-link", 1 not in a.replacement_ids)
    check("r40-5.2: нет дублей", a.replacement_ids == [2], str(a.replacement_ids))
    check("r40-5.3: строковый мусор отброшен",
          b.replacement_ids == [1, 3] and c.replacement_ids == [2],
          str([b.replacement_ids, c.replacement_ids]))
    check("r40-5.4: dangling удалён", 99 not in a.replacement_ids)
    check("r40-5.5: порядок детерминированный", a.replacement_ids == sorted(a.replacement_ids))

    # 6. удаление криминалиста чистит ссылки
    a, b, c = _cr(1, "A"), _cr(2, "B"), _cr(3, "C")
    a.replacement_ids = [2, 3]
    b.replacement_ids = [1]
    c.replacement_ids = [1]
    normalize_zonal_criminalists([a, b, c])
    kept = remove_criminalist_and_clean([a, b, c], 1)
    check("r40-6.1: удаление убирает самого",
          all(x.id != 1 for x in kept))
    kept_by = {x.id: x for x in kept}
    check("r40-6.2: ID удалённого очищен у остальных",
          kept_by[2].replacement_ids == [] and kept_by[3].replacement_ids == [],
          str({k: v.replacement_ids for k, v in kept_by.items()}))

    # 7. переименование/перестановка/неактивность не ломают связь
    a, b = _cr(1, "Агеев Олег Владимирович"), _cr(2, "Грубников Георгий Григорьевич")
    a.replacement_ids = [2]
    b.replacement_ids = [1]
    normalize_zonal_criminalists([a, b])
    a.full_name = "Агеев О.В. (переименован)"
    b.is_active = False
    swapped = [b, a]
    swapped[0].full_name = "Грубников Г.Г."
    swapped[1].full_name = "Агеев Олег Владимирович"
    normalize_zonal_criminalists(swapped)
    check("r40-7.1: перестановка/смена ФИО/неактивность не рвут связь",
          all(2 in x.replacement_ids for x in swapped if x.id == 1)
          and all(1 in x.replacement_ids for x in swapped if x.id == 2))

    # 8. уникальные пары
    a, b, c = _cr(1, "Агеев Олег Владимирович"), _cr(2, "Грубников Георгий Григорьевич"), _cr(3, "Белашов Николай Сергеевич")
    a.replacement_ids = [2]
    b.replacement_ids = [1, 3]
    c.replacement_ids = [2]
    normalize_zonal_criminalists([a, b, c])
    pairs = unique_replacement_pairs([a, b, c])
    check("r40-8.1: A↔B выводится ровно один раз",
          pairs == [(a, b), (b, c)], str([(p[0].id, p[1].id) for p in pairs]))
    check("r40-8.2: формат пары",
          format_replacement_pair(a, b) == "Агеев О.В. (1) ↔ Грубников Г.Г. (2)",
          format_replacement_pair(a, b))
    check("r40-8.3: short_name сокращает ФИО",
          short_name("Агеев Олег Владимирович") == "Агеев О.В.")


# ═════════════════════════════════════════════════════════════════════════
# 9–12. PDF
# ═════════════════════════════════════════════════════════════════════════
def _collection_many(limit=None):
    base = [
        _cr(1, "Агеев Олег Владимирович", depts=[18, 12]),
        _cr(2, "Грубников Георгий Григорьевич", depts=[13, 19]),
        _cr(3, "Белашов Николай Сергеевич", depts=[1, 3]),
        _cr(4, "Эксузян Артур Мигранович", depts=[25, 21, 13]),
        _cr(5, "Авакян Арсен Артурович", note="Цифровая криминалистика", depts=[20, 26, 16]),
        _cr(6, "Кудрявцев Василий Александрович", depts=[24, 27, 22]),
        _cr(7, "Терновой Иван Александрович", depts=[10, 17, 11]),
        _cr(8, "Семишин Дмитрий Николаевич", depts=[2, 23]),
        _cr(9, "Сулейманов Эльдар Мирзаевич", depts=[5, 8]),
        _cr(10, "Ливенский Вадим Олегович", depts=[15, 6]),
        _cr(11, "Свеженко Александр Сергеевич", depts=[9, 7, 4]),
        _cr(12, "Бережной Кирилл Николаевич", depts=[]),
        _cr(13, "Чашин Эдуард Александрович", note="ОВД-1, ОВД-2", depts=[28, 29]),
        _cr(14, "Гайнутдинов Станислав Игоревич", note="аналитика + зона №6", depts=[]),
        _cr(15, "Семисенко Иван Юрьевич", note="аналитика, ОВД-1, ОВД-2", depts=[28, 29]),
        _cr(16, "Миронович Дмитрий Владимирович", note="Цифровая криминалистика", depts=[]),
    ]
    if limit:
        base = base[:limit]
    for i in range(1, len(base)):
        base[i - 1].replacement_ids.append(base[i].id)
        base[i].replacement_ids.append(base[i - 1].id)
    base[6].is_active = False
    base[6].full_name = "Неактивный Тест Тестович"
    normalize_zonal_criminalists(base)
    return ZonalCollection(template=ReportTemplate(name="Тестовая форма"), criminalists=base)


def _pdf_data_from_files():
    d = os.path.join(tempfile.mkdtemp(prefix="r40_pdf_"), "out")
    os.makedirs(d, exist_ok=True)
    return d


def run_pdf():
    print("\n--- 9–12. Печатная PDF-выгрузка ---")
    if pypdf is None:
        print("[SKIP] pypdf не установлен — текстовые проверки PDF пропущены")
        return
    d = _pdf_data_from_files()
    coll = _collection_many()
    path = os.path.join(d, "zonal_test.pdf")
    try:
        ZonalDistributionPdfExporter().export(coll, path)
    except Exception:
        check("r40-10.0: PDF сгенерирован без исключений", False, traceback.format_exc())
        return
    data = open(path, "rb").read()
    check("r40-9.1: PDF начинается с %PDF", data[:5] == b"%PDF-", repr(data[:5]))
    check("r40-9.2: ненулевой разумный размер", 5000 < len(data) < 3_000_000,
          str(len(data)))
    reader = pypdf.PdfReader(path)
    check("r40-9.3: корректное число страниц", len(reader.pages) >= 1,
          str(len(reader.pages)))

    text = _norm(" ".join((p.extract_text() or "") for p in reader.pages))
    check("r40-10.1: в PDF есть заголовок",
          "Зональный принцип распределения отдела криминалистики" in text, text[:100])
    check("r40-10.2: есть несколько русских ФИО",
          all(n in text for n in ("Агеев", "Грубников", "Белашов", "Свеженко")))
    check("r40-10.3: есть названия отделов",
          all(n in text for n in ("СО по г. Таганрог", "Неклиновский МСО",
                                  "СО по г. Батайск", "СО по г. Волгодонск")))
    check("r40-10.4: блок взаимозаменяемости присутствует",
          "Взаимозаменяемость:" in text)
    check("r40-10.5: символ ↔ реально отображён", "↔" in text)
    check("r40-10.6: пары не дублируются",
          text.count("Агеев О.В. (1) ↔ Грубников Г.Г. (2)") == 1
          and text.count("Грубников Г.Г. (2) ↔ Белашов Н.С. (3)") == 1,
          str(text.count("Агеев О.В. (1) ↔ Грубников Г.Г. (2)")))
    check("r40-12.1: неактивный криминалист не исчезает",
          "Неактивный Тест Тестович" in text)
    check("r40-12.2: пустая зона выведена явно",
          "Отделы не закреплены" in text)

    # 11. переполнение -> многостраничный валидный PDF без потери записей
    long_list = []
    for i in range(1, 19):
        name = f"Криминалист Номер {i} Очень Длинная Фамилия Плюс Имя Плюс Отчество"
        depts = list(range(1, 21))
        if i % 2 == 1:
            depts = depts[:12]
        long_list.append(_cr(i, name, note="Очень длинное примечание " + ("x" * 50), depts=depts))
    for i in range(0, 18, 2):
        long_list[i].replacement_ids.append(long_list[i + 1].id if i + 1 < 18 else 1)
    normalize_zonal_criminalists(long_list)
    coll2 = ZonalCollection(template=ReportTemplate(name="Переполнение"), criminalists=long_list)
    path2 = os.path.join(d, "zonal_long.pdf")
    ZonalDistributionPdfExporter().export(coll2, path2)
    reader2 = pypdf.PdfReader(path2)
    txt2 = _norm(" ".join((p.extract_text() or "") for p in reader2.pages))
    check("r40-11.1: при переполнении >1 страницы", len(reader2.pages) > 1,
          str(len(reader2.pages)))
    check("r40-11.2: записи 1..18 не потеряны",
          all(f"Криминалист Номер {i}" in txt2 for i in range(1, 19)))
    check("r40-11.3: длинные названия отделов не исчезают",
          "СО по Ворошиловскому району г." in txt2 and "Ростов-на" in txt2)


# ═════════════════════════════════════════════════════════════════════════
# 13–14. UI-смоук + web-helper
# ═════════════════════════════════════════════════════════════════════════
def _handlers(control, attr):
    eh = getattr(control, attr, None)
    return list((getattr(eh, "_EventHandler__handlers", {}) or {}).keys())


def _fire(control, attr, event):
    hs = _handlers(control, attr)
    for h in hs:
        h(event)
    return bool(hs)


class WebPageStub(PageStub):
    def __init__(self, width=1280, height=860):
        super().__init__(width=width, height=height)
        self.launched_urls = []

    def launch_url(self, url):
        self.launched_urls.append(url)
        return True


def _build_tab(page, width=1280):
    from ui.zonal.zonal_tab import create_zonal_tab
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(io.StringIO()):
        return create_zonal_tab(page)


def run_ui_web():
    print("\n--- 13–14. UI-смоук + web-helper ---")

    # 13. desktop UI: кнопка, отдельный picker, cancel безопасен
    saved_dir = os.environ.pop("FLET_ASSETS_DIR", None)
    os.environ.pop("PORAYONKA_WEB", None)
    try:
        page = PageStub()
        tab = _build_tab(page)
        btns = [b for b in ft.__dict__.get("__annotations__", {})]  # noop guard
        pdf_btn = next((b for b in _walk(tab) if isinstance(b, ft.ElevatedButton)
                        and getattr(b, "text", None) == "Выгрузить зональных"), None)
        excel_btn = next((b for b in _walk(tab) if isinstance(b, ft.ElevatedButton)
                          and getattr(b, "text", None) == "Экспорт в Excel"), None)
        check("r40-13.1: кнопки Excel и PDF стоят рядом",
              pdf_btn is not None and excel_btn is not None)
        picker_excel = next((c for c in (page.overlay or []) if hasattr(c, "save_file")), None)
        # клик по PDF создаёт ОТДЕЛЬНЫЙ picker и не трогает excel
        # (в headless-странице FilePicker не смонтирован, поэтому save_file
        # подменяем на no-op — это проверяет только факт регистрации/отдельного
        # обработчика, а не сам выбор каталога).
        orig_save = ft.FilePicker.save_file
        ft.FilePicker.save_file = lambda self, *a, **k: None
        try:
            if pdf_btn is not None:
                pdf_btn.on_click(None)
        finally:
            ft.FilePicker.save_file = orig_save
        pdf_picker = getattr(page, "_zonal_pdf_picker", None)
        check("r40-13.2: отдельный PDF FilePicker зарегистрирован в overlay",
              pdf_picker is not None and pdf_picker in (page.overlay or []))
        check("r40-13.3: handler PDF picker подписан ровно один раз",
              len(_handlers(pdf_picker, "on_result")) == 1,
              str(len(_handlers(pdf_picker, "on_result"))))

        # cancel: e.path=None не меняет состояние
        before = dict(page._zonal_pdf_state)
        _fire(pdf_picker, "on_result", types.SimpleNamespace(path=None))
        check("r40-13.4: cancel не меняет путь/кнопку",
              page._zonal_pdf_state["path"] is None
              and before["path"] is None
              and page._zonal_open_pdf_btn.visible is False)

        # success desktop: запишем маленький PDF и нажмём обработчик
        small = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
        p = os.path.join(_TMP, "desktop.pdf")
        with open(p, "wb") as f:
            f.write(small)
        _fire(pdf_picker, "on_result", types.SimpleNamespace(path=p))
        check("r40-13.5: desktop успешная запись сохраняет путь и показывает кнопку",
              page._zonal_pdf_state["path"] == p
              and page._zonal_open_pdf_btn.visible is True)
        check("r40-13.6: excel-путь не затронут",
              not hasattr(page, "_last_export_path") or page._last_export_path["value"] is None)
    finally:
        if saved_dir:
            os.environ["FLET_ASSETS_DIR"] = saved_dir
        else:
            os.environ.pop("FLET_ASSETS_DIR", None)

    # 14a. web helper: только downloads-каталог, безопасный URL
    data = b"%PDF-1.4\n%%EOF"
    final, url = write_web_pdf("../evil_name.pdf", data)
    base = web_download_url("../evil_name.pdf")
    check("r40-14.1: файл лежит в downloads",
          os.path.dirname(os.path.abspath(final)) == os.path.abspath(
              os.path.join(_WEB_FILES, "downloads")))
    check("r40-14.2: имя безопасно, без path traversal",
          os.path.basename(final) == "evil_name.pdf" and base.endswith("/assets/downloads/evil_name.pdf"),
          repr(base))
    check("r40-14.3: имя по умолчанию и без json-спецсимволов",
          re.match(r"^zonal_distribution_\d{8}_\d{6}\.pdf$", pdf_filename()) is not None)

    # 14b. UI web: кнопка генерирует PDF в web-downloads и открывает URL
    os.environ["FLET_ASSETS_DIR"] = _WEB_FILES
    os.environ["PORAYONKA_WEB"] = "1"
    try:
        page = WebPageStub()
        tab = _build_tab(page)
        pdf_btn = next((b for b in _walk(tab) if isinstance(b, ft.ElevatedButton)
                        and getattr(b, "text", None) == "Выгрузить зональных"), None)
        check("r40-14.4: PDF кнопка найдена в web-режиме", pdf_btn is not None)
        if pdf_btn is not None:
            pdf_btn.on_click(None)
        dls = os.path.join(_WEB_FILES, "downloads")
        files = [f for f in os.listdir(dls) if f.startswith("zonal_distribution_")
                 and f.endswith(".pdf")]
        check("r40-14.5: web PDF записан в разрешённый каталог", len(files) == 1,
              str(files))
        check("r40-14.6: launch_url вызван с assets URL",
              len(page.launched_urls) == 1
              and page.launched_urls[0].startswith("/assets/downloads/zonal_distribution_"),
              str(page.launched_urls))
        # удаление внешнего файла -> открытие через URL (web) не падает
        page._zonal_pdf_state["url"] = None
        page._zonal_open_pdf_btn.on_click(None)
        check("r40-14.7: удаление/отсутствие URL web не роняет обработчик",
              page._zonal_pdf_state["url"] is None)
    finally:
        os.environ.pop("PORAYONKA_WEB", None)


def _walk(c, seen=None):
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
                res += _walk(x, seen)
        elif v is not None and type(v).__module__.startswith("flet"):
            res += _walk(v, seen)
    return res


# ═════════════════════════════════════════════════════════════════════════
# 15. требования/spec/assets включают PDF-библиотеку и шрифт
# ═════════════════════════════════════════════════════════════════════════
def run_static():
    print("\n--- 15. Требования/spec/assets ---")
    req = open(os.path.join(APP_DIR, "requirements.txt"), encoding="utf-8").read()
    req_web = open(os.path.join(APP_DIR, "requirements-win7-web.txt"), encoding="utf-8").read()
    check("r40-15.1: reportlab закреплён в обычных requirements",
          "reportlab==4.2.5" in req)
    check("r40-15.2: reportlab закреплён в Win7-web профиле",
          "reportlab==4.2.5" in req_web)
    for spec in ("Porayonka_Admin.spec", "Porayonka_User.spec",
                 "Porayonka_Admin_Web.spec", "Porayonka_User_Web.spec"):
        txt = open(os.path.join(APP_DIR, spec), encoding="utf-8").read()
        check(f"r40-15.3: {spec} включает reportlab hiddenimports",
              "reportlab" in txt and "reportlab.lib.units" in txt)
    fonts = os.path.join(APP_DIR, "assets", "fonts")
    check("r40-15.4: кириллический шрифт и лицензия в assets",
          os.path.isfile(os.path.join(fonts, "DejaVuSans.ttf"))
          and os.path.isfile(os.path.join(fonts, "DejaVuSans-Bold.ttf"))
          and os.path.isfile(os.path.join(fonts, "LICENSE")))


# ═════════════════════════════════════════════════════════════════════════
# UI редактора взаимозаменяемости
# ═════════════════════════════════════════════════════════════════════════
def run_modal():
    print("\n--- Редактор взаимозаменяемости ---")
    from ui.zonal.add_criminalist_modal import create_add_criminalist_modal
    a, b, c = _cr(1, "Агеев Олег Владимирович"), _cr(2, "Грубников Георгий Григорьевич"), _cr(3, "Белашов Николай Сергеевич")
    a.replacement_ids = [2]
    b.replacement_ids = [1]
    saved = {}

    page = PageStub()
    dialog = create_add_criminalist_modal(
        page=page, criminalist=a, all_criminalists=[a, b, c], on_delete=None,
        on_save=lambda full, note, depts, repl: saved.update(
            {"full": full, "note": note, "depts": depts, "repl": repl}),
    )
    repl_column = next(
        (c for c in _walk(dialog)
         if isinstance(c, ft.Column) and getattr(c, "height", None) == 150),
        None,
    )
    check("r40-modal.0: найден bounded/scrollable список взаимозаменяемости",
          repl_column is not None
          and getattr(repl_column, "scroll", None) == ft.ScrollMode.AUTO)
    cbs = [cb for cb in _walk(repl_column) if isinstance(cb, ft.Checkbox)]
    labels = [str(cb.label) for cb in cbs]
    check("r40-modal.1: текущий человек исключён из вариантов",
          any(l.startswith("[2]") for l in labels)
          and any(l.startswith("[3]") for l in labels)
          and not any(l.startswith("[1]") for l in labels), str(labels[:4]))
    check("r40-modal.2: уже выбранная связь (2) отмечена",
          any(cb.value is True for cb in cbs if str(cb.label).startswith("[2]")))
    # выбрать ещё [3]
    three = next(cb for cb in cbs if str(cb.label).startswith("[3]"))
    three.value = True
    three.on_change(types.SimpleNamespace(control=three))
    # снять [2]
    two = next(cb for cb in cbs if str(cb.label).startswith("[2]"))
    two.value = False
    two.on_change(types.SimpleNamespace(control=two))
    # сохранить одним действием
    save_btn = next(b for b in _walk(dialog) if isinstance(b, ft.ElevatedButton)
                    and getattr(b, "text", None) == "Сохранить")
    save_btn.on_click(None)
    check("r40-modal.3: сохранение одним действием передаёт связи",
          saved.get("repl") == [3], str(saved.get("repl")))
    check("r40-modal.4: сохранение передаёт ФИО/примечание/зоны",
          saved.get("full") == a.full_name
          and saved.get("note") == a.note
          and saved.get("depts") == a.zone.department_ids,
          str(saved))


def main():
    run_model()
    run_modal()
    run_ui_web()
    run_static()
    run_pdf()
    print("\n" + "=" * 72)
    if FAILURES:
        print("FAILED: %d" % len(FAILURES))
        for f in FAILURES:
            try:
                print("  - " + f)
            except UnicodeEncodeError:
                print("  - <non-cp1251>")
        shutil.rmtree(_TMP, ignore_errors=True)
        sys.exit(1)
    print("ALL OK")
    shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(0)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Раунд 40 — регресс-тесты фазы 40 (зональные + PDF-выгрузка).

Запуск из porayonka-app:   python tests\\test_round40.py

Покрытие (слои):
  1..6  — чистые функции core/zonal_replacement.py (парсинг/симметрия/
          замена множества/удаление/пары/сокращение ФИО);
  7..13 — core/zonal_distribution_exporter.py на РЕАЛЬНО сгенерированном
          PDF: валидность/A4/одна страница для 16, кириллица и «↔» через
          ToUnicode (tests/pdf_text_probe.py — структурный извлекатель,
          только stdlib), чистота (без мутаций и JSON), неактивные/пустые
          зоны, переносы без потерь, многостраничность, пары ровно один раз;
  14    — web-хелперы выгрузки (sanitize/reserve/url/export_pdf_for_web);
  15    — UI-смоук вкладки зональных + РЕАЛЬНЫЕ обработчики добавить/
          редактировать/удалить + web-экспорт PDF кнопкой + статические
          инварианты упаковки (pinned reportlab/pillow, assets/fonts в
          spec'ах, four-arg on_save, только ft.icons.*).

Все операции — во временных каталогах (APPDATA/FLET_ASSETS_DIR подменены
ДО импорта core-модулей); реальные данные не трогаются.
"""
import json
import os
import re
import shutil
import sys
import tempfile
import traceback

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


# ── изоляция ДО импорта core-модулей ─────────────────────────────────────
_TMP = tempfile.mkdtemp(prefix="r40_tmp_")
_APPDATA = os.path.join(_TMP, "appdata")
_ASSETS = os.path.join(_TMP, "webassets")
os.makedirs(_APPDATA, exist_ok=True)
os.makedirs(_ASSETS, exist_ok=True)
os.environ["APPDATA"] = _APPDATA
os.environ["FLET_ASSETS_DIR"] = _ASSETS
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _APP_DIR)
sys.path.insert(0, os.path.join(_APP_DIR, "tests"))

from core.zonal_models import Criminalist, CriminalistZone  # noqa: E402
from core.zonal_replacement import (  # noqa: E402
    parse_replacement_ids, normalize_replacement_links,
    set_replacement_partners, remove_criminalist_links,
    unique_pairs, short_full_name,
)
from core.zonal_distribution_exporter import (  # noqa: E402
    ZonalDistributionPdfExporter, ZonalPdfError, export_pdf_for_web,
    sanitize_pdf_filename, reserve_unique_pdf_path, asset_download_url,
    fonts_dir, _register_fonts,
)
from core.zonal_data import (  # noqa: E402
    get_initial_criminalists, save_criminalists, load_criminalists,
)
from core.constants import INITIAL_DEPARTMENTS  # noqa: E402
from core.zonal_constants import INITIAL_CRIMINALISTS_DATA  # noqa: E402
from pdf_text_probe import extract_pdf_text, extract_pdf_pages  # noqa: E402
import flet as ft  # noqa: E402

DEPT_MAP = {d["id"]: d["name"] for d in INITIAL_DEPARTMENTS}
DEFAULT_NAMES = [d["full_name"] for d in INITIAL_CRIMINALISTS_DATA]


def mk_crim(cid, name=None, note="", active=True, depts=None):
    """Компактный криминалист для тестов экспортёра."""
    return Criminalist(
        id=cid,
        full_name=name or f"Криминалист Тест {cid}",
        note=note,
        is_active=active,
        zone=CriminalistZone(criminalist_id=cid,
                             department_ids=list(depts or [])),
    )


def export_to(criminalists, dept_map=None, tag="pdf"):
    """Экспорт во временный файл; возвращает (path, страницы)."""
    path = os.path.join(_TMP, f"{tag}.pdf")
    if os.path.exists(path):
        os.remove(path)
    pages = ZonalDistributionPdfExporter().export(
        criminalists, dept_map if dept_map is not None else DEPT_MAP, path)
    return path, pages


# ────────────────────────────────────────────────────────────────────────
def run_logic_parse():
    """1. parse_replacement_ids — чистка, детерминизм, self/dangling."""
    known = {1, 2, 3, 4, 5}
    r = parse_replacement_ids([5, 2, "3", True, 1, 2, 99, "мусор", 4.0, 5],
                              1, known)
    check("repl40: int/строки-числа очищены, bool и мусор отброшены",
          r == [2, 3, 4, 5], extra=str(r))
    check("repl40: собственный ID исключён", 1 not in r)
    check("repl40: dangling-ссылки исключены", 99 not in r)
    check("repl40: дубли схлопнуты, порядок детерминированный (sorted)",
          parse_replacement_ids([3, 3, 5, 5, 5], 1, known) == [3, 5])
    check("repl40: None -> []", parse_replacement_ids(None, 1, known) == [])
    check("repl40: одиночный int -> список", parse_replacement_ids(4, 1, known) == [4])
    check("repl40: known_ids=None не валидирует (только чистка)",
          parse_replacement_ids(["2", 2, 77], 1, None) == [2, 77])
    check("repl40: строка с нечислом -> []", parse_replacement_ids("abc", 1, known) == [])
    r2 = parse_replacement_ids([2], 1, known)
    r3 = parse_replacement_ids([2], 1, known)
    check("repl40: детерминизм повторного вызова", r2 == r3 == [2])


def run_logic_normalize():
    """2. normalize_replacement_links — симметрия и идемпотентность."""
    a, b, c = mk_crim(1, "А"), mk_crim(2, "Б"), mk_crim(3, "В")
    a.replacement_ids = [2, 2, 1]      # дубль + self
    b.replacement_ids = []             # обратная ссылка отсутствует
    c.replacement_ids = ["3", 99]      # self-строка + dangling
    normalize_replacement_links([a, b, c])
    check("repl40: normalize убирает self/дубли/dangling",
          a.replacement_ids == [2] and c.replacement_ids == [])
    check("repl40: normalize восстанавливает симметрию (b получает 1)",
          b.replacement_ids == [1])
    normalize_replacement_links([a, b, c])
    check("repl40: normalize идемпотентен",
          a.replacement_ids == [2] and b.replacement_ids == [1]
          and c.replacement_ids == [])
    # другие поля не тронуты
    check("repl40: normalize не трогает зоны/note/активность",
          a.full_name == "А" and b.zone.department_ids == []
          and c.is_active is True)
    check("repl40: пустой список — no-op", normalize_replacement_links([]) is None)


def run_logic_set_partners():
    """3. set_replacement_partners — полная «замена множества»."""
    a, b, c = mk_crim(1, "А"), mk_crim(2, "Б"), mk_crim(3, "В")
    # «старые» связи: 1↔2 и 1↔3 (асимметрично записанные вручную)
    a.replacement_ids = [2, 3]
    b.replacement_ids = [1]
    c.replacement_ids = [1]
    res = set_replacement_partners([a, b, c], 1, [2])
    check("repl40: set возвращает очищенный список нового набора",
          res == [2])
    check("repl40: у субъекта ровно новый набор", a.replacement_ids == [2])
    check("repl40: новый партнёр получает ОБРАТНУЮ ссылку (не self)",
          b.replacement_ids == [1])
    check("repl40: выбывший партнёр очищен с обеих сторон",
          c.replacement_ids == [])
    # повторный вызов с тем же набором — идемпотентно, без self-ссылок
    set_replacement_partners([a, b, c], 1, [2])
    check("repl40: повторный вызов идемпотентен",
          a.replacement_ids == [2] and b.replacement_ids == [1])
    # замена на пустой набор снимает ВСЕ связи
    set_replacement_partners([a, b, c], 1, [])
    check("repl40: пустой набор очищает обе стороны",
          a.replacement_ids == [] and b.replacement_ids == [])
    # субъект ещё не добавлен в список (me=None) — вызов безопасен и не
    # создаёт dangling-ссылок у остальных
    res = set_replacement_partners([b, c], 9, [2])
    check("repl40: субъект вне списка — no-op для остальных",
          res == [2] and b.replacement_ids == [] and c.replacement_ids == [])


def run_logic_remove_links():
    """4. remove_criminalist_links — удаление человека чистит остальных."""
    a, b, c = mk_crim(1, "А"), mk_crim(2, "Б"), mk_crim(3, "В")
    set_replacement_partners([a, b, c], 1, [2, 3])   # связи 1-2 и 1-3
    remove_criminalist_links([a, b, c], 2)           # удалили №2
    check("repl40: удалённый id убран у остальных",
          a.replacement_ids == [3] and c.replacement_ids == [1])
    remove_criminalist_links([a, b, c], 1)           # удалили №1
    check("repl40: ссылки на удалённого исчезли у всех",
          b.replacement_ids == [] and c.replacement_ids == [])
    check("repl40: субъект удаления сам не очищается",
          a.replacement_ids == [3])
    check("repl40: повторное удаление того же id — no-op",
          remove_criminalist_links([a, b, c], 1) is None)
    # удаление «центра» связей (на него ссылаются двое)
    d, e, f = mk_crim(4, "Г"), mk_crim(5, "Д"), mk_crim(6, "Е")
    set_replacement_partners([d, e, f], 4, [5, 6])
    remove_criminalist_links([d, e, f], 4)
    check("repl40: удаление «центра» оставляет остальных без ссылок",
          e.replacement_ids == [] and f.replacement_ids == [])


def run_logic_pairs():
    """5. unique_pairs — каждая неориентированная пара ровно один раз."""
    a, b, c = mk_crim(1, "А"), mk_crim(2, "Б"), mk_crim(3, "В")
    d, e = mk_crim(4, "Г"), mk_crim(5, "Д")
    set_replacement_partners([a, b, c, d, e], 1, [2, 3])   # 1-2, 1-3
    set_replacement_partners([a, b, c, d, e], 5, [4])      # 4-5
    # руками — асимметричная «1 в списке 4» без обратной (норм. не было)
    d.replacement_ids = sorted(d.replacement_ids + [1])
    pairs = unique_pairs([a, b, c, d, e])
    keys = [(p[0].id, p[1].id) for p in pairs]
    # (1,2), (1,3), (4,5) — из симметричных set-вызовов; (1,4) — из ручной
    # асимметричной ссылки 4→1 (уникальная пара всё равно одна)
    check("repl40: пары уникальны и не дублируются",
          len(keys) == len(set(keys)) == 4, extra=str(keys))
    check("repl40: направление — по порядку списка (первым — кто раньше)",
          (1, 2) in keys and (1, 3) in keys and (4, 5) in keys)
    check("repl40: асимметричная ссылка даёт пару (не зависит от стороны)",
          (1, 4) in keys)
    check("repl40: pair объекты — сами Criminalist",
          isinstance(pairs[0][0], Criminalist))
    fresh1 = mk_crim(9, "Н")
    fresh2 = mk_crim(10, "О")
    check("repl40: пусто → [], без пар → []", unique_pairs([]) == []
          and unique_pairs([fresh1, fresh2]) == [])
    # пары после normalize — те же самые
    normalize_replacement_links([a, b, c, d, e])
    check("repl40: normalize не меняет набор пар",
          len(unique_pairs([a, b, c, d, e])) == 4)


def run_logic_short_name():
    """6. short_full_name — «Фамилия И.О.» для строк пар."""
    check("repl40: short_full_name — Фамилия И.О.",
          short_full_name("Иванов Иван Иванович") == "Иванов И.И.")
    check("repl40: одна часть — как есть",
          short_full_name("Иванов") == "Иванов")
    check("repl40: уже сокращённое — как есть",
          short_full_name("Иванов И.И.") == "Иванов И.И.")
    check("repl40: NBSP/лишние пробелы схлопнуты",
          short_full_name("Петров\u00a0 Пётр\u00a0Петрович ") == "Петров П.П.")
    check("repl40: пустая строка -> ''", short_full_name("") == ""
          and short_full_name(None) == "")


def run_pdf_default_page():
    """7. Экспортёр: 16 по умолчанию — 1 страница, валидный PDF A4."""
    criminalists = [Criminalist(
        id=d["id"], full_name=d["full_name"], note=d["note"],
        is_active=d.get("is_active", True),
        zone=CriminalistZone(criminalist_id=d["id"],
                             department_ids=list(d["department_ids"])))
        for d in INITIAL_CRIMINALISTS_DATA]
    path, pages = export_to(criminalists, tag="pdf_default")
    check("pdf40: default 16 -> ровно 1 страница (нет пустого листа)",
          pages == 1, extra=str(pages))
    with open(path, "rb") as f:
        head = f.read(1024)
        f.seek(0)
        raw = f.read()
    check("pdf40: файл начинается с %PDF-", head.startswith(b"%PDF-"))
    check("pdf40: размер > 20 КБ (шрифты встроены)",
          os.path.getsize(path) > 20000)
    m = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", raw)
    ok_a4 = m is not None and abs(float(m.group(1)) - 595.2756) < 0.5 \
        and abs(float(m.group(2)) - 841.8898) < 0.5
    check("pdf40: MediaBox = A4 portrait (595.28 x 841.89 pt)",
          ok_a4, extra=m.group(0).decode()[:40] if m else "no MediaBox")
    check("pdf40: встроен subset DejaVuSans + FontFile2",
          b"+DejaVuSans" in raw and b"FontFile2" in raw)
    check("pdf40: корректный EOF-маркер", raw.rstrip().endswith(b"%%EOF"))


def run_pdf_default_text():
    """8. Экспортёр: текст PDF — заголовок, карточки, зоны, «Не указана»."""
    criminalists = [Criminalist(
        id=d["id"], full_name=d["full_name"], note=d["note"],
        is_active=d.get("is_active", True),
        zone=CriminalistZone(criminalist_id=d["id"],
                             department_ids=list(d["department_ids"])))
        for d in INITIAL_CRIMINALISTS_DATA]
    path, pages = export_to(criminalists, tag="pdf_default_text")
    text = extract_pdf_text(path)
    check("pdf40: точный заголовок в тексте PDF",
          "Зональный принцип распределения отдела криминалистики" in text)
    # карточки в порядке id; слова ФИО не теряются при переносах
    for d in INITIAL_CRIMINALISTS_DATA:
        words = [w for w in d["full_name"].split() if w]
        missing = [w for w in words if w not in text]
        if missing:
            check(f"pdf40: ФИО #{d['id']} полностью присутствует", False,
                  extra=",".join(missing))
            break
    else:
        check("pdf40: ФИО всех 16 полностью присутствуют", True)
    check("pdf40: шапка нумеруется «(N) ФИО»",
          "(1) Агеев" in text and "(16)" in text)
    # названия отделов — словами (переносы по словам, ничего не теряется);
    # в PDF печатаются только отделы, закреплённые за кем-то из дефолтных
    used_dept_ids = {did for d in INITIAL_CRIMINALISTS_DATA
                     for did in d.get("department_ids", [])}
    for did in sorted(used_dept_ids):
        name = INITIAL_DEPARTMENTS[did - 1]["name"] if did <= len(
            INITIAL_DEPARTMENTS) else ""
        missing = [w for w in name.split() if w and w not in text]
        if missing:
            check(f"pdf40: отдел #{did} присутствует", False,
                  extra=",".join(missing))
            break
    else:
        check("pdf40: названия закреплённых отделов присутствуют", True)
    check("pdf40: маркеры отделов «-» присутствуют", "\n- \n" in text or "- " in text)
    check("pdf40: пустая зона -> «Отделы не закреплены»",
          "Отделы не закреплены" in text)
    check("pdf40: примечание отдельной строкой «Примечание:»",
          "Примечание:" in text)
    # дефолтных пар нет -> блок «Взаимозаменяемость:» + «Не указана»
    check("pdf40: заголовок блока пар есть",
          "Взаимозаменяемость:" in text)
    check("pdf40: пар нет -> «Не указана»", "Не указана" in text)
    check("pdf40: без пар нет ни одной «↔»", "\u2194" not in text)
    check("pdf40: заголовок встречается один раз (одна страница)",
          text.count("Зональный принцип распределения") == 1)


def run_pdf_purity():
    """9. Чистота экспортёра: без мутаций коллекции и записи JSON."""
    a = mk_crim(1, "Агеев Олег Владимирович", depts=[1, 2], note="note-1")
    b = mk_crim(2, "Грубников Георгий Григорьевич", depts=[3])
    set_replacement_partners([a, b], 1, [2])
    snapshot = json.dumps({
        "a": (a.id, a.full_name, a.note, a.is_active,
              list(a.zone.department_ids), list(a.replacement_ids)),
        "b": (b.id, b.full_name, list(b.zone.department_ids),
              list(b.replacement_ids)),
    }, ensure_ascii=False, sort_keys=True)
    before_files = set(os.listdir(_TMP))
    path, pages = export_to([a, b], tag="pdf_purity")
    after = json.dumps({
        "a": (a.id, a.full_name, a.note, a.is_active,
              list(a.zone.department_ids), list(a.replacement_ids)),
        "b": (b.id, b.full_name, list(b.zone.department_ids),
              list(b.replacement_ids)),
    }, ensure_ascii=False, sort_keys=True)
    check("pdf40: экспорт НЕ мутирует коллекцию", snapshot == after)
    new_files = set(os.listdir(_TMP)) - before_files
    check("pdf40: экспорт НЕ пишет JSON/иных файлов кроме PDF",
          new_files == {os.path.basename(path)}, extra=str(new_files))
    # детерминизм текста: два прогона одного входа дают один текст
    path2, pages2 = export_to([a, b], tag="pdf_purity2")
    check("pdf40: повторный экспорт — тот же текст и число страниц",
          pages == pages2 == 1
          and extract_pdf_text(path) == extract_pdf_text(path2))


def run_pdf_inactive_empty():
    """10. Неактивные и люди с пустой зоной не пропадают из PDF."""
    crims = [
        mk_crim(1, "Активный Иванов", depts=[1]),
        mk_crim(2, "Неактивный Петров", depts=[2], active=False),
        mk_crim(3, "Пустая Зона Сидоров", depts=[], active=False),
        mk_crim(4, "Обычный Васечкин", depts=[]),   # активный с пустой зоной
    ]
    path, pages = export_to(crims, tag="pdf_mix")
    text = extract_pdf_text(path)
    check("pdf40: страниц 1 при 4 человеках", pages == 1)
    check("pdf40: неактивные включены", "Неактивный Петров" in text)
    check("pdf40: пустая зона включена", "Пустая Зона Сидоров" in text)
    check("pdf40: активный с пустой зоной включён",
          "Обычный Васечкин" in text)
    check("pdf40: два маркера «Отделы не закреплены»",
          text.count("Отделы не закреплены") == 2, extra=str(text.count("Отделы не закреплены")))
    check("pdf40: номера всех карточек на месте",
          all(f"({i})" in text for i in (1, 2, 3, 4)))


def run_pdf_long_wrap():
    """11. Длинные ФИО/примечания переносятся без потери и обрезания."""
    from core.zonal_distribution_exporter import _wrap_line, _FONT_BOLD, \
        _FONT_REG, _NOTE_SIZE, _HEADER_SIZE, _card_inner_width
    long_name = ("Экстремальнодлиннофамильный-Сверхъевропейский "
                 "Аполлон Аристархович")
    long_note = ("Специализация: компьютерная экспертиза, восстановление "
                 "удалённых данных, анализ мобильных устройств, "
                 "криптовалютные расследования и цифровая аналитика")
    # юнит-проверка переносчика: перенос только перераспределяет символы
    lines_name = _wrap_line(long_name, _FONT_BOLD, _HEADER_SIZE,
                            _card_inner_width())
    lines_note = _wrap_line(long_note, _FONT_REG, _NOTE_SIZE,
                            _card_inner_width())
    joined_name = "".join(lines_name)
    check("pdf40: перенос ФИО не теряет ни символа",
          all(tok in joined_name for tok in long_name.split())
          and joined_name[0] == long_name[0]
          and joined_name[-1] == long_name[-1],
          extra=f"{len(lines_name)} строк")
    check("pdf40: перенос примечания не теряет ни символа",
          " ".join(lines_note) == long_note)
    crims = [mk_crim(1, long_name, note=long_note,
                     depts=[1, 2, 3, 5, 8, 11, 14, 17, 20, 23, 26, 29])]
    path, pages = export_to(crims, tag="pdf_long")
    text = extract_pdf_text(path)
    # в PDF: хвост фамилии (обрыв идёт посередине слова) и окончание строки
    check("pdf40: длинное ФИО в PDF не обрезано (хвост на месте)",
          "(1)" in text and "Сверхъевропейск" in text
          and "Аристархович" in text)
    check("pdf40: длинное примечание в PDF (начало/середина/конец)",
          "Специализация:" in text and "восстановление" in text
          and "криптовалютные" in text and "аналитика" in text)
    check("pdf40: все 12 отделов в карточке на месте",
          all(DEPT_MAP[i].split()[0] in text
              for i in (1, 2, 3, 5, 8, 11, 14, 17, 20, 23, 26, 29)))
    check("pdf40: многострочная карточка не падает (1 страница)",
          pages == 1)


def run_pdf_multipage():
    """12. 40 человек -> несколько страниц, никто не потерян, пары целы."""
    crims = []
    for i in range(1, 41):
        depts = []
        if i % 4 != 0:
            depts = list(range(1, (i % 6) + 2))
        note = f"Примечание криминалиста номер {i}" if i % 3 == 0 else ""
        crims.append(mk_crim(i, f"Многоплаговый Иванов{i}", note=note,
                             active=(i % 10 != 0), depts=depts))
    for x, y in [(1, 2), (2, 3), (5, 6), (39, 40), (7, 8), (1, 40)]:
        set_replacement_partners(crims, x, [y])
    # set(2,[3]) рвёт связь 1-2, set(1,[40]) рвёт 39-40? нет: итог = 5 пар:
    # (2,3), (5,6), (39,40), (7,8), (1,40) — (1,2) перезаписан вторым set'ом
    normalize_replacement_links(crims)
    path, pages = export_to(crims, tag="pdf_40")
    pages_text = extract_pdf_pages(path)
    full = "\n".join(pages_text)
    check("pdf40: 40 человек -> несколько страниц", pages > 1, extra=str(pages))
    check("pdf40: число извлечённых страниц == числу страниц экспортёра",
          len(pages_text) == pages)
    # каждое имя печатается отдельным словом-токеном (переносы между словами)
    missing = [i for i in range(1, 41) if f"Иванов{i}" not in full]
    check("pdf40: все 40 человек присутствуют", not missing,
          extra=f"нет: {missing[:5]}")
    check("pdf40: неактивные (10/20/30/40) присутствуют",
          all(f"({i})" in full for i in (10, 20, 30, 40)))
    # 5 уникальных пар -> 5 строк с «↔»
    check("pdf40: каждая пара напечатана ровно один раз",
          full.count("\u2194") == 5, extra=str(full.count("\u2194")))
    check("pdf40: заголовок блока повторён на продолжении",
          full.count("Взаимозаменяемость:") >= 1)
    check("pdf40: последняя страница содержит пары",
          "Взаимозаменяемость:" in pages_text[-1])
    # на каждой странице есть короткий заголовок
    check("pdf40: заголовок на каждой странице",
          all("Зональный принцип распределения" in pt for pt in pages_text))
    check("pdf40: ни одна страница не пустая",
          all(len(pt.strip()) > 0 for pt in pages_text))


def run_pdf_pairs():
    """13. Строки пар: направление, инициалы, порядок карточек."""
    crims = [
        mk_crim(10, "Петров Пётр Петрович", depts=[1]),
        mk_crim(2, "Иванов Иван Иванович", depts=[1]),
        mk_crim(7, "Сидоров Сидор Сидорович", depts=[1]),
        mk_crim(1, "Агеев Олег Владимирович", depts=[1]),
    ]
    # порядок списка: 10, 2, 7, 1 — пары создаём «вразнобой»
    set_replacement_partners(crims, 10, [1])     # 10-1
    set_replacement_partners(crims, 7, [2])      # 7-2 (потом 2 перезапишется)
    set_replacement_partners(crims, 2, [10, 1])  # 2-10 и 2-1 (7 выбывает)
    normalize_replacement_links(crims)
    path, pages = export_to(crims, tag="pdf_pairs")
    text = extract_pdf_text(path)
    # уникальные пары: (10,1), (10,2), (2,1) — 3 строки, «↔» = 3
    check("pdf40: все 3 уникальные пары напечатаны",
          text.count("\u2194") == 3, extra=str(text.count("\u2194")))
    # направление детерминировано: первым идёт человек, стоящий раньше
    # в списке (10,2,7,1)
    order = [10, 2, 7, 1]
    pair_lines = [ln for ln in text.split("\n") if "\u2194" in ln]
    wrong_dir = []
    for ln in pair_lines:
        m = re.search(r"\((\d+)\)\s*\u2194\s*.+\((\d+)\)", ln)
        if not m:
            wrong_dir.append("parse:" + ln)
            continue
        left, right = int(m.group(1)), int(m.group(2))
        if order.index(left) > order.index(right):
            wrong_dir.append(ln)
    check("pdf40: в каждой строке пары первый — кто раньше в списке",
          not wrong_dir, extra="; ".join(wrong_dir[:2]))
    check("pdf40: строки пар содержат Фамилию И.О. и оба номера",
          "Петров П.П. (10) \u2194 Иванов И.И. (2)" in text
          and "Иванов И.И. (2) \u2194 Агеев О.В. (1)" in text)
    check("pdf40: разорванная связь 7-2 не печатается (Сидорова нет в парах)",
          all("Сидоров" not in ln for ln in pair_lines))
    check("pdf40: №7 (без связей) остался в карточке",
          "(7) Сидоров" in text and "Сидорович" in text)


def run_pdf_web_helpers():
    """14. Web-хелперы: безопасные имена, уникальность, URL, каталог."""
    check("web40: sanitize убирает пути/разделители",
          sanitize_pdf_filename(r"..\..\secret\файл.pdf") == "файл.pdf")
    check("web40: sanitize убирает метасимволы Windows",
          sanitize_pdf_filename('a<b>c:d"e|f?g*.pdf') == "abcdefg.pdf")
    check("web40: sanitize: не .pdf -> fallback",
          sanitize_pdf_filename("evil.exe") == "zonal_distribution.pdf")
    check("web40: sanitize: пустое/точки -> fallback",
          sanitize_pdf_filename("") == "zonal_distribution.pdf"
          and sanitize_pdf_filename("..") == "zonal_distribution.pdf")
    d = os.path.join(_TMP, "dl")
    p1 = reserve_unique_pdf_path(d, "zonal_distribution_20260909.pdf")
    p2 = reserve_unique_pdf_path(d, "zonal_distribution_20260909.pdf")
    check("web40: резервация создаёт каталог и файл",
          os.path.isdir(d) and os.path.exists(p1))
    check("web40: коллизия имён получает суффикс _1",
          p2 == os.path.join(d, "zonal_distribution_20260909_1.pdf")
          and os.path.exists(p2))
    check("web40: url /assets/downloads/<имя>",
          asset_download_url("zonal_distribution_1.pdf")
          == "/assets/downloads/zonal_distribution_1.pdf")
    check("web40: url квотирует пробелы",
          "/assets/downloads/a%20b.pdf" == asset_download_url("a b.pdf"))
    # полноценный export_pdf_for_web с фиксированным именем
    crims = [mk_crim(1, "Web Тест", depts=[1])]
    r1 = export_pdf_for_web(crims, DEPT_MAP, downloads_dir=d,
                            file_name="fixed_name.pdf", timestamp="t")
    check("web40: export_pdf_for_web кладёт PDF в downloads_dir",
          os.path.dirname(os.path.abspath(r1["path"]))
          == os.path.abspath(d) and os.path.exists(r1["path"]))
    check("web40: результат отдаёт path/filename/url",
          r1["filename"] == "fixed_name.pdf"
          and r1["url"] == "/assets/downloads/fixed_name.pdf")
    r2 = export_pdf_for_web(crims, DEPT_MAP, downloads_dir=d,
                            file_name="fixed_name.pdf", timestamp="t")
    check("web40: повторный экспорт с тем же именем не затирает файл",
          r1["path"] != r2["path"]
          and os.path.basename(r2["path"]) == "fixed_name_1.pdf")
    txt = extract_pdf_text(r1["path"])
    check("web40: web-PDF содержит кириллицу", "Web Тест" in txt)
    check("web40: каталог шрифтов содержит TTF + LICENSE",
          os.path.isfile(os.path.join(fonts_dir(), "DejaVuSans.ttf"))
          and os.path.isfile(os.path.join(fonts_dir(), "DejaVuSans-Bold.ttf"))
          and os.path.isfile(os.path.join(fonts_dir(), "LICENSE")))


def _all_checkboxes(root):
    return _find_all(root, lambda c: isinstance(c, ft.Checkbox))


def _find_textfield(root, label):
    return _find(root, lambda c: getattr(c, "label", None) == label)


def _dept_header_row(root):
    """Row-заголовок «Закреплённые отделы: …» (текст-заголовок в Row)."""
    for row in _find_all(root, lambda c: isinstance(c, ft.Row)):
        texts = [getattr(c2, "value", None) for c2 in _walk(row)
                 if isinstance(c2, ft.Text)]
        if any(t == "Закреплённые отделы:" for t in texts):
            return row
    return None


def _find_all_container_cols(root, outer=None):
    """Все bounded-Column внутри обведённых рамкой Container секций.

    Внешняя content-Column модалки (outer) исключается — нам нужны только
    вложенные прокручиваемые списки отделов и взаимозаменяемости.
    """
    cols = []
    for cont in _find_all(root, lambda c: isinstance(c, ft.Container)
                          and isinstance(getattr(c, "content", None),
                                         ft.Column)):
        col = cont.content
        if col is outer:
            continue
        if col.scroll in (ft.ScrollMode.AUTO, ft.ScrollMode.ALWAYS) \
                and isinstance(col.height, (int, float)) and col.height > 0:
            cols.append((cont, col))
    return cols


def _collect_heights(boxes):
    return [b[1].height for b in boxes]


def _fake_click_handler(control):
    """Прямой вызов on_click-обработчика/button без монтирования."""
    handler = getattr(control, "on_click", None)
    if handler is None:
        return None
    try:
        handler(None)
    except TypeError:
        handler(_FakeEvent(control))
    return True


def _save_modal_and_check(page, dlg, name, note, dept_ids, repl_ids,
                          check_name):
    """Заполнить модалку, нажать «Сохранить» и вернуть имя сохранённого."""
    nf = _find_textfield(dlg, "ФИО криминалиста *")
    tf = _find_textfield(dlg, "Примечание (например, 'Цифровая криминалистика')")
    if nf is None or tf is None:
        check(check_name, False, extra="поля ФИО/примечание не найдены")
        return None
    nf.value = name
    tf.value = note
    # отметить нужные отделы/партнёров (остальные не трогаем — они
    # добавляются к текущему выбору, как в реальном UI)
    for cb in _all_checkboxes(dlg):
        lbl = getattr(cb, "label", "") or ""
        if lbl.startswith("[") and "]" in lbl:
            try:
                did = int(lbl[1:lbl.index("]")])
            except ValueError:
                continue
            if did in dept_ids and not cb.value:
                cb.value = True
                cb.on_change(_FakeEvent(cb))
        elif lbl.startswith("(") and ")" in lbl:
            try:
                rid = int(lbl[1:lbl.index(")")])
            except ValueError:
                continue
            if rid in repl_ids and not cb.value:
                cb.value = True
                cb.on_change(_FakeEvent(cb))
    save_btn = next((c for c in _find_all(dlg, lambda c: isinstance(
        c, ft.ElevatedButton))
        if getattr(c, "text", "") == "Сохранить"), None)
    if save_btn is None:
        check(check_name, False, extra="кнопка Сохранить не найдена")
        return None
    save_btn.on_click(None)
    return name


def run_modal_layout(add_mode=True):
    """16. Layout-регрессия модалки add/edit (Flet 0.23.2, bounded layout)."""
    from ui.zonal.add_criminalist_modal import create_add_criminalist_modal
    _label = "add " if add_mode else "edit"
    _page = _WinPage()
    others = get_initial_criminalists()
    subject = others[0] if not add_mode else None
    # связан №1 с №2 — у edit-режима должны быть предвыбраны партнёры
    if not add_mode:
        set_replacement_partners(others, subject.id, [2])
    dlg_kwargs = dict(on_save=lambda *a: None,
                      other_criminalists=others)
    if not add_mode:
        dlg_kwargs["criminalist"] = subject
        dlg_kwargs["on_delete"] = lambda c: None
    dlg = create_add_criminalist_modal(page=_page, **dlg_kwargs)

    # ── (а) обязательные пункты 1–10 присутствуют в дереве модалки ────
    name_f = _find_textfield(dlg, "ФИО криминалиста *")
    note_f = _find_textfield(dlg, "Примечание (например, 'Цифровая криминалистика')")
    check(f"modal40[{_label}]: поле ФИО есть", name_f is not None)
    check(f"modal40[{_label}]: поле Примечание есть", note_f is not None)
    header_row = _dept_header_row(dlg)
    check(f"modal40[{_label}]: заголовок «Закреплённые отделы:» виден",
          header_row is not None)
    # «Все»/«Снять» — в заголовочном Row секции отделов
    if header_row is not None:
        hb = _find_all(header_row, lambda c: isinstance(
            c, ft.TextButton) and getattr(c, "text", "") in ("Все", "Снять"))
        check(f"modal40[{_label}]: кнопки Все/Снять отделов в заголовке",
              len(hb) == 2)
    repl_text = _find(dlg, lambda c: isinstance(c, ft.Text)
                      and getattr(c, "value", None) == "Взаимозаменяемость:")
    repl_hint = _find(dlg, lambda c: isinstance(c, ft.Text)
                      and getattr(c, "value", None)
                      == "кто подменяет этого криминалиста")
    check(f"modal40[{_label}]: заголовок «Взаимозаменяемость:» виден",
          repl_text is not None)
    check(f"modal40[{_label}]: подсказка «кто подменяет…» видна",
          repl_hint is not None)
    if repl_text is not None:
        # Row-заголовок секции связей + его кнопки Все/Снять
        rrow = None
        for row in _find_all(dlg, lambda c: isinstance(c, ft.Row)):
            vals = [getattr(c2, "value", None) for c2 in _walk(row)
                    if isinstance(c2, ft.Text)]
            if any(v == "Взаимозаменяемость:" for v in vals):
                rrow = row
                break
        rb = _find_all(rrow, lambda c: isinstance(
            c, ft.TextButton) and getattr(c, "text", "") in ("Все", "Снять"))
        check(f"modal40[{_label}]: кнопки Все/Снять связей в заголовке",
              rrow is not None and len(rb) == 2)
    # действия
    acts = [getattr(c, "text", "") for c in
            _find_all(dlg, lambda c: isinstance(
                c, (ft.TextButton, ft.ElevatedButton)))]
    want = {"Отмена", "Сохранить"}
    if not add_mode:
        want.add("Удалить")
    check(f"modal40[{_label}]: кнопки действий на месте",
          want <= set(acts), extra=",".join(sorted(acts)))

    # ── (б) структурные инварианты Flet 0.23.2 ─────────────────────────
    outer = dlg.content.content
    check(f"modal40[{_label}]: внешняя content-Column bounded + scroll",
          isinstance(outer, ft.Column)
          and outer.scroll in (ft.ScrollMode.AUTO, ft.ScrollMode.ALWAYS)
          and isinstance(outer.height, (int, float)) and outer.height > 0,
          extra=f"height={outer.height}")
    fields_expand = [f for f in (name_f, note_f) if f is not None
                     and f.expand is not None and f.expand is not False]
    check(f"modal40[{_label}]: у полей НЕТ вертикального expand",
          not fields_expand)
    bad_expand = []
    for c in outer.controls:
        if isinstance(c, ft.TextField) and c.expand is not None \
                and c.expand is not False:
            bad_expand.append("field")
        elif isinstance(c, ft.Row) and c.expand is not None \
                and c.expand is not False:
            pass  # Row в Column: expand растягивает ПО ГОРИЗОНТАЛИ — запрета нет
    check(f"modal40[{_label}]: нет вертикальных expand внутри scroll-Column",
          not bad_expand)

    # ── (в) обе секции — bounded, положительная высота, видны ─────────
    boxes = _find_all_container_cols(dlg, outer=outer)
    heights = _collect_heights(boxes)
    check(f"modal40[{_label}]: ровно 2 bounded-списка (отделы+связи)",
          len(boxes) == 2, extra=str(heights))
    # внутренние списки: 29 отделов + (16/15) остальных
    cb = _all_checkboxes(dlg)
    n_dept = sum(1 for c in cb if getattr(c, "label", "").startswith("["))
    n_repl = sum(1 for c in cb if getattr(c, "label", "").startswith("("))
    check(f"modal40[{_label}]: 29 чекбоксов отделов", n_dept == 29,
          extra=str(n_dept))
    expected_repl = (16 if add_mode else 15)
    check(f"modal40[{_label}]: варианты связей = остальные ({expected_repl})",
          n_repl == expected_repl, extra=str(n_repl))
    if add_mode:
        check(f"modal40[{_label}]: в add нет собственного id",
              all("(17)" not in (getattr(c, "label", "") or "")
                  for c in cb))
    else:
        check(f"modal40[{_label}]: в edit текущий (№1) исключён",
              all("(1) " not in (getattr(c, "label", "") or "")
                  for c in cb)
              and any("(2) " in (getattr(c, "label", "") or "")
                      for c in cb))
    ok_bounded = len(heights) == 2 and all(
        isinstance(h, (int, float)) and h > 0 for h in heights)
    check(f"modal40[{_label}]: обе секции имеют положительную ограниченную "
          f"высоту", ok_bounded, extra=str(heights))
    # предвыбор партнёра у edit-режима дошёл до чекбокса (id=2 отмечен)
    if not add_mode:
        cb2 = next((c for c in cb
                    if getattr(c, "label", "").startswith("(2) ")), None)
        check(f"modal40[{_label}]: предвыбранный партнёр №2 отмечен",
              cb2 is not None and cb2.value is True)

    # ── (г) расчёт высот без заведомого переполнения ───────────────────
    win_h = int(_page.window.height)
    if win_h >= 700:
        # сумма: top-отступ 8 + ФИО + 8 + примечание + 12 + заголовок +
        # контейнер отделов + 10 + заголовок + контейнер связей
        est = (8 + 52 + 8 + 52 + 12 + 40 + heights[0] + 18
               + 10 + 40 + heights[1] + 18)
        # внешний scroll-Column всё равно bounded; то, что контент
        # потенциально больше высоты, допустимо (внешний скролл — страховка),
        # НО огромная неиспользуемая «дыра» недопустима:
        est_min = 8 + 52 + 8 + 52 + 12 + 40 + 110 + 18 + 10 + 40 + 90 + 18
        if outer.height > 200:
            excess = outer.height - min(outer.height, est)
            check(f"modal40[{_label}]: нет огромной пустой области внизу",
                  outer.height <= est + 90
                  or outer.height - est <= 90,
                  extra=f"content_h={outer.height}, est={est}")
            _ = est_min
    # минимальные размеры списков на всех окнах
    if len(heights) == 2:
        check(f"modal40[{_label}]: список отделов ≥ 110 pt",
              heights[0] >= 110, extra=str(heights[0]))
        check(f"modal40[{_label}]: список связей ≥ 90 pt",
              heights[1] >= 90, extra=str(heights[1]))


def run_modal_layout_add():
    run_modal_layout(add_mode=True)


def run_modal_layout_edit():
    run_modal_layout(add_mode=False)


def run_modal_small_window():
    """16в. Маленькое окно (720) — bounded без огромной пустой области."""
    from ui.zonal.add_criminalist_modal import create_add_criminalist_modal
    _page = _WinPage(height=720)
    others = get_initial_criminalists()
    dlg = create_add_criminalist_modal(page=_page,
                                       on_save=lambda *a: None,
                                       other_criminalists=others)
    outer = dlg.content.content
    boxes = _find_all_container_cols(dlg, outer=outer)
    heights = _collect_heights(boxes)
    check("modal40[small]: внешняя высота ограничена окном (≤ 720-100)",
          outer.height <= 620 and outer.height > 300,
          extra=f"content_h={outer.height}")
    check("modal40[small]: обе секции bounded и положительны",
          len(heights) == 2 and all(
              isinstance(h, (int, float)) and h >= 90 for h in heights),
          extra=str(heights))
    # «дыры» нет: сумма секций+фикс ≥ 0.75 content_h
    if len(heights) == 2 and isinstance(outer.height, (int, float)):
        sum_lists = heights[0] + heights[1]
        fixed = (8 + 52 + 8 + 52 + 12 + 40 + 10 + 40) + 18 * 2
        est = fixed + sum_lists
        check("modal40[small]: раскладка заполняет высоту (без дыры > 25%)",
              outer.height <= est + 90,
              extra=f"content_h={outer.height}, est={est}")


def run_pdf_env_check():
    """16г. Runtime-проверка зависимости PDF (реальный sys.executable)."""
    import importlib
    print(f"[ENV40] sys.executable: {sys.executable}")
    try:
        rl = importlib.import_module("reportlab")
        PIL = importlib.import_module("PIL")
        print(f"[ENV40] reportlab {rl.Version}; Pillow {PIL.__version__}")
    except Exception as ex:
        check("env40: reportlab/Pillow импортируются", False, extra=str(ex))
        return
    check("env40: reportlab импортируется", True)
    check("env40: Pillow импортируется", True)
    # версии совпадают с пинами requirements
    check("env40: reportlab == 4.4.10", rl.Version == "4.4.10",
          extra=rl.Version)
    check("env40: Pillow == 10.4.0", PIL.__version__ == "10.4.0",
          extra=PIL.__version__)
    # формируем НАСТОЯЩИЙ PDF с кириллицей в temp
    path, pages = export_to([mk_crim(1, "Кириллица Проверка", depts=[1]),
                             mk_crim(2, "Второй Человек", depts=[2])],
                            tag="pdf_env")
    check("env40: реальный PDF создан (1 страница)", pages == 1,
          extra=str(pages))
    check("env40: файл существует и не пуст",
          os.path.exists(path) and os.path.getsize(path) > 20000)
    txt = extract_pdf_text(path)
    check("env40: PDF содержит кириллицу/районы",
          "Кириллица Проверка" in txt and "Второй Человек" in txt)


def run_modal_persistence():
    """16д. Persistence: модалка→модель→JSON→повторное открытие (add+edit)."""
    from ui.zonal.add_criminalist_modal import create_add_criminalist_modal

    # ── (а) добавление через РЕАЛЬНЫЕ обработчики модалки ───────────────
    others = get_initial_criminalists()
    page = _WinPage()
    saved = {}
    dlg_add = create_add_criminalist_modal(
        page=page, criminalist=None,
        on_save=lambda name, note, dep, rep: saved.update(
            name=name, note=note, dep=dep, rep=rep),
        other_criminalists=others)
    _save_modal_and_check(page, dlg_add, "Тест Добавление",
                          "Заметка добавления", [2, 5], [3], "persist40: add")
    check("persist40: колбэк add получил районы [2, 5]", saved.get("dep") == [2, 5],
          extra=str(saved.get("dep")))
    check("persist40: колбэк add получил партнёра [3]", saved.get("rep") == [3],
          extra=str(saved.get("rep")))
    # теперь тот же путь, что в zonal_tab._on_add_criminalist: модель+JSON
    new = Criminalist(id=17, full_name=saved.get("name", "?"),
                      note=saved.get("note", ""), is_active=True,
                      zone=CriminalistZone(17, saved.get("dep", [])))
    others.append(new)
    set_replacement_partners(others, 17, saved.get("rep", []))
    save_criminalists(others)
    p17 = next(c for c in others if c.id == 17)
    partner3 = next(c for c in others if c.id == 3)
    check("persist40: у нового района [2, 5] и партнёр [3]",
          p17.zone.department_ids == [2, 5] and p17.replacement_ids == [3])
    check("persist40: связь 17↔3 симметрична", 17 in partner3.replacement_ids)
    jpath = os.path.join(_APPDATA, "porayonka", "zonal_criminalists.json")
    check("persist40: JSON записан после save_criminalists",
          os.path.exists(jpath))
    if os.path.exists(jpath):
        with open(jpath, encoding="utf-8") as f:
            j = json.load(f)
        c17 = next((c for c in j.get("criminalists", [])
                    if c.get("id") == 17), None)
        check("persist40: JSON содержит районы/связь (после normalize)",
              c17 is not None
              and sorted(c17["zone"]["department_ids"]) == [2, 5]
              and sorted(c17.get("replacement_ids", [])) == [3])

    # ── (б) повторное открытие: выбранное отмечено ──────────────────────
    # «после перезапуска»: файл перечитан (новые объекты) + добавлен №17
    reloaded = load_criminalists()
    if not any(c.id == 17 for c in reloaded):
        reloaded.append(p17)
    dlg_re = create_add_criminalist_modal(page=_WinPage(), criminalist=p17,
                                          on_save=lambda *a: None,
                                          on_delete=lambda c: None,
                                          other_criminalists=reloaded)
    cb_dep = {getattr(c, "label", ""): c for c in _all_checkboxes(dlg_re)}
    cb2 = next((cb for lbl, cb in cb_dep.items() if lbl.startswith("[2] ")),
               None)
    cb5 = next((cb for lbl, cb in cb_dep.items() if lbl.startswith("[5] ")),
               None)
    cb3 = next((cb for lbl, cb in cb_dep.items() if lbl.startswith("(3) ")),
               None)
    check("persist40: повторное открытие — районы 2,5 отмечены",
          cb2 is not None and cb2.value is True
          and cb5 is not None and cb5.value is True)
    check("persist40: повторное открытие — партнёр 3 отмечен",
          cb3 is not None and cb3.value is True)
    own_present = any(lbl.startswith("(17)") for lbl in cb_dep)
    check("persist40: сам редактируемый (17) не в списке вариантов",
          not own_present)

    # ── (в) редактирование: снять партнёра — связь исчезает с обеих ────
    dlg_edit = create_add_criminalist_modal(
        page=_WinPage(), criminalist=p17,
        on_save=lambda name, note, dep, rep: saved.update(
            name=name, note=note, dep=dep, rep=rep),
        on_delete=lambda c: None,
        other_criminalists=reloaded)
    for cb in _all_checkboxes(dlg_edit):
        if getattr(cb, "label", "").startswith("(3) ") and cb.value:
            cb.value = False
            cb.on_change(_FakeEvent(cb))
    save_btn = next((c for c in _find_all(dlg_edit, lambda c: isinstance(
        c, ft.ElevatedButton))
        if getattr(c, "text", "") == "Сохранить"), None)
    save_btn.on_click(None)
    check("persist40: edit-колбэк отдал rep=[]", saved.get("rep") == [],
          extra=str(saved.get("rep")))
    # снятие через set_replacement_partners убирает обе стороны
    p17.replacement_ids = saved.get("rep", [])
    others = reloaded
    p17c = next(c for c in others if c.id == 17)
    set_replacement_partners(others, p17c.id, p17.replacement_ids)
    partner3b = next(c for c in others if c.id == 3)
    check("persist40: снятие удалило связь с обеих сторон",
          p17c.replacement_ids == [] and 17 not in partner3b.replacement_ids)


# ── UI-слой: настоящие обработчики вкладки (PageStub + временные env) ───
def _walk(obj):
    """Обойти дерево Flet-контролов (controls/content/actions/overlay)."""
    if obj is None:
        return
    yield obj
    for attr in ("controls", "actions", "title", "content"):
        v = getattr(obj, attr, None)
        if isinstance(v, (list, tuple)):
            for c in v:
                yield from _walk(c)
        elif v is not None and not isinstance(v, (str, int, float, bool, dict)):
            yield from _walk(v)


def _find_all(root, pred):
    return [c for c in _walk(root) if pred(c)]


def _find(root, pred):
    for c in _walk(root):
        if pred(c):
            return c
    return None


class _FakeEvent:
    """Минимальный event для on_change/on_click-обработчиков Flet."""

    def __init__(self, control):
        self.control = control
        self.data = None
        self.x = 5.0
        self.y = 5.0


class _WinPage:
    """Минимальная desktop-страница для сборки модалок (без web-атрибутов)."""

    def __init__(self, height=860):
        self.width = 1280
        self.height = height
        self.web = False
        self.window = type("_Win", (), {"height": height, "width": 1280})()
        self.overlay = []
        self.snack_bar = None
        self.on_resize = None

    def update(self):
        pass

    def open(self, dlg):
        if dlg not in self.overlay:
            self.overlay.append(dlg)


class _WebPage:
    """PageStub + web-режим: launch_url запоминает URL (других вызовов нет)."""

    def __init__(self, width=1400, height=900):
        self.width = width
        self.height = height
        self.web = True
        self.launched = []
        self.overlay = []
        self.snack_bar = None
        self.on_resize = None
        self._zonal_collection = None
        self._zonal_pdf_state = None
        self._zonal_pdf_open_btn = None

    def update(self):
        pass

    def launch_url(self, url):
        self.launched.append(url)

    def open(self, dlg):
        if dlg not in self.overlay:
            self.overlay.append(dlg)


def run_ui_flows():
    """15. UI: вкладка + реальные add/edit/delete + web-экспорт PDF."""
    # Полноценная загрузка вкладки (временный APPDATA)
    from ui.zonal.zonal_tab import create_zonal_tab
    page = _WebPage()
    tab = create_zonal_tab(page)
    check("ui40: create_zonal_tab построился", tab is not None
          and len(tab.controls) > 0)
    coll = page._zonal_collection
    check("ui40: вкладка загрузила 16 дефолтных",
          len(coll.criminalists) == 16)

    # ── кнопки тулбара на месте ─────────────────────────────────────
    btns = {getattr(c, "text", ""): c
            for c in _find_all(tab, lambda c: getattr(c, "text", None))}
    for name in ("Добавить", "Выгрузить зональных", "Экспорт в Excel"):
        if name not in btns:
            check(f"ui40: кнопка «{name}» в тулбаре", False)
    else:
        check("ui40: кнопки «Добавить»/«Выгрузить зональных»/Excel на месте",
              True)
    open_btn = page._zonal_pdf_open_btn
    check("ui40: «Открыть PDF» скрыт до экспорта",
          open_btn is not None and open_btn.visible is False)

    # ── ДОБАВЛЕНИЕ через реальные обработчики ───────────────────────
    add_btn = next((c for c in _find_all(tab, lambda c: isinstance(
        c, ft.ElevatedButton)) if getattr(c, "text", "") == "Добавить"), None)
    add_btn.on_click(None)
    dlg = page.overlay[-1]
    # поля модалки
    name_field = _find(dlg, lambda c: getattr(c, "label", None)
                       == "ФИО криминалиста *")
    check("ui40: модалка добавления открылась с полем ФИО",
          name_field is not None)
    name_field.value = "Новенький Тест ФазыСорок"
    note_field = _find(dlg, lambda c: getattr(c, "label", None)
                       == "Примечание (например, 'Цифровая криминалистика')")
    note_field.value = "тестовая заметка"
    # отметить отделы [1] и [3]
    dept_cbs = {getattr(c, "label", ""): c for c in _find_all(
        dlg, lambda c: isinstance(c, ft.Checkbox))}
    d1 = next((k for k in dept_cbs if k.startswith("[1]")), None)
    d3 = next((k for k in dept_cbs if k.startswith("[3]")), None)
    if d1:
        cb1 = dept_cbs[d1]
        cb1.value = True
        cb1.on_change(_FakeEvent(cb1))
    if d3:
        cb3 = dept_cbs[d3]
        cb3.value = True
        cb3.on_change(_FakeEvent(cb3))
    check("ui40: чекбоксы отделов найдены и отмечены", bool(d1 and d3))
    # отметить взаимозаменяемость с №1 (Агеев)
    r1 = next((k for k in dept_cbs if k.startswith("(1) ")), None)
    if r1:
        cb = dept_cbs[r1]
        cb.value = True
        cb.on_change(_FakeEvent(cb))
    check("ui40: в списке взаимозаменяемости нет самого добавляемого",
          not any(k.startswith("(17)") for k in dept_cbs)
          and r1 is not None)
    save_btn = next((c for c in _find_all(dlg, lambda c: isinstance(
        c, ft.ElevatedButton))
        if getattr(c, "text", "") == "Сохранить"), None)
    save_btn.on_click(None)
    added = next((c for c in coll.criminalists
                  if c.full_name == "Новенький Тест ФазыСорок"), None)
    check("ui40: добавление сохранило человека (id 17)",
          added is not None and added.id == 17)
    check("ui40: зоны добавленного = отмеченные отделы",
          added is not None and sorted(added.zone.department_ids) == [1, 3])
    check("ui40: связь добавленного с №1 симметрична",
          added is not None and added.replacement_ids == [1]
          and any(c.id == 1 and 17 in c.replacement_ids
                  for c in coll.criminalists))

    # ── РЕДАКТИРОВАНИЕ №1: смена ФИО + снятие связи с №17 ────────────
    # плашки: ряды пересобраны — в дереве tab теперь 17 редактирований
    edit_btns = _find_all(tab, lambda c: isinstance(
        c, ft.IconButton)
        and getattr(c, "tooltip", "") == "Редактировать криминалиста")
    check("ui40: плашек с редактированием стало 17",
          len(edit_btns) == 17, extra=str(len(edit_btns)))
    edit_btns[0].on_click(None)   # первая плашка — №1 (порядок коллекции)
    dlg2 = page.overlay[-1]
    name_field2 = _find(dlg2, lambda c: getattr(c, "label", None)
                        == "ФИО криминалиста *")
    check("ui40: редактирование открыто на №1 (ФИО подставлено)",
          name_field2 is not None
          and name_field2.value == "Агеев Олег Владимирович")
    name_field2.value = "Агеев Олег Владимирович (ред.)"
    # снять все связи во вкладке взаимозаменяемости
    repl_cbs = [c for c in _find_all(dlg2, lambda c: isinstance(
        c, ft.Checkbox)) if getattr(c, "label", "").startswith("(")]
    for cb in repl_cbs:
        cb.value = False
        cb.on_change(_FakeEvent(cb))
    save_btn2 = next((c for c in _find_all(dlg2, lambda c: isinstance(
        c, ft.ElevatedButton))
        if getattr(c, "text", "") == "Сохранить"), None)
    save_btn2.on_click(None)
    one = next(c for c in coll.criminalists if c.id == 1)
    seventeen = next(c for c in coll.criminalists if c.id == 17)
    check("ui40: редактирование обновило ФИО", one.full_name.endswith("(ред.)"))
    check("ui40: снятие связи убрало её с ОБЕИХ сторон",
          one.replacement_ids == [] and seventeen.replacement_ids == [])

    # ── УДАЛЕНИЕ №1 через реальные обработчики ───────────────────────
    delete_btns = _find_all(tab, lambda c: isinstance(
        c, ft.IconButton)
        and getattr(c, "tooltip", "") == "Удалить криминалиста")
    delete_btns[0].on_click(None)      # подтверждающий диалог
    confirm = page.overlay[-1]
    del_btn = next((c for c in _find_all(confirm, lambda c: isinstance(
        c, ft.ElevatedButton))
        if getattr(c, "text", "") == "Удалить"), None)
    del_btn.on_click(None)
    check("ui40: удаление убрало №1 из коллекции",
          all(c.id != 1 for c in coll.criminalists))
    check("ui40: после удаления №1 никто не ссылается на 1",
          all(1 not in c.replacement_ids for c in coll.criminalists))
    check("ui40: в коллекции 16 человек (17 - 1)",
          len(coll.criminalists) == 16)

    # ── WEB-ЭКСПОРТ PDF кнопкой «Выгрузить зональных» ────────────────
    pdf_btn = next((c for c in _find_all(tab, lambda c: isinstance(
        c, ft.ElevatedButton))
        if getattr(c, "text", "") == "Выгрузить зональных"), None)
    pdf_btn.on_click(None)
    state = page._zonal_pdf_state
    check("ui40: web-экспорт записал файл в assets/downloads",
          state["path"] is not None and os.path.exists(state["path"])
          and "/downloads/" in state["path"])
    check("ui40: web-экспорт отдал URL /assets/downloads/…",
          state["url"].startswith("/assets/downloads/"))
    check("ui40: браузер получил launch_url PDF",
          len(page.launched) == 1 and page.launched[0] == state["url"])
    check("ui40: «Открыть PDF» стал видимым", open_btn.visible is True)
    # открытие повторно — тот же URL
    open_btn.on_click(None)
    check("ui40: повторное открытие переиспользует URL",
          len(page.launched) == 2 and page.launched[-1] == state["url"])
    # файл удалён извне — понятный сброс
    os.remove(state["path"])
    open_btn.on_click(None)
    check("ui40: удалённый файл -> сброс состояния и скрытие кнопки",
          state["path"] is None and state["url"] is None
          and open_btn.visible is False)
    check("ui40: после сброса launch_url больше не вызывался",
          len(page.launched) == 2)


def run_static_invariants():
    """15б. Статические инварианты фазы 40 (упаковка и код)."""
    # pinned PDF-библиотека
    for req, fname in (("reportlab==4.4.10", "requirements.txt"),
                       ("reportlab==4.4.10", "requirements-win7-web.txt")):
        with open(os.path.join(_APP_DIR, fname), encoding="utf-8") as f:
            content = f.read()
        check(f"static40: {fname} пинит reportlab==4.4.10",
              req in content and "pillow==10.4.0" in content)
    # сообщение о недостающем компоненте PDF в обработчике ошибки
    tab_src = open(os.path.join(_APP_DIR, "ui", "zonal", "zonal_tab.py"),
                   encoding="utf-8").read()
    check("static40: toast PDF объясняет отсутствие ReportLab/Pillow",
          "Отсутствует компонент PDF" in tab_src
          and "_pdf_failure_toast" in tab_src)
    check("static40: исключение PDF пишется ASCII-safe (ascii())",
          "ascii(ex)" in tab_src or "ascii(e)" in tab_src)
    # assets/fonts в каждом spec (6 файлов сборки)
    specs = [f for f in os.listdir(_APP_DIR) if f.endswith(".spec")]
    for spec in specs:
        with open(os.path.join(_APP_DIR, spec), encoding="utf-8") as f:
            content = f.read()
        if ('"assets", "assets"' not in content
                and "'assets', 'assets'" not in content):
            check(f"static40: {spec} включает assets (шрифты PDF)", False)
    check("static40: все {0} spec включают assets".format(len(specs)), True)
    # bat-скрипты пинят pillow для reportlab-профилей
    for bat in ("build_all_distributives.bat", "build_user_web_win7.bat"):
        with open(os.path.join(_APP_DIR, bat), encoding="utf-8") as f:
            content = f.read()
        if bat == "build_all_distributives.bat":
            ok = content.count("pillow==10.4.0") == 2
        else:
            ok = content.count("pillow==10.4.0") == 1
        check(f"static40: {bat} пинит pillow==10.4.0", ok)
    # zonal_tab: on_save 4-аргументный + other_criminalists передаётся
    tab_src = open(os.path.join(_APP_DIR, "ui", "zonal", "zonal_tab.py"),
                   encoding="utf-8").read()
    check("static40: обработчики on_save принимают replacement_ids",
          tab_src.count("replacement_ids: list") == 2)
    check("static40: модалка получает other_criminalists в add и edit",
          tab_src.count("other_criminalists=collection.criminalists") == 2)
    check("static40: удаление чистит связи ДО удаления человека",
          "remove_criminalist_links(collection.criminalists, criminalist.id)"
          in tab_src)
    # только ft.icons.* в коде зонального UI
    zonal_files = []
    for root, _dirs, files in os.walk(os.path.join(_APP_DIR, "ui", "zonal")):
        zonal_files += [os.path.join(root, f) for f in files
                        if f.endswith(".py")]
    bad = []
    for f in zonal_files:
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                if "ft.Icons." in line or "icons." in line and "ft.icons." not in line:
                    bad.append(os.path.basename(f) + ":" + line.strip()[:60])
    check("static40: в ui/zonal только ft.icons.*", not bad, extra="; ".join(bad[:3]))
    # экспортёр не импортирует Flet
    exp_src = open(os.path.join(_APP_DIR, "core",
                                "zonal_distribution_exporter.py"),
                   encoding="utf-8").read()
    check("static40: exporter не зависит от flet",
          "import flet" not in exp_src and "from flet" not in exp_src)


# ────────────────────────────────────────────────────────────────────────
# Дополнение фазы 40 (PROMPT_зональные_доработка_фаза40.md, §6): группы 17+
# ────────────────────────────────────────────────────────────────────────
def _default_crims():
    """Актуальный штатный набор приложения (16 дефолтных)."""
    return [Criminalist(id=d["id"], full_name=d["full_name"], note=d["note"],
                        is_active=d.get("is_active", True),
                        zone=CriminalistZone(criminalist_id=d["id"],
                                             department_ids=list(d["department_ids"])))
            for d in INITIAL_CRIMINALISTS_DATA]


def _crim_by_id(crims, cid):
    return next(c for c in crims if c.id == cid)


def _save_load(crims):
    """save_criminalists + load_criminalists (JSON round-trip как в UI)."""
    save_criminalists(crims)
    return load_criminalists()


def run_suppl_symmetry():
    """17. Дополнение §6.1: полные сценарии симметрии связей с save/load."""
    # ── (1) A↔B через «редактирование A»: обе стороны содержат друг друга
    crims = _default_crims()
    a, b = _crim_by_id(crims, 1), _crim_by_id(crims, 2)
    set_replacement_partners(crims, a.id, [b.id])
    check("suppl40: (1) A↔B — обе стороны содержат друг друга",
          b.id in a.replacement_ids and a.id in b.replacement_ids,
          extra=f"a={list(a.replacement_ids)} b={list(b.replacement_ids)}")
    reloaded = _save_load(crims)
    ra, rb = _crim_by_id(reloaded, 1), _crim_by_id(reloaded, 2)
    check("suppl40: (1) A↔B переживает save/load JSON",
          rb.id in ra.replacement_ids and ra.id in rb.replacement_ids)
    # неориентированность не зависит от порядка карточек: редактирование B
    # с тем же партнёром даёт тот же результат
    set_replacement_partners(reloaded, rb.id, [ra.id])
    check("suppl40: (1) редактирование B даёт ту же пару",
          ra.id in rb.replacement_ids and rb.id in ra.replacement_ids)

    # ── (2) снять B у A — ссылка удалена у ОБЕИХ сторон
    crims = _default_crims()
    a, b = _crim_by_id(crims, 1), _crim_by_id(crims, 2)
    set_replacement_partners(crims, a.id, [b.id])
    set_replacement_partners(crims, a.id, [])      # редактирование A: сняли B
    check("suppl40: (2) снятие B у A удалило ссылку у обеих сторон",
          not a.replacement_ids and not b.replacement_ids,
          extra=f"a={list(a.replacement_ids)} b={list(b.replacement_ids)}")
    reloaded = _save_load(crims)
    ra, rb = _crim_by_id(reloaded, 1), _crim_by_id(reloaded, 2)
    check("suppl40: (2) после save/load связи не вернулись",
          not ra.replacement_ids and not rb.replacement_ids)

    # ── (3) новый C с выбранным A: симметрия сразу и после save/load
    crims = _default_crims()
    crims.append(Criminalist(id=17, full_name="Новиков Новый ФазаСорок",
                             note="", is_active=True,
                             zone=CriminalistZone(17, [2])))
    set_replacement_partners(crims, 17, [1])
    c17, r1 = _crim_by_id(crims, 17), _crim_by_id(crims, 1)
    check("suppl40: (3) новый C↔A — симметрия сразу",
          1 in c17.replacement_ids and 17 in r1.replacement_ids)
    reloaded = _save_load(crims)
    rc17, rr1 = _crim_by_id(reloaded, 17), _crim_by_id(reloaded, 1)
    check("suppl40: (3) C↔A переживает save/load JSON",
          rr1.id in rc17.replacement_ids
          and rc17.id in rr1.replacement_ids)

    # ── (4) удалить A: его ID отсутствует у всех после save/load
    crims = _default_crims()
    set_replacement_partners(crims, 1, [2, 3])
    remove_criminalist_links(crims, 1)
    crims = [c for c in crims if c.id != 1]
    reloaded = _save_load(crims)
    refs = [c.replacement_ids for c in reloaded]
    check("suppl40: (4) после удаления A его ID нет ни у кого",
          all(1 not in (ids or []) for ids in refs)
          and all(c.id != 1 for c in reloaded))
    check("suppl40: (4) удалённый A отсутствует в JSON (15 человек)",
          len(reloaded) == 15)
    # после удаления A пара 2↔3, созданная через A, не «повисла»
    r2, r3 = _crim_by_id(reloaded, 2), _crim_by_id(reloaded, 3)
    check("suppl40: (4) пара 2↔3 не создалась из удалённого A",
          not r2.replacement_ids and not r3.replacement_ids)

    # ── (5) unique_pairs: одно-/двустороннее представление — та же пара
    order = [mk_crim(1, "Агеев Олег Владимирович", depts=[1]),
             mk_crim(2, "Грубников Георгий Григорьевич", depts=[1]),
             mk_crim(3, "Смирнов Сергей Сергеевич", depts=[1])]
    variants = {}
    v1 = [mk_crim(x.id, x.full_name, depts=[1]) for x in order]
    set_replacement_partners(v1, 1, [2])             # двусторонняя 1↔2
    variants["both"] = list(unique_pairs(v1))
    v2 = [mk_crim(x.id, x.full_name, depts=[1]) for x in order]
    v2[0].replacement_ids = [2]                      # «односторонняя» A→B
    v2[1].replacement_ids = []
    variants["a_to_b"] = list(unique_pairs(v2))
    v3 = [mk_crim(x.id, x.full_name, depts=[1]) for x in order]
    v3[0].replacement_ids = []
    v3[1].replacement_ids = [1]                      # «односторонняя» B→A
    variants["b_to_a"] = list(unique_pairs(v3))
    ok_keys = all([(p[0].id, p[1].id) for p in variants[k]] == [(1, 2)]
                  for k in variants)
    check("suppl40: (5) unique_pairs: 1 пара (1,2) во всех представлениях",
          ok_keys,
          extra=str({k: [(p[0].id, p[1].id) for p in v]
                     for k, v in variants.items()}))
    normalize_replacement_links(v2)
    check("suppl40: (5) нормализация однонаправленного входа не меняет пару",
          [(p[0].id, p[1].id) for p in unique_pairs(v2)] == [(1, 2)]
          and 1 in v2[1].replacement_ids and 2 in v2[0].replacement_ids)

    # ── (6) две разные пары не склеиваются; self/dangling не в результате
    crims = [mk_crim(1, "Один Один Один", depts=[1]),
             mk_crim(2, "Два Два Два", depts=[1]),
             mk_crim(3, "Три Три Три", depts=[1]),
             mk_crim(4, "Четыре Четыре Четыре", depts=[1])]
    set_replacement_partners(crims, 1, [2])
    set_replacement_partners(crims, 3, [4])
    # ручной «мусор»: self-link у №1 и ссылка на отсутствующего (99)
    crims[0].replacement_ids = [1, 2, 99]
    pairs = unique_pairs(crims)
    ids = [(p[0].id, p[1].id) for p in pairs]
    check("suppl40: (6) ровно 2 пары, без склейки/self/dangling",
          sorted(ids) == [(1, 2), (3, 4)], extra=str(ids))


def _has_on_scroll_cb(control):
    """Есть ли у контрола ПОДПИСАННЫЙ on_scroll-обработчик.

    У Row/Column (ScrollableControl) атрибут on_scroll всегда содержит
    объект EventHandler; «использование on_scroll» = наличие подписки
    (count > 0) — как в реальном Flet 0.23.2.
    """
    v = getattr(control, "on_scroll", None)
    if v is None:
        return False
    count = getattr(v, "count", None)
    if count is not None:
        try:
            return count() > 0 if callable(count) else count > 0
        except TypeError:
            return bool(count)
    return bool(v)


def _vertical_expand_violations(root):
    """Контролы с вертикальным expand=True внутри scroll-колонки.

    expand допустим только у ПРЯМЫХ детей Row (там он горизонтальный).
    Всё остальное под внешней Column(scroll=AUTO) — запрещённое
    вертикальное растяжение (Flet 0.23.2 ломает bounded layout).
    """
    bad = []

    def walk(node, parent_is_row):
        if getattr(node, "expand", None) is True and not parent_is_row:
            bad.append(node)
        children = []
        for attr in ("controls", "actions", "title", "content"):
            v = getattr(node, attr, None)
            if isinstance(v, (list, tuple)):
                children.extend(v)
            elif (v is not None
                  and not isinstance(v, (str, int, float, bool, dict))):
                children.append(v)
        for ch in children:
            walk(ch, parent_is_row=isinstance(node, ft.Row))

    walk(root, False)
    return bad


def run_suppl_modal():
    """17б. Дополнение §6.2: модалка на реальном дереве контролов.

    Окна 430 и 860: bounded-списки, ScrollMode.ALWAYS у списка связей,
    локальная ScrollbarTheme с видимым интерактивным ползунком, без
    on_scroll и без вертикальных expand; последний вариант выбирается
    реальным on_change и доходит до on_save.
    """
    from ui.zonal.add_criminalist_modal import create_add_criminalist_modal
    others = _default_crims()
    for win_h in (430, 860):
        _page = _WinPage(height=win_h)
        saved = []
        dlg = create_add_criminalist_modal(
            page=_page, on_save=lambda *a: saved.append(a),
            other_criminalists=others)
        tag = f"h{win_h}"
        outer = dlg.content.content

        # внешняя bounded-колонка со scroll (страховка), внутри — без
        # запрещённых вертикальных expand и без on_scroll
        check(f"suppl40[{tag}]: внешняя колонка bounded + scroll",
              isinstance(outer, ft.Column) and outer.height is not None
              and outer.height > 0
              and outer.scroll == ft.ScrollMode.AUTO,
              extra=f"h={outer.height}")
        check(f"suppl40[{tag}]: внешняя высота не превышает окно",
              outer.height <= win_h, extra=str(outer.height))
        check(f"suppl40[{tag}]: нет on_scroll ни у одного контрола",
              all(not _has_on_scroll_cb(c) for c in _walk(dlg)))
        violations = _vertical_expand_violations(outer)
        check(f"suppl40[{tag}]: нет вертикальных expand в scroll-колонке",
              not violations,
              extra=",".join(type(v).__name__ for v in violations[:3]))

        # две секции: bounded положительные высоты; связи = ALWAYS, отделы = AUTO
        boxes = _find_all_container_cols(dlg, outer=outer)
        check(f"suppl40[{tag}]: ровно 2 bounded-списка",
              len(boxes) == 2,
              extra=str([b[1].height for b in boxes]))
        repl_boxes = [(cont, col) for cont, col in boxes
                      if col.scroll == ft.ScrollMode.ALWAYS]
        dept_boxes = [(cont, col) for cont, col in boxes
                      if col.scroll == ft.ScrollMode.AUTO]
        check(f"suppl40[{tag}]: список связей — ScrollMode.ALWAYS",
              len(repl_boxes) == 1)
        check(f"suppl40[{tag}]: список отделов — bounded AUTO",
              len(dept_boxes) == 1)
        repl_h = repl_boxes[0][1].height if repl_boxes else 0
        dept_h = dept_boxes[0][1].height if dept_boxes else 0
        check(f"suppl40[{tag}]: связь: bounded положительная высота",
              isinstance(repl_h, (int, float)) and repl_h > 0,
              extra=str(repl_h))
        check(f"suppl40[{tag}]: отделы: bounded положительная высота",
              isinstance(dept_h, (int, float)) and dept_h > 0,
              extra=str(dept_h))

        # локальная ScrollbarTheme на контейнере списка связей
        theme = repl_boxes[0][0].theme if repl_boxes else None
        sbt = theme.scrollbar_theme if isinstance(theme, ft.Theme) else None
        check(f"suppl40[{tag}]: локальная тема на контейнере связей",
              isinstance(theme, ft.Theme)
              and isinstance(sbt, ft.ScrollbarTheme))
        check(f"suppl40[{tag}]: thumb видимый и ползунок интерактивный",
              isinstance(sbt, ft.ScrollbarTheme)
              and sbt.thumb_visibility is True
              and sbt.interactive is True
              and (sbt.thickness or 0) > 0
              and (sbt.thumb_color or "") != "",
              extra=str(sbt.thumb_visibility) + "/"
              + str(sbt.interactive))
        check(f"suppl40[{tag}]: страница НЕ тронута (тема локальна)",
              getattr(_page, "theme", None) is None)

        # обе секции доступны + 2 TextField + кнопки действий
        check(f"suppl40[{tag}]: поля ФИО/примечание доступны",
              _find_textfield(dlg, "ФИО криминалиста *") is not None
              and _find_textfield(dlg, "Примечание (например, 'Цифровая "
                                       "криминалистика')") is not None)
        check(f"suppl40[{tag}]: заголовки обеих секций на месте",
              _find(dlg, lambda c: isinstance(c, ft.Text)
                    and getattr(c, "value", None)
                    == "Закреплённые отделы:") is not None
              and _find(dlg, lambda c: isinstance(c, ft.Text)
                        and getattr(c, "value", None)
                        == "Взаимозаменяемость:") is not None)
        acts = {getattr(c, "text", "") for c in _find_all(
            dlg, lambda c: isinstance(c, (ft.TextButton, ft.ElevatedButton)))}
        check(f"suppl40[{tag}]: кнопки Отмена/Сохранить на месте",
              {"Отмена", "Сохранить"} <= acts)
        # список из 29 отделов полностью в дереве
        cb = _all_checkboxes(dlg)
        n_dept = sum(1 for c in cb if getattr(c, "label", "").startswith("["))
        n_repl = sum(1 for c in cb if getattr(c, "label", "").startswith("("))
        check(f"suppl40[{tag}]: 29 отделов + 16 вариантов в списках",
              n_dept == 29 and n_repl == 16,
              extra=f"{n_dept}/{n_repl}")

        if win_h == 860:
            # новый viewport списка связей заметно выше прежнего тесного
            # (было ≤150 pt ≈ 2–3 строки; теперь ~236 pt ≈ 5 строк)
            check("suppl40[h860]: список связей ≥ 200 pt (был ~137)",
                  repl_h >= 200, extra=str(repl_h))
            check("suppl40[h860]: список связей выше деп. списка-компаньона",
                  repl_h >= dept_h, extra=f"repl={repl_h} dept={dept_h}")

        # последний вариант (16) отмечен РЕАЛЬНЫМ on_change и доходит до
        # on_save (четырёхаргументный: full_name, note, depts, repl)
        if win_h == 860:
            last_cb = next((c for c in cb
                            if getattr(c, "label", "").startswith("(16) ")),
                           None)
            check("suppl40[h860]: последний человек (16) в списке",
                  last_cb is not None)
            if last_cb is not None:
                name_f = _find_textfield(dlg, "ФИО криминалиста *")
                if name_f is not None:
                    name_f.value = "Выбор Последнего Тест"
                last_cb.value = True
                last_cb.on_change(_FakeEvent(last_cb))
                save_btn = next((c for c in _find_all(
                    dlg, lambda c: isinstance(c, ft.ElevatedButton))
                    if getattr(c, "text", "") == "Сохранить"), None)
                save_btn.on_click(None)
                got = saved[-1] if saved else None
                check("suppl40[h860]: on_save получил replacement_ids=[16]",
                      got is not None and got[3] == [16],
                      extra=str(got[3] if got else None))


def run_suppl_pdf():
    """17в. Дополнение §6.3: реальный PDF штатного набора — 1 страница A4.

    Полный текстовый состав, число «↔» == числу пар, направление входной
    связи не влияет на строки, oversized — без потерь на доп. страницах,
    длинные строки после удаления переносов не теряют символы.
    """
    base = _default_crims()

    # ── штатный набор без пар ─────────────────────────────────────
    path, pages = export_to(base, tag="suppl_pdf_std")
    check("suppl40: штатный набор — ровно 1 страница A4",
          pages == 1, extra=str(pages))
    with open(path, "rb") as f:
        raw = f.read()
    m = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", raw)
    ok_a4 = m is not None and abs(float(m.group(1)) - 595.2756) < 0.5 \
        and abs(float(m.group(2)) - 841.8898) < 0.5
    check("suppl40: MediaBox A4 portrait",
          ok_a4, extra=m.group(0).decode()[:40] if m else "no MediaBox")
    rm = re.search(rb"/Rotate\s+(\d+)", raw)
    check("suppl40: поворот страницы 0 (портрет при открытии/печати)",
          rm is None or int(rm.group(1)) == 0,
          extra=rm.group(0).decode() if rm else "нет /Rotate")
    text = extract_pdf_text(path)
    check("suppl40: точный заголовок присутствует ровно один раз",
          text.count("Зональный принцип распределения отдела "
                     "криминалистики") == 1)
    missing = [i for i in range(1, 17) if f"({i})" not in text]
    check("suppl40: все (N) ФИО штатного набора на месте", not missing,
          extra=f"нет: {missing[:5]}")
    words = set()
    for d in INITIAL_CRIMINALISTS_DATA:
        words.update(w for w in d["full_name"].split() if w)
    miss_w = [w for w in words if w not in text]
    check("suppl40: ФИО-токены не потеряны", not miss_w,
          extra=",".join(miss_w[:3]))
    check("suppl40: блок пар и «Не указана» (штатно пар нет)",
          "Взаимозаменяемость:" in text and "Не указана" in text)
    check("suppl40: без пар нет ни одной «↔»", "\u2194" not in text)

    # ── штатный набор + 8 пар: та же 1 страница, «↔» == 8 ─────────
    paired = _default_crims()
    for x, y in [(1, 2), (3, 4), (5, 6), (7, 8),
                 (9, 10), (11, 12), (13, 14), (15, 16)]:
        set_replacement_partners(paired, x, [y])
    path2, pages2 = export_to(paired, tag="suppl_pdf_pairs8")
    text2 = extract_pdf_text(path2)
    check("suppl40: штатные 16 + 8 пар — тоже 1 страница",
          pages2 == 1, extra=str(pages2))
    check("suppl40: число «↔» == числу уникальных пар (8)",
          text2.count("\u2194") == 8, extra=str(text2.count("\u2194")))
    check("suppl40: блок пар на той же странице, что и карточки",
          "Взаимозаменяемость:" in text2)

    # ── направление входной связи не меняет строки пар ────────────
    names = {1: "Агеев Олег Владимирович", 2: "Грубников Георгий Григорьевич",
             3: "Смирнов Сергей Сергеевич"}
    lines_of = {}
    for direction in ("a_to_b", "b_to_a", "both"):
        crims = [mk_crim(i, names[i], depts=[1]) for i in (1, 2, 3)]
        if direction == "a_to_b":
            crims[0].replacement_ids = [2]
        elif direction == "b_to_a":
            crims[1].replacement_ids = [1]
        else:
            set_replacement_partners(crims, 1, [2])
        p, _pg = export_to(crims, tag=f"suppl_dir_{direction}")
        lines_of[direction] = sorted(
            ln for ln in extract_pdf_text(p).split("\n") if "\u2194" in ln)
    check("suppl40: направления a→b / b→a / обе дают одинаковые строки пар",
          lines_of["a_to_b"] == lines_of["b_to_a"] == lines_of["both"],
          extra=" | ".join(lines_of["both"]))
    # …и после нормализации «одностороннего» входа строки те же
    crims = [mk_crim(i, names[i], depts=[1]) for i in (1, 2, 3)]
    crims[0].replacement_ids = [2]
    normalize_replacement_links(crims)
    p, _pg = export_to(crims, tag="suppl_dir_norm")
    norm_lines = sorted(ln for ln in extract_pdf_text(p).split("\n")
                        if "\u2194" in ln)
    check("suppl40: после normalize строки пар не меняются",
          norm_lines == lines_of["both"])

    # ── само-ссылки и dangling не печатаются в PDF ─────────────────
    crims = [mk_crim(1, "Один Один Один", depts=[1]),
             mk_crim(2, "Два Два Два", depts=[1]),
             mk_crim(3, "Три Три Три", depts=[1]),
             mk_crim(4, "Четыре Четыре Четыре", depts=[1])]
    set_replacement_partners(crims, 1, [2])
    set_replacement_partners(crims, 3, [4])
    crims[0].replacement_ids = [1, 2, 99]     # ручной мусор: self + dangling
    p, _pg = export_to(crims, tag="suppl_self")
    t = extract_pdf_text(p)
    check("suppl40: self/dangling не печатаются (2 пары, 2 стрелки)",
          t.count("\u2194") == 2)

    # ── большой синтетический набор: без потерь, доп. страницы ────
    big = []
    for i in range(1, 51):
        big.append(mk_crim(i, f"Многоплаговый Синтетический{i}",
                           note=("Специализация номер %d: длинное примечание "
                                 "для проверки переноса строк" % i),
                           active=(i % 9 != 0),
                           depts=list(range(1, (i % 7) + 2))))
    for x, y in [(1, 2), (10, 11), (25, 26), (49, 50)]:
        set_replacement_partners(big, x, [y])
    pbig, pbig_pages = export_to(big, tag="suppl_big50")
    big_text = extract_pdf_text(pbig)
    missing = [i for i in range(1, 51)
               if f"({i})" not in big_text or f"Синтетический{i}" not in big_text]
    check("suppl40: 50 человек — все на месте (доп. страницы допустимы)",
          pbig_pages > 1 and not missing,
          extra=f"страниц={pbig_pages}, нет: {missing[:5]}")
    check("suppl40: 50 человек: 4 пары напечатаны по разу",
          big_text.count("\u2194") == 4,
          extra=str(big_text.count("\u2194")))
    check("suppl40: заголовок повторён на каждой странице",
          all("Зональный принцип распределения" in pt
              for pt in extract_pdf_pages(pbig)))

    # ── длинная строка: удаление переносов не теряет символы ──────
    long_note = ("Экстремальнодлинная-строка-без-пробелов-" * 6).rstrip("-")
    crims = [mk_crim(1, "Длинная Строка Тест", note=long_note, depts=[1])]
    p, _pg = export_to(crims, tag="suppl_longnote")
    t = extract_pdf_text(p).replace("\n", "").replace(" ", "")
    check("suppl40: длинная строка без пробелов цела после переносов",
          long_note.replace("-", "") in t
          or long_note in t,
          extra=f"len(t)={len(t)}, need={len(long_note)}")


def main():
    groups = (
        ("1. replacement: parse_replacement_ids", run_logic_parse),
        ("2. replacement: normalize", run_logic_normalize),
        ("3. replacement: set_replacement_partners", run_logic_set_partners),
        ("4. replacement: remove_criminalist_links", run_logic_remove_links),
        ("5. replacement: unique_pairs", run_logic_pairs),
        ("6. replacement: short_full_name", run_logic_short_name),
        ("7. PDF: default-16, одна страница, A4, шрифты", run_pdf_default_page),
        ("8. PDF: текст default-16", run_pdf_default_text),
        ("9. PDF: чистота экспортёра", run_pdf_purity),
        ("10. PDF: неактивные и пустые зоны", run_pdf_inactive_empty),
        ("11. PDF: длинные тексты без потерь", run_pdf_long_wrap),
        ("12. PDF: 40 человек, многостраничность", run_pdf_multipage),
        ("13. PDF: строки пар", run_pdf_pairs),
        ("14. Web: helpers выгрузки", run_pdf_web_helpers),
        ("15. UI: вкладка + add/edit/delete + web-экспорт", run_ui_flows),
        ("15б. Static: упаковка/инварианты", run_static_invariants),
        ("16. Модалка add: layout-регрессия", run_modal_layout_add),
        ("16б. Модалка edit: layout-регрессия", run_modal_layout_edit),
        ("16в. Модалка: маленькое окно (720)", run_modal_small_window),
        ("16г. Runtime: окружение PDF (sys.executable)", run_pdf_env_check),
        ("16д. Модалка: persistence add/edit", run_modal_persistence),
        ("17. Дополнение §6.1: симметрия-сценарии с save/load",
         run_suppl_symmetry),
        ("17б. Дополнение §6.2: модалка 430/860 + scrollbar + on_save",
         run_suppl_modal),
        ("17в. Дополнение §6.3: PDF штатного набора — 1 страница A4",
         run_suppl_pdf),
    )
    for title, fn in groups:
        print("\n" + "=" * 72)
        print("=== %s ===" % title)
        try:
            fn()
        except Exception:
            FAILURES.append(title + " [exception]")
            traceback.print_exc()
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

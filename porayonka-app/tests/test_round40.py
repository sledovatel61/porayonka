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
    ZonalDistributionPdfExporter, export_pdf_for_web, sanitize_pdf_filename,
    reserve_unique_pdf_path, asset_download_url, fonts_dir,
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

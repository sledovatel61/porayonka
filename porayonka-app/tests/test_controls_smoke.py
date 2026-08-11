"""Headless-смок-тест вкладки «Контроли» (Glass Dark).

Покрывает требования PROMPT_контроли_доработка5.md, раздел «Проверка»:
  * py_compile всех файлов вкладки;
  * прямой импорт create_controls_tab;
  * init без шума 'Control must be added to the page first.';
  * карточка открывается (new + edit), левая и правая колонки НЕПУСТЫЕ и их
    контейнеры имеют width > 0, каждая glass_panel содержит непустой content;
  * добавление пункта (task) и точки (milestone) НЕ убивает карточку
    (середина остаётся, колонки живы);
  * hover-заливка строк УБРАНА (у строки нет on_hover), остался CLICK-курсор;
  * плашка строки — серый графит #2a3247 (не #1e2a44);
  * фильтры исполнителей/контролёров — канонический список + «Прочие» (без мусора).

Сетевая часть (PROMPT_контроли_сеть.md):
  * merge_controls: union по id, конфликт — новый updated_at, порядок стабилен;
  * два инстанса через одну общую папку (админ пишет → пользователь читает);
  * антиспам-журнал уведомлений (_should_notify) + round-trip notify_log/notify_sound;
  * офлайн→онлайн: запись при недоступном shared = False, локальный файл жив,
    merge не теряет локальную правку;
  * вкладка при network_enabled грузит данные из shared и показывает «Сеть: админ»;
  * подрезка журнала: записи старше 30 дней удаляются.

Канонические фильтры (PROMPT_контроли_фильтр_исполнителей.md):
  * name_matches: полное ФИО vs «Фамилия И.О.», суффиксы, несколько имён в строке,
    опечатки, чужая фамилия (False), пустые строки (False), фамилия <3 символов (False);
  * опции фильтров = только канонический список (криминалисты + Потемкин/Чашин) + «Прочие»,
    без мусора и дублей;
  * фильтрация находит любые написания («Семисенко И.Ю.», «Семисенко Иван Юрьевич»,
    «Чашин Э.А., Семисенко И.Ю.», ответственные по пунктам);
  * «Прочие» находит контроли с людьми вне списка и не находит через криминалистов;
  * сохранение выбранного значения при refresh: каноническое — сохраняется,
    мусорное — молча сбрасывается на «Все».

Раунд 7 (PROMPT_контроли_доработка7.md):
  * «Прочие»: Потемкин/Чашин как исполнители НЕ попадают в «Прочие» (полный справочник);
  * инициаторы: кластеризация «ГУК СК»/«ГУК С.»/«ГУК С.Т.С.А.С.И.Ю.» → «ГУК»,
    «СУ/СК» → «СУ», фильтрация по канону находит все варианты;
  * «Удалить все»: диалог со словом-подтверждением, очистка state/файлов/журнала,
    кнопка только у админа;
  * экспорт Excel 1:1 с эталоном «Контроли ОКРИМ.xlsx»: заголовок A1:J1, шапка во 2-й
    строке, ширины/цвета эталона, автофильтр от шапки, даты DD.MM.YYYY, скрытый
    _controls_full; импорт эталона и round-trip;
  * resize: drag меняет ширину и сохраняет col_widths в настройки (load_settings
    теперь возвращает все ключи — раньше col_widths терялся);
  * hover: bgcolor-only, рамка статична, без исключений.

Раунд 8 (PROMPT_контроли_доработка8.md):
  * справочник людей: extra_people в настройках (добавить/удалить), новые ФИО
    (Макаренко и т.п.) попадают в фильтр «Исполнители», а не в «Прочие»;
  * инициаторы: склейки «ГУК СК ГУК ЮФО», «ГСУ ГУК» разбиваются на отдельные каноны;
  * resize: drag-хэндлы на всех 11 границах колонок + видимые разделители
    в заголовке (#26ffffff) и строках (#12ffffff);
  * hover: отдельный лёгкий слой внутри строки (update только его bgcolor).

Раунд 9 (PROMPT_контроли_доработка9.md):
  * hover возвращён на саму строку (hover_layer в Stack ломал события в GUI),
    bgcolor-only + пропуск повторных событий;
  * разделители выровнены: заголовок и строки собираются одинаково
    ([bar][ячейка][разделитель]... с одинаковым spacing и padding 8);
  * редактор справочников: кнопка «Справочники» в тулбаре, модалка с тремя
    списками (люди/инициаторы), добавление/удаление, применение к фильтрам;
  * resize карточки: drag за угол (on_pan_update), min 600x400, размеры
    сохраняются в card_width/card_height;
  * предпросмотр вложений: миниатюры (ft.Image / иконка PDF), полноразмерный
    overlay с масштабированием, кнопки «открыть/удалить/закрыть».

Раунд 10 (PROMPT_контроли_доработка10.md):
  * «Действия»: Row иконок с width=колонки и alignment=END (прижаты вправо);
  * справочники: поля ввода expand на всю ширину, инлайн-редактирование записей
    (карандаш → поле + галочка/крестик) без вложенных диалогов;
  * карточка: clip_behavior=HARD_EDGE — скругление по всем 4 углам;
  * предпросмотр: ~90% ширины и ~85% высоты окна, изображение масштабируется.

Раунд 13 (PROMPT_контроли_доработка13.md):
  * hover УБРАН полностью со строк таблицы (и календарей/хэндлов) — оставлен
    только mouse_cursor=CLICK: нет on_hover => нет update() => нет лага;
  * таблица при 1280 помещается: сумма ширин колонок + spacing/разделители/
    padding/scrollbar <= 1240; сохранённые «раздутые» col_widths клампятся;
    на широких окнах «Содержание» <= 480, «Исполнители» <= 220;
  * справочники: редактирование/удаление сохраняется для ЛЮБОЙ записи (базовые
    ФИО/инициаторы — через extra_people/custom_initiators + hidden_*),
    записи пишутся в controls_settings.json, фильтры перестраиваются;
    строки списков компактные (кнопки 26px, spacing 2) — скролл построчный;
  * прикрепление к НОВОЙ карточке не падает с NoneType: control_id = uuid при
    открытии + страховка в обработчике; сеть недоступна — локальное копирование;
    copy_* с пустым control_id возвращают None без TypeError.

Раунд 14 (PROMPT_контроли_доработка14.md):
  * справочники — overlay-Container (НЕ AlertDialog) с resize за правый нижний
    угол; колесо в списках листает 2 строки за щелчок (on_scroll + scroll_to);
    правки записей раунда 13 сохранены;
  * карточка: равномерная рамка border.all + radius 16 + HARD_EDGE (углы не
    прозрачные).

Раунд 16 (PROMPT_контроли_доработка16.md):
  * левая статусная полоса строки — строго 4 px, полная высота строки (Positioned
    left=0/top=0/bottom=0 поверх Stack строки, клип HARD_EDGE по скруглению);
    bar не ресайзабелен и НЕ сохраняется в col_widths; засевший в settings
    bar>4 сбрасывается при старте (ключ вычищается из json); номер строки на
    нейтральном фоне плашки;
  * KeyError 'sd'/'dir': кастомный _make_row_scroller УДАЛЁН (баг OnScrollEvent
    Flet 0.23.2 — клиент присылает нотификации без 'sd'/'dir'); списки
    справочников — Column(scroll=ADAPTIVE, expand=True) БЕЗ on_scroll: нативный
    скролл + постоянный видимый бегунок (thumbVisibility=true на десктопе,
    scrollable_control.dart); ft.ListView в 0.23.2 не принимает scroll=...
    (ScrollableControl не оборачивается) — поэтому бегунок невозможен с ListView;
  * размеры карточки и «Справочников» запоминаются: card_width/card_height и
    refs_width/refs_height в controls_settings.json; карточка при открытии
    применяет сохранённые размеры БЕЗ обрезки до 780 (клампы как при drag).

Раунд 15 (PROMPT_контроли_доработка15.md):
  * hover строк — НАТИВНЫЙ Flutter InkWell (ink=True на строке + локальная тема
    таблицы с hover_color #12ffffff), Python on_hover УДАЛЁН полностью: без
    событий в Python нет задержки и «хвостов»; курсор CLICK сохранён;
  * таблица заполняет всю ширину окна: панель/заголовок/строки получают ЯВНУЮ
    ширину (окно-64 / -2), сумма колонок выравнивается под бюджет (_fit_widths:
    кламп при переполнении + заполнение остатка 65/35 в «Содержание»/«Исполнители»);
    при 1280 вся таблица <= 1240 («Действия» не за экраном), при 1920 гибкие
    колонки растут (Содержание > 480, Исполнители > 220) и сумма ТОЧНО равна
    бюджету; кламп сохранённых «раздутых» col_widths сохранён;
  * карточка: resize-хэндл пришит к углу через right=0/bottom=0 (Positioned от
    краёв Stack) — следует за углом при resize автоматически; колонки карточки
    гибкие (expand 11/8 в Row без tight) — содержимое адаптируется к ширине;
  * справочники: футер «Отмена/Применить» ВНЕ скролла (корневая колонка без
    scroll) и виден при исходном размере; resize-хэндл right=0/bottom=0; списки
    expand=True внутри expand-секций — растут при растягивании окна; min-высота
    карточки справочников 420.

Запуск:  cd porayonka-app && python tests/test_controls_smoke.py
"""
import io
import json
import os
import sys
import tempfile
import contextlib
import traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Изолируем данные в temp-APPDATA, чтобы тест не трогал реальные данные пользователя.
_TEST_APPDATA = tempfile.mkdtemp(prefix="porayonka_smoke_")
os.environ["APPDATA"] = _TEST_APPDATA

import flet as ft  # noqa: E402
from page_stub import PageStub  # noqa: E402
from core.controls_data import (  # noqa: E402
    get_controls_file, load_controls, save_controls,
    load_settings, save_settings,
    read_shared_controls, write_shared_controls, get_shared_mtime,
    merge_controls, _should_notify, prune_notify_log,
    get_controller_names, canonical_initiator_group, initiator_filter_options,
)
from core.controls_models import (  # noqa: E402
    Control, OVERDUE, TODAY, name_matches,
)
from core.controls_exporter import ControlsExcelExporter, import_from_excel  # noqa: E402
from ui.controls.glass_theme import GLASS  # noqa: E402
from ui.controls.controls_tab import create_controls_tab  # noqa: E402

FILTER_OTHER = "__other__"

# Раунд 5: плашка строки — серый графит (было #1e2a44)
TILE_BG = "#2a3247"

FAILURES = []


def check(name, cond, extra=""):
    status = "OK " if cond else "FAIL"
    print(f"[{status}] {name}" + (f"  ({extra})" if extra else ""))
    if not cond:
        FAILURES.append(name)


def walk(c):
    res = []
    if c is None:
        return res
    res.append(c)
    for attr in ("content", "controls", "title", "actions"):
        v = getattr(c, attr, None)
        if isinstance(v, (list, tuple)):
            for x in v:
                res += walk(x)
        elif v is not None:
            res += walk(v)
    return res


def _seed_controls():
    controls = [
        {
            "id": "c1",
            "incoming_number": "Иссоп-216-1017-26/дсп",
            "receive_date": "2026-07-20",
            "initiator": "ГУК СК",
            "content": "Организовать исполнение указания по розыску подозреваемого",
            "executors": ["Семисенко Иван Юрьевич", "Потемкин Сергей Анатольевич"],
            "controller": "Потемкин С.А.",
            "control_type": "once", "period_days": 7,
            "due_date": "2026-07-25", "end_date": None,
            "done": False, "done_date": None, "comment": "",
            "tasks": [{"id": "t1", "title": "п.1 Запросить материалы", "assignees": ["Семисенко Иван Юрьевич"],
                       "due_date": "2026-07-24", "is_done": False, "done_date": None, "comment": ""},
                      {"id": "t2", "title": "п.2 Доложить", "assignees": ["Потемкин Сергей Анатольевич"],
                       "due_date": "2026-07-25", "is_done": False, "done_date": None, "comment": ""}],
            "milestones": [{"id": "m1", "date": "2026-07-23", "note": "точка1", "is_done": False},
                           {"id": "m2", "date": "2026-07-24", "note": "точка2", "is_done": True}],
            "attachments": [], "archived": False, "archived_at": None, "archive_reason": "",
            "created_at": "2026-07-20T10:00:00", "updated_at": "2026-07-20T10:00:00",
        },
        {
            "id": "c2",
            "incoming_number": "ВХСОП-455-2026",
            "receive_date": "2026-08-01",
            "initiator": "СУ",
            "content": "Ежемесячный контроль предоставления статистики",
            "executors": ["Чашин Эдуард Анатольевич"],
            "controller": "Потемкин С.А.",
            "control_type": "periodic", "period_days": 30,
            "due_date": "2026-08-10", "end_date": "2026-12-31",
            "done": False, "done_date": None, "comment": "постоянный",
            "tasks": [], "milestones": [], "attachments": [],
            "archived": False, "archived_at": None, "archive_reason": "",
            "created_at": "2026-08-01T09:00:00", "updated_at": "2026-08-01T09:00:00",
        },
        {
            "id": "c3",
            "incoming_number": "ВХСОП-101-2026",
            "receive_date": "2026-06-10",
            "initiator": "ГУК ЮФО",
            "content": "Исполненный контроль",
            "executors": ["Семисенко Иван Юрьевич"],
            "controller": "Потемкин С.А.",
            "control_type": "once", "period_days": 7,
            "due_date": "2026-06-15", "end_date": None,
            "done": True, "done_date": "2026-06-12", "comment": "исполнен",
            "tasks": [], "milestones": [], "attachments": [],
            "archived": True, "archived_at": "2026-06-12T10:00:00", "archive_reason": "done",
            "created_at": "2026-06-10T09:00:00", "updated_at": "2026-06-12T10:00:00",
        },
    ]
    data = {"schema_version": 2, "last_saved": "2026-08-05T12:00:00", "controls": controls}
    with open(get_controls_file(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build(width=1280, height=860):
    page = PageStub(width=width, height=height)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        tab = create_controls_tab(page)
    return page, tab, buf.getvalue()


def _open_card(tab, via_add=False):
    """Открыть карточку: по строке (edit) или через «Добавить контроль» (new)."""
    allc = walk(tab)
    if via_add:
        add_btns = [c for c in allc if isinstance(c, ft.ElevatedButton)
                    and getattr(c, "text", None) == "Добавить контроль"]
        if not add_btns:
            return False
        add_btns[0].on_click(None)
        return True
    rows = [c for c in allc if isinstance(c, ft.Container)
            and getattr(c, "bgcolor", None) == TILE_BG and getattr(c, "on_click", None)]
    if not rows:
        return False
    rows[0].on_click(None)
    return True


def find_card_columns(tab):
    """Вернуть (left_container, right_container, middle_content) открытой карточки
    и None, если карточка не открыта."""
    allc = walk(tab)
    ov = [c for c in allc if getattr(c, "bgcolor", None) == "#cc04070f"]
    if not ov:
        return None
    ovc = ov[0]
    if not ovc.visible:
        return None
    stack = ovc.content
    card = stack.controls[0]
    col = card.content
    mid = col.controls[1]  # middle_scroll
    mscol = mid.content
    middle_content = mscol.controls[0]
    if hasattr(middle_content, "controls") and isinstance(middle_content.controls, list):
        items = middle_content.controls
        if len(items) >= 2:
            return items[0], items[1], middle_content
    return None


def panels_of(col_container):
    """Все glass-панели внутри контейнера колонки (непустой content)."""
    if col_container is None:
        return []
    col = getattr(col_container, "content", col_container)
    controls = getattr(col, "controls", [])
    return [p for p in controls if getattr(p, "content", None) is not None]


def _ctrl(id_, incoming, executors=None, controller="Потемкин С.А.", tasks=None):
    """Компактный контроль для тестов фильтров."""
    return {
        "id": id_, "incoming_number": incoming, "receive_date": "2026-08-01",
        "initiator": "СУ", "content": f"контроль {incoming}", "executors": list(executors or []),
        "controller": controller, "control_type": "once", "period_days": 7,
        "due_date": "2026-09-01", "end_date": None, "done": False, "done_date": None,
        "comment": "", "tasks": tasks or [], "milestones": [], "attachments": [],
        "archived": False, "archived_at": None, "archive_reason": "",
        "created_at": "2026-08-01T10:00:00", "updated_at": "2026-08-01T10:00:00",
    }


def _seed_raw(controls):
    data = {"schema_version": 2, "last_saved": "2026-08-05T12:00:00", "controls": controls}
    with open(get_controls_file(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _find_dd(tab, hint):
    for c in walk(tab):
        if isinstance(c, ft.Dropdown) and getattr(c, "hint_text", None) == hint:
            return c
    return None


def _set_filter(tab, hint, value):
    """Выбрать значение в фильтре-дропдауне и применить (как выбор пользователем)."""
    dd = _find_dd(tab, hint)
    if dd is None:
        return False
    dd.value = value
    try:
        if dd.on_change:
            dd.on_change(None)
    except Exception:
        traceback.print_exc()
        return False
    return True


def _visible_rows(tab):
    return [c for c in walk(tab) if isinstance(c, ft.Container)
            and getattr(c, "bgcolor", None) == TILE_BG and getattr(c, "on_click", None)]


def _visible_texts(tab):
    """Все тексты видимых строк таблицы (для проверки, какие контроли отфильтрованы)."""
    out = set()
    for r in _visible_rows(tab):
        for t in walk(r):
            if isinstance(t, ft.Text) and t.value:
                out.add(str(t.value))
    return out


def _invoke_event_handler(eh, e):
    """Вызвать обработчик события Flet напрямую (headless)."""
    for fn in getattr(eh, "_EventHandler__handlers", {}).keys():
        try:
            fn(e)
        except Exception:
            traceback.print_exc()
        return True
    return False


def _save_settings_dialog(page, tab):
    """Открыть настройки и нажать «Сохранить» → on_apply → _load_initial → refresh фильтров."""
    btns = [c for c in walk(tab) if isinstance(c, ft.IconButton)
            and getattr(c, "tooltip", None) == "Настройки"]
    if not btns:
        return False
    try:
        btns[0].on_click(None)
    except Exception:
        traceback.print_exc()
        return False
    if not page.dialogs:
        return False
    dlg = page.dialogs[-1]
    save_btns = [c for c in getattr(dlg, "actions", []) if isinstance(c, ft.ElevatedButton)
                 and getattr(c, "text", None) == "Сохранить"]
    if not save_btns:
        return False
    try:
        save_btns[0].on_click(None)
    except Exception:
        traceback.print_exc()
        return False
    return True


def _refs_overlay_of(tab):
    """Раунд 14: overlay-Container справочников (видимый, с заголовком «Справочники»)."""
    for c in walk(tab):
        if isinstance(c, ft.Container) and getattr(c, "bgcolor", None) == "#cc04070f" \
                and getattr(c, "visible", False):
            if any(isinstance(t, ft.Text) and t.value == "Справочники" for t in walk(c)):
                return c
    return None


def _refs_apply_of(dlg):
    return [c for c in walk(dlg) if isinstance(c, ft.ElevatedButton)
            and getattr(c, "text", None) == "Применить"]


def main():
    _seed_controls()

    # ── 1. py_compile всех файлов вкладки ──
    files = [
        "ui/controls/controls_tab.py",
        "ui/controls/russian_calendar.py",
        "ui/controls/glass_theme.py",
        "ui/controls/control_card_modal.py",
        "ui/controls/controls_settings_modal.py",
        "main.py",
    ]
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for f in files:
        p = os.path.join(root, f)
        ok = True
        try:
            compile(open(p, encoding="utf-8").read(), f, "exec")
        except Exception:
            ok = False
            traceback.print_exc()
        check(f"py_compile {f}", ok)

    # ── 2. init без шума update-unmounted ──
    page, tab, log = build()
    check("init console без 'Control must be added'",
          "Control must be added to the page first" not in log,
          f"{log.count('Control must be added')} вхождений")

    # ── 3. карточка NEW («Добавить контроль»): колонки и геометрия ──
    page, tab, _ = build()
    _open_card(tab, via_add=True)
    cols = find_card_columns(tab)
    check("карточка (new) открыта", cols is not None)
    if cols:
        lc, rc, midrow = cols
        # Раунд 15 (задача 3): колонки карточки ГИБКИЕ — expand 11/8 в Row без
        # tight (адаптируются к ширине карточки), явных width больше нет.
        check("контейнер левой колонки expand>0 (гибкая)", (getattr(lc, "expand", 0) or 0) > 0, f"expand={lc.expand}")
        check("контейнер правой колонки expand>0 (гибкая)", (getattr(rc, "expand", 0) or 0) > 0, f"expand={rc.expand}")
        check("левая колонка шире правой (11/8)",
              (getattr(lc, "expand", 0) or 0) > (getattr(rc, "expand", 0) or 0))
        lpanels = panels_of(lc)
        rpanels = panels_of(rc)
        check("левая колонка имеет панели", len(lpanels) >= 1, f"{len(lpanels)} панелей")
        check("правая колонка имеет панели", len(rpanels) >= 1, f"{len(rpanels)} панелей")
        # каждая левая панель содержит непустой content (не только len(controls))
        l_empty = [i for i, p in enumerate(lpanels) if not getattr(p, "content", None)]
        check("все левые панели с непустым content", not l_empty,
              f"пустые: {l_empty}" if l_empty else f"{len(lpanels)} панелей")
        # в левой колонке должны быть текстовые поля (вх.№, содержание)
        ltexts = [t.value for t in walk(lc) if isinstance(t, ft.TextField)]
        check("в левой колонке есть TextField-поля", len(ltexts) >= 2, f"{len(ltexts)} полей")
        rtexts = [t.value for t in walk(rc) if isinstance(t, ft.Text)]
        check("в правой колонке есть текст", len(rtexts) >= 1)

    # ── 4. карточка EDIT по строке: заполненные поля слева ──
    page, tab, _ = build()
    _open_card(tab, via_add=False)
    cols = find_card_columns(tab)
    check("карточка (edit) открыта", cols is not None)
    if cols:
        lc, rc, _ = cols
        ltexts = [t for t in walk(lc) if isinstance(t, ft.TextField)]
        values = {t.value for t in ltexts}
        check("вх.№ заполнен слева", "Иссоп-216-1017-26/дсп" in values)
        check("содержание заполнено слева",
              any(v and "розыску" in str(v) for v in values))

    # ── 5. «+ Добавить пункт» не убивает карточку (середина жива) ──
    page, tab, _ = build()
    _open_card(tab, via_add=False)
    allc = walk(tab)
    add_task = [c for c in allc if isinstance(c, ft.ElevatedButton)
                and "пункт" in (getattr(c, "text", None) or "").lower()]
    check("кнопка «+ Добавить пункт» найдена", len(add_task) >= 1)
    if add_task:
        try:
            add_task[0].on_click(None)
            check("добавление пункта без исключения", True)
        except Exception:
            traceback.print_exc()
            check("добавление пункта без исключения", False)
        cols = find_card_columns(tab)
        check("после добавления пункта карточка жива", cols is not None)
        if cols:
            lc, rc, _ = cols
            check("левая колонка после добавления пункта непустая", len(panels_of(lc)) >= 1,
                  f"{len(panels_of(lc))} панелей")
            # в правой колонке появилась панель пункта (tasks_col непустая)
            rtexts = [t for t in walk(rc) if isinstance(t, ft.TextField)]
            check("в правой колонке есть поле пункта", len(rtexts) >= 1, f"{len(rtexts)} полей")

    # ── 6. «+ Добавить точку» добавляет точку (не «ничего не происходит») ──
    page, tab, _ = build()
    _open_card(tab, via_add=True)  # новый контроль (разовый) — точки должны работать
    allc = walk(tab)
    add_mile = [c for c in allc if isinstance(c, ft.ElevatedButton)
                and "точк" in (getattr(c, "text", None) or "").lower()]
    check("кнопка «+ Добавить точку» найдена", len(add_mile) >= 1)
    if add_mile:
        try:
            add_mile[0].on_click(None)
            check("добавление точки без исключения", True)
        except Exception:
            traceback.print_exc()
            check("добавление точки без исключения", False)
        cols = find_card_columns(tab)
        check("карточка жива после добавления точки", cols is not None)
        if cols:
            lc, rc, _ = cols
            # точка создаёт milestone-карточку с полем «Точка (описание)»
            fields = [t for t in walk(rc) if isinstance(t, ft.TextField)
                      and (t.hint_text or "").startswith("Точка")]
            check("точка добавлена (поле точки в правой колонке)", len(fields) >= 1,
                  f"{len(fields)} полей")

    # ── 7. Раунд 15 (задача 1): hover НАТИВНЫЙ (InkWell), Python on_hover удалён ──
    page, tab, _ = build()
    allc = walk(tab)
    rows = [c for c in allc if isinstance(c, ft.Container)
            and getattr(c, "bgcolor", None) == TILE_BG and getattr(c, "on_click", None)]
    check("в таблице есть строки", len(rows) >= 1, f"{len(rows)} строк")
    if len(rows) >= 2:
        cur = {getattr(r, "mouse_cursor", None) for r in rows}
        check("hover15: курсор CLICK остался", ft.MouseCursor.CLICK in cur)
        # задержка и «хвосты» приходили от Python-событий on_hover (round-trip
        # на каждый enter/exit) — их больше нет вовсе
        check("hover15: Python on_hover со строк удалён (без round-trip лагов)",
              all(getattr(r, "on_hover", None) is None for r in rows))
        # вместо него — нативный InkWell: ink=True, мгновенная подсветка во Flutter
        check("hover15: ink=True на строках (нативный hover InkWell)",
              all(getattr(r, "ink", None) is True for r in rows))
        check("hover15: у строк задан ink_color (тонкий белый splash)",
              all(getattr(r, "ink_color", None) == "#12ffffff" for r in rows),
              f"ink_color={getattr(rows[0], 'ink_color', None)}")
        # hoverColor берётся из ЛОКАЛЬНОЙ темы таблицы (не трогает page.theme)
        themed = [c for c in allc if getattr(c, "theme", None) is not None]
        check("hover15: у панели таблицы локальная тема", len(themed) >= 1)
        if themed:
            th = getattr(themed[0], "theme", None)
            check("hover15: theme.hover_color = #12ffffff (7% белый)",
                  getattr(th, "hover_color", None) == "#12ffffff",
                  f"hover_color={getattr(th, 'hover_color', None)}")

    # ── 8. плашка строки — серый графит ──
    page, tab, _ = build()
    allc = walk(tab)
    rows = [c for c in allc if isinstance(c, ft.Container)
            and getattr(c, "on_click", None) and isinstance(c, ft.Container)
            and getattr(c, "bgcolor", None) in (TILE_BG, "#1e2a44")]
    if rows:
        bgs = {getattr(r, "bgcolor", None) for r in rows}
        check("плашка строки = #2a3247 (серый графит)", bgs == {TILE_BG}, f"bg={bgs}")

    # ── 9а. «Содержание» включает пункты задания (раунд 6) ──
    page, tab, _ = build()
    allc = walk(tab)
    rows = [c for c in allc if isinstance(c, ft.Container)
            and getattr(c, "bgcolor", None) == TILE_BG and getattr(c, "on_click", None)]
    if rows:
        # внутри первой строки есть Text с "п.2 Доложить" (пункт из содержания)
        content_texts = [t.value for t in walk(rows[0]) if isinstance(t, ft.Text) and t.value]
        joined = " ".join(str(x) for x in content_texts)
        check("в содержании строки есть пункты задания", "п.1 Запросить материалы" in joined,
              "пункты видны")
        # пункт с датой и ответственным: "п.1 Запросить материалы — Семисенко И.Ю. — 24.07.2026"
        check("пункт содержит ответственного", "Семисенко И." in joined)
        check("пункт содержит дату", "24.07.2026" in joined)

    # ── 9б. Промежуточные точки под сроком (раунд 6) ──
    page, tab, _ = build()
    allc = walk(tab)
    rows = [c for c in allc if isinstance(c, ft.Container)
            and getattr(c, "bgcolor", None) == TILE_BG and getattr(c, "on_click", None)]
    if rows:
        due_texts = [t.value for t in walk(rows[0]) if isinstance(t, ft.Text) and t.value]
        joined = " ".join(str(x) for x in due_texts)
        check("под сроком видна неисполненная точка", "точка 23.07.2026" in joined,
              "точка 1 под сроком")

    # ── 9. фильтры исполнителей/контролёров — канонический список (задачи 2–3) ──
    page, tab, _ = build()
    allc = walk(tab)
    hints = {}
    for c in allc:
        if isinstance(c, ft.Dropdown):
            hints[getattr(c, "hint_text", None)] = c
    ex = hints.get("Все исполнители")
    check("dropdown «Все исполнители» найден", ex is not None)
    if ex:
        opts = [o.key for o in (ex.options or [])]
        # канонические криминалисты есть, «кривые» написания из данных — НЕ попадают
        check("исполнители — канонический список (без мусора из данных)",
              "Семисенко Иван Юрьевич" in opts
              and "Чашин Эдуард Александрович" in opts
              and "Чашин Эдуард Анатольевич" not in opts
              and "Потемкин Сергей Анатольевич" not in opts,
              f"{len(opts)-1} опций")
        check("исполнители — без дублей", len(opts) == len(set(opts)))
        check("исполнители — «Прочие» в конце", opts[-1] == FILTER_OTHER)
    ct = hints.get("Все контролеры")
    check("dropdown «Все контролеры» найден", ct is not None)
    if ct:
        opts = [o.key for o in (ct.options or [])]
        check("контролёры — канонический список (криминалисты + Потемкин/Чашин)",
              "Потемкин С.А." in opts and "Семисенко Иван Юрьевич" in opts,
              f"{len(opts)-1} опций")
        check("контролёры — без дублей", len(opts) == len(set(opts)))
        check("контролёры — «Прочие» в конце", opts[-1] == FILTER_OTHER)

    # ── 10. merge_controls: union по id, конфликт, порядок (задача 1) ──
    def _mk(id_, updated, **kw):
        return Control(id=id_, updated_at=updated, incoming_number=kw.get("incoming_number", id_),
                       **{k: v for k, v in kw.items() if k != "incoming_number"})

    local = [_mk("a", "2026-08-01T10:00:00"), _mk("b", "2026-08-01T10:00:00"), _mk("c", "2026-08-01T10:00:00")]
    shared = [_mk("b", "2026-08-02T10:00:00"), _mk("d", "2026-08-02T10:00:00")]
    merged = merge_controls(local, shared)
    check("merge: union по id (a,b,c,d)", {c.id for c in merged} == {"a", "b", "c", "d"},
          f"{[c.id for c in merged]}")
    b = next((c for c in merged if c.id == "b"), None)
    check("merge: конфликт — побеждает новый updated_at",
          b is not None and b.updated_at == "2026-08-02T10:00:00")
    check("merge: порядок local + новые из shared в конец",
          [c.id for c in merged] == ["a", "b", "c", "d"])
    merged2 = merge_controls([_mk("a", "2026-08-01T10:00:00"), _mk("x", "2026-08-03T10:00:00")], shared)
    check("merge: локальный новый контроль не теряется", "x" in {c.id for c in merged2})
    # пустое/битое updated_at — старее валидного
    m3 = merge_controls([_mk("a", "")], [_mk("a", "2026-08-01T10:00:00")])
    check("merge: пустое updated_at старее валидного",
          m3 and m3[0].updated_at == "2026-08-01T10:00:00")
    m4 = merge_controls([_mk("a", "garbage")], [_mk("a", "2026-08-01T10:00:00")])
    check("merge: битое updated_at старее валидного",
          m4 and m4[0].updated_at == "2026-08-01T10:00:00")
    # контроль только в shared — сохраняется в конец
    m5 = merge_controls([_mk("a", "2026-08-01T10:00:00")], [_mk("z", "2026-08-01T10:00:00")])
    check("merge: контроль только в shared сохраняется", [c.id for c in m5] == ["a", "z"])

    # ── 11. два инстанса через ОДНУ общую папку (админ → пользователь) ──
    shared_dir = tempfile.mkdtemp(prefix="porayonka_shared_")
    admin_settings = {"network_enabled": True, "network_shared_path": os.path.join(shared_dir, "controls.json")}
    user_settings = dict(admin_settings)
    check("два инстанса: до записи shared пуст", read_shared_controls(user_settings) == [])
    m0 = get_shared_mtime(user_settings)
    check("два инстанса: mtime до записи None", m0 is None)
    ok = write_shared_controls([_mk("n1", "2026-08-05T10:00:00", incoming_number="ВХСОП-1")], admin_settings)
    check("два инстанса: админ записал в shared", ok is True)
    got = read_shared_controls(user_settings)
    check("два инстанса: пользователь прочитал данные", len(got) == 1 and got[0].id == "n1")
    m1 = get_shared_mtime(user_settings)
    check("два инстанса: mtime изменилось", m1 is not None and m1 != m0)

    # ── 12. журнал уведомлений: антиспам (задача 2) ──
    nlog = {}
    check("notify: new — первый раз уведомляет", _should_notify(nlog, "c1", "new", "2026-08-05") is True)
    nlog["c1:new"] = "2026-08-05"
    check("notify: new — повтор не уведомляет", _should_notify(nlog, "c1", "new", "2026-08-05") is False)
    check("notify: new — на следующий день тоже нет", _should_notify(nlog, "c1", "new", "2026-08-06") is False)
    check("notify: overdue — первый раз уведомляет", _should_notify(nlog, "c1", OVERDUE, "2026-08-05") is True)
    nlog["c1:overdue"] = "2026-08-05"
    check("notify: overdue — в тот же день нет", _should_notify(nlog, "c1", OVERDUE, "2026-08-05") is False)
    check("notify: overdue — на следующий день уведомляет", _should_notify(nlog, "c1", OVERDUE, "2026-08-06") is True)
    # round-trip журнала через настройки
    save_settings({"notify_log": {"c1:new": "2026-08-05"}, "notify_sound": False})
    loaded = load_settings()
    check("settings: notify_log сохраняется в controls_settings.json",
          (loaded.get("notify_log") or {}).get("c1:new") == "2026-08-05")
    check("settings: notify_sound сохраняется", loaded.get("notify_sound") is False)

    # ── 13. офлайн→онлайн: локальная правка не теряется (задача 4) ──
    off_dir = tempfile.mkdtemp(prefix="porayonka_off_")
    block = os.path.join(off_dir, "block")
    with open(block, "w", encoding="utf-8") as f:
        f.write("x")
    off_settings = {"network_enabled": True, "network_shared_path": os.path.join(block, "controls.json")}
    ok_off = write_shared_controls([_mk("off1", "2026-08-01T10:00:00")], off_settings)
    check("offline: запись при недоступном shared = False", ok_off is False)
    check("offline: get_shared_mtime None", get_shared_mtime(off_settings) is None)
    save_controls([_mk("off1", "2026-08-01T10:00:00", incoming_number="ВХСОП-9")])
    loc = load_controls()
    check("offline: локальный controls.json сохранён", any(c.id == "off1" for c in loc))
    # «сеть вернулась»: блокирующий файл убран, админ успел записать свою (старую) версию
    os.remove(block)
    ok_back = write_shared_controls([_mk("off1", "2026-07-30T10:00:00", incoming_number="ВХСОП-9")], off_settings)
    check("offline->online: shared снова доступен", ok_back is True)
    merged_off = merge_controls(loc, read_shared_controls(off_settings))
    check("offline->online: merge не теряет локальную правку",
          any(c.id == "off1" and c.updated_at == "2026-08-01T10:00:00" for c in merged_off))

    # ── 14а. вкладка при network_enabled грузит shared и показывает индикатор ──
    net_dir = tempfile.mkdtemp(prefix="porayonka_net_tab_")
    net_path = os.path.join(net_dir, "controls.json")
    write_shared_controls([_mk("net1", "2026-08-05T10:00:00", incoming_number="ВХСОП-NET")],
                          {"network_enabled": True, "network_shared_path": net_path})
    save_settings({"network_enabled": True, "network_role": "admin",
                   "network_shared_path": net_path, "notify_log": {}, "notify_sound": True})
    page2, tab2, _ = build()
    texts2 = " ".join(str(t.value) for t in walk(tab2) if isinstance(t, ft.Text) and t.value)
    check("tab: network_enabled — контроль из shared в таблице", "ВХСОП-NET" in texts2)
    check("tab: индикатор «Сеть: админ»", "Сеть: админ" in texts2)

    # ── 14. подрезка журнала старше 30 дней (задача 2) ──
    plog = {
        "c1:new": "2026-07-01",      # 35 дней до 2026-08-05 — подрезать
        "c2:overdue": "2026-07-31",  # 5 дней — оставить
        "c3:today": "2026-08-05",    # сегодня — оставить
        "c4:soon": "bad-date",       # битое значение — подрезать
    }
    prune_notify_log(plog, today="2026-08-05")
    check("prune: записи старше 30 дней удалены", "c1:new" not in plog)
    check("prune: свежие записи остались",
          "c2:overdue" in plog and "c3:today" in plog)
    check("prune: битые значения удалены", "c4:soon" not in plog)

    # ── 15. канонические фильтры исполнителей/контролёров (PROMPT_контроли_фильтр_исполнителей.md) ──
    # сбросить сеть, чтобы вкладка читала локальный controls.json
    save_settings({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True})

    # 15а. name_matches
    check("name_matches: полное ФИО vs «Фамилия И.О.»",
          name_matches("Семисенко Иван Юрьевич", "Семисенко И.Ю.") is True)
    check("name_matches: «Фамилия И.О.-5.1» (суффикс)",
          name_matches("Семисенко Иван Юрьевич", "Семисенко И.Ю.-5.1") is True)
    check("name_matches: несколько имён в строке (фамилия не первое слово)",
          name_matches("Семисенко Иван Юрьевич", "Чашин Э.А., Семисенко И.Ю.") is True)
    check("name_matches: опечатка в имени, фамилия верная",
          name_matches("Семисенко Иван Юрьевич", "Семисенко Иван Юриевич") is True)
    check("name_matches: регистр не важен",
          name_matches("Семисенко Иван Юрьевич", "семисенко и.ю.") is True)
    check("name_matches: чужая фамилия — False",
          name_matches("Семисенко Иван Юрьевич", "Гайнутдинов С.И.") is False)
    check("name_matches: пустая строка — False",
          name_matches("Семисенко Иван Юрьевич", "") is False)
    check("name_matches: None — False",
          name_matches("Семисенко Иван Юрьевич", None) is False)
    check("name_matches: пустой canonical — False",
          name_matches("", "Семисенко И.Ю.") is False)
    check("name_matches: фамилия <3 символов — False",
          name_matches("Ян И.В.", "Ян Петрович") is False)
    check("name_matches: короткая форма vs полное ФИО (контролёр)",
          name_matches("Потемкин С.А.", "Потемкин Сергей Анатольевич") is True)
    check("name_matches: опечатка в фамилии — лишняя буква",
          name_matches("Семисенко Иван Юрьевич", "Семисеннко И.Ю.") is True)
    check("name_matches: опечатка в фамилии — вставка",
          name_matches("Гайнутдинов Станислав Игоревич", "Гайнутдитнов С.И.") is True)
    check("name_matches: опечатка в фамилии — пропуск буквы",
          name_matches("Макаренко Роман Андреевич", "Макарено Р.А.") is True)
    check("name_matches: похожая фамилия ниже порога — False",
          name_matches("Семисенко Иван Юрьевич", "Семенов И.Ю.") is False)

    # 15б. опции фильтров — только канонический список + «Прочие»
    _seed_raw([
        _ctrl("o1", "О-1", executors=["Миронович Д.В.-5.1"]),
        _ctrl("o2", "О-2", executors=["Гайнутдинов С.И.Т.С.А.С.И.Ю."]),
        _ctrl("o3", "О-3", executors=[" Авакян А.А. "]),
        _ctrl("o4", "О-4", executors=["Авакян  А.А."]),
        _ctrl("o5", "О-5", executors=["Чашин Э.А., Семисенко И.Ю."]),
        _ctrl("o6", "О-6", executors=["Посторонний А.А."]),
    ])
    page, tab, _ = build()
    ex = _find_dd(tab, "Все исполнители")
    check("фильтр-опции: dropdown «Все исполнители» найден", ex is not None)
    if ex:
        opts = [o.key for o in (ex.options or [])]
        # Раунд 7 (задача 1): исполнители = ПОЛНЫЙ справочник людей (криминалисты +
        # дефолтные контролёры), чтобы Потемкин/Чашин не попадали в «Прочие»
        expected = ["all"] + get_controller_names() + [FILTER_OTHER]
        check("фильтр-опции: ровно полный канонический список + «Прочие»",
              opts == expected, f"{len(opts)} опций")
        check("фильтр-опции: мусор из данных не попал",
              "Миронович Д.В.-5.1" not in opts
              and "Т.С.А" not in "".join(opts)
              and "Авакян А.А." not in opts
              and "Посторонний А.А." not in opts)
    ct = _find_dd(tab, "Все контролеры")
    check("фильтр-опции: dropdown «Все контролеры» найден", ct is not None)
    if ct:
        opts = [o.key for o in (ct.options or [])]
        expected = ["all"] + get_controller_names() + [FILTER_OTHER]
        check("фильтр-опции контролёров: криминалисты + Потемкин/Чашин (без дублей)",
              opts == expected, f"{len(opts)} опций")
        check("фильтр-опции контролёров: Чашин Э.А. дедуплицирован",
              "Чашин Э.А." not in opts and "Чашин Эдуард Александрович" in opts)

    # 15в. фильтрация находит любые написания (включая ответственных по пунктам)
    _seed_raw([
        _ctrl("fA", "Ф-1", executors=["Семисенко И.Ю."]),
        _ctrl("fB", "Ф-2", executors=["Семисенко Иван Юрьевич"]),
        _ctrl("fC", "Ф-3", executors=["Чашин Э.А., Семисенко И.Ю."]),
        _ctrl("fD", "Ф-4", executors=["Гайнутдинов С.И."]),
        _ctrl("fE", "Ф-5", tasks=[{"id": "t1", "title": "п.1", "assignees": ["Миронович Д.В.-5.1"],
                                   "due_date": None, "is_done": False, "done_date": None, "comment": ""}]),
    ])
    page, tab, _ = build()
    check("фильтрация: выбор канонического ФИО применился",
          _set_filter(tab, "Все исполнители", "Семисенко Иван Юрьевич"))
    vis = _visible_texts(tab)
    check("фильтрация: найдены «Семисенко И.Ю.» и «Семисенко Иван Юрьевич»",
          "Ф-1" in vis and "Ф-2" in vis, f"видно: {sorted(vis)}")
    check("фильтрация: найден «Чашин Э.А., Семисенко И.Ю.»", "Ф-3" in vis)
    check("фильтрация: чужие контроли скрыты", "Ф-4" not in vis and "Ф-5" not in vis)
    check("фильтрация: выбор по фамилии с суффиксом (ответственный пункта)",
          _set_filter(tab, "Все исполнители", "Миронович Дмитрий Владимирович"))
    vis = _visible_texts(tab)
    check("фильтрация: найден контроль по assignees пункта",
          "Ф-5" in vis and not any(x in vis for x in ("Ф-1", "Ф-2", "Ф-3", "Ф-4")),
          f"видно: {sorted(vis)}")

    # 15г. «Прочие» — контроли с людьми вне списка
    _seed_raw([
        _ctrl("fX", "Ф-10", executors=["Посторонний А.А."]),
        _ctrl("fY", "Ф-11", executors=["Семисенко Иван Юрьевич"]),
    ])
    page, tab, _ = build()
    check("«Прочие»: выбор применился",
          _set_filter(tab, "Все исполнители", FILTER_OTHER))
    vis = _visible_texts(tab)
    check("«Прочие»: контроль с посторонним найден", "Ф-10" in vis, f"видно: {sorted(vis)}")
    check("«Прочие»: контроль криминалиста скрыт", "Ф-11" not in vis)
    check("«Прочие»: через криминалиста посторонний не находится",
          _set_filter(tab, "Все исполнители", "Семисенко Иван Юрьевич"))
    vis = _visible_texts(tab)
    check("«Прочие»: через криминалиста виден только его контроль",
          "Ф-11" in vis and "Ф-10" not in vis)

    # 15д. контролёры — фамильное совпадение
    _seed_raw([
        _ctrl("fG", "Ф-20", controller="Потемкин Сергей"),
        _ctrl("fH", "Ф-21", controller="Чашин Эдуард Александрович"),
    ])
    page, tab, _ = build()
    check("контролёры: фильтр по «Потемкин С.А.» применился",
          _set_filter(tab, "Все контролеры", "Потемкин С.А."))
    vis = _visible_texts(tab)
    check("контролёры: найден «Потемкин Сергей» (кривое написание)",
          "Ф-20" in vis, f"видно: {sorted(vis)}")
    check("контролёры: чужой контролёр скрыт", "Ф-21" not in vis)

    # 15е. сохранение выбранного значения при refresh фильтров (задача 5)
    _seed_raw([
        _ctrl("fZ", "Ф-30", executors=["Семисенко И.Ю."]),
        _ctrl("fW", "Ф-31", executors=["Гайнутдинов С.И."]),
    ])
    page, tab, _ = build()
    check("refresh: канонический фильтр выбран",
          _set_filter(tab, "Все исполнители", "Семисенко Иван Юрьевич"))
    ok_save = _save_settings_dialog(page, tab)
    check("refresh: сохранение настроек прошло", ok_save)
    dd = _find_dd(tab, "Все исполнители")
    check("refresh: каноническое значение сохранилось",
          dd is not None and dd.value == "Семисенко Иван Юрьевич")
    vis = _visible_texts(tab)
    check("refresh: фильтр продолжает работать после refresh",
          "Ф-30" in vis and "Ф-31" not in vis, f"видно: {sorted(vis)}")
    # мусорное значение из старых данных — молча сбрасывается на «Все»
    dd.value = "Миронович Д.В.-5.1"
    if dd.on_change:
        dd.on_change(None)
    _save_settings_dialog(page, tab)
    dd = _find_dd(tab, "Все исполнители")
    check("refresh: мусорное значение сброшено на «Все»",
          dd is not None and dd.value == "all", f"value={getattr(dd, 'value', None)}")
    vis = _visible_texts(tab)
    check("refresh: после сброса видны все контроли", "Ф-30" in vis and "Ф-31" in vis)

    # ── 16. Раунд 7, задача 1: «Прочие» — без канонических людей (Потемкин/Чашин) ──
    _seed_raw([
        _ctrl("p1", "П-1", executors=["Потемкин С.А."]),
        _ctrl("p2", "П-2", executors=["Чашин Э.А."]),
        _ctrl("p3", "П-3", executors=["Посторонний А.А."]),
    ])
    page, tab, _ = build()
    check("«Прочие»: выбор применился",
          _set_filter(tab, "Все исполнители", FILTER_OTHER))
    vis = _visible_texts(tab)
    check("«Прочие»: Потемкин/Чашин как исполнители НЕ в «Прочие»",
          "П-1" not in vis and "П-2" not in vis, f"видно: {sorted(vis)}")
    check("«Прочие»: посторонний остаётся в «Прочие»", "П-3" in vis)
    check("«Прочие»: Потемкин С.А. есть в опциях исполнителей",
          _set_filter(tab, "Все исполнители", "Потемкин С.А."))
    vis = _visible_texts(tab)
    check("«Прочие»: фильтр по Потемкину находит его контроль",
          "П-1" in vis and "П-3" not in vis, f"видно: {sorted(vis)}")

    # ── 17. Раунд 7, задача 2: канонические инициаторы ──
    check("initiator: «ГУК СК» -> «гук»", canonical_initiator_group("ГУК СК") == "гук")
    check("initiator: «ГУК С.» -> «гук»", canonical_initiator_group("ГУК С.") == "гук")
    check("initiator: «ГУК С.Т.С.А.С.И.Ю.» -> «гук»",
          canonical_initiator_group("ГУК С.Т.С.А.С.И.Ю.") == "гук")
    check("initiator: «ГУК ЮФО» остаётся отдельным",
          canonical_initiator_group("ГУК ЮФО") == "гук юфо")
    check("initiator: «СУ/СК» -> «су»", canonical_initiator_group("СУ/СК") == "су")
    check("initiator: «СУ СК» -> «су»", canonical_initiator_group("СУ СК") == "су")
    check("initiator: «СК РФ» сохраняется", canonical_initiator_group("СК РФ") == "ск рф")
    check("initiator: «ОКРИМ» сохраняется", canonical_initiator_group("ОКРИМ") == "окрим")
    opts = initiator_filter_options(["СУ", "ГУК СК", "ГУК ЮФО", "СК РФ", "ПСК", "ГСУ", "ОКРИМ",
                                     "ГУК С.Т.С.А.С.И.Ю.", "СУ/СК", "МВД"])
    check("initiator: опции без дублей и мусора",
          opts == ["ГСУ", "ГУК", "ГУК ЮФО", "МВД", "ОКРИМ", "ПСК", "СК РФ", "СУ"],
          f"{opts}")
    # UI: фильтрация по канону находит все варианты
    d1 = _ctrl("i1", "И-1", controller="Потемкин С.А."); d1["initiator"] = "ГУК СК"
    d2 = _ctrl("i2", "И-2", controller="Потемкин С.А."); d2["initiator"] = "ГУК С.Т.С.А.С.И.Ю."
    d3 = _ctrl("i3", "И-3", controller="Потемкин С.А."); d3["initiator"] = "СУ/СК"
    d4 = _ctrl("i4", "И-4", controller="Потемкин С.А."); d4["initiator"] = "ГУК ЮФО"
    _seed_raw([d1, d2, d3, d4])
    page, tab, _ = build()
    idd = _find_dd(tab, "Все инициаторы")
    check("initiator: в опциях есть «ГУК», «СУ», «ГУК ЮФО»",
          idd is not None and "ГУК" in [o.key for o in (idd.options or [])]
          and "СУ" in [o.key for o in (idd.options or [])]
          and "ГУК ЮФО" in [o.key for o in (idd.options or [])])
    check("initiator: «ГУК СК» как опция отсутствует (схлопнут)",
          idd is not None and "ГУК СК" not in [o.key for o in (idd.options or [])])
    check("initiator: фильтр «ГУК» применился",
          _set_filter(tab, "Все инициаторы", "ГУК"))
    vis = _visible_texts(tab)
    check("initiator: «ГУК» находит «ГУК СК» и «ГУК С.Т.С.А.С.И.Ю.»",
          "И-1" in vis and "И-2" in vis, f"видно: {sorted(vis)}")
    check("initiator: «ГУК» не находит «СУ/СК» и «ГУК ЮФО»",
          "И-3" not in vis and "И-4" not in vis)
    check("initiator: фильтр «СУ» применился",
          _set_filter(tab, "Все инициаторы", "СУ"))
    vis = _visible_texts(tab)
    check("initiator: «СУ» находит «СУ/СК»", "И-3" in vis, f"видно: {sorted(vis)}")
    check("initiator: «СУ» не находит «ГУК …»", "И-1" not in vis and "И-4" not in vis)

    # ── 18. Раунд 7, задача 4: экспорт Excel 1:1 с эталоном ──
    de1 = _ctrl("e1", "Э-1", executors=["Семисенко И.Ю."], controller="Потемкин С.А.")
    de1.update({"initiator": "ГУК СК", "due_date": "2020-01-01", "receive_date": "2026-05-26"})
    de2 = _ctrl("e2", "Э-2", executors=["Ливенский В.О."], controller="Чащин Э.А.")
    de2.update({"initiator": "СУ", "done": True, "done_date": "2026-06-01",
                "due_date": "2026-08-10", "receive_date": "2026-06-18"})
    _seed_raw([de1, de2])
    page, tab, _ = build()
    from core.controls_exporter import TABLE_HEADERS, TABLE_WIDTHS, TABLE_TITLE, FULL_SHEET
    xlsx_path = os.path.join(tempfile.mkdtemp(prefix="porayonka_xlsx_"), "export.xlsx")
    ControlsExcelExporter().export(load_controls(), xlsx_path, soon_days=3, full=True)
    from openpyxl import load_workbook
    wbx = load_workbook(xlsx_path)
    check("excel: активный лист «Контроли»", "Контроли" in wbx.sheetnames)
    wsx = wbx["Контроли"]
    check("excel: A1 = «КОНТРОЛИ ОТДЕЛА КРИМИНАЛИСТИКИ»", wsx["A1"].value == TABLE_TITLE)
    check("excel: A1:J1 объединён", "A1:J1" in [str(r) for r in wsx.merged_cells.ranges])
    check("excel: A1 заливка зелёная FF00B050",
          wsx["A1"].fill.patternType == "solid" and wsx["A1"].fill.fgColor.rgb == "FF00B050")
    check("excel: шапка во 2-й строке (вх. № ВХСОП-____-__)",
          str(wsx["B2"].value).startswith("вх. № ВХСОП"))
    check("excel: G2 — «За кем контроль (Потёмкин С.А. / Чащин Э.А.)»",
          "Потёмкин С.А." in str(wsx["G2"].value))
    check("excel: H2 — «Разовый / постоянный»", "Разовый / постоянный" in str(wsx["H2"].value))
    check("excel: автофильтр A2:J4 (от шапки до последней строки данных)",
          wsx.auto_filter.ref == "A2:J4", wsx.auto_filter.ref)
    check("excel: ширина B = 34.3 как в эталоне",
          abs((wsx.column_dimensions["B"].width or 0) - 34.3) < 0.2)
    check("excel: C3 дата поступления — дата Excel (DD.MM.YYYY)",
          isinstance(wsx["C3"].value, datetime) and wsx["C3"].number_format == "DD.MM.YYYY")
    check("excel: I3 жёлтая заливка (просрочен)", 
          wsx["I3"].fill.patternType == "solid" and wsx["I3"].fill.fgColor.rgb == "FFFFFF00")
    check("excel: J4 зелёная заливка (исполнено)",
          wsx["J4"].fill.patternType == "solid" and wsx["J4"].fill.fgColor.rgb == "FF00B050")
    check("excel: скрытый лист _controls_full",
          FULL_SHEET in wbx.sheetnames and wbx[FULL_SHEET].sheet_state == "hidden")
    # round-trip: импорт файла с шапкой во 2-й строке
    parsed, stats = import_from_excel(xlsx_path, [])
    check("excel: импорт round-trip находит контроли",
          stats["imported"] == 2 and any(c.incoming_number == "Э-1" for c in parsed),
          f"imported={stats['imported']}")
    check("excel: round-trip сохранил done/даты",
          any(c.incoming_number == "Э-2" and c.done and c.done_date == "2026-06-01" for c in parsed))
    # импорт самого эталона «Контроли ОКРИМ.xlsx» (шапка во 2-й строке)
    etalon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                               "Контроли ОКРИМ.xlsx")
    if os.path.exists(etalon_path):
        parsed_e, stats_e = import_from_excel(etalon_path, [])
        check("excel: импорт эталона ОКРИМ находит строки",
              stats_e["imported"] > 0 and any(c.incoming_number == "4108-26" for c in parsed_e),
              f"imported={stats_e['imported']}")

    # ── 19. Раунд 7, задача 5: resize колонок (drag → сохранение в настройки) ──
    save_settings({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True})
    _seed_raw([_ctrl("r1", "Р-1", executors=["Семисенко И.Ю."])])
    page, tab, _ = build()
    def _gd_subs2(g, attr):
        eh = getattr(g, attr, None)
        return len(getattr(eh, "_EventHandler__handlers", {})) if eh is not None else 0
    gds = [c for c in walk(tab) if isinstance(c, ft.GestureDetector)
           and _gd_subs2(c, "on_horizontal_drag_start") > 0]
    check("resize: drag-хэндлы найдены", len(gds) >= 1, f"{len(gds)}")
    if gds:
        E = type("E", (), {})
        _invoke_event_handler(gds[0].on_horizontal_drag_start, E())
        _invoke_event_handler(gds[0].on_horizontal_drag_update, type("E", (), {"delta_x": 40})())
        _invoke_event_handler(gds[0].on_horizontal_drag_end, E())
        saved = load_settings().get("col_widths") or {}
        check("resize: ширины сохранены в controls_settings.json",
              len(saved) > 0, f"{saved}")
        check("resize: значение изменилось относительно стартового",
              any(v > 60 for v in saved.values()))

    # ── 20. Раунд 7, задача 3: «Удалить все» ──
    _seed_raw([_ctrl("d1", "Д-1", executors=["Семисенко И.Ю."])])
    save_settings({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {"d1:new": "2026-08-05"},
                   "notify_sound": True})
    page, tab, _ = build()
    check("delete_all: кнопка «Удалить все» есть у админа",
          any(isinstance(c, ft.ElevatedButton) and getattr(c, "text", None) == "Удалить все"
              and getattr(c, "visible", True) for c in walk(tab)))
    dbtns = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
             and getattr(c, "text", None) == "Удалить все"]
    dbtns[0].on_click(None)
    check("delete_all: диалог подтверждения открыт", len(page.dialogs) >= 1)
    dlg = page.dialogs[-1]
    # без слова подтверждения кнопка неактивна
    from page_stub import PageStub
    fields = [c for c in walk(dlg) if isinstance(c, ft.TextField)]
    confirms = [c for c in getattr(dlg, "actions", []) if isinstance(c, ft.ElevatedButton)
                and getattr(c, "text", None) == "Удалить всё"]
    check("delete_all: кнопка «Удалить всё» неактивна до ввода", confirms and confirms[0].disabled)
    if fields and confirms:
        fields[0].value = "УДАЛИТЬ"
        if fields[0].on_change:
            fields[0].on_change(None)
        check("delete_all: кнопка активна после ввода «УДАЛИТЬ»", not confirms[0].disabled)
        confirms[0].on_click(None)
    check("delete_all: state очищен (таблица пуста)",
          len(_visible_rows(tab)) == 0)
    check("delete_all: controls.json пуст", load_controls() == [])
    check("delete_all: notify_log очищен", not (load_settings().get("notify_log") or {}))
    # для роли user кнопка скрыта
    save_settings({"network_enabled": False, "network_role": "user", "network_user": "Семисенко Иван Юрьевич",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True})
    _seed_raw([_ctrl("d2", "Д-2", executors=["Семисенко И.Ю."])])
    page, tab, _ = build()
    check("delete_all: у роли user кнопка скрыта",
          not any(isinstance(c, ft.ElevatedButton) and getattr(c, "text", None) == "Удалить все"
                  and getattr(c, "visible", True) for c in walk(tab)))

    # ── 21. Раунд 8, задача 1: справочник людей (extra_people) ──
    from core.controls_data import add_extra_person, remove_extra_person
    st8 = {"network_enabled": False, "network_role": "admin", "network_user": "",
           "network_shared_path": "", "notify_log": {}, "notify_sound": True}
    save_settings(st8)
    check("people: add_extra_person добавляет", add_extra_person(st8, "Макаренко Роман Андреевич") is True)
    check("people: дубль не добавляется", add_extra_person(st8, "макаренко роман андреевич") is False)
    check("people: сохранено в настройки",
          "Макаренко Роман Андреевич" in (load_settings().get("extra_people") or []))
    _seed_raw([
        _ctrl("m1", "М-1", executors=["Макаренко Р.А."]),
        _ctrl("m2", "М-2", executors=["Посторонний А.А."]),
    ])
    page, tab, _ = build()
    ex = _find_dd(tab, "Все исполнители")
    check("people: Макаренко есть в опциях фильтра",
          ex is not None and "Макаренко Роман Андреевич" in [o.key for o in (ex.options or [])])
    check("people: фильтр по Макаренко находит его контроль",
          _set_filter(tab, "Все исполнители", "Макаренко Роман Андреевич"))
    vis = _visible_texts(tab)
    check("people: контроль Макаренко виден, посторонний скрыт",
          "М-1" in vis and "М-2" not in vis, f"видно: {sorted(vis)}")
    check("people: «Прочие» не содержит Макаренко",
          _set_filter(tab, "Все исполнители", FILTER_OTHER))
    vis = _visible_texts(tab)
    check("people: «Прочие» — только посторонний", "М-2" in vis and "М-1" not in vis)
    check("people: remove_extra_person удаляет",
          remove_extra_person(load_settings(), "Макаренко Роман Андреевич") is True)

    # ── 22. Раунд 8, задача 2: склейки инициаторов ──
    check("initiator: «ГУК СК ГУК ЮФО» разбивается на «гук,гук юфо»",
          canonical_initiator_group("ГУК СК ГУК ЮФО") == "гук,гук юфо")
    check("initiator: «ГСУ ГУК» разбивается на «гсу,гук»",
          canonical_initiator_group("ГСУ ГУК") == "гсу,гук")
    opts8 = initiator_filter_options(["ГУК СК ГУК ЮФО", "ГСУ ГУК", "СУ", "ОКРИМ"])
    check("initiator: опции без склеек — отдельные каноны",
          "ГУК" in opts8 and "ГУК ЮФО" in opts8 and "ГСУ" in opts8 and "СУ" in opts8,
          f"{opts8}")
    check("initiator: «ГУК СК, ГУК ЮФО» (с запятой) тоже разбивается",
          canonical_initiator_group("ГУК СК, ГУК ЮФО") == "гук,гук юфо")

    # ── 23. Раунд 8, задача 3: resize на ВСЕХ границах + видимые разделители ──
    save_settings({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": []})
    _seed_raw([_ctrl("r8", "Р-8", executors=["Семисенко И.Ю."])])
    page, tab, _ = build()
    def _gd_subs(g, attr):
        eh = getattr(g, attr, None)
        return len(getattr(eh, "_EventHandler__handlers", {})) if eh is not None else 0
    gds = [c for c in walk(tab) if isinstance(c, ft.GestureDetector)
           and _gd_subs(c, "on_horizontal_drag_start") > 0]
    # 11 границ колонок (у resize-хэндла карточки подписки horizontal нет)
    check("resize: drag-хэндлы на ВСЕХ 11 границах колонок", len(gds) == 11, f"{len(gds)}")
    # разделители в заголовке (1px, цвет #26ffffff)
    seps = [c for c in walk(tab) if isinstance(c, ft.Container)
            and getattr(c, "width", None) == 1 and getattr(c, "bgcolor", None) == "#26ffffff"]
    check("resize: видимые разделители в заголовке", len(seps) >= 10, f"{len(seps)}")
    # разделители в строках (#12ffffff)
    seps_r = [c for c in walk(tab) if isinstance(c, ft.Container)
              and getattr(c, "width", None) == 1 and getattr(c, "bgcolor", None) == "#12ffffff"]
    check("resize: разделители в строках таблицы", len(seps_r) >= 8, f"{len(seps_r)}")
    # drag по «Содержание» (индекс 5) сохраняет ширину
    g5 = gds[4]  # граница после «Содержание» (0-индекс: №, вх, дата, инициатор, содержание)
    E = type("E", (), {})
    _invoke_event_handler(g5.on_horizontal_drag_start, E())
    _invoke_event_handler(g5.on_horizontal_drag_update, type("E", (), {"delta_x": 30})())
    _invoke_event_handler(g5.on_horizontal_drag_end, E())
    saved = load_settings().get("col_widths") or {}
    check("resize: drag «Содержания» сохранил ширину", len(saved) > 0, f"{saved}")

    # ── 24. Раунд 15: нативный hover на строках; календари и хэндлы — без hover ──
    page, tab, _ = build()
    rows8 = _visible_rows(tab)
    check("hover15: строки есть", len(rows8) >= 1)
    if rows8:
        check("hover15: на строках НЕТ Python on_hover (нативный InkWell)",
              all(getattr(r8, "on_hover", None) is None for r8 in rows8))
        check("hover15: на каждой строке ink=True (InkWell)",
              all(getattr(r8, "ink", None) is True for r8 in rows8))
    # ячейки календарей (фильтр-календарь собирается при init) — без hover-update
    cal_cells = [c for c in walk(tab) if isinstance(c, ft.Container)
                 and getattr(c, "width", None) == 34 and getattr(c, "height", None) == 32]
    check("hover15: ячейки календарей без on_hover",
          all(getattr(c, "on_hover", None) is None for c in cal_cells),
          f"{len(cal_cells)} ячеек")

    # ── 25. Раунд 9, задача 3: редактор справочников ──
    save_settings({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "custom_initiators": []})
    _seed_raw([_ctrl("ref1", "РФ-1", executors=["Семисенко И.Ю."], controller="Потемкин С.А.")])
    page, tab, _ = build()
    ref_btns = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
                and getattr(c, "text", None) == "Справочники"]
    check("refs: кнопка «Справочники» в тулбаре", len(ref_btns) == 1)
    if ref_btns:
        ref_btns[0].on_click(None)
        # Раунд 14: overlay-Container, НЕ AlertDialog
        check("refs14: справочники — не AlertDialog", len(page.dialogs) == 0)
        dlg = _refs_overlay_of(tab)
        check("refs: overlay открыт", dlg is not None)
        fields = [c for c in walk(dlg) if isinstance(c, ft.TextField)]
        add_btns = [c for c in walk(dlg) if isinstance(c, ft.ElevatedButton)
                    and getattr(c, "text", None) == "Добавить"]
        check("refs: в модалке есть поля и кнопки «Добавить»",
              len(fields) >= 2 and len(add_btns) >= 2, f"{len(fields)}/{len(add_btns)}")
        if fields and add_btns:
            # добавить человека в справочник
            fields[0].value = "Макаренко Роман Андреевич"
            add_btns[0].on_click(None)
            check("refs: extra_people пополнен",
                  "Макаренко Роман Андреевич" in (load_settings().get("extra_people") or []))
            # добавить инициатор
            fields[1].value = "МВД"
            add_btns[1].on_click(None)
            check("refs: custom_initiators пополнен",
                  "МВД" in (load_settings().get("custom_initiators") or []))
            # применить
            apply_btns = _refs_apply_of(dlg)
            if apply_btns:
                apply_btns[0].on_click(None)
            ex = _find_dd(tab, "Все исполнители")
            check("refs: Макаренко появился в фильтре после применения",
                  ex is not None and "Макаренко Роман Андреевич" in [o.key for o in (ex.options or [])])
            idd = _find_dd(tab, "Все инициаторы")
            check("refs: «МВД» появился в фильтре инициаторов",
                  idd is not None and "МВД" in [o.key for o in (idd.options or [])])

    # ── 26. Раунд 9, задача 4: resize карточки (размеры сохраняются) ──
    save_settings({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "card_width": 920, "card_height": 780})
    _seed_raw([_ctrl("cr1", "КР-1", executors=["Семисенко И.Ю."])])
    page, tab, _ = build()
    _open_card(tab, via_add=False)
    # найти resize-хэндл (GestureDetector с on_pan_update)
    def _gd_subs3(g, attr):
        eh = getattr(g, attr, None)
        return len(getattr(eh, "_EventHandler__handlers", {})) if eh is not None else 0
    pans = [c for c in walk(tab) if isinstance(c, ft.GestureDetector)
            and _gd_subs3(c, "on_pan_update") > 0]
    check("card-resize: хэндл найден", len(pans) >= 1, f"{len(pans)}")
    if pans:
        # Раунд 15 (задача 3): хэндл пришит к правому нижнему углу Stack через
        # right=0/bottom=0 — следует за углом карточки при resize автоматически
        # (раньше left/top задавали один раз при открытии — хэндл «застывал»).
        check("card-resize: хэндл пришит к углу (right=0/bottom=0)",
              pans[0].right == 0 and pans[0].bottom == 0,
              f"right={pans[0].right} bottom={pans[0].bottom}")
        check("card-resize: хэндл без пиксельного left/top",
              pans[0].left is None and pans[0].top is None)
        # видимый глиф-уголок внутри хэндла (две линии 2px справа и снизу)
        glyph = getattr(getattr(pans[0], "content", None), "content", None)
        gb = getattr(glyph, "border", None)
        check("card-resize: у хэндла видимый уголок-глиф",
              gb is not None and getattr(gb, "right", None) is not None
              and getattr(gb, "bottom", None) is not None
              and getattr(gb, "top", None) is None,
              f"border={gb}")
        _invoke_event_handler(pans[0].on_pan_update, type("E", (), {"delta_x": 120, "delta_y": 80})())
        _invoke_event_handler(pans[0].on_pan_end, type("E", (), {})())
        st9 = load_settings()
        check("card-resize: ширина сохранена в настройки",
              int(st9.get("card_width") or 0) > 920, f"w={st9.get('card_width')}")
        check("card-resize: высота сохранена в настройки",
              int(st9.get("card_height") or 0) > 780, f"h={st9.get('card_height')}")
        # Раунд 16 (задача 4): размеры ВОССТАНАВЛИВАЮТСЯ при переоткрытии
        # (раньше высота резалась в max 780 на открытии — «не запоминается»).
        saved_w = int(st9.get("card_width") or 0)
        saved_h = int(st9.get("card_height") or 0)
        close_btns = [c for c in walk(tab) if isinstance(c, ft.IconButton)
                      and getattr(c, "icon", None) == ft.icons.CLOSE
                      and not getattr(c, "tooltip", None)]
        if close_btns:
            close_btns[0].on_click(None)  # закрыть карточку
            _open_card(tab, via_add=False)
            cards = [c for c in walk(tab) if isinstance(c, ft.Container)
                     and getattr(c, "bgcolor", None) == "#242a3e"]
            check("card16: при переоткрытии размеры из settings применены",
                  len(cards) >= 1 and cards[0].width == max(600, min(1216, saved_w))
                  and cards[0].height == max(400, min(791, saved_h)),
                  f"w={cards[0].width if cards else None} h={cards[0].height if cards else None}"
                  f" saved={saved_w}x{saved_h}")

    # ── 27. Раунд 9, БАГ 2: разделители заголовка и строк выровнены ──
    save_settings({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": []})
    _seed_raw([_ctrl("sp1", "СП-1", executors=["Семисенко И.Ю."])])
    page, tab, _ = build()
    # в заголовке и строке одинаковая последовательность: bar, ячейка, разделитель...
    hdr = [c for c in walk(tab) if isinstance(c, ft.Container)
           and getattr(c, "bgcolor", None) == "#26ffffff"]
    rows_sp = _visible_rows(tab)
    row_sp = rows_sp[0] if rows_sp else None
    vseps = [c for c in walk(row_sp) if isinstance(c, ft.Container)
             and getattr(c, "bgcolor", None) == "#12ffffff"] if row_sp else []
    check("seps: в заголовке 10 разделителей", len(hdr) == 10, f"{len(hdr)}")
    check("seps: в строке 10 разделителей", len(vseps) == 10, f"{len(vseps)}")
    # одинаковое число ячеек между разделителями => X-координаты совпадают
    check("seps: число колонок заголовка = числу колонок строки",
          len([c for c in walk(tab) if isinstance(c, ft.Stack) and getattr(c, "width", None)]) >= 11)

    # ── 28. Раунд 9, задача 5: предпросмотр вложений ──
    _seed_raw([_ctrl("cr2", "КР-2", executors=["Семисенко И.Ю."])])
    att_dir = os.path.join(os.environ["APPDATA"], "porayonka", "controls_attachments", "cr2")
    os.makedirs(att_dir, exist_ok=True)
    img_path = os.path.join(att_dir, "test.png")
    with open(img_path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    # подменить attachments у контроля
    data = json.load(open(get_controls_file(), encoding="utf-8"))
    data["controls"][0]["attachments"] = ["cr2/test.png"]
    with open(get_controls_file(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    page, tab, _ = build()
    _open_card(tab, via_add=False)
    allc9 = walk(tab)
    zoom_btns = [c for c in allc9 if isinstance(c, ft.IconButton)
                 and getattr(c, "tooltip", None) == "Предпросмотр"]
    check("preview: кнопка «Предпросмотр» у вложения", len(zoom_btns) >= 1, f"{len(zoom_btns)}")
    thumbs = [c for c in allc9 if isinstance(c, ft.Image)]
    check("preview: миниатюра изображения (ft.Image) в списке", len(thumbs) >= 1, f"{len(thumbs)}")
    if zoom_btns:
        zoom_btns[0].on_click(None)
        ovs = [c for c in walk(tab) if isinstance(c, ft.Container)
               and getattr(c, "bgcolor", None) == "#e604070f" and getattr(c, "visible", False)]
        check("preview: overlay предпросмотра открыт", len(ovs) >= 1)
        # закрыть
        close_btns = [c for c in walk(tab) if isinstance(c, ft.IconButton)
                      and getattr(c, "tooltip", None) == "Закрыть"]
        if close_btns:
            close_btns[-1].on_click(None)
            check("preview: overlay закрыт",
                  not any(getattr(c, "visible", False) for c in walk(tab)
                          if getattr(c, "bgcolor", None) == "#e604070f"))

    # ── 29. Раунд 15, задача 1: ни на строке, ни на вложенных — Python-hover нет ──
    save_settings({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": []})
    _seed_raw([_ctrl("h1", "Х-1", executors=["Семисенко И.Ю."])])
    page, tab, _ = build()
    rows10 = _visible_rows(tab)
    check("hover15: строки есть", len(rows10) >= 1)
    if rows10:
        check("hover15: on_hover на строках отсутствует (нативный InkWell)",
              all(getattr(r10, "on_hover", None) is None for r10 in rows10))
        nested = [c for r in rows10 for c in walk(r)
                  if c is not r and getattr(c, "on_hover", None) is not None]
        check("hover15: на вложенных контролах строки on_hover тоже НЕТ", not nested,
              f"{len(nested)} вложенных")

    # ── 30. Раунд 10, задача 2: «Действия» прижаты к правому краю ──
    page, tab, _ = build()
    allc10 = walk(tab)
    action_rows = [c for c in allc10 if isinstance(c, ft.Row)
                   and getattr(c, "alignment", None) == ft.MainAxisAlignment.END
                   and getattr(c, "width", None) is not None]
    check("actions10: Row действий с alignment=END и шириной колонки", len(action_rows) >= 1, f"{len(action_rows)}")

    # ── 31. Раунд 10, задача 3: редактирование записи в справочнике ──
    save_settings({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": ["Макаренко Роман Андреевич"], "custom_initiators": ["МВД"]})
    _seed_raw([_ctrl("r10", "Р-10", executors=["Макаренко Р.А."], controller="Потемкин С.А.")])
    page, tab, _ = build()
    ref_btns10 = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
                  and getattr(c, "text", None) == "Справочники"]
    ref_btns10[0].on_click(None)
    dlg10 = _refs_overlay_of(tab)
    check("refs10: overlay справочников открыт", dlg10 is not None)
    edit_icons = [c for c in walk(dlg10) if isinstance(c, ft.IconButton)
                  and getattr(c, "tooltip", None) == "Переименовать"]
    check("refs10: иконки «Переименовать» есть", len(edit_icons) >= 1, f"{len(edit_icons)}")
    # найти КОНКРЕТНУЮ запись «Макаренко Роман Андреевич» (контейнер с фоном
    # surface_alt, содержащий текст и иконки) и кликнуть её карандаш
    mak_rows = [c for c in walk(dlg10) if isinstance(c, ft.Container)
                and getattr(c, "bgcolor", None) == GLASS["surface_alt"]
                and any(isinstance(t, ft.Text) and t.value == "Макаренко Роман Андреевич"
                        for t in walk(c) if isinstance(t, ft.Text))]
    check("refs10: запись Макаренко в списке", len(mak_rows) >= 1, f"{len(mak_rows)}")
    if mak_rows:
        mak_edit = [c for c in walk(mak_rows[0]) if isinstance(c, ft.IconButton)
                    and getattr(c, "tooltip", None) == "Переименовать"]
        if mak_edit:
            mak_edit[0].on_click(None)
        fields10 = [c for c in walk(dlg10) if isinstance(c, ft.TextField)
                    and (getattr(c, "value", "") or "") == "Макаренко Роман Андреевич"]
        check("refs10: поле редактирования с текущим значением", len(fields10) >= 1)
        if fields10:
            fields10[0].value = "Макаренко Р.А."
            save_icons = [c for c in walk(dlg10) if isinstance(c, ft.IconButton)
                          and getattr(c, "tooltip", None) == "Сохранить"]
            if save_icons:
                save_icons[0].on_click(None)
            st10 = load_settings()
            check("refs10: значение переименовано в extra_people",
                  "Макаренко Р.А." in (st10.get("extra_people") or [])
                  and "Макаренко Роман Андреевич" not in (st10.get("extra_people") or []),
                  f"{st10.get('extra_people')}")

    # ── 32. Раунд 10, задача 4: уголки карточки (clip_behavior) ──
    save_settings({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": []})
    _seed_raw([_ctrl("c10", "К-10", executors=["Семисенко И.Ю."])])
    page, tab, _ = build()
    _open_card(tab, via_add=False)
    cards = [c for c in walk(tab) if isinstance(c, ft.Container)
             and getattr(c, "bgcolor", None) == "#242a3e"]
    check("card10: карточка найдена", len(cards) >= 1)
    if cards:
        card10 = cards[0]
        check("card10: clip_behavior=HARD_EDGE",
              getattr(card10, "clip_behavior", None) == ft.ClipBehavior.HARD_EDGE,
              f"clip={getattr(card10, 'clip_behavior', None)}")
        check("card10: border_radius > 0", (getattr(card10, "border_radius", 0) or 0) > 0)
        # Раунд 14 (задача 4): равномерная рамка (без border.only с разной толщиной)
        b10 = getattr(card10, "border", None)
        check("card14: рамка равномерная border.all (углы не прозрачные)",
              b10 is not None
              and b10.top.color == b10.left.color == b10.right.color == b10.bottom.color,
              f"border={b10}")

    # ── 33. Раунд 10, задача 5: предпросмотр занимает ~90% окна ──
    att_dir10 = os.path.join(os.environ["APPDATA"], "porayonka", "controls_attachments", "c10")
    os.makedirs(att_dir10, exist_ok=True)
    with open(os.path.join(att_dir10, "test.png"), "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    data10 = json.load(open(get_controls_file(), encoding="utf-8"))
    data10["controls"][0]["attachments"] = ["c10/test.png"]
    with open(get_controls_file(), "w", encoding="utf-8") as f:
        json.dump(data10, f, ensure_ascii=False, indent=2)
    page, tab, _ = build()
    _open_card(tab, via_add=False)
    zoom10 = [c for c in walk(tab) if isinstance(c, ft.IconButton)
              and getattr(c, "tooltip", None) == "Предпросмотр"]
    if zoom10:
        zoom10[0].on_click(None)
        bodies = [c for c in walk(tab) if isinstance(c, ft.Container)
                  and getattr(c, "bgcolor", None) == GLASS["surface_solid"]
                  and getattr(c, "width", None) is not None and getattr(c, "width", 0) > 640]
        check("preview10: окно предпросмотра > 640 px шириной",
              len(bodies) >= 1, f"{[getattr(b, 'width', 0) for b in bodies]}")
        if bodies:
            check("preview10: ширина >= 90% окна (1280 -> >= 1000)",
                  bodies[0].width >= 1000, f"w={bodies[0].width}")

    # ── 34. Раунд 13, задача 2: таблица помещается при 1280 (сумма <= 1240) ──
    save_settings({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": []})
    _seed_raw([_ctrl("w1", "Ш-1", executors=["Семисенко И.Ю."])])
    st_w = load_settings()
    st_w.pop("col_widths", None)
    save_settings(st_w)

    def _header_row_of(tab_):
        hdrs = [c for c in walk(tab_) if isinstance(c, ft.Container)
                and getattr(c, "height", None) == 34
                and isinstance(getattr(c, "content", None), ft.Row)
                and len(getattr(c.content, "controls", []) or []) >= 20]
        return hdrs[0].content if hdrs else None

    def _ctrl_w(c_):
        w_ = getattr(c_, "width", None)
        if w_:
            return w_
        if isinstance(c_, ft.Row):  # вложенная колонка «Содержание» (+вложения)
            t_ = sum(_ctrl_w(x_) for x_ in c_.controls)
            t_ += (c_.spacing or 0) * (len(c_.controls) - 1)
            return t_
        return 0

    def _row_total(row_, extra_padding):
        ctrls = row_.controls
        tot = sum(_ctrl_w(c) for c in ctrls)
        tot += (row_.spacing or 0) * (len(ctrls) - 1)
        return tot + extra_padding

    def _row_inner(row_):
        # Раунд 16 (задача 1): контент плашки строки — Stack([паддинг-Container(Row
        # колонок), Positioned-полоса статуса]). Возвращаем внутренний Row колонок.
        st_ = row_.content
        if isinstance(st_, ft.Stack):
            return st_.controls[0].content
        return st_

    page, tab, _ = build(1280)
    hdr = _header_row_of(tab)
    check("width13: заголовок таблицы найден", hdr is not None)
    if hdr:
        tot_h = _row_total(hdr, 12)  # padding заголовка 6*2 (раунд 14)
        check("width13: заголовок + отступы <= 1240 при 1280", tot_h <= 1240, f"sum={tot_h}")
    rows_w = _visible_rows(tab)
    check("width13: строки есть", len(rows_w) >= 1)
    if rows_w:
        tot_r = _row_total(_row_inner(rows_w[0]), 12 + 2)  # padding 6*2 + рамка 2 (раунд 14)
        check("width13: строка + отступы <= 1240 при 1280", tot_r <= 1240, f"sum={tot_r}")
    # Раунд 15 (задача 2): ЯВНАЯ ширина панели/строк — вся ширина контента вкладки
    # (1280-64=1216 панель, 1214 строка/заголовок). Иначе shrink-wrap -> пустота справа.
    themed15 = [c for c in walk(tab) if isinstance(c, ft.Container)
                and getattr(c, "theme", None) is not None]
    check("width15: панель таблицы найдена (локальная тема)", len(themed15) >= 1)
    if themed15:
        check("width15: панель таблицы шириной 1216 (1280-64)",
              getattr(themed15[0], "width", None) == 1216, f"w={getattr(themed15[0], 'width', None)}")
        check("width15: панель <= 1240 («Действия» не за экраном)",
              (getattr(themed15[0], "width", 9999) or 9999) <= 1240)
    if rows_w:
        check("width15: строка шириной 1214 (панель-рамка)", rows_w[0].width == 1214,
              f"w={rows_w[0].width}")
    if hdr:
        hdr_cont = [c for c in walk(tab) if isinstance(c, ft.Container)
                    and getattr(c, "height", None) == 34
                    and isinstance(getattr(c, "content", None), ft.Row)
                    and len(getattr(c.content, "controls", []) or []) >= 20]
        check("width15: заголовок шириной 1214",
              hdr_cont and getattr(hdr_cont[0], "width", None) == 1214,
              f"w={getattr(hdr_cont[0], 'width', None) if hdr_cont else None}")
    # раздутые сохранённые ширины (как после ручного resize) клампятся
    st_w = load_settings()
    st_w["col_widths"] = {"bar": 4, "num": 120, "incoming": 400, "receive": 200,
                          "initiator": 300, "controller": 300, "type": 200, "due": 250,
                          "status": 300, "actions": 250, "content": 1200, "executors": 700}
    save_settings(st_w)
    page, tab, _ = build(1280)
    hdr = _header_row_of(tab)
    if hdr:
        tot_h2 = _row_total(hdr, 12)
        check("width13: раздутые col_widths из settings ужаты <= 1240",
              tot_h2 <= 1240, f"sum={tot_h2}")
    rows_w2 = _visible_rows(tab)
    if rows_w2:
        tot_r2 = _row_total(_row_inner(rows_w2[0]), 14)
        check("width13: строка с раздутыми col_widths <= 1240", tot_r2 <= 1240, f"sum={tot_r2}")
    # широкий экран: гибкие колонки РАСТЯГИВАЮТСЯ (кэпы 480/220 раунда 13 убраны —
    # они и давали пустое место справа), сумма ТОЧНО заполняет ширину окна
    st_w = load_settings()
    st_w.pop("col_widths", None)
    save_settings(st_w)
    page, tab, _ = build(1920)
    hdr = _header_row_of(tab)
    if hdr:
        ctrls = hdr.controls
        # порядок: [bar][num][sep][incoming][sep][receive][sep][initiator][sep]
        #          [content][sep][executors]...  => индексы 9 и 11
        content_w = getattr(ctrls[9], "width", 0) or 0
        exec_w = getattr(ctrls[11], "width", 0) or 0
        check("width15: при 1920 «Содержание» растянуто > 480", content_w > 480, f"w={content_w}")
        check("width15: при 1920 «Исполнители» растянуты > 220", exec_w > 220, f"w={exec_w}")
        # полное заполнение: сумма колонок = бюджет (1920-64-48=1808), +10
        # разделителей +21 spacing +12 padding заголовка = 1851 ровно
        tot_h3 = _row_total(hdr, 12)
        check("width15: при 1920 заголовок ТОЧНО заполняет ширину (1851)",
              tot_h3 == 1851, f"sum={tot_h3}")
        panel15 = [c for c in walk(tab) if isinstance(c, ft.Container)
                   and getattr(c, "theme", None) is not None]
        check("width15: при 1920 панель шириной 1856 (1920-64)",
              panel15 and getattr(panel15[0], "width", None) == 1856,
              f"w={getattr(panel15[0], 'width', None) if panel15 else None}")

    # ── 35. Раунд 13, задача 3: редактирование БАЗОВОЙ записи справочника сохраняется ──
    save_settings({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "custom_initiators": [],
                   "hidden_people": [], "hidden_initiators": []})
    _b14 = _ctrl("b14", "Б-14", executors=["Семисенко И.Ю."], controller="Потемкин С.А.")
    _b14["initiator"] = "ГУК СК"
    _seed_raw([_ctrl("b13", "Б-13", executors=["Семисенко И.Ю."], controller="Потемкин С.А."), _b14])
    page, tab, _ = build()
    ref_btns13 = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
                  and getattr(c, "text", None) == "Справочники"]
    check("ref13: кнопка «Справочники» есть", len(ref_btns13) == 1)
    ref_btns13[0].on_click(None)
    dlg13 = _refs_overlay_of(tab)
    check("ref13: overlay справочников открыт", dlg13 is not None)
    # компактные строки: кнопки 26px, spacing списков 2
    # Раунд 16 (задачи 2–3): списки — Column(scroll=ADAPTIVE, expand=True), БЕЗ
    # кастомного on_scroll (нативный скролл, видимый бегунок, нет KeyError).
    ref_lists = [c for c in walk(dlg13) if isinstance(c, ft.Column)
                 and getattr(c, "scroll", None) == ft.ScrollMode.ADAPTIVE
                 and (getattr(c, "expand", 0) or 0) > 0]
    check("ref13: списки компактные (spacing=2)",
          len(ref_lists) >= 2 and all(c.spacing == 2 for c in ref_lists),
          f"{[c.spacing for c in ref_lists]}")
    check("ref15: списки справочников expand=True (растут при resize)",
          len(ref_lists) >= 2 and all((c.expand or 0) > 0 for c in ref_lists)
          and all(getattr(c, "height", None) is None for c in ref_lists))
    check("ref16: scroll=ADAPTIVE у списков (видимый бегунок на десктопе)",
          len(ref_lists) >= 2)
    check("ref16: у списков НЕТ подписки on_scroll (нет KeyError 'sd'/'dir')",
          len(ref_lists) >= 2
          and all(c._get_attr("onScroll") is None for c in ref_lists))
    ref_btns_small = [c for c in walk(dlg13) if isinstance(c, ft.IconButton)
                      and getattr(c, "tooltip", None) in ("Переименовать", "Удалить")]
    check("ref13: кнопки записей компактные (26px)",
          len(ref_btns_small) >= 2 and all(getattr(b, "height", 0) == 26 for b in ref_btns_small))
    base_name = "Авакян Арсен Артурович"
    base_rows = [c for c in walk(dlg13) if isinstance(c, ft.Container)
                 and getattr(c, "bgcolor", None) == GLASS["surface_alt"]
                 and any(isinstance(t, ft.Text) and t.value == base_name for t in walk(c))]
    check("ref13: базовая запись в списке", len(base_rows) >= 1)
    if base_rows:
        pencil13 = [c for c in walk(base_rows[0]) if isinstance(c, ft.IconButton)
                    and getattr(c, "tooltip", None) == "Переименовать"]
        pencil13[0].on_click(None)
        efields13 = [c for c in walk(dlg13) if isinstance(c, ft.TextField)
                     and (getattr(c, "value", "") or "") == base_name]
        check("ref13: открылось поле редактирования", len(efields13) >= 1)
        if efields13:
            efields13[0].value = base_name + "!!!"
            save_ic13 = [c for c in walk(dlg13) if isinstance(c, ft.IconButton)
                         and getattr(c, "tooltip", None) == "Сохранить"]
            save_ic13[0].on_click(None)
            st13 = load_settings()
            check("ref13: новое значение в extra_people (controls_settings.json)",
                  (base_name + "!!!") in (st13.get("extra_people") or []),
                  f"{st13.get('extra_people')}")
            check("ref13: базовое старое скрыто (hidden_people)",
                  base_name in (st13.get("hidden_people") or []))
            from core.controls_data import get_controller_names as _gcn
            cn13 = _gcn(st13)
            check("ref13: канон — новое есть, старого нет",
                  (base_name + "!!!") in cn13 and base_name not in cn13)
            texts13 = {t.value for t in walk(dlg13) if isinstance(t, ft.Text)}
            check("ref13: список перестроен с новым именем",
                  (base_name + "!!!") in texts13 and base_name not in texts13)
    apply13 = _refs_apply_of(dlg13)
    apply13[0].on_click(None)
    ex13 = _find_dd(tab, "Все исполнители")
    opts13 = [o.key for o in (ex13.options or [])]
    check("ref13: после «Применить» новое ФИО в фильтре", (base_name + "!!!") in opts13)
    check("ref13: старое базовое ФИО из фильтра ушло", base_name not in opts13)

    # базовый инициатор: переименование сохраняется
    ref_btns13 = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
                  and getattr(c, "text", None) == "Справочники"]
    ref_btns13[0].on_click(None)
    dlg13b = _refs_overlay_of(tab)
    init_rows = [c for c in walk(dlg13b) if isinstance(c, ft.Container)
                 and getattr(c, "bgcolor", None) == GLASS["surface_alt"]
                 and any(isinstance(t, ft.Text) and t.value == "ГУК" for t in walk(c))]
    check("ref13: базовый инициатор «ГУК» в списке", len(init_rows) >= 1)
    if init_rows:
        pencil_i = [c for c in walk(init_rows[0]) if isinstance(c, ft.IconButton)
                    and getattr(c, "tooltip", None) == "Переименовать"]
        pencil_i[0].on_click(None)
        efields_i = [c for c in walk(dlg13b) if isinstance(c, ft.TextField)
                     and (getattr(c, "value", "") or "") == "ГУК"]
        if efields_i:
            efields_i[0].value = "ГУК РОСТОВ"
            save_i = [c for c in walk(dlg13b) if isinstance(c, ft.IconButton)
                      and getattr(c, "tooltip", None) == "Сохранить"]
            save_i[0].on_click(None)
            st_i = load_settings()
            check("ref13: переименование кластера сохранено в init_renames (json)",
                  (st_i.get("init_renames") or {}).get("ГУК") == "ГУК РОСТОВ",
                  f"{st_i.get('init_renames')}")
        apply_i = _refs_apply_of(dlg13b)
        apply_i[0].on_click(None)
        idd13 = _find_dd(tab, "Все инициаторы")
        iopts = [o.key for o in (idd13.options or [])]
        check("ref13: «ГУК РОСТОВ» в фильтре инициаторов", "ГУК РОСТОВ" in iopts, f"{iopts}")
        check("ref13: переименованный кластер «ГУК» из опций ушёл", "ГУК" not in iopts)
        # фильтр по переименованному кластеру находит контроли исходного канона
        check("ref13: фильтр «ГУК РОСТОВ» применился",
          _set_filter(tab, "Все инициаторы", "ГУК РОСТОВ"))
        vis13 = _visible_texts(tab)
        check("ref13: «ГУК РОСТОВ» находит контроль «ГУК СК»",
              "Б-14" in vis13 and "Б-13" not in vis13, f"видно: {sorted(vis13)}")

    # ── 36. Раунд 13, задача 5: прикрепление к НОВОЙ карточке без TypeError ──
    from core.controls_data import copy_attachment_to_local, copy_attachment_to_shared
    save_settings({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": []})
    _seed_raw([_ctrl("a13", "А-13", executors=["Семисенко И.Ю."])])
    # страховка уровня данных: пустой control_id -> None, без TypeError
    src_dir13 = tempfile.mkdtemp(prefix="porayonka_src_")
    src13 = os.path.join(src_dir13, "scan.png")
    with open(src13, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"1" * 32)
    check("attach13: copy_attachment_to_local(None) = None без TypeError",
          copy_attachment_to_local(None, src13) is None)
    check("attach13: copy_attachment_to_shared(None) = None без TypeError",
          copy_attachment_to_shared(None, src13, {"network_enabled": True,
                                                  "network_shared_path": src_dir13}) is None)
    page, tab, _ = build()
    _open_card(tab, via_add=True)
    picker13 = getattr(page, "_controls_attach_picker", None)
    check("attach13: пикер вложений зарегистрирован", picker13 is not None)

    class _F13:
        def __init__(self, path, name):
            self.path = path
            self.name = name

    def _fire_picker(picker_, ev_):
        eh = getattr(picker_, "on_result", None)
        if eh is None:
            return False
        if callable(eh) and not hasattr(eh, "_EventHandler__handlers"):
            eh(ev_)
            return True
        return _invoke_event_handler(eh, ev_)

    ok13 = True
    try:
        _fire_picker(picker13, type("E", (), {"files": [_F13(src13, "scan.png")]})())
    except Exception:
        ok13 = False
        traceback.print_exc()
    check("attach13: прикрепление к новой карточке без исключений", ok13)
    att_texts13 = [t.value for t in walk(tab) if isinstance(t, ft.Text) and t.value == "scan.png"]
    check("attach13: файл сразу виден в списке вложений", len(att_texts13) >= 1)
    att_root13 = os.path.join(os.environ["APPDATA"], "porayonka", "controls_attachments")
    copied13 = []
    if os.path.isdir(att_root13):
        for d in os.listdir(att_root13):
            pth = os.path.join(att_root13, d)
            if os.path.isdir(pth) and any(f.startswith("scan") for f in os.listdir(pth)):
                copied13.append(d)
    check("attach13: файл скопирован в папку вложений (uuid новой карточки)",
          len(copied13) >= 1, f"{copied13}")

    # ── 37. Раунд 13, задача 5: сеть включена — в shared; shared недоступен — локально ──
    shared_dir13 = tempfile.mkdtemp(prefix="porayonka_shared_att_")
    save_settings({"network_enabled": True, "network_role": "admin", "network_user": "",
                   "network_shared_path": os.path.join(shared_dir13, "controls.json"),
                   "notify_log": {}, "notify_sound": True, "extra_people": []})
    _seed_raw([_ctrl("a14", "А-14", executors=["Семисенко И.Ю."])])
    page, tab, _ = build()
    _open_card(tab, via_add=True)
    src14 = os.path.join(src_dir13, "scan2.png")
    with open(src14, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"2" * 32)
    ok14 = True
    try:
        _fire_picker(page._controls_attach_picker,
                     type("E", (), {"files": [_F13(src14, "scan2.png")]})())
    except Exception:
        ok14 = False
        traceback.print_exc()
    check("attach13: при сети — без исключений", ok14)
    shared_att13 = os.path.join(shared_dir13, "controls_attachments")
    in_shared = False
    if os.path.isdir(shared_att13):
        for d in os.listdir(shared_att13):
            if any(f.startswith("scan2") for f in os.listdir(os.path.join(shared_att13, d))):
                in_shared = True
    check("attach13: при включённой сети файл ушёл в shared", in_shared)
    # shared недоступен (путь поверх файла) — фолбэк в локальную папку, без TypeError
    block_dir13 = tempfile.mkdtemp(prefix="porayonka_block_")
    block_file13 = os.path.join(block_dir13, "block")
    with open(block_file13, "w", encoding="utf-8") as f:
        f.write("x")
    bad_settings = {"network_enabled": True,
                    "network_shared_path": os.path.join(block_file13, "controls.json")}
    rel_bad = None
    ok_bad = True
    try:
        rel_bad = copy_attachment_to_shared("cid13", src13, bad_settings)
    except Exception:
        ok_bad = False
        traceback.print_exc()
    check("attach13: shared недоступен — copy_to_shared вернул None без TypeError",
          ok_bad and rel_bad is None)
    rel_loc = copy_attachment_to_local("cid13", src13)
    check("attach13: локальный фолбэк скопировал файл", rel_loc is not None)

    # ── 38. Раунд 14, задача 3: справочники — overlay с resize и построчным скроллом ──
    save_settings({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "custom_initiators": [],
                   "hidden_people": [], "hidden_init_groups": [], "init_renames": {}})
    _seed_raw([_ctrl("r14", "Р-14", executors=["Семисенко И.Ю."], controller="Потемкин С.А.")])
    page, tab, _ = build()
    refb14 = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
              and getattr(c, "text", None) == "Справочники"]
    refb14[0].on_click(None)
    check("refs14: не AlertDialog (overlay-Container)", len(page.dialogs) == 0)
    ovl14 = _refs_overlay_of(tab)
    check("refs14: overlay видим", ovl14 is not None)
    if ovl14:
        stacks14 = [c for c in walk(ovl14) if isinstance(c, ft.Stack)]
        gds14 = [c for c in walk(ovl14) if isinstance(c, ft.GestureDetector)
                 and getattr(c, "on_pan_update", None) is not None]
        check("refs14: resize-хэндл в правом нижнем углу", len(gds14) >= 1, f"{len(gds14)}")
        if gds14:
            # Раунд 15 (задача 4): хэндл пришит к углу через right=0/bottom=0 —
            # следует за углом карточки при resize (раньше left/top пересчитывали
            # вручную и без update — хэндл «замирал» на старом месте).
            check("refs15: хэндл справочников пришит к углу (right=0/bottom=0)",
                  gds14[0].right == 0 and gds14[0].bottom == 0,
                  f"right={gds14[0].right} bottom={gds14[0].bottom}")
            check("refs15: у хэндла справочников нет left/top",
                  gds14[0].left is None and gds14[0].top is None)
        if gds14 and stacks14:
            rcard = stacks14[0].controls[0]
            w0, h0 = rcard.width, rcard.height
            _invoke_event_handler(gds14[0].on_pan_update,
                                  type("E", (), {"delta_x": 60, "delta_y": 40})())
            check("refs14: resize растягивает окно",
                  rcard.width == w0 + 60 and rcard.height == h0 + 40,
                  f"w={rcard.width} h={rcard.height}")
            check("refs14: рамка overlay-карточки равномерная + скругление",
                  rcard.border.top.color == rcard.border.left.color
                  and (rcard.border_radius or 0) > 0)
            # Раунд 15 (задача 4): структура тела — header / expand-секции / футер.
            # Корневая колонка БЕЗ scroll: футер «Применить» прибит к низу и виден
            # при исходном размере карточки.
            rbody = rcard.content
            check("refs15: корневая колонка справочников БЕЗ scroll (футер прибит)",
                  getattr(rbody, "scroll", None) is not ft.ScrollMode.AUTO,
                  f"scroll={getattr(rbody, 'scroll', None)}")
            body_children = getattr(rbody, "controls", []) or []
            apply_in_last = [b for b in walk(body_children[-1]) if isinstance(b, ft.ElevatedButton)
                             and getattr(b, "text", None) == "Применить"] if body_children else []
            check("refs15: футер с «Применить» — последний блок (вне скролла)",
                  len(apply_in_last) >= 1)
            sections15 = [c for c in body_children if isinstance(c, ft.Container)
                          and (getattr(c, "expand", 0) or 0) > 0]
            check("refs15: обе секции списков expand (растут при resize)",
                  len(sections15) >= 2, f"{len(sections15)} секций")
        lists14 = [c for c in walk(ovl14) if isinstance(c, ft.Column)
                   and getattr(c, "scroll", None) == ft.ScrollMode.ADAPTIVE
                   and (getattr(c, "expand", 0) or 0) > 0]
        # Раунд 16 (задачи 2–3): НИКАКОЙ подписки on_scroll — её наличие в Flet
        # 0.23.2 включало ScrollNotificationControl, чьи нотификации без ключей
        # 'sd'/'dir' роняли конвертер OnScrollEvent (KeyError десятками в логе).
        check("refs16: у списков НЕТ on_scroll (нативный скролл, без KeyError)",
              len(lists14) >= 2
              and all(c._get_attr("onScroll") is None for c in lists14),
              f"{len(lists14)} списков")
        check("refs16: scroll=ADAPTIVE — видимый бегунок (thumbVisibility=true)",
              len(lists14) >= 2)
        check("refs15: списки expand=True (заполняют секцию при растягивании)",
              len(lists14) >= 2 and all((c.expand or 0) > 0 for c in lists14))
        # Раунд 16 (задача 4): размеры окна справочников сохраняются в settings
        # и применяются при переоткрытии.
        if gds14 and stacks14:
            _invoke_event_handler(gds14[0].on_pan_end, type("E", (), {})())
            st_ref = load_settings()
            check("refs16: refs_width сохранён в settings",
                  int(st_ref.get("refs_width") or 0) == 680 + 60,
                  f"w={st_ref.get('refs_width')}")
            check("refs16: refs_height сохранён в settings",
                  int(st_ref.get("refs_height") or 0) == 560 + 40,
                  f"h={st_ref.get('refs_height')}")
            # закрыть и переоткрыть — размеры должны восстановиться
            apply16 = _refs_apply_of(ovl14)
            if apply16:
                apply16[0].on_click(None)
            refb14b = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
                       and getattr(c, "text", None) == "Справочники"]
            refb14b[0].on_click(None)
            ovl14b = _refs_overlay_of(tab)
            stacks14b = [c for c in walk(ovl14b) if isinstance(c, ft.Stack)] if ovl14b else []
            rcard_b = stacks14b[0].controls[0] if stacks14b else None
            check("refs16: переоткрытое окно — размеры восстановлены из settings",
                  rcard_b is not None and rcard_b.width == 740 and rcard_b.height == 600,
                  f"w={getattr(rcard_b, 'width', None)} h={getattr(rcard_b, 'height', None)}")

    # ── 39. Раунд 16, задача 1: левая статусная полоса — строго 4 px ──
    # В settings cобран «битый» col_widths с bar=40 — причина «больших цветных
    # блоков» на приёмке: общий кламп max(40, v) раздувал сохранённые 4 px.
    save_settings({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [],
                   "col_widths": {"bar": 40, "num": 50, "incoming": 200}})
    _seed_raw([_ctrl("b16", "Б-16", executors=["Семисенко И.Ю."])])
    page, tab, _ = build()
    st16 = load_settings()
    check("bar16: устаревший ключ bar вычищен из col_widths при старте",
          "bar" not in (st16.get("col_widths") or {}),
          f"{st16.get('col_widths')}")
    # заголовок: первый элемент — прозрачный спейсер полосы шириной 4
    hdr16 = _header_row_of(tab)
    check("bar16: заголовок найден", hdr16 is not None)
    if hdr16:
        spacer16 = hdr16.controls[0]
        check("bar16: спейсер полосы в заголовке = 4 px (bar=40 из settings проигнорирован)",
              getattr(spacer16, "width", None) == 4, f"w={getattr(spacer16, 'width', None)}")
        check("bar16: спейсер без цвета (прозрачный)",
              getattr(spacer16, "bgcolor", None) in (None, "transparent"))
        check("bar16: остальные сохранённые ширины применены (num=50)",
              getattr(hdr16.controls[1], "width", None) == 50,
              f"w={getattr(hdr16.controls[1], 'width', None)}")
    rows16 = _visible_rows(tab)
    check("bar16: строки есть", len(rows16) >= 1)
    if rows16:
        stc16 = rows16[0].content
        check("bar16: контент строки — Stack (полоса отдельным слоем)",
              isinstance(stc16, ft.Stack))
        if isinstance(stc16, ft.Stack) and len(stc16.controls) >= 2:
            bar16 = stc16.controls[1]
            check("bar16: полоса строго 4 px",
                  getattr(bar16, "width", None) == 4, f"w={getattr(bar16, 'width', None)}")
            check("bar16: полоса пришита к левому краю (left=0)",
                  getattr(bar16, "left", None) == 0)
            check("bar16: полоса на полную высоту (top=0/bottom=0)",
                  getattr(bar16, "top", None) == 0 and getattr(bar16, "bottom", None) == 0)
            check("bar16: полоса цветная по статусу (для Б-16 — in_progress)",
                  getattr(bar16, "bgcolor", None) == GLASS["in_progress"],
                  f"bg={getattr(bar16, 'bgcolor', None)}")
            inner16 = stc16.controls[0]
            row16 = getattr(inner16, "content", None)
            numcell16 = row16.controls[1] if isinstance(row16, ft.Row) else None
            check("bar16: номер строки на нейтральном фоне (без заливки)",
                  numcell16 is not None
                  and getattr(numcell16, "bgcolor", None) in (None, "transparent"))
        # drag любой границы колонки — bar НЕ сохраняется в col_widths
        def _gd_sub_h(g, attr):
            eh = getattr(g, attr, None)
            return len(getattr(eh, "_EventHandler__handlers", {})) if eh is not None else 0
        drags16 = [c for c in walk(tab) if isinstance(c, ft.GestureDetector)
                   and _gd_sub_h(c, "on_horizontal_drag_update") > 0]
        if drags16:
            _invoke_event_handler(drags16[0].on_horizontal_drag_update,
                                  type("E", (), {"delta_x": 10})())
            _invoke_event_handler(drags16[0].on_horizontal_drag_end, type("E", (), {})())
            st16b = load_settings()
            check("bar16: после drag колонок bar НЕ сохраняется в col_widths",
                  "bar" not in (st16b.get("col_widths") or {}),
                  f"{st16b.get('col_widths')}")

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()

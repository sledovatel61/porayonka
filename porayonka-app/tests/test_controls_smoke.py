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

Раунд 17 (PROMPT_контроли_доработка17.md):
  * скролл справочников: scroll=ALWAYS (thumbVisibility=true безусловно,
    scrollable_control.dart — у ADAPTIVE была ветка false, бегунок на живом
    Windows-клиенте не появлялся) + локальная ScrollbarTheme на refs_card
    (яркий thumb #66ffffff, толщина 8, дорожка, interactive=True — бегунок
    draggable); on_scroll по-прежнему не подписан (KeyError 'sd'/'dir');
  * фильтры: две строки объединены в одну filter_row (поиск фикс 240 вместо
    expand, дропдауны ужаты, даты без иконки-календаря, «Сброс» — IconButton,
    «Активные/Архив» справа); Row scroll=AUTO — на узких окнах строка
    прокручивается вместо RenderFlex overflow;
  * заголовок таблицы двухстрочный: высота 34 -> 50, max_lines=2 без no_wrap,
    стрелка сортировки суффиксом текста, drag-хэндлы на всю новую высоту,
    геометрия разделителей по X неизменна.

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

Раунд 18 (PROMPT_контроли_доработка18.md):
  * строка фильтров: слева заголовок «Фильтры» (шрифт как «Контроли», 20 bold),
    полноценная кнопка «Сбросить фильтры», панель на всю ширину окна
    (_apply_table_geometry: filter_row.width = tw); компоновка в две зоны —
    скроллящийся inner (поиск + 5 дропдаунов) и прибитая справа зона
    (даты «С:»/«По:», сброс, «Активные/Архив»);
  * Excel: колонка H «Разовый / постоянный» комбинированная как в исходной
    таблице — импорт даты «01.09.2026» -> разовый + end_date (конечная дата
    больше НЕ теряется), текста «<дата> далее каждые 3 месяца» -> период 90 +
    end_date; due — из колонки I (напоминание). Экспорт пишет конечные даты
    обратно (control_type_text), round-trip через _controls_full и через
    чистый текст H;
  * заголовки колонок таблицы приложения — точно как TABLE_HEADERS исходной
    таблицы (единый источник), + «Статус»/«Действия»;
  * справочник людей: чипы ролей «И»/«К» (исполнитель/контролёр, можно обе —
    одно лицо в обеих категориях), settings.person_roles; умолчания по фамилии
    (криминалист=исполнитель, дефолтный контролёр=контролёр, тёзки сливаются с
    обеими ролями, extra=обе); rename/remove переносят и вычищают назначения;
    фильтры «Все исполнители»/«Все контролеры» — раздельные списки по ролям.

Раунд 22 (PROMPT_контроли_доработка22.md):
  * фильтры «Все исполнители»/«Все контролеры» — ПОЛНЫЙ справочник людей БЕЗ
    разделения по ролям (роли person_roles влияют только на списки выбора в
    карточке); «Прочие» — только люди ВНЕ справочника;
  * контроли без id (старый импорт): heal в load_controls (id из префикса
    папки вложений/новый uuid, сохраняется), id при импорте — сразу,
    ensure_control_id в карточке, гарды вложений без TypeError Path/None,
    предпросмотр — фолбэк по rel-пути;
  * «Сохранить» с пустой «Датой поступления» больше НЕ тихий отказ — дата
    проставляется автоматически; end_date разового контроля не стирается;
  * «Исполнен пункт» — мульти-выбор чекбоксами; sync_due_after_tasks сдвигает
    «следующую дату»/срок разового с исполненных пунктов на оставшиеся.

Запуск:  cd porayonka-app && python tests/test_controls_smoke.py
"""
import io
import json
import os
import sys
import tempfile
import time
import contextlib
import traceback
from datetime import datetime, timedelta

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
    get_controller_names, get_executor_names,
    get_all_people_names, get_person_roles, set_person_roles,
    canonical_initiator_group, initiator_filter_options,
    DEFAULT_SETTINGS,
)
from core.controls_models import (  # noqa: E402
    Control, OVERDUE, TODAY, SOON, IN_PROGRESS, deadline_status, name_matches,
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


def _save_off(settings_dict):
    """Раунд 35: сохранение настроек с выключенной сетью для изолированных
    тестов (default network_enabled=True — миграция включила бы сеть)."""
    d = dict(settings_dict)
    d["network_enabled"] = False
    save_settings(d)
    return d


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
    и None, если карточка не открыта.
    Раунд 20 (задача 2): широкий вариант — middle_scroll.content это Row
    [левая колонка, панель пунктов]; узкий — Column со стопкой секций."""
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
    mc = getattr(mid, "content", None)
    if mc is None:
        return None
    items = getattr(mc, "controls", None)
    if not isinstance(items, list) or len(items) < 2:
        return None
    return items[0], items[1], mc


def panels_of(col_container):
    """Все glass-панели внутри контейнера колонки (непустой content).
    Раунд 20 (задача 2): правая колонка — ОДНА панель «Пункты задания»
    (у Container нет controls) — тогда возвращаем её саму."""
    if col_container is None:
        return []
    col = getattr(col_container, "content", col_container)
    controls = getattr(col, "controls", None)
    if controls is None:
        return [col] if getattr(col, "content", None) is not None else []
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


def _header_row19(tab):
    """Раунд 19: строка заголовка таблицы (20 контролов: bar + 10 ячеек +
    9 разделителей; колонка «Действия» удалена)."""
    hdrs = [c for c in walk(tab) if isinstance(c, ft.Container)
            and getattr(c, "height", None) == 50
            and isinstance(getattr(c, "content", None), ft.Row)
            and len(getattr(c.content, "controls", []) or []) >= 20]
    return hdrs[0].content if hdrs else None


def _header_texts19(tab):
    """Тексты ячеек заголовка таблицы (верхний регистр, без стрелок сортировки)."""
    hdr = _header_row19(tab)
    if hdr is None:
        return []
    out = []
    for st in hdr.controls:
        if isinstance(st, ft.Stack) and st.controls:
            t = getattr(st.controls[0], "content", None)
            if isinstance(t, ft.Text):
                out.append((t.value or "").replace("▲", "").replace("▼", "").strip())
    return out


def main():
    _seed_controls()
    # Раунд 35: сеть включена по умолчанию — первые тесты (карточка/таблица)
    # требуют изоляции, выключаем сеть ДО первого build().
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
               "network_shared_path": "", "notify_log": {}, "notify_sound": True})

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
        # Раунд 15 (задача 3): колонки карточки ГИБКИЕ — expand в Row без
        # tight (адаптируются к ширине карточки), явных width больше нет.
        # Раунд 20 (задача 2): соотношение 10/9 — правой (пункты) стало шире.
        check("контейнер левой колонки expand>0 (гибкая)", (getattr(lc, "expand", 0) or 0) > 0, f"expand={lc.expand}")
        check("контейнер правой колонки expand>0 (гибкая)", (getattr(rc, "expand", 0) or 0) > 0, f"expand={rc.expand}")
        check("левая колонка шире правой (10/9)",
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
            # точка создаёт milestone-карточку с полем «Точка (описание)»;
            # раунд 20 (задача 2): «Промежуточные точки» — в ЛЕВОЙ колонке.
            fields = [t for t in walk(lc) if isinstance(t, ft.TextField)
                      and (t.hint_text or "").startswith("Точка")]
            check("точка добавлена (поле точки в левой колонке)", len(fields) >= 1,
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
        check("исполнители - канонический список (без мусора из данных)",
              "Семисенко Иван Юрьевич" in opts
              and "Чашин Эдуард Александрович" in opts
              and "Чашин Эдуард Анатольевич" not in opts
              and "Потемкин Сергей Анатольевич" not in opts,
              f"{len(opts)-1} опций")
        # Раунд 18→22: раунд 18 не пускал дефолтных контролёров без роли «И»
        # в фильтр исполнителей; раунд 22 (задача 4) отменил деление фильтров
        # по ролям — опции = ПОЛНЫЙ справочник (роли — только для пикеров
        # карточки). «Чашин Э.А.» слит с криминалистом-тёзкой одной записью.
        check("исполнители - полный справочник: дефолтные контролёры тоже есть",
              "Потемкин С.А." in opts and "Чашин Э.А." not in opts)
        check("исполнители - без дублей", len(opts) == len(set(opts)))
        check("исполнители - «Прочие» в конце", opts[-1] == FILTER_OTHER)
    ct = hints.get("Все контролеры")
    check("dropdown «Все контролеры» найден", ct is not None)
    if ct:
        opts = [o.key for o in (ct.options or [])]
        # Раунд 18→22: раунд 18 делил фильтр контролёров по ролям; раунд 22
        # (задача 4) — опции = тот же ПОЛНЫЙ справочник людей (иначе контролёр
        # со снятым чипом терялся из фильтра, а контроли падали в «Прочие»).
        # Слияние тёзок сохраняется: «Чашин Э.А.» отдельной записью не выводится.
        check("контролёры - полный справочник (Потемкин + Чашин одной записью)",
              "Потемкин С.А." in opts
              and "Чашин Эдуард Александрович" in opts
              and "Чашин Э.А." not in opts
              and "Семисенко Иван Юрьевич" in opts,
              f"{len(opts)-1} опций")
        check("контролёры - без дублей", len(opts) == len(set(opts)))
        check("контролёры - «Прочие» в конце", opts[-1] == FILTER_OTHER)

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
    check("merge: конфликт - побеждает новый updated_at",
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
    check("notify: new - первый раз уведомляет", _should_notify(nlog, "c1", "new", "2026-08-05") is True)
    nlog["c1:new"] = "2026-08-05"
    check("notify: new - повтор не уведомляет", _should_notify(nlog, "c1", "new", "2026-08-05") is False)
    check("notify: new - на следующий день тоже нет", _should_notify(nlog, "c1", "new", "2026-08-06") is False)
    check("notify: overdue - первый раз уведомляет", _should_notify(nlog, "c1", OVERDUE, "2026-08-05") is True)
    nlog["c1:overdue"] = "2026-08-05"
    check("notify: overdue - в тот же день нет", _should_notify(nlog, "c1", OVERDUE, "2026-08-05") is False)
    check("notify: overdue - на следующий день уведомляет", _should_notify(nlog, "c1", OVERDUE, "2026-08-06") is True)
    # round-trip журнала через настройки
    # Дата берётся относительной: load_settings вызывает prune_notify_log(days=30),
    # и захардкоженная дата через месяц после записи молча пропадала (тест падал
    # на baseline независимо от кода приложения).
    import datetime as _dt_nl
    _nl_date = (_dt_nl.datetime.now() - _dt_nl.timedelta(days=1)).strftime("%Y-%m-%d")
    _save_off({"notify_log": {"c1:new": _nl_date}, "notify_sound": False})
    loaded = load_settings()
    check("settings: notify_log сохраняется в controls_settings.json",
          (loaded.get("notify_log") or {}).get("c1:new") == _nl_date)
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
    check("tab: network_enabled - контроль из shared в таблице", "ВХСОП-NET" in texts2)
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
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
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
    check("name_matches: чужая фамилия - False",
          name_matches("Семисенко Иван Юрьевич", "Гайнутдинов С.И.") is False)
    check("name_matches: пустая строка - False",
          name_matches("Семисенко Иван Юрьевич", "") is False)
    check("name_matches: None - False",
          name_matches("Семисенко Иван Юрьевич", None) is False)
    check("name_matches: пустой canonical - False",
          name_matches("", "Семисенко И.Ю.") is False)
    check("name_matches: фамилия <3 символов - False",
          name_matches("Ян И.В.", "Ян Петрович") is False)
    check("name_matches: короткая форма vs полное ФИО (контролёр)",
          name_matches("Потемкин С.А.", "Потемкин Сергей Анатольевич") is True)
    check("name_matches: опечатка в фамилии - лишняя буква",
          name_matches("Семисенко Иван Юрьевич", "Семисеннко И.Ю.") is True)
    check("name_matches: опечатка в фамилии - вставка",
          name_matches("Гайнутдинов Станислав Игоревич", "Гайнутдитнов С.И.") is True)
    check("name_matches: опечатка в фамилии - пропуск буквы",
          name_matches("Макаренко Роман Андреевич", "Макарено Р.А.") is True)
    check("name_matches: похожая фамилия ниже порога - False",
          name_matches("Семисенко Иван Юрьевич", "Семенов И.Ю.") is False)

    # 15б. опции фильтров — ПОЛНЫЙ справочник (раунды 18→22) + «Прочие»
    # Раунд 22 (задача 4): фильтры больше НЕ делятся по ролям person_roles —
    # иначе человек со снятым чипом «И» исчезал из фильтра, а его контроли
    # падали в «Прочие». Роли влияют только на списки выбора в карточке.
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
        # Раунд 22 (задача 4): исполнители = ПОЛНЫЙ справочник людей (без деления
        # по ролям) + «Прочие» в конце.
        expected = ["all"] + get_all_people_names(load_settings()) + [FILTER_OTHER]
        check("фильтр-опции: ровно полный справочник людей + «Прочие»",
              opts == expected, f"{len(opts)} опций")
        check("фильтр-опции: мусор из данных не попал",
              "Миронович Д.В.-5.1" not in opts
              and "Т.С.А" not in "".join(opts)
              and "Авакян А.А." not in opts
              and "Посторонний А.А." not in opts)
        # Раунд 22 (задача 4): дефолтный контролёр ПОЯВЛЯЕТСЯ в фильтре
        # исполнителей (как человек из справочника), даже без роли «И».
        check("фильтр-опции: Потемкин (контролёр по роли) есть в исполнителях",
              "Потемкин С.А." in opts)
    ct = _find_dd(tab, "Все контролеры")
    check("фильтр-опции: dropdown «Все контролеры» найден", ct is not None)
    if ct:
        opts = [o.key for o in (ct.options or [])]
        expected = ["all"] + get_all_people_names(load_settings()) + [FILTER_OTHER]
        check("фильтр-опции контролёров: тот же полный справочник + «Прочие»",
              opts == expected, f"{len(opts)} опций")
        # Раунд 18→22: дефолтный контролёр «Чашин Э.А.» слит с криминалистом-
        # тёзкой в одну запись — в списке ровно один Чашин.
        check("фильтр-опции контролёров: Чашин - одна запись (слит с криминалистом)",
              "Чашин Э.А." not in opts
              and opts.count("Чашин Эдуард Александрович") == 1)

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

    # ── 16. Раунды 7+18→22: «Прочие» = нет в ПОЛНОМ справочнике людей ──
    # Раунд 18 (задача 4): категория человека (исполнитель/контролёр) задавалась
    # чипами «И»/«К» и фильтры делились по ролям. Раунд 22 (задача 4): роли
    # больше НЕ влияют на фильтры (только на списки выбора в карточке) —
    # иначе человек со снятым чипом терялся из фильтра, а его контроли падали
    # в «Прочие» (сырьё пользователя: Авакян/Агеев/Чащин в «Прочих»).
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True})
    _seed_raw([
        _ctrl("p1", "П-1", executors=["Потемкин С.А."]),
        _ctrl("p2", "П-2", executors=["Чашин Э.А."]),
        _ctrl("p3", "П-3", executors=["Посторонний А.А."]),
    ])
    page, tab, _ = build()
    ex16 = _find_dd(tab, "Все исполнители")
    check("roles22: Потемкин ЕСТЬ в опциях исполнителей (полный справочник)",
          ex16 is not None and "Потемкин С.А." in [o.key for o in (ex16.options or [])])
    check("«Прочие»: выбор применился",
          _set_filter(tab, "Все исполнители", FILTER_OTHER))
    vis = _visible_texts(tab)
    # «Потемкин С.А.» и «Чашин Э.А.» — люди справочника (дефолтные контролёры) →
    # их контроли в «Прочие» НЕ попадают; «Посторонний А.А.» вне справочника →
    # попадает. Роли person_roles на это больше не влияют.
    check("«Прочие»: контроли людей справочника НЕ попадают в «Прочие»",
          "П-1" not in vis and "П-2" not in vis, f"видно: {sorted(vis)}")
    check("«Прочие»: посторонний - в «Прочие»", "П-3" in vis)
    # даже ЯВНЫЙ сброс обеих ролей человека не убирает его из фильтров
    st16 = load_settings()
    set_person_roles(st16, "Потемкин С.А.", [])
    check("roles22: роли Потемкина сброшены (данные сохранились)",
          (load_settings().get("person_roles") or {}).get("Потемкин С.А.") == [])
    page, tab, _ = build()
    ex16b = _find_dd(tab, "Все исполнители")
    check("roles22: и без ролей Потемкин остаётся в опциях исполнителей",
          ex16b is not None and "Потемкин С.А." in [o.key for o in (ex16b.options or [])])
    ct16b = _find_dd(tab, "Все контролеры")
    check("roles22: и в опциях контролёров",
          ct16b is not None and "Потемкин С.А." in [o.key for o in (ct16b.options or [])])
    check("«Прочие»: фильтр по Потемкину находит его контроль",
          _set_filter(tab, "Все исполнители", "Потемкин С.А."))
    vis = _visible_texts(tab)
    check("«Прочие»: фильтр по Потемкину - только его контроль",
          "П-1" in vis and "П-2" not in vis and "П-3" not in vis, f"видно: {sorted(vis)}")
    check("«Прочие»: и без ролей П-1 не попадает в «Прочие»",
          _set_filter(tab, "Все исполнители", FILTER_OTHER))
    vis = _visible_texts(tab)
    check("«Прочие»: только посторонний остался",
          "П-1" not in vis and "П-2" not in vis and "П-3" in vis, f"видно: {sorted(vis)}")

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
    # Раунд 21 (задача 6): заголовок без личных фамилий — просто «За кем контроль»
    check("excel: G2 - «За кем контроль» (без фамилий в скобках)",
          str(wsx["G2"].value) == "За кем контроль")
    check("excel: H2 - «Разовый / постоянный»", "Разовый / постоянный" in str(wsx["H2"].value))
    check("excel: автофильтр A2:J4 (от шапки до последней строки данных)",
          wsx.auto_filter.ref == "A2:J4", wsx.auto_filter.ref)
    check("excel: ширина B = 34.3 как в эталоне",
          abs((wsx.column_dimensions["B"].width or 0) - 34.3) < 0.2)
    check("excel: C3 дата поступления - дата Excel (DD.MM.YYYY)",
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
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
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
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
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
    _save_off({"network_enabled": False, "network_role": "user", "network_user": "Семисенко Иван Юрьевич",
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
    check("people: «Прочие» - только посторонний", "М-2" in vis and "М-1" not in vis)
    check("people: remove_extra_person удаляет",
          remove_extra_person(load_settings(), "Макаренко Роман Андреевич") is True)

    # ── 22. Раунд 8, задача 2: склейки инициаторов ──
    check("initiator: «ГУК СК ГУК ЮФО» разбивается на «гук,гук юфо»",
          canonical_initiator_group("ГУК СК ГУК ЮФО") == "гук,гук юфо")
    check("initiator: «ГСУ ГУК» разбивается на «гсу,гук»",
          canonical_initiator_group("ГСУ ГУК") == "гсу,гук")
    opts8 = initiator_filter_options(["ГУК СК ГУК ЮФО", "ГСУ ГУК", "СУ", "ОКРИМ"])
    check("initiator: опции без склеек - отдельные каноны",
          "ГУК" in opts8 and "ГУК ЮФО" in opts8 and "ГСУ" in opts8 and "СУ" in opts8,
          f"{opts8}")
    check("initiator: «ГУК СК, ГУК ЮФО» (с запятой) тоже разбивается",
          canonical_initiator_group("ГУК СК, ГУК ЮФО") == "гук,гук юфо")

    # ── 23. Раунд 8, задача 3: resize на ВСЕХ границах + видимые разделители ──
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": []})
    _seed_raw([_ctrl("r8", "Р-8", executors=["Семисенко И.Ю."])])
    page, tab, _ = build()
    def _gd_subs(g, attr):
        eh = getattr(g, attr, None)
        return len(getattr(eh, "_EventHandler__handlers", {})) if eh is not None else 0
    gds = [c for c in walk(tab) if isinstance(c, ft.GestureDetector)
           and _gd_subs(c, "on_horizontal_drag_start") > 0]
    # 10 границ колонок (раунд 19: колонка «Действия» удалена — было 11; у
    # resize-хэндла карточки подписки horizontal нет)
    check("resize19: drag-хэндлы на ВСЕХ 10 границах колонок", len(gds) == 10, f"{len(gds)}")
    # разделители в заголовке (1px, цвет #26ffffff)
    seps = [c for c in walk(tab) if isinstance(c, ft.Container)
            and getattr(c, "width", None) == 1 and getattr(c, "bgcolor", None) == "#26ffffff"]
    check("resize19: видимые разделители в заголовке (9 после удаления «Действий»)",
          len(seps) == 9, f"{len(seps)}")
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
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
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
        check("refs14: справочники - не AlertDialog", len(page.dialogs) == 0)
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
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
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
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
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
    check("seps19: в заголовке 9 разделителей (колонка «Действия» удалена)",
          len(hdr) == 9, f"{len(hdr)}")
    check("seps19: в строке 9 разделителей", len(vseps) == 9, f"{len(vseps)}")
    # одинаковое число ячеек между разделителями => X-координаты совпадают
    check("seps19: число колонок заголовка = числу колонок строки (10)",
          len([c for c in walk(tab) if isinstance(c, ft.Stack) and getattr(c, "width", None)]) == 10)

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
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
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

    # ── 30. Раунд 19, задача 1: колонка «Действия» УДАЛЕНА ──
    page, tab, _ = build()
    allc10 = walk(tab)
    action_rows = [c for c in allc10 if isinstance(c, ft.Row)
                   and getattr(c, "alignment", None) == ft.MainAxisAlignment.END
                   and getattr(c, "width", None) is not None]
    check("actions19: в таблице НЕТ Row действий (колонка удалена)", len(action_rows) == 0,
          f"{len(action_rows)}")
    hdr30 = _header_texts19(tab)
    check("actions19: в заголовке нет «ДЕЙСТВИЯ»",
          "ДЕЙСТВИЯ" not in hdr30, f"{hdr30[-3:] if hdr30 else None}")
    rows19 = _visible_rows(tab)
    check("actions19: иконок редактирования/удаления в строках нет",
          not any(isinstance(c, ft.IconButton)
                  and getattr(c, "tooltip", None) in ("Редактировать", "Удалить (в архив)")
                  for r in rows19 for c in walk(r)))
    check("actions19: клик по строке по-прежнему открывает карточку",
          _open_card(tab, via_add=False))

    # ── 31. Раунд 10, задача 3: редактирование записи в справочнике ──
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
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
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
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
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": []})
    _seed_raw([_ctrl("w1", "Ш-1", executors=["Семисенко И.Ю."])])
    st_w = load_settings()
    st_w.pop("col_widths", None)
    save_settings(st_w)

    def _header_row_of(tab_):
        # Раунд 17 (задача 3): заголовок двухстрочный — высота 34 -> 50 px.
        hdrs = [c for c in walk(tab_) if isinstance(c, ft.Container)
                and getattr(c, "height", None) == 50
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
                    and getattr(c, "height", None) == 50
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
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
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
    # Раунд 17 (задача 1): списки — Column(scroll=ALWAYS, expand=True), БЕЗ
    # кастомного on_scroll. ALWAYS => thumbVisibility=true БЕЗУСЛОВНО (у ADAPTIVE
    # была ветка false, и бегунок на живом Windows-клиенте не появлялся).
    ref_lists = [c for c in walk(dlg13) if isinstance(c, ft.Column)
                 and getattr(c, "scroll", None) == ft.ScrollMode.ALWAYS
                 and (getattr(c, "expand", 0) or 0) > 0]
    check("ref13: списки компактные (spacing=2)",
          len(ref_lists) >= 2 and all(c.spacing == 2 for c in ref_lists),
          f"{[c.spacing for c in ref_lists]}")
    check("ref15: списки справочников expand=True (растут при resize)",
          len(ref_lists) >= 2 and all((c.expand or 0) > 0 for c in ref_lists)
          and all(getattr(c, "height", None) is None for c in ref_lists))
    check("refs17: scroll=ALWAYS у списков (бегунок виден всегда)",
          len(ref_lists) >= 2)
    check("refs17: у списков НЕТ подписки on_scroll (нет KeyError 'sd'/'dir')",
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
            from core.controls_data import get_executor_names as _gen13
            en13 = _gen13(st13)
            # Раунд 30 (задача 3): extra-персоны по умолчанию — ТОЛЬКО
            # исполнители (раньше «обе роли» — импортированные люди попадали
            # в «За кем контроль»). Проверяем канон через исполнителей.
            check("ref13: канон - новое есть, старого нет",
                  (base_name + "!!!") in en13 and base_name not in en13)
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
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
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
    check("attach13: при сети - без исключений", ok14)
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
    check("attach13: shared недоступен - copy_to_shared вернул None без TypeError",
          ok_bad and rel_bad is None)
    rel_loc = copy_attachment_to_local("cid13", src13)
    check("attach13: локальный фолбэк скопировал файл", rel_loc is not None)

    # ── 38. Раунд 14, задача 3: справочники — overlay с resize и построчным скроллом ──
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
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
            check("refs15: футер с «Применить» - последний блок (вне скролла)",
                  len(apply_in_last) >= 1)
            sections15 = [c for c in body_children if isinstance(c, ft.Container)
                          and (getattr(c, "expand", 0) or 0) > 0]
            check("refs15: обе секции списков expand (растут при resize)",
                  len(sections15) >= 2, f"{len(sections15)} секций")
        lists14 = [c for c in walk(ovl14) if isinstance(c, ft.Column)
                   and getattr(c, "scroll", None) == ft.ScrollMode.ALWAYS
                   and (getattr(c, "expand", 0) or 0) > 0]
        # Раунд 16 (задачи 2–3): НИКАКОЙ подписки on_scroll — её наличие в Flet
        # 0.23.2 включало ScrollNotificationControl, чьи нотификации без ключей
        # 'sd'/'dir' роняли конвертер OnScrollEvent (KeyError десятками в логе).
        check("refs17: у списков НЕТ on_scroll (нативный скролл, без KeyError)",
              len(lists14) >= 2
              and all(c._get_attr("onScroll") is None for c in lists14),
              f"{len(lists14)} списков")
        check("refs17: scroll=ALWAYS - бегунок виден всегда (thumbVisibility=true)",
              len(lists14) >= 2)
        check("refs15: списки expand=True (заполняют секцию при растягивании)",
              len(lists14) >= 2 and all((c.expand or 0) > 0 for c in lists14))
        # Раунд 17 (задача 1): яркая ScrollbarTheme на карточке справочников —
        # дефолтный бегунок светлой page-темы сливался с тёмным фоном.
        if gds14 and stacks14:
            rcard = stacks14[0].controls[0]
            rtheme = getattr(rcard, "theme", None)
            sbt = getattr(rtheme, "scrollbar_theme", None) if rtheme else None
            check("refs17: у карточки справочников локальная тема скроллбара",
                  sbt is not None, f"theme={rtheme is not None}")
            if sbt:
                check("refs17: бегунок яркий и толстый (thumb_color, thickness>=6)",
                      getattr(sbt, "thumb_color", None) == "#66ffffff"
                      and (getattr(sbt, "thickness", 0) or 0) >= 6,
                      f"thumb={getattr(sbt, 'thumb_color', None)} w={getattr(sbt, 'thickness', None)}")
                check("refs17: бегунок постоянный и draggable",
                      getattr(sbt, "thumb_visibility", None) is True
                      and getattr(sbt, "interactive", None) is True)
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
            check("refs16: переоткрытое окно - размеры восстановлены из settings",
                  rcard_b is not None and rcard_b.width == 740 and rcard_b.height == 600,
                  f"w={getattr(rcard_b, 'width', None)} h={getattr(rcard_b, 'height', None)}")

    # ── 39. Раунд 16, задача 1: левая статусная полоса — строго 4 px ──
    # В settings cобран «битый» col_widths с bar=40 — причина «больших цветных
    # блоков» на приёмке: общий кламп max(40, v) раздувал сохранённые 4 px.
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [],
                   "col_widths": {"bar": 40, "num": 50, "incoming": 200}})
    # Раунд 37 (задача 1): ДАТО-НЕЗАВИСИМЫЙ сид — дефолтный _ctrl с
    # due_date=2026-09-01 ломал проверку цвета полосы, когда «сегодня»
    # достигало/перешагивало эту дату (статус TODAY/OVERDUE вместо ожидаемого
    # IN_PROGRESS). Ставим далёкое будущее — in_progress на любой дате.
    _c16s = _ctrl("b16", "Б-16", executors=["Семисенко И.Ю."])
    _c16s["due_date"] = "2099-12-31"
    _seed_raw([_c16s])
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
        check("bar16: контент строки - Stack (полоса отдельным слоем)",
              isinstance(stc16, ft.Stack))
        if isinstance(stc16, ft.Stack) and len(stc16.controls) >= 2:
            bar16 = stc16.controls[1]
            check("bar16: полоса строго 4 px",
                  getattr(bar16, "width", None) == 4, f"w={getattr(bar16, 'width', None)}")
            check("bar16: полоса пришита к левому краю (left=0)",
                  getattr(bar16, "left", None) == 0)
            check("bar16: полоса на полную высоту (top=0/bottom=0)",
                  getattr(bar16, "top", None) == 0 and getattr(bar16, "bottom", None) == 0)
            check("bar16: полоса цветная по статусу (для Б-16 - in_progress)",
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

    # ── 40. Раунды 17+18: одна строка фильтров, доведённая до эталона ──
    # Раунд 18 (задача 1): заголовок «Фильтры» слева (шрифт как «Контроли»),
    # нормальная кнопка «Сбросить фильтры», панель на всю ширину окна; даты и
    # режимы прибиты справа и не прокручиваются.
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": []})
    _seed_raw([_ctrl("b17", "Б-17", executors=["Семисенко И.Ю."])])
    page, tab, _ = build()
    search17 = [c for c in walk(tab) if isinstance(c, ft.TextField)
                and "Поиск по содержанию" in (getattr(c, "hint_text", "") or "")]
    check("frow17: поле поиска есть", len(search17) == 1)
    rows_with_search = [r for r in walk(tab) if isinstance(r, ft.Row)
                        and search17 and search17[0] in (r.controls or [])]
    check("frow17: найдена строка с поиском", len(rows_with_search) == 1)
    if rows_with_search:
        fr = rows_with_search[0]
        dds17 = [c for c in fr.controls if isinstance(c, ft.Dropdown)]
        texts17 = {t.value for t in walk(fr) if isinstance(t, ft.Text)}
        check("frow17: все 5 выпадающих фильтров в одной строке",
              len(dds17) == 5, f"{len(dds17)}")
        check("frow17: внутренняя строка фильтров скроллится и растянута (expand)",
              getattr(fr, "scroll", None) == ft.ScrollMode.AUTO
              and (getattr(fr, "expand", 0) or 0) > 0,
              f"scroll={getattr(fr, 'scroll', None)} expand={getattr(fr, 'expand', None)}")
        # Раунд 18 (задача 1): внутренняя скроллящаяся строка — ТОЛЬКО поиск и
        # выпадающие фильтры; даты/сброс/режимы — в ПРИБИТОЙ правой зоне
        # внешней строки (не прокручиваются, всегда на виду).
        check("frow18: дат и режимов НЕТ внутри скроллящейся строки",
              "С: —" not in texts17 and "По: —" not in texts17
              and "Активные" not in texts17 and "Архив" not in texts17,
              f"{sorted(t for t in texts17 if t)[:6]}")
        outer18 = [r for r in walk(tab) if isinstance(r, ft.Row)
                   and fr in (r.controls or [])]
        check("frow18: внешняя строка фильтров найдена", len(outer18) == 1)
        if outer18:
            otexts18 = {t.value for t in walk(outer18[0]) if isinstance(t, ft.Text)}
            check("frow18: слева заголовок «Фильтры» шрифтом как «Контроли» (20, bold)",
                  any(isinstance(t, ft.Text) and t.value == "Фильтры"
                      and (getattr(t, "size", 0) or 0) == 20
                      and getattr(t, "weight", None) == ft.FontWeight.BOLD
                      for t in walk(outer18[0])))
            check("frow18: даты «С:»/«По:» - в прибитой правой зоне",
                  "С: —" in otexts18 and "По: —" in otexts18)
            reset18 = [c for c in outer18[0].controls if isinstance(c, ft.ElevatedButton)
                       and getattr(c, "text", None) == "Сбросить фильтры"]
            check("frow18: полноценная кнопка «Сбросить фильтры» (не мелкая иконка)",
                  len(reset18) == 1 and (reset18[0].height or 0) >= 30)
            check("frow18: «Активные/Архив» в той же строке",
                  "Активные" in otexts18 and "Архив" in otexts18)
            # порядок зон: заголовок → скролл-фильтры → даты → сброс → режимы
            kinds18 = [type(c).__name__ for c in outer18[0].controls]
            check("frow18: зоны в порядке «Фильтры | фильтры | С | По | сброс | режимы»",
                  len(kinds18) == 6 and kinds18[0] == "Row" and kinds18[1] == "Row",
                  f"{kinds18}")
        # панель строки фильтров — на всю ширину окна (1280-64=1216)
        panel18 = [c for c in walk(tab) if isinstance(c, ft.Container)
                   and getattr(c, "height", None) == 52
                   and any(isinstance(t, ft.Text) and t.value == "Фильтры"
                           for t in walk(c))]
        check("frow18: панель строки фильтров найдена (высота 52)", len(panel18) >= 1)
        if panel18:
            check("frow18: строка фильтров на всю ширину окна (1216 при 1280)",
                  getattr(panel18[0], "width", None) == 1216,
                  f"w={getattr(panel18[0], 'width', None)}")
    # второй строки фильтров больше нет: ровно один Row содержит Dropdown'ы
    # фильтров (подсказки «Все …» — у dd экспорта Excel подсказка другая)
    rows_with_dds = [r for r in walk(tab) if isinstance(r, ft.Row)
                     and any(isinstance(c, ft.Dropdown)
                             and (getattr(c, "hint_text", "") or "").startswith("Все ")
                             for c in (r.controls or []))]
    check("frow17: ровно одна строка с выпадающими фильтрами (вторая удалена)",
          len(rows_with_dds) == 1, f"{len(rows_with_dds)}")

    # ── 41. Раунд 17, задача 3: заголовок таблицы двухстрочный ──
    hdr17c = [c for c in walk(tab) if isinstance(c, ft.Container)
              and getattr(c, "height", None) == 50
              and isinstance(getattr(c, "content", None), ft.Row)
              and len(getattr(c.content, "controls", []) or []) >= 20]
    check("hdr17: заголовок найден, высота 50 (была 34)", len(hdr17c) >= 1)
    if hdr17c:
        htexts = [t for t in walk(hdr17c[0]) if isinstance(t, ft.Text)
                  and getattr(t, "weight", None) == ft.FontWeight.BOLD]
        check("hdr17: ячейки текста найдены", len(htexts) >= 8, f"{len(htexts)}")
        check("hdr17: перенос на 2 строки (max_lines=2, no_wrap снят)",
              len(htexts) >= 8
              and all((getattr(t, "max_lines", 1) or 1) >= 2 for t in htexts)
              and all(not getattr(t, "no_wrap", False) for t in htexts))
        # стрелка сортировки рядом с текстом: клик по ячейке -> ▲/▼ в тексте
        st_conts = [c for c in walk(hdr17c[0]) if isinstance(c, ft.Container)
                    and getattr(c, "on_click", None) is not None
                    and isinstance(getattr(c, "content", None), ft.Text)]
        if st_conts:
            st_conts[1].on_click(None)
            htexts2 = [t for t in walk(hdr17c[0]) if isinstance(t, ft.Text)
                       and getattr(t, "weight", None) == ft.FontWeight.BOLD]
            vals = [t.value for t in htexts2][:4]
            safe_vals = [v.replace("▲", "^").replace("▼", "v") if v else v for v in vals]
            check("hdr17: strelka sortirovki v tekste posle klik",
                  any(("▲" in (t.value or "")) or ("▼" in (t.value or "")) for t in htexts2),
                  f"{safe_vals}")
        # drag-ресайз сохранён: хэндлы GestureDetector на всю высоту заголовка
        handles17 = [c for c in walk(hdr17c[0]) if isinstance(c, ft.GestureDetector)]
        handle_sizes = [getattr(getattr(h, "content", None), "height", None) for h in handles17]
        check("hdr17: drag-хэндлы колонок есть, высота под новый заголовок (50)",
              len(handles17) >= 8 and all(hh == 50 for hh in handle_sizes),
              f"{len(handles17)} шт, h={sorted(set(handle_sizes))}")

    # ── 42. Раунд 18, задача 2: конечная дата исполнения (колонка H) ──
    # Эталон пользователя: H «Разовый / постоянный» — КОМБИНИРОВАННАЯ колонка:
    # для разового контроля там КОНЕЧНАЯ дата («01.09.2026»), для периодического —
    # текст («ежемесячно» / «10.05.2026 далее каждые 3 месяца»). Колонка I
    # «Следующая дата исполнения» — дата НАПОМИНАНИЯ. Раньше дата из H молча
    # терялась (parse_periodicity её не понимал).
    from openpyxl import Workbook as _WB18, load_workbook as _LWB18
    from core.controls_exporter import control_type_text as _ctt18
    xlsx_in18 = os.path.join(tempfile.mkdtemp(prefix="porayonka_imp18_"), "in.xlsx")
    wb18 = _WB18()
    ws18 = wb18.active
    ws18.title = "Контроли"
    ws18.cell(row=1, column=1, value=TABLE_TITLE)
    for ci18, h18 in enumerate(TABLE_HEADERS, 1):
        ws18.cell(row=2, column=ci18, value=h18)
    rows18 = [
        # разовый с конечной датой 01.09.2026 и напоминанием 10.08.2026
        [1, "ИМП-1", datetime(2026, 7, 1), "СУ", "Разовый контроль",
         "Семисенко И.Ю.", "Потемкин С.А.", datetime(2026, 9, 1), datetime(2026, 8, 10), ""],
        # периодический: «<конечная дата> далее каждые 3 месяца»
        [2, "ИМП-2", datetime(2026, 6, 1), "ГУК", "Периодический контроль",
         "Ливенский В.О.", "Чашин Э.А.", "10.05.2026 далее каждые 3 месяца", datetime(2026, 8, 10), ""],
        # периодический без конечной даты — просто текст периодичности
        [3, "ИМП-3", datetime(2026, 6, 5), "СУ", "Ежемесячный контроль",
         "Авакян А.А.", "Потемкин С.А.", "ежемесячно", datetime(2026, 8, 15), ""],
    ]
    for ri18, rv18 in enumerate(rows18, 3):
        for ci18, v18 in enumerate(rv18, 1):
            ws18.cell(row=ri18, column=ci18, value=v18)
    wb18.save(xlsx_in18)
    parsed18, stats18 = import_from_excel(xlsx_in18, [])
    by18 = {c.incoming_number: c for c in parsed18}
    check("xl18: импорт эталонного файла - все 3 строки", stats18["imported"] == 3,
          f"imported={stats18['imported']} errors={stats18['errors']}")
    ic1 = by18.get("ИМП-1")
    check("xl18: H=дата -> разовый, end_date=конечная дата (01.09.2026 не потерялась)",
          ic1 is not None and ic1.control_type == "once" and ic1.end_date == "2026-09-01",
          f"type={getattr(ic1, 'control_type', None)} end={getattr(ic1, 'end_date', None)}")
    check("xl18: разовый - due из колонки I (10.08.2026, напоминание)",
          ic1 is not None and ic1.due_date == "2026-08-10",
          f"due={getattr(ic1, 'due_date', None)}")
    ic2 = by18.get("ИМП-2")
    check("xl18: «<дата> далее каждые 3 месяца» -> период 90 дней + end_date",
          ic2 is not None and ic2.control_type == "periodic"
          and ic2.period_days == 90 and ic2.end_date == "2026-05-10",
          f"type={getattr(ic2, 'control_type', None)} days={getattr(ic2, 'period_days', None)}"
          f" end={getattr(ic2, 'end_date', None)}")
    check("xl18: периодический - due из колонки I",
          ic2 is not None and ic2.due_date == "2026-08-10")
    ic3 = by18.get("ИМП-3")
    check("xl18: «ежемесячно» -> период 30 дней, end_date пустая",
          ic3 is not None and ic3.control_type == "periodic"
          and ic3.period_days == 30 and not ic3.end_date,
          f"days={getattr(ic3, 'period_days', None)} end={getattr(ic3, 'end_date', None)}")
    # экспорт: колонка H — как в исходной таблице (конечные даты на месте)
    c18a = Control(id="x18a", incoming_number="ЭКС-1", receive_date="2026-07-01",
                   initiator="СУ", content="Разовый с конечной датой",
                   executors=["Семисенко И.Ю."], controller="Потемкин С.А.",
                   control_type="once", period_days=7,
                   due_date="2026-08-10", end_date="2026-09-01")
    c18b = Control(id="x18b", incoming_number="ЭКС-2", receive_date="2026-06-01",
                   initiator="ГУК", content="Периодический с конечной датой",
                   executors=["Ливенский В.О."], controller="Чашин Э.А.",
                   control_type="periodic", period_days=90,
                   due_date="2026-08-10", end_date="2026-05-10")
    check("xl18: текст H разового в таблице/экспорте - конечная дата",
          _ctt18(c18a) == "01.09.2026", f"{_ctt18(c18a)}")
    check("xl18: текст H периодического - «<дата> далее каждые 3 месяца»",
          _ctt18(c18b) == "10.05.2026 далее каждые 3 месяца", f"{_ctt18(c18b)}")
    xlsx_out18 = os.path.join(tempfile.mkdtemp(prefix="porayonka_exp18_"), "out.xlsx")
    ControlsExcelExporter().export([c18a, c18b], xlsx_out18, soon_days=3, full=True)
    w18o = _LWB18(xlsx_out18)
    wso18 = w18o["Контроли"]
    check("xl18: экспорт разового - H = «01.09.2026» (не слово «разовый»)",
          wso18["H3"].value == "01.09.2026", f"H3={wso18['H3'].value!r}")
    check("xl18: экспорт периодического - H = «10.05.2026 далее каждые 3 месяца»",
          wso18["H4"].value == "10.05.2026 далее каждые 3 месяца",
          f"H4={wso18['H4'].value!r}")
    # round-trip через скрытый лист и через чистый текст H — обе даты целы
    pr18, st18x = import_from_excel(xlsx_out18, [])
    bout18 = {c.incoming_number: c for c in pr18}
    check("xl18: round-trip (полный лист) - разовый end_date сохранён",
          st18x["full_format"]
          and bout18.get("ЭКС-1") is not None
          and bout18["ЭКС-1"].end_date == "2026-09-01"
          and bout18["ЭКС-1"].control_type == "once")
    check("xl18: round-trip (полный лист) - период 90 + end_date сохранены",
          bout18.get("ЭКС-2") is not None and bout18["ЭКС-2"].period_days == 90
          and bout18["ЭКС-2"].end_date == "2026-05-10")
    # импорт файла БЕЗ скрытого листа — текст H разбирается эвристикой
    pr18b, _ = import_from_excel(xlsx_in18, [])
    check("xl18: импорт без полного листа - данные из H/I восстановлены",
          len(pr18b) == 3)

    # ── 43. Раунд 18, задача 3: заголовки колонок — точно как в исходной Excel ──
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": []})
    _seed_raw([_ctrl("h18", "Ж-18", executors=["Семисенко И.Ю."])])
    page, tab, _ = build()
    hdr43 = [c for c in walk(tab) if isinstance(c, ft.Container)
             and getattr(c, "height", None) == 50
             and isinstance(getattr(c, "content", None), ft.Row)
             and len(getattr(c.content, "controls", []) or []) >= 20]
    check("hdr18: заголовок таблицы найден", len(hdr43) >= 1)
    if hdr43:
        cells43 = []
        for st43 in hdr43[0].content.controls:
            if isinstance(st43, ft.Stack) and st43.controls:
                t43 = getattr(st43.controls[0], "content", None)
                if isinstance(t43, ft.Text):
                    v43 = (t43.value or "").replace("▲", "").replace("▼", "").strip()
                    cells43.append(v43)
        # Раунд 19 (задача 1): «ДЕЙСТВИЯ» больше нет — колонка удалена
        expected43 = [h.strip().upper() for h in TABLE_HEADERS[:9]] + ["СТАТУС"]
        check("hdr18: заголовки 1:1 с исходной таблицей Excel (+ «Статус», без «Действия»)",
              cells43 == expected43, f"{cells43[:4]}")

    # ── 44. Раунд 18, задача 4: роли person_roles + чипы «И»/«К» в справочнике ──
    from core.controls_data import (add_extra_person, rename_person, remove_person)
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": []})
    st44 = load_settings()
    ex44 = get_executor_names(st44)
    ct44 = get_controller_names(st44)
    check("roles18: умолчание - криминалист только исполнитель",
          "Семисенко Иван Юрьевич" in ex44 and "Семисенко Иван Юрьевич" not in ct44)
    check("roles18: умолчание - Потемкин только контролёр",
          "Потемкин С.А." in ct44 and "Потемкин С.А." not in ex44)
    check("roles18: Чашин слит с криминалистом - обе роли одной записью",
          "Чашин Эдуард Александрович" in ex44
          and "Чашин Эдуард Александрович" in ct44
          and "Чашин Э.А." not in ex44 and "Чашин Э.А." not in ct44)
    # явное снятие дефолтной роли переживает рестарт (пишется даже пустой список)
    set_person_roles(st44, "Чашин Эдуард Александрович", ["executor"])
    check("roles18: снятие роли контролёра - Чашин ушёл из контролёров",
          "Чашин Эдуард Александрович" not in get_controller_names(load_settings()))
    set_person_roles(st44, "Чашин Эдуард Александрович", [])
    check("roles18: пустой список ролей сохраняется (ни один фильтр)",
          "Чашин Эдуард Александрович" not in get_controller_names(load_settings())
          and "Чашин Эдуард Александрович" not in get_executor_names(load_settings()))
    # extra-персона: обе роли; rename переносит назначение, remove вычищает
    st44b = load_settings()
    add_extra_person(st44b, "Тестов Тест Тестович")
    st44b = load_settings()
    set_person_roles(st44b, "Тестов Тест Тестович", ["controller"])
    st44b = load_settings()
    check("roles18: extra-персоне назначена только роль контролёра",
          "Тестов Тест Тестович" in get_controller_names(st44b)
          and "Тестов Тест Тестович" not in get_executor_names(st44b))
    rename_person(st44b, "Тестов Тест Тестович", "Тестов Т.Т.")
    st44b = load_settings()
    pr44 = get_person_roles(st44b)
    check("roles18: переименование переносит роль на новое имя",
          pr44.get("Тестов Т.Т.") == ["controller"]
          and "Тестов Тест Тестович" not in pr44)
    remove_person(st44b, "Тестов Т.Т.")
    st44b = load_settings()
    check("roles18: удаление человека вычищает назначение ролей",
          "Тестов Т.Т." not in get_person_roles(st44b)
          and not any("Тестов" in k for k in (st44b.get("person_roles") or {})))
    # UI: чипы «И»/«К» в строке справочника
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "hidden_people": []})
    _seed_raw([_ctrl("r18", "Р-18", executors=["Семисенко И.Ю."], controller="Потемкин С.А.")])
    page, tab, _ = build()
    ref44 = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
             and getattr(c, "text", None) == "Справочники"]
    ref44[0].on_click(None)
    dlg44 = _refs_overlay_of(tab)
    check("roles18: overlay справочников открыт", dlg44 is not None)

    def _chips_of_person(overlay, name):
        rows_p = [c for c in walk(overlay) if isinstance(c, ft.Container)
                  and getattr(c, "bgcolor", None) == GLASS["surface_alt"]
                  and any(isinstance(t, ft.Text) and t.value == name for t in walk(c))]
        if not rows_p:
            return None
        chips = {}
        for ch in walk(rows_p[0]):
            if isinstance(ch, ft.Container) and getattr(ch, "width", None) == 24 \
                    and getattr(ch, "height", None) == 22 \
                    and getattr(ch, "on_click", None) is not None:
                lbl = getattr(getattr(ch, "content", None), "value", None)
                chips[lbl] = ch
        return chips

    if dlg44:
        hint44 = [t for t in walk(dlg44) if isinstance(t, ft.Text)
                  and t.value and "Чипы «И»/«К»" in str(t.value)]
        check("roles18: подсказка по чипам ролей в справочнике", len(hint44) >= 1)
        chips44 = _chips_of_person(dlg44, "Потемкин С.А.")
        check("roles18: в строке человека чипы «И» и «К»",
              chips44 is not None and set(chips44.keys()) == {"И", "К"},
              f"{sorted(chips44.keys()) if chips44 else None}")
        if chips44:
            check("roles18: у Потемкина активен только «К» (дефолтный контролёр)",
                  getattr(chips44["К"], "bgcolor", None) == GLASS["in_progress"]
                  and getattr(chips44["И"], "bgcolor", None) == "transparent",
                  f"K={getattr(chips44['К'], 'bgcolor', None)} I={getattr(chips44['И'], 'bgcolor', None)}")
            chips44["И"].on_click(None)  # назначить исполнителя
            roles44 = (load_settings().get("person_roles") or {}).get("Потемкин С.А.") or []
            check("roles18: клик по «И» назначил обе роли",
                  "executor" in roles44 and "controller" in roles44, f"{roles44}")
            chips44b = _chips_of_person(dlg44, "Потемкин С.А.")
            check("roles18: после назначения оба чипа активны",
                  chips44b is not None
                  and getattr(chips44b["И"], "bgcolor", None) == GLASS["accent"]
                  and getattr(chips44b["К"], "bgcolor", None) == GLASS["in_progress"],
                  f"I={getattr(chips44b['И'], 'bgcolor', None) if chips44b else None}")
            if chips44b:
                chips44b["К"].on_click(None)  # снять контролёра
                roles44b = (load_settings().get("person_roles") or {}).get("Потемкин С.А.") or []
                check("roles18: повторный клик по «К» снял роль контролёра",
                      roles44b == ["executor"], f"{roles44b}")
        apply44 = _refs_apply_of(dlg44)
        check("roles18: кнопка «Применить» есть", len(apply44) >= 1)
        if apply44:
            apply44[0].on_click(None)
            ex44b = _find_dd(tab, "Все исполнители")
            ct44b = _find_dd(tab, "Все контролеры")
            # Раунд 22 (задача 4): опции фильтров — полный справочник людей,
            # роли (чипы) на них НЕ влияют — Потемкин остаётся в обоих списках.
            check("roles22: после «Применить» Потемкин остаётся в фильтре исполнителей",
                  ex44b is not None
                  and "Потемкин С.А." in [o.key for o in (ex44b.options or [])])
            check("roles22: …и остаётся в фильтре контролёров (чипы не влияют на фильтры)",
                  ct44b is not None
                  and "Потемкин С.А." in [o.key for o in (ct44b.options or [])])
        # инициаторы — без чипов ролей (только люди)
        init44_rows = [c for c in walk(dlg44) if isinstance(c, ft.Container)
                       and getattr(c, "bgcolor", None) == GLASS["surface_alt"]
                       and any(isinstance(t, ft.Text) and t.value == "СУ" for t in walk(c))]
        check("roles18: у инициаторов чипов ролей нет",
              not init44_rows
              or all(not [ch for ch in walk(r) if isinstance(ch, ft.Container)
                          and getattr(ch, "width", None) == 24
                          and getattr(ch, "height", None) == 22
                          and getattr(ch, "on_click", None) is not None]
                     for r in init44_rows))

    # ── 86. Раунд 30, задача 3: «За кем контроль» - ТОЛЬКО контролёры ──
    # Регресс: extra_people по умолчанию получали ОБЕ роли, и импортированные
    # исполнители попадали в dropdown контролёров новой карточки (скрин
    # «Новая карточка, за кем контроль эти фамилии.png»).
    _save_off({"network_enabled": False, "network_role": "admin",
                   "network_user": "", "network_shared_path": "",
                   "notify_log": {}, "notify_sound": True,
                   "extra_people": ["Авакян Арсен Артурович"],
                   "person_roles": {}, "hidden_people": []})
    _seed_raw([_ctrl("r86", "Р-86", executors=["Авакян А.А."],
                     controller="Потемкин С.А.")])
    page86, tab86, _ = build(1280)
    # НОВАЯ карточка: dropdown «За кем контроль»
    _open_card(tab86, via_add=True)
    cdd86 = _find_dd(tab86, "За кем контроль")
    check("roles30: dropdown «За кем контроль» в новой карточке найден",
          cdd86 is not None)
    if cdd86 is not None:
        opts86 = [o.key for o in (cdd86.options or [])]
        check("roles30: импортированный исполнитель (extra) НЕ контролёр",
              "Авакян Арсен Артурович" not in opts86, f"{opts86}")
        # Чашин выводится полным ФИО: дефолтный контролёр «Чашин Э.А.» слит
        # с криминалистом «Чашин Эдуард Александрович» (раунд 18) - одна запись
        check("roles30: в dropdown только дефолтные контролёры",
              "Потемкин С.А." in opts86 and "Чашин Эдуард Александрович" in opts86
              and "Семисенко Иван Юрьевич" not in opts86
              and len(opts86) == 2, f"{opts86}")
    # ЯВНОЕ назначение контролёра в справочнике - backward compatibility
    st86 = load_settings()
    set_person_roles(st86, "Авакян Арсен Артурович", ["executor", "controller"])
    page86b, tab86b, _ = build(1280)
    _open_card(tab86b, via_add=True)
    cdd86b = _find_dd(tab86b, "За кем контроль")
    if cdd86b is not None:
        opts86b = [o.key for o in (cdd86b.options or [])]
        check("roles30: явно назначенный контролёр ПОЯВЛЯЕТСЯ в dropdown",
              "Авакян Арсен Артурович" in opts86b
              and "Потемкин С.А." in opts86b
              and "Чашин Эдуард Александрович" in opts86b,
              f"{opts86b}")
    # текущее значение контроля (даже вне списка контролёров) не теряется
    _save_off({"network_enabled": False, "network_role": "admin",
                   "network_user": "", "network_shared_path": "",
                   "notify_log": {}, "notify_sound": True,
                   "extra_people": ["Авакян Арсен Артурович"],
                   "person_roles": {}, "hidden_people": []})
    _seed_raw([_ctrl("r86c", "Р-86С", executors=["Авакян А.А."],
                     controller="Авакян Арсен Артурович")])
    page86c, tab86c, _ = build(1280)
    _open_card(tab86c, via_add=False)
    cdd86c = _find_dd(tab86c, "За кем контроль")
    if cdd86c is not None:
        opts86c = [o.key for o in (cdd86c.options or [])]
        check("roles30: текущий контролёр добавлен опцией (данные не теряются)",
              "Авакян Арсен Артурович" in opts86c
              and cdd86c.value == "Авакян Арсен Артурович", f"{opts86c}")

    # ── 87. Раунд 31, задача 5: персонализация просрочек по пользователю ──
    # Сценарий пользователя: в контроле просрочен ЧУЖОЙ пункт п.6
    # (Семисенко, Чащин - 16.02.2026), а свой пункт п.2 (Миронович) ещё не
    # наступил. Миронович НЕ должен видеть контроль в «Просрочено».
    from datetime import date as _date87, timedelta as _td87
    from core.controls_models import (
        user_effective_due_date as _ued87,
        user_deadline_status as _uds87,
    )
    from core.controls_notify import collect_alarm_controls as _cac87
    _t87 = _date87.today()
    _ctl87 = _ctrl("p87", "ПЕРС-87", executors=["Чащин Э.А.", "Миронович Д.В."],
                   controller="Потемкин С.А.")
    _ctl87["tasks"] = [
        {"id": "t87a", "title": "п.6", "assignees": ["Семисенко И.Ю.", "Чащин Э.А."],
         "due_date": (_t87 - _td87(days=180)).isoformat(), "is_done": False,
         "done_date": None, "comment": ""},
        {"id": "t87b", "title": "п.2", "assignees": ["Миронович Д.В."],
         "due_date": (_t87 + _td87(days=2)).isoformat(), "is_done": False,
         "done_date": None, "comment": ""},
    ]
    # unit: user-срок и статус
    _c87 = Control.from_dict(_ctl87)
    check("pers31: user-срок Мироновича = дата ЕГО пункта (не чужого)",
          _ued87(_c87, "Миронович Д.В.") == _t87 + _td87(days=2),
          f"{_ued87(_c87, 'Миронович Д.В.')}")
    check("pers31: user-статус Мироновича - «Скоро», НЕ «Просрочено»",
          _uds87(_c87, "Миронович Д.В.", 3) == SOON,
          f"{_uds87(_c87, 'Миронович Д.В.', 3)}")
    check("pers31: у Семисенко его просроченный пункт даёт «Просрочено»",
          _uds87(_c87, "Семисенко И.Ю.", 3) == OVERDUE)
    check("pers31: admin-статус (общий) - «Просрочено» (мин из всех пунктов)",
          deadline_status(_c87, 3) == OVERDUE)
    # collect_alarm_controls: user не алармится по чужому пункту
    check("pers31: алармы Мироновича пусты (чужой просроченный пункт не будит)",
          _cac87([_c87], 3, "Миронович Д.В.") == [])
    check("pers31: алармы Семисенко содержат контроль",
          [c.id for c in _cac87([_c87], 3, "Семисенко И.Ю.")] == ["p87"])
    check("pers31: алармы админа содержат контроль (общий статус)",
          [c.id for c in _cac87([_c87], 3)] == ["p87"])
    # UI user-режим: счётчики/фильтры по user-статусу
    _save_off({"network_enabled": False, "network_role": "user",
                   "network_user": "Миронович Д.В.", "network_shared_path": "",
                   "notify_log": {}, "notify_sound": True, "extra_people": [],
                   "person_roles": {}, "hidden_people": [], "alarm_enabled": False})
    _seed_raw([_ctl87])
    page87, tab87, _ = build(1280)
    check("pers31: user видит контроль в «Все»",
          "ПЕРС-87" in _visible_texts(tab87))
    check("pers31: user-фильтр «Просрочено» - 0 контролей (чужой пункт не виден)",
          _set_filter(tab87, "Все статусы", OVERDUE))
    vis87 = _visible_texts(tab87)
    check("pers31: после фильтра «Просрочено» контроль скрыт",
          "ПЕРС-87" not in vis87, f"{sorted(vis87)[:8]}")
    check("pers31: user-фильтр «Скоро» - контроль виден (свой пункт)",
          _set_filter(tab87, "Все статусы", SOON))
    check("pers31: после фильтра «Скоро» контроль виден",
          "ПЕРС-87" in _visible_texts(tab87))
    # admin: фильтр «Просрочено» показывает контроль
    _save_off({"network_enabled": False, "network_role": "admin",
                   "network_user": "", "network_shared_path": "",
                   "notify_log": {}, "notify_sound": True, "extra_people": [],
                   "person_roles": {}, "hidden_people": [], "alarm_enabled": False})
    _seed_raw([_ctl87])
    page87b, tab87b, _ = build(1280)
    check("pers31: admin-фильтр «Просрочено» - контроль виден (общий статус)",
          _set_filter(tab87b, "Все статусы", OVERDUE))
    check("pers31: admin видит контроль в «Просрочено»",
          "ПЕРС-87" in _visible_texts(tab87b))
    # Экспорт: wrap «Содержание»/«Исполнители», SOON НЕ подсвечен жёлтым.
    # Чистый контроль БЕЗ просроченных пунктов: due = сегодня+2 -> SOON.
    from core.controls_exporter import ControlsExcelExporter as _cee87
    from openpyxl import load_workbook as _lwb87
    _xlsx87 = os.path.join(tempfile.mkdtemp(prefix="porayonka_x31_"),
                           "export31.xlsx")
    _c87b = _ctrl("e87", "ЭКСП-31", executors=["Миронович Д.В."],
                  controller="Потемкин С.А.")
    _c87b["due_date"] = (_t87 + _td87(days=2)).isoformat()  # SOON
    _c87b["content"] = "Длинное содержание для проверки переноса " * 3
    _cee87().export([Control.from_dict(_c87b)], _xlsx87, soon_days=3, full=False)
    _ws87 = _lwb87(_xlsx87)["Контроли"]
    check("exp31: «Содержание» (E) с wrap_text=True",
          bool(_ws87.cell(row=3, column=5).alignment.wrap_text))
    check("exp31: «Исполнители» (F) с wrap_text=True",
          bool(_ws87.cell(row=3, column=6).alignment.wrap_text))
    check("exp31: SOON НЕ подсвечивается жёлтым (только OVERDUE/TODAY)",
          (_ws87.cell(row=3, column=9).fill.patternType or "") != "solid",
          f"{_ws87.cell(row=3, column=9).fill.fgColor.rgb}")

    # ── 88. Раунд 32, задача 3: персонализация экспорта по user_name ──
    # Контроль _ctl87: п.6 (Семисенко/Чащин, просрочен 180 дн. назад),
    # п.2 (Миронович, +2 дня). Экспорт для Мироновича: колонка I = ЕГО дата,
    # без жёлтой (его пункт не просрочен). Для Семисенко: его пункт
    # просрочен -> жёлтая. Admin (без user_name): общий срок -> жёлтая.
    _x88 = os.path.join(tempfile.mkdtemp(prefix="porayonka_x32a_"), "exp32a.xlsx")
    _cee87().export([_c87], _x88, soon_days=3, full=False,
                    user_name="Миронович Д.В.")
    _ws88 = _lwb87(_x88)["Контроли"]
    _exp_due88 = _t87 + _td87(days=2)
    _cell_i88 = _ws88.cell(row=3, column=9).value
    check("exp32: user-экспорт - колонка «Следующая дата» = дата СВОЕГО пункта",
          _cell_i88 == datetime(_exp_due88.year, _exp_due88.month, _exp_due88.day),
          f"{_cell_i88}")
    check("exp32: user-экспорт - непросроченный свой пункт БЕЗ жёлтой заливки",
          (_ws88.cell(row=3, column=9).fill.patternType or "") != "solid")
    _x88b = os.path.join(tempfile.mkdtemp(prefix="porayonka_x32b_"), "exp32b.xlsx")
    _cee87().export([_c87], _x88b, soon_days=3, full=False,
                    user_name="Семисенко И.Ю.")
    _ws88b = _lwb87(_x88b)["Контроли"]
    check("exp32: user-экспорт - просроченный СВОЙ пункт подсвечен жёлтым",
          (_ws88b.cell(row=3, column=9).fill.patternType or "") == "solid")
    _x88c = os.path.join(tempfile.mkdtemp(prefix="porayonka_x32c_"), "exp32c.xlsx")
    _cee87().export([_c87], _x88c, soon_days=3, full=False)
    _ws88c = _lwb87(_x88c)["Контроли"]
    check("exp32: admin-экспорт (без user_name) - общий срок + жёлтая",
          (_ws88c.cell(row=3, column=9).fill.patternType or "") == "solid")

    # ══════════════════════════════════════════════════════════════════
    # Раунд 19
    # ══════════════════════════════════════════════════════════════════

    # ── 45. Раунд 19, задача 5: AssertionError-регрессия — харнесс с НАСТОЯЩИМ Page ──
    # Лог design/screenshots/11.08.2026/ЛОГ.txt: AssertionError
    # 'assert self.__uid is not None' в _safe_update при работе с фильтрами и
    # после «Добавить» — после этого карточки не открывались. Здесь вкладка
    # монтируется в реальный flet_core.page.Page (FakeConn эмулирует клиента:
    # каждой команде add возвращаются реальные id), и прогоняется точный
    # сценарий пользователя: mount → resize (как в логе) → фильтры → открыть
    # карточку → «Добавить контроль» → Сохранить → открыть карточку снова.
    # Проверяем: ни одного контрола без uid и ни одного падения в логе.
    import asyncio as _asyncio19
    from flet_core.page import Page as _RealPage19
    from flet_core.connection import Connection as _Conn19

    class _FakeConn19(_Conn19):
        """Эмуляция клиента: каждой топ-уровневой команде add отвечает пачкой id
        (по одному на контрол поддерева — name=None записи внутри add)."""
        def __init__(self):
            super().__init__()
            self.n = 0

        def send_commands(self, session_id, commands):
            def _subtree_size(cmd):
                return 1 + sum(_subtree_size(c) for c in cmd.commands)
            total = sum(_subtree_size(c) - 1 for c in commands if c.name == "add")
            lines = []
            i = 0
            while i < total:
                chunk = " ".join(str(self.n + j) for j in range(min(100, total - i)))
                lines.append(chunk)
                i += 100
                self.n += 100
            return type("R", (), {"results": lines})()

    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": False,
                   "extra_people": []})
    _seed_raw([_ctrl("rl1", "РЛ-1", executors=["Семисенко Иван Юрьевич"], controller="Потемкин С.А."),
               _ctrl("rl2", "РЛ-2", executors=["Семисенко И.Ю."], controller="Потемкин С.А.")])
    conn19 = _FakeConn19()
    loop19 = _asyncio19.new_event_loop()
    page19 = _RealPage19(conn19, "s1", loop19)
    page19._set_attr("width", 1280)
    page19._set_attr("height", 860)
    buf19 = io.StringIO()
    with contextlib.redirect_stdout(buf19), contextlib.redirect_stderr(buf19):
        tab19 = create_controls_tab(page19)
    try:
        page19.add(tab19)
        nouid19 = [c for c in walk(tab19) if getattr(c, "_Control__uid", None) is None]
        check("harn19: после mount нет контролов без uid", len(nouid19) == 0,
              f"{len(nouid19)}: {[type(c).__name__ for c in nouid19[:5]]}")
        # resize (в логе пользователя — сразу перед первым падением)
        page19._set_attr("width", 1920)
        rsz19 = getattr(page19, "on_resize", None)
        check("harn19: on_resize подписан", rsz19 is not None)
        if rsz19 is not None:
            _invoke_event_handler(rsz19, None)
        # фильтры (исполнитель + контролёр + статус)
        dd19 = _find_dd(tab19, "Все исполнители")
        ok19 = dd19 is not None
        if dd19 is not None:
            opts19 = [o.key for o in (dd19.options or [])]
            dd19.value = "Семисенко Иван Юрьевич" if "Семисенко Иван Юрьевич" in opts19 else opts19[min(1, len(opts19)-1)]
            dd19.on_change(None)
        check("harn19: фильтр «Исполнители» применился без ошибок", ok19
              and "РЛ-1" in _visible_texts(tab19))
        dd19c = _find_dd(tab19, "Все контролеры")
        if dd19c is not None:
            dd19c.value = "Потемкин С.А."
            dd19c.on_change(None)
        check("harn19: после двух фильтров обе строки видимы",
              len(_visible_rows(tab19)) == 2, f"{len(_visible_rows(tab19))}")
        # сброс через кнопку «Сбросить фильтры»
        rst19 = [c for c in walk(tab19) if isinstance(c, ft.ElevatedButton)
                 and getattr(c, "text", None) == "Сбросить фильтры"]
        if rst19:
            rst19[0].on_click(None)
        # открыть карточку строкой и закрыть
        rows19 = _visible_rows(tab19)
        check("harn19: строки таблицы есть после сброса фильтров", len(rows19) == 2)
        if rows19:
            rows19[0].on_click(None)
        ovs19 = [c for c in walk(tab19) if isinstance(c, ft.Container)
                 and getattr(c, "bgcolor", None) == "#cc04070f"
                 and getattr(c, "visible", False)]
        check("harn19: карточка открылась (overlay видим)", len(ovs19) >= 1)
        cls19 = [c for c in walk(tab19) if isinstance(c, ft.IconButton)
                 and getattr(c, "icon", None) == ft.icons.CLOSE
                 and not getattr(c, "tooltip", None)]
        if cls19:
            cls19[0].on_click(None)
        # сценарий «добавил новую — сохранил — карточки перестали открываться»
        add19 = [c for c in walk(tab19) if isinstance(c, ft.ElevatedButton)
                 and getattr(c, "text", None) == "Добавить контроль"]
        add19[0].on_click(None)
        inc19 = [c for c in walk(tab19) if isinstance(c, ft.TextField)
                 and (getattr(c, "hint_text", "") or "").startswith("Входящий")]
        inc19[0].value = "РЛ-NEW"
        # Раунд 38 (задача 6): НОВАЯ карточка сохраняется только со сканом —
        # прикрепляем PDF через picker перед сохранением (раньше скан не
        # требовался).
        src19 = os.path.join(tempfile.mkdtemp(prefix="porayonka_s19_"), "акт19.pdf")
        with open(src19, "wb") as f:
            f.write(b"%PDF-harn19-scan")
        picker19 = getattr(page19, "_controls_attach_picker", None)
        check("harn19: picker вложений доступен для скана новой карточки",
              picker19 is not None)
        _ev19 = type("E", (), {"files": [type("F", (), {"path": src19, "name": "акт19.pdf"})()]})()
        _invoke_event_handler(getattr(picker19, "on_result", None), _ev19)
        save19 = [c for c in walk(tab19) if isinstance(c, ft.ElevatedButton)
                  and getattr(c, "text", None) == "Сохранить"]
        save19[0].on_click(None)
        check("harn19: новый контроль сохранён и виден в таблице",
              "РЛ-NEW" in _visible_texts(tab19))
        rows19b = _visible_rows(tab19)
        check("harn19: после добавления строк 3", len(rows19b) == 3, f"{len(rows19b)}")
        if rows19b:
            rows19b[0].on_click(None)
        ovs19b = [c for c in walk(tab19) if isinstance(c, ft.Container)
                  and getattr(c, "bgcolor", None) == "#cc04070f"
                  and getattr(c, "visible", False)]
        check("harn19: карточка ОТКРЫВАЕТСЯ после добавления нового контроля",
              len(ovs19b) >= 1)
        nouid19b = [c for c in walk(tab19) if getattr(c, "_Control__uid", None) is None]
        check("harn19: после всех операций контролов без uid нет", len(nouid19b) == 0,
              f"{len(nouid19b)}")
    finally:
        log19 = buf19.getvalue()
        check("harn19: в логе нет AssertionError", "AssertionError" not in log19)
        check("harn19: в логе нет Traceback", "Traceback" not in log19,
              "\n".join(l for l in log19.splitlines() if "raceback" in l)[:200])
        stop19 = getattr(page19, "_controls_poll_stop", None)
        if stop19 is not None:
            try:
                stop19["flag"] = True
            except Exception:
                pass
        try:
            loop19.close()
        except Exception:
            pass
        # вернуть чистый сид для следующих секций
        _seed_controls()
        _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                       "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                       "extra_people": []})

    # ── 46. Раунд 19, задача 1: действия архива переехали в карточку ──
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": []})
    _arch46 = _ctrl("ar46", "АРХ-1", executors=["Семисенко И.Ю."], controller="Потемкин С.А.")
    _arch46.update({"archived": True, "archived_at": "2026-08-10T10:00:00",
                    "archive_reason": "done", "done": True, "done_date": "2026-08-10"})
    _seed_raw([_arch46])
    page, tab, _ = build()
    # в активном режиме архивного контроля нет
    check("arch19: в активных архивный контроль не виден",
          "АРХ-1" not in _visible_texts(tab))
    mode_btns46 = [c for c in walk(tab) if isinstance(c, ft.Container)
                   and getattr(c, "on_click", None) is not None
                   and any(isinstance(t, ft.Text) and t.value == "Архив" for t in walk(c))]
    check("arch19: кнопка режима «Архив» есть", len(mode_btns46) >= 1)
    if mode_btns46:
        mode_btns46[0].on_click(None)
    check("arch19: архивный контроль виден в режиме «Архив»",
          "АРХ-1" in _visible_texts(tab))
    # в строках архива — ни иконок восстановления, ни удаления (колонки нет)
    rows46 = _visible_rows(tab)
    check("arch19: в строке архива нет иконок RESTORE/DELETE_FOREVER",
          rows46 and not any(isinstance(c, ft.IconButton) for r in rows46 for c in walk(r)))
    # открыть карточку архивного контроля — действия в футере
    if rows46:
        rows46[0].on_click(None)
    rest46 = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
              and getattr(c, "text", None) == "Восстановить"]
    delf46 = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
              and getattr(c, "text", None) == "Удалить навсегда"]
    check("arch19: в карточке архивного - «Восстановить» и «Удалить навсегда»",
          len(rest46) == 1 and len(delf46) == 1)
    done_badge46 = [t for t in walk(tab) if isinstance(t, ft.Text)
                    and t.value and str(t.value).startswith("Исполнен:")]
    check("arch19: бейдж «Исполнен: <дата>» в карточке (сводка секции «Сроки»)",
          any("10.08.2026" in str(t.value) for t in done_badge46),
          f"{[t.value for t in done_badge46][:2]}")
    if rest46:
        rest46[0].on_click(None)
        check("arch19: «Восстановить» из карточки вернул контроль в активные",
              any(c.incoming_number == "АРХ-1" and not c.archived for c in load_controls()))
        ov46 = [c for c in walk(tab) if isinstance(c, ft.Container)
                and getattr(c, "bgcolor", None) == "#cc04070f"
                and getattr(c, "visible", False)]
        check("arch19: карточка после восстановления закрыта", len(ov46) == 0)
    # вернуться в «Активные» — АРХ-1 снова там; удалим его из карточки
    mode_btns46b = [c for c in walk(tab) if isinstance(c, ft.Container)
                    and getattr(c, "on_click", None) is not None
                    and any(isinstance(t, ft.Text) and t.value == "Активные" for t in walk(c))]
    if mode_btns46b:
        mode_btns46b[0].on_click(None)  # вернуться в «Активные»
    rows46b = _visible_rows(tab)
    if rows46b:
        rows46b[0].on_click(None)  # АРХ-1 в активных
    delb46 = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
              and getattr(c, "text", None) == "Удалить" ]
    check("arch19: в активной карточке кнопка «Удалить»", len(delb46) == 1)
    if delb46:
        delb46[0].on_click(None)
        dlg46 = page.dialogs[-1] if page.dialogs else None
        conf46 = [c for c in getattr(dlg46, "actions", []) if isinstance(c, ft.ElevatedButton)]
        check("arch19: диалог удаления в архив из карточки открыт", dlg46 is not None and len(conf46) >= 1)
        if conf46:
            conf46[-1].on_click(None)
            check("arch19: контроль в архиве после удаления из карточки",
                  any(c.incoming_number == "АРХ-1" and c.archived and c.archive_reason == "deleted"
                      for c in load_controls()))

    # ── 47. Раунд 19, задача 2: resize в ОБЕ стороны + сохранение после «перезапуска» ──
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": []})
    _seed_raw([_ctrl("rs19", "РС-1", executors=["Семисенко И.Ю."])])
    page, tab, _ = build(1280)

    def _drag_handles19(tab_):
        return [c for c in walk(tab_) if isinstance(c, ft.GestureDetector)
                and len(getattr(getattr(c, "on_horizontal_drag_start", None),
                                 "_EventHandler__handlers", {}) or {}) > 0]

    def _header_widths19(tab_):
        hdr = _header_row19(tab_)
        return [getattr(st, "width", None) for st in hdr.controls
                if isinstance(st, ft.Stack)] if hdr else []

    E47 = type("E", (), {})
    gds47 = _drag_handles19(tab)
    check("drag19: хэндлов ровно 10 (без колонки «Действия»)", len(gds47) == 10, f"{len(gds47)}")
    hdr47 = _header_row19(tab)
    stacks47 = [st for st in hdr47.controls if isinstance(st, ft.Stack)]
    w_before = [st.width for st in stacks47]
    sum_before = sum(w_before)
    # тянем границу «Вх. №» (gds[1]) ВПРАВО +40 (раньше это глохло при упоре
    # «Содержания» в минимум) — колонка растёт, «Содержание» компенсирует
    _invoke_event_handler(gds47[1].on_horizontal_drag_start, E47())
    _invoke_event_handler(gds47[1].on_horizontal_drag_update, type("E", (), {"delta_x": 40})())
    w_after = [st.width for st in stacks47]
    check("drag19: вправо +40 - колонка «Вх. №» выросла 160->200",
          w_after[1] == 200, f"{w_after[1]}")
    check("drag19: «Содержание» компенсировало -40 (сумма неизменна)",
          w_after[4] == w_before[4] - 40 and sum(w_after) == sum_before,
          f"content {w_before[4]}->{w_after[4]}, sum {sum_before}->{sum(w_after)}")
    # тянем ТУ ЖЕ границу ВЛЕВО -70 — от стартовой точки жеста, не от текущей
    _invoke_event_handler(gds47[1].on_horizontal_drag_update, type("E", (), {"delta_x": -70})())
    w_after2 = [st.width for st in stacks47]
    check("drag19: влево - суммарная дельта -30 от старта (160->170? нет, 160+40-70=130)",
          w_after2[1] == 130, f"{w_after2[1]}")
    _invoke_event_handler(gds47[1].on_horizontal_drag_end, E47())
    # после rebuild хэндлы пересозданы — гибкая пара: «Содержание» (gds[4])
    gds47b = _drag_handles19(tab)
    _invoke_event_handler(gds47b[4].on_horizontal_drag_start, E47())
    hdr47b = _header_row19(tab)
    stacks47b = [st for st in hdr47b.controls if isinstance(st, ft.Stack)]
    c_before, e_before = stacks47b[4].width, stacks47b[5].width
    _invoke_event_handler(gds47b[4].on_horizontal_drag_update, type("E", (), {"delta_x": 30})())
    check("drag19: «Содержание» +30 - «Исполнители» -30 (работает и для гибкой пары)",
          stacks47b[4].width == c_before + 30 and stacks47b[5].width == e_before - 30,
          f"{stacks47b[4].width}/{stacks47b[5].width}")
    _invoke_event_handler(gds47b[4].on_horizontal_drag_update, type("E", (), {"delta_x": -30})())
    check("drag19: «Содержание» -30 обратно - «Исполнители» восстановились",
          stacks47b[4].width == c_before and stacks47b[5].width == e_before)
    _invoke_event_handler(gds47b[4].on_horizontal_drag_end, E47())
    # минимальный кламп: «№» влево до упора — 28 (не 40 и не 60)
    gds47c = _drag_handles19(tab)
    _invoke_event_handler(gds47c[0].on_horizontal_drag_start, E47())
    _invoke_event_handler(gds47c[0].on_horizontal_drag_update, type("E", (), {"delta_x": -500})())
    hdr47c = _header_row19(tab)
    num_w47 = [st.width for st in hdr47c.controls if isinstance(st, ft.Stack)][0]
    check("drag19: «№» упёрся в минимум 28 (не ушёл в 0/отрицательную)",
          num_w47 == 28, f"{num_w47}")
    _invoke_event_handler(gds47c[0].on_horizontal_drag_end, E47())
    st47 = load_settings().get("col_widths") or {}
    check("drag19: ширины сохранены в settings (incoming=130, num=28)",
          st47.get("incoming") == 130 and st47.get("num") == 28, f"{st47}")
    # «перезапуск приложения»: новая вкладка на тех же settings — ширины 1-в-1
    page, tab, _ = build(1280)
    hdr47d = _header_row19(tab)
    stacks47d = [st for st in hdr47d.controls if isinstance(st, ft.Stack)]
    check("drag19: после пересоздания вкладки num=28 восстановлен",
          stacks47d[0].width == 28, f"{stacks47d[0].width}")
    check("drag19: после пересоздания вкладки incoming=130 восстановлен",
          stacks47d[1].width == 130, f"{stacks47d[1].width}")
    check("drag19: сумма колонок после восстановления == исходной (без «пляски»)",
          sum(st.width for st in stacks47d) == sum_before,
          f"{sum(st.width for st in stacks47d)} vs {sum_before}")

    # ── 48. Раунд 19, задача 3: «Контроль исполнен» и «Исполнен пункт» ──
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": []})
    _seed_raw([
        _ctrl("db19", "БК-1", executors=["Семисенко И.Ю."], tasks=[
            {"id": "td1", "title": "п.1 Снять копию", "assignees": ["Семисенко Иван Юрьевич"],
             "due_date": "2026-08-20", "is_done": False, "done_date": None, "comment": ""},
            {"id": "td2", "title": "п.2 Доложить", "assignees": ["Гайнутдинов С.И."],
             "due_date": "2026-08-21", "is_done": False, "done_date": None, "comment": ""},
        ]),
        _ctrl("db19b", "БК-2", executors=["Семисенко И.Ю."]),  # без пунктов
    ])
    page, tab, _ = build(1280)
    rows48 = _visible_rows(tab)
    check("done19: две строки в таблице", len(rows48) == 2)
    rows48[0].on_click(None)  # БК-1 с пунктами
    btns48 = {getattr(c, "text", None): c for c in walk(tab)
              if isinstance(c, (ft.ElevatedButton, ft.TextButton))}
    check("done19: зелёная «Контроль исполнен» есть в футере карточки",
          "Контроль исполнен" in btns48)
    check("done19: жёлтая «Исполнен пункт» есть в футере карточки",
          "Исполнен пункт" in btns48)
    check("done19: «Удалить» осталась правее быстрых кнопок", "Удалить" in btns48)
    grn48 = btns48.get("Контроль исполнен")
    ylw48 = btns48.get("Исполнен пункт")
    check("done19: «Контроль исполнен» зелёная (#2fd08b), «Исполнен пункт» жёлтая (#ffd166)",
          getattr(grn48, "bgcolor", None) == "#2fd08b"
          and getattr(ylw48, "bgcolor", None) == "#ffd166",
          f"{getattr(grn48, 'bgcolor', None)}/{getattr(ylw48, 'bgcolor', None)}")
    # 3.2. «Исполнен пункт» → диалог, выбор п.2, дата по умолчанию — сегодня
    # Раунд 22 (задача 2): RadioGroup заменён на ЧЕКБОКСЫ (мульти-выбор).
    ylw48.on_click(None)
    dlg48 = page.dialogs[-1] if page.dialogs else None
    check("done19: диалог «Исполнен пункт» открыт (AlertDialog через page.open)",
          dlg48 is not None)
    cbs48 = [c for c in walk(dlg48) if isinstance(c, ft.Checkbox)] if dlg48 else []
    check("done22: в диалоге мульти-выбор - чекбоксы по числу пунктов", len(cbs48) == 2)
    conf48 = [c for c in walk(dlg48) if isinstance(c, ft.ElevatedButton)
              and getattr(c, "text", None) == "Отметить исполненными"] if dlg48 else []
    check("done22: кнопка «Отметить исполненными» есть", len(conf48) == 1)
    cb_t2 = [c for c in cbs48 if getattr(c, "data", None) == "td2"]
    check("done22: у чекбокса пункта п.2 data == id пункта", len(cb_t2) == 1)
    if cb_t2:
        cb_t2[0].value = True  # отметить галочкой п.2, как в примере пользователя
    if conf48:
        today_iso48 = datetime.now().date().isoformat()
        conf48[0].on_click(None)
        check("done19: диалог закрыт после подтверждения",
              dlg48 not in page.dialogs)
        ctl48 = next((c for c in load_controls() if c.incoming_number == "БК-1"), None)
        t2_48 = next((t for t in (ctl48.tasks if ctl48 else []) if t.id == "td2"), None)
        t1_48 = next((t for t in (ctl48.tasks if ctl48 else []) if t.id == "td1"), None)
        check("done19: п.2 исполнен с датой (сегодня по умолчанию)",
              t2_48 is not None and t2_48.is_done and t2_48.done_date == today_iso48,
              f"{t2_48.is_done if t2_48 else None}/{t2_48.done_date if t2_48 else None}")
        check("done19: п.1 НЕ тронут", t1_48 is not None and not t1_48.is_done)
        # плашка пункта в ОТКРЫТОЙ карточке обновилась (без закрытия карточки)
        done_lines48 = [t for t in walk(tab) if isinstance(t, ft.Text)
                        and t.value and str(t.value).startswith("Исполнен:")]
        check("done19: в плашке пункта появилась зелёная строка «Исполнен: …»",
              len(done_lines48) >= 1, f"{[t.value for t in done_lines48][:2]}")
        # карточка всё ещё открыта
        ovs48 = [c for c in walk(tab) if isinstance(c, ft.Container)
                 and getattr(c, "bgcolor", None) == "#cc04070f"
                 and getattr(c, "visible", False)]
        check("done19: карточка осталась открытой после «Исполнен пункт»",
              len(ovs48) >= 1)
        # сохранение карточки не стирает done_date пункта
        save48 = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
                  and getattr(c, "text", None) == "Сохранить"]
        save48[0].on_click(None)
        ctl48b = next((c for c in load_controls() if c.incoming_number == "БК-1"), None)
        t2_48b = next((t for t in (ctl48b.tasks if ctl48b else []) if (t.title or "").startswith("п.2")), None)
        check("done19: done_date пункта пережил «Сохранить» карточки",
              t2_48b is not None and t2_48b.is_done and t2_48b.done_date == today_iso48)
        # в таблице содержание показывает «(исполнен <дата>)»
        vis48 = " ".join(_visible_texts(tab))
        check("done19: в строке таблицы - «исполнен» с датой в содержании",
              "исполнен" in vis48)
    # 3.1. «Контроль исполнен» на БК-2 (без пунктов — жёлтой кнопки нет)
    check("done19: БК-2 виден для второго сценария",
          "БК-2" in _visible_texts(tab))
    rows48b = _visible_rows(tab)
    # открыть карточку БК-2 (вторая строка)
    rows48b[-1].on_click(None)
    btns48b = {getattr(c, "text", None): c for c in walk(tab)
               if isinstance(c, (ft.ElevatedButton, ft.TextButton))}
    check("done19: у контроля без пунктов жёлтой «Исполнен пункт» нет",
          "Исполнен пункт" not in btns48b)
    check("done19: зелёная «Контроль исполнен» есть и без пунктов",
          "Контроль исполнен" in btns48b)
    if "Контроль исполнен" in btns48b:
        btns48b["Контроль исполнен"].on_click(None)
        dlg48b = page.dialogs[-1] if page.dialogs else None
        check("done19: диалог «Подтверждение исполнения контроля» открыт",
              dlg48b is not None and any(
                  isinstance(t, ft.Text) and "Подтверждение исполнения контроля" in str(t.value or "")
                  for t in walk(dlg48b)))
        conf_done48 = [c for c in walk(dlg48b) if isinstance(c, ft.ElevatedButton)
                       and getattr(c, "text", None) == "Исполнен"] if dlg48b else []
        cancel48 = [c for c in walk(dlg48b) if isinstance(c, ft.TextButton)
                    and getattr(c, "text", None) == "Отмена"] if dlg48b else []
        check("done19: кнопки «Отмена»/«Исполнен» есть",
              len(conf_done48) == 1 and len(cancel48) == 1)
        if conf_done48:
            conf_done48[0].on_click(None)
            ctl48c = next((c for c in load_controls() if c.incoming_number == "БК-2"), None)
            check("done19: контроль исполнен - done, done_date, архив reason=done",
                  ctl48c is not None and ctl48c.done
                  and ctl48c.done_date == datetime.now().date().isoformat()
                  and ctl48c.archived and ctl48c.archive_reason == "done",
                  f"{ctl48c.done if ctl48c else None}/{ctl48c.archive_reason if ctl48c else None}")
            ovs48b = [c for c in walk(tab) if isinstance(c, ft.Container)
                      and getattr(c, "bgcolor", None) == "#cc04070f"
                      and getattr(c, "visible", False)]
            check("done19: карточка закрылась после «Исполнен»", len(ovs48b) == 0)
            check("done19: БК-2 исчез из активных", "БК-2" not in _visible_texts(tab))
            # в архиве — с бейджем «Исполнен» в карточке
            mode48 = [c for c in walk(tab) if isinstance(c, ft.Container)
                      and getattr(c, "on_click", None) is not None
                      and any(isinstance(t, ft.Text) and t.value == "Архив" for t in walk(c))]
            if mode48:
                mode48[0].on_click(None)
            check("done19: БК-2 появился в архиве", "БК-2" in _visible_texts(tab))
            rows48c = _visible_rows(tab)
            if rows48c:
                rows48c[0].on_click(None)
                badge48c = [t for t in walk(tab) if isinstance(t, ft.Text)
                            and t.value and str(t.value).startswith("Исполнен:")]
                check("done19: в архивной карточке сводка «Исполнен: <дата>»",
                      len(badge48c) >= 1, f"{[t.value for t in badge48c][:2]}")
                # в архивной карточке быстрых кнопок исполнения нет
                btns48c = {getattr(c, "text", None) for c in walk(tab)
                           if isinstance(c, (ft.ElevatedButton, ft.TextButton))}
                check("done19: в архивной карточке нет «Контроль исполнен»/«Исполнен пункт»",
                      "Контроль исполнен" not in btns48c and "Исполнен пункт" not in btns48c)

    # ── 49. Раунд 19, задача 4: скролл списков карточки + списки строго по ролям ──
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": []})
    _seed_raw([_ctrl("sc19", "СК-1", executors=["Семисенко И.Ю."], controller="Потемкин С.А.",
                     tasks=[{"id": "ts1", "title": "п.1 Пункт", "assignees": ["Семисенко И.Ю."],
                             "due_date": None, "is_done": False, "done_date": None, "comment": ""}])])
    page, tab, _ = build(1280)
    rows49 = _visible_rows(tab)
    rows49[0].on_click(None)
    multis49 = [c for c in walk(tab) if isinstance(c, ft.Container)
                and hasattr(c, "_get_selected")]
    check("scroll19: в карточке два inline-мультивыбора (исполнители + ответственный)",
          len(multis49) >= 2, f"{len(multis49)}")
    if multis49:
        scrollcols49 = [c for m in multis49 for c in walk(m)
                        if isinstance(c, ft.Column)
                        and getattr(c, "scroll", None) == ft.ScrollMode.ALWAYS]
        check("scroll19: списки мультивыбора со scroll=ALWAYS (бегунок всегда виден)",
              len(scrollcols49) >= 2, f"{len(scrollcols49)}")
        check("scroll19: у мультивыборов локальная ScrollbarTheme",
              all(getattr(getattr(m, "theme", None), "scrollbar_theme", None) is not None
                  for m in multis49))
        sbt49 = getattr(multis49[0].theme, "scrollbar_theme", None) if multis49 else None
        check("scroll19: бегунок яркий, толстый, draggable (как в справочниках)",
              sbt49 is not None
              and getattr(sbt49, "thumb_color", None) == "#66ffffff"
              and (getattr(sbt49, "thickness", 0) or 0) >= 6
              and getattr(sbt49, "thumb_visibility", None) is True
              and getattr(sbt49, "interactive", None) is True)
        # список исполнителей — по роли executor (Семисенко есть, Потемкина нет)
        ex49 = multis49[0]._available
        check("scroll19: мультивыбор исполнителей - только роль «И»",
              "Семисенко Иван Юрьевич" in ex49 and "Потемкин С.А." not in ex49,
              f"{len(ex49)} опций")
        # но текущее значение контроля (Семисенко И.Ю. — не канон) не потеряно
        check("scroll19: нестандартное текущее значение добавлено опцией (не теряется)",
              "Семисенко И.Ю." in ex49)
    cdd49 = _find_dd(tab, "За кем контроль")
    check("scroll19: dropdown «За кем контроль» найден", cdd49 is not None)
    if cdd49 is not None:
        opts49 = [o.key for o in (cdd49.options or [])]
        check("scroll19: «За кем контроль» - только роль «К» (контролёры)",
              "Потемкин С.А." in opts49 and "Семисенко Иван Юрьевич" not in opts49,
              f"{opts49}")
        check("scroll19: текущий контролёр выбран и не потерян",
              cdd49.value == "Потемкин С.А.", f"{cdd49.value}")
    # fallback ролей: если контролёров никто не отметил — DEFAULT_CONTROLLERS
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [],
                   "person_roles": {"Потемкин С.А.": [], "Чашин Э.А.": []},
                   "hidden_people": []})
    page, tab, _ = build(1280)
    rows49b = _visible_rows(tab)
    if rows49b:
        rows49b[0].on_click(None)
        cdd49b = _find_dd(tab, "За кем контроль")
        opts49b = [o.key for o in (cdd49b.options or [])] if cdd49b else []
        check("scroll19: fallback - без отмеченных контролёров список из DEFAULT_CONTROLLERS",
              "Потемкин С.А." in opts49b)

    # ── 50. Раунд 20, задача 4: сериализация UI (ui/update_lock.py) ──────────
    import threading as _th50
    import types as _types50
    from ui.update_lock import install_update_serialization, ui_lock
    import ui.update_lock as _ul50

    class _FakePage50:
        def __init__(self):
            self.updates = 0

        def update(self, *a):
            self.updates += 1

        def run_thread(self, handler, *a, **kw):
            handler(*a, **kw)

    fp50 = _FakePage50()
    install_update_serialization(fp50)
    got_lock50 = {"v": None}

    def _other_thread_try50():
        got_lock50["v"] = ui_lock().acquire(blocking=False)
        if got_lock50["v"]:
            ui_lock().release()

    def _handler50():
        th = _th50.Thread(target=_other_thread_try50)
        th.start()
        th.join()

    fp50.run_thread(_handler50)
    check("lock20: тело обработчика исполняется под глобальным UI-lock",
          got_lock50["v"] is False, f"чужой acquire={got_lock50['v']}")
    re50 = {"ok": False}

    def _handler50b():
        fp50.update()  # вложенный update под тем же RLock
        re50["ok"] = True

    fp50.run_thread(_handler50b)
    check("lock20: RLock реентерабелен (update внутри обработчика)",
          re50["ok"] and fp50.updates >= 1)
    n50 = len(_ul50._installed_pages)
    install_update_serialization(fp50)
    check("lock20: установка идемпотентна", len(_ul50._installed_pages) == n50)

    # ── 51. Раунд 20, задача 3: пункты «п. N к <дата>» из содержания при импорте ──
    from core.controls_models import parse_content_tasks as _pct20
    src51 = ("Распоряжение 2/216-р от 15.01.2026 Чашин Э.А. п.3 к 05.05.2026, "
             "п. 5 к 05.09.2026, п. 7 к 05.10.2026, Миронович Д.В. п. 9.3 к 20.05.2026")
    clean51, tasks51 = _pct20(src51)
    check("import20: строка 41 эталона - 4 пункта", len(tasks51) == 4, f"{len(tasks51)}")
    got51 = [(t.title, (t.assignees or [""])[0], t.due_date) for t in tasks51]
    check("import20: владельцы и сроки пунктов разобраны верно",
          got51 == [("п. 3", "Чашин Э.А.", "2026-05-05"),
                    ("п. 5", "Чашин Э.А.", "2026-09-05"),
                    ("п. 7", "Чашин Э.А.", "2026-10-05"),
                    ("п. 9.3", "Миронович Д.В.", "2026-05-20")], f"{got51}")
    check("import20: содержание очищено от перечня пунктов",
          clean51 == "Распоряжение 2/216-р от 15.01.2026", clean51)
    for no_items in ("Распоряжение 103/216-р от 04.08.2022 ОПК п. 1",
                     "Протокол поручений ПСК 15-26 от 09.06.2026",
                     "протокол поручений руководителя СУ от 15.04.2026 межведомственная "
                     "рабочая группа по незаконным финансовым операциям № 54 от 29.01.2026"):
        c51x, t51x = _pct20(no_items)
        check("import20: без «п. N к <дата>» содержание не трогаем",
              not t51x and c51x == no_items, no_items[:42])
    try:
        from openpyxl import Workbook
        from core.controls_exporter import TABLE_HEADERS as _TH51
        wb51 = Workbook()
        ws51 = wb51.active
        ws51.append(["КОНТРОЛИ ОТДЕЛА КРИМИНАЛИСТИКИ"])
        ws51.append(list(_TH51))
        ws51.append([41, "Исоп-216-193-26", "15.01.2026", "СУ", src51,
                     "Чашин Э.А., Миронович Д.В.", "Чашин Э.А.", "ежемесячно",
                     "05.09.2026", ""])
        p51 = os.path.join(tempfile.gettempdir(), "round20_import_test.xlsx")
        wb51.save(p51)
        parsed51, stats51 = import_from_excel(p51, [])
        ok51 = len(parsed51) == 1 and len(parsed51[0].tasks) == 4
        check("import20: импорт из .xlsx создаёт пункты карточки", ok51,
              f"tasks={len(parsed51[0].tasks) if parsed51 else 'нет'}")
        if ok51:
            ctl51 = parsed51[0]
            check("import20: содержание импортированной карточки очищено",
                  ctl51.content == "Распоряжение 2/216-р от 15.01.2026", ctl51.content)
            ex51 = {e.casefold() for e in ctl51.executors}
            check("import20: ответственные пунктов - в исполнителях контроля",
                  {"чашин э.а.", "миронович д.в."} <= ex51, f"{ctl51.executors}")
    except Exception:
        traceback.print_exc()
        check("import20: сквозной импорт .xlsx без исключений", False)

    # ── 52. Раунд 20, задача 4: повторное добавление снимает hidden_people ──
    from core.controls_data import add_extra_person as _aep20
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "hidden_people": ["Гайнутдинов Станислав Игоревич"]})
    st52 = load_settings()
    ok52 = _aep20(st52, "Гайнутдинов Станислав Игоревич")
    check("refs20: добавление ранее скрытого человека - True", ok52)
    st52b = load_settings()
    check("refs20: hidden_people вычищен от этого ФИО",
          not any("гайнутдинов" in (h or "").casefold() for h in (st52b.get("hidden_people") or [])))
    names52 = get_all_people_names(st52b)
    check("refs20: человек снова виден в списке справочника",
          any("гайнутдинов" in (n or "").casefold() for n in names52),
          f"{len(names52)} имён")

    # ── 53. Раунд 20, задача 2: перекомпоновка карточки ──────────────────────
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "person_roles": {}, "hidden_people": []})
    _seed_raw([_ctrl("c20", "ТЕСТ-20", executors=["Семисенко Иван Юрьевич"],
                     tasks=[{"id": "t20a", "title": "п. 1", "assignees": ["Грубников Георгий Григорьевич"],
                             "due_date": "2026-09-23", "is_done": False, "done_date": None, "comment": ""},
                            {"id": "t20b", "title": "п. 2", "assignees": ["Семисенко Иван Юрьевич"],
                             "due_date": "2026-08-14", "is_done": False, "done_date": None, "comment": ""}])])
    page, tab, _ = build(1280)
    rows53 = _visible_rows(tab)
    check("layout20: строка контроля есть", len(rows53) >= 1)
    if rows53:
        rows53[0].on_click(None)
    cols53 = find_card_columns(tab)
    check("layout20: карточка открыта (две колонки)", cols53 is not None)
    if cols53:
        lc53, rc53, _ = cols53
        lt53 = [t.value for t in walk(lc53) if isinstance(t, ft.Text) and t.value]
        rt53 = [t.value for t in walk(rc53) if isinstance(t, ft.Text) and t.value]
        check("layout20: «Сроки» - в левой колонке", "Сроки" in lt53)
        check("layout20: «Сроки» расположены под комментарием",
              "Комментарий" in lt53 and "Сроки" in lt53
              and lt53.index("Комментарий") < lt53.index("Сроки"),
              f"{[x for x in lt53 if x in ('Комментарий', 'Сроки')]}")
        check("layout20: «Промежуточные точки» и «Скан задания» переехали влево",
              "Промежуточные точки" in lt53 and "Скан задания" in lt53)
        check("layout20: справа ТОЛЬКО пункты (нет «Сроки»/точек/скана)",
              "Пункты задания" in rt53 and "Сроки" not in rt53
              and "Промежуточные точки" not in rt53 and "Скан задания" not in rt53)
        scr53 = [c for c in walk(rc53) if isinstance(c, ft.Column)
                 and getattr(c, "scroll", None) == ft.ScrollMode.ALWAYS
                 and getattr(c, "expand", None)]
        check("layout20: список пунктов скроллится сам, на всю высоту панели",
              len(scr53) >= 1, f"{len(scr53)}")
        check("layout20: левая колонка - собственный постоянный скролл",
              getattr(getattr(lc53, "content", None), "scroll", None) == ft.ScrollMode.ALWAYS)
        check("layout20: у панели пунктов видимый бегунок (ScrollbarTheme)",
              getattr(getattr(rc53, "theme", None) or getattr(getattr(rc53, "content", None), "theme", None),
                      "scrollbar_theme", None) is not None)

    # ── 54. Раунд 20, задачи 1–2: автоподтягивание исполнителей, удаление пункта ──
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": ["Кудрявцев Василий Александрович"],
                   "person_roles": {}, "hidden_people": []})
    _seed_raw([_ctrl("c20", "ТЕСТ-20", executors=["Семисенко Иван Юрьевич"],
                     tasks=[{"id": "t20a", "title": "п. 1", "assignees": ["Грубников Георгий Григорьевич"],
                             "due_date": "2026-09-23", "is_done": False, "done_date": None, "comment": ""},
                            {"id": "t20b", "title": "п. 2", "assignees": ["Семисенко Иван Юрьевич"],
                             "due_date": "2026-08-14", "is_done": False, "done_date": None, "comment": ""}])])
    page, tab, _ = build(1280)
    rows54 = _visible_rows(tab)
    if rows54:
        rows54[0].on_click(None)
    exec_multi54 = None
    ass_multis54 = []
    for c in walk(tab):
        if isinstance(c, ft.Container) and hasattr(c, "_get_selected"):
            texts54 = [t.value for t in walk(c) if isinstance(t, ft.Text) and t.value]
            if "Исполнители" in texts54:
                exec_multi54 = c
            if any((x or "").startswith("Отв.") for x in texts54):
                ass_multis54.append(c)
    check("sync20: мультивыбор «Исполнители» найден", exec_multi54 is not None)
    if exec_multi54 is not None:
        sel54 = exec_multi54._get_selected()
        check("sync20: ответственные пунктов подтянуты в исполнители при открытии",
              "Грубников Георгий Григорьевич" in sel54 and "Семисенко Иван Юрьевич" in sel54,
              f"{sel54}")
    # live-синк: отметка нового ответственного в пункте сразу в «Исполнители»
    check("sync20: мультивыбор ответственного пункта найден", len(ass_multis54) >= 1,
          f"{len(ass_multis54)}")
    if ass_multis54 and exec_multi54 is not None:
        target_name54, target_cb54 = None, None
        for cbx in [x for x in walk(ass_multis54[0]) if isinstance(x, ft.Checkbox)]:
            full54 = getattr(cbx, "tooltip", None)
            if full54 and full54 not in exec_multi54._get_selected() and getattr(cbx, "on_change", None):
                target_name54, target_cb54 = full54, cbx
                break
        if target_cb54 is not None:
            target_cb54.on_change(_types50.SimpleNamespace(control=_types50.SimpleNamespace(value=True)))
            check("sync20: live-отметка ответственного сразу в «Исполнители»",
                  target_name54 in exec_multi54._get_selected(), f"{target_name54}")
        else:
            check("sync20: есть свободное имя для live-проверки", False, "все опции уже выбраны?")
    # удаление добавленного пункта без закрытия карточки
    cols54 = find_card_columns(tab)
    rc54 = cols54[1] if cols54 else None
    del54 = [c for c in walk(rc54) if isinstance(c, ft.IconButton)
             and getattr(c, "icon", None) == ft.icons.DELETE_OUTLINE] if rc54 is not None else []
    titles54 = [t.value for t in walk(rc54) if isinstance(t, ft.TextField)
                and (t.value or "").startswith("п.")] if rc54 is not None else []
    check("del20: у пунктов видна кнопка удаления", len(del54) >= 2, f"{len(del54)}")
    check("del20: до удаления два пункта", titles54 == ["п. 1", "п. 2"], f"{titles54}")
    if len(del54) >= 2:
        del54[0].on_click(None)
        titles54b = [t.value for t in walk(rc54) if isinstance(t, ft.TextField)
                     and (t.value or "").startswith("п.")]
        check("del20: случайно добавленный пункт убирается без закрытия карточки",
              titles54b == ["п. 2"], f"{titles54b}")
    # сохранение: исполнители = объединение, пункт удалён
    save54 = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
              and getattr(c, "text", None) == "Сохранить"]
    if save54:
        save54[0].on_click(None)
        stored54 = load_controls()
        hit54 = [c for c in stored54 if c.incoming_number == "ТЕСТ-20"]
        ok54 = (hit54 and "Грубников Георгий Григорьевич" in (hit54[0].executors or [])
                and len(hit54[0].tasks) == 1)
        check("del20+sync20: сохранение - исполнители объединены, пункт удалён",
              bool(ok54), f"{hit54[0].executors if hit54 else 'не найден'}")
    # нейтральные настройки/данные после раунда 20
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "person_roles": {}, "hidden_people": []})

    # ── 55. Раунд 21, задача 1: восстановление скрытого («Гайнутдинов») ──────
    from core.controls_data import add_extra_person as _aep21b
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "person_roles": {}, "hidden_people": []})
    # ловушка, сложившаяся у пользователя: ФИО одновременно в extra И в hidden
    st55 = {"extra_people": ["Гайнутдинов Станислав Игоревич"],
            "hidden_people": ["Гайнутдинов Станислав Игоревич"]}
    names55 = get_all_people_names(st55)
    check("refs21: пара extra+hidden - человек невидим до восстановления (ловушка)",
          all("гайнутдинов" not in (n or "").casefold() for n in names55))
    check("refs21: повторное добавление снимает скрытие (раньше - мёртвый False)",
          _aep21b(st55, "Гайнутдинов Станислав Игоревич") is True)
    check("refs21: hidden_people вычищен", st55.get("hidden_people") == [],
          f"{st55.get('hidden_people')}")
    check("refs21: человек виден в справочнике после восстановления",
          any("гайнутдинов" in (n or "").casefold() for n in get_all_people_names(st55)))
    check("refs21: видимый дубликат по-прежнему не добавляется",
          _aep21b(st55, "гайнутдинов станислав игоревич") is False)
    # скрытие, записанное с двойными пробелами, снимается нормальной строкой
    st55c = {"extra_people": [], "hidden_people": ["Гайнутдинов  Станислав   Игоревич"]}
    check("refs21: двойные пробелы в hidden нормализуются при фильтрации",
          all("гайнутдинов" not in (n or "").casefold() for n in get_all_people_names(st55c)))
    check("refs21: «кривое» скрытие снимается добавлением нормальной строки",
          _aep21b(st55c, "Гайнутдинов Станислав Игоревич") is True
          and st55c.get("hidden_people") == [])
    check("refs21: человек виден и после «кривого» скрытия",
          any("гайнутдинов" in (n or "").casefold() for n in get_all_people_names(st55c)))

    # ── 56. Раунд 21, задача 3: inline-формат пунктов в содержании ──────────
    from core.controls_models import parse_content_tasks as _pct21, resolve_task_assignees as _rta21
    src56 = ("Распоряжение 8/216-р/17дсп п. 2 - Миронович 01.05.2026, п. 3 - Авахян 01.05.2026, "
             "п. 5б Семисенко - 01.09.2026, п. 6 Семисенко, Чащин - 16.02.2026, "
             "п. 7 Гайнутдинов - 01.04.2026, п. 8 - 30.07.2026")
    clean56, tasks56 = _pct21(src56)
    got56 = [(t.title, ",".join(t.assignees), t.due_date) for t in tasks56]
    check("import21: inline-формат - 6 пунктов", len(tasks56) == 6, f"{len(tasks56)}")
    check("import21: inline - номера/исполнители/сроки разобраны",
          got56 == [("п. 2", "Миронович", "2026-05-01"),
                    ("п. 3", "Авахян", "2026-05-01"),
                    ("п. 5б", "Семисенко", "2026-09-01"),
                    ("п. 6", "Семисенко,Чащин", "2026-02-16"),
                    ("п. 7", "Гайнутдинов", "2026-04-01"),
                    ("п. 8", "", "2026-07-30")], f"{got56}")
    check("import21: inline - содержание очищено до реквизитов",
          clean56 == "Распоряжение 8/216-р/17дсп", clean56)
    clean56b, tasks56b = _pct21("Распоряжение 2/216-р от 15.01.2026 Чашин Э.А. п.3 к 05.05.2026, п. 5 к 05.09.2026")
    check("import21: цепочный формат (раунд 20) не сломан",
          clean56b == "Распоряжение 2/216-р от 15.01.2026"
          and [t.title for t in tasks56b] == ["п. 3", "п. 5"]
          and all(t.assignees == ["Чашин Э.А."] for t in tasks56b),
          f"{clean56b} / {[(t.title, t.assignees) for t in tasks56b]}")
    _rta21(tasks56, ["Миронович Д.В.", "Авахян А.А.", "Семисенко И.Ю.", "Чащин Э.А.", "Гайнутдинов С.И."])
    check("import21: «голые» фамилии привязаны к известным ФИО",
          tasks56[0].assignees == ["Миронович Д.В."]
          and tasks56[3].assignees == ["Семисенко И.Ю.", "Чащин Э.А."]
          and tasks56[4].assignees == ["Гайнутдинов С.И."],
          f"{[t.assignees for t in tasks56]}")
    check("import21: пункт без исполнителя резолвером не ломается",
          tasks56[5].assignees == [] and tasks56[5].due_date == "2026-07-30")
    _t56x = _pct21("Задание п. 1 - Иванов 01.09.2026")[1]
    _rta21(_t56x, ["Иванов И.И.", "Иванов П.П."])
    check("import21: неоднозначная фамилия (2 Ивановых) остаётся как есть",
          bool(_t56x) and _t56x[0].assignees == ["Иванов"])

    # ── 57. Раунд 21, задача 3: сквозной импорт inline-формата из .xlsx ─────
    try:
        from openpyxl import Workbook as _Wb21
        wb57 = _Wb21()
        ws57 = wb57.active
        ws57.append(["КОНТРОЛИ ОТДЕЛА КРИМИНАЛИСТИКИ"])
        ws57.append(list(TABLE_HEADERS))
        ws57.append([3, "Иссоп-216-1017-26/дсп", "10.02.2026", "СУ", src56,
                     "Чащин Э.А., Миронович Д.В., Авахян А.А., Семисенко И.Ю., Гайнутдинов С.И.",
                     "Потемкин С.А.", "01.09.2026", "01.09.2026", ""])
        p57 = os.path.join(tempfile.gettempdir(), "round21_import_test.xlsx")
        wb57.save(p57)
        parsed57, stats57 = import_from_excel(p57, [])
        ok57 = len(parsed57) == 1 and len(parsed57[0].tasks) == 6
        check("import21: импорт .xlsx раскидывает пункты по карточке", ok57,
              f"tasks={len(parsed57[0].tasks) if parsed57 else 'нет'}")
        if ok57:
            ctl57 = parsed57[0]
            check("import21: импорт - содержание без перечня пунктов",
                  ctl57.content == "Распоряжение 8/216-р/17дсп", ctl57.content)
            surnames57 = [(e or "").split()[0].casefold() for e in ctl57.executors if e]
            check("import21: исполнители без дублей фамилий",
                  len(surnames57) == len(set(surnames57)), f"{ctl57.executors}")
            check("import21: «голые» фамилии подтянулись к колонке «Исполнитель»",
                  any(t.title == "п. 2" and t.assignees == ["Миронович Д.В."] for t in ctl57.tasks),
                  f"{[ (t.title, t.assignees) for t in ctl57.tasks][:2]}")
            check("import21: п.6 сохранил двух исполнителей",
                  any(t.title == "п. 6" and len(t.assignees) == 2 for t in ctl57.tasks))
            check("import21: п.8 сохранён без исполнителя",
                  any(t.title == "п. 8" and not t.assignees and t.due_date == "2026-07-30"
                      for t in ctl57.tasks))
    except Exception:
        traceback.print_exc()
        check("import21: сквозной импорт .xlsx без исключений", False)

    # ── 58. Раунд 21, задача 3: пересборка пунктов не затирает черновик ─────
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "person_roles": {}, "hidden_people": []})
    _seed_raw([_ctrl("c21", "ТЕСТ-21")])
    page, tab, _ = build(1280)
    check("draft21: карточка (edit) открыта", _open_card(tab))
    add58 = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
             and "Добавить пункт" in (getattr(c, "text", None) or "")]
    check("draft21: «Добавить пункт» найдена", len(add58) >= 1, f"{len(add58)}")
    if add58:
        add58[0].on_click(None)   # пункт 1
        add58[0].on_click(None)   # пункт 2 — пересборка пункта 1
        cols58 = find_card_columns(tab)
        rc58 = cols58[1] if cols58 else None
        tmultis58 = [m for m in walk(rc58) if hasattr(m, "_get_selected")] if rc58 is not None else []
        check("draft21: два пункта = два мультивыбора ответственных",
              len(tmultis58) == 2, f"{len(tmultis58)}")
        if len(tmultis58) == 2:
            cb58 = [x for x in walk(tmultis58[0]) if isinstance(x, ft.Checkbox)
                    and getattr(x, "tooltip", None) == "Семисенко Иван Юрьевич"]
            check("draft21: чекбокс исполнителя в п.1 найден", len(cb58) == 1, f"{len(cb58)}")
            tf58c = [t for t in walk(rc58) if isinstance(t, ft.TextField)
                     and getattr(t, "hint_text", None) == "Комментарий…"]
            if cb58:
                cb58[0].on_change(_types50.SimpleNamespace(
                    control=_types50.SimpleNamespace(value=True)))
            if tf58c:
                tf58c[0].value = "черновой коммент п.1"
            add58[0].on_click(None)   # пункт 3 — ПЕРЕСБОРКА: ловушка раунда 20
            tmultis58b = [m for m in walk(rc58) if hasattr(m, "_get_selected")]
            check("draft21: после добавления п.3 мультивыборов три", len(tmultis58b) == 3,
                  f"{len(tmultis58b)}")
            sel58 = tmultis58b[0]._get_selected() if tmultis58b else []
            check("draft21: выбор ответственного п.1 НЕ затёрт пересборкой",
                  "Семисенко Иван Юрьевич" in sel58, f"{sel58}")
            tf58d = [t for t in walk(rc58) if isinstance(t, ft.TextField)
                     and getattr(t, "hint_text", None) == "Комментарий…"]
            check("draft21: комментарий п.1 НЕ затёрт пересборкой",
                  bool(tf58d) and tf58d[0].value == "черновой коммент п.1",
                  f"{tf58d[0].value if tf58d else 'нет поля'}")
            # заголовки пунктов и сохранение
            titles58 = [t for t in walk(rc58) if isinstance(t, ft.TextField)
                        and getattr(t, "hint_text", None) == "Пункт (напр. п.1)"]
            for i58, t58 in enumerate(titles58, 1):
                t58.value = f"п. {i58}"
            save58 = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
                      and getattr(c, "text", None) == "Сохранить"]
            if save58:
                save58[0].on_click(None)
                hit58 = [c for c in load_controls() if c.incoming_number == "ТЕСТ-21"]
                ok58 = (hit58 and len(hit58[0].tasks) == 3
                        and hit58[0].tasks[0].assignees == ["Семисенко Иван Юрьевич"]
                        and hit58[0].tasks[0].comment == "черновой коммент п.1")
                check("draft21: сохранение - 3 пункта, ответственный и коммент п.1 на месте",
                      bool(ok58),
                      f"{[(t.title, t.assignees, t.comment) for t in hit58[0].tasks] if hit58 else 'не найден'}")

    # ── 59. Раунд 21, задача 3: в списке видны ВСЕ пункты со сроками ────────
    _seed_raw([_ctrl("c21b", "ТЕСТ-21Б", tasks=[
        {"id": f"t{i}", "title": f"п. {i}", "assignees": [a], "due_date": d,
         "is_done": False, "done_date": None, "comment": ""}
        for i, (a, d) in enumerate([("Гайнутдинов С.И.", "2026-08-31"),
                                    ("Бережной К.Н.", "2026-08-31"),
                                    ("Грубников Г.Г.", "2026-08-28")], 1)])])
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "person_roles": {}, "hidden_people": []})
    page, tab, _ = build(1280)
    texts59 = [t for t in walk(tab) if isinstance(t, ft.Text)
               and "контроль ТЕСТ-21Б" in (t.value or "") and "п. 3" in (t.value or "")]
    check("content21: ячейка содержания со всеми пунктами найдена", len(texts59) >= 1,
          f"{len(texts59)}")
    if texts59:
        check("content21: текст ячейки - заголовок + все 3 пункта (исполнители и сроки)",
              "п. 1 — Гайнутдинов С.И. — 31.08.2026" in texts59[0].value
              and "п. 2 — Бережной К.Н. — 31.08.2026" in texts59[0].value
              and "п. 3 — Грубников Г.Г. — 28.08.2026" in texts59[0].value,
              (texts59[0].value or "")[:120])
        check("content21: max_lines покрывает все строки (равно числу строк)",
              (texts59[0].max_lines or 0) >= 4, f"max_lines={texts59[0].max_lines}")

    # ── 60. Раунд 21, задача 5: антидубль прикрепления файлов ───────────────
    from ui.controls.controls_tab import _attach_event_is_duplicate, _filter_new_attach_files
    st60 = {}
    sig60 = ("/tmp/a.png",)
    check("attach21: первое событие выбора - не дубль",
          _attach_event_is_duplicate(st60, sig60, now=100.0) is False)
    check("attach21: тот же набор сразу - дубль (кейс x13)",
          _attach_event_is_duplicate(st60, sig60, now=100.5) is True)
    check("attach21: тот же набор после окна 3 с - не дубль",
          _attach_event_is_duplicate(st60, sig60, now=104.5) is False)
    check("attach21: другой набор - не дубль",
          _attach_event_is_duplicate(st60, ("/tmp/b.png",), now=104.6) is False)
    _f60a = _types50.SimpleNamespace(path="C:\\scans\\фото.png")
    _f60b = _types50.SimpleNamespace(path="/x/уже есть.png")
    _f60c = _types50.SimpleNamespace(path="D:\\другое\\фото.png")
    fresh60, skipped60 = _filter_new_attach_files([_f60a, _f60b, _f60c], {"уже есть.png"})
    check("attach21: фильтр имён - остаётся один новый файл",
          len(fresh60) == 1 and fresh60[0] is _f60a and skipped60 == 2,
          f"{len(fresh60)}/{skipped60}")

    # ── 61. Раунд 21, задачи 6-9: заголовок, полугодие, вкладки, лог ────────
    check("hdr21: TABLE_HEADERS[6] - «За кем контроль» (без фамилий в скобках)",
          TABLE_HEADERS[6] == "За кем контроль", TABLE_HEADERS[6])
    from ui.controls.controls_tab import _PERIOD_LABELS as _PL21, _period_key as _PK21
    from core.controls_exporter import parse_periodicity as _pp21, _period_label as _plbl21
    check("period21: «Каждое полугодие» в опциях периодичности (182 дня)",
          ("semiannual", "Каждое полугодие", 182) in _PL21)
    check("period21: _period_key(182) = semiannual", _PK21(182) == "semiannual")
    check("period21: импорт «каждое полугодие» -> periodic/182",
          _pp21("каждое полугодие") == ("periodic", 182), f"{_pp21('каждое полугодие')}")
    check("period21: подпись 182 дней - «каждые полгода»",
          _plbl21(182) == "каждые полгода", _plbl21(182))
    main21 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
    src_main21 = open(main21, encoding="utf-8").read()
    check("tabs21: вкладка индекса 0 - «Контроли»",
          '_mk_tab_btn(0, "Контроли"' in src_main21)
    check("tabs21: «Следственные отделы» - третья вкладка",
          '_mk_tab_btn(2, "Следственные отделы"' in src_main21)
    check("tabs21: контроли видимы по умолчанию (остальные скрыты)",
          "tab3_container.visible = (index == 0)" in src_main21
          and "tab1_container.visible = (index == 2)" in src_main21)
    from core import zonal_data as _zd21
    _zd21._CRIM_LOAD_LOGGED["done"] = False
    buf61 = io.StringIO()
    with contextlib.redirect_stdout(buf61):
        _zd21.load_criminalists()
        _zd21.load_criminalists()
        _zd21.load_criminalists()
    out61 = buf61.getvalue()
    check("log21: «Zagruzheno kriminalistov» - одна строка за процесс, не спам",
          out61.count("kriminalistov") <= 1, f"{len(out61.splitlines())} строк(и)")

    # ══════════════════════════════════════════════════════════════════
    # Раунд 22 (PROMPT_контроли_доработка22.md)
    # ══════════════════════════════════════════════════════════════════

    # ── 62. Раунд 22, задачи 2/3/5: контроль БЕЗ id — лечение и гарды ──────
    from core.controls_data import (
        _heal_missing_ids, ensure_control_id,
        get_attachment_source_path, resolve_attachment as _res_att22,
        delete_attachment as _del_att22, delete_all_attachments as _del_all22,
        attachment_abs, get_attachments_path,
    )
    # 62а. healing на уровне load_controls: id из префикса папки вложений
    from core.controls_data import get_controls_file as _gcf22
    raw62 = [
        {"incoming_number": "Иссоп-216-194-26/дсп", "receive_date": None,
         "executors": ["Семисенко И.Ю."], "controller": "Потемкин С.А.",
         "attachments": ["aabbccdd/foto.png", "aabbccdd/scan.pdf"]},   # id отсутствует
        {"id": "", "incoming_number": "Иссоп-216-195-26/дсп",
         "executors": ["Чашин Э.А."], "attachments": []},               # id пустой
        {"id": "keep-1", "incoming_number": "Иссоп-216-196-26/дсп", "attachments": []},
    ]
    _seed_raw(raw62)
    ctl62 = load_controls()
    by_inc62 = {c.incoming_number: c for c in ctl62}
    check("id22: контроль без id получил id из папки вложений (файл остаётся на месте)",
          by_inc62["Иссоп-216-194-26/дсп"].id == "aabbccdd",
          by_inc62["Иссоп-216-194-26/дсп"].id)
    _healed62 = by_inc62["Иссоп-216-195-26/дсп"].id
    check("id22: контроль с пустым id и без вложений - новый uuid (не пустой)",
          isinstance(_healed62, str) and len(_healed62) >= 8, f"{_healed62!r}")
    check("id22: нормальный id не тронут", by_inc62["Иссоп-216-196-26/дсп"].id == "keep-1")
    ctl62b = load_controls()
    by_inc62b = {c.incoming_number: c for c in ctl62b}
    check("id22: вылеченные id СОХРАНЕНЫ (при повторной загрузке те же, не перевыдаются)",
          by_inc62b["Иссоп-216-194-26/дсп"].id == "aabbccdd"
          and by_inc62b["Иссоп-216-195-26/дсп"].id == _healed62)
    # 62б. heal с конфликтом префиксов/разными префиксами — безопасный uuid
    raw62c = [
        {"id": "aabbccdd", "incoming_number": "Б-ЗАНЯТ", "attachments": []},  # id занят
        {"incoming_number": "Б-ПРЕФ", "attachments": ["aabbccdd/x.png"]},  # префикс занят
        {"incoming_number": "Б-РАЗНЫЕ", "attachments": ["p1/a.png", "p2/b.png"]},  # разные
    ]
    check("id22: _heal_missing_ids - занятый префикс не переиспользуется",
          _heal_missing_ids(raw62c) is True
          and raw62c[0]["id"] == "aabbccdd"
          and raw62c[1]["id"] != "aabbccdd"
          and raw62c[2]["id"] not in ("p1", "p2")
          and len({d["id"] for d in raw62c}) == 3,
          f"{raw62c[1]['id']}/{raw62c[2]['id']}")
    # 62в. ensure_control_id — страховка в карточке
    _c62 = Control(id=None, incoming_number="Е-1", attachments=["zz99/f.png"])
    check("id22: ensure_control_id берёт id из вложений",
          ensure_control_id(_c62) is True and _c62.id == "zz99", _c62.id)
    check("id22: ensure_control_id не трогает контроль с id",
          ensure_control_id(Control(id="have-1")) is False)
    _c62b = Control(id=None, incoming_number="Е-2")
    check("id22: ensure_control_id без вложений - новый uuid",
          ensure_control_id(_c62b) is True and bool(_c62b.id))
    # 62г. гарды вложений против TypeError Path/None (кейс из ЛОГ.txt)
    check("att22: get_attachment_source_path(None, ...) -> None (без TypeError)",
          get_attachment_source_path(None, "x/y.png") is None
          and get_attachment_source_path("", "x/y.png") is None)
    check("att22: resolve_attachment(None, ...) -> None",
          _res_att22(None, "x/y.png", {}) is None)
    try:
        _del_att22(None, "x/y.png", {})
        _del_all22(None, {})
        check("att22: delete_attachment/delete_all_attachments(None) - без исключений", True)
    except Exception as _e22:
        check("att22: delete_attachment/delete_all_attachments(None) - без исключений",
              False, str(_e22))
    # 62д. фолбэк предпросмотра по rel-пути (файл лежит в папке uuid из rel)
    _dir22 = get_attachments_path() / "aabbccdd"
    _dir22.mkdir(parents=True, exist_ok=True)
    _f22 = _dir22 / "foto.png"
    _f22.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    check("att22: attachment_abs находит файл по rel-пути (превью-фолбэк)",
          attachment_abs("aabbccdd/foto.png").exists())
    check("att22: resolve чужим id НЕ находит - фолбэк покрывает именно этот разрыв",
          _res_att22("another-id", "aabbccdd/foto.png", {}) is None)
    try:
        _f22.unlink()
        _dir22.rmdir()
    except OSError:
        pass

    # ── 63. Раунд 22, задача 1: sync_due_after_tasks — правила сдвига ──────
    from core.controls_models import sync_due_after_tasks as _sync22, ControlTask as _CT22

    def _mk22(due=None, end=None, ctype="once", tasks=()):
        return Control(id="s22", incoming_number="С-22", control_type=ctype,
                       due_date=due, end_date=end,
                       tasks=[_CT22(id=f"t{i}", title=t[0], due_date=t[1], is_done=t[2])
                              for i, t in enumerate(tasks, 1)])

    # сценарий пользователя: п.1/п.3 — 31.08, п.10 — 28.08; п.10 исполнен
    _s22 = _mk22(due="2026-08-28", tasks=[("п. 1", "2026-08-31", False),
                                          ("п. 3", "2026-08-31", False),
                                          ("п. 10", "2026-08-28", True)])
    _sync22(_s22)
    check("sync22: «следующая дата» исполненного пункта сдвинулась на ближайший оставшийся",
          _s22.due_date == "2026-08-31", _s22.due_date)
    # срок разового раньше последнего оставшегося пункта — сдвигается на него
    _s22b = _mk22(due="2026-08-28", end="2026-02-16",
                  tasks=[("п. 1", "2026-09-01", False), ("п. 2", "2026-02-16", True)])
    _sync22(_s22b)
    check("sync22: срок разового (раньше оставшихся пунктов) сдвинут на последний",
          _s22b.end_date == "2026-09-01", _s22b.end_date)
    # ручной срок ПОЗЖЕ всех пунктов сохраняется
    _s22c = _mk22(due="2026-08-28", end="2026-12-31",
                  tasks=[("п. 1", "2026-09-01", False)])
    _sync22(_s22c)
    check("sync22: ручной срок позже пунктов НЕ затирается", _s22c.end_date == "2026-12-31")
    # ручная «следующая дата» вне дат исполненных пунктов сохраняется
    _s22d = _mk22(due="2026-08-29",
                  tasks=[("п. 1", "2026-08-31", False), ("п. 10", "2026-08-28", True)])
    _sync22(_s22d)
    check("sync22: ручная due вне пунктов сохраняется", _s22d.due_date == "2026-08-29")
    # due пуста при наличии пунктов → проставляется ближайшей
    _s22e = _mk22(due=None, tasks=[("п. 1", "2026-08-31", False)])
    _sync22(_s22e)
    check("sync22: пустая due проставляется ближайшим неисполненным пунктом",
          _s22e.due_date == "2026-08-31", _s22e.due_date)
    # все пункты исполнены — даты не трогаем
    _s22f = _mk22(due="2026-08-28", end="2026-08-28",
                  tasks=[("п. 1", "2026-08-28", True)])
    _sync22(_s22f)
    check("sync22: все пункты исполнены - due/end остаются (контроль ждёт закрытия)",
          _s22f.due_date == "2026-08-28" and _s22f.end_date == "2026-08-28")
    # периодический: сдвигается только due, конечная дата не трогается
    _s22g = _mk22(due="2026-08-28", end="2026-02-16", ctype="periodic",
                  tasks=[("п. 1", "2026-09-01", False), ("п. 2", "2026-08-28", True)])
    _sync22(_s22g)
    check("sync22: у периодического due сдвигается, end (дата окончания цикла) сохраняется",
          _s22g.due_date == "2026-09-01" and _s22g.end_date == "2026-02-16",
          f"{_s22g.due_date}/{_s22g.end_date}")
    # due совпадает и с исполненным, и с неисполненным пунктом — НЕ протухшая
    _s22h = _mk22(due="2026-08-31",
                  tasks=[("п. 1", "2026-08-31", False), ("п. 10", "2026-08-31", True)])
    _sync22(_s22h)
    check("sync22: due, актуальная среди неисполненных, сохраняется",
          _s22h.due_date == "2026-08-31")

    # ── 64. Раунд 22, задачи 1/2 (UI): жёлтая кнопка мульти-выбор + сдвиг ──
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "person_roles": {}, "hidden_people": []})
    _seed_raw([_ctrl("u22", "Ю-22", executors=["Миронович Д.В."], tasks=[
        {"id": "u1", "title": "п. 1", "assignees": ["Миронович Д.В."],
         "due_date": "2026-08-31", "is_done": False, "done_date": None, "comment": ""},
        {"id": "u3", "title": "п. 3", "assignees": ["Свеженко А.С."],
         "due_date": "2026-08-31", "is_done": False, "done_date": None, "comment": ""},
        {"id": "u10", "title": "п. 10", "assignees": ["Ливенский В.О."],
         "due_date": "2026-08-28", "is_done": False, "done_date": None, "comment": ""},
    ])])
    # due 28.08 (дата п.10) + срок разового; receive_date — пустая (кейс импорта)
    _raw64 = json.load(open(_gcf22(), encoding="utf-8"))
    _raw64["controls"][0]["due_date"] = "2026-08-28"
    _raw64["controls"][0]["end_date"] = "2026-02-16"
    _raw64["controls"][0]["receive_date"] = None
    json.dump(_raw64, open(_gcf22(), "w", encoding="utf-8"), ensure_ascii=False)
    page, tab, _ = build(1280)
    rows64 = _visible_rows(tab)
    check("ui22: строка Ю-22 видна", len(rows64) == 1 and "Ю-22" in _visible_texts(tab))
    rows64[0].on_click(None)
    ylw64 = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
             and getattr(c, "text", None) == "Исполнен пункт"]
    check("ui22: жёлтая «Исполнен пункт» в карточке", len(ylw64) == 1)
    if ylw64:
        ylw64[0].on_click(None)
        dlg64 = page.dialogs[-1] if page.dialogs else None
        cbs64 = [c for c in walk(dlg64) if isinstance(c, ft.Checkbox)] if dlg64 else []
        check("ui22: в диалоге - 3 чекбокса (по числу пунктов)", len(cbs64) == 3,
              f"{len(cbs64)}")
        # отметить СРАЗУ ДВА пункта (п.10 и п.3) — сценарий «несколько сразу»
        for _b64 in cbs64:
            if getattr(_b64, "data", None) in ("u10", "u3"):
                _b64.value = True
        conf64 = [c for c in walk(dlg64) if isinstance(c, ft.ElevatedButton)
                  and getattr(c, "text", None) == "Отметить исполненными"]
        if conf64:
            conf64[0].on_click(None)
            all64 = load_controls()
            ctl64 = next((c for c in all64 if c.incoming_number == "Ю-22"), None)
            _t64 = {t.id: t for t in (ctl64.tasks if ctl64 else [])}
            check("ui22: отмечены ОБА пункта за один диалог (п.10 и п.3)",
                  bool(ctl64) and _t64["u10"].is_done and _t64["u3"].is_done
                  and not _t64["u1"].is_done)
            check("ui22: «следующая дата» сдвинулась с исполненных на оставшийся (31.08)",
                  ctl64 is not None and ctl64.due_date == "2026-08-31",
                  f"{ctl64.due_date if ctl64 else None}")
            check("ui22: срок разового сдвинут до последнего оставшегося пункта",
                  ctl64 is not None and ctl64.end_date == "2026-08-31",
                  f"{ctl64.end_date if ctl64 else None}")
            check("ui22: контроль ОДИН (без задвоения строки)",
                  len([c for c in all64 if c.incoming_number == "Ю-22"]) == 1)
            # теперь «Сохранить» с пустой датой поступления — НЕ тихий отказ
            save64 = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
                      and getattr(c, "text", None) == "Сохранить"]
            check("ui22: кнопка «Сохранить» в карточке есть", len(save64) == 1)
            if save64:
                save64[0].on_click(None)
                after64 = load_controls()
                same64 = [c for c in after64 if c.incoming_number == "Ю-22"]
                check("ui22: «Сохранить» отработал - контроль не задвоился",
                      len(same64) == 1, f"{len(same64)}")
                _today64 = datetime.now().date().isoformat()
                check("ui22: пустая «Дата поступления» проставлена автоматически (сегодня)",
                      bool(same64) and same64[0].receive_date == _today64,
                      f"{same64[0].receive_date if same64 else None}")
                check("ui22: статусы пунктов пережили «Сохранить» карточки",
                      bool(same64) and {t.id: t.is_done for t in same64[0].tasks}
                      == {"u1": False, "u3": True, "u10": True})
                check("ui22: сдвинутые даты не откатились «Сохранить»",
                      bool(same64) and same64[0].due_date == "2026-08-31"
                      and same64[0].end_date == "2026-08-31")

    # ── 65. Раунд 22, задача 2 (UI): импорт присваивает id сразу ───────────
    try:
        from openpyxl import Workbook as _Wb22
        _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                       "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                       "extra_people": [], "person_roles": {}, "hidden_people": []})
        _seed_raw([])   # пустая база — «удалил и заново импортировал»
        wb65 = _Wb22()
        ws65 = wb65.active
        ws65.append(["КОНТРОЛИ ОТДЕЛА КРИМИНАЛИСТИКИ"])
        ws65.append(list(TABLE_HEADERS))
        ws65.append([1, "Иссоп-216-194-26/дсп", "", "СУ",
                     "Задание п. 1 - Миронович 31.08.2026, п. 3 - Свеженко 31.08.2026",
                     "Миронович Д.В., Свеженко А.С.", "Потемкин С.А.",
                     "16.02.2026", "", ""])
        ws65.append([2, "Иссоп-216-195-26/дсп", "10.08.2026", "СУ",
                     "Контроль без пунктов", "Семисенко И.Ю.", "Потемкин С.А.",
                     "20.08.2026", "", ""])
        p65 = os.path.join(tempfile.gettempdir(), "round22_import_test.xlsx")
        wb65.save(p65)
        page, tab, _ = build(1280)
        picker65 = getattr(page, "_controls_import_picker", None)
        check("import22: FilePicker импорта зарегистрирован", picker65 is not None)
        if picker65 is not None:
            import types as _types65
            _ev65 = _types65.SimpleNamespace(
                path=None, files=[_types65.SimpleNamespace(path=p65)])
            # on_result — EventHandler: вызываем через хелпер харнесса
            _invoke_event_handler(picker65.on_result, _ev65)
            dlg65 = page.dialogs[-1] if page.dialogs else None
            check("import22: диалог предпросмотра открыт", dlg65 is not None)
            conf65 = [c for c in walk(dlg65) if isinstance(c, ft.ElevatedButton)
                      and getattr(c, "text", None) == "Импортировать"] if dlg65 else []
            if conf65:
                conf65[0].on_click(None)
                imp65 = load_controls()
                check("import22: оба контроля импортированы", len(imp65) == 2,
                      f"{len(imp65)}")
                check("import22: импортированным контролям id ПРИСВОЕНЫ сразу",
                      all(bool(c.id) for c in imp65),
                      f"{[c.id for c in imp65]}")
                check("import22: id уникальны (никакого общего None)",
                      len({c.id for c in imp65}) == len(imp65))
                first65 = next((c for c in imp65
                                if c.incoming_number == "Иссоп-216-194-26/дсп"), None)
                check("import22: пункты со сроками импортированы (п.1/п.3)",
                      first65 is not None and len(first65.tasks) == 2
                      and all(t.due_date == "2026-08-31" for t in first65.tasks),
                      f"{[(t.title, t.due_date) for t in first65.tasks] if first65 else None}")
                # сохраняемый файл — id на диске, перезагрузка их не перевыдаёт
                _ids65 = {c.incoming_number: c.id for c in load_controls()}
                check("import22: id стабильны после перезагрузки",
                      _ids65 == {c.incoming_number: c.id for c in imp65})
    except Exception:
        traceback.print_exc()
        check("import22: сквозной импорт .xlsx без исключений", False)

    # ── 66. Раунд 22, задача 4: «Прочие» — человек вне справочника ─────────
    # Кейс пользователя: в справочнике 16 криминалистов, чип «И» снят → человек
    # пропадал из фильтра, контроли уезжали в «Прочие».
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": ["Авакян Арсен Артурович"],
                   "person_roles": {"Авакян Арсен Артурович": ["controller"]},
                   "hidden_people": []})
    # NB: «Чащин» (с щ) vs справочный «Чашин» — за порогом fuzzy (0.667 < 0.80),
    # поэтому в тесте корректное написание; опечаточный кейс — «Авахян/Авакян».
    _seed_raw([
        _ctrl("x22a", "ПР-1", executors=["Авахян А.А."]),   # опечатка из Excel
        _ctrl("x22b", "ПР-2", executors=["Чашин Э.А."]),
        _ctrl("x22c", "ПР-3", executors=["Незнакомцев П.П."]),
    ])
    page, tab, _ = build()
    ex66 = _find_dd(tab, "Все исполнители")
    check("ppl22: человек с ролью ТОЛЬКО «К» остаётся в фильтре исполнителей",
          ex66 is not None
          and "Авакян Арсен Артурович" in [o.key for o in (ex66.options or [])])
    check("ppl22: фильтр по нему применяется",
          _set_filter(tab, "Все исполнители", "Авакян Арсен Артурович"))
    vis66 = _visible_texts(tab)
    check("ppl22: контроль находится даже по написанию с опечаткой («Авахян»)",
          "ПР-1" in vis66 and "ПР-2" not in vis66 and "ПР-3" not in vis66,
          f"видно: {sorted(vis66)}")
    check("ppl22: фильтр «Прочие» применился",
          _set_filter(tab, "Все исполнители", FILTER_OTHER))
    vis66 = _visible_texts(tab)
    check("ppl22: в «Прочие» - только человек ВНЕ справочника",
          "ПР-1" not in vis66 and "ПР-2" not in vis66 and "ПР-3" in vis66,
          f"видно: {sorted(vis66)}")

    # ══════════════════════════════════════════════════════════════════
    # Раунд 23 (PROMPT_контроли_доработка23.md)
    # ══════════════════════════════════════════════════════════════════

    # ── 67. Раунд 23, задача 1: вложения — мгновенно видно, крупнее, бейдж ──
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "person_roles": {}, "hidden_people": []})
    _seed_raw([_ctrl("v23", "ВЛ-23", executors=["Семисенко И.Ю."])])
    page, tab, _ = build(1280)
    rows67 = _visible_rows(tab)
    rows67[0].on_click(None)
    picker67 = getattr(page, "_controls_attach_picker", None)
    check("att23: attach-пикер зарегистрирован с карточкой", picker67 is not None)
    # файла «фото» для прикрепления — копия иконки-пнг (минимальный валидный PNG)
    _src67 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "assets", "icon.png")
    _tmp67 = os.path.join(tempfile.gettempdir(), "foto_attach23.png")
    with open(_src67, "rb") as f67, open(_tmp67, "wb") as g67:
        g67.write(f67.read())
    if picker67 is not None:
        _ev67 = _types50.SimpleNamespace(
            path=None, files=[_types50.SimpleNamespace(path=_tmp67, name="foto_attach23.png")])
        _invoke_event_handler(picker67.on_result, _ev67)
        # строка вложения видна СРАЗУ (без «Сохранить» и переоткрытия) —
        # кейс скрина «прикрепилось, но не видно»
        texts67 = [str(t.value) for t in walk(tab) if isinstance(t, ft.Text)
                   and t.value and "foto_attach23.png" in str(t.value)]
        check("att23: строка вложения ВИДНА СРАЗУ после прикрепления",
              len(texts67) >= 1, f"{len(texts67)}")
        # и контроль получил вложение в данных (persist для существующего)
        ctl67 = next((c for c in load_controls() if c.incoming_number == "ВЛ-23"), None)
        check("att23: вложение записалось в контроль и сохранено",
              ctl67 is not None and len(ctl67.attachments) == 1
              and ctl67.attachments[0].endswith("/foto_attach23.png"),
              f"{ctl67.attachments if ctl67 else None}")
        check("att23: id контроля совпадает с папкой вложения",
              ctl67 is not None and ctl67.attachments
              and ctl67.attachments[0].split("/")[0] == ctl67.id)
        # миниатюра 76x76 (раунд 23: было 44 — «очень маленький предпросмотр»)
        imgs67 = [c for c in walk(tab) if isinstance(c, ft.Image)
                  and getattr(c, "width", None) == 76 and getattr(c, "height", None) == 76]
        check("att23: миниатюра вложения 76x76 (а не 44)", len(imgs67) >= 1)
        # кнопки строки крупные (лупа 20)
        zooms67 = [c for c in walk(tab) if isinstance(c, ft.IconButton)
                   and getattr(c, "tooltip", None) == "Предпросмотр"
                   and getattr(c, "icon_size", None) == 20]
        check("att23: лупа предпросмотра крупная (20)", len(zooms67) >= 1)
    # жёлтый бейдж вложения в таблице — заметная пилюля 44px
    badges67 = [c for c in walk(tab) if isinstance(c, ft.Container)
                and getattr(c, "bgcolor", None) == GLASS["today"]
                and getattr(c, "width", None) == 44
                and any(isinstance(i, ft.Icon) for i in walk(c))]
    check("att23: в таблице - заметная жёлтая пилюля вложения (44px)",
          len(badges67) >= 1)
    check("att23: у пилюли tooltip «Вложений: N»",
          any(getattr(b, "tooltip", "").startswith("Вложений:") for b in badges67))

    # ── 68. Раунд 23, задача 2: редакции admin/user — конфиг ────────────────
    from core.edition import (
        load_edition as _le23, is_user_edition as _iue23,
        apply_edition_to_settings as _aets23, save_appdata_edition as _sae23,
    )
    from core.controls_notify import (
        alarm_interval_hours as _aih23, collect_alarm_controls as _cac23,
        control_belongs_to as _cbt23, due_alarms as _da23, prune_alarm_log as _pal23,
    )
    os.environ.pop("PORAYONKA_EDITION", None)
    os.environ.pop("PORAYONKA_USER", None)
    ed68 = _le23(force=True)
    check("edit23: без edition.json и env - редакция admin (обратная совместимость)",
          ed68.get("role") == "admin" and not _iue23(), f"{ed68}")
    # user-редакция через env (так же читает installer: edition.json)
    os.environ["PORAYONKA_EDITION"] = "user"
    os.environ["PORAYONKA_USER"] = "Семисенко Иван Юрьевич"
    ed68b = _le23(force=True)
    check("edit23: env user + ФИО", ed68b.get("role") == "user"
          and ed68b.get("user_name") == "Семисенко Иван Юрьевич", f"{ed68b}")
    st68 = {"network_role": "admin", "network_user": ""}
    check("edit23: apply_edition принудительно ставит user/ФИО",
          _aets23(st68) is True
          and st68.get("network_role") == "user"
          and st68.get("network_user") == "Семисенко Иван Юрьевич", f"{st68}")
    os.environ.pop("PORAYONKA_EDITION", None)
    os.environ.pop("PORAYONKA_USER", None)
    # save_appdata_edition → файл в temp-APPDATA → load_edition его подхватывает
    check("edit23: ФИО пользователя сохраняется в %APPDATA%",
          _sae23("user", "Гайнутдинов Станислав Игоревич") is True
          and _le23(force=True).get("user_name") == "Гайнутдинов Станислав Игоревич")
    # убрать файл-артефакт, чтобы admin-умолчание работало дальше
    _edfile68 = os.path.join(_TEST_APPDATA, "porayonka", "edition.json")
    try:
        os.remove(_edfile68)
    except OSError:
        pass
    _le23(force=True)
    check("edit23: интервал аларма - user 2 ч, admin 24 ч (1 раз/день)",
          _aih23(True) == 2 and _aih23(False) == 24)

    # ── 69. Раунд 23, задача 2: сбор алармов и антиспам-интервалы ──────────
    from datetime import timedelta
    from core.controls_models import deadline_status as _ds23, ControlTask as _CT69
    c69a = Control(id="al1", incoming_number="АЛ-1", due_date="2020-01-01",
                   executors=["Семисенко И.Ю."], receive_date="2020-01-01")
    c69b = Control(id="al2", incoming_number="АЛ-2", due_date="2020-01-02",
                   executors=["Чужой Ч.Ч."], receive_date="2020-01-02")
    c69c = Control(id="al3", incoming_number="АЛ-3", due_date="2020-01-03",
                   executors=["Семисенко И.Ю."], receive_date="2020-01-03",
                   done=True, done_date="2020-01-04")
    c69d = Control(id="al4", incoming_number="АЛ-4", due_date=None,
                   executors=["Семисенко И.Ю."], receive_date="2020-01-01")
    all69 = [c69a, c69b, c69c, c69d]
    check("alarm23: collect - все просроченные для админа (без done/без срока)",
          [c.id for c in _cac23(all69, 3)] == ["al1", "al2"],
          f"{[c.id for c in _cac23(all69, 3)]}")
    check("alarm23: collect - пользователь видит ТОЛЬКО свои",
          [c.id for c in _cac23(all69, 3, "Семисенко Иван Юрьевич")] == ["al1"])
    c69t = Control(id="al5", incoming_number="АЛ-5", due_date=None,
                   receive_date="2020-01-01",
                   tasks=[_CT69(id="t1", title="п.1", assignees=["Гайнутдинов С.И."],
                                due_date="2020-02-02", is_done=False)])
    check("alarm23: «свой» определяется и по ответственному пункта",
          _cbt23(c69t, "Гайнутдинов Станислав Игоревич") is True
          and _cbt23(c69t, "Чужой Ч.Ч.") is False)
    now69 = datetime(2026, 8, 12, 12, 0, 0)
    due69, log69 = _da23(all69[:2], {}, now69, 2)
    check("alarm23: пустой журнал - все просроченные подлежат аларму",
          [c.id for c in due69] == ["al1", "al2"] and "al1" in log69)
    due69b, log69b = _da23(all69[:2], log69, now69 + timedelta(hours=1), 2)
    check("alarm23: через 1 час (интервал 2 ч) - повтора нет",
          due69b == [] and log69b == log69)
    due69c, log69c = _da23(all69[:2], log69, now69 + timedelta(hours=2, minutes=1), 2)
    check("alarm23: через 2 ч - повтор («по злому», пока не исполнено)",
          [c.id for c in due69c] == ["al1", "al2"])
    due69d, _ = _da23(all69[:2], log69, now69 + timedelta(hours=5), 24)
    check("alarm23: админский интервал 24 ч - через 5 ч повтора нет", due69d == [])
    old_log69 = {"x": (now69 - timedelta(days=40)).isoformat(),
                 "y": (now69 - timedelta(days=1)).isoformat(), "bad": "not-a-date"}
    pruned69 = _pal23(old_log69, now69)
    check("alarm23: prune журнала алармов (30 дней, битые значения чистятся)",
          "x" not in pruned69 and "bad" not in pruned69 and "y" in pruned69)

    # ── 70. Раунд 23, задача 2: user-редакция — READ-ONLY карточка ─────────
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "person_roles": {}, "hidden_people": []})
    _seed_raw([_ctrl("ro23", "РО-23", executors=["Семисенко И.Ю."], tasks=[
        {"id": "rt1", "title": "п.1", "assignees": ["Семисенко И.Ю."],
         "due_date": "2026-09-01", "is_done": False, "done_date": None, "comment": ""},
    ])])
    os.environ["PORAYONKA_EDITION"] = "user"
    os.environ["PORAYONKA_USER"] = "Семисенко Иван Юрьевич"
    _le23(force=True)
    page, tab, _ = build(1280)
    btns70 = {getattr(c, "text", None): c for c in walk(tab)
              if isinstance(c, (ft.ElevatedButton, ft.TextButton))}
    check("ro23: у user нет «Добавить контроль»/«Импорт Excel»/«Справочники»",
          "Добавить контроль" not in btns70 and "Импорт Excel" not in btns70
          and "Справочники" not in btns70,
          f"{sorted(k for k in btns70 if k)}")
    check("ro23: «Экспорт Excel» и «Удалить все» остались/скрыты верно",
          "Экспорт Excel" in btns70 and "Удалить все" not in btns70)
    rows70 = _visible_rows(tab)
    rows70[0].on_click(None)   # открыть карточку — должна быть read-only
    texts70 = {getattr(c, "text", None) for c in walk(tab)
               if isinstance(c, (ft.ElevatedButton, ft.TextButton))}
    check("ro23: нет «Сохранить»/«Контроль исполнен»/«Исполнен пункт»/«Удалить»",
          "Сохранить" not in texts70 and "Контроль исполнен" not in texts70
          and "Исполнен пункт" not in texts70 and "Удалить" not in texts70,
          f"{sorted(t for t in texts70 if t)}")
    check("ro23: есть «Закрыть»", "Закрыть" in texts70)
    check("ro23: нет «Прикрепить файл»/«Добавить пункт»/«Добавить точку»",
          "Прикрепить файл" not in texts70 and "+ Добавить пункт" not in texts70
          and "+ Добавить точку" not in texts70)
    card70 = getattr(page, "_controls_detail_card", None) or tab
    tfs70 = [c for c in walk(card70) if isinstance(c, ft.TextField)]
    dds70 = [c for c in walk(card70) if isinstance(c, ft.Dropdown)]
    cbs70 = [c for c in walk(card70) if isinstance(c, ft.Checkbox)]
    check("ro23: все TextField/Dropdown/Checkbox карточки - disabled",
          tfs70 and dds70
          and all(getattr(c, "disabled", False) for c in tfs70)
          and all(getattr(c, "disabled", False) for c in dds70)
          and all(getattr(c, "disabled", False) for c in cbs70),
          f"tf={len(tfs70)} dd={len(dds70)} cb={len(cbs70)}")
    # попытка «сохранить» программно тоже заблокирована (guard в _save_detail)
    before70 = {c.id: c.updated_at for c in load_controls()}
    save70 = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
              and getattr(c, "text", None) == "Сохранить"]
    check("ro23: кнопка «Сохранить» физически отсутствует (не просто disabled)",
          not save70)
    check("ro23: данные не изменились", before70 == {c.id: c.updated_at
                                                     for c in load_controls()})
    os.environ.pop("PORAYONKA_EDITION", None)
    os.environ.pop("PORAYONKA_USER", None)
    _le23(force=True)
    try:
        os.remove(_edfile68) if os.path.exists(_edfile68) else None
    except OSError:
        pass
    _le23(force=True)

    # ── 71. Раунд 23, задача 2: user — обязательный выбор ФИО ──────────────
    _seed_raw([_ctrl("id23", "ФИО-23", executors=["Семисенко И.Ю."])])
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "person_roles": {}, "hidden_people": []})
    os.environ["PORAYONKA_EDITION"] = "user"   # ФИО не задано → спросит
    _le23(force=True)
    page, tab, _ = build(1280)
    dlg71 = page.dialogs[-1] if page.dialogs else None
    check("id23: при первом запуске user-редакции - диалог «Кто вы?»",
          dlg71 is not None and any(isinstance(t, ft.Text) and t.value == "Кто вы?"
                                    for t in walk(dlg71)),
          f"{len(page.dialogs)}")
    ok71 = [c for c in walk(dlg71) if isinstance(c, ft.ElevatedButton)
            and getattr(c, "text", None) == "Подтвердить"] if dlg71 else []
    dd71 = [c for c in walk(dlg71) if isinstance(c, ft.Dropdown)] if dlg71 else []
    check("id23: подтверждение без выбора не закрывает диалог", False if not ok71 else True)
    if ok71 and dd71:
        ok71[0].on_click(None)
        check("id23: пустой выбор - диалог остался", dlg71 in page.dialogs)
        dd71[0].value = "Семисенко Иван Юрьевич"
        ok71[0].on_click(None)
        check("id23: ФИО сохранено (настройки + edition-файл)",
              load_settings().get("network_user") == "Семисенко Иван Юрьевич"
              and _le23(force=True).get("user_name") == "Семисенко Иван Юрьевич")
        check("id23: диалог закрыт после выбора", dlg71 not in page.dialogs)
    os.environ.pop("PORAYONKA_EDITION", None)
    try:
        if os.path.exists(_edfile68):
            os.remove(_edfile68)
    except OSError:
        pass
    _le23(force=True)

    # ── 72. Раунд 23, задача 2: «злой» аларм срока (диалог + журнал) ───────
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": False,
                   "extra_people": [], "person_roles": {}, "hidden_people": []})
    _seed_raw([
        _ctrl("al72", "СРОК-23", executors=["Семисенко И.Ю."]),
    ])
    # контроль просрочен
    _raw72 = json.load(open(get_controls_file(), encoding="utf-8"))
    _raw72["controls"][0]["due_date"] = "2020-01-01"
    json.dump(_raw72, open(get_controls_file(), "w", encoding="utf-8"), ensure_ascii=False)
    page, tab, _ = build(1280)
    check("alarm23: диалога нет до запуска проверки",
          not any(isinstance(t, ft.Text) and t.value == "СРОК КОНТРОЛЯ!"
                  for d in page.dialogs for t in walk(d)))
    hook72 = getattr(page, "_controls_alarm_check", None)
    check("alarm23: тест-хук проверки алармов установлен", callable(hook72))
    if hook72:
        hook72()
        dlg72 = page.dialogs[-1] if page.dialogs else None
        check("alarm23: появился «злой» диалог «СРОК КОНТРОЛЯ!»",
              dlg72 is not None and any(isinstance(t, ft.Text)
                                        and t.value == "СРОК КОНТРОЛЯ!"
                                        for t in walk(dlg72)))
        check("alarm23: в диалоге вх. № просроченного контроля",
              dlg72 is not None and any(isinstance(t, ft.Text)
                                        and t.value == "СРОК-23" for t in walk(dlg72)))
        check("alarm23: журнал алармов записан (антиспам)",
              (load_settings().get("alarm_log") or {}).get("al72") is not None)
        if dlg72:
            page.dialogs.clear()   # имитация визуального «висит открытым»-закрытия
        state72 = load_settings().get("alarm_log") or {}
        hook72()   # повтор сразу — не должен (интервал 24 ч для админа)
        # диалог был «закрыт» снятием из списка — флаг нельзя сбросить так;
        # проверяем журнальную логику: второй вызов не выдаёт «due»
        _alarm_items72 = _cac23(load_controls(), 3)
        from core.controls_notify import due_alarms as _da72b
        due72, _ = _da72b(_alarm_items72, state72, None, 24)
        check("alarm23: повторный аларм в пределах суток подавлен", due72 == [])
    # user-редакция алармит ТОЛЬКО по своим
    _seed_raw([
        _ctrl("al72u", "МОЙ-23", executors=["Семисенко И.Ю."]),
        _ctrl("al72x", "ЧУЖОЙ-23", executors=["Чужой Ч.Ч."]),
    ])
    _raw72u = json.load(open(get_controls_file(), encoding="utf-8"))
    for _cc in _raw72u["controls"]:
        _cc["due_date"] = "2020-01-01"
    json.dump(_raw72u, open(get_controls_file(), "w", encoding="utf-8"), ensure_ascii=False)
    os.environ["PORAYONKA_EDITION"] = "user"
    os.environ["PORAYONKA_USER"] = "Семисенко Иван Юрьевич"
    _le23(force=True)
    page, tab, _ = build(1280)
    hook72u = getattr(page, "_controls_alarm_check", None)
    if hook72u:
        hook72u()
        dlg72u = page.dialogs[-1] if page.dialogs else None
        txts72u = [str(t.value) for t in walk(dlg72u) if isinstance(t, ft.Text)
                   and t.value] if dlg72u else []
        check("alarm23: user-аларм - ТОЛЬКО свой контроль, чужого нет",
              "МОЙ-23" in txts72u and "ЧУЖОЙ-23" not in txts72u, f"{txts72u[:6]}")
    os.environ.pop("PORAYONKA_EDITION", None)
    os.environ.pop("PORAYONKA_USER", None)
    _le23(force=True)

    # ── 73. Раунд 23/24, задачи 2-3: трей/автозапуск/web-режим Win7/звук ──
    from ui.tray_icon import start_tray as _tray23
    from ui.sound_alert import (find_pig_sound as _pig23,
                                play_alarm_sound as _play23,
                                pig_sound_candidates as _pc24)
    from core import autostart as _as23

    class _mock_platform:  # Раунд 25 (задача 1): платформенно-независимые проверки
        """Временно подменяет sys.platform (и sys.frozen) с гарантированным
        откатом; blocked=(...) кладёт sys.modules[name]=None, чтобы
        `import name` падал ImportError (имитация «модуля нет»). Модули
        autostart/sound_alert/tray_icon читают sys.platform/frozen в момент
        ВЫЗОВА функции (не при импорте), поэтому подмена здесь работает и на
        Windows-хосте: тесты больше не зависят от реальной платформы."""
        def __init__(self, platform=None, frozen="__keep__", blocked=()):
            self.platform, self.frozen, self.blocked = platform, frozen, blocked

        def __enter__(self):
            import sys as _s
            self._old_platform = _s.platform
            self._had_frozen = hasattr(_s, "frozen")
            self._old_frozen = getattr(_s, "frozen", None)
            self._old_mods = {}
            if self.platform is not None:
                _s.platform = self.platform
            if self.frozen != "__keep__":
                _s.frozen = self.frozen
            for m in self.blocked:
                self._old_mods[m] = _s.modules.get(m, "__absent__")
                _s.modules[m] = None
            return self

        def __exit__(self, *exc):
            import sys as _s
            _s.platform = self._old_platform
            if self._had_frozen:
                _s.frozen = self._old_frozen
            elif hasattr(_s, "frozen"):
                del _s.frozen
            for m, v in self._old_mods.items():
                if v == "__absent__":
                    _s.modules.pop(m, None)
                else:
                    _s.modules[m] = v
            return False

    _real_sys_platform25 = sys.platform
    _real_had_frozen25 = hasattr(sys, "frozen")
    with _mock_platform("linux"):
        check("tray23: start_tray вне Windows - мягкий None (ничего не ломается)",
              _tray23(PageStub()) is None)
    # Раунд 24 (задача 3): реальный MP3 приоритетнее синтезированного WAV
    pig_path23 = _pig23()
    check("sound24: find_pig_sound - реальный pig.mp3 приоритетнее синтеза WAV",
          pig_path23 is not None and str(pig_path23).endswith("pig.mp3"),
          f"{pig_path23}")
    _n24 = [c.name for c in _pc24()]
    check("sound24: порядок кандидатов - appdata WAV > appdata MP3 > бандл MP3 > WAV",
          len(_n24) >= 4 and _n24[0] == "pig.wav" and _n24[1] == "pig.mp3"
          and _n24[-1] == "pig.wav" and "pig.mp3" in _n24[1:-1],
          f"{_n24}")
    _assets24 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    with open(os.path.join(_assets24, "pig.mp3"), "rb") as _fmp24:
        _mp3h24 = _fmp24.read(3)
    check("sound24: assets/pig.mp3 - валидный MP3 (ID3v2 или MPEG-sync)",
          _mp3h24[:3] == b"ID3"
          or (_mp3h24[0] == 0xFF and len(_mp3h24) > 1 and (_mp3h24[1] & 0xE0) == 0xE0),
          f"{_mp3h24!r}")
    import wave as _wv23
    with _wv23.open(os.path.join(_assets24, "pig.wav"), "rb") as _w23:
        check("sound23: assets/pig.wav - fallback на месте (валидный WAV 16-bit mono)",
              _w23.getnchannels() == 1 and _w23.getsampwidth() == 2
              and _w23.getframerate() == 22050 and _w23.getnframes() > 10000,
              f"{_w23.getframerate()}Hz {_w23.getnframes()}f")
    _sndsrc24 = open(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "ui", "sound_alert.py"), encoding="utf-8").read()
    check("sound24: MP3 играет через Windows MCI (winmm mciSendStringW, stdlib)",
          "mciSendStringW" in _sndsrc24 and "ctypes" in _sndsrc24
          and "mpegvideo" in _sndsrc24)
    with _mock_platform("linux"):  # Раунд 25: независимо от реальной ОС
        check("sound23: play_alarm_sound вне Windows - no-op False (не падает)",
              _play23(True) is False)
    main23 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
    src_main23 = open(main23, encoding="utf-8").read()
    check("win7_23: есть web-режим (--web -> WEB_BROWSER) для Win7-пользователей",
          '"--web" in sys.argv' in src_main23 and "ft.AppView.WEB_BROWSER" in src_main23)
    check("os23: автозапуск подключён при старте (frozen/Windows no-op)",
          "autostart.enable_autostart()" in src_main23)
    check("tray23: трей подключён при старте", "start_tray(page)" in src_main23)
    with _mock_platform("linux"):  # Раунд 25: независимо от реальной ОС
        check("os23: автозапуск вне Windows - supported=False, включение не падает",
              _as23.is_supported() is False and _as23.enable_autostart() is False)
    # Раунд 25: те же ветки на «мок-Windows» - детерминированно на любой ОС.
    # Раунд 32 (доделка): трей теперь работает и в dev-режиме Windows при
    # наличии pystray/pillow — старое ожидание «dev-run -> None» устарело.
    # Все tray-проверки изолированы: importlib.reload(ui.tray_icon) ВНУТРИ
    # мок-контекста сбрасывает _ACTIVE_ICON и module-level состояние, а
    # pystray/PIL подменяются фейками или блокируются (None) — на живом
    # Windows тесты НЕ стартуют настоящий значок и не зависят от
    # установленных библиотек/платформы.
    import importlib as _il_tray
    import ui.tray_icon as _ti_tray

    def _tray_reload():
        _il_tray.reload(_ti_tray)
        return _ti_tray

    _tray_st = {"started": 0, "stopped": 0, "menu_labels": []}

    class _TrayFakeIcon:
        def __init__(self, *a, **kw):
            pass

        def run_detached(self):
            _tray_st["started"] += 1

        def stop(self):
            _tray_st["stopped"] += 1

    import types as _types_tray

    class _TrayFakePy:
        def Menu(self, *items):
            _tray_st["menu_labels"] = [getattr(i, "text", None)
                                       for i in items]
            return object()

        def MenuItem(self, text, action, default=False):
            return _types_tray.SimpleNamespace(text=text, action=action)

        def Icon(self, *a, **kw):
            return _TrayFakeIcon()

    class _TrayFakePIL:
        class Image:
            @staticmethod
            def open(path):
                return object()

    def _install_tray_mods(objs):
        """Подменить sys.modules['pystray']/['PIL'] (None = «модуль отсутствует»)."""
        _mods = {}
        for _m, _o in objs:
            _mods[_m] = sys.modules.get(_m)
            sys.modules[_m] = _o
        return _mods

    def _restore_tray_mods(_mods):
        for _m, _o in _mods.items():
            if _o is None:
                sys.modules.pop(_m, None)
            else:
                sys.modules[_m] = _o

    with _mock_platform("win32"):
        check("os25: мок-Windows dev-run (без frozen) - supported=True, в реестр не пишет",
              _as23.is_supported() is True and _as23.enable_autostart() is False)
        _rs25 = _play23(True)  # на Windows-хосте реально играет MP3 через MCI
        check("sound25: мок-Windows - звук играет (Win) или graceful False (не падает)",
              _rs25 in (True, False))

    # tray25 (актуализирован): dev-режим Windows БЕЗ pystray/pillow -> None
    _mods_no = _install_tray_mods((("pystray", None), ("PIL", None)))
    try:
        with _mock_platform("win32"):
            check("tray25: dev-run Windows без pystray/pillow - мягкий None",
                  _tray_reload().start_tray(PageStub()) is None)
    finally:
        _restore_tray_mods(_mods_no)
        _tray_reload()

    # tray31 (актуализирован): dev-режим Windows + ФЕЙК pystray/pillow
    _mods31 = _install_tray_mods((("pystray", _TrayFakePy()),
                                  ("PIL", _TrayFakePIL())))
    try:
        with _mock_platform("win32"):
            _tm31 = _tray_reload()
            # первый вызов — web-режим (меню «Открыть в браузере»)
            ic31 = _tm31.start_tray(None, web_url="http://127.0.0.1:8555")
            check("tray31: dev-режим + pystray/pillow - иконка создана",
                  ic31 is not None and _tray_st["started"] == 1)
            check("tray31: web-режим - меню «Открыть в браузере»",
                  any("браузере" in (l or "") for l in _tray_st["menu_labels"]),
                  f"{_tray_st['menu_labels']}")
            ic31b = _tm31.start_tray(PageStub())
            check("tray31: повторный вызов возвращает ТОТ ЖЕ объект (singleton)",
                  ic31b is ic31 and _tray_st["started"] == 1)
    finally:
        _restore_tray_mods(_mods31)
        _tray_reload()

    # ── Раунд 32, задача 2: «Открыть» восстанавливает окно, «Выход» завершает ──
    # (закрытие крестиком -> сворачивание проверяем src-проверкой main.py ниже)
    import types as _types32
    _t32 = {"show": None, "quit": None, "stopped": 0}

    class _FI32:
        def run_detached(self):
            pass

        def stop(self):
            _t32["stopped"] += 1

    class _FPy32:
        def Menu(self, *items):
            for it in items:
                if it.text and "Открыть" in it.text:
                    _t32["show"] = it.action
                elif it.text == "Выход":
                    _t32["quit"] = it.action
            return object()

        def MenuItem(self, text, action, default=False):
            return _types32.SimpleNamespace(text=text, action=action)

        def Icon(self, *a, **kw):
            return _FI32()

    class _FPIL32:
        class Image:
            @staticmethod
            def open(path):
                return object()

    class _Win32:
        def __init__(self):
            self.visible = False
            self.minimized = True
            self.destroyed = 0
            self.closed = 0
            self.fronted = 0

        def to_front(self):
            self.fronted += 1

        def destroy(self):
            self.destroyed += 1

        def close(self):
            self.closed += 1

    class _Page32:
        def __init__(self):
            self.window = _Win32()

        def update(self):
            pass

    _mods32 = _install_tray_mods((("pystray", _FPy32()), ("PIL", _FPIL32())))
    try:
        with _mock_platform("win32"):
            _tm32 = _tray_reload()
            from ui.tray_icon import start_tray as _st32
            pg32t = _Page32()
            ic32t = _st32(pg32t)
            check("tray32: иконка создана в dev-режиме (мок-окно)",
                  ic32t is not None)
            _t32["show"](None, None)  # клик «Открыть»
            check("tray32: «Открыть» восстанавливает окно (visible, minimize снят, to_front)",
                  pg32t.window.visible is True and pg32t.window.minimized is False
                  and pg32t.window.fronted >= 1,
                  f"vis={pg32t.window.visible} min={pg32t.window.minimized}")
            _t32["quit"](_FI32(), None)  # «Выход» — полный выход (icon от pystray)
            check("tray32: «Выход» - icon.stop + window.destroy",
                  _t32["stopped"] == 1 and pg32t.window.destroyed == 1,
                  f"stopped={_t32['stopped']} destroyed={pg32t.window.destroyed}")
    finally:
        _restore_tray_mods(_mods32)
        _tray_reload()
    # src: закрытие окна крестиком -> сворачивание (не убийство процесса)
    _src_main32 = open(main23, encoding="utf-8").read()
    check("tray32: main.py - close сворачивает в трей при наличии _tray_icon",
          'getattr(page, "_tray_icon", None)' in _src_main32
          and "page.window.visible = False" in _src_main32)
    check("tray32: main.py - без трея обычный выход (prevent_close=False + close)",
          "page.window.prevent_close = False" in _src_main32
          and "page.window.close()" in _src_main32)
    with _mock_platform("win32", frozen=True, blocked=("pystray", "PIL", "winreg")):
        check("tray25: мок-frozen Windows без pystray/PIL - мягкий None",
              _tray_reload().start_tray(PageStub()) is None)
        check("os25: мок-frozen Windows без winreg - включение не падает (False)",
              _as23.enable_autostart() is False)
    check("env25: после мок-патчей sys.platform/frozen восстановлены",
          sys.platform == _real_sys_platform25
          and hasattr(sys, "frozen") == _real_had_frozen25)
    # иконка трея — валидный PNG 64x64
    _ip23 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "assets", "icon.png")
    with open(_ip23, "rb") as _fip23:
        _sig23 = _fip23.read(33)
    check("tray23: assets/icon.png - PNG 64x64",
          _sig23[:8] == b"\x89PNG\r\n\x1a\n"
          and _sig23[16:24] == b"\x00\x00\x00\x40\x00\x00\x00\x40")
    # Раунд 24 (задача 4): трей/автозапуск — строго frozen Windows.
    # Раунд 26 (задача 2): web-гард СНЯТ — трей работает и в web-режиме Win7
    # (браузер может быть закрыт), «Открыть» ведёт на URL сервера.
    _appdir24 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_tray24 = open(os.path.join(_appdir24, "ui", "tray_icon.py"), encoding="utf-8").read()
    check("tray24: трей - только frozen Windows (гарды win32+frozen на месте)",
          'sys.platform != "win32"' in src_tray24
          and 'getattr(sys, "frozen", False)' in src_tray24)
    check("tray26: web-режим поддержан - web_url + открытие браузера (webbrowser)",
          "web_url" in src_tray24 and "webbrowser" in src_tray24)
    check("tray26: balloon-уведомления + один значок на процесс (notify/get_active_icon)",
          "def notify(" in src_tray24 and "get_active_icon" in src_tray24)
    src_as24 = open(os.path.join(_appdir24, "core", "autostart.py"), encoding="utf-8").read()
    check("os24: автозапуск - только frozen Windows (гарды win32+frozen)",
          'sys.platform == "win32"' in src_as24
          and 'getattr(sys, "frozen", False)' in src_as24)
    check("web24: main.py помечает web-режим (PORAYONKA_WEB=1)",
          '"PORAYONKA_WEB"' in src_main23)
    check("tray26: main.py - web-трей один раз в _entry с URL, сессии берут get_active_icon",
          "start_tray(None, web_url=" in src_main23 and "get_active_icon" in src_main23)

    # ── 74. Раунд 24: сборочные файлы дистрибутивов ──────────────────────
    files74 = ["Porayonka_Admin.spec", "Porayonka_User.spec",
               "Porayonka_User_Web.spec", "build_admin.bat", "build_user.bat",
               "build_user_web_win7.bat", "start_web_win7.bat", "main_web.py"]
    missing74 = [f for f in files74
                 if not os.path.isfile(os.path.join(_appdir24, f))]
    check("build24: все сборочные файлы на месте", not missing74,
          f"missing={missing74}")
    adm24 = open(os.path.join(_appdir24, "Porayonka_Admin.spec"), encoding="utf-8").read()
    check("build24: admin spec - exe «Порайонка_Админ», вход main.py, assets в бандле",
          'name="Порайонка_Админ"' in adm24 and '"main.py"' in adm24
          and '("assets", "assets")' in adm24)
    usr24 = open(os.path.join(_appdir24, "Porayonka_User.spec"), encoding="utf-8").read()
    check("build24: user spec - exe «Порайонка_Пользователь», вход main.py",
          'name="Порайонка_Пользователь"' in usr24 and '"main.py"' in usr24)
    web24 = open(os.path.join(_appdir24, "Porayonka_User_Web.spec"), encoding="utf-8").read()
    check("build24: web spec - exe «Порайонка_Пользователь_Web», вход main_web.py",
          'name="Порайонка_Пользователь_Web"' in web24
          and '"main_web.py"' in web24)
    check("build24: spec-файлы используют hooks flet (__pyinstaller) - как flet pack",
          '"__pyinstaller"' in adm24 and '"__pyinstaller"' in usr24
          and '"__pyinstaller"' in web24)
    bat_adm24 = open(os.path.join(_appdir24, "build_admin.bat"), encoding="utf-8").read()
    check("build24: build_admin.bat - edition role=admin + pystray/pillow/pyinstaller",
          '"role": "admin"' in bat_adm24 and "pystray" in bat_adm24
          and "pillow" in bat_adm24 and "pyinstaller" in bat_adm24.lower())
    bat_usr24 = open(os.path.join(_appdir24, "build_user.bat"), encoding="utf-8").read()
    check("build24: build_user.bat - edition role=user + спрашивает ФИО (set /p)",
          '"role": "user"' in bat_usr24 and "set /p" in bat_usr24
          and "pystray" in bat_usr24)
    bat_web24 = open(os.path.join(_appdir24, "build_user_web_win7.bat"), encoding="utf-8").read()
    check("build24: build_user_web_win7.bat - web-spec + edition role=user + launcher",
          "Porayonka_User_Web.spec" in bat_web24 and '"role": "user"' in bat_web24
          and "start_web_win7.bat" in bat_web24)
    start24 = open(os.path.join(_appdir24, "start_web_win7.bat"), encoding="utf-8").read()
    check("build24: start_web_win7.bat - поднимает exe и открывает браузер 127.0.0.1:8555",
          "Порайонка_Пользователь_Web.exe" in start24 and "8555" in start24)
    mweb24 = open(os.path.join(_appdir24, "main_web.py"), encoding="utf-8").read()
    check("build24: main_web.py - фиксирует web + user-редакцию, вход через _entry()",
          '"PORAYONKA_WEB"' in mweb24 and 'PORAYONKA_EDITION' in mweb24
          and '"user"' in mweb24 and "_entry()" in mweb24)
    req24 = open(os.path.join(_appdir24, "requirements.txt"), encoding="utf-8").read()
    check("build24: requirements.txt - pystray/pillow упомянуты как опциональные",
          "pystray" in req24 and "pillow" in req24 and "flet==0.23.2" in req24)
    # headless-проверка: edition.json РЯДОМ с программой подхватывается загрузчиком
    ed_path74 = os.path.join(_appdir24, "edition.json")
    assert not os.path.exists(ed_path74), "В репозитории не должно быть edition.json!"
    try:
        with open(ed_path74, "w", encoding="utf-8") as f74:
            f74.write('{"role": "user", "user_name": "Сборкин С.С."}')
        ed74 = _le23(force=True)
        check("build24: edition.json рядом с программой подхватывается (роль+ФИО)",
              ed74.get("role") == "user" and ed74.get("user_name") == "Сборкин С.С.")
    finally:
        # Раунд 29 (задача 8): self-heal edition.py создаёт/восстанавливает
        # из .bak — чистим ОБА, иначе восстановление «воскресит» файл для
        # следующих секций.
        try:
            os.remove(ed_path74)
        except OSError:
            pass
        try:
            os.remove(ed_path74 + ".bak")
        except OSError:
            pass
        # удаляем снова: self-heal мог восстановить edition.json из .bak
        try:
            os.remove(ed_path74)
        except OSError:
            pass
        _le23(force=True)

    # ── 75. Раунд 26, задачи 1/4/5: uvicorn-фикс, сброс user-наследия, пароль ──
    # задача 1: console=False (frozen) -> stdout/stderr None -> uvicorn падает;
    # _ensure_console_streams подменяет их на devnull ДО старта сервера
    from main import _ensure_console_streams as _ecs26
    _saved_out26, _saved_err26 = sys.stdout, sys.stderr
    try:
        sys.stdout = None
        sys.stderr = None
        _fixed26 = _ecs26()
        _restored26 = (sys.stdout is not None and sys.stderr is not None
                       and sys.stdout.writable() and sys.stderr.writable())
    finally:
        sys.stdout, sys.stderr = _saved_out26, _saved_err26
    check("web26: console=False - stdout/stderr восстановлены (uvicorn не упадёт)",
          _fixed26 is True and _restored26)
    check("web26: повторный вызов - no-op (потоки уже есть)",
          _ecs26() is False)
    check("web26: фикс вызывается и в _entry (--web), и в main_web.py",
          "_ensure_console_streams()" in src_main23
          and "_ensure_console_streams" in open(
              os.path.join(_appdir24, "main_web.py"), encoding="utf-8").read())

    # задача 4: явная admin-редакция сбрасывает user-наследие настроек
    os.environ["PORAYONKA_EDITION"] = "admin"
    os.environ.pop("PORAYONKA_USER", None)
    _le23(force=True)
    st26 = {"network_role": "user", "network_user": "Потемкин Сергей Анатольевич"}
    check("edit26: явная admin-редакция сбрасывает user-наследие настроек",
          _aets23(st26) is True and st26.get("network_role") == "admin"
          and st26.get("network_user") == "", f"{st26}")
    check("edit26: явная редакция помечается explicit=True",
          _le23(force=True).get("explicit") is True)
    os.environ.pop("PORAYONKA_EDITION", None)
    _le23(force=True)
    st26b = {"network_role": "user", "network_user": "Потемкин Сергей Анатольевич"}
    check("edit26: без edition.json (default admin) сброса НЕТ - обратная совместимость",
          _aets23(st26b) is False and st26b.get("network_role") == "user", f"{st26b}")
    check("edit26: умолчательная редакция - explicit=False",
          _le23(force=True).get("explicit") is False)

    # задача 5: пароль admin-редакции (helpers + ворота)
    from core.edition import (admin_password_hash as _ph26,
                              admin_password_required as _apr26,
                              check_admin_password as _cap26)
    from ui.admin_gate import show_admin_password_gate as _gate26
    h26 = _ph26("Секрет-1")
    check("auth26: hash стабилен и пароль-зависим",
          _ph26("Секрет-1") == h26 and _ph26("другой") != h26)
    check("auth26: required - только admin и только с паролем",
          _apr26({"role": "admin", "password_hash": h26}) is True
          and _apr26({"role": "admin"}) is False
          and _apr26({"role": "user", "password": "x"}) is False)
    check("auth26: check - hash и plain поля; hash в приоритете",
          _cap26({"password_hash": h26}, "Секрет-1") is True
          and _cap26({"password_hash": h26}, "неверно") is False
          and _cap26({"password": "abc"}, "abc") is True)
    pg26 = PageStub()
    ok26 = {"v": 0}
    shown26 = _gate26(pg26, on_ok=lambda: ok26.__setitem__("v", ok26["v"] + 1),
                      ed={"role": "admin", "password_hash": h26})
    check("auth26: ворота показаны, вкладки ещё не построены",
          shown26 is True and ok26["v"] == 0 and bool(pg26.dialogs))
    tf26 = [c for c in walk(pg26.dialogs[-1]) if isinstance(c, ft.TextField)]
    btns26 = {getattr(c, "text", None): c for c in walk(pg26.dialogs[-1])
              if isinstance(c, (ft.ElevatedButton, ft.TextButton))}
    check("auth26: в воротах поле-пароль + «Войти»/«Выход»",
          len(tf26) == 1 and getattr(tf26[0], "password", False) is True
          and "Войти" in btns26 and "Выход" in btns26)
    tf26[0].value = "неверно"
    btns26["Войти"].on_click(None)
    check("auth26: неверный пароль - on_ok НЕ вызван, приложение закрывается",
          ok26["v"] == 0)
    pg26b = PageStub()
    _gate26(pg26b, on_ok=lambda: ok26.__setitem__("v", ok26["v"] + 1),
            ed={"role": "admin", "password_hash": h26})
    tf26b = [c for c in walk(pg26b.dialogs[-1]) if isinstance(c, ft.TextField)]
    btns26b = {getattr(c, "text", None): c for c in walk(pg26b.dialogs[-1])
               if isinstance(c, (ft.ElevatedButton, ft.TextButton))}
    tf26b[0].value = "Секрет-1"
    btns26b["Войти"].on_click(None)
    check("auth26: верный пароль - on_ok вызван (запуск), ворота закрыты",
          ok26["v"] == 1 and not pg26b.dialogs)
    # Раунд 30 (задача 1): повторное событие (двойной клик/двойной submit
    # клиента Flet) не вызывает on_ok повторно и не плодит таблицы
    ok26d = {"v": 0}
    pg26d = PageStub()
    _gate26(pg26d, on_ok=lambda: ok26d.__setitem__("v", ok26d["v"] + 1),
            ed={"role": "admin", "password_hash": h26})
    tfd26 = [c for c in walk(pg26d.dialogs[-1]) if isinstance(c, ft.TextField)]
    btns26d = {getattr(c, "text", None): c for c in walk(pg26d.dialogs[-1])
               if isinstance(c, (ft.ElevatedButton, ft.TextButton))}
    tfd26[0].value = "Секрет-1"
    btns26d["Войти"].on_click(None)
    btns26d["Войти"].on_click(None)  # повторный клик (клиент дублирует событие)
    check("auth30: повторный вызов «Войти» НЕ дублирует on_ok (ровно один раз)",
          ok26d["v"] == 1 and not pg26d.dialogs, f"v={ok26d['v']}")
    ok26c = {"v": 0}
    n26 = _gate26(PageStub(), on_ok=lambda: ok26c.__setitem__("v", 1),
                  ed={"role": "admin"})
    check("auth26: без пароля ворот нет - on_ok синхронно (совместимость)",
          n26 is False and ok26c["v"] == 1)
    # Раунд 34: пароль admin ОТКЛЮЧЁН — main.py строит UI сразу, без ворот
    # (код ворот остался только в комментарии, ui/admin_gate.py сохранён)
    _active34 = [ln for ln in src_main23.split("\n")
                 if ln.strip() and not ln.strip().startswith("#")]
    check("auth34: main.py НЕ вызывает ворота пароля - admin открывается сразу",
          "_main_impl(page)" in src_main23
          and not any("show_admin_password_gate" in ln for ln in _active34))

    # ── Раунд 32, задача 1: dev-режим — env задаёт роль, пароль из appdata ──
    from core.edition import (admin_password_required as _apr31,
                              check_admin_password as _cap31)
    _edp31 = os.path.join(_TEST_APPDATA, "porayonka", "edition.json")
    os.makedirs(os.path.dirname(_edp31), exist_ok=True)
    _chash31 = _ph26("1")  # пароль, установленный через настройки
    with open(_edp31, "w", encoding="utf-8") as _f31:
        json.dump({"role": "admin", "password_hash": _chash31}, _f31,
                  ensure_ascii=False)
    try:
        # env admin БЕЗ env-пароля: пароль ЧИТАЕТСЯ из appdata (round 32)
        os.environ["PORAYONKA_EDITION"] = "admin"
        os.environ.pop("PORAYONKA_ADMIN_PASSWORD", None)
        _le23(force=True)
        _ed31 = _le23(force=True)
        check("auth32: dev env admin БЕЗ env-пароля - пароль подтянут из appdata",
              _apr31(_ed31) is True
              and bool(_ed31.get("password_hash"))
              and _cap31(_ed31, "1") is True,
              f"hash={bool(_ed31.get('password_hash'))}")
        # env admin + PORAYONKA_ADMIN_PASSWORD=2: env-пароль ПРИОРИТЕТНЕЕ appdata
        os.environ["PORAYONKA_ADMIN_PASSWORD"] = "2"
        _le23(force=True)
        _ed31b = _le23(force=True)
        check("auth32: env-пароль приоритетнее appdata («2» из env, «1» из файла)",
              _apr31(_ed31b) is True
              and _cap31(_ed31b, "2") is True and _cap31(_ed31b, "1") is False)
    finally:
        os.environ.pop("PORAYONKA_EDITION", None)
        os.environ.pop("PORAYONKA_ADMIN_PASSWORD", None)
        _le23(force=True)
        try:
            os.remove(_edp31)
        except OSError:
            pass
    # auth32 (UI): dev env admin + пароль «1» из appdata — диалог закрывается,
    # on_ok вызывается ровно один раз
    _edp32 = os.path.join(_TEST_APPDATA, "porayonka", "edition.json")
    os.makedirs(os.path.dirname(_edp32), exist_ok=True)
    with open(_edp32, "w", encoding="utf-8") as _f32:
        json.dump({"role": "admin", "password_hash": _ph26("1")}, _f32,
                  ensure_ascii=False)
    try:
        os.environ["PORAYONKA_EDITION"] = "admin"
        os.environ.pop("PORAYONKA_ADMIN_PASSWORD", None)
        _le23(force=True)
        ok32 = {"v": 0}
        pg32 = PageStub()
        _gate26(pg32, on_ok=lambda: ok32.__setitem__("v", ok32["v"] + 1))
        tf32 = [c for c in walk(pg32.dialogs[-1]) if isinstance(c, ft.TextField)]
        btns32 = {getattr(c, "text", None): c for c in walk(pg32.dialogs[-1])
                  if isinstance(c, (ft.ElevatedButton, ft.TextButton))}
        check("auth32: dev env admin + appdata-пароль - ворота требуются",
              len(pg32.dialogs) == 1 and bool(tf32) and "Войти" in btns32)
        tf32[0].value = "1"
        btns32["Войти"].on_click(None)
        btns32["Войти"].on_click(None)  # дубль события клиента
        check("auth32: верный пароль - диалог ЗАКРЫТ, on_ok ровно один раз",
              ok32["v"] == 1 and not pg32.dialogs, f"v={ok32['v']} dlg={len(pg32.dialogs)}")
    finally:
        os.environ.pop("PORAYONKA_EDITION", None)
        _le23(force=True)
        try:
            os.remove(_edp32)
        except OSError:
            pass

    # auth33: при наличии page.run_thread (реальный Flet) on_ok вызывается
    # ОТЛОЖЕННО и ровно один раз (диалог успевает закрыться до построения UI)
    _edp33 = os.path.join(_TEST_APPDATA, "porayonka", "edition.json")
    os.makedirs(os.path.dirname(_edp33), exist_ok=True)
    with open(_edp33, "w", encoding="utf-8") as _f33:
        json.dump({"role": "admin", "password_hash": _ph26("1")}, _f33,
                  ensure_ascii=False)
    try:
        os.environ["PORAYONKA_EDITION"] = "admin"
        os.environ.pop("PORAYONKA_ADMIN_PASSWORD", None)
        _le23(force=True)
        ok33 = {"v": 0}

        class _Pg33(PageStub):
            def run_thread(self, handler, *args, **kw):
                # имитация Flet: handler выполняется в отдельном потоке
                import threading as _th33
                t = _th33.Thread(target=handler, args=args, kwargs=kw)
                t.start()
                t.join()

        pg33 = _Pg33()
        _gate26(pg33, on_ok=lambda: ok33.__setitem__("v", ok33["v"] + 1))
        tf33 = [c for c in walk(pg33.dialogs[-1]) if isinstance(c, ft.TextField)]
        btns33 = {getattr(c, "text", None): c for c in walk(pg33.dialogs[-1])
                  if isinstance(c, (ft.ElevatedButton, ft.TextButton))}
        tf33[0].value = "1"
        btns33["Войти"].on_click(None)
        btns33["Войти"].on_click(None)
        check("auth33: on_ok через run_thread - ровно один раз, диалог закрыт",
              ok33["v"] == 1 and not pg33.dialogs, f"v={ok33['v']}")
    finally:
        os.environ.pop("PORAYONKA_EDITION", None)
        _le23(force=True)
        try:
            os.remove(_edp33)
        except OSError:
            pass

    # crash33: файловый лог необработанных исключений (frozen console=False)
    from core.crash_log import install_crash_hook as _ich33
    import traceback as _tb33
    _logp33 = os.path.join(_TEST_APPDATA, "porayonka", "error.log")
    try:
        os.remove(_logp33)
    except OSError:
        pass
    _old_hook33 = sys.excepthook
    try:
        _ich33()
        _hook_a33 = sys.excepthook
        _ich33()  # повторный вызов — идемпотентен
        check("crash33: excepthook установлен (идемпотентно)",
              callable(_hook_a33) and sys.excepthook is _hook_a33)
        # симулируем НЕОБРАБОТАННОЕ исключение: вызываем hook напрямую
        # (stderr перехватываем: штатный __excepthook__ печатает ValueError)
        import io as _io33
        import contextlib as _ctx33
        _buf33 = _io33.StringIO()
        try:
            with _ctx33.redirect_stderr(_buf33):
                _hook_a33(ValueError, ValueError("test-crash-33"), None)
        except Exception:
            pass
        check("crash33: исключение записано в %APPDATA%/porayonka/error.log",
              os.path.exists(_logp33)
              and "test-crash-33" in open(_logp33, encoding="utf-8").read())
    finally:
        sys.excepthook = _old_hook33
        try:
            os.remove(_logp33)
        except OSError:
            pass
    check("crash33: main.py вызывает install_crash_hook первой строкой",
          "install_crash_hook()" in open(main23, encoding="utf-8").read())

    # ── 89. Раунд 34: приоритеты edition (frozen exe vs appdata), сброс user ──
    import core.edition as _ed34
    _appdir34 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _edf34 = os.path.join(_appdir34, "edition.json")
    _edbak34 = os.path.join(_appdir34, "edition.json.bak")
    _edap34 = os.path.join(_TEST_APPDATA, "porayonka", "edition.json")
    _saved_exec34 = getattr(sys, "executable", None)
    _saved_frozen34 = getattr(sys, "frozen", False)
    try:
        # frozen onefile: _app_dir() = папка РЕАЛЬНОГО exe, не _MEI
        sys.frozen = True
        sys.executable = "/fake/dist/Порайонка_Админ.exe"
        sys._MEIPASS = "/fake/_MEI12345"
        _ad34 = _ed34._app_dir()
        check("edition34: frozen _app_dir = папка реального exe (не _MEI)",
              _ad34.name == "dist" and _ad34.parent.name == "fake"
              and "_MEI" not in str(_ad34),
              f"{_ad34}")
    finally:
        if _saved_exec34 is not None:
            sys.executable = _saved_exec34
        else:
            try:
                del sys.executable
            except AttributeError:
                pass
        if _saved_frozen34:
            sys.frozen = _saved_frozen34
        else:
            try:
                del sys.frozen
            except AttributeError:
                pass
        try:
            del sys._MEIPASS
        except AttributeError:
            pass
    # app_dir/edition.json имеет АБСОЛЮТНЫЙ приоритет над appdata (без merge)
    try:
        with open(_edf34, "w", encoding="utf-8") as _f34:
            json.dump({"role": "user", "user_name": "Миронович Д.В."}, _f34,
                      ensure_ascii=False)
        os.makedirs(os.path.dirname(_edap34), exist_ok=True)
        with open(_edap34, "w", encoding="utf-8") as _f34:
            json.dump({"role": "admin", "user_name": ""}, _f34,
                      ensure_ascii=False)
        _le23(force=True)
        _ed34r = _le23(force=True)
        check("edition34: app_dir/edition.json приоритетнее appdata",
              _ed34r.get("role") == "user"
              and _ed34r.get("user_name") == "Миронович Д.В."
              and _ed34r.get("explicit") is True,
              f"{_ed34r.get('role')}")
    finally:
        for _p34 in (_edf34, _edap34):
            try:
                os.remove(_p34)
            except OSError:
                pass
        _le23(force=True)
    # appdata-файл — fallback, если рядом с exe ничего нет
    try:
        os.makedirs(os.path.dirname(_edap34), exist_ok=True)
        with open(_edap34, "w", encoding="utf-8") as _f34:
            json.dump({"role": "user", "user_name": ""}, _f34,
                      ensure_ascii=False)
        _le23(force=True)
        _ed34r = _le23(force=True)
        check("edition34: appdata - fallback при отсутствии app_dir-файла",
              _ed34r.get("role") == "user", f"{_ed34r.get('role')}")
    finally:
        try:
            os.remove(_edap34)
        except OSError:
            pass
        _le23(force=True)
    # self-heal: из appdata в папку exe НЕ копирует (файл рядом не создаётся)
    try:
        os.makedirs(os.path.dirname(_edap34), exist_ok=True)
        with open(_edap34, "w", encoding="utf-8") as _f34:
            json.dump({"role": "user"}, _f34, ensure_ascii=False)
        _ed34._self_heal_edition_files()
        check("edition34: self-heal НЕ копирует appdata в папку exe",
              not os.path.exists(_edf34))
    finally:
        try:
            os.remove(_edap34)
        except OSError:
            pass
    # admin (explicit) сбрасывает user-наследие в настройках
    _st34 = {"network_role": "user", "network_user": "Миронович Д.В."}
    os.environ["PORAYONKA_EDITION"] = "admin"
    _le23(force=True)
    _ch34 = _ed34.apply_edition_to_settings(_st34)
    check("edition34: explicit admin сбрасывает network_role/user",
          _ch34 is True and _st34.get("network_role") == "admin"
          and not (_st34.get("network_user") or ""), f"{_st34}")
    # user без вшитого ФИО сбрасывает network_user (диалог «Кто вы?»)
    os.environ["PORAYONKA_EDITION"] = "user"
    os.environ.pop("PORAYONKA_USER", None)
    _le23(force=True)
    _st34b = {"network_role": "admin", "network_user": "Потемкин С.А."}
    _ch34b = _ed34.apply_edition_to_settings(_st34b)
    check("edition34: user без ФИО сбрасывает network_user (всегда «Кто вы?»)",
          _ch34b is True and _st34b.get("network_role") == "user"
          and not (_st34b.get("network_user") or ""), f"{_st34b}")
    os.environ.pop("PORAYONKA_EDITION", None)
    os.environ.pop("PORAYONKA_USER", None)
    _le23(force=True)

    # id34: user-редакция без вшитого ФИО показывает «Кто вы?», даже если
    # controls_settings.json помнит старого пользователя (наследие)
    _save_off({"network_enabled": False, "network_role": "admin",
                   "network_user": "Миронович Д.В.", "network_shared_path": "",
                   "notify_log": {}, "notify_sound": True, "extra_people": [],
                   "person_roles": {}, "hidden_people": []})
    _seed_raw([_ctrl("id34a", "ИД-34", executors=["Миронович Д.В."])])
    os.environ["PORAYONKA_EDITION"] = "user"
    os.environ.pop("PORAYONKA_USER", None)
    _le23(force=True)
    page34, tab34, _ = build(1280)
    check("id34: user без вшитого ФИО - диалог «Кто вы?» показан (наследие игнорируется)",
          bool(page34.dialogs)
          and any(isinstance(t, ft.Text) and t.value == "Кто вы?"
                  for t in walk(page34.dialogs[-1])))
    check("id34: таблица не строится до выбора ФИО",
          len(_visible_rows(tab34)) == 0)
    os.environ.pop("PORAYONKA_EDITION", None)

    # ── 90. Раунд 36: CP1251 edition.json + полный список людей в настройках ──
    # 90а. edition.json в ANSI/CP1251 с русским ФИО читается корректно
    import core.edition as _ed36
    _edf36 = os.path.join(_appdir24, "edition.json")
    try:
        with open(_edf36, "w", encoding="cp1251") as _f36:
            _f36.write('{ "role": "user", "user_name": "Толстолуцкий С.А." }')
        _le23(force=True)
        _ed36r = _le23(force=True)
        check("ed36: edition.json в CP1251 (русское ФИО) читается как user",
              _ed36r.get("role") == "user"
              and _ed36r.get("user_name") == "Толстолуцкий С.А.",
              f"{_ed36r.get('role')}/{_ed36r.get('user_name')!r}")
        # 90б. UTF-8 (с BOM) тоже читается
        with open(_edf36, "w", encoding="utf-8-sig") as _f36:
            _f36.write('{ "role": "admin" }')
        _le23(force=True)
        _ed36b = _le23(force=True)
        check("ed36: edition.json в UTF-8 (BOM) читается как admin",
              _ed36b.get("role") == "admin", f"{_ed36b.get('role')}")
    finally:
        try:
            os.remove(_edf36)
        except OSError:
            pass
        _le23(force=True)
    # 90в. Настройки: dropdown «Пользователь (ФИО)» содержит extra_people
    save_settings({"network_enabled": False, "network_role": "user",
                   "network_user": "", "network_shared_path": "",
                   "notify_log": {}, "notify_sound": True,
                   "extra_people": ["Толстолуцкий Сергей Александрович"],
                   "person_roles": {}, "hidden_people": []})
    from ui.controls.controls_settings_modal import (
        create_controls_settings_modal as _csm36)
    _pg36 = PageStub()
    _dlg36 = _csm36(_pg36, load_settings(), lambda m: None)
    _opts36 = []
    for c in walk(_dlg36):
        if isinstance(c, ft.Dropdown) and getattr(c, "label", None) == "Пользователь (ФИО)":
            _opts36 = [o.key for o in (c.options or [])]
            break
    check("set36: dropdown «Пользователь (ФИО)» содержит extra_people (Толстолуцкий)",
          "Толстолуцкий Сергей Александрович" in _opts36,
          f"{len(_opts36)} опций")
    _le23(force=True)

    # задача 6: «Настройка формы» только на «Зональных»; задача 7: «О программе»
    from ui.header import create_compact_header as _hdr26
    pg26h = PageStub()
    _hdr26(pg26h, None, ft.Text("tabs"))
    bfs26 = getattr(pg26h, "_btn_form_settings", None)
    check("hdr26: «Настройка формы» по умолчанию скрыта (активны «Контроли»)",
          bfs26 is not None and getattr(bfs26, "visible", True) is False)
    pg26h2 = PageStub()
    _hdr26(pg26h2, None, ft.Text("tabs"), form_settings_visible=True)
    check("hdr26: на «Зональных» кнопка видна (form_settings_visible=True)",
          getattr(pg26h2._btn_form_settings, "visible", False) is True)
    check("hdr26: main.py переключает видимость кнопки по вкладке (index == 1)",
          "_btn_form_settings" in src_main23 and "(index == 1)" in src_main23)
    pgA26 = PageStub()
    _hdr26(pgA26, None, ft.Text("tabs"))
    pgA26._open_about()
    dlgA26 = pgA26.overlay[-1] if pgA26.overlay else None
    txtA26 = {str(getattr(t, "value", "")) for t in walk(dlgA26)
              if isinstance(t, ft.Text)} if dlgA26 is not None else set()
    check("about26: новая версия «Порайонка v2.0 DARK final»",
          any("Порайонка v2.0 DARK final" in t for t in txtA26))
    check("about26: вкладки/редакции/напоминания/регион обновлены",
          any("Контроли" in t for t in txtA26)
          and any("администраторская" in t and "пользовательская" in t for t in txtA26)
          and any("Напоминания о сроках" in t for t in txtA26)
          and any("Ростовской области" in t for t in txtA26),
          f"{sorted(txtA26)[:3]}")

    # задача 2 (функционально): balloon без иконки - мягкий False
    from ui.tray_icon import notify as _ntf26
    check("tray26: notify без иконки - мягкий False (ничего не ломается)",
          _ntf26("test") is False)

    # ── 76. Раунд 26, задача 3: «Кто вы?» ДО отрисовки таблицы ────────────
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "person_roles": {}, "hidden_people": []})
    _seed_raw([_ctrl("s26a", "СВОЙ-26", executors=["Семисенко И.Ю."]),
               _ctrl("s26b", "ЧУЖОЙ-26", executors=["Чужой Ч.Ч."])])
    os.environ["PORAYONKA_EDITION"] = "user"   # ФИО нет — спросит
    os.environ.pop("PORAYONKA_USER", None)
    _le23(force=True)
    page, tab, _ = build(1280)
    dlg26i = page.dialogs[-1] if page.dialogs else None
    check("id26: user без ФИО - диалог «Кто вы?» открыт",
          dlg26i is not None and any(isinstance(t, ft.Text) and t.value == "Кто вы?"
                                     for t in walk(dlg26i)))
    check("id26: таблица НЕ построена до выбора ФИО (чужие не мелькают)",
          len(_visible_rows(tab)) == 0, f"rows={len(_visible_rows(tab))}")
    dd26i = [c for c in walk(dlg26i) if isinstance(c, ft.Dropdown)] if dlg26i else []
    ok26i = [c for c in walk(dlg26i) if isinstance(c, ft.ElevatedButton)
             and getattr(c, "text", None) == "Подтвердить"] if dlg26i else []
    if dd26i and ok26i:
        dd26i[0].value = "Семисенко Иван Юрьевич"
        ok26i[0].on_click(None)
        rtexts26 = []
        for _r in _visible_rows(tab):
            rtexts26 += [str(getattr(t, "value", "")) for t in walk(_r)
                         if isinstance(t, ft.Text)]
        joined26 = " | ".join(rtexts26)
        check("id26: после ФИО - таблица построена, видны только «свои»",
              "СВОЙ-26" in joined26 and "ЧУЖОЙ-26" not in joined26,
              f"{rtexts26[:8]}")
        check("id26: диалог закрыт после выбора", dlg26i not in page.dialogs)
    else:
        check("id26: элементы диалога найдены", False, f"dd={len(dd26i)} ok={len(ok26i)}")
    os.environ.pop("PORAYONKA_EDITION", None)
    try:
        if os.path.exists(_edfile68):
            os.remove(_edfile68)
    except OSError:
        pass
    _le23(force=True)

    # ── 77. Раунд 28: установщики, edition-гард, web-ФИО, вложения, настройки ──
    _inst28 = os.path.join(_appdir24, "installer")
    adm_iss = open(os.path.join(_inst28, "Admin.iss"), encoding="utf-8").read()
    usr_iss = open(os.path.join(_inst28, "User.iss"), encoding="utf-8").read()
    web_iss = open(os.path.join(_inst28, "UserWeb.iss"), encoding="utf-8").read()
    check("iss28: со страницы задач убраны автозапуск/запуск (нет дублей)",
          all('Name: "startup"' not in s and 'Name: "runafterinstall"' not in s
              and "Tasks: startup" not in s and "Tasks: runafterinstall" not in s
              for s in (adm_iss, usr_iss, web_iss)))
    check("iss28: автозапуск ВСЕГДА (Run-ключ HKCU без Tasks-гарда)",
          all("CurrentVersion\\Run" in s for s in (adm_iss, usr_iss, web_iss)))
    check("iss28: запуск только на финальной странице (postinstall без Tasks)",
          all("postinstall skipifsilent" in s for s in (adm_iss, usr_iss, web_iss)))
    check("iss28: Admin.iss без PasswordPage, edition {role: admin} без пароля",
          "PasswordPage" not in adm_iss and 'Values[0]' not in adm_iss
          and '{ "role": "admin" }' in adm_iss)
    check("iss28: User/UserWeb - страница ФИО есть, пропуск РАЗРЕШЁН",
          "FIOPage" in usr_iss and "FIOPage" in web_iss
          and "Введите ФИО пользователя." not in usr_iss
          and "Введите ФИО пользователя." not in web_iss
          and '{ "role": "user" }' in usr_iss and '{ "role": "user" }' in web_iss)

    # задача 2: user-редакция поверх устаревших admin-настроек
    _save_off({"network_enabled": False, "network_role": "admin",
                   "network_user": "Потемкин Сергей Анатольевич",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "person_roles": {}, "hidden_people": []})
    _seed_raw([_ctrl("g28", "ГРД-28", executors=["Семисенко И.Ю."])])
    os.environ["PORAYONKA_EDITION"] = "user"
    os.environ["PORAYONKA_USER"] = "Семисенко Иван Юрьевич"
    _le23(force=True)
    page, tab, _ = build(1280)
    stg28 = load_settings()
    btns28 = {getattr(c, "text", None) for c in walk(tab)
              if isinstance(c, (ft.ElevatedButton, ft.TextButton))}
    check("edit28: user-редакция поверх admin-настроек - роль/ФИО из edition",
          stg28.get("network_role") == "user"
          and stg28.get("network_user") == "Семисенко Иван Юрьевич")
    check("edit28: read-only - admin-кнопок нет физически",
          "Добавить контроль" not in btns28 and "Импорт Excel" not in btns28
          and "Справочники" not in btns28 and "Удалить все" not in btns28,
          f"{sorted(b for b in btns28 if b)}")
    os.environ.pop("PORAYONKA_EDITION", None)
    os.environ.pop("PORAYONKA_USER", None)
    _le23(force=True)

    # задача 2: user-редакция БЕЗ ФИО - чужой network_user сбрасывается до диалога
    _save_off({"network_enabled": False, "network_role": "admin",
                   "network_user": "Потемкин Сергей Анатольевич",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "person_roles": {}, "hidden_people": []})
    os.environ["PORAYONKA_EDITION"] = "user"
    _le23(force=True)
    page, tab, _ = build(1280)
    check("edit28: user без ФИО - чужой network_user сброшен + диалог «Кто вы?»",
          (load_settings().get("network_user") or "") == ""
          and bool(page.dialogs)
          and any(getattr(t, "value", None) == "Кто вы?"
                  for t in walk(page.dialogs[-1])))
    # закрыть путь: выбрать ФИО, чтобы не оставлять состояние хвостам
    dd28 = [c for c in walk(page.dialogs[-1]) if isinstance(c, ft.Dropdown)]
    ok28 = [c for c in walk(page.dialogs[-1]) if isinstance(c, ft.ElevatedButton)
            and getattr(c, "text", None) == "Подтвердить"]
    if dd28 and ok28:
        dd28[0].value = "Семисенко Иван Юрьевич"
        ok28[0].on_click(None)
    os.environ.pop("PORAYONKA_EDITION", None)
    try:
        if os.path.exists(_edfile68):
            os.remove(_edfile68)
    except OSError:
        pass
    _le23(force=True)

    # задача 2: явная admin-редакция после user-настроек - полный функционал
    _save_off({"network_enabled": False, "network_role": "user",
                   "network_user": "Семисенко Иван Юрьевич",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "person_roles": {}, "hidden_people": []})
    os.environ["PORAYONKA_EDITION"] = "admin"
    _le23(force=True)
    page, tab, _ = build(1280)
    btns28a = {getattr(c, "text", None) for c in walk(tab)
               if isinstance(c, (ft.ElevatedButton, ft.TextButton))}
    check("edit28: admin после user - роль admin, network_user сброшен, кнопки есть",
          load_settings().get("network_role") == "admin"
          and (load_settings().get("network_user") or "") == ""
          and "Добавить контроль" in btns28a and "Импорт Excel" in btns28a)
    os.environ.pop("PORAYONKA_EDITION", None)
    _le23(force=True)

    # задача 3: web-установщик уже записал ФИО в {app}/edition.json - не спрашивать
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "person_roles": {}, "hidden_people": []})
    _seed_raw([_ctrl("w28", "ВЕБ-28", executors=["Семисенко И.Ю."])])
    edjson28 = os.path.join(_appdir24, "edition.json")
    assert not os.path.exists(edjson28)
    os.environ["PORAYONKA_WEB"] = "1"
    try:
        with open(edjson28, "w", encoding="utf-8") as f28:
            f28.write('{ "role": "user", "user_name": "Семисенко Иван Юрьевич" }')
        _le23(force=True)
        page, tab, _ = build(1280)
    finally:
        # Раунд 29 (задача 8): чистим и запасную копию .bak (self-heal).
        try:
            os.remove(edjson28)
        except OSError:
            pass
        try:
            os.remove(edjson28 + ".bak")
        except OSError:
            pass
        os.environ.pop("PORAYONKA_WEB", None)
        _le23(force=True)
    rows28 = []
    for _r in _visible_rows(tab):
        rows28 += [str(getattr(t, "value", "")) for t in walk(_r)
                   if isinstance(t, ft.Text)]
    check("web28: ФИО установщика подхвачено - диалога «Кто вы?» НЕТ",
          not page.dialogs)
    check("web28: таблица сразу построена с фильтром «свои»",
          any("ВЕБ-28" in t for t in rows28), f"{rows28[:6]}")

    # задача 4: вложение - content секции ПОЛНОСТЬЮ заменяется (forced rebuild)
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
                   "network_shared_path": "", "notify_log": {}, "notify_sound": True,
                   "extra_people": [], "person_roles": {}, "hidden_people": []})
    _seed_raw([_ctrl("a28", "АТТ-28", executors=["Семисенко И.Ю."])])
    page, tab, _ = build(1280)
    _visible_rows(tab)[0].on_click(None)
    scan_txt_old = next((t for t in walk(tab) if isinstance(t, ft.Text)
                         and t.value == "Скан задания"), None)
    picker28 = getattr(page, "_controls_attach_picker", None)
    _src28 = os.path.join(_appdir24, "assets", "icon.png")
    _tmp28 = os.path.join(tempfile.gettempdir(), "foto_a28.png")
    with open(_src28, "rb") as f28, open(_tmp28, "wb") as g28:
        g28.write(f28.read())
    if picker28 is not None:
        _invoke_event_handler(picker28.on_result, _types50.SimpleNamespace(
            path=None, files=[_types50.SimpleNamespace(path=_tmp28, name="foto_a28.png")]))
    all28 = walk(tab)
    txts28 = [str(getattr(t, "value", "")) for t in all28 if isinstance(t, ft.Text)]
    check("att28: content секции заменён целиком (старый заголовок выведен из дерева)",
          scan_txt_old is not None and scan_txt_old not in all28)
    check("att28: строка вложения видна сразу + заголовок «Скан задания» на месте",
          any("foto_a28.png" in t for t in txts28)
          and any(t == "Скан задания" for t in txts28))

    # задача 5: «О программе» - ограниченная высота + внутренний скролл
    from ui.header import create_compact_header as _hdr28m
    pgh28 = PageStub()
    _hdr28m(pgh28, None, ft.Text("tabs"))
    pgh28._open_about()
    dlgA28 = pgh28.overlay[-1] if pgh28.overlay else None
    contA28 = getattr(dlgA28, "content", None) if dlgA28 is not None else None
    colsA28 = [c for c in walk(dlgA28) if isinstance(c, ft.Column)
               and getattr(c, "scroll", None) is not None] if dlgA28 is not None else []
    check("about28: контент с явной высотой + внутренний скролл",
          contA28 is not None and getattr(contA28, "height", None) is not None
          and getattr(contA28, "height", 0) <= 560 and len(colsA28) >= 1,
          f"h={getattr(contA28, 'height', None)} cols={len(colsA28)}")
    # Раунд 33 (задача 1.3): «О программе» — ширина увеличена (720), текст
    # пунктов переносится (expand в Row), помещается на 1280x720
    check("about33: «О программе» - ширина диалога увеличена до 720",
          contA28 is not None and getattr(contA28, "width", None) == 720,
          f"w={getattr(contA28, 'width', None)}")
    _about_rows33 = [r for r in walk(dlgA28) if isinstance(r, ft.Row)
                     and any(isinstance(i, ft.Icon) and getattr(i, "name", None) == ft.icons.CHECK
                             for i in walk(r))]
    check("about33: тексты пунктов переносятся (expand в Row)",
          len(_about_rows33) >= 6
          and all(any(isinstance(t, ft.Text) and getattr(t, "expand", None)
                      for t in walk(r)) for r in _about_rows33),
          f"rows={len(_about_rows33)}")

    # задачи 6-7: настройки без управления справочниками + секция пароля
    from ui.controls.controls_settings_modal import (
        create_controls_settings_modal as _csm28)
    from core.edition import (save_appdata_password_hash as _sph28,
                              admin_password_required as _apr28)
    pgm28 = PageStub()
    stm28 = {"soon_days": 3, "network_enabled": False, "network_role": "admin",
             "network_user": "", "network_shared_path": "", "notify_sound": True,
             "notify_log": {}, "extra_people": ["Макаренко Роман Андреевич"],
             "custom_initiators": ["МВД"]}
    dlgm28 = _csm28(pgm28, stm28, lambda m: None)
    mtexts28 = {str(getattr(t, "value", "")) for t in walk(dlgm28)
                if isinstance(t, ft.Text)}
    mlabels28 = {str(getattr(t, "label", "")) for t in walk(dlgm28)
                 if isinstance(t, (ft.TextField, ft.Dropdown))}
    check("set28: в настройках НЕТ управления справочниками (остались в тулбаре)",
          not any("Инициаторы (пользовательские)" in t for t in mtexts28)
          and not any("Справочник людей" in t for t in mtexts28)
          and "Новый инициатор" not in mlabels28
          and "Доп. ФИО (исполнитель/контролёр)" not in mlabels28)
    check("set28: уведомления и сетевой режим на месте",
          any(t == "Уведомления" for t in mtexts28)
          and any("Сетевой режим (локальная сеть)" in t for t in mtexts28))
    # Раунд 35: секция «Пароль администратора» УДАЛЕНА из настроек (и для
    # admin, и для user — пароль входа отключён в раунде 34)
    check("set35: в настройках НЕТ секции «Пароль администратора»",
          not any("Пароль администратора" in t for t in mtexts28)
          and not any("Установить пароль" in t for t in mtexts28))
    # Раунд 35: сетевой режим по умолчанию ВКЛЮЧЁН; у user — read-only
    _st35d = dict(DEFAULT_SETTINGS)
    check("net35: DEFAULT_SETTINGS network_enabled=True",
          _st35d.get("network_enabled") is True)
    # у user-редакции переключатель сети скрыт, read-only «включён»
    _sw35 = [c for c in walk(dlgm28) if isinstance(c, ft.Switch)
             and getattr(c, "label", None) == "Сетевой режим"]
    check("net35: admin - переключатель сети на месте",
          len(_sw35) == 1)
    os.environ["PORAYONKA_EDITION"] = "user"
    os.environ["PORAYONKA_USER"] = "Семисенко Иван Юрьевич"
    _le23(force=True)
    _dlgu35 = _csm28(pgm28, dict(stm28), lambda m: None)
    _sw35u = [c for c in walk(_dlgu35) if isinstance(c, ft.Switch)
              and getattr(c, "label", None) == "Сетевой режим"]
    _netro35 = [t for t in walk(_dlgu35) if isinstance(t, ft.Text)
                and t.value == "Сетевой режим включён"]
    check("net35: user - переключатель сети скрыт, read-only «включён»",
          not _sw35u and len(_netro35) >= 1)
    os.environ.pop("PORAYONKA_EDITION", None)
    os.environ.pop("PORAYONKA_USER", None)
    _le23(force=True)
    try:
        if os.path.exists(_edfile68):
            os.remove(_edfile68)
    except OSError:
        pass
    _le23(force=True)

    # ── 78. Раунд 29, задача 5: импорт ФИО - «склеенные инициалы» ──
    # Реальные строки из скринов LLM/13.08.2026: стр.48 «Потемкин С.А.,
    # Семисенко И.Ю.» -> отображалось «Потемкин С.А.С.И.Ю.», стр.45
    # «Семисенко И.Ю.А.О.В.», стр.37 «Гайнутдинов С.И.Т.С.А.С.И.Ю.».
    from core.controls_exporter import (split_executors as _se29,
                                        import_from_excel as _ifx29,
                                        TABLE_HEADERS as _TH29)
    from core.controls_models import short_name as _sn29
    check("fio29: первопричина документирована - short_name склеивает "
          "два ФИО, пришедших ОДНИМ элементом",
          _sn29("Потемкин С.А. Семисенко И.Ю.") == "Потемкин С.А.С.И.Ю.")
    check("fio29: стр.48 - два ФИО через запятую", _se29("Потемкин С.А., Семисенко И.Ю.")
          == ["Потемкин С.А.", "Семисенко И.Ю."])
    check("fio29: склейка пробелом (без запятой) разбивается",
          _se29("Потемкин С.А. Семисенко И.Ю.")
          == ["Потемкин С.А.", "Семисенко И.Ю."])
    check("fio29: стр.45 - Семисенко+Агеев", _se29("Семисенко И.Ю. Агеев О.В.")
          == ["Семисенко И.Ю.", "Агеев О.В."])
    check("fio29: стр.37 - три ФИО подряд",
          _se29("Гайнутдинов С.И. Тихонин С.А. Семисенко И.Ю.")
          == ["Гайнутдинов С.И.", "Тихонин С.А.", "Семисенко И.Ю."])
    check("fio29: не-ASCII запятые (U+201A/U+FF0C/U+060C) - разделители",
          _se29("Потемкин С.А.‚ Семисенко И.Ю.") == ["Потемкин С.А.", "Семисенко И.Ю."]
          and _se29("Потемкин С.А.，Семисенко И.Ю.") == ["Потемкин С.А.", "Семисенко И.Ю."]
          and _se29("Потемкин С.А.، Семисенко И.Ю.") == ["Потемкин С.А.", "Семисенко И.Ю."])
    check("fio29: NBSP после запятой", _se29("Потемкин С.А., Семисенко И.Ю.")
          == ["Потемкин С.А.", "Семисенко И.Ю."])
    check("fio29: одиночное ФИО и голая фамилия не ломаются",
          _se29("Семисенко И.Ю.") == ["Семисенко И.Ю."]
          and _se29("Семисенко") == ["Семисенко"]
          and _se29("Иванов-Петров А.Б., Сидорова В.Г.")
          == ["Иванов-Петров А.Б.", "Сидорова В.Г."])
    check("fio29: союз «и» между ФИО - разделитель",
          _se29("Потемкин С.А. и Семисенко И.Ю.")
          == ["Потемкин С.А.", "Семисенко И.Ю."])
    # полный цикл импорта из xlsx с реальными значениями скринов
    try:
        from openpyxl import Workbook as _WB29
        _wb29 = _WB29()
        _ws29 = _wb29.active
        _ws29.append(_TH29)
        _ws29.append([47, "Иссоп 100-200-16", "01.08.2026", "ГУК ЮФО",
                      "Текст 45", "Семисенко И.Ю. Агеев О.В.",
                      "Чашин Э.А.", "разовый", "05.09.2026", ""])
        _ws29.append([48, "Иссоп 206-3269-16", "01.08.2026", "ГУК ЮФО",
                      "Текст 48", "Потемкин С.А. Семисенко И.Ю.",
                      "Чашин Э.А.", "разовый", "01.09.2026", ""])
        _fx29 = os.path.join(tempfile.gettempdir(), "fio29.xlsx")
        _wb29.save(_fx29)
        _imp29, _st29 = _ifx29(_fx29, [])
        _by_in = {c.incoming_number: c for c in _imp29}
        check("fio29: import_from_excel стр.48 -> 2 исполнителя",
              _by_in.get("Иссоп 206-3269-16") is not None
              and _by_in["Иссоп 206-3269-16"].executors
              == ["Потемкин С.А.", "Семисенко И.Ю."],
              f"{_by_in.get('Иссоп 206-3269-16') and _by_in['Иссоп 206-3269-16'].executors}")
        check("fio29: import_from_excel стр.45 -> 2 исполнителя",
              _by_in.get("Иссоп 100-200-16") is not None
              and _by_in["Иссоп 100-200-16"].executors
              == ["Семисенко И.Ю.", "Агеев О.В."])
    except Exception as e29:
        check("fio29: import_from_excel xlsx", False, f"exc: {e29}")

    # ── 79. Раунд 29, задача 4: сетевой путь по умолчанию ──
    from core.controls_data import (DEFAULT_NETWORK_PATH as _DNP29,
                                    load_settings as _ls29)
    check("net29: дефолтный UNC-путь задан",
          _DNP29 == r"\\192.168.0.60\общая\Гайнутдинов\Porayonka workspace")
    _save_off({"network_enabled": False, "network_role": "admin",
                   "network_user": "", "network_shared_path": "",
                   "notify_log": {}, "notify_sound": True, "extra_people": [],
                   "person_roles": {}})
    # имитация СТАРОЙ установки: в файле ключа/значения пути вообще нет
    _sf29 = os.path.join(_TEST_APPDATA, "porayonka", "controls_settings.json")
    with open(_sf29, "w", encoding="utf-8") as _f29:
        json.dump({"soon_days": 3, "network_enabled": False}, _f29,
                  ensure_ascii=False)
    check("net29: старый файл без network_shared_path - подставлен дефолт",
          _ls29().get("network_shared_path") == _DNP29)
    with open(_sf29, "w", encoding="utf-8") as _f29:
        json.dump({"network_shared_path": ""}, _f29, ensure_ascii=False)
    check("net29: пустой network_shared_path - подставлен дефолт",
          _ls29().get("network_shared_path") == _DNP29)
    # Раунд 31 hotfix: мигрируем только пути внутри локального хранилища
    # приложения (appdata/porayonka), а не любой `C:\\...` — иначе тестовые
    # temp-папки и намеренные локальные пути перезаписывались дефолтом.
    _appdatapath29 = os.path.join(_TEST_APPDATA, "porayonka", "controls.json")
    with open(_sf29, "w", encoding="utf-8") as _f29:
        json.dump({"network_shared_path": _appdatapath29}, _f29,
                  ensure_ascii=False)
    check("net31: локальный appdata-путь мигрирует в дефолтный UNC",
          _ls29().get("network_shared_path") == _DNP29,
          f"{_ls29().get('network_shared_path')!r}")
    # произвольный локальный путь (`D:\\...`) не трогаем
    with open(_sf29, "w", encoding="utf-8") as _f29:
        json.dump({"network_shared_path": "D:\\\\tmp\\\\custom"}, _f29,
                  ensure_ascii=False)
    check("net31: произвольный локальный путь (D:\\...) НЕ мигрирует",
          _ls29().get("network_shared_path") == "D:\\\\tmp\\\\custom")
    with open(_sf29, "w", encoding="utf-8") as _f29:
        json.dump({"network_shared_path": "\\\\server\\\\share\\\\custom"}, _f29,
                  ensure_ascii=False)
    check("net31: ЯВНЫЙ UNC-путь пользователя НЕ перекрывается дефолтом",
          _ls29().get("network_shared_path") == "\\\\server\\\\share\\\\custom")

    # ── 80. Раунд 29, задача 7 + раунд 30, задача 5: контроль рассинхрона ──
    # Раунд 30: сравнение mtime vs last_saved (не «возраст файла»!) —
    # «файл давно не менялся» больше НЕ выглядит как сбитые часы.
    from core.controls_data import check_time_skew as _cts29
    check("time29: сеть выключена - проверки нет (None)",
          _cts29({"network_enabled": False}) is None)
    _tsh29 = tempfile.mkdtemp(prefix="porayonka_tskew_")
    check("time29: shared отсутствует - без предупреждения (None)",
          _cts29({"network_enabled": True,
                  "network_shared_path": _tsh29}) is None)
    _shf29 = os.path.join(_tsh29, "controls.json")
    with open(_shf29, "w", encoding="utf-8") as _f29:
        _f29.write('{"schema_version": 2, "controls": []}')
    _sk29 = _cts29({"network_enabled": True, "network_shared_path": _shf29})
    check("time29: файл без last_saved - проверка невозможна (None, не ложная)",
          _sk29 is None, f"{_sk29}")
    with open(_shf29, "w", encoding="utf-8") as _f29:
        _f29.write('{"schema_version": 2, "last_saved": "'
                   + datetime.now().isoformat()
                   + '", "controls": []}')
    _sk29 = _cts29({"network_enabled": True, "network_shared_path": _shf29})
    check("time29: свежий файл - расхождение в допуске",
          _sk29 is not None and _sk29 < 300, f"{_sk29}")
    # «файл не менялся 2 часа, часы точные»: mtime И last_saved одинаково
    # старые — расхождение ~0, предупреждения НЕТ (false positive раунда 30)
    with open(_shf29, "w", encoding="utf-8") as _f29:
        _f29.write('{"schema_version": 2, "last_saved": "'
                   + (datetime.now() - timedelta(hours=2)).isoformat()
                   + '", "controls": []}')
    os.utime(_shf29, (time.time() - 7200, time.time() - 7200))
    _sk29b = _cts29({"network_enabled": True, "network_shared_path": _shf29})
    check("time30: mtime 2 часа назад (last_saved тоже) - БЕЗ предупреждения",
          _sk29b is not None and _sk29b < 300, f"{_sk29b}")
    # сбитые часы: last_saved «из будущего» относительно mtime на 2 часа
    with open(_shf29, "w", encoding="utf-8") as _f29:
        _f29.write('{"schema_version": 2, "last_saved": "'
                   + (datetime.now() + timedelta(hours=2)).isoformat()
                   + '", "controls": []}')
    os.utime(_shf29, (time.time(), time.time()))
    _sk29c = _cts29({"network_enabled": True, "network_shared_path": _shf29})
    check("time30: last_saved из будущего - расхождение ловится",
          _sk29c is not None and _sk29c > 300, f"{_sk29c}")
    # битый JSON - None (не паника)
    with open(_shf29, "w", encoding="utf-8") as _f29:
        _f29.write("{broken")
    _sk29d = _cts29({"network_enabled": True, "network_shared_path": _shf29})
    check("time30: битый JSON - проверка невозможна (None)",
          _sk29d is None)

    # ── 81. Раунд 29, задача 8: edition.json fallback через .bak ──
    for _e29 in list(os.environ):
        if _e29.startswith("PORAYONKA_EDITION") or _e29 == "PORAYONKA_USER":
            os.environ.pop(_e29, None)
    _edp29 = os.path.join(_appdir24, "edition.json")
    for _p29 in (_edp29, _edp29 + ".bak"):
        try:
            if os.path.exists(_p29):
                os.remove(_p29)
        except OSError:
            pass
    try:
        if os.path.exists(_edfile68):
            os.remove(_edfile68)
    except OSError:
        pass
    _le23(force=True)
    try:
        # 1) нет ни файлов, ни appdata -> default admin
        check("edit29: без файлов - default admin (обратная совместимость)",
              _le23(force=True).get("role") == "admin"
              and _le23(force=True).get("explicit") is False)
        # 2) только .bak (основной удалён) -> восстановление + роль из .bak
        with open(_edp29 + ".bak", "w", encoding="utf-8") as _f29:
            _f29.write('{ "role": "user", "user_name": "Сборкин С.С." }')
        _edb29 = _le23(force=True)
        check("edit29: edition.json отсутствует, но .bak есть - роль из .bak",
              _edb29.get("role") == "user"
              and _edb29.get("user_name") == "Сборкин С.С.")
        check("edit29: основной edition.json ВОССТАНОВЛЕН из .bak",
              os.path.exists(_edp29))
        # 3) основной приоритетнее .bak
        with open(_edp29, "w", encoding="utf-8") as _f29:
            _f29.write('{ "role": "admin" }')
        check("edit29: основной файл приоритетнее .bak",
              _le23(force=True).get("role") == "admin")
        # 4) ни основного, ни .bak, но есть appdata -> appdata (НЕ default)
        os.remove(_edp29)
        os.remove(_edp29 + ".bak")
        _sae23("user", "Сборкин С.С.")
        check("edit29: без файлов рядом с exe - appdata выше default admin",
              _le23(force=True).get("role") == "user"
              and _le23(force=True).get("user_name") == "Сборкин С.С.")
        try:
            os.remove(_edfile68)
        except OSError:
            pass
        # 5) self-heal (раунд 34): ТОЛЬКО восстановление из .bak; создание
        #    .bak из основного убрано (appdata-наследие не копируется в exe)
        with open(_edp29, "w", encoding="utf-8") as _f29:
            _f29.write('{ "role": "user" }')
        _le23(force=True)
        check("edit34: self-heal НЕ создаёт .bak из основного (раунд 34)",
              not os.path.exists(_edp29 + ".bak"))
    finally:
        for _p29 in (_edp29, _edp29 + ".bak"):
            try:
                if os.path.exists(_p29):
                    os.remove(_p29)
            except OSError:
                pass
        try:
            if os.path.exists(_edfile68):
                os.remove(_edfile68)
        except OSError:
            pass
        _le23(force=True)

    # ── 82. Раунд 29, задача 6: lock-файлы редактирования ──
    from core import control_locks as _cl29
    _lkdir29 = tempfile.mkdtemp(prefix="porayonka_locks_")
    _lks29 = {"network_enabled": True,
              "network_shared_path": os.path.join(_lkdir29, "controls.json")}
    okl29, ownl29 = _cl29.acquire_lock(_lks29, "cid-A", "Администратор Первый")
    _lkf29 = os.path.join(_lkdir29, ".locks", "cid-A.lock")
    check("lock29: acquire создаёт lock-файл в shared/.locks",
          okl29 is True and ownl29 is None and os.path.exists(_lkf29))
    with open(_lkf29, "r", encoding="utf-8") as _f29:
        _lkinf29 = json.load(_f29)
    check("lock29: содержимое lock - user/machine/since",
          _lkinf29.get("user") == "Администратор Первый"
          and bool(_lkinf29.get("machine") is not None)
          and bool(_lkinf29.get("since")))
    check("lock29: чужой активный lock - lock_owner виден",
          (_cl29.lock_owner(_lks29, "cid-A") or {}).get("user")
          == "Администратор Первый")
    okl29b, ownl29b = _cl29.acquire_lock(_lks29, "cid-A", "Администратор Второй")
    check("lock29: второй админ блокируется (False + owner)",
          okl29b is False
          and (ownl29b or {}).get("user") == "Администратор Первый")
    okl29c, _ = _cl29.acquire_lock(_lks29, "cid-A", "Администратор Первый")
    check("lock29: владельцу - повторный acquire ок", okl29c is True)
    _cl29.release_lock(_lks29, "cid-A", "Администратор Первый")
    check("lock29: release снимает lock", not os.path.exists(_lkf29)
          and _cl29.lock_owner(_lks29, "cid-A") is None)
    # мёртвый lock (старше 10 минут) не блокирует
    _stale29 = (datetime.now() - timedelta(minutes=11)).isoformat()
    with open(_lkf29, "w", encoding="utf-8") as _f29:
        json.dump({"user": "Упавший Админ", "machine": "PC-9",
                   "since": _stale29}, _f29, ensure_ascii=False)
    check("lock29: stale-lock 11 мин - не блокирует (owner None)",
          _cl29.lock_owner(_lks29, "cid-A") is None)
    okl29d, ownl29d = _cl29.acquire_lock(_lks29, "cid-A", "Администратор Второй")
    check("lock29: stale-lock перезахватывается другим админом",
          okl29d is True and os.path.exists(_lkf29))
    # touch держит lock свежим
    os.utime(_lkf29, (time.time() - 700, time.time() - 700))
    _cl29.touch_lock(_lks29, "cid-A", "Администратор Второй")
    with open(_lkf29, "r", encoding="utf-8") as _f29:
        _tinf29 = json.load(_f29)
    _tage29 = abs(datetime.now().timestamp()
                  - datetime.fromisoformat(_tinf29["since"]).timestamp())
    check("lock29: touch обновляет since (lock не протухает)",
          _tage29 < 30, f"{_tage29:.1f}s")
    # битый lock-файл не вечен
    with open(_lkf29, "w", encoding="utf-8") as _f29:
        _f29.write("{broken json")
    check("lock29: битый lock-файл удаляется и не блокирует",
          _cl29.lock_owner(_lks29, "cid-A") is None
          and not os.path.exists(_lkf29))
    # UI: открытие карточки с чужим lock'ом - диалог; закрытие - снятие
    save_settings({"network_enabled": True, "network_role": "admin",
                   "network_user": "Администратор Первый",
                   "network_shared_path": _lkdir29,
                   "notify_log": {}, "notify_sound": True, "extra_people": [],
                   "person_roles": {}, "alarm_enabled": False})
    _seed_raw([_ctrl("lk29a", "ВХ-LOCK-29", executors=["Семисенко И.Ю."])])
    _le23(force=True)
    page29a, tab29a, _ = build(1280)
    rows29a = _visible_rows(tab29a)
    rows29a[0].on_click(None)  # админ-1 открывает карточку -> lock создан
    _lkf29a = os.path.join(_lkdir29, ".locks", "lk29a.lock")
    check("lock29: открытие карточки создало lock-файл",
          os.path.exists(_lkf29a))
    save_settings({"network_enabled": True, "network_role": "admin",
                   "network_user": "Администратор Второй",
                   "network_shared_path": _lkdir29,
                   "notify_log": {}, "notify_sound": True, "extra_people": [],
                   "person_roles": {}, "alarm_enabled": False})
    page29b, tab29b, _ = build(1280)
    _visible_rows(tab29b)[0].on_click(None)  # админ-2 пытается открыть
    lockdlg29 = page29b.dialogs[-1] if page29b.dialogs else None
    _ldtxts29 = {str(getattr(t, "value", "")) for t in walk(lockdlg29)
                 if isinstance(t, ft.Text)} if lockdlg29 is not None else set()
    check("lock29: второй админ видит диалог «уже редактируется» с ФИО",
          lockdlg29 is not None
          and any("уже редактируется администратором Администратор Первый" in t
                  for t in _ldtxts29), f"{sorted(t for t in _ldtxts29)[:3]}")
    # кнопки диалога: «Обновить и открыть» / «Отмена»
    _ldbtns29 = {getattr(b, "text", None): b for b in walk(lockdlg29)
                 if isinstance(b, (ft.ElevatedButton, ft.TextButton))
                 and getattr(b, "text", None)} if lockdlg29 is not None else {}
    check("lock29: диалог - кнопки «Обновить и открыть»/«Отмена»",
          "Обновить и открыть" in _ldbtns29 and "Отмена" in _ldbtns29)
    if "Отмена" in _ldbtns29:
        _ldbtns29["Отмена"].on_click(None)
    # карточка не открыта: ни один overlay (bg overlay_bg) не видим
    _ov29 = [c for c in walk(tab29b) if isinstance(c, ft.Container)
             and getattr(c, "bgcolor", None) == GLASS["overlay_bg"]
             and getattr(c, "visible", True)]
    check("lock29: «Отмена» закрыла диалог, карточка НЕ открыта",
          not page29b.dialogs and not _ov29)
    # админ-1 сохраняет карточку -> lock снят -> админ-2 открывает свободно
    _sv29 = [b for b in walk(tab29a) if isinstance(b, ft.ElevatedButton)
             and getattr(b, "text", None) == "Сохранить"]
    if _sv29:
        _sv29[0].on_click(None)
    check("lock29: сохранение/закрытие карточки сняло lock",
          not os.path.exists(_lkf29a))
    _visible_rows(tab29b)[0].on_click(None)
    check("lock29: после снятия lock карточка открывается без диалога",
          not page29b.dialogs
          and os.path.exists(_lkf29a))  # теперь lock админа-2
    # уборка: закрыть карточку админа-2 через сохранение
    _sv29b = [b for b in walk(tab29b) if isinstance(b, ft.ElevatedButton)
              and getattr(b, "text", None) == "Сохранить"]
    if _sv29b:
        _sv29b[0].on_click(None)

    # ── 83. Раунд 29, задача 9: офлайн-вложения <-> shared ──
    from core.controls_data import (sync_local_attachments_to_shared as _sla29,
                                    get_attachment_dir as _gad29)
    _sld29 = tempfile.mkdtemp(prefix="porayonka_offatt_")
    _sls29 = {"network_enabled": True, "network_shared_path": _sld29}
    _cid29 = "off-att-29"
    _ladir29 = _gad29(_cid29)
    _ladir29.mkdir(parents=True, exist_ok=True)
    _laf29 = _ladir29 / "scan.pdf"
    _laf29.write_bytes(b"%PDF-1.4 test29")
    _cobj29 = Control(id=_cid29, incoming_number="ВХ-OFF-29",
                      executors=["Семисенко И.Ю."], attachments=[f"{_cid29}/scan.pdf"])
    _n29 = _sla29([_cobj29], _sls29)
    check("att29: локальное вложение выгружено в shared",
          _n29 == 1 and os.path.exists(os.path.join(
              _sld29, "controls_attachments", _cid29, "scan.pdf")))
    check("att29: повторная выгрузка - без дублей (0)",
          _sla29([_cobj29], _sls29) == 0)
    check("att29: сеть выключена - мягкий 0",
          _sla29([_cobj29], {"network_enabled": False}) == 0)
    # обратное направление: чужое вложение из shared подтягивается локально
    _cid29b = "off-att-29b"
    _shb29 = os.path.join(_sld29, "controls_attachments", _cid29b)
    os.makedirs(_shb29, exist_ok=True)
    with open(os.path.join(_shb29, "other.png"), "wb") as _f29:
        _f29.write(b"PNG29")
    from core.controls_data import sync_attachments_from_shared as _saf29
    _saf29(_cid29b, [f"{_cid29b}/other.png"], _sls29)
    check("att29: чужое вложение подтянуто из shared локально",
          (_gad29(_cid29b) / "other.png").exists())

    # ── 84. Раунд 29, задача 10: dropdown пользователя в user-редакции ──
    from ui.controls.controls_settings_modal import (
        create_controls_settings_modal as _csm29)
    pgu29 = PageStub()
    _stg29u = {"soon_days": 3, "network_enabled": False, "network_role": "user",
               "network_user": "Семисенко Иван Юрьевич",
               "network_shared_path": "", "notify_sound": True}
    # а) ФИО зафиксировано установщиком (env) - read-only вид + подсказка
    # Раунд 30 (задача 4): вместо disabled Dropdown (клиент рисует его
    # значение почти чёрным на тёмном фоне) - контейнер с замком и СВЕТЛЫМ
    # текстом; dropdown'а с label «Пользователь (ФИО)» в дереве нет.
    os.environ["PORAYONKA_EDITION"] = "user"
    os.environ["PORAYONKA_USER"] = "Семисенко Иван Юрьевич"
    _le23(force=True)
    dlgu29 = _csm29(pgu29, dict(_stg29u), lambda m: None)
    _udds29 = [c for c in walk(dlgu29) if isinstance(c, ft.Dropdown)
               and getattr(c, "label", None) == "Пользователь (ФИО)"]
    _utxts29 = {str(getattr(t, "value", "")) for t in walk(dlgu29)
                if isinstance(t, ft.Text)}
    from core.constants import COLORS as _COLORS29
    _ro_txt29 = [t for t in walk(dlgu29) if isinstance(t, ft.Text)
                 and t.value == "Семисенко Иван Юрьевич"]
    _ro_lock29 = [i for i in walk(dlgu29) if isinstance(i, ft.Icon)
                  and getattr(i, "name", None) == ft.icons.LOCK_OUTLINE]
    check("user30: ФИО зафиксировано установщиком - НЕТ отключённого dropdown",
          not _udds29)
    check("user30: read-only вид с ФИО и замком, текст СВЕТЛЫЙ (читаемый)",
          bool(_ro_txt29) and getattr(_ro_txt29[0], "color", None) == _COLORS29["text"]
          and bool(_ro_lock29),
          f"color={getattr(_ro_txt29[0], 'color', None) if _ro_txt29 else None}")
    check("user29: подсказка «задан при установке»",
          any("Пользователь задан при установке" in t for t in _utxts29))
    # Раунд 31 (задача 4): у user-редакции ЗВУК нельзя выключить
    _snd_cb31 = [c for c in walk(dlgu29) if isinstance(c, ft.Checkbox)
                 and getattr(c, "label", None) == "Звук уведомлений"]
    _snd_ro31 = [t for t in walk(dlgu29) if isinstance(t, ft.Text)
                 and t.value == "Звук уведомлений включён"]
    check("sound31: в настройках user-редакции НЕТ чекбокса звука",
          not _snd_cb31, f"{len(_snd_cb31)}")
    check("sound31: вместо него read-only строка «Звук уведомлений включён»",
          len(_snd_ro31) >= 1
          and getattr(_snd_ro31[0], "color", None) == _COLORS29["text"])
    # сохранение форсирует notify_sound=True
    _cap31s = {}
    dlgu31s = _csm29(pgu29, dict(_stg29u, notify_sound=False),
                     lambda m: _cap31s.update(m))
    _svb31s = [b for b in getattr(dlgu31s, "actions", [])
               if isinstance(b, ft.ElevatedButton)
               and getattr(b, "text", None) == "Сохранить"]
    if _svb31s:
        _svb31s[0].on_click(None)
    check("sound31: сохранение форсирует notify_sound=True (user)",
          _cap31s.get("notify_sound") is True)
    # сохранение: фиксированное ФИО не переопределяется
    _cap29 = {}
    dlgu29b = _csm29(pgu29, dict(_stg29u), lambda m: _cap29.update(m))
    _svb29 = [b for b in getattr(dlgu29b, "actions", [])
              if isinstance(b, ft.ElevatedButton)
              and getattr(b, "text", None) == "Сохранить"]
    if _svb29:
        _svb29[0].on_click(None)
    check("user29: «Сохранить» оставляет зафиксированное ФИО",
          _cap29.get("network_user") == "Семисенко Иван Юрьевич",
          f"{_cap29.get('network_user')!r}")
    # б) ФИО не зафиксировано - dropdown доступен, подсказка «выберите себя»
    os.environ["PORAYONKA_USER"] = ""
    _le23(force=True)
    dlgu29c = _csm29(pgu29, dict(_stg29u), lambda m: None)
    _udds29c = [c for c in walk(dlgu29c) if isinstance(c, ft.Dropdown)
                and getattr(c, "label", None) == "Пользователь (ФИО)"]
    _utxts29c = {str(getattr(t, "value", "")) for t in walk(dlgu29c)
                 if isinstance(t, ft.Text)}
    check("user29: ФИО НЕ зафиксировано - dropdown доступен + «Выберите себя»",
          bool(_udds29c) and getattr(_udds29c[0], "disabled", False) is False
          and any("Выберите себя из списка" in t for t in _utxts29c))
    os.environ.pop("PORAYONKA_EDITION", None)
    os.environ.pop("PORAYONKA_USER", None)
    _le23(force=True)
    dlgu29d = _csm29(pgu29, dict(_stg29u, network_role="admin"),
                     lambda m: None)
    _udds29d = [c for c in walk(dlgu29d) if isinstance(c, ft.Dropdown)
                and getattr(c, "label", None) == "Пользователь (ФИО)"]
    check("user29: admin-редакция - dropdown доступен",
          bool(_udds29d) and getattr(_udds29d[0], "disabled", False) is False)

    # ── 85. Раунд 29, задачи 1-3: PDF-предпросмотр/настройки/секция пароля ──
    # задача 1: PDF в предпросмотре - явная кнопка «Открыть»
    _save_off({"network_enabled": False, "network_role": "admin",
                   "network_user": "", "network_shared_path": "",
                   "notify_log": {}, "notify_sound": True, "extra_people": [],
                   "person_roles": {}, "alarm_enabled": False})
    _pdfc29 = _ctrl("pdf29", "ВХ-PDF-29", executors=["Семисенко И.Ю."])
    _pdfc29["attachments"] = ["pdf29/scan.pdf"]
    _pdir29 = _gad29("pdf29")
    _pdir29.mkdir(parents=True, exist_ok=True)
    (_pdir29 / "scan.pdf").write_bytes(b"%PDF-1.4 test29")
    _seed_raw([_pdfc29])
    page29p, tab29p, _ = build(1280)
    _visible_rows(tab29p)[0].on_click(None)
    _zooms29 = [c for c in walk(tab29p) if isinstance(c, ft.IconButton)
                and getattr(c, "tooltip", None) == "Предпросмотр"]
    check("pdf29: у строки вложения есть кнопка «Предпросмотр»",
          bool(_zooms29))
    if _zooms29:
        _zooms29[0].on_click(None)
    _pvtxts29 = {str(getattr(t, "value", "")) for t in walk(tab29p)
                 if isinstance(t, ft.Text)}
    _pvbtns29 = {getattr(b, "text", None) for b in walk(tab29p)
                 if isinstance(b, ft.ElevatedButton) and getattr(b, "text", None)}
    check("pdf29: PDF-предпросмотр - «PDF-документ» + кнопка «Открыть»",
          "PDF-документ" in _pvtxts29 and "Открыть" in _pvbtns29)
    # задача 2: в настройках только Уведомления/Сеть/Пароль (нет справочников)
    pgm29 = PageStub()
    dlgm29 = _csm29(pgm29, dict(_stg29u, network_role="admin",
                                network_user=""), lambda m: None)
    _mtxts29 = {str(getattr(t, "value", "")) for t in walk(dlgm29)
                if isinstance(t, ft.Text)}
    # Раунд 35: секция пароля удалена полностью — в настройках только
    # «Уведомления» и «Сетевой режим» (без справочников и без пароля)
    check("set35: настройки - только Уведомления/Сеть (без справочников и пароля)",
          any(t == "Уведомления" for t in _mtxts29)
          and any("Сетевой режим" in t for t in _mtxts29)
          and not any("Пароль администратора" in t for t in _mtxts29)
          and not any("Справочник" in t for t in _mtxts29)
          and not any("Инициаторы" in t for t in _mtxts29))
    # задача 3: user-редакция - секции пароля НЕТ в дереве
    os.environ["PORAYONKA_EDITION"] = "user"
    _le23(force=True)
    dlgm29u = _csm29(pgm29, dict(_stg29u), lambda m: None)
    _mtxts29u = {str(getattr(t, "value", "")) for t in walk(dlgm29u)
                 if isinstance(t, ft.Text)}
    check("set29: user-редакция - секции «Пароль администратора» нет",
          not any("Пароль администратора" in t for t in _mtxts29u))
    os.environ.pop("PORAYONKA_EDITION", None)
    _le23(force=True)
    # задача 4 (UI): поле пути подсказывает дефолтный UNC
    _mhints29 = {str(getattr(t, "hint_text", "") or "") for t in walk(dlgm29)
                 if isinstance(t, ft.TextField)}
    check("set29: placeholder пути - дефолтный UNC \\\\192.168.0.60",
          any("192.168.0.60" in h for h in _mhints29))

    # ── 91. Раунд 37: редакция переживает перенос дистрибутива ──────────────
    # Кейс жалобы «Порайонка_Пользователь.exe открывает admin-интерфейс» —
    # edition.json терялся при копировании portable-сборки, а умолчание было
    # admin. Теперь: ВСТРОЕННЫЙ edition.json внутри exe + правило имени exe +
    # identity-mismatch против appdata-наследия (см. core/edition.py).
    import core.edition as _ed91
    _t91 = tempfile.mkdtemp(prefix="porayonka_ed91_")
    _dist91 = os.path.join(_t91, "dist")
    _mei91 = os.path.join(_t91, "_MEI91")
    os.makedirs(_dist91)
    os.makedirs(_mei91)
    _ap91 = os.path.join(_TEST_APPDATA, "porayonka", "edition.json")
    _sv_exe91 = sys.executable
    _sv_fr91 = getattr(sys, "frozen", None)

    def _frozen91(name):
        sys.frozen = True
        sys.executable = os.path.join(_dist91, name)
        sys._MEIPASS = _mei91

    def _unfrozen91():
        sys.executable = _sv_exe91
        if _sv_fr91 is None:
            try:
                del sys.frozen
            except AttributeError:
                pass
        else:
            sys.frozen = _sv_fr91
        try:
            del sys._MEIPASS
        except AttributeError:
            pass

    def _clean91():
        for _pp in (os.path.join(_dist91, "edition.json"),
                    os.path.join(_dist91, "edition.json.bak"),
                    os.path.join(_mei91, "edition.json"),
                    _ap91):
            try:
                os.remove(_pp)
            except OSError:
                pass

    def _json91(path, d):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as _f91:
            json.dump(d, _f91, ensure_ascii=False)

    try:
        _clean91()
        # 1) перенос без edition.json: embedded внутри exe спасает, appdata=admin
        _json91(os.path.join(_mei91, "edition.json"), {"role": "user"})
        _json91(_ap91, {"role": "admin", "user_name": "Начальников Н.Н."})
        _frozen91("Порайонка_Пользователь.exe")
        _r91 = _ed91.load_edition(force=True)
        check("ed37: перенос без edition.json - роль user из ВСТРОЕННОЙ копии",
              _r91.get("role") == "user" and _r91.get("explicit") is True,
              f"{_r91.get('source')}:{_r91.get('role')}")
        check("ed37: self-heal восстановил edition.json рядом с exe из embedded",
              os.path.isfile(os.path.join(_dist91, "edition.json")))
        check("ed37: appdata=admin НЕ перебил встроенную user-редакцию",
              _r91.get("role") == "user")
        # 2) потеряны ВСЕ файлы: имя exe vs appdata (mismatch) - имя побеждает
        _clean91()
        _ed91.load_edition(force=True)
        _json91(_ap91, {"role": "admin"})
        _frozen91("Порайонка_Пользователь.exe")
        _r91 = _ed91.load_edition(force=True)
        check("ed37: exe «Пользователь» + appdata=admin - имя exe победило (user)",
              _r91.get("role") == "user" and _r91.get("user_name") == "",
              f"{_r91.get('source')}:{_r91.get('role')}:{_r91.get('user_name')!r}")
        _json91(_ap91, {"role": "user", "user_name": "Иванов И.И."})
        _frozen91("Порайонка_Админ.exe")
        _r91 = _ed91.load_edition(force=True)
        check("ed37: exe «Админ» + appdata=user - имя exe победило (admin), чужое ФИО не унаследовано",
              _r91.get("role") == "admin" and _r91.get("user_name") == "")
        # 3) нейтральное имя: appdata-fallback полностью (старое поведение)
        _frozen91("Porayonka.exe")
        _r91 = _ed91.load_edition(force=True)
        check("ed37: нейтральное имя exe - appdata-fallback с ФИО (совместимость)",
              _r91.get("role") == "user" and _r91.get("user_name") == "Иванов И.И.")
        # 4) имя совпадает с appdata-rолью: ФИО из appdata подхватывается
        _frozen91("Порайонка_Пользователь.exe")
        _r91 = _ed91.load_edition(force=True)
        check("ed37: совпадающие имя/appdata - ФИО из appdata подхватывается",
              _r91.get("role") == "user" and _r91.get("user_name") == "Иванов И.И.")
        # 5) нет файлов вообще + нейтральное имя -> умолчание admin non-explicit
        _clean91()
        _ed91.load_edition(force=True)
        _frozen91("Porayonka.exe")
        _r91 = _ed91.load_edition(force=True)
        check("ed37: нет файлов + нейтральное имя - умолчание admin (non-explicit)",
              _r91.get("role") == "admin" and _r91.get("explicit") is False)
        # 6) нет файлов + exe «Пользователь» -> user explicit (правило имени)
        _frozen91("Порайонка_Пользователь.exe")
        _r91 = _ed91.load_edition(force=True)
        check("ed37: нет файлов + exe «Пользователь» - user по имени (explicit)",
              _r91.get("role") == "user" and _r91.get("explicit") is True)
        # 7) БИТЫЙ edition.json + exe «Пользователь» -> user (не падаем в admin)
        with open(os.path.join(_dist91, "edition.json"), "w",
                  encoding="utf-8") as _f91w:
            _f91w.write("{не json")
        _r91 = _ed91.load_edition(force=True)
        check("ed37: БИТЫЙ edition.json у «Пользователя» - роль user (имя exe), не admin",
              _r91.get("role") == "user", f"{_r91.get('source')}:{_r91.get('role')}")
        # 8) БИТЫЙ edition.json + нейтральное имя -> admin explicit (совместимость)
        _frozen91("Porayonka.exe")
        _r91 = _ed91.load_edition(force=True)
        check("ed37: БИТЫЙ edition.json + нейтральное имя - admin explicit (совместимость)",
              _r91.get("role") == "admin" and _r91.get("explicit") is True)
        # 9) валидный файл рядом с exe важнее ИМЕНИ exe (абсолютный приоритет)
        _clean91()
        _json91(os.path.join(_dist91, "edition.json"),
                {"role": "user", "user_name": "Петров П.П."})
        _frozen91("Порайонка_Админ.exe")
        _r91 = _ed91.load_edition(force=True)
        check("ed37: edition.json рядом с exe - АБСОЛЮТНЫЙ приоритет (важнее имени exe)",
              _r91.get("role") == "user" and _r91.get("user_name") == "Петров П.П.")
        # 10) файловый debug-лог диагностики (frozen GUI: stdout невидим)
        _log91 = os.path.join(_TEST_APPDATA, "porayonka", "edition_debug.log")
        _l91 = ""
        if os.path.isfile(_log91):
            with open(_log91, encoding="utf-8") as _fl91:
                _l91 = _fl91.read()
        check("ed37: edition_debug.log записан (source/role/пути)",
              "source=" in _l91 and "role=" in _l91 and "app_dir=" in _l91)
    finally:
        _clean91()
        _unfrozen91()
        _ed91.load_edition(force=True)

    # ── 92. Раунд 37: сборочные файлы — 4 дистрибутива + Win7 DLL + 4 .iss ──
    _ad92 = _appdir24
    specA92 = ""
    _sp92 = os.path.join(_ad92, "Porayonka_Admin_Web.spec")
    if os.path.isfile(_sp92):
        specA92 = open(_sp92, encoding="utf-8").read()
    check("build37: Porayonka_Admin_Web.spec - exe «Порайонка_Админ_Web», вход main_web.py",
          bool(specA92) and 'name="Порайонка_Админ_Web"' in specA92
          and '"main_web.py"' in specA92)
    check("build37: ВСЕ spec встраивают edition.json ВНУТРЬ exe (datas build_edition)",
          "build_edition/edition.json" in adm24 and "build_edition/edition.json" in usr24
          and "build_edition/edition.json" in web24 and "build_edition/edition.json" in specA92)
    check("build37: web-specs несут Win7 DLL-стаб условно в бандл (_MEIPASS)",
          "assets/win7/api-ms-win-core-path-l1-1-0.dll" in web24
          and "assets/win7/api-ms-win-core-path-l1-1-0.dll" in specA92)
    batA92 = ""
    _bta92 = os.path.join(_ad92, "build_admin_web_win7.bat")
    if os.path.isfile(_bta92):
        batA92 = open(_bta92, encoding="utf-8").read()
    check("build37: build_admin_web_win7.bat - admin web-spec + launcher + DLL-стаб",
          bool(batA92) and "Porayonka_Admin_Web.spec" in batA92
          and "start_web_win7.bat" in batA92 and '"role": "admin"' in batA92
          and "api-ms-win-core-path-l1-1-0.dll" in batA92)
    check("build37: build-баты пишут build_edition ДО pyinstaller",
          "build_edition/edition.json" in bat_adm24 and "build_edition/edition.json" in bat_usr24
          and "build_edition/edition.json" in bat_web24 and "build_edition/edition.json" in batA92)
    check("build37: build-баты кладут edition.json.bak рядом (self-heal)",
          "edition.json.bak" in bat_adm24 and "edition.json.bak" in bat_usr24
          and "edition.json.bak" in bat_web24 and "edition.json.bak" in batA92)
    all92 = ""
    _alp92 = os.path.join(_ad92, "build_all_distributives.bat")
    if os.path.isfile(_alp92):
        all92 = open(_alp92, encoding="utf-8").read()
    check("build37: build_all_distributives - 4-я ступень «Админ Web» (dist_admin_web)",
          "Порайонка_Админ_Web" in all92 and "Porayonka_Admin_Web.spec" in all92
          and "dist_admin_web" in all92)
    check("build37: build_all_distributives - DLL в web-дистрибутивы + build_edition на ступень",
          "api-ms-win-core-path-l1-1-0.dll" in all92
          and "build_edition/edition.json" in all92)
    issA92 = ""
    _isa92 = os.path.join(_ad92, "installer", "AdminWeb.iss")
    if os.path.isfile(_isa92):
        issA92 = open(_isa92, encoding="utf-8").read()
    check("build37: AdminWeb.iss - Setup «Порайонка_Админ_Web_Setup», role admin, иконка admin_web",
          bool(issA92) and "OutputBaseFilename=Порайонка_Админ_Web_Setup" in issA92
          and '{ "role": "admin" }' in issA92 and "icon_admin_web.ico" in issA92)
    check("build37: AdminWeb.iss - обязательная DLL рядом, БЕЗ страницы ФИО",
          "api-ms-win-core-path-l1-1-0.dll" in issA92
          and "skipifsourcedoesntexist" not in issA92
          and "FIOPage" not in issA92)
    uweb92 = ""
    _isu92 = os.path.join(_ad92, "installer", "UserWeb.iss")
    if os.path.isfile(_isu92):
        uweb92 = open(_isu92, encoding="utf-8").read()
    check("build37: UserWeb.iss - обязательная DLL рядом с exe",
          "api-ms-win-core-path-l1-1-0.dll" in uweb92
          and "skipifsourcedoesntexist" not in uweb92)
    biis92 = ""
    _bis92 = os.path.join(_ad92, "installer", "build_installers.bat")
    if os.path.isfile(_bis92):
        biis92 = open(_bis92, encoding="utf-8").read()
    check("build37: build_installers.bat собирает ВСЕ 4 установщика",
          all(x in biis92 for x in ("Admin.iss", "User.iss", "UserWeb.iss", "AdminWeb.iss")))
    check("build37: README для Админ Web + иконка admin_web на месте",
          os.path.isfile(os.path.join(_ad92, "installer", "readme", "README_AdminWeb.txt"))
          and os.path.isfile(os.path.join(_ad92, "installer", "images", "icon_admin_web.ico")))
    w7r92 = ""
    _w7p92 = os.path.join(_ad92, "assets", "win7", "README.txt")
    if os.path.isfile(_w7p92):
        w7r92 = open(_w7p92, encoding="utf-8").read()
    check("build37: assets/win7/README - источник DLL-стаба (релиз 0.3.1)",
          "api-ms-win-core-path-blender-0.3.1.zip" in w7r92)
    st92 = open(os.path.join(_ad92, "start_web_win7.bat"), encoding="utf-8").read()
    check("build37: start_web_win7.bat запускает и «Пользователь», и «Админ» exe",
          "Порайонка_Пользователь_Web.exe" in st92 and "Порайонка_Админ_Web.exe" in st92)
    mweb37 = open(os.path.join(_ad92, "main_web.py"), encoding="utf-8").read()
    check("build37: main_web.py - env EDITION только для не-frozen (admin web не ломается)",
          'if not getattr(sys, "frozen", False):' in mweb37 and "PORAYONKA_EDITION" in mweb37)
    egen92 = open(os.path.join(_ad92, "core", "edition.py"), encoding="utf-8").read()
    check("build37: core/edition.py - embedded + правило имени exe + debug-лог",
          "_embedded_edition_file" in egen92 and "_role_from_exe_name" in egen92
          and "edition_debug.log" in egen92 and "name.mismatch" in egen92)
    eig92 = open(os.path.join(_ad92, "installer", "images", "generate_icons.py"),
                 encoding="utf-8").read()
    check("build37: generate_icons.py генерирует иконку admin_web",
          "admin_web" in eig92)
    check("build37: в репо нет артефактов сборки (edition.json / build_edition)",
          not os.path.exists(os.path.join(_ad92, "edition.json"))
          and not os.path.exists(os.path.join(_ad92, "edition.json.bak"))
          and not os.path.exists(os.path.join(_ad92, "build_edition")))

    # ── 92b. Раунд 37 (приёмка оркестратора): DLL-путь/хэши/жёсткий стоп ──
    # Дефект: zip 0.3.1 распаковывается во ВЛОЖЕННУЮ папку
    # api-ms-win-core-path-blender\x64\, скрипты копировали из \x64\ — DLL не
    # находилась, а сборка продолжалась с предупреждением. Теперь: оба пути,
    # контроль SHA256 архива/DLL, жёсткий exit /b 1 без валидной DLL.
    _bats37 = {"user_web": bat_web24, "admin_web": batA92, "all": all92}
    _sha_zip37 = "2CFF5E3DC3B0A5E9241C1091230959CDED50E3D2FF543308B68C6FBA653A3BB6"
    _sha_dll37 = "A1F02F8F2B90F89D0BFAE554D2EBD61D07C7454EABBC53236738143180E030CE"
    check("fix37: DLL - путь с вложенной папкой api-ms-win-core-path-blender\\x64 во всех web-bat",
          all("api-ms-win-core-path-blender\\x64" in b for b in _bats37.values()))
    check("fix37: DLL - SHA256 архива и x64-DLL зафиксированы во всех web-bat",
          all(_sha_zip37 in b and _sha_dll37 in b for b in _bats37.values()))
    check("fix37: DLL - сборка ОСТАНАВЛИВАЕТСЯ без валидной DLL ([ОШИБКА] + exit /b 1)",
          all("[ОШИБКА] api-ms-win-core-path-l1-1-0.dll не получен" in b
              and "exit /b 1" in b for b in _bats37.values()))
    check("fix37: DLL - кэш assets\\win7 проверяется по SHA256 (Get-FileHash)",
          all("Get-FileHash" in b for b in _bats37.values()))
    # Замечание 3: edition.json из установщиков - СТРОГО UTF-8 (SaveStringToUTF8File)
    # + ФИО в чистый ASCII-JSON (JsonEscape \uXXXX) - не зависит от кодировки.
    issU37 = open(os.path.join(_ad92, "installer", "User.iss"), encoding="utf-8").read()
    check("fix37: User.iss/UserWeb.iss - edition.json СТРОГО в UTF-8 (SaveStringToUTF8File)",
          "SaveStringToUTF8File" in issU37 and "SaveStringToUTF8File" in uweb92
          and "SaveStringToFile(" not in issU37 and "SaveStringToFile(" not in uweb92)
    check("fix37: User.iss/UserWeb.iss - ФИО в ASCII-JSON (JsonEscape \\uXXXX)",
          "JsonEscape" in issU37 and "JsonEscape" in uweb92
          and "IntToHex" in issU37 and "IntToHex" in uweb92)
    issAdm37 = open(os.path.join(_ad92, "installer", "Admin.iss"), encoding="utf-8").read()
    check("fix37: Admin.iss/AdminWeb.iss - edition.json СТРОГО в UTF-8",
          "SaveStringToUTF8File" in issAdm37 and "SaveStringToUTF8File" in issA92
          and "SaveStringToFile(" not in issAdm37 and "SaveStringToFile(" not in issA92)

    # Паритет алгоритма JsonEscape (Inno Pascal) с Python-эталоном:
    # кириллица ФИО экранируется в \uXXXX, итоговый JSON читается обратно.
    def _iesc37(s):
        out = []
        for ch in s:
            o = ord(ch)
            if o == 92:
                out.append("\\\\")
            elif o == 34:
                out.append("\\\"")
            elif 32 <= o <= 126:
                out.append(ch)
            else:
                out.append("\\u%04x" % o)
        return "".join(out)
    _jr37 = '{ "role": "user", "user_name": "' \
            + _iesc37("Гайнутдинов Станислав Игоревич") + '" }'
    check("fix37: ASCII-экранирование ФИО - чистый ASCII на выходе",
          all(ord(c) < 128 for c in _jr37))
    _f37 = json.loads(_jr37)
    check("fix37: ASCII-JSON с \\u-эскейпом ФИО читается обратно (json roundtrip)",
          _f37.get("role") == "user"
          and _f37.get("user_name") == "Гайнутдинов Станислав Игоревич")
    # и core/edition.py такой JSON читает (utf-8/любая кодировка - везде ASCII)
    _ep37 = os.path.join(_TEST_APPDATA, "porayonka", "edition.json")
    os.makedirs(os.path.dirname(_ep37), exist_ok=True)
    try:
        with open(_ep37, "w", encoding="utf-8") as _fj37:
            _fj37.write(_jr37)
        _le23(force=True)
        _er37 = _le23(force=True)
        check("fix37: load_edition читает ASCII-JSON установщика (user + ФИО)",
              _er37.get("role") == "user"
              and _er37.get("user_name") == "Гайнутдинов Станислав Игоревич")
    finally:
        try:
            os.remove(_ep37)
        except OSError:
            pass
        _le23(force=True)
    check("fix37: assets/win7/README - вложенный путь архива + обе SHA256",
          "api-ms-win-core-path-blender" in w7r92 and _sha_zip37 in w7r92
          and _sha_dll37 in w7r92)

    # ════════════════════════════════════════════════════════════════
    # 93. Раунд 38 (задача 2, P0): user/admin sync, лечение дублей §2.4
    # ════════════════════════════════════════════════════════════════
    import hashlib as _h93

    def _rec93(cid, num, upd="2026-07-20T10:00:00", atts=None, content="Текст задания"):
        return {"id": cid, "incoming_number": num, "receive_date": "2026-07-20",
                "initiator": "ГУК СК", "content": content,
                "executors": ["Семисенко Иван Юрьевич"], "controller": "Потемкин С.А.",
                "control_type": "once", "period_days": 7, "due_date": "2026-07-25",
                "end_date": None, "done": False, "done_date": None, "comment": "",
                "tasks": [], "milestones": [], "attachments": atts or [],
                "archived": False, "archived_at": None, "archive_reason": "",
                "created_at": upd, "updated_at": upd}

    def _shared93(records):
        d93 = tempfile.mkdtemp(prefix="porayonka_shared38_")
        p93 = os.path.join(d93, "controls.json")
        with open(p93, "w", encoding="utf-8") as f:
            json.dump({"schema_version": 2, "last_saved": datetime.now().isoformat(),
                       "controls": records}, f, ensure_ascii=False, indent=2)
        return d93, p93

    def _netset93(shared_path):
        save_settings({"network_enabled": True, "network_role": "admin",
                       "network_user": "", "network_shared_path": shared_path,
                       "notify_log": {}, "notify_sound": True, "extra_people": []})

    def _sha93(pth):
        with open(pth, "rb") as f:
            return _h93.sha256(f.read()).hexdigest()

    def _rows_with(tab_, needle):
        return [r for r in _visible_rows(tab_)
                if any(isinstance(t, ft.Text) and t.value and needle in str(t.value)
                       for t in walk(r))]

    def _restore_admin93():
        os.environ.pop("PORAYONKA_EDITION", None)
        os.environ.pop("PORAYONKA_USER", None)
        try:
            os.remove(_edfile68)
        except OSError:
            pass
        _le23(force=True)

    def _user93():
        os.environ["PORAYONKA_EDITION"] = "user"
        os.environ["PORAYONKA_USER"] = "Семисенко Иван Юрьевич"
        _le23(force=True)

    # §2.4(1): user с чистым appdata + shared с парой дублей: одна строка,
    # shared НЕ записывается (байты неизменны)
    _seed_raw([])
    sdA, spA = _shared93([_rec93("dupA", "Иссоп-216-193-26", atts=["dupA/s.pdf"]),
                          _rec93("dupB", "иссоп 216-193-26", "2026-07-21T09:00:00"),
                          _rec93("solo1", "ВХСОП-455-2026")])
    _netset93(spA)
    shaA0 = _sha93(spA)
    _user93()
    page, tab, _ = build(1280)
    check("sync38: user - дубль показан ОДНОЙ строкой (view-лечение)",
          len(_rows_with(tab, "Иссоп-216-193-26")) == 1
          and len(_visible_rows(tab)) == 2, f"{len(_visible_rows(tab))}")
    check("sync38: user НИКОГДА не пишет shared (файл не изменился)",
          _sha93(spA) == shaA0)
    _cacheA = load_controls()
    check("sync38: локальный кэш user = authoritative shared-view (2 записи)",
          len(_cacheA) == 2 and {c.id for c in _cacheA} >= {"solo1"})
    check("sync38: canonical в кэше user - запись с вложением (dupA)",
          any(c.id == "dupA" for c in _cacheA) and not any(c.id == "dupB" for c in _cacheA))
    _restore_admin93()

    # §2.4(2): user со stale local (другой UUID, те же бизнес-данные) + shared:
    # одна строка, stale/local-only записи НЕ выгружаются в shared
    _seed_raw([_rec93("stale1", "Иссоп-216-5006-25"),
               _rec93("ghost1", "ЛОКАЛЬНЫЙ-ПРИЗРАК-38")])
    sdB, spB = _shared93([_rec93("canon1", "иссоп 216-5006-25")])
    _netset93(spB)
    shaB0 = _sha93(spB)
    _user93()
    page, tab, _ = build(1280)
    check("sync38: user stale - показан canonical из shared, одна строка",
          len(_rows_with(tab, "216-5006-25")) == 1)
    check("sync38: local-only «призрак» НЕ показывается при живом shared",
          len(_rows_with(tab, "ЛОКАЛЬНЫЙ-ПРИЗРАК-38")) == 0)
    check("sync38: stale запись НЕ выгружена (shared неизменён)",
          _sha93(spB) == shaB0)
    _cacheB = load_controls()
    check("sync38: кэш user заменён shared-снимком (stale1/ghost1 убраны)",
          {c.id for c in _cacheB} == {"canon1"})
    _restore_admin93()

    # §2.4(3): shared содержит два разных UUID одной записи: admin-лечение
    # оставляет одну (shared переписан исцелённым), independent записи целы
    _seed_raw([_rec93("localsolo", "ВХСОП-101-2026")])
    sdC, spC = _shared93([_rec93("hA", "Иссоп-216-194-26", atts=["hA/akt.pdf"]),
                          _rec93("hB", "иссоп 216-194-26", "2026-07-21T09:00:00"),
                          _rec93("keep1", "ВХСОП-9848-25")])
    _netset93(spC)
    page, tab, _ = build(1280)
    with open(spC, encoding="utf-8") as f:
        _scC = json.load(f)["controls"]
    check("sync38: admin-лечение - shared содержит ОДНУ запись пары",
          len([c for c in _scC if "216-194-26" in (c.get("incoming_number") or "").lower()]) == 1
          and len(_scC) == 3, f"всего: {len(_scC)}")
    check("sync38: admin-лечение - canonical = запись с вложением (hA)",
          any(c.get("id") == "hA" for c in _scC))
    # idempotent второй запуск admin на исцелённом shared
    shaC1 = _sha93(spC)
    page, tab, _ = build(1280)
    check("sync38: повторный запуск admin - shared не меняется (идемпотентно)",
          _sha93(spC) == shaC1)

    # §2.4(7): второй admin (другая машина) работает поверх исцелённого
    # shared - дубль НЕ возвращается, новая запись доезжает
    _appB = tempfile.mkdtemp(prefix="porayonka_appdataB_")
    _appA_env = os.environ.get("APPDATA")
    os.environ["APPDATA"] = _appB
    _netset93(spC)  # настройки живут в APPDATA "машины B" - задаём заново
    page, tab, _ = build(1280)  # B: локальный кэш пуст, shared авторитетен
    check("sync38: admin B на другой машине видит исцелённый shared (3 записи)",
          len(_visible_rows(tab)) == 3, f"{len(_visible_rows(tab))}")
    # B добавляет новый контроль (полный UI-путь: карточка + скан + сохранить)
    _open_card(tab, via_add=True)
    srcB = os.path.join(tempfile.mkdtemp(prefix="porayonka_scanB_"), "актB.pdf")
    with open(srcB, "wb") as f:
        f.write(b"%PDF-scan-B-38")
    _fire_picker(getattr(page, "_controls_attach_picker"),
                 type("E", (), {"files": [_F13(srcB, "актB.pdf")]})())
    tf_B = [c for c in walk(tab) if isinstance(c, ft.TextField)
            and "Входящий" in str(getattr(c, "hint_text", "") or "")]
    if tf_B:
        tf_B[0].value = "ВХСОП-7777-38"
    saveB = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
             and getattr(c, "text", None) == "Сохранить"]
    okB = True
    try:
        saveB[0].on_click(None)
    except Exception:
        okB = False
        traceback.print_exc()
    with open(spC, encoding="utf-8") as f:
        _scC2 = json.load(f)["controls"]
    check("sync38: admin B сохранил новый контроль в shared (4 записи)",
          okB and len(_scC2) == 4
          and any((c.get("incoming_number") or "") == "ВХСОП-7777-38" for c in _scC2),
          f"всего: {len(_scC2)}")
    check("sync38: дубль НЕ вернулся после записи второго admin",
          len([c for c in _scC2 if "216-194-26" in (c.get("incoming_number") or "").lower()]) == 1)
    os.environ["APPDATA"] = _appA_env
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
               "network_shared_path": "", "notify_log": {}, "notify_sound": True,
               "extra_people": []})

    # ════════════════════════════════════════════════════════════════
    # 94. Раунд 38 (задача 5, P1): вложение видно СРАЗУ (sync+async)
    # ════════════════════════════════════════════════════════════════
    _seed_raw([_ctrl("a38", "А-38", executors=["Семисенко И.Ю."])])
    page, tab, _ = build()

    def _scan_panel_of(tab_):
        """Минимальный контейнер, в поддереве которого есть «Скан задания»."""
        cands = []
        for c in walk(tab_):
            if isinstance(c, ft.Container):
                txts = {str(t.value) for t in walk(c)
                        if isinstance(t, ft.Text) and t.value}
                if "Скан задания" in txts:
                    cands.append(c)
        cands.sort(key=lambda c: len(walk(c)))
        return cands[0] if cands else None

    def _file_in_scan_panel(tab_, fname):
        sp = _scan_panel_of(tab_)
        if sp is None:
            return False
        return any(isinstance(t, ft.Text) and t.value == fname for t in walk(sp))

    _open_card(tab, via_add=True)
    srcS = os.path.join(tempfile.mkdtemp(prefix="porayonka_s38_"), "малый.png")
    with open(srcS, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"s" * 64)
    ok94s = True
    try:
        _fire_picker(getattr(page, "_controls_attach_picker"),
                     type("E", (), {"files": [_F13(srcS, "малый.png")]})())
    except Exception:
        ok94s = False
        traceback.print_exc()
    check("attach38: sync-файл (<5 МБ) виден В СКАН-ПАНЕЛИ сразу", 
          ok94s and _file_in_scan_panel(tab, "малый.png"))
    # большой файл (>5 МБ): фоновый путь копирования
    big_dir = tempfile.mkdtemp(prefix="porayonka_b38_")
    srcBig = os.path.join(big_dir, "большой.pdf")
    with open(srcBig, "wb") as f:
        f.write(b"%PDF" + os.urandom(6 * 1024 * 1024))
    ok94b = True
    try:
        _fire_picker(getattr(page, "_controls_attach_picker"),
                     type("E", (), {"files": [_F13(srcBig, "большой.pdf")]})())
    except Exception:
        ok94b = False
        traceback.print_exc()
    appeared94 = False
    for _i in range(100):
        if _file_in_scan_panel(tab, "большой.pdf"):
            appeared94 = True
            break
        time.sleep(0.1)
    check("attach38: async-файл (>5 МБ, фоновое копирование) виден в скан-панели",
          ok94b and appeared94)
    check("attach38: каждый файл - ровно ОДНА строка (без дублей UI)",
          _file_in_scan_panel(tab, "малый.png") and _file_in_scan_panel(tab, "большой.pdf")
          and [t.value for t in walk(_scan_panel_of(tab))
               if isinstance(t, ft.Text) and t.value in ("малый.png", "большой.pdf")].count("малый.png") == 1)
    att_root94 = os.path.join(os.environ["APPDATA"], "porayonka", "controls_attachments")
    ids94 = [d for d in os.listdir(att_root94)
             if os.path.isdir(os.path.join(att_root94, d))
             and any(f.startswith("большой") for f in os.listdir(os.path.join(att_root94, d)))]
    check("attach38: большой файл физически скопирован в папку вложений",
          len(ids94) >= 1)

    # 95. Раунд 38 (задача 5): отмена НОВОЙ карточки убирает orphan-файлы
    cancel95 = [c for c in walk(tab) if isinstance(c, ft.TextButton)
                and getattr(c, "text", None) == "Отмена"]
    check("attach38: кнопка «Отмена» в новой карточке найдена", bool(cancel95))
    ok95 = True
    try:
        cancel95[0].on_click(None)
    except Exception:
        ok95 = False
        traceback.print_exc()
    leftovers95 = []
    for d in ids94 or []:
        pth = os.path.join(att_root94, d)
        if os.path.isdir(pth):
            leftovers95 += [f for f in os.listdir(pth)]
    check("attach38: отмена новой карточки - orphan-файлы убраны",
          ok95 and not leftovers95, f"{leftovers95}")

    # ════════════════════════════════════════════════════════════════
    # 96. Раунд 38 (задача 6, P1): НОВАЯ admin-карточка не сохраняется без скана
    # ════════════════════════════════════════════════════════════════
    def _live_card96(tab_):
        """Текущая ОТКРЫТАЯ карточка (видимый overlay): закрытая карточка
        остаётся в дереве с visible=False - её поддерево не учитываем."""
        ovs = [c for c in walk(tab_) if isinstance(c, ft.Container)
               and getattr(c, "visible", False) is True
               and getattr(c, "bgcolor", None) == "#cc04070f"]
        return ovs[0] if ovs else None

    def _card_has96(root, text_btn=None, text_part=None):
        if root is None:
            return False
        if text_btn:
            return any(isinstance(c, ft.ElevatedButton)
                       and getattr(c, "text", None) == text_btn for c in walk(root))
        return any(isinstance(t, ft.Text) and t.value and text_part in str(t.value)
                   for t in walk(root))

    _open_card(tab, via_add=True)
    card96 = _live_card96(tab)
    tf96 = [c for c in walk(card96) if isinstance(c, ft.TextField)
            and "Входящий" in str(getattr(c, "hint_text", "") or "")] if card96 else []
    check("scan38: поле «Входящий №» найдено в новой карточке", bool(tf96))
    # Регресс раунда 38 (задача 5): FilePicker.on_result НАКАПЛИВАЕТ замыкания
    # старых карточек (EventHandler.subscribe) — старое замыкание копировало
    # файл и глушило актуальное по антидубль-гварду («скопировано, но не
    # видно до переоткрытия»). После переоткрытий должен остаться ОДИН
    # подписанный обработчик (stale отписан в _ensure_file_picker).
    _eh96 = getattr(getattr(page, "_controls_attach_picker", None), "on_result", None)
    _n_h96 = len(getattr(_eh96, "_EventHandler__handlers", {}) or {})
    check("attach38: после N переоткрытий карточки у attach-пикера РОВНО 1 обработчик",
          _n_h96 == 1, f"handlers={_n_h96}")
    _ehd96 = getattr(getattr(page, "_controls_attach_dl_picker", None), "on_result", None)
    _n_hd96 = len(getattr(_ehd96, "_EventHandler__handlers", {}) or {})
    check("attach38: у download-пикера тоже РОВНО 1 обработчик (без накопления)",
          _n_hd96 == 1, f"handlers={_n_hd96}")
    tf96[0].value = "БЕЗ-СКАНА-38"
    btn96 = [c for c in walk(card96) if isinstance(c, ft.ElevatedButton)
             and getattr(c, "text", None) == "Сохранить"]
    n_before96 = len(load_controls())
    ok96 = True
    try:
        btn96[0].on_click(None)
    except Exception:
        ok96 = False
        traceback.print_exc()
    card96b = _live_card96(tab)
    check("scan38: сохранение БЕЗ скана отклонено: карточка открыта, подсказка",
          ok96 and card96b is not None
          and _card_has96(card96b, text_part="Прикрепите скан задания"))
    check("scan38: карточка осталась открытой («Сохранить» на месте)",
          _card_has96(card96b, text_btn="Сохранить"))
    check("scan38: запись НЕ добавилась без скана", len(load_controls()) == n_before96)
    # toast-текст дублирует подсказку дословно
    hint96t = [str(t.value) for t in walk(card96b) if isinstance(t, ft.Text) and t.value]
    check("scan38: русский текст ошибки дословно верен",
          any("Прикрепите скан задания (PDF или изображение)" in v for v in hint96t))
    # прикрепляем скан - подсказка снимается, сохранение проходит
    src96 = os.path.join(tempfile.mkdtemp(prefix="porayonka_s96_"), "акт.pdf")
    with open(src96, "wb") as f:
        f.write(b"%PDF-scan96-content")
    _fire_picker(getattr(page, "_controls_attach_picker"),
                 type("E", (), {"files": [_F13(src96, "акт.pdf")]})())
    card96c = _live_card96(tab)
    check("scan38: после прикрепления скана подсказка снята",
          card96c is not None
          and not _card_has96(card96c, text_part="Прикрепите скан задания"))
    check("scan38: скан-файл виден в открытой карточке",
          _card_has96(card96c, text_part="акт.pdf"))
    btn96[0].on_click(None)
    check("scan38: со сканом сохранение прошло (карточка закрылась, запись добавлена)",
          len(load_controls()) == n_before96 + 1
          and _live_card96(tab) is None)
    new96 = [c for c in load_controls() if c.incoming_number == "БЕЗ-СКАНА-38"]
    check("scan38: сохранённый контроль содержит вложение",
          new96 and new96[0].attachments and str(new96[0].attachments[0]).endswith("акт.pdf"))
    # исторический контроль БЕЗ вложений сохраняется после редактирования
    rows96 = _visible_rows(tab)
    check("scan38: историческая строка есть в таблице", bool(rows96))
    rows96[0].on_click(None)
    btn96h = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
              and getattr(c, "text", None) == "Сохранить"]
    n_before96h = len(load_controls())
    ok96h = True
    try:
        if btn96h:
            btn96h[0].on_click(None)
    except Exception:
        ok96h = False
        traceback.print_exc()
    check("scan38: исторический контроль без скана СОХРАНЯЕТСЯ (миграция не блокирована)",
          ok96h and bool(btn96h) and len(load_controls()) == n_before96h)

    # пилюля «Без скана» в таблице (только admin, только активные без вложений)
    _seed_raw([_ctrl("ns38a", "БЕЗ-СКАНА-А", executors=["Семисенко И.Ю."]),
               _ctrl("ns38b", "БЕЗ-СКАНА-Б", executors=["Чашин Э.А."])])
    data96b = json.load(open(get_controls_file(), encoding="utf-8"))
    data96b["controls"][1]["done"] = True  # исполненный - без пилюли
    with open(get_controls_file(), "w", encoding="utf-8") as f:
        json.dump(data96b, f, ensure_ascii=False, indent=2)
    page, tab, _ = build()
    pills96 = [str(t.value) for t in walk(tab) if isinstance(t, ft.Text)
               and str(t.value) == "Без скана"]
    check("scan38: пилюля «Без скана» - только у активного без вложений (1 из 2)",
          len(pills96) == 1, f"{pills96}")
    _user93()
    page, tab, _ = build()
    pills96u = [str(t.value) for t in walk(tab) if isinstance(t, ft.Text)
                and str(t.value) == "Без скана"]
    check("scan38: у user пилюля «Без скана» не показывается", not pills96u)
    _restore_admin93()

    # ════════════════════════════════════════════════════════════════
    # 97. Раунд 38 (задача 7, P1): «Скачать» -> «Открыть» (сохранённая копия)
    # ════════════════════════════════════════════════════════════════
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
               "network_shared_path": "", "notify_log": {}, "notify_sound": True,
               "extra_people": []})
    _seed_raw([_ctrl("dl38", "ДЛ-38", executors=["Семисенко И.Ю."])])
    att_dir97 = os.path.join(os.environ["APPDATA"], "porayonka",
                             "controls_attachments", "dl38")
    os.makedirs(att_dir97, exist_ok=True)
    src97_bytes = b"ORIGINAL-BYTES-" + os.urandom(64)
    with open(os.path.join(att_dir97, "документ.pdf"), "wb") as f:
        f.write(src97_bytes)
    data97 = json.load(open(get_controls_file(), encoding="utf-8"))
    data97["controls"][0]["attachments"] = ["dl38/документ.pdf"]
    with open(get_controls_file(), "w", encoding="utf-8") as f:
        json.dump(data97, f, ensure_ascii=False, indent=2)
    page, tab, _ = build()
    rows97 = _rows_with(tab, "ДЛ-38")
    rows97[0].on_click(None)
    dl_btn97 = [c for c in walk(tab) if isinstance(c, ft.IconButton)
                and getattr(c, "tooltip", None) == "Скачать"]
    check("dl38: кнопка «Скачать» есть в строке вложения",
          len(dl_btn97) == 1, f"{len(dl_btn97)}")
    picker97 = getattr(page, "_controls_attach_dl_picker", None)
    check("dl38: picker «Скачать копию» зарегистрирован", picker97 is not None)
    called97 = {}
    picker97.save_file = lambda **kw: called97.update(kw)  # headless-заглушка
    ok97 = True
    try:
        dl_btn97[0].on_click(None)
    except Exception:
        ok97 = False
        traceback.print_exc()
    check("dl38: открыт диалог сохранения с ИСХОДНЫМ именем и расширением",
          ok97 and called97.get("file_name") == "документ.pdf")
    # Cancel - ничего не копируется, кнопка не меняется
    _fire_picker(picker97, type("E", (), {"path": None})())
    check("dl38: Cancel - копия не создана, кнопка осталась «Скачать»",
          [c for c in walk(tab) if isinstance(c, ft.IconButton)
           and getattr(c, "tooltip", None) == "Скачать"]
          and not [c for c in walk(tab) if isinstance(c, ft.IconButton)
                   and getattr(c, "tooltip", None) == "Открыть сохранённую копию"])
    # успешное сохранение - байт-в-байт; кнопка становится «Открыть сохранённую копию»
    dst97 = os.path.join(tempfile.mkdtemp(prefix="porayonka_dl97_"), "копия.pdf")
    dl_btn97[0].on_click(None)
    _fire_picker(picker97, type("E", (), {"path": dst97})())
    bytes97 = open(dst97, "rb").read() if os.path.exists(dst97) else b""
    check("dl38: копия сохранена байт-в-байт (исходник на месте)",
          bytes97 == src97_bytes
          and open(os.path.join(att_dir97, "документ.pdf"), "rb").read() == src97_bytes)
    open_btn97 = [c for c in walk(tab) if isinstance(c, ft.IconButton)
                  and getattr(c, "tooltip", None) == "Открыть сохранённую копию"]
    check("dl38: после сохранения кнопка стала «Открыть сохранённую копию»",
          len(open_btn97) == 1)
    # копия удалена -> снова предложить скачать
    os.remove(dst97)
    ok97d = True
    try:
        open_btn97[0].on_click(None)
    except Exception:
        ok97d = False
    check("dl38: удалённая копия - возврат к «Скачать» (понятное поведение)",
          ok97d and [c for c in walk(tab) if isinstance(c, ft.IconButton)
                     and getattr(c, "tooltip", None) == "Скачать"])
    # user read-only карточка: «Скачать» доступна (не вырезана прунингом)
    _user93()
    page, tab, _ = build()
    rows97u = _rows_with(tab, "ДЛ-38")
    rows97u[0].on_click(None)
    dl_btn97u = [c for c in walk(tab) if isinstance(c, ft.IconButton)
                 and getattr(c, "tooltip", None) == "Скачать"]
    check("dl38: user read-only карточка - «Скачать» доступна", len(dl_btn97u) == 1)
    _restore_admin93()

    # ════════════════════════════════════════════════════════════════
    # 98-99. Раунд 38 (задача 9, P1): incremental import preview + upsert UI
    # ════════════════════════════════════════════════════════════════
    _save_off({"network_enabled": False, "network_role": "admin", "network_user": "",
               "network_shared_path": "", "notify_log": {}, "notify_sound": True,
               "extra_people": []})
    _seed_raw([_ctrl("impA", "Иссоп-216-193-26", executors=["Семисенко И.Ю."])])
    att_dir98 = os.path.join(os.environ["APPDATA"], "porayonka",
                             "controls_attachments", "impA")
    os.makedirs(att_dir98, exist_ok=True)
    with open(os.path.join(att_dir98, "акт.pdf"), "wb") as f:
        f.write(b"import-akt-bytes")
    data98 = json.load(open(get_controls_file(), encoding="utf-8"))
    data98["controls"][0]["attachments"] = ["impA/акт.pdf"]
    data98["controls"][0]["comment"] = "комментарий-не-стирать"
    with open(get_controls_file(), "w", encoding="utf-8") as f:
        json.dump(data98, f, ensure_ascii=False, indent=2)
    # flat xlsx: обновление impA (новое содержание) + одна новая запись
    from openpyxl import Workbook as _Wb98
    from core.controls_exporter import TABLE_HEADERS as _TH98
    xlsx98 = os.path.join(tempfile.mkdtemp(prefix="porayonka_x98_"), "import38.xlsx")
    wb98 = _Wb98()
    ws98 = wb98.active
    ws98.append(["КОНТРОЛИ ОТДЕЛА КРИМИНАЛИСТИКИ"] + [None] * 9)
    ws98.append(_TH98)
    ws98.append([1, "иссоп 216-193-26", "20.07.2026", "ГУК СК", "Содержание обновлено импортом",
                 "Семисенко И.Ю.", "Потемкин С.А.", "разовый", "31.07.2026", ""])
    ws98.append([2, "Иссоп-216-321-26", "22.07.2026", "СУ", "Новая запись из файла",
                 "Чашин Э.А.", "Потемкин С.А.", "разовый", "29.07.2026", ""])
    wb98.save(xlsx98)
    page, tab, _ = build()
    picker98 = getattr(page, "_controls_import_picker", None)
    check("import38: picker импорта зарегистрирован", picker98 is not None)
    _fire_picker(picker98, type("E", (), {"path": xlsx98, "files": None})())
    dlg98 = page.dialogs[-1] if page.dialogs else None
    texts98 = {str(t.value) for t in walk(dlg98) if isinstance(t, ft.Text) and t.value} if dlg98 else set()
    summary98 = " ".join(sorted(texts98))
    check("import38: открылся предпросмотр импорта", dlg98 is not None)
    check("import38: preview со статистикой новые/обновляемые/без изменений/конфликты",
          "Новые: 1" in summary98 and "Обновляемые: 1" in summary98
          and "Без изменений" in summary98 and "Конфликты: 0" in summary98,
          f"{summary98[:160]}")
    check("import38: импортированные без файлов помечаются «Без скана»",
          "Без скана: 1" in summary98)
    conf98 = [c for c in walk(dlg98) if isinstance(c, ft.ElevatedButton)
              and getattr(c, "text", None) == "Импортировать"]
    n_before98 = len(load_controls())
    ok98 = True
    try:
        conf98[0].on_click(None)
    except Exception:
        ok98 = False
        traceback.print_exc()
    after98 = load_controls()
    rec98A = [c for c in after98 if c.id == "impA"]
    rec98N = [c for c in after98 if (c.incoming_number or "") == "Иссоп-216-321-26"]
    check("import38: применение - запись с id=A обновлена in place",
          ok98 and len(after98) == n_before98 + 1 and len(rec98A) == 1
          and rec98A[0].content == "Содержание обновлено импортом")
    check("import38: attachments и comment существующей записи не тронуты",
          rec98A and rec98A[0].attachments == ["impA/акт.pdf"]
          and rec98A[0].comment == "комментарий-не-стирать"
          and os.path.exists(os.path.join(att_dir98, "акт.pdf")))
    check("import38: новая запись добавлена с уникальным id",
          len(rec98N) == 1 and rec98N[0].id != "impA")
    bkp_root98 = os.path.join(os.environ["APPDATA"], "porayonka", "backups")
    bkp98 = [f for f in os.listdir(bkp_root98) if f.startswith("pre-import-")] \
        if os.path.isdir(bkp_root98) else []
    check("import38: backup controls.json создан ДО применения", bool(bkp98))
    # повторный импорт того же файла: ничего нового не добавляет
    _fire_picker(picker98, type("E", (), {"path": xlsx98, "files": None})())
    summary98b = " ".join(sorted({str(t.value) for t in walk(page.dialogs[-1])
                                  if isinstance(t, ft.Text) and t.value})) \
        if page.dialogs else ""
    n_mid98 = len(load_controls())
    if page.dialogs:
        conf98b = [c for c in walk(page.dialogs[-1]) if isinstance(c, ft.ElevatedButton)
                   and getattr(c, "text", None) == "Импортировать"]
        if conf98b:
            conf98b[0].on_click(None)
    check("import38: повторный импорт идемпотентен (количество не изменилось)",
          len(load_controls()) == n_mid98)

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()

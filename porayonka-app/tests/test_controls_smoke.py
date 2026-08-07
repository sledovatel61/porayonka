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

Запуск:  cd porayonka-app && python tests/test_controls_smoke.py
"""
import io
import json
import os
import sys
import tempfile
import contextlib
import traceback

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
    get_criminalists_only, get_controller_names,
)
from core.controls_models import (  # noqa: E402
    Control, OVERDUE, TODAY, name_matches,
)
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
    for attr in ("content", "controls"):
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
        check("контейнер левой колонки width>0", (getattr(lc, "width", 0) or 0) > 0, f"width={lc.width}")
        check("контейнер правой колонки width>0", (getattr(rc, "width", 0) or 0) > 0, f"width={rc.width}")
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

    # ── 7. Hover строки ВЕРНУТ и БЫСТРЫЙ (раунд 6): on_hover меняет рамку на #4f8cff и фон #2c3650 ──
    page, tab, _ = build()
    allc = walk(tab)
    rows = [c for c in allc if isinstance(c, ft.Container)
            and getattr(c, "bgcolor", None) == TILE_BG and getattr(c, "on_click", None)]
    check("в таблице есть строки", len(rows) >= 1, f"{len(rows)} строк")
    if rows:
        with_hover = [r for r in rows if getattr(r, "on_hover", None) is not None]
        check("у строк ЕСТЬ on_hover (раунд 6)", len(with_hover) == len(rows), f"{len(with_hover)}/{len(rows)}")
        cur = {getattr(r, "mouse_cursor", None) for r in rows}
        check("курсор CLICK остался", ft.MouseCursor.CLICK in cur)
        # вызвать on_hover(true) -> border accent #4f8cff, bgcolor hover_bg #2c3650
        r = rows[0]
        try:
            r.on_hover(type("E", (), {"data": "true"})())
            b = getattr(r, "border", None)
            hover_bg_ok = getattr(r, "bgcolor", None) == "#2c3650"
            accent_border = False
            if b is not None:
                # border.all: bottom side contains the accent color
                try:
                    accent_border = getattr(b, "bottom", None) is not None and getattr(b.bottom, "color", None) == "#4f8cff"
                except Exception:
                    accent_border = False
            check("hover: фон #2c3650", hover_bg_ok, f"bg={r.bgcolor}")
            check("hover: рамка #4f8cff", accent_border)
            # вернуть обратно
            r.on_hover(type("E", (), {"data": "false"})())
            check("hover off: фон вернулся #2a3247", getattr(r, "bgcolor", None) == TILE_BG, f"bg={r.bgcolor}")
        except Exception:
            traceback.print_exc()
            check("hover вызов без исключения", False)

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
        expected = ["all"] + get_criminalists_only() + [FILTER_OTHER]
        check("фильтр-опции: ровно канонический список + «Прочие»",
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

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()

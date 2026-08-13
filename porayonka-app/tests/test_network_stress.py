"""Стресс-аудит сетевой синхронизации вкладки «Контроли» (раунд 30).

Эмулирует несколько клиентов приложения (каждый со СВОЕЙ %APPDATA%-папкой и
ОБЩИМ shared-каталогом), параллельные операции (threading), offline-режим,
конфликты одновременного редактирования, большие вложения, медленную/битую
сеть, рассинхрон часов, алармы, удаление shared-файла.

Сценарии — по PROMPT_контроли_стресс_аудит.md:
  1. конфликты при одновременном добавлении (оба офлайн → сеть вернулась);
  2. конфликт при одновременном редактировании одного контроля (LWW, без
     слияния полей, тай-брейк);
  3. offline-режим: локальные данные не затираются пустым shared, seed;
  4. удаление shared-файла во время работы: работа на локальных, пересоздание
     при сохранении;
  5. большие вложения: атомарная копия, обрыв на полпути без битых файлов,
     фоновое копирование (>5 МБ) без зависания UI;
  6. медленная/нестабильная сеть: mtime не читается → offline, битый JSON →
     recovery, нет повторных чтений файла;
  7. множественные клиенты: гонка записей (уникальные tmp + os.replace),
     подрезка .bak, конвергенция через merge, user-фильтры;
  8. время на ПК: «будущее/прошлое» updated_at, детерминизм, UTC-нормализация;
  9. алармы: антиспам-интервалы, только свои контроли, один диалог;
 10. рестарт при доступном shared: офлайн-правки прошлой сессии не теряются
     (_load_initial merge);
 11. merge-before-write в _persist: чужой контроль не затирается при сохранении;
 12. вложения: синк из shared в локальную папку другого клиента через poll.

Запуск:  cd porayonka-app && python tests/test_network_stress.py
"""
import io
import json
import os
import sys
import tempfile
import contextlib
import traceback
import threading
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Изолируем данные в temp-APPDATA, чтобы тест не трогал реальные данные пользователя.
_TEST_APPDATA = tempfile.mkdtemp(prefix="porayonka_stress_")
os.environ["APPDATA"] = _TEST_APPDATA

import flet as ft  # noqa: E402
from page_stub import PageStub  # noqa: E402
from core.controls_data import (  # noqa: E402
    get_controls_file, load_controls, save_controls,
    load_settings, save_settings,
    read_shared_controls, write_shared_controls, get_shared_mtime,
    merge_controls, _updated_sort_key,
    copy_attachment_to_local, copy_attachment_to_shared,
    sync_attachments_from_shared, resolve_attachment,
)
from core.controls_models import (  # noqa: E402
    Control, ControlTask, OVERDUE,
)
from core.controls_notify import (  # noqa: E402
    collect_alarm_controls, due_alarms, alarm_interval_hours,
)
from ui.controls.controls_tab import create_controls_tab  # noqa: E402
from ui.controls.controls_tab import (  # noqa: E402
    _file_size_mb, _ATTACH_ASYNC_MB, _attach_event_is_duplicate,
)
import ui.controls.controls_tab as ct_module  # noqa: E402
import core.controls_data as cd_module  # noqa: E402

TILE_BG = "#2a3247"
FAILURES = []
_CHECKS = {"n": 0}


def check(name, cond, extra=""):
    _CHECKS["n"] += 1
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


def build(width=1280, height=860):
    page = PageStub(width=width, height=height)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        tab = create_controls_tab(page)
    return page, tab, buf.getvalue()


def _rows(tab):
    return [c for c in walk(tab) if isinstance(c, ft.Container)
            and getattr(c, "bgcolor", None) == TILE_BG and getattr(c, "on_click", None)]


def _texts(tab):
    return {str(t.value) for t in walk(tab) if isinstance(t, ft.Text) and t.value}


def _invoke_event_handler(eh, e):
    for fn in getattr(eh, "_EventHandler__handlers", {}).keys():
        try:
            fn(e)
        except Exception:
            traceback.print_exc()
        return True
    return False


# Глобальный лок на os.environ["APPDATA"] (процесс-глобальная переменная —
# переключение между клиентами должно быть сериализовано).
_ENV_LOCK = threading.Lock()


class Client:
    """Один «клиент» приложения: своя APPDATA-папка + общий shared-путь.

    Использование: `with client: ...` — внутри контекста все функции уровня
    данных (load/save_controls и т.п.) работают с APPDATA этого клиента.
    """

    def __init__(self, name, shared_path, role="admin", user=""):
        self.name = name
        self.shared_path = shared_path
        self.appdata = tempfile.mkdtemp(prefix=f"porayonka_stress_{name}_")
        self.settings = {
            "network_enabled": True,
            "network_role": role,
            "network_user": user,
            "network_shared_path": shared_path,
            "notify_log": {},
            "notify_sound": False,
        }

    def prepare(self):
        """Записать настройки клиента (вызывать внутри контекста)."""
        save_settings(dict(self.settings))

    def __enter__(self):
        _ENV_LOCK.acquire()
        self._old = os.environ.get("APPDATA")
        os.environ["APPDATA"] = self.appdata
        return self

    def __exit__(self, *exc):
        if self._old is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = self._old
        _ENV_LOCK.release()
        return False


def _mk(control_id, incoming=None, updated=None, **kw):
    c = Control(id=control_id, incoming_number=incoming or control_id)
    if updated:
        c.updated_at = updated
    for k, v in kw.items():
        setattr(c, k, v)
    return c


def _mk_task(id_, title="п. 1", assignees=None, due=None):
    return ControlTask(id=id_, title=title, assignees=list(assignees or []),
                       due_date=due)


def _shared_ctx():
    """Свежая общая папка + настройки «сервера» (без APPDATA)."""
    d = tempfile.mkdtemp(prefix="stress_shared_")
    return d, os.path.join(d, "controls.json"), {
        "network_enabled": True, "network_shared_path": os.path.join(d, "controls.json")}


# ──────────────────────────────────────────────────────────────────────────
# 1. Конфликты при одновременном добавлении (оба офлайн → сеть вернулась)
# ──────────────────────────────────────────────────────────────────────────
def scenario_concurrent_adds():
    shared_dir, shared_path, server_settings = _shared_ctx()
    write_shared_controls([_mk("c0", "ВХСОП-0", "2026-08-01T10:00:00")], server_settings)
    a = Client("add_a", shared_path)
    b = Client("add_b", shared_path)

    # Оба офлайн: shared недоступен, локальные сохранения работают
    block = os.path.join(shared_dir, "block")
    with open(block, "w", encoding="utf-8") as f:
        f.write("x")
    off_settings = {"network_enabled": True,
                    "network_shared_path": os.path.join(block, "controls.json")}
    ca = _mk("ca", "ВХСОП-A", "2026-08-10T09:00:00",
             tasks=[_mk_task("t1", due="2026-09-01")],
             attachments=["ca/scan.pdf"], executors=["Семисенко И.Ю."])
    cb = _mk("cb", "ВХСОП-B", "2026-08-10T09:05:00",
             tasks=[_mk_task("t2", title="п. 2", due="2026-09-05")])
    with a:
        a.prepare()
        save_controls([_mk("c0", "ВХСОП-0", "2026-08-01T10:00:00"), ca])
        check("1: офлайн-запись в shared не удалась (A)", 
              write_shared_controls(load_controls(), off_settings) is False)
    with b:
        b.prepare()
        save_controls([_mk("c0", "ВХСОП-0", "2026-08-01T10:00:00"), cb])
        check("1: офлайн-запись в shared не удалась (B)",
              write_shared_controls(load_controls(), off_settings) is False)
        check("1: локальные данные B целы", len(load_controls()) == 2)

    # Сеть вернулась: оба выходят в сеть ОДНОВРЕМЕННО (истинная гонка)
    with a:
        local_a = list(load_controls())
    with b:
        local_b = list(load_controls())
    barrier = threading.Barrier(2)
    results = {}

    def _online(name, local):
        try:
            barrier.wait(timeout=10)
            merged = merge_controls(local, read_shared_controls(server_settings))
            write_shared_controls(merged, server_settings)
            results[name] = True
        except Exception as e:
            results[name] = e

    ta = threading.Thread(target=_online, args=("A", local_a))
    tb = threading.Thread(target=_online, args=("B", local_b))
    ta.start()
    tb.start()
    ta.join(timeout=20)
    tb.join(timeout=20)
    check("1: оба «выхода в сеть» завершились без ошибок",
          results.get("A") is True and results.get("B") is True, f"{results}")

    # Сверка: КАЖДЫЙ клиент делает merge ещё раз (имитация polling-циклов) —
    # union должен сойтись с обеих сторон, чей бы набор ни победил в гонке
    with a:
        m = merge_controls(load_controls(), read_shared_controls(a.settings))
        write_shared_controls(m, a.settings)
    with b:
        m = merge_controls(load_controls(), read_shared_controls(b.settings))
        write_shared_controls(m, b.settings)
    final = read_shared_controls(server_settings)
    ids = {c.id for c in final}
    check("1: union сошёлся: c0 + ca + cb у обоих", ids == {"c0", "ca", "cb"}, f"{ids}")
    check("1: дублей нет (ровно 3 контроля)", len(final) == 3, f"{len(final)}")
    ca_final = next((c for c in final if c.id == "ca"), None)
    check("1: у контроля A сохранились id/incoming/tasks/attachments",
          ca_final is not None and ca_final.incoming_number == "ВХСОП-A"
          and len(ca_final.tasks) == 1 and ca_final.tasks[0].due_date == "2026-09-01"
          and ca_final.attachments == ["ca/scan.pdf"])
    cb_final = next((c for c in final if c.id == "cb"), None)
    check("1: у контроля B сохранились задачи",
          cb_final is not None and len(cb_final.tasks) == 1
          and cb_final.tasks[0].title == "п. 2")
    with a:
        m2 = merge_controls(load_controls(), read_shared_controls(a.settings))
        check("1: клиент A после синхронизации видит все 3",
              {c.id for c in m2} == {"c0", "ca", "cb"})
    with b:
        m2 = merge_controls(load_controls(), read_shared_controls(b.settings))
        check("1: клиент B после синхронизации видит все 3",
              {c.id for c in m2} == {"c0", "ca", "cb"})


# ──────────────────────────────────────────────────────────────────────────
# 2. Конфликт при одновременном редактировании одного контроля
# ──────────────────────────────────────────────────────────────────────────
def scenario_concurrent_edit():
    vA = _mk("c1", "ВХСОП-1", "2026-08-02T10:00:00", content="правка A", executors=["Исп А"])
    vB = _mk("c1", "ВХСОП-1", "2026-08-02T10:00:01", content="исходное", executors=["Исп Б"])

    w = merge_controls([vA], [vB])[0]
    check("2: победил сохранивший ПОЗЖЕ (B)", w.updated_at == vB.updated_at)
    check("2: НЕТ слияния полей — объект целиком B (content B, executors B)",
          w.content == "исходное" and w.executors == ["Исп Б"],
          f"content={w.content!r} executors={w.executors}")

    # «A сохранил ПОЗЖЕ»: версия A новее — побеждает A целиком
    vA_later = _mk("c1", "ВХСОП-1", "2026-08-02T10:00:02",
                   content="правка A", executors=["Исп А"])
    wA = merge_controls([vA_later], [vB])[0]
    check("2: если позже сохранил A — побеждает A целиком",
          wA.updated_at == vA_later.updated_at and wA.content == "правка A"
          and wA.executors == ["Исп А"])
    w3 = merge_controls([vA], [vB])[0]
    w4 = merge_controls([vB], [vA])[0]
    check("2: победитель не зависит от порядка аргументов merge",
          w3.updated_at == w4.updated_at == vB.updated_at
          and w3.content == w4.content == "исходное")

    tie_local = _mk("c1", "ВХСОП-1", "2026-08-02T10:00:00", content="локальная")
    tie_shared = _mk("c1", "ВХСОП-1", "2026-08-02T10:00:00", content="сетевая")
    t = merge_controls([tie_local], [tie_shared])[0]
    check("2: совпавший updated_at (в пределах микросекунды) — локальная, без слияния",
          t.content == "локальная")
    # поле-в-поле слияния нет и в тай-кейсе: содержимое ровно одной из версий
    check("2: тай-кейс — содержимое ровно одной версии",
          t.content in ("локальная", "сетевая"))


# ──────────────────────────────────────────────────────────────────────────
# 3. Offline-режим: локальные данные не затираются пустым shared, seed
# ──────────────────────────────────────────────────────────────────────────
def scenario_offline():
    _, shared_path, server_settings = _shared_ctx()
    with Client("off", shared_path) as cli:
        cli.prepare()
        save_controls([_mk("x1", "ВХСОП-X", "2026-08-01T10:00:00")])
        check("3: shared отсутствует → read_shared_controls = []",
              read_shared_controls(cli.settings) == [])
        # «старт приложения»: shared отсутствует — засев из локальных
        ok = write_shared_controls(load_controls(), cli.settings)
        check("3: seed — shared создан из локальных данных",
              ok and [c.id for c in read_shared_controls(cli.settings)] == ["x1"])
        # пустой shared (файл ЕСТЬ, controls=[]) — локальные НЕ перезаписываются
        write_shared_controls([], server_settings)
        local = load_controls()
        check("3: локальные данные не затираются пустым shared-файлом",
              [c.id for c in local] == ["x1"])
        # офлайн-сохранение: локальный файл жив, shared-запись = False
        block_dir = tempfile.mkdtemp(prefix="stress_block_")
        block = os.path.join(block_dir, "b")
        with open(block, "w", encoding="utf-8") as f:
            f.write("x")
        off = {"network_enabled": True,
               "network_shared_path": os.path.join(block, "controls.json")}
        save_controls([_mk("x1", "ВХСОП-X", "2026-08-01T10:00:00"),
                       _mk("x2", "ВХСОП-X2", "2026-08-02T10:00:00")])
        check("3: запись в shared при офлайне = False (не паника)",
              write_shared_controls(load_controls(), off) is False)
        check("3: локальные правки сохранены (x1+x2)",
              len(load_controls()) == 2)


# ──────────────────────────────────────────────────────────────────────────
# 4. Удаление shared-файла во время работы приложения
# ──────────────────────────────────────────────────────────────────────────
def scenario_shared_deleted():
    shared_dir, shared_path, server_settings = _shared_ctx()
    with Client("del", shared_path) as cli:
        cli.prepare()
        write_shared_controls([_mk("d0", "ВХСОП-D0", "2026-08-01T10:00:00")], cli.settings)
        save_controls([_mk("d0", "ВХСОП-D0", "2026-08-01T10:00:00")])
        page, tab, _ = build()
        try:
            os.remove(shared_path)  # shared удалён во время работы
            page._controls_poll_apply(None, [])
            txt = _texts(tab)
            check("4: индикатор «Сеть: нет связи»", any("нет связи" in t for t in txt))
            check("4: приложение работает на локальных данных", "ВХСОП-D0" in txt)
            # следующее сохранение пересоздаёт shared
            ok = write_shared_controls(load_controls(), cli.settings)
            check("4: shared пересоздан при сохранении",
                  ok and [c.id for c in read_shared_controls(cli.settings)] == ["d0"])
        finally:
            page._controls_poll_stop["flag"] = True


# ──────────────────────────────────────────────────────────────────────────
# 5. Большие вложения: атомарность, обрыв копии, фоновая копия
# ──────────────────────────────────────────────────────────────────────────
def scenario_attachments():
    shared_dir, shared_path, server_settings = _shared_ctx()
    src = os.path.join(tempfile.mkdtemp(prefix="stress_src_"), "scan.pdf")
    with open(src, "wb") as f:
        f.write(b"%PDF-1.4 fake-content-" + b"0" * 4096)
    with Client("att", shared_path) as cli:
        cli.prepare()
        rel = copy_attachment_to_shared("cid1", src, cli.settings)
        check("5: копия в shared успешна и имеет вид <id>/<файл>",
              rel == "cid1/scan.pdf")
        check("5: файл реально лежит в shared-папке вложений",
              os.path.exists(os.path.join(shared_dir, "controls_attachments",
                                          "cid1", "scan.pdf")))
        # обрыв копирования на полпути (сеть упала)
        orig_copy2 = cd_module.shutil.copy2

        def _boom(*a, **kw):
            raise OSError("network dropped mid-copy")

        cd_module.shutil.copy2 = _boom
        try:
            rel2 = copy_attachment_to_shared("cid2", src, cli.settings)
        finally:
            cd_module.shutil.copy2 = orig_copy2
        check("5: оборванная копия → None (без исключения)", rel2 is None)
        cid2_dir = os.path.join(shared_dir, "controls_attachments", "cid2")
        names = os.listdir(cid2_dir) if os.path.isdir(cid2_dir) else []
        check("5: НЕТ битого файла под финальным именем", "scan.pdf" not in names,
              f"{names}")
        check("5: НЕТ tmp-мусора после обрыва",
              not any(n.endswith(".tmp") for n in names))
        # локальный фолбэк цел и открывается
        rel_loc = copy_attachment_to_local("cid2", src)
        check("5: локальный фолбэк работает", rel_loc == "cid2/scan.pdf")
        p = resolve_attachment("cid2", rel_loc, cli.settings)
        check("5: resolve находит полный локальный файл (не битый shared)",
              p is not None and os.path.getsize(p) == os.path.getsize(src))
        # битый/пустой control_id — None без TypeError (раунд 22)
        check("5: пустой control_id → None без TypeError",
              copy_attachment_to_shared(None, src, cli.settings) is None
              and copy_attachment_to_local(None, src) is None)


def scenario_big_attach_async_ui():
    """Полный прогон: событие FilePicker с крупным файлом → фоновая копия."""
    shared_dir, shared_path, server_settings = _shared_ctx()
    big = os.path.join(tempfile.gettempdir(), "stress_big_scan2.pdf")
    with open(big, "wb") as f:
        f.truncate(6 * 1024 * 1024)
    try:
        with Client("bigu", shared_path) as cli:
            cli.prepare()
            write_shared_controls(
                [_mk("big2", "ВХСОП-BIG2", "2026-08-01T10:00:00")], cli.settings)
            save_controls([_mk("big2", "ВХСОП-BIG2", "2026-08-01T10:00:00")])
            page, tab, _ = build()
            try:
                check("5c: _file_size_mb видит размер >5 МБ",
                      _file_size_mb(type("F", (), {"path": big})()) > _ATTACH_ASYNC_MB)
                rows = _rows(tab)
                check("5c: строка контроля найдена", len(rows) >= 1)
                rows[0].on_click(None)
                picker = getattr(page, "_controls_attach_picker", None)
                check("5c: пикер найден", picker is not None)
                if picker is None:
                    return
                _invoke_event_handler(picker.on_result, type("E", (), {
                    "files": [type("F", (), {"path": big, "name": "stress_big_scan2.pdf"})()]} )())
                # фоновая копия + применение: ждём завершения (до 10 с)
                deadline = time.time() + 10
                done = False
                ctl = None
                while time.time() < deadline:
                    ctl = next((c for c in load_controls() if c.id == "big2"), None)
                    if ctl and ctl.attachments:
                        done = True
                        break
                    time.sleep(0.05)
                check("5c: крупный файл прикрепился через ФОНОВУЮ копию",
                      done and ctl is not None
                      and any(str(a).endswith("stress_big_scan2.pdf") for a in ctl.attachments))
                sh_path = os.path.join(shared_dir, "controls_attachments", "big2")
                check("5c: файл лежит в shared-папке вложений",
                      os.path.exists(os.path.join(sh_path, "stress_big_scan2.pdf")))
                check("5c: tmp-мусора в папке вложений нет",
                      not any(n.endswith(".tmp") for n in os.listdir(sh_path)))
                txt = _texts(tab)
                check("5c: строка вложения видна в UI",
                      any("stress_big_scan2.pdf" in t for t in txt))
            finally:
                page._controls_poll_stop["flag"] = True
    finally:
        try:
            os.remove(big)
        except OSError:
            pass


# ──────────────────────────────────────────────────────────────────────────
# 6. Медленная/нестабильная сеть
# ──────────────────────────────────────────────────────────────────────────
def scenario_slow_network():
    shared_dir, shared_path, server_settings = _shared_ctx()
    with Client("slow", shared_path) as cli:
        cli.prepare()
        write_shared_controls([], cli.settings)  # пустой shared-файл
        save_controls([])
        page, tab, _ = build()
        try:
            real_read = ct_module.read_shared_controls
            calls = {"n": 0}

            def _slow_read(settings):
                calls["n"] += 1
                time.sleep(0.05)  # имитация медленного SMB
                return real_read(settings)

            ct_module.read_shared_controls = _slow_read
            try:
                page._controls_poll_io()
                page._controls_poll_io()
                check("6: mtime не менялся — файл НЕ перечитывается (нет лишней нагрузки)",
                      calls["n"] == 0, f"reads={calls['n']}")
                write_shared_controls(
                    [_mk("slow1", "ВХСОП-SLOW", "2026-08-01T10:00:00")], cli.settings)
                # детерминизм: явно ставим mtime (+1 с) — на ФС с грубой
                # гранулярностью (FAT32 и т.п.) две записи в одну секунду
                # дали бы ОДИНАКОВЫЙ mtime и изменение «не заметилось» бы
                _stamp6 = get_shared_mtime(cli.settings) + 1.0
                os.utime(shared_path, (_stamp6, _stamp6))
                page._controls_poll_io()
                check("6: после изменения mtime файл прочитан ровно один раз",
                      calls["n"] == 1, f"reads={calls['n']}")
                txt = _texts(tab)
                check("6: новый контроль подхвачен опросом", "ВХСОП-SLOW" in txt)
            finally:
                ct_module.read_shared_controls = real_read

            # shared недоступен → offline-индикатор, без паники
            os.remove(shared_path)
            page._controls_poll_apply(None, [])
            txt = _texts(tab)
            check("6: shared недоступен — «Сеть: нет связи»",
                  any("нет связи" in t for t in txt))
            # сеть вернулась (другой админ пересоздал файл с контролем)
            write_shared_controls(
                [_mk("slow2", "ВХСОП-BACK", "2026-08-02T10:00:00")], cli.settings)
            mtime = get_shared_mtime(cli.settings)
            page._controls_poll_apply(mtime, read_shared_controls(cli.settings))
            txt = _texts(tab)
            check("6: сеть вернулась — контроль виден, индикатор «Сеть: админ»",
                  "ВХСОП-BACK" in txt and any("Сеть: админ" in t for t in txt))

            # битый JSON в shared — не паника, возврат []
            with open(shared_path, "w", encoding="utf-8") as f:
                f.write("{broken json!!!")
            got = read_shared_controls(cli.settings)
            check("6: битый shared-файл → [] без исключений", got == [])
            check("6: mtime битого файла читается без падения",
                  get_shared_mtime(cli.settings) is not None)
        finally:
            page._controls_poll_stop["flag"] = True


def scenario_corrupt_startup():
    """Старт при битом shared-файле: приложение живо, recovery из локальных."""
    shared_dir, shared_path, server_settings = _shared_ctx()
    with Client("corr", shared_path) as cli:
        cli.prepare()
        with open(shared_path, "w", encoding="utf-8") as f:
            f.write("{corrupt")
        save_controls([_mk("r1", "ВХСОП-R1", "2026-08-01T10:00:00")])
        page, tab, log = build()
        try:
            txt = _texts(tab)
            check("6b: при битом shared приложение стартует, локальные видны",
                  "ВХСОП-R1" in txt)
            got = read_shared_controls(cli.settings)
            check("6b: битый shared восстановлен из локальных данных (seed)",
                  [c.id for c in got] == ["r1"])
        finally:
            page._controls_poll_stop["flag"] = True


# ──────────────────────────────────────────────────────────────────────────
# 7. Множественные клиенты: гонка записей, .bak, конвергенция, user-фильтр
# ──────────────────────────────────────────────────────────────────────────
def scenario_many_clients():
    _, shared_path, server_settings = _shared_ctx()
    payloads = [
        [_mk(f"w{t}_{i}", f"ВХСОП-{t}-{i}", f"2026-08-01T10:00:{i:02d}")
         for i in range(3)]
        for t in range(4)
    ]
    errors = []

    def _writer(t):
        try:
            for _ in range(5):  # 5 раундов на клиента
                ok = write_shared_controls(payloads[t], server_settings)
                if not ok:
                    errors.append(f"w{t}: write=False")
                got = read_shared_controls(server_settings)
                if not got:
                    errors.append(f"w{t}: файл прочитан как пустой/битый")
        except Exception as e:
            errors.append(f"w{t}: {e!r}")

    threads = [threading.Thread(target=_writer, args=(t,)) for t in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    check("7: 4 клиента × 5 записей — все успешны, файл всегда валидный JSON",
          not errors, f"{errors[:3]}")
    leftovers = [n for n in os.listdir(shared_path.rsplit(os.sep, 1)[0])
                 if n.endswith(".tmp")]
    check("7: tmp-остатков после гонки нет (уникальные tmp + атомарный replace)",
          not leftovers, f"{leftovers}")
    baks = [n for n in os.listdir(shared_path.rsplit(os.sep, 1)[0])
            if n.startswith("controls.json.bak.")]
    # при гонке возможен временный перекос (prune-vs-copy без блокировок) —
    # детерминированная проверка подрезки ниже, при последовательной записи
    check("7: при гонке бэкапы не размножаются лавинообразно (<=8)",
          len(baks) <= 8, f"{len(baks)}")
    # детерминированно: 12 последовательных записей одного клиента → <=5 .bak
    _bak_dir = tempfile.mkdtemp(prefix="stress_bak_")
    _bak_settings = {"network_enabled": True,
                     "network_shared_path": os.path.join(_bak_dir, "controls.json")}
    for i in range(12):
        write_shared_controls(
            [_mk(f"b{i}", updated=f"2026-08-01T10:00:{i:02d}")], _bak_settings)
    _baks = [n for n in os.listdir(_bak_dir) if n.startswith("controls.json.bak.")]
    check("7: бэкапы в shared ПОДРЕЗАНЫ (12 записей → <=5, не копятся вечно)",
          len(_baks) <= 5, f"{len(_baks)}")
    final = read_shared_controls(server_settings)
    all_ids = {c.id for pl in payloads for c in pl}
    # last-write-wins: в файле может быть один из наборов — сверка через merge
    reconciled = merge_controls(final, [c for pl in payloads for c in pl])
    check("7: конвергенция — после merge все 12 контролей на месте",
          len({c.id for c in reconciled}) == 12,
          f"{len({c.id for c in reconciled})}")
    # контроль целостности: содержимое файла — ровно один полный набор (не каша)
    ok_sets = [sorted(c.id for c in pl) for pl in payloads]
    check("7: содержимое файла — ровно один полный набор (без «каши»)",
          sorted(c.id for c in final) in ok_sets)


def scenario_user_filter():
    _, shared_path, server_settings = _shared_ctx()
    with Client("usr", shared_path, role="user",
                user="Семисенко Иван Юрьевич") as cli:
        cli.prepare()
        write_shared_controls([
            _mk("m1", "МОЙ", "2026-08-01T10:00:00", executors=["Семисенко И.Ю."]),
            _mk("ch1", "ЧУЖОЙ", "2026-08-01T10:00:00", executors=["Чужой Ч.Ч."]),
        ], cli.settings)
        page, tab, _ = build()
        try:
            txt = _texts(tab)
            check("7b: user видит только свои контроли",
                  "МОЙ" in txt and "ЧУЖОЙ" not in txt, f"{sorted(txt)[:6]}")
            rows = _rows(tab)
            check("7b: в таблице ровно один контроль пользователя", len(rows) == 1)
        finally:
            page._controls_poll_stop["flag"] = True


# ──────────────────────────────────────────────────────────────────────────
# 8. Время на ПК: «будущее/прошлое» updated_at, детерминизм, UTC
# ──────────────────────────────────────────────────────────────────────────
def scenario_clock_skew():
    future = _mk("f1", "ВХСОП-F", "2030-01-01T00:00:00", content="будущее")
    past = _mk("f1", "ВХСОП-F", "2020-01-01T00:00:00", content="прошлое")
    w1 = merge_controls([past], [future])[0]
    w2 = merge_controls([future], [past])[0]
    check("8: updated_at «из будущего» побеждает детерминированно",
          w1.updated_at == "2030-01-01T00:00:00"
          and w2.updated_at == "2030-01-01T00:00:00")
    check("8: «отстающие» часы не ломают merge (нет исключений)", True)
    # пустое/битое updated_at — старее валидного
    m_bad = merge_controls([_mk("x", updated="мусор")],
                           [_mk("x", updated="2026-08-01T10:00:00")])
    check("8: битое updated_at старее валидного",
          m_bad[0].updated_at == "2026-08-01T10:00:00")
    # UTC-нормализация: naive-ISO трактуется как UTC → одинаковый результат
    # на любом ПК (раньше каждый ПК считал epoch в своём поясе)
    key = _updated_sort_key(_mk("t", updated="2026-08-13T10:00:00"))
    expected = datetime(2026, 8, 13, 10, 0, 0, tzinfo=timezone.utc).timestamp()
    check("8: naive-ISO нормализуется в UTC (детерминизм между часовыми поясами)",
          abs(key[1] - expected) < 1e-6, f"{key[1]} vs {expected}")
    # aware-строка тоже корректна
    key_a = _updated_sort_key(
        _mk("t", updated="2026-08-13T10:00:00+05:00"))
    exp_a = datetime(2026, 8, 13, 10, 0, 0, tzinfo=timezone(timedelta(hours=5))).timestamp()
    check("8: aware-ISO (с поясом) считается корректно",
          abs(key_a[1] - exp_a) < 1e-6)


# ──────────────────────────────────────────────────────────────────────────
# 9. Алармы/уведомления: антиспам, только свои, один диалог
# ──────────────────────────────────────────────────────────────────────────
def scenario_alarms():
    mine = _mk("al1", "АЛ-1", due_date="2020-01-01", executors=["Семисенко И.Ю."])
    other = _mk("al2", "АЛ-2", due_date="2020-01-01", executors=["Чужой Ч.Ч."])
    done = _mk("al3", "АЛ-3", due_date="2020-01-01", executors=["Семисенко И.Ю."],
               done=True)
    all_c = [mine, other, done]
    adm = collect_alarm_controls(all_c, 3)
    check("9: админ видит все просроченные (кроме исполненных)",
          {c.id for c in adm} == {"al1", "al2"})
    usr = collect_alarm_controls(all_c, 3, "Семисенко Иван Юрьевич")
    check("9: пользователь — ТОЛЬКО свои контроли", [c.id for c in usr] == ["al1"])
    now = datetime(2026, 8, 12, 12, 0, 0)
    due1, log1 = due_alarms([mine, other], {}, now, 2)
    check("9: первый цикл — оба алармятся, журнал пишется",
          len(due1) == 2 and "al1" in log1)
    due2, log2 = due_alarms([mine, other], log1, now + timedelta(hours=1), 2)
    check("9: через час (интервал 2 ч) повтора НЕТ — не дублируется бесконечно",
          due2 == [])
    due3, _ = due_alarms([mine, other], log2, now + timedelta(hours=2, minutes=1), 2)
    check("9: через 2 ч — повтор («злой» аларм)", len(due3) == 2)
    due4, _ = due_alarms([mine, other], log1, now + timedelta(hours=5), 24)
    check("9: админский интервал 24 ч — через 5 ч повтора нет", due4 == [])
    check("9: интервалы — user 2 ч, админ 24 ч",
          alarm_interval_hours(True) == 2 and alarm_interval_hours(False) == 24)

    # UI: один диалог на цикл, журнал подавляет повтор
    _, shared_path, _srv = _shared_ctx()
    with Client("alrm", shared_path) as cli:
        cli.prepare()
        save_settings({"network_enabled": False, "network_role": "admin",
                       "network_user": "", "network_shared_path": "",
                       "notify_log": {}, "notify_sound": False, "alarm_enabled": True})
        save_controls([mine])
        page, tab, _ = build()
        try:
            hook = getattr(page, "_controls_alarm_check", None)
            check("9: тест-хук алармов установлен", callable(hook))
            if callable(hook):
                hook()
                hook()
                dlg = page.dialogs
                check("9: повторный цикл не плодит диалоги (один «СРОК КОНТРОЛЯ!»)",
                      len(dlg) == 1
                      and any(isinstance(t, ft.Text) and t.value == "СРОК КОНТРОЛЯ!"
                              for d in dlg for t in walk(d)))
                check("9: журнал алармов записан (антиспам)",
                      (load_settings().get("alarm_log") or {}).get("al1") is not None)
        finally:
            page._controls_poll_stop["flag"] = True


# ──────────────────────────────────────────────────────────────────────────
# 10. Рестарт при доступном shared: офлайн-правки прошлой сессии не теряются
# ──────────────────────────────────────────────────────────────────────────
def scenario_startup_merge():
    _, shared_path, server_settings = _shared_ctx()
    with Client("restart", shared_path) as cli:
        cli.prepare()
        # локально: офлайн-добавление прошлой сессии + УСТАРЕВШАЯ версия s0
        save_controls([_mk("l1", "ВХСОП-L1", "2026-08-10T09:00:00"),
                       _mk("s0", "ВХСОП-S0", "2026-08-01T10:00:00")])
        # shared: свежая версия s0 + добавленный другим админом s2
        write_shared_controls([
            _mk("s0", "ВХСОП-S0", "2026-08-05T10:00:00", content="новая версия"),
            _mk("s2", "ВХСОП-S2", "2026-08-04T10:00:00"),
        ], cli.settings)
        page, tab, _ = build()
        try:
            txt = _texts(tab)
            check("10: офлайн-контроль прошлой сессии НЕ потерян при старте",
                  "ВХСОП-L1" in txt, f"{sorted(txt)[:8]}")
            check("10: контроль другого админа из shared виден", "ВХСОП-S2" in txt)
            shared_now = read_shared_controls(cli.settings)
            s0 = next((c for c in shared_now if c.id == "s0"), None)
            check("10: конфликтная версия s0 — свежая из shared (LWW), не откат",
                  s0 is not None and s0.updated_at == "2026-08-05T10:00:00"
                  and s0.content == "новая версия")
            check("10: локальный l1 запушен обратно в shared при старте",
                  "l1" in {c.id for c in shared_now})
            check("10: дублей после стартового merge нет",
                  len({c.id for c in shared_now}) == 3)
        finally:
            page._controls_poll_stop["flag"] = True


# ──────────────────────────────────────────────────────────────────────────
# 11. merge-before-write в _persist: чужой контроль не затирается сохранением
# ──────────────────────────────────────────────────────────────────────────
def scenario_persist_merge():
    _, shared_path, server_settings = _shared_ctx()
    with Client("pers", shared_path) as cli:
        cli.prepare()
        write_shared_controls([_mk("p0", "ВХСОП-P0", "2026-08-01T10:00:00")], cli.settings)
        save_controls([_mk("p0", "ВХСОП-P0", "2026-08-01T10:00:00")])
        page, tab, _ = build()
        try:
            # другой админ добавил контроль, пока мы работали
            write_shared_controls([
                _mk("p0", "ВХСОП-P0", "2026-08-01T10:00:00"),
                _mk("p_other", "ВХСОП-OTHER", "2026-08-02T10:00:00"),
            ], cli.settings)
            # детерминизм mtime (см. сценарий 6): грубая гранулярность ФС
            # не должна мешать проверке merge-before-write
            _stamp11 = get_shared_mtime(cli.settings) + 1.0
            os.utime(shared_path, (_stamp11, _stamp11))
            # добавляем свой контроль через UI и сохраняем
            add_btns = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
                        and getattr(c, "text", None) == "Добавить контроль"]
            check("11: кнопка «Добавить контроль» найдена", len(add_btns) == 1)
            if add_btns:
                add_btns[0].on_click(None)
            inc_field = next((c for c in walk(tab) if isinstance(c, ft.TextField)
                              and (getattr(c, "hint_text", None) or "").startswith("Входящий")), None)
            check("11: поле «Входящий №» найдено", inc_field is not None)
            if inc_field is not None:
                inc_field.value = "ВХСОП-NEW"
            save_btn = [c for c in walk(tab) if isinstance(c, ft.ElevatedButton)
                        and getattr(c, "text", None) == "Сохранить"]
            check("11: кнопка «Сохранить» найдена", len(save_btn) == 1)
            if save_btn:
                save_btn[0].on_click(None)
            shared_now = read_shared_controls(cli.settings)
            ids = {c.id for c in shared_now}
            check("11: merge-before-write — чужой контроль p_other НЕ затёрт",
                  "p_other" in ids and "p0" in ids, f"{ids}")
            check("11: новый контроль записан в shared",
                  any(c.incoming_number == "ВХСОП-NEW" for c in shared_now))
            local_now = load_controls()
            check("11: локальный файл не отстаёт от state (содержит всё)",
                  {c.id for c in local_now} == ids, f"{len(local_now)}")
        finally:
            page._controls_poll_stop["flag"] = True


# ──────────────────────────────────────────────────────────────────────────
# 12. Вложения: синк из shared в локальную папку другого клиента через poll
# ──────────────────────────────────────────────────────────────────────────
def scenario_attach_sync_client():
    shared_dir, shared_path, server_settings = _shared_ctx()
    with Client("synca", shared_path) as cli:
        cli.prepare()
        write_shared_controls([], cli.settings)
        save_controls([])
        page, tab, _ = build()
        try:
            # другой админ прикрепил файл к контролю
            att_dir = os.path.join(shared_dir, "controls_attachments", "att1")
            os.makedirs(att_dir, exist_ok=True)
            with open(os.path.join(att_dir, "scan.pdf"), "wb") as f:
                f.write(b"%PDF-1.4 fake-content")
            write_shared_controls([
                _mk("att1", "ВХСОП-ATT", "2026-08-01T10:00:00",
                    attachments=["att1/scan.pdf"]),
            ], cli.settings)
            # детерминизм mtime (см. сценарий 6)
            _stamp12 = get_shared_mtime(cli.settings) + 1.0
            os.utime(shared_path, (_stamp12, _stamp12))
            mtime = get_shared_mtime(cli.settings)
            page._controls_poll_apply(mtime, read_shared_controls(cli.settings))
            local_att = os.path.join(cli.appdata, "porayonka",
                                     "controls_attachments", "att1", "scan.pdf")
            check("12: вложение подтянуто из shared в ЛОКАЛЬНУЮ папку клиента",
                  os.path.exists(local_att))
            check("12: файл-вложение цел (размер совпадает)",
                  os.path.getsize(local_att) == len(b"%PDF-1.4 fake-content"))
            txt = _texts(tab)
            check("12: контроль с вложением виден после poll", "ВХСОП-ATT" in txt)
        finally:
            page._controls_poll_stop["flag"] = True


# ──────────────────────────────────────────────────────────────────────────
def main():
    scenario_concurrent_adds()        # 1
    scenario_concurrent_edit()        # 2
    scenario_offline()                # 3
    scenario_shared_deleted()         # 4
    scenario_attachments()            # 5 (атомарность, обрыв)
    scenario_big_attach_async_ui()    # 5 (фоновая копия >5 МБ через UI)
    scenario_slow_network()           # 6
    scenario_corrupt_startup()        # 6b
    scenario_many_clients()           # 7 (гонка, .bak, конвергенция)
    scenario_user_filter()            # 7b
    scenario_clock_skew()             # 8
    scenario_alarms()                 # 9
    scenario_startup_merge()          # 10
    scenario_persist_merge()          # 11
    scenario_attach_sync_client()     # 12

    print()
    print(f"Проверок выполнено: {_CHECKS['n']}")
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()

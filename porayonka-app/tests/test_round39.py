# -*- coding: utf-8 -*-
"""Раунд 39 — проверки (точка входа обязательного контура).

Запуск из porayonka-app:   python tests\\test_round39.py

Проверки разделены по слоям (никакого «static+mock+integration в одном
сотне-строчном файле»):

  r39_logic   — single-instance guard и tray: acquired / already_running /
                отказ API (fail-open) / настоящий не-Windows fail-open /
                release-идемпотентность / конкурентный захват / реальные два
                процесса (эмyляция ОС-ным локом; на Windows дополнительно —
                настоящий CreateMutexW), логика LazyTabHost;
  r39_ui      — через НАСТОЯЩИЕ обработчики: очистка конечной даты + полный
                persistence/Excel round-trip, ленивые вкладки в реальном
                main._main_impl, веб-импорт Excel (FilePicker upload ->
                progress -> preview -> confirm) со сценариями cancel/error/
                repeat/same-name/user-edition/no-upload-dir;
  r39_static  — инварианты связки (один владелец браузера, FLET_UPLOAD_DIR/
                FLET_SECRET_KEY до ft.app, guard до/после ft.app).

Харнесс глушит главный класс ложноположительных прогонов: необработанное
исключение в фоновом потоке (pystray setup_handler и т.п.) превращается в FAIL,
а не в «ALL OK» с трейсбеком сбоку.

Данные не трогаются: APPDATA и FLET_UPLOAD_DIR подменяются на временные каталоги
ДО импорта core-модулей.
"""
import os
import shutil
import sys
import tempfile
import traceback

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── изоляция ДО импорта core/* ────────────────────────────────────────────
_TMP = tempfile.mkdtemp(prefix="r39_tmp_")
_APPDATA = os.path.join(_TMP, "appdata")
_UPLOADS = os.path.join(_TMP, "uploads")
os.makedirs(_APPDATA, exist_ok=True)
os.makedirs(_UPLOADS, exist_ok=True)
os.environ["APPDATA"] = _APPDATA
os.environ["R39_APPDATA"] = _APPDATA
os.environ["FLET_UPLOAD_DIR"] = _UPLOADS
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

sys.path.insert(0, APP_DIR)
sys.path.insert(0, os.path.join(APP_DIR, "tests"))

import r39_logic                                             # noqa: E402
import r39_static                                            # noqa: E402
import r39_ui                                                # noqa: E402
from r39_harness import (FAILURES, SKIPPED, THREAD_ERRORS,  # noqa: E402
                         fail_on_thread_errors, guard_thread_errors)

GROUPS = (
    ("harness", guard_thread_errors),
    ("logic: single-instance", r39_logic.run_single_instance),
    ("logic: два процесса", r39_logic.run_single_instance_crossprocess),
    ("logic: tray", r39_logic.run_tray),
    ("logic: LazyTabHost", r39_logic.run_lazy_host),
    ("ui: конечная дата", r39_ui.run_end_date),
    ("ui: ленивые вкладки", r39_ui.run_lazy_tabs_runtime),
    ("ui: веб-импорт Excel", r39_ui.run_web_import),
    ("static: браузер", r39_static.run_browser_owner),
    ("static: web-загрузка", r39_static.run_upload_wiring),
    ("static: guard/трей", r39_static.run_guard_wiring),
)


def main():
    for title, fn in GROUPS:
        print("\n" + "=" * 72)
        print("=== %s ===" % title)
        try:
            fn()
        except Exception:
            FAILURES.append("%s [exception]" % title)
            traceback.print_exc()
    # фон: любое необработанное исключение потока = FAIL прогона
    print("\n" + "=" * 72)
    fail_on_thread_errors()
    if THREAD_ERRORS:
        print("Фоновых исключений: %d" % len(THREAD_ERRORS))
    if SKIPPED:
        print("Не проверялось на этой платформе: %s" % "; ".join(SKIPPED))
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

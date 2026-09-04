# -*- coding: utf-8 -*-
"""Раунд 39: агрегатор. Запускает пять предметных наборов проверок.

Монолитный файл раунда 39 разделён по областям — static/mock/integration
больше не перемешаны в одном модуле, и каждый набор запускается отдельно:

    tests/test_round39_enddate.py     задача 1 — конечная дата
    tests/test_round39_lazytabs.py    задача 2 — ленивые вкладки
    tests/test_round39_browser.py     задача 3 — владелец открытия браузера
    tests/test_round39_tray.py        задача 4 — tray (один Icon, один stop)
    tests/test_round39_mutex.py       задача 4 — single-instance guard
    tests/test_round39_webimport.py   задача 5 — Excel-импорт в Admin Web

Каждый набор — самостоятельный процесс: они подменяют sys.platform,
модуль ctypes и pystray, поэтому изоляция процессом надёжнее, чем импорт
в одном интерпретаторе.

Запуск из porayonka-app:  python tests\\test_round39.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

SUITES = [
    ("1. Конечная дата", "test_round39_enddate.py"),
    ("2. Ленивые вкладки", "test_round39_lazytabs.py"),
    ("3. Владелец открытия браузера", "test_round39_browser.py"),
    ("4. Tray: один Icon, один stop", "test_round39_tray.py"),
    ("4. Single-instance guard", "test_round39_mutex.py"),
    ("5. Excel-импорт в Admin Web", "test_round39_webimport.py"),
]


def main():
    failed = []
    totals = {"ok": 0, "fail": 0}
    for title, fname in SUITES:
        print("\n" + "#" * 70)
        print("### " + title + "  (" + fname + ")")
        print("#" * 70)
        p = subprocess.run([sys.executable, os.path.join(HERE, fname)],
                           cwd=os.path.dirname(HERE),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = p.stdout.decode("utf-8", "replace")
        sys.stdout.write(out)
        totals["ok"] += out.count("[OK ]")
        totals["fail"] += out.count("[FAIL]")
        if p.returncode != 0:
            failed.append("%s (%s) exit=%d" % (title, fname, p.returncode))

    print("\n" + "=" * 70)
    print("ИТОГО раунд 39: OK=%d FAIL=%d" % (totals["ok"], totals["fail"]))
    if failed:
        print("FAILED SUITES: %d" % len(failed))
        for f in failed:
            print("  - " + f)
        sys.exit(1)
    print("ALL OK")
    sys.exit(0)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Раунд 39 (задача 3): ровно один владелец открытия браузера (Flet)."""
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


def test_browser_owner():
    print("\n=== 3. Один владелец открытия браузера ===")

    bat = io.open(START_BAT, encoding="utf-8", errors="replace").read()
    low = bat.lower()
    # `start http://...` / `start "" http://...` / `start "" "http://...`
    bad = []
    for line in low.splitlines():
        s = line.strip()
        if s.startswith("::") or s.startswith("rem "):
            continue
        if s.startswith("start") and "http" in s:
            bad.append(line.strip())
    check("r39-3.1a: start_web_win7.bat НЕ открывает браузер (нет start http)",
          not bad, "; ".join(bad))
    check("r39-3.1b: bat по-прежнему запускает сервер",
          "Порайонка_Пользователь_Web.exe" in bat
          and "Порайонка_Админ_Web.exe" in bat)
    check("r39-3.1c: bat ждёт HTTP-доступности сервера",
          "HttpWebRequest" in bat and "8555" in bat)
    check("r39-3.1d: bat печатает адрес для ручного открытия",
          "http://127.0.0.1:%WEBPORT%" in bat)

    src_main = io.open(MAIN_PY, encoding="utf-8").read()
    check("r39-3.2a: владелец документирован (BROWSER_OWNER)",
          'BROWSER_OWNER = "flet:AppView.WEB_BROWSER"' in src_main)
    check("r39-3.2b: авто-старт открывает браузер только через Flet",
          src_main.count("ft.AppView.WEB_BROWSER") == 1
          and "view=ft.AppView.WEB_BROWSER" in src_main)
    tree = ast.parse(src_main)
    webbrowser_in_entry = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr == "open" \
                    and isinstance(f.value, ast.Name) and f.value.id == "webbrowser":
                webbrowser_in_entry = True
    check("r39-3.2c: main.py НЕ зовёт webbrowser.open сам", not webbrowser_in_entry)
    ft_app_calls = [
        nd for nd in ast.walk(tree)
        if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Attribute)
        and nd.func.attr == "app" and isinstance(nd.func.value, ast.Name)
        and nd.func.value.id == "ft"]
    check("r39-3.2d: сервер/клиент поднимается ровно двумя ft.app "
          "(web-ветка + desktop-ветка), дублей нет",
          len(ft_app_calls) == 2, str(len(ft_app_calls)))

    # main_web.py: каждый _open_browser() ведёт к sys.exit() в том же блоке.
    src_web = io.open(MAIN_WEB_PY, encoding="utf-8").read()
    wtree = ast.parse(src_web)
    opens = 0
    orphan = 0
    for node in ast.walk(wtree):
        if isinstance(node, ast.If):
            def _is_call(n, name):
                if isinstance(n, ast.Expr):
                    n = n.value
                return (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                        and n.func.id == name)

            has_open = any(_is_call(n, "_open_browser") for n in node.body)
            if not has_open:
                continue
            opens += 1
            def _is_sysexit(n):
                if isinstance(n, ast.Expr):
                    n = n.value
                return (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "exit"
                        and isinstance(n.func.value, ast.Name)
                        and n.func.value.id == "sys")

            has_exit = any(_is_sysexit(n) for n in node.body)
            if not has_exit:
                orphan += 1
    check("r39-3.3a: main_web.py: найдены ветки повторного запуска с _open_browser",
          opens >= 1, f"branches={opens}")
    check("r39-3.3b: КАЖДЫЙ _open_browser сопровождается sys.exit() "
          "(Flet в этом процессе не стартует -> дубля нет)",
          orphan == 0, f"orphans={orphan}")
    check("r39-3.3c: _open_browser вызывается ТОЛЬКО в ветках повторного запуска",
          src_web.count("_open_browser(") == opens + 1)   # +1 определение
    check("r39-3.3d: main_web.py не открывает браузер на обычном старте",
          src_web.index("from main import _entry")
          < src_web.index('if __name__ == "__main__":'))

    # «Открыть» из трея — явная команда пользователя, остаётся.
    src_tray = io.open(os.path.join(ROOT, "ui", "tray_icon.py"),
                       encoding="utf-8").read()
    check("r39-3.4: «Открыть» в меню трея (явная команда) сохранён",
          "webbrowser.open(web_url)" in src_tray)




def main():
    install_thread_guard()
    for fn in (test_browser_owner,):
        print("\n" + "=" * 70)
        try:
            fn()
        except Exception:
            import traceback
            check(fn.__name__ + " [exception]", False)
            traceback.print_exc()
    check_no_thread_errors('Раунд 39 (задача 3): ровно один владелец')
    sys.exit(report('Раунд 39 (задача 3): ровно один владелец открытия браузера ('))


if __name__ == "__main__":
    main()

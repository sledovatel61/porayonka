# -*- coding: utf-8 -*-
"""Раунд 39, группа STATIC: только те проверки, которые осмысленны именно как
проверка исходника/сборочного файла (поведение проверяется в r39_logic/r39_ui).

Смысл: зафиксировать ИНВАРИАНТЫ связки — кто открывает браузер, где задаются
каталог и ключ загрузки, что guard занимает ДО запуска UI и освобождается при
выходе. Такие правила нельзя подтвердить моком «на поведение», их видно в коде.
"""
import ast
import io
import os

from r39_harness import check

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_PY = os.path.join(ROOT, "main.py")
MAIN_WEB_PY = os.path.join(ROOT, "main_web.py")
BAT = os.path.join(ROOT, "start_web_win7.bat")
TRAY = os.path.join(ROOT, "ui", "tray_icon.py")


def _read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def run_browser_owner():
    print("\n--- 3. Единственный владелец открытия браузера (инварианты) ---")
    bat = _read(BAT)
    active = [ln.strip() for ln in bat.splitlines()
              if not ln.strip().lower().startswith(("::", "rem ", "@echo"))]
    bad = [ln for ln in active if ln.lower().startswith("start") and "http" in ln]
    check("r39-3.1a: start_web_win7.bat НЕ открывает браузер (нет `start http`)",
          not bad, "; ".join(bad))
    check("r39-3.1b: bat по-прежнему запускает сервер и ждёт доступности HTTP",
          "Порайонка_Пользователь_Web.exe" in bat
          and "Порайонка_Админ_Web.exe" in bat and "HttpWebRequest" in bat)
    check("r39-3.1c: bat печатает фактический адрес (порт из перебора 8555..8564)",
          "http://127.0.0.1:%WEBPORT%" in bat and "8555..8564" in bat)
    check("r39-3.1d: stderr PowerShell не смешан со stdout (в файл — только порт) "
          "и значение проверяется на 85xx",
          '2>nul' in bat and 'findstr /r "^85[0-9][0-9]$"' in bat)

    src = _read(MAIN_PY)
    check("r39-3.2a: владелец задокументирован (BROWSER_OWNER)",
          'BROWSER_OWNER = "flet:AppView.WEB_BROWSER"' in src)
    check("r39-3.2b: браузер открывает ровно ОДИН вызов Flet",
          src.count("view=ft.AppView.WEB_BROWSER") == 1)
    tree = ast.parse(src)
    auto_open = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "open" and isinstance(n.func.value, ast.Name)
                 and n.func.value.id == "webbrowser"]
    check("r39-3.2c: main.py НЕ зовёт webbrowser.open (автостарт — только Flet)",
          not auto_open, str(len(auto_open)))
    # явная команда «Открыть» из трея — сохранена (это действие пользователя)
    check("r39-3.2d: «Открыть» из меню трея (явное действие) сохранено",
          "webbrowser.open(web_url)" in _read(TRAY))

    # main_web.py: _open_browser только на повторном запуске и всегда с sys.exit
    wsrc = _read(MAIN_WEB_PY)
    wtree = ast.parse(wsrc)

    def _call(n, name, attr=None):
        if isinstance(n, ast.Expr):
            n = n.value
        if not isinstance(n, ast.Call):
            return False
        f = n.func
        if attr is not None:
            return (isinstance(f, ast.Attribute) and f.attr == attr
                    and isinstance(f.value, ast.Name) and f.value.id == "sys")
        return isinstance(f, ast.Name) and f.id == name

    opens = exits = 0
    for node in ast.walk(wtree):
        if isinstance(node, ast.If):
            o = sum(1 for n in node.body if _call(n, "_open_browser"))
            opens += o
            exits += sum(1 for n in node.body if _call(n, None, "exit"))
    check("r39-3.3a: КАЖДЫЙ _open_browser() в ветке повторного запуска "
          "сопровождён sys.exit() (Flet в этом процессе не стартует)",
          opens >= 1 and exits >= opens, "open=%s exit=%s" % (opens, exits))
    check("r39-3.3b: на обычном старте main_web.py браузер не открывает "
          "(после импорта _entry() вызовов _open_browser нет)",
          opens == wsrc[:wsrc.index("from main import _entry")].count("_open_browser(") - 1,
          str(opens))


def run_upload_wiring():
    print("\n--- 5b. Связка web-загрузки (инварианты main.py) ---")
    src = _read(MAIN_PY)
    i_app = src.index("ft.app(target=main, view=ft.AppView.WEB_BROWSER")
    i_dir = src.index('os.environ["FLET_UPLOAD_DIR"]')
    i_key = src.index('os.environ["FLET_SECRET_KEY"]')
    check("r39-5.8a: FLET_UPLOAD_DIR задаётся ДО ft.app (сервер читает env при старте)",
          0 < i_dir < i_app, "%s < %s" % (i_dir, i_app))
    check("r39-5.8b: FLET_SECRET_KEY задаётся ДО ft.app", 0 < i_key < i_app)
    check("r39-5.8c: каталог загрузки — %APPDATA%\\porayonka\\web_uploads, "
          "создаётся заранее", '"web_uploads"' in src and "makedirs" in src)
    check("r39-5.8d: ключ стабильный (файл upload_secret.key) и криптостойкий "
          "(secrets.token_hex)", "upload_secret.key" in src and "token_hex" in src)
    check("r39-5.8e: env задаётся в web-ветке, desktop-ветка его НЕ трогает "
          "(desktop-импорт не ломается)",
          src.index('if "--web" in sys.argv:') < i_dir < i_app)
    # main_web.py переиспользует _entry() -> правка действует для обеих web-сборок
    check("r39-5.8f: main_web.py использует общий _entry() (правка покрывает "
          "обе web-редакции)", "from main import _entry" in _read(MAIN_WEB_PY))


def run_guard_wiring():
    print("\n--- 4d. Подключение guard'а и трея в main.py (инварианты) ---")
    src = _read(MAIN_PY)
    entry = src[src.index("def _entry():"):]
    desktop = entry[entry.index("else:"):]
    i_app = desktop.index("ft.app(target=main)")
    check("r39-4.16a: desktop-ветка занимает guard ДО ft.app",
          "single_instance as _si39" in desktop[:i_app]
          and "_si39.acquire()" in desktop[:i_app])
    check("r39-4.16b: при занятом mutex окно/трей НЕ создаются, управление "
          "передаётся первому экземпляру",
          "focus_existing()" in desktop[:i_app] and "return" in desktop[:i_app])
    check("r39-4.16c: guard освобождается в finally после ft.app "
          "(выход через окно/краш-путь тоже)",
          "_si39b.release()" in desktop[i_app:])
    check("r39-4.16d: web-ветка guard НЕ занимает (single-instance — desktop; "
          "для web штатная защита — проверка порта)",
          "single_instance" not in entry[:entry.index("else:")])
    tray = _read(TRAY)
    i_first = tray.index("if _ACTIVE_ICON is not None:")
    i_with = tray.index("with _TRAY_LOCK:")
    i_second = tray.index("if _ACTIVE_ICON is not None:", i_with)
    check("r39-4.16e: tray — double-checked locking (проверка и ДО, и ПОСЛЕ lock)",
          i_first < i_with < i_second)
    check("r39-4.16f: вне Windows значок не создаётся вовсе",
          'if sys.platform != "win32":' in tray[:tray.index("def notify") + 400]
          or 'if sys.platform != "win32":' in tray)

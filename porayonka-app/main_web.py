# main_web.py
# Раунд 24 (задача 2): точка входа WEB-версии для Windows 7 (пользовательская
# и — с раунда 37 — админская редакции). Нативный клиент Flet 0.23.2
# (Flutter) требует Win10+, поэтому на Win7 приложение работает как локальный
# web-сервер + браузер (Chrome/Firefox).
#
#   python main_web.py                → http://0.0.0.0:8555 (откроется браузер)
#   python main_web.py --port 9000    → переопределение порта
#
# Перед запуском фиксируются:
#   PORAYONKA_WEB=1        — web-режим (трей/автозапуск пропускаются);
#   PORAYONKA_EDITION=user — read-only пользовательская редакция (setdefault:
#                            ТОЛЬКО dev-запуск; в frozen exe роль задаёт
#                            edition.json рядом/встроенный — раунд 37, чтобы
#                            общий вход работал и для admin web-сборки Win7).
# Дальше управление — общему входу main.py (`_entry()`), чтобы и dev-запуск,
# и frozen-бандл (Porayonka_User_Web.spec / Porayonka_Admin_Web.spec)
# работали одинаково: в frozen физического main.py на диске нет, поэтому НЕ
# runpy, а обычный импорт.
import os
import sys

# ── Раунд 38 (задача 3.3): стартовый лог ДО любых тяжёлых импортов ─────────
# Падение «важного» импорта (fastapi/pydantic и т.п.) в frozen console=False
# раньше терялось бесследно («серый экран» — «Failed to execute script
# 'main_web'»). Любая стадия запуска пишется ASCII-сообщением в
# %APPDATA%\porayonka\web_startup.log (перезаписывается при каждом запуске,
# идемпотентно, cp1251-безопасно).
def _startup_log(msg: str) -> None:
    try:
        from datetime import datetime
        appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
        logdir = os.path.join(appdata, "porayonka")
        os.makedirs(logdir, exist_ok=True)
        with open(os.path.join(logdir, "web_startup.log"), "a",
                  encoding="utf-8", errors="replace") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except Exception:
        pass
    try:
        print(f"[MAIN_WEB] {msg}")
    except Exception:
        pass


def _startup_log_reset() -> None:
    try:
        appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
        logdir = os.path.join(appdata, "porayonka")
        os.makedirs(logdir, exist_ok=True)
        with open(os.path.join(logdir, "web_startup.log"), "w",
                  encoding="utf-8", errors="replace") as f:
            from datetime import datetime
            f.write(f"[{datetime.now().isoformat()}] porayonka web startup\n")
    except Exception:
        pass


_startup_log_reset()
_startup_log("interpreter=%s frozen=%s" % (
    sys.version.replace("\n", " "), getattr(sys, "frozen", False)))

os.environ["PORAYONKA_WEB"] = "1"
# Раунд 37: env PORAYONKA_EDITION — только для dev-запуска `python
# main_web.py`. В frozen-сборках env игнорируется (раунд 34), а роль берётся
# из edition.json рядом/встроенного — иначе web-сборка АДМИНА для Win7
# тоже становилась бы «user» по этому setdefault.
if not getattr(sys, "frozen", False):
    os.environ.setdefault("PORAYONKA_EDITION", "user")

if "--web" not in sys.argv:
    sys.argv.insert(1, "--web")
if "--host" not in sys.argv:
    sys.argv += ["--host", "0.0.0.0"]
if "--port" not in sys.argv:
    sys.argv += ["--port", "8555"]


def _current_port() -> int:
    try:
        return int(sys.argv[sys.argv.index("--port") + 1])
    except Exception:
        return 8555


def _http_ok(port: int, timeout: float = 1.5) -> bool:
    """На указанном порту УЖЕ отвечает http-сервер (наш повторный запуск)."""
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/",
                                    timeout=timeout) as r:
            return 200 <= r.status < 500
    except Exception:
        return False


def _set_port(port: int) -> None:
    try:
        i = sys.argv.index("--port")
        sys.argv[i + 1] = str(port)
    except ValueError:
        sys.argv += ["--port", str(port)]


def _open_browser(port: int) -> None:
    try:
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{port}")
    except Exception:
        pass


# Раунд 38 (задача 3.3): повторный запуск НЕ дублирует сервер и браузер.
# - порт уже обслуживает наш сервер -> просто открыть браузер и выйти;
# - порт занят ЧУЖИМ процессом -> подобрать следующий свободный порт
#   (8556..8565) с понятной строкой в логе.
_port0 = _current_port()
if _http_ok(_port0):
    _startup_log(f"server already running on {_port0}: open browser, exit")
    _open_browser(_port0)
    sys.exit(0)
else:
    import socket
    for _cand in range(_port0, _port0 + 10):
        _s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            _s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            _s.bind(("0.0.0.0", _cand))
            _s.close()
            if _cand != _port0:
                # свободный порт найден, но вдруг там тоже наш сервер
                if _http_ok(_cand):
                    _startup_log(
                        f"server already running on {_cand}: open browser, exit")
                    _open_browser(_cand)
                    sys.exit(0)
                _startup_log(f"port {_port0} busy -> use {_cand}")
                _set_port(_cand)
            break
        except OSError:
            _s.close()
            if _http_ok(_cand):
                _startup_log(
                    f"server already running on {_cand}: open browser, exit")
                _open_browser(_cand)
                sys.exit(0)
            continue
    else:
        _startup_log("no free port in range 8555..8564")

from main import _entry, _ensure_console_streams

# Раунд 26 (задача 1): frozen onefile (console=False) → sys.stdout/stderr=None
# → uvicorn.logging падает ('NoneType'.isatty). Чиним ДО старта сервера.
_ensure_console_streams()

# Раунд 33 (задача 1.1): файловый лог необработанных исключений (frozen
# console=False). Явно — на случай, если main.py импортируется иначе.
try:
    from core.crash_log import install_crash_hook
    install_crash_hook()
except Exception:
    pass

_startup_log(f"starting server on port {_current_port()}")

if __name__ == "__main__":
    try:
        _entry()
    except SystemExit:
        raise
    except BaseException as _e38:
        # Раунд 38 (задача 3.3): import-time падение/ранняя ошибка uvicorn —
        # не теряем: полный traceback в web_startup.log + видимое окно в
        # frozen-сборке (MessageBox) с путём к логу.
        import traceback as _tb38
        _startup_log("FATAL: %s: %s\n%s" % (
            type(_e38).__name__, _e38, "".join(_tb38.format_tb(_e38.__traceback__))))
        try:
            if sys.platform.startswith("win") and getattr(sys, "frozen", False):
                import ctypes
                appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
                ctypes.windll.user32.MessageBoxW(
                    0,
                    "Порайонка (web) не запустилась.\n\n"
                    "Подробности в файле:\n"
                    + os.path.join(appdata, "porayonka", "web_startup.log"),
                    "Порайонка — ошибка запуска", 0x10)
        except Exception:
            pass
        raise

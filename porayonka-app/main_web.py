# main_web.py
# Раунд 24 (задача 2): точка входа WEB-версии для Windows 7 (пользовательская
# редакция). Нативный клиент Flet 0.23.2 (Flutter) требует Win10+, поэтому на
# Win7 приложение работает как локальный web-сервер + браузер (Chrome/Firefox).
#
#   python main_web.py                → http://0.0.0.0:8555 (откроется браузер)
#   python main_web.py --port 9000    → переопределение порта
#
# Перед запуском фиксируются:
#   PORAYONKA_WEB=1        — web-режим (трей/автозапуск пропускаются);
#   PORAYONKA_EDITION=user — read-only пользовательская редакция (setdefault:
#                            явное переопределение окружением допустимо для
#                            диагностики).
# Дальше управление — общему входу main.py (`_entry()`), чтобы и dev-запуск,
# и frozen-бандл (Porayonka_User_Web.spec) работали одинаково: в frozen
# физического main.py на диске нет, поэтому НЕ runpy, а обычный импорт.
import os
import sys

os.environ["PORAYONKA_WEB"] = "1"
os.environ.setdefault("PORAYONKA_EDITION", "user")

if "--web" not in sys.argv:
    sys.argv.insert(1, "--web")
if "--host" not in sys.argv:
    sys.argv += ["--host", "0.0.0.0"]
if "--port" not in sys.argv:
    sys.argv += ["--port", "8555"]

from main import _entry, _ensure_console_streams

# Раунд 26 (задача 1): frozen onefile (console=False) → sys.stdout/stderr=None
# → uvicorn.logging падает ('NoneType'.isatty). Чиним ДО старта сервера.
_ensure_console_streams()

if __name__ == "__main__":
    _entry()

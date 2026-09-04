# core/crash_log.py
# Раунд 33 (задача 1.1): файловое логирование НЕОБРАБОТАННЫХ исключений.
#
# В frozen-сборках PyInstaller (console=False) sys.stdout/stderr = None —
# падения не видны («серый экран» без единой строки в логе). Устанавливаем
# sys.excepthook: любое необработанное исключение пишется в
# %APPDATA%/porayonka/error.log (UTF-8, с ротацией: старый файл удаляется,
# если превысил 500 КБ), затем делегируется штатному sys.__excepthook__.
import os
import sys
import traceback
from datetime import datetime

ERROR_LOG_MAX_BYTES = 500_000


def _error_log_path() -> str:
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(appdata, "porayonka", "error.log")


def _write_error_log(text: str) -> None:
    try:
        path = _error_log_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            if os.path.exists(path) and os.path.getsize(path) > ERROR_LOG_MAX_BYTES:
                os.remove(path)
        except OSError:
            pass
        with open(path, "a", encoding="utf-8", errors="replace") as f:
            f.write(text)
            f.write("\n")
    except Exception:
        pass  # логирование не должно ронять приложение


write_error_log = _write_error_log


def _crash_hook(exc_type, exc_value, tb):
    try:
        lines = [f"[{datetime.now().isoformat()}] {exc_type.__name__}: {exc_value}"]
        lines.append("".join(traceback.format_tb(tb)))
        _write_error_log("\n".join(lines))
    except Exception:
        pass
    try:
        sys.__excepthook__(exc_type, exc_value, tb)
    except Exception:
        pass


def install_crash_hook() -> None:
    """Установить sys.excepthook (идемпотентно). Вызывать ПЕРВОЙ строкой в
    main.py / main_web.py."""
    try:
        if getattr(sys, "excepthook", None) is not _crash_hook:
            sys.excepthook = _crash_hook
    except Exception:
        pass

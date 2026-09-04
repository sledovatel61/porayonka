# core/single_instance.py
# Раунд 39 (задача 4): single-instance guard для desktop-редакций.
#
# Корень «двух значков в трее»: второй процесс ничем не останавливался — два
# pystray.Icon, два polling'а сроков, перетирающие друг друга записи
# controls.json. Guard — именованный mutex ядра в пространстве имён Local\
# (per-session, корректно для RDP + консоли; Global\ потребовал бы
# SeCreateGlobalPrivilege и сломал бы запуск под ограниченной учёткой):
#
#     CreateMutexW(NULL, FALSE, "Local\\Porayonka_<edition>")
#
# Состояния: acquired (мы первые) | already_exists (работать НЕЛЬЗЯ) |
# fail_open (API вызвать не удалось — приложение работает без защиты).
# ERROR_ALREADY_EXISTS — это НЕ ошибка API, а ответ ядра «экземпляр уже
# запущен»; трактовать его как fail-open = не починить баг вообще.
#
# GetLastError() читается СРАЗУ после CreateMutexW и только при предварительном
# SetLastError(0): успешные вызовы WinAPI last error не сбрасывают, а процесс
# до acquire() уже выполнял проверяющие вызовы (mkdir существующей папки ->
# ERROR_ALREADY_EXISTS, проверки реестра/файлов). Без обнуления первый
# экземпляр мог быть принят за второй и не запуститься вовсе.
#
# При already_exists выданный handle закрываем, иначе сами становимся
# держателем и мешаем реальному владельцу. Освобождение — «Выход» из трея,
# выход из ft.app и atexit; после падения процесса ядро снимает mutex само
# (в отличие от pid-файла «залипаний» не бывает).

import atexit
import ctypes
import os
import sys
import threading

ERROR_ALREADY_EXISTS = 183
_MUTEX_PREFIX = "Local\\Porayonka_"
_WINDOW_TITLE = "Порайонка — СК РФ Ростовская область"  # = page.title в main.py

_lock = threading.RLock()
_handle = None            # HANDLE (int) или None
_state = "none"           # none | acquired | already_exists | fail_open
_reason = ""


def mutex_name(edition: str = None) -> str:
    """Имя mutex'а: разные редакции (admin/user) — разные имена (это разные
    программы с разными данными, они могут работать одновременно), два
    экземпляра ОДНОЙ редакции — нет."""
    ed = (edition or "").strip().lower()
    if not ed:
        try:
            from core.edition import load_edition
            ed = str(load_edition().get("role") or "").strip().lower()
        except Exception:
            ed = ""
    if not ed:
        ed = os.environ.get("PORAYONKA_EDITION", "").strip().lower() or "app"
    # ASCII-safe: CreateMutexW unicode-безопасен, а вот лог — нет
    return _MUTEX_PREFIX + ed.encode("ascii", "replace").decode("ascii")


def _kernel32():
    return ctypes.windll.kernel32  # AttributeError вне Windows


def acquire(edition: str = None):
    """Занять guard. Возвращает (ok, reason):

    (True,  "acquired")       — мы первый экземпляр;
    (False, "already_exists") — экземпляр уже запущен, работать нельзя;
    (True,  "fail_open:<что>") — API недоступен, работаем без защиты.

    Идемпотентно: повторный вызов возвращает текущее состояние и НЕ создаёт
    второй handle.
    """
    global _handle, _state, _reason
    with _lock:
        if _state == "acquired":
            return True, "acquired"
        if _state == "already_exists":
            return False, "already_exists"
        if _state == "fail_open":
            return True, "fail_open:" + _reason

        if sys.platform != "win32":
            _state, _reason = "fail_open", "not_windows"
            return True, "fail_open:not_windows"

        name = mutex_name(edition)
        safe_name = name.encode("ascii", "replace").decode("ascii")
        try:
            k32 = _kernel32()
            k32.CreateMutexW.restype = ctypes.c_void_p
            k32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool,
                                         ctypes.c_wchar_p]
            k32.GetLastError.restype = ctypes.c_uint32
            k32.GetLastError.argtypes = []
            set_le = getattr(k32, "SetLastError", None)
            if callable(set_le):
                set_le(0)          # без этого err может быть ПРОШЛЫМ (см. шапку)
            h = k32.CreateMutexW(None, False, name)
            err = k32.GetLastError()
        except Exception as ex:
            _state, _reason = "fail_open", "%s: %s" % (type(ex).__name__, ex)
            print("[SINGLE_INSTANCE] fail-open (%s): %s" % (_reason, safe_name))
            return True, "fail_open:" + _reason

        if not h:
            _state, _reason = "fail_open", "null_handle(err=%s)" % err
            print("[SINGLE_INSTANCE] fail-open (%s)" % _reason)
            return True, "fail_open:" + _reason

        if err == ERROR_ALREADY_EXISTS:
            try:
                _kernel32().CloseHandle(ctypes.c_void_p(h))
            except Exception:
                pass
            _handle = None
            _state, _reason = "already_exists", name
            print("[SINGLE_INSTANCE] another instance is already running: %s"
                  % safe_name)
            return False, "already_exists"

        _handle = h
        _state, _reason = "acquired", name
        try:
            atexit.register(release)
        except Exception:
            pass
        print("[SINGLE_INSTANCE] guard acquired: %s" % safe_name)
        return True, "acquired"


def is_acquired() -> bool:
    """Наш ли это guard (первый экземпляр)."""
    with _lock:
        return _state == "acquired"


def status() -> str:
    """none/acquired/already_exists/fail_open."""
    with _lock:
        return _state


def detail() -> str:
    with _lock:
        return _reason


def already_running() -> bool:
    with _lock:
        return _state == "already_exists"


def release():
    """Освободить guard («Выход» из трея / штатное завершение). Идемпотентно,
    безопасно и без предварительного acquire()."""
    global _handle, _state, _reason
    with _lock:
        h, _handle = _handle, None
        _state, _reason = "none", ""
        if not h:
            return
        try:
            _kernel32().CloseHandle(ctypes.c_void_p(h))
            print("[SINGLE_INSTANCE] guard released")
        except Exception as ex:
            print("[SINGLE_INSTANCE] release error: %s: %s"
                  % (type(ex).__name__, ex))


def focus_existing(window_title: str = None):
    """Передать управление первому экземпляру (поднять его окно). Fail-soft:
    окно не найдено (свёрнуто в трей, другой заголовок, не Windows) — False."""
    title = window_title or _WINDOW_TITLE
    try:
        if sys.platform != "win32":
            return False
        u32 = ctypes.windll.user32
        hwnd = u32.FindWindowW(None, title)
        if not hwnd:
            print("[SINGLE_INSTANCE] existing window not found")
            return False
        if u32.IsIconic(hwnd):
            u32.ShowWindow(hwnd, 9)     # SW_RESTORE
        else:
            u32.ShowWindow(hwnd, 5)     # SW_SHOW
        u32.SetForegroundWindow(hwnd)
        print("[SINGLE_INSTANCE] existing window focused")
        return True
    except Exception as ex:
        print("[SINGLE_INSTANCE] focus error: %s: %s" % (type(ex).__name__, ex))
        return False

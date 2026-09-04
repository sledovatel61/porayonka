# core/single_instance.py
# ════════════════════════════════════════════════════════════════════════
# Раунд 39 (задача 4): SINGLE-INSTANCE guard (Windows named mutex).
# ════════════════════════════════════════════════════════════════════════
#
# КОРНЕВАЯ ПРИЧИНА «два значка в трее»: второй запущенный экземпляр
# приложения ничем не останавливался. Два процесса = два pystray.Icon =
# два значка, два polling'а сроков, две записи в controls.json (последний
# записавший перетирает чужие правки). Guard'а не было вообще: ни файла,
# ни порта, ни mutex'а.
#
# Решение — именованный mutex ядра Windows в пространстве имён Local\
# (per-session: у пользователя в RDP-сессии и в консоли свои экземпляры,
# что корректно; Global\ требовал бы SeCreateGlobalPrivilege и ломал бы
# обычный запуск под ограниченной учёткой — Win7-пользователи именно такие):
#
#     CreateMutexW(NULL, FALSE, "Local\\Porayonka_<edition>")
#
# Объект ядра живёт, пока жив хотя бы один держатель. Поэтому:
#   * CreateMutexW вернул handle и GetLastError()==0            -> МЫ первые;
#   * GetLastError()==ERROR_ALREADY_EXISTS (183)                -> уже есть
#     живой экземпляр, мы ВТОРЫЕ (handle всё равно валиден и его надо
#     закрыть, но приложению работать нельзя);
#   * сам API вызвать не удалось (не Windows / нет kernel32 /
#     исключение ctypes) -> FAIL-OPEN, приложение работает (лучше без
#     защиты, чем нерабочая программа).
#
# ВАЖНО: fail-open ДОПУСТИМ ТОЛЬКО при невозможности вызвать API.
# ERROR_ALREADY_EXISTS — это НЕ ошибка API, а внятный ответ ядра
# «экземпляр уже запущен»; трактовать его как fail-open — значит не
# починить баг вообще.
#
# Освобождение: «Выход» в трее и завершение процесса. Ядро закроет handle
# и при аварийном падении (mutex снимается автоматически) — «залипшего»
# guard'а после краха не бывает, в отличие от pid-файла.

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
    """Имя mutex'а. Разные редакции (admin/user) — разные имена: админская
    и пользовательская сборки могут работать одновременно (это разные
    программы с разными данными), а два экземпляра ОДНОЙ редакции — нет."""
    ed = (edition or "").strip().lower()
    if not ed:
        try:
            from core.edition import load_edition
            ed = str(load_edition().get("role") or "").strip().lower()
        except Exception:
            ed = ""
    if not ed:
        ed = os.environ.get("PORAYONKA_EDITION", "").strip().lower() or "app"
    # имя mutex'а — ASCII-safe (cp1251-роль из edition.json не ожидаем, но
    # перестрахуемся: CreateMutexW unicode-safe, а вот лог — нет).
    ed = ed.encode("ascii", "replace").decode("ascii")
    return _MUTEX_PREFIX + ed


def _kernel32():
    return ctypes.windll.kernel32  # AttributeError вне Windows


def acquire(edition: str = None):
    """Занять single-instance guard.

    Возвращает (ok: bool, reason: str):
      (True,  "acquired")        — мы первый экземпляр, работаем;
      (False, "already_exists")  — экземпляр уже запущен, работать НЕЛЬЗЯ;
      (True,  "fail_open:<что>") — API недоступен, работаем без защиты.
    Идемпотентно: повторный вызов из того же процесса возвращает текущее
    состояние и НЕ создаёт второй handle.
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
            # Не Windows (Linux-разработка, CI) — named mutex'а нет.
            _state, _reason = "fail_open", "not_windows"
            return True, "fail_open:not_windows"

        name = mutex_name(edition)
        try:
            k32 = _kernel32()
            k32.CreateMutexW.restype = ctypes.c_void_p
            k32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool,
                                         ctypes.c_wchar_p]
            k32.GetLastError.restype = ctypes.c_uint32
            k32.GetLastError.argtypes = []
            h = k32.CreateMutexW(None, False, name)
            err = k32.GetLastError()
        except Exception as ex:
            # API вызвать не удалось -> fail-open (явно диагностировано).
            _state, _reason = "fail_open", "%s: %s" % (type(ex).__name__, ex)
            print("[SINGLE_INSTANCE] fail-open (%s): %s"
                  % (_reason, name.encode("ascii", "replace").decode("ascii")))
            return True, "fail_open:" + _reason

        if not h:
            _state, _reason = "fail_open", "null_handle(err=%s)" % err
            print("[SINGLE_INSTANCE] fail-open (%s)" % _state)
            return True, "fail_open:" + _reason

        if err == ERROR_ALREADY_EXISTS:
            # Валидный handle, но экземпляр уже есть. Handle закрываем
            # (иначе сами становимся «держателем» и мешаем реальному
            # владельцу определить своё одиночество) — guard НЕ наш.
            try:
                _kernel32().CloseHandle(ctypes.c_void_p(h))
            except Exception:
                pass
            _handle = None
            _state, _reason = "already_exists", name
            print("[SINGLE_INSTANCE] another instance is already running: %s"
                  % name.encode("ascii", "replace").decode("ascii"))
            return False, "already_exists"

        _handle = h
        _state, _reason = "acquired", name
        try:
            atexit.register(release)
        except Exception:
            pass
        print("[SINGLE_INSTANCE] guard acquired: %s"
              % name.encode("ascii", "replace").decode("ascii"))
        return True, "acquired"


def is_acquired() -> bool:
    """Наш ли это guard (первый экземпляр)."""
    with _lock:
        return _state == "acquired"


def status() -> str:
    """Текущее состояние guard'а: none/acquired/already_exists/fail_open."""
    with _lock:
        return _state


def detail() -> str:
    with _lock:
        return _reason


def already_running() -> bool:
    with _lock:
        return _state == "already_exists"


def release():
    """Освободить guard («Выход» из трея / штатное завершение).
    Идемпотентно; безопасно вызывать несколько раз и без acquire()."""
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
    """Передать управление первому экземпляру: поднять его окно на передний
    план. Fail-soft — если окно не найдено (свёрнуто в трей, другой
    заголовок, не Windows), просто возвращает False, ничего не ломая."""
    title = window_title or _WINDOW_TITLE
    try:
        if sys.platform != "win32":
            return False
        u32 = ctypes.windll.user32
        hwnd = u32.FindWindowW(None, title)
        if not hwnd:
            print("[SINGLE_INSTANCE] existing window not found")
            return False
        SW_RESTORE = 9
        SW_SHOW = 5
        if u32.IsIconic(hwnd):
            u32.ShowWindow(hwnd, SW_RESTORE)
        else:
            u32.ShowWindow(hwnd, SW_SHOW)
        u32.SetForegroundWindow(hwnd)
        print("[SINGLE_INSTANCE] existing window focused")
        return True
    except Exception as ex:
        print("[SINGLE_INSTANCE] focus error: %s: %s" % (type(ex).__name__, ex))
        return False

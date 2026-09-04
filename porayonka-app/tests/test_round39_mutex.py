# -*- coding: utf-8 -*-
"""Раунд 39 (задача 4): single-instance guard — ДЕТЕРМИНИРОВАННЫЕ тесты.

Почему отдельный файл и почему переписан
────────────────────────────────────────
В версии кандидата проверки r39-4.5a/4.5b выглядели так:

    si.release()
    ok, why = si.acquire("admin")
    check("не-Windows -> fail-open", ok is True and why.startswith("fail_open"))

то есть исход зависел от ФАКТИЧЕСКОЙ платформы прогона. На Linux он
случайно совпадал с ожиданием, а на Windows тот же код честно получал
"acquired" и давал 2 FAIL. Это дефект ТЕСТА, а не production-кода:
core/single_instance.py ведёт себя ровно так, как требует задание.

Здесь платформа и kernel32 всегда подменяются явно, поэтому результат
одинаков на любой ОС. Покрыты все шесть требуемых сценариев:

  1. Windows -> acquired;
  2. Windows -> already_running (ERROR_ALREADY_EXISTS, НЕ fail-open);
  3. WinAPI error -> fail-open;
  4. НАСТОЯЩИЙ non-Windows -> fail-open (sys.platform принудительно "linux");
  5. release / идемпотентность;
  6. конкурентный acquire из многих потоков.
"""
import importlib
import os
import sys
import threading
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from r39_harness import (                                   # noqa: E402
    check, check_no_thread_errors, install_thread_guard, read_src, report,
)


class _CFunc:
    """Подделка ctypes-функции: вызывается И принимает restype/argtypes.

    Production-код делает `k32.CreateMutexW.restype = ...` — на bound-методе
    это AttributeError, поэтому нужен именно объект с __dict__.
    """

    def __init__(self, fn):
        self._fn = fn
        self.restype = None
        self.argtypes = None

    def __call__(self, *a, **kw):
        return self._fn(*a, **kw)


class FakeKernel32:
    """Поддельный kernel32 с управляемым GetLastError и счётчиками."""

    def __init__(self):
        self.create = 0
        self.close = 0
        self.lasterr = 0
        self.last_name = None
        self.handle = 0x1234
        self.raise_on_create = None
        self.CreateMutexW = _CFunc(self._create)
        self.GetLastError = _CFunc(self._lasterr)
        self.CloseHandle = _CFunc(self._close)

    def _create(self, sec, initial, name):
        self.create += 1
        self.last_name = name
        if self.raise_on_create is not None:
            raise self.raise_on_create
        return self.handle

    def _lasterr(self):
        return self.lasterr

    def _close(self, h):
        self.close += 1
        return 1


def _fake_ctypes(k32, u32=None):
    m = types.ModuleType("ctypes")
    m.windll = types.SimpleNamespace(kernel32=k32, user32=u32)
    # эти вызываются в production-коде — нужны callables
    m.c_void_p = lambda x=None: x
    m.c_bool = lambda x=None: x
    m.c_wchar_p = lambda x=None: x
    m.c_uint32 = lambda x=None: x
    return m


class _env:
    """Подменить sys.platform и модуль ctypes, перезагрузить single_instance."""

    def __init__(self, platform, ctypes_mod=None):
        self.platform, self.ctypes_mod = platform, ctypes_mod

    def __enter__(self):
        self._plat = sys.platform
        self._ct = sys.modules.get("ctypes")
        sys.platform = self.platform
        if self.ctypes_mod is not None:
            sys.modules["ctypes"] = self.ctypes_mod
        from core import single_instance as si
        self.si = importlib.reload(si)
        return self.si

    def __exit__(self, *a):
        try:
            self.si.release()
        except Exception:
            pass
        sys.platform = self._plat
        if self._ct is not None:
            sys.modules["ctypes"] = self._ct
        else:
            sys.modules.pop("ctypes", None)
        from core import single_instance as si
        importlib.reload(si)
        return False


# ── 1. Windows: свежий mutex -> acquired ─────────────────────────────────
def test_windows_acquired():
    print("\n=== 4.1 Windows: свежий mutex -> acquired ===")
    k = FakeKernel32()
    k.lasterr = 0
    with _env("win32", _fake_ctypes(k)) as si:
        ok, why = si.acquire("admin")
        check("r39-4.1a: Windows, свободный mutex -> acquired",
              ok is True and why == "acquired", why)
        check("r39-4.1b: is_acquired() True", si.is_acquired() is True)
        check("r39-4.1c: status() == acquired", si.status() == "acquired",
              si.status())
        check("r39-4.1d: CreateMutexW вызван РОВНО один раз", k.create == 1,
              str(k.create))
        check("r39-4.1e: имя mutex'а Local\\Porayonka_admin",
              k.last_name == "Local\\Porayonka_admin", str(k.last_name))
        check("r39-4.1f: handle НЕ закрыт (guard наш и держится)",
              k.close == 0, str(k.close))
        # идемпотентность acquire
        ok2, why2 = si.acquire("admin")
        check("r39-4.1g: повторный acquire идемпотентен, 2-го handle нет",
              ok2 is True and why2 == "acquired" and k.create == 1,
              "%s creates=%d" % (why2, k.create))
        check("r39-4.1h: разные редакции -> разные имена mutex'а",
              si.mutex_name("admin") != si.mutex_name("user"),
              si.mutex_name("user"))


# ── 2. Windows: mutex занят -> already_running (НЕ fail-open) ────────────
def test_windows_already_running():
    print("\n=== 4.2 Windows: mutex занят -> already_running ===")
    k = FakeKernel32()
    k.lasterr = 183  # ERROR_ALREADY_EXISTS
    with _env("win32", _fake_ctypes(k)) as si:
        check("r39-4.2a: константа ERROR_ALREADY_EXISTS == 183",
              si.ERROR_ALREADY_EXISTS == 183, str(si.ERROR_ALREADY_EXISTS))
        ok, why = si.acquire("admin")
        check("r39-4.2b: занятый mutex -> работать НЕЛЬЗЯ",
              ok is False and why == "already_exists", why)
        check("r39-4.2c: это НЕ fail-open (ключевое требование задания)",
              not why.startswith("fail_open")
              and si.status() == "already_exists", si.status())
        check("r39-4.2d: already_running() True",
              si.already_running() is True)
        check("r39-4.2e: is_acquired() False — guard не наш",
              si.is_acquired() is False)
        check("r39-4.2f: чужой handle закрыт (не мешаем владельцу)",
              k.close == 1, str(k.close))
        ok2, why2 = si.acquire("admin")
        check("r39-4.2g: повторный acquire при занятом mutex тоже отказывает",
              ok2 is False and why2 == "already_exists", why2)


# ── 3. Ошибка WinAPI -> fail-open ────────────────────────────────────────
def test_winapi_error_fail_open():
    print("\n=== 4.3 Ошибка WinAPI -> fail-open ===")
    # 3a. windll вообще нет (ctypes без windll — AttributeError)
    broken = types.ModuleType("ctypes")
    with _env("win32", broken) as si:
        ok, why = si.acquire("admin")
        check("r39-4.3a: нет kernel32 -> fail-open (приложение работает)",
              ok is True and why.startswith("fail_open"), why)
        check("r39-4.3b: fail-open НЕ помечает guard «нашим»",
              si.is_acquired() is False and si.status() == "fail_open",
              si.status())
        check("r39-4.3c: причина fail-open явно диагностирована",
              bool(si.detail()), si.detail())

    # 3b. CreateMutexW бросает исключение
    k = FakeKernel32()
    k.raise_on_create = OSError("access denied")
    with _env("win32", _fake_ctypes(k)) as si:
        ok, why = si.acquire("admin")
        check("r39-4.3d: исключение в CreateMutexW -> fail-open",
              ok is True and why.startswith("fail_open"), why)
        check("r39-4.3e: тип исключения попал в диагностику",
              "OSError" in si.detail(), si.detail())

    # 3c. CreateMutexW вернул NULL
    k2 = FakeKernel32()
    k2.handle = 0
    k2.lasterr = 5
    with _env("win32", _fake_ctypes(k2)) as si:
        ok, why = si.acquire("admin")
        check("r39-4.3f: NULL handle -> fail-open с кодом ошибки",
              ok is True and why.startswith("fail_open")
              and "null_handle" in why, why)
        check("r39-4.3g: NULL handle — это НЕ already_running",
              si.already_running() is False)


# ── 4. НАСТОЯЩИЙ non-Windows -> fail-open ────────────────────────────────
def test_real_non_windows_fail_open():
    print("\n=== 4.4 Настоящий non-Windows -> fail-open ===")
    # Именно здесь чинится дефект тестов кандидата: платформа задаётся
    # ЯВНО, а не берётся из окружения прогона. На Windows этот тест теперь
    # тоже проходит.
    k = FakeKernel32()
    with _env("linux", _fake_ctypes(k)) as si:
        ok, why = si.acquire("admin")
        check("r39-4.4a: non-Windows -> fail-open (приложение работает)",
              ok is True and why == "fail_open:not_windows", why)
        check("r39-4.4b: причина именно not_windows, а не ошибка API",
              si.detail() == "not_windows", si.detail())
        check("r39-4.4c: guard НЕ «наш» (is_acquired False)",
              si.is_acquired() is False and si.status() == "fail_open",
              si.status())
        check("r39-4.4d: на non-Windows WinAPI не дёргается вообще",
              k.create == 0, str(k.create))
        check("r39-4.4e: already_running() False", si.already_running() is False)
        check("r39-4.4f: focus_existing на non-Windows — мягкий False",
              si.focus_existing("Порайонка") is False)

    with _env("darwin", _fake_ctypes(FakeKernel32())) as si:
        ok, why = si.acquire("user")
        check("r39-4.4g: macOS -> тот же fail-open:not_windows",
              ok is True and why == "fail_open:not_windows", why)


# ── 5. release / идемпотентность ─────────────────────────────────────────
def test_release_idempotency():
    print("\n=== 4.5 release / идемпотентность ===")
    k = FakeKernel32()
    with _env("win32", _fake_ctypes(k)) as si:
        si.acquire("admin")
        check("r39-4.5a: перед release guard наш", si.is_acquired() is True)
        si.release()
        check("r39-4.5b: release() сбрасывает состояние в none",
              si.status() == "none" and si.is_acquired() is False, si.status())
        check("r39-4.5c: release() закрыл handle РОВНО один раз",
              k.close == 1, str(k.close))
        n = k.close
        si.release()
        si.release()
        check("r39-4.5d: повторный release идемпотентен (лишнего CloseHandle нет)",
              k.close == n, str(k.close))
        # после release guard можно занять снова (важно для «Выход» -> запуск)
        k.lasterr = 0
        ok, why = si.acquire("admin")
        check("r39-4.5e: после release guard занимается ЗАНОВО "
              "(повторный запуск после «Выхода» возможен)",
              ok is True and why == "acquired", why)

    # release без acquire не падает
    with _env("win32", _fake_ctypes(FakeKernel32())) as si:
        si.release()
        check("r39-4.5f: release() без acquire() безопасен",
              si.status() == "none", si.status())


# ── 6. Конкурентный acquire ──────────────────────────────────────────────
def test_concurrent_acquire():
    print("\n=== 4.6 Конкурентный acquire ===")
    N = 16
    k = FakeKernel32()
    k.lasterr = 0
    with _env("win32", _fake_ctypes(k)) as si:
        barrier = threading.Barrier(N)
        results = []
        lock = threading.Lock()

        def worker():
            barrier.wait()
            r = si.acquire("admin")
            with lock:
                results.append(r)

        ts = [threading.Thread(target=worker, name="r39-acq-%d" % i)
              for i in range(N)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(10)

        check("r39-4.6a: все %d потоков вернулись" % N,
              len(results) == N, str(len(results)))
        check("r39-4.6b: КОНКУРЕНТНО создан ровно ОДИН mutex-handle",
              k.create == 1, str(k.create))
        check("r39-4.6c: все потоки получили один и тот же ответ acquired",
              all(r == (True, "acquired") for r in results),
              str(set(results)))
        check("r39-4.6d: итоговое состояние — acquired",
              si.is_acquired() is True and si.status() == "acquired",
              si.status())
        check("r39-4.6e: лишних CloseHandle при гонке нет",
              k.close == 0, str(k.close))

    # конкурентная гонка при уже занятом mutex: никто не должен «проскочить»
    k2 = FakeKernel32()
    k2.lasterr = 183
    with _env("win32", _fake_ctypes(k2)) as si:
        barrier = threading.Barrier(N)
        res2 = []
        lock2 = threading.Lock()

        def worker2():
            barrier.wait()
            r = si.acquire("admin")
            with lock2:
                res2.append(r)

        ts = [threading.Thread(target=worker2, name="r39-busy-%d" % i)
              for i in range(N)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(10)
        check("r39-4.6f: при занятом mutex НИ ОДИН из %d потоков не стартует" % N,
              all(r == (False, "already_exists") for r in res2),
              str(set(res2)))
        check("r39-4.6g: CreateMutexW при гонке вызван один раз",
              k2.create == 1, str(k2.create))


# ── 7. main.py: guard подключён в desktop-ветке ──────────────────────────
def test_main_wiring():
    print("\n=== 4.7 main.py: guard в desktop-ветке ===")
    src = read_src("main.py")
    i_entry = src.index("def _entry():")
    i_desktop = src.index("ft.app(target=main)")
    seg = src[i_entry:i_desktop]
    check("r39-4.7a: guard занимается ДО ft.app(target=main)",
          "single_instance" in seg and "acquire()" in seg)
    check("r39-4.7b: при занятом guard процесс не стартует, а передаёт "
          "управление первому экземпляру",
          "focus_existing()" in seg and "return" in seg)
    check("r39-4.7c: guard освобождается при выходе", "_si39b.release()" in src)
    # Web-ветка (от начала _entry до её собственного ft.app) не должна
    # занимать desktop-guard: web-процесс — это сервер, а не второе окно.
    i_web = src.index("ft.app(target=main, view=")
    web_branch = src[i_entry:i_web]
    check("r39-4.7d: web-ветка НЕ занимает desktop single-instance guard",
          "single_instance" not in web_branch and "_si39.acquire" not in web_branch)
    check("r39-4.7e: guard живёт именно в desktop-ветке (после web ft.app)",
          i_web < src.index("from core import single_instance as _si39")
          < i_desktop)


def main():
    install_thread_guard()
    for fn in (test_windows_acquired, test_windows_already_running,
               test_winapi_error_fail_open, test_real_non_windows_fail_open,
               test_release_idempotency, test_concurrent_acquire,
               test_main_wiring):
        print("\n" + "=" * 70)
        try:
            fn()
        except Exception:
            import traceback
            check(fn.__name__ + " [exception]", False)
            traceback.print_exc()
    check_no_thread_errors("single-instance")
    sys.exit(report("Round 39 / single-instance"))


if __name__ == "__main__":
    main()

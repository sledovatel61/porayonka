# -*- coding: utf-8 -*-
"""Раунд 39: общий харнесс проверок (изолированные данные + перехват фона).

Используется только tests/test_round39.py и группами r39_logic / r39_ui /
r39_static. Смысл:

  * check() — единственная точка учёта результата (FAIL -> exit code 1);
  * skip() — честно помечает то, что физически не проверялось на этой ОС
    (SKIP не считается успехом и не считается падением);
  * guard_thread_errors() — ЛЮБОЕ необработанное исключение в фоновом потоке
    (pystray setup_handler, поллинг вложений, _post_to_ui) превращается в FAIL
    прогона, а не в «красивый» ALL OK с трейсбеком в стороне;
  * walk/find/click — работа с ДЕРЕВОМ реальных Flet-контролов: проверки
    идут через настоящие обработчики, а не присваиванием ожидаемого значения.
"""
import contextlib
import io
import os
import sys
import threading
import traceback

FAILURES = []
THREAD_ERRORS = []
SKIPPED = []


def check(name, cond, extra=""):
    status = "OK " if cond else "FAIL"
    try:
        print(f"[{status}] {name}" + (f"  ({extra})" if extra else ""))
    except UnicodeEncodeError:
        print(f"[{status}] <non-cp1251 output>", file=sys.stderr)
        FAILURES.append(name + " [non-cp1251 output]")
        return
    if not cond:
        FAILURES.append(name)


def skip(name, why):
    try:
        print(f"[SKIP] {name}  ({why})")
    except UnicodeEncodeError:
        print("[SKIP] <non-cp1251 output>")
    SKIPPED.append(name)


def guard_thread_errors():
    """Необработанные исключения фоновых потоков -> FAIL прогона.

    threading.excepthook (3.8+) перехватывает всё, что падает в потоке,
    sys.unraisablehook — то, что падает в __del__/GC-колбэках. Оба пишут в
    THREAD_ERRORS; раннер превращает непустой список в FAIL.
    """
    def _hook(args):
        thr = getattr(args, "thread", None)
        name = getattr(thr, "name", "?")
        exc = args.exc_value
        THREAD_ERRORS.append(
            "thread %s: %s: %s\n%s" % (
                name, type(exc).__name__, exc,
                "".join(traceback.format_tb(exc.__traceback__))))

    def _unraisable(unraisable):
        THREAD_ERRORS.append(
            "unraisable %s: %s: %s" % (getattr(unraisable, "object_type", "?"),
                                       type(unraisable.exc_value).__name__,
                                       unraisable.exc_value))

    def _worker():
        raise RuntimeError("r39-guard-selftest")

    threading.excepthook = _hook
    sys.unraisablehook = _unraisable

    # САМОПРОВЕРКА харнесса: если guard не работает, остальной прогон
    # не имеет права выдавать ALL OK при падающем фоне.
    t = threading.Thread(target=_worker, name="r39-guard-selftest")
    t.start()
    t.join(5)
    caught = any("r39-guard-selftest" in e for e in THREAD_ERRORS)
    check("r39-0.1: харнесс перехватывает исключение фонового потока", caught)
    THREAD_ERRORS[:] = [e for e in THREAD_ERRORS if "r39-guard-selftest" not in e]
    return caught


def fail_on_thread_errors(stage=""):
    for e in THREAD_ERRORS:
        FAILURES.append("фоновое исключение%s: %s" % (stage, e.splitlines()[0]))
        print("    " + e.replace("\n", "\n    "))


class force_platform:
    """Временно сделать sys.platform=PLATFORM (или вернуть обратно).

    Никаких «если мы не на Windows — ждём fail-open»: обе ветки проверяются
    детерминированно на ЛЮБОЙ ОС.
    """

    def __init__(self, platform):
        self.platform = platform
        self._old = None

    def __enter__(self):
        self._old = sys.platform
        if self.platform is not None:
            sys.platform = self.platform
        return self

    def __exit__(self, *a):
        sys.platform = self._old
        return False


class blocked_module:
    """sys.modules[name] = None -> import бросает ImportError (нет библиотеки)."""

    def __init__(self, **mods):
        self.mods = mods
        self._old = {}

    def __enter__(self):
        for nm, obj in self.mods.items():
            self._old[nm] = sys.modules.get(nm, "__absent__")
            if obj is None:
                sys.modules[nm] = None
            else:
                sys.modules[nm] = obj
        return self

    def __exit__(self, *a):
        for nm, v in self._old.items():
            if v == "__absent__":
                sys.modules.pop(nm, None)
            else:
                sys.modules[nm] = v
        return False


# ── обход дерева Flet-контролов ──────────────────────────────────────────
def walk(c, seen=None):
    if seen is None:
        seen = set()
    res = []
    if c is None or id(c) in seen:
        return res
    seen.add(id(c))
    res.append(c)
    for attr in ("content", "controls", "title", "actions", "badge"):
        v = getattr(c, attr, None)
        if isinstance(v, (list, tuple)):
            for x in v:
                res += walk(x, seen)
        elif v is not None and type(v).__module__.startswith("flet"):
            res += walk(v, seen)
    return res


def texts(root, out=None):
    import flet as ft
    if out is None:
        out = set()
    for c in walk(root):
        if isinstance(c, ft.Text) and getattr(c, "value", None):
            out.add(str(c.value))
    return out


def find(root, cls, **attrs):
    out = []
    for c in walk(root):
        if not isinstance(c, cls):
            continue
        if all(getattr(c, k, None) == v for k, v in attrs.items()):
            out.append(c)
    return out


def click(root, cls, **attrs):
    """Кликнуть первый подходящий контрол ЕГО ЖЕ реальным on_click."""
    for c in find(root, cls, **attrs):
        fn = getattr(c, "on_click", None)
        if callable(fn):
            fn(None)
            return True
    return False


def click_tooltip(root, cls, needle):
    for c in find(root, cls):
        if needle in str(getattr(c, "tooltip", "") or ""):
            fn = getattr(c, "on_click", None)
            if callable(fn):
                fn(None)
                return c
    return None

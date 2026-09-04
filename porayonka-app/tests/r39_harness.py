# -*- coding: utf-8 -*-
"""Раунд 39: общий харнес тестов (check, обход дерева Flet, страж потоков).

Вынесен из монолитного tests/test_round39.py, чтобы static-, mock- и
integration-проверки жили в разных файлах и переиспользовали одно и то же.
"""
import io
import os
import sys
import threading
import traceback

FAILURES = []


def check(name, cond, extra=""):
    """Записать проверку. Не-cp1251 вывод в консоли Win7 — это тоже FAIL."""
    status = "OK " if cond else "FAIL"
    try:
        print(f"[{status}] {name}" + (f"  ({extra})" if extra else ""))
    except UnicodeEncodeError:
        print(f"[{status}] <non-cp1251 output>", file=sys.stderr)
        FAILURES.append(name + " [non-cp1251 output]")
        return
    if not cond:
        FAILURES.append(name)


# ── страж фоновых потоков ────────────────────────────────────────────────
# Требование ревью: необработанное исключение в фоновом потоке (например,
# pystray setup_handler на SimpleNamespace без register_open) НЕ должно
# молча печататься в stderr и теряться — оно обязано приводить к FAIL.
_THREAD_ERRORS = []


def install_thread_guard():
    """Перехватывать исключения фоновых потоков (threading.excepthook)."""
    def _hook(args):
        txt = "".join(traceback.format_exception(
            args.exc_type, args.exc_value, args.exc_traceback))
        _THREAD_ERRORS.append(
            "%s in thread %s: %s"
            % (args.exc_type.__name__,
               getattr(args.thread, "name", "?"), args.exc_value))
        try:
            sys.stderr.write(txt)
        except Exception:
            pass
    try:
        threading.excepthook = _hook
    except Exception:
        pass


def thread_errors():
    return list(_THREAD_ERRORS)


def check_no_thread_errors(label="фоновые потоки"):
    """Отдельная проверка: за прогон не было необработанных исключений."""
    errs = thread_errors()
    check("r39-0.thread: %s — без необработанных исключений" % label,
          not errs, "; ".join(errs[:3]))
    del _THREAD_ERRORS[:]


def report(title="Round 39"):
    """Итог прогона; возвращает код возврата процесса."""
    print("\n" + "=" * 70)
    if FAILURES:
        print(f"{title}: FAILED: {len(FAILURES)}")
        for f in FAILURES:
            try:
                print("  - " + f)
            except UnicodeEncodeError:
                print("  - <non-cp1251>")
        return 1
    print(f"{title}: ALL OK")
    return 0


# ── обход дерева контролов Flet ──────────────────────────────────────────
def walk(c, seen=None):
    """Обойти дерево контролов Flet (content/controls/title/actions/badge)."""
    import flet as ft  # noqa: F401 — нужен только как признак модуля
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
        elif v is not None and hasattr(v, "_Control__uid") or (
                v is not None and v.__class__.__module__.startswith("flet")):
            res += walk(v, seen)
    return res


def texts(root):
    import flet as ft
    return {str(t.value) for t in walk(root)
            if isinstance(t, ft.Text) and getattr(t, "value", None)}


def find(root, cls, **attrs):
    """Все контролы класса cls с совпадающими атрибутами."""
    out = []
    for c in walk(root):
        if not isinstance(c, cls):
            continue
        if all(getattr(c, k, None) == v for k, v in attrs.items()):
            out.append(c)
    return out


def click(root, cls, text=None, tooltip=None):
    """Кликнуть первый контрол cls с нужным text/tooltip. True если нашли."""
    kw = {}
    if text is not None:
        kw["text"] = text
    if tooltip is not None:
        kw["tooltip"] = tooltip
    for c in find(root, cls, **kw):
        fn = getattr(c, "on_click", None)
        if callable(fn):
            fn(None)
            return True
    return False


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_src(*parts):
    return io.open(os.path.join(repo_root(), *parts), encoding="utf-8").read()

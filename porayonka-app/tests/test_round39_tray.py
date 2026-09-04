# -*- coding: utf-8 -*-
"""Раунд 39 (задача 4, tray-часть): один pystray.Icon, отсутствие двойного stop.

Отличие от версии кандидата
───────────────────────────
Кандидат подменял pystray объектом types.SimpleNamespace, у которого нет
register_open/_handler. Поддельный Icon.run_detached() ничего не делал, но
в тестах, где к значку обращались как к настоящему, фоновой поток pystray
падал с необработанным AttributeError ('SimpleNamespace' has no attribute
register_open') — traceback печатался в stderr и НЕ приводил к FAIL.

Здесь:
  * фейковый Icon имитирует pystray честно: run_detached() запускает
    настоящий поток setup-handler'а;
  * threading.excepthook перехвачен (r39_harness.install_thread_guard) —
    любое необработанное исключение фонового потока даёт FAIL.
"""
import os
import sys
import threading
import time
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from r39_harness import (                                   # noqa: E402
    check, check_no_thread_errors, install_thread_guard, read_src, report,
)


class FakeIcon:
    """Имитация pystray.Icon, включая фоновый setup-поток."""

    def __init__(self, state, name, image, title, menu):
        self.state = state
        self.name, self.image, self.title, self.menu = name, image, title, menu
        self.visible = False
        self._thread = None
        state["icons"] += 1

    # pystray.Icon.run_detached() поднимает поток и зовёт setup-handler
    def run_detached(self, setup=None):
        self.state["detached"] += 1

        def _run():
            # Реальный pystray здесь трогает внутренности значка. Если
            # объект-заглушка их не имеет — тут и рождался тот самый
            # необработанный AttributeError фонового потока.
            self.register_open()
            self.visible = True
            if setup is not None:
                setup(self)

        self._thread = threading.Thread(target=_run, name="fake-pystray",
                                        daemon=True)
        self._thread.start()

    def register_open(self):
        self.state["opened"] += 1

    def stop(self):
        self.state["stopped"] += 1
        self.visible = False

    def notify(self, message, title=None):
        self.state["notify"] += 1
        return True


def _fake_pystray(state):
    def _Icon(name, image, title, menu):
        return FakeIcon(state, name, image, title, menu)

    def _MenuItem(text, action, default=False):
        return types.SimpleNamespace(text=text, action=action, default=default)

    def _Menu(*items):
        return types.SimpleNamespace(items=items)

    return types.SimpleNamespace(Icon=_Icon, MenuItem=_MenuItem, Menu=_Menu)


class _win_tray:
    """sys.platform=win32 + подменённые pystray/PIL + reload ui.tray_icon."""

    def __init__(self, state):
        self.state = state

    def __enter__(self):
        import importlib
        self._plat = sys.platform
        sys.platform = "win32"
        self._old = {}
        pil = types.ModuleType("PIL")
        pil.Image = types.SimpleNamespace(open=lambda p: object())
        for nm, mod in (("pystray", _fake_pystray(self.state)), ("PIL", pil)):
            self._old[nm] = sys.modules.get(nm, "__absent__")
            sys.modules[nm] = mod
        import ui.tray_icon as ti
        self.ti = importlib.reload(ti)
        return self.ti

    def __exit__(self, *a):
        import importlib
        try:
            self.ti.stop_tray()
        except Exception:
            pass
        sys.platform = self._plat
        for nm, v in self._old.items():
            if v == "__absent__":
                sys.modules.pop(nm, None)
            else:
                sys.modules[nm] = v
        import ui.tray_icon as ti
        importlib.reload(ti)
        return False


def _settle():
    """Дать фоновым потокам pystray отработать (и упасть, если упадут)."""
    time.sleep(0.15)


# ── 1. Повторный вызов start_tray ────────────────────────────────────────
def test_repeat_start():
    print("\n=== 4T.1 Повторный start_tray ===")
    st = {"icons": 0, "stopped": 0, "detached": 0, "opened": 0, "notify": 0}
    with _win_tray(st) as ti:
        i1 = ti.start_tray(None, web_url="http://127.0.0.1:8555")
        i2 = ti.start_tray(None, web_url="http://127.0.0.1:8555")
        i3 = ti.start_tray(object())
        _settle()
        check("r39-4T.1a: повторный start_tray возвращает ТОТ ЖЕ icon",
              i1 is not None and i1 is i2 and i2 is i3)
        check("r39-4T.1b: pystray.Icon создан РОВНО один раз",
              st["icons"] == 1, str(st["icons"]))
        check("r39-4T.1c: run_detached вызван один раз",
              st["detached"] == 1, str(st["detached"]))
        check("r39-4T.1d: get_active_icon() отдаёт тот же значок",
              ti.get_active_icon() is i1)
        check("r39-4T.1e: фоновый setup значка отработал",
              st["opened"] == 1, str(st["opened"]))


# ── 2. Конкурентный start_tray ───────────────────────────────────────────
def test_concurrent_start():
    print("\n=== 4T.2 Конкурентный start_tray ===")
    st = {"icons": 0, "stopped": 0, "detached": 0, "opened": 0, "notify": 0}
    with _win_tray(st) as ti:
        N = 16
        barrier = threading.Barrier(N)
        got, lock = [], threading.Lock()

        def w():
            barrier.wait()
            ic = ti.start_tray(None, web_url="http://127.0.0.1:8555")
            with lock:
                got.append(ic)

        ts = [threading.Thread(target=w, name="r39-tray-%d" % i)
              for i in range(N)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(10)
        _settle()
        check("r39-4T.2a: %d конкурентных start_tray -> ОДИН pystray.Icon" % N,
              st["icons"] == 1, str(st["icons"]))
        check("r39-4T.2b: все потоки получили один и тот же icon",
              len(got) == N and all(g is got[0] and g is not None for g in got),
              str(len({id(g) for g in got})))
        check("r39-4T.2c: run_detached вызван один раз",
              st["detached"] == 1, str(st["detached"]))


# ── 3. «Выход»: ровно один stop, без двойного icon.stop() ────────────────
def test_quit_single_stop():
    print("\n=== 4T.3 «Выход»: ровно один icon.stop() ===")
    st = {"icons": 0, "stopped": 0, "detached": 0, "opened": 0, "notify": 0}
    real_exit = os._exit
    with _win_tray(st) as ti:
        icon = ti.start_tray(None, web_url="http://127.0.0.1:8555")
        _settle()
        items = list(getattr(icon.menu, "items", ()))
        quit_item = None
        for it in items:
            if getattr(it, "text", None) == "Выход":
                quit_item = it
        check("r39-4T.3a: пункт «Выход» в меню найден", quit_item is not None)
        if quit_item is not None:
            os._exit = lambda code=0: None      # не убивать тестовый процесс
            try:
                quit_item.action(icon, quit_item)
            finally:
                os._exit = real_exit
            _settle()
            check("r39-4T.3b: «Выход» останавливает значок РОВНО ОДИН раз "
                  "(нет двойного icon.stop())",
                  st["stopped"] == 1, str(st["stopped"]))
            check("r39-4T.3c: после «Выхода» реестр значка пуст",
                  ti.get_active_icon() is None)
            # повторный stop_tray не должен вызвать stop ещё раз
            ti.stop_tray()
            check("r39-4T.3d: повторный stop_tray идемпотентен",
                  st["stopped"] == 1, str(st["stopped"]))
            n2 = ti.start_tray(None, web_url="http://127.0.0.1:8555")
            _settle()
            check("r39-4T.3e: после «Выхода» значок можно запустить снова",
                  n2 is not None and st["icons"] == 2, str(st["icons"]))


# ── 4. stop_tray освобождает single-instance guard ───────────────────────
def test_stop_releases_guard():
    print("\n=== 4T.4 «Выход» освобождает single-instance guard ===")
    src = read_src("ui", "tray_icon.py")
    check("r39-4T.4a: _quit() зовёт stop_tray с release_guard=True",
          "stop_tray(icon=icon, release_guard=True)" in src)
    check("r39-4T.4b: _quit() НЕ зовёт icon.stop() напрямую "
          "(иначе двойной stop)",
          "icon.stop()" not in src.split("def stop_tray")[0]
          .split("def _quit")[-1])
    check("r39-4T.4c: stop_tray умеет освобождать guard",
          "from core.single_instance import release" in src)

    st = {"icons": 0, "stopped": 0, "detached": 0, "opened": 0, "notify": 0}
    with _win_tray(st) as ti:
        released = {"n": 0}
        import core.single_instance as si
        real = si.release

        def _rel():
            released["n"] += 1
            return real()
        si.release = _rel
        try:
            ti.start_tray(None, web_url="http://127.0.0.1:8555")
            _settle()
            ti.stop_tray(release_guard=True)
            _settle()
            check("r39-4T.4d: stop_tray(release_guard=True) реально освободил guard",
                  released["n"] == 1, str(released["n"]))
        finally:
            si.release = real


# ── 5. Не-Windows: трея нет, но и падения нет ────────────────────────────
def test_non_windows():
    print("\n=== 4T.5 Не-Windows: мягкий отказ ===")
    import importlib
    plat = sys.platform
    try:
        sys.platform = "linux"
        import ui.tray_icon as ti
        ti = importlib.reload(ti)
        check("r39-4T.5a: на не-Windows start_tray -> None (без исключения)",
              ti.start_tray(None) is None)
        check("r39-4T.5b: get_active_icon() -> None",
              ti.get_active_icon() is None)
        check("r39-4T.5c: stop_tray() без значка безопасен",
              ti.stop_tray() is None)
        check("r39-4T.5d: notify() без значка -> мягкий False",
              ti.notify("тест") is False)
    finally:
        sys.platform = plat
        import ui.tray_icon as ti
        importlib.reload(ti)


def main():
    install_thread_guard()
    for fn in (test_repeat_start, test_concurrent_start,
               test_quit_single_stop, test_stop_releases_guard,
               test_non_windows):
        print("\n" + "=" * 70)
        try:
            fn()
        except Exception:
            import traceback
            check(fn.__name__ + " [exception]", False)
            traceback.print_exc()
    _settle()
    check_no_thread_errors("tray/pystray")
    sys.exit(report("Round 39 / tray"))


if __name__ == "__main__":
    main()

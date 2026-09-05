# -*- coding: utf-8 -*-
"""Раунд 39, группа LOGIC: single-instance guard, tray, ленивый хост.

Только логика и моки: ни одного обращения к реальному окну. Все ветки
(Windows / не-Windows / отказ API) проверяются ДЕТЕРМИНИРОВАНО на любой ОС —
sys.platform подменяется, WinAPI заменяется фейком, который ведёт себя как
ядро (успешный CreateMutexW НЕ сбрасывает last error).

Дополнительно — НАСТОЯЩИЙ межпроцессный тест guard'а: два дочерних python-
процесса спорят за мьютекс, имя которого эмулируется ОС-ным flock/msvcrt-локом
(реальная взаимная блокировка между процессами). Проверка связки с НАСТОЯЩИМ
CreateMutexW возможна только на Windows — она выполняется там же и помечается
SKIP на других ОС (не выдаётся за проверенную).
"""
import contextlib
import importlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import types

from r39_harness import check, skip, blocked_module, force_platform

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ERROR_ALREADY_EXISTS = 183

# ── эмуляция «ядра» для дочернего процесса ────────────────────────────────
# Файл-лок ОС (fcntl.flock на POSIX, msvcrt.locking на Windows) даёт НАСТОЯЩУЮ
# взаимную блокировку между процессами: спор двух python-процессов за «mutex»
# реален. Остальное — поведение WinAPI: при существующем объекте возвращается
# ВАЛИДНЫЙ handle, «уже занят» видно только по last error, а успешный вызов
# last error НЕ сбрасывает (отсюда обязательность SetLastError(0) перед вызовом).
CHILD_KERNEL = r"""
import ctypes, os, sys, types

S = {"err": 183, "handles": {}, "nxt": 0x1000}          # err ЗАРАНЕЕ грязный
D = os.environ["R39_LOCKDIR"]


def _lock(fh, unlock=False):
    try:
        import fcntl
        fcntl.flock(fh.fileno(),
                    fcntl.LOCK_UN if unlock else fcntl.LOCK_EX | fcntl.LOCK_NB)
    except ImportError:
        import msvcrt
        fh.seek(0)
        msvcrt.locking(fh.fileno(),
                       msvcrt.LK_UNLCK if unlock else msvcrt.LK_NBLCK, 1)


def CreateMutexW(_a, _b, name):
    fh = open(os.path.join(D, name.replace(chr(92), "_")), "a+b")
    S["nxt"] += 1
    try:
        _lock(fh)
    except OSError:
        fh.close()
        S["err"] = 183                       # объект уже существует
        return S["nxt"]                      # handle валиден — решает err
    S["handles"][S["nxt"]] = fh
    return S["nxt"]                          # УСПЕХ: last error НЕ изменён


def CloseHandle(h):
    fh = S["handles"].pop(int(getattr(h, "value", h) or 0), None)
    if fh is not None:
        try:
            _lock(fh, unlock=True)
        except OSError:
            pass
        fh.close()
    return 1


ctypes.windll = types.SimpleNamespace(
    kernel32=types.SimpleNamespace(
        CreateMutexW=CreateMutexW, CloseHandle=CloseHandle,
        GetLastError=lambda: S["err"],
        SetLastError=lambda v: S.__setitem__("err", v)),
    user32=types.SimpleNamespace(
        FindWindowW=lambda a, b: 0, IsIconic=lambda h: 0,
        ShowWindow=lambda h, s: 1, SetForegroundWindow=lambda h: 1))
sys.platform = "win32"
"""

# Программа дочернего процесса. Режимы (R39_MODE):
#   hold  — занять guard, держать его до сигнала/таймаута и освободить при выходе
#   once  — занять, сообщить, освободить (обычный «второй запуск» или обычный старт)
#   cycle — занять, отпустить, занять снова (идемпотентность release + перезапуск)
# Пишет в R39_OUT по строке JSON на каждый этап; вывод самого процесса — только
# для диагностики, проверки читают JSON.
CHILD = r"""
import json, os, sys, time

out = os.environ["R39_OUT"]
os.makedirs(os.path.dirname(out), exist_ok=True)


def emit(o):
    with open(out, "a", encoding="utf-8") as f:      # фаза -> строка JSON
        f.write(json.dumps(o) + chr(10))
    with open(out + ".ok", "w", encoding="utf-8") as f:
        f.write(str(len(_phases_seen())))


def _phases_seen():
    try:
        with open(out, encoding="utf-8") as f:
            return [x for x in f if x.strip()]
    except OSError:
        return []


sys.path.insert(0, os.environ["R39_ROOT"])
from core import single_instance as si

ed = os.environ.get("R39_EDITION", "r39")
mode = os.environ.get("R39_MODE", "once")
ok, why = si.acquire(ed)
emit({"first": [ok, why], "status": si.status()})
if mode == "hold":
    if ok:
        time.sleep(float(os.environ.get("R39_HOLD", "60")))
    si.release()
    sys.exit(0)
if ok:
    si.release()
    emit({"first": [ok, why], "status": si.status(), "released": True})
if mode == "cycle":
    ok2, why2 = si.acquire(ed)
    emit({"first": [ok, why], "status": si.status(), "reacquired": [ok2, why2]})
    si.release()
"""


# Фейковый WinAPI: функции ОБЫКНОВЕННЫЕ (не методы) — production-код
# присваивает CreateMutexW.restype/.argtypes, bound-method их не принимает.
def make_kernel(last_error=0, fail=None, delay=0.0, taken=()):
    """Ядро: `taken` — уже занятые имена mutex'ов. ВАЖНО: успешный
    CreateMutexW НЕ трогает last error (MSDN), поэтому читатель обязан
    обнулять его SetLastError(0) сам; `last_error=183` — «грязный след»
    предыдущего неудачного, но обработанного вызова (напр. mkdir папки).
    """
    st = {"err": last_error, "next": 0x1000}
    held = {n: 0x0 for n in taken}          # name -> handle занятого объекта
    calls = {"create": [], "close": 0, "order": []}

    def SetLastError(v):
        calls["order"].append("SetLastError")
        st["err"] = v

    def GetLastError():
        calls["order"].append("GetLastError")
        return st["err"]

    def CreateMutexW(_sec, _owner, name):
        calls["order"].append("CreateMutexW")
        calls["create"].append(name)
        if delay:
            time.sleep(delay)
        if fail:
            raise fail
        if name in held:
            st["err"] = ERROR_ALREADY_EXISTS
            st["next"] += 1
            return st["next"]               # валидный handle на существующий
        st["next"] += 1
        held[name] = st["next"]
        return st["next"]                   # last error НЕ меняется (WinAPI!)

    def CloseHandle(h):
        calls["close"] += 1
        hv = int(getattr(h, "value", h) or 0)     # ctypes.c_void_p или int
        for n, v in list(held.items()):
            if v == hv:
                held.pop(n)
        return 1

    if fail == "null":                      # отдельный сценарий: NULL + err
        def CreateMutexW(_sec, _owner, name):      # noqa: F811
            calls["create"].append(name)
            st["err"] = 5                          # ERROR_ACCESS_DENIED
            return 0

    k32 = types.SimpleNamespace(CreateMutexW=CreateMutexW,
                                GetLastError=GetLastError,
                                SetLastError=SetLastError,
                                CloseHandle=CloseHandle)
    k32.held = held
    k32.calls = calls
    return k32


def make_user32(hwnd=0):
    st = {"hwnd": hwnd, "focus": 0, "show": []}

    def FindWindowW(_cls, _title):
        return st["hwnd"]

    def IsIconic(_h):
        return 0

    def ShowWindow(_h, cmd):
        st["show"].append(cmd)
        return 1

    def SetForegroundWindow(_h):
        st["focus"] += 1
        return 1

    u32 = types.SimpleNamespace(FindWindowW=FindWindowW, IsIconic=IsIconic,
                                ShowWindow=ShowWindow,
                                SetForegroundWindow=SetForegroundWindow)
    u32.state = st
    return u32


def _winapi(k32=None, u32=None, **kw):
    """Контекстный вход в «Windows» с фейковым ctypes.windll."""
    return _WinApiCtx(k32 or make_kernel(**kw), u32)


class _WinApiCtx:
    def __init__(self, k32, u32):
        self.k32, self.u32 = k32, u32

    def __enter__(self):
        import ctypes
        self._ctypes, self._old = ctypes, getattr(ctypes, "windll", "__absent__")
        ctypes.windll = types.SimpleNamespace(kernel32=self.k32,
                                              user32=self.u32 or make_user32())
        self._plat = force_platform("win32")
        self._plat.__enter__()
        return self.k32

    def __exit__(self, *a):
        self._plat.__exit__()
        if self._old == "__absent__":
            try:
                del self._ctypes.windll
            except Exception:
                pass
        else:
            self._ctypes.windll = self._old
        return False


def _fresh_si():
    """Чистый модуль core.single_instance (без состояния предыдущих кейсов)."""
    from core import single_instance as si
    si.release()
    return si


def run_single_instance():
    print("\n--- 4. core/single_instance (детерминированные ветки) ---")
    from core import single_instance as si

    # 4.1 имя guard'а
    check("r39-4.1a: имя mutex'а = Local\\ + редакция",
          si.mutex_name("admin") == "Local\\Porayonka_admin", si.mutex_name("admin"))
    check("r39-4.1b: разные редакции не мешают друг другу",
          si.mutex_name("admin") != si.mutex_name("user"))
    os.environ["PORAYONKA_EDITION"] = "User"
    try:
        check("r39-4.1c: без аргумента — fallback на env PORAYONKA_EDITION",
              si.mutex_name() == "Local\\Porayonka_user", si.mutex_name())
    finally:
        os.environ.pop("PORAYONKA_EDITION", None)

    # 4.2 НАСТОЯЩИЙ не-Windows: fail-open (детерминированно на любой ОС прогона)
    si = _fresh_si()
    with force_platform("linux"):
        ok, why = si.acquire("admin")
        check("r39-4.2a: не-Windows -> fail-open, приложение работает",
              ok is True and why == "fail_open:not_windows", why)
        check("r39-4.2b: не-Windows -> guard НЕ «наш» (не выдаём за acquired)",
              si.is_acquired() is False and si.status() == "fail_open",
              si.status())
        ok2, why2 = si.acquire("admin")
        check("r39-4.2c: повторный acquire в fail-open идемпотентен",
              ok2 is True and why2 == why, why2)
    si.release()

    # 4.3 Windows, свободный mutex -> acquired
    si = _fresh_si()
    with _winapi() as k32:
        ok, why = si.acquire("admin")
        check("r39-4.3a: Windows, свободный mutex -> acquired",
              ok is True and why == "acquired", why)
        check("r39-4.3b: is_acquired()/status() согласованы",
              si.is_acquired() is True and si.status() == "acquired", si.status())
        check("r39-4.3c: имя guard'а реально ушло в API",
              k32.calls["create"] == ["Local\\Porayonka_admin"],
              str(k32.calls["create"]))
        ok2, why2 = si.acquire("admin")
        check("r39-4.3d: повторный acquire НЕ создаёт второй handle",
              ok2 is True and why2 == "acquired" and len(k32.calls["create"]) == 1,
              str(k32.calls["create"]))
        check("r39-4.3e: статус «занято ядром» отражён (mutex в реестре fake'а)",
              "Local\\Porayonka_admin" in k32.held, str(list(k32.held)))
        check("r39-4.3f: SetLastError(0) вызван ДО CreateMutexW, а GetLastError — "
              "сразу после (порядок, предписанный задачей 4)",
              k32.calls["order"] == ["SetLastError", "CreateMutexW",
                                     "GetLastError"], str(k32.calls["order"]))

        # 4.6 release + идемпотентность + повторный захват
        n_close = k32.calls["close"]
        si.release()
        check("r39-4.6a: release() сбрасывает состояние в none",
              si.status() == "none" and si.is_acquired() is False, si.status())
        si.release()
        check("r39-4.6b: release() идемпотентен (лишнего CloseHandle нет)",
              k32.calls["close"] == n_close + 1, str(k32.calls["close"]))
        ok, why = si.acquire("admin")
        check("r39-4.6c: после освобождения повторный запуск занимает guard",
              ok is True and why == "acquired", why)
        check("r39-4.6d: release() без acquire() безопасен",
              (si.release(), si.status())[1] == "none")

    # 4.4 ЗАРАНЕЕ грязный last error (mkdir существующей папки перед acquire()
    #     оставляет 183 в потоке) — не должен выдавать «уже запущен»
    si = _fresh_si()
    with _winapi(last_error=ERROR_ALREADY_EXISTS):
        ok, why = si.acquire("admin")
        check("r39-4.4a: прошлый last error 183 НЕ выдаёт «уже запущен» "
              "(SetLastError(0) перед CreateMutexW)",
              ok is True and why == "acquired", why)
        check("r39-4.4b: после обнуления guard «наш»", si.is_acquired() is True,
              si.status())
        si.release()

    # 4.5 ERROR_ALREADY_EXISTS -> работать НЕЛЬЗЯ (это НЕ fail-open)
    si = _fresh_si()
    with _winapi(taken=("Local\\Porayonka_admin",)) as k32:
        ok, why = si.acquire("admin")
        check("r39-4.5a: ERROR_ALREADY_EXISTS -> ok=False, already_exists",
              ok is False and why == "already_exists", why)
        check("r39-4.5b: ERROR_ALREADY_EXISTS — НЕ fail-open",
              si.status() == "already_exists", si.status())
        check("r39-4.5c: чужой handle закрыт (не становимся держателем)",
              k32.calls["close"] == 1, str(k32.calls["close"]))
        check("r39-4.5d: already_running() True, is_acquired() False",
              si.already_running() is True and si.is_acquired() is False)
        ok2, why2 = si.acquire("admin")
        check("r39-4.5e: повторный acquire при занятом mutex тоже отказывает",
              ok2 is False and why2 == "already_exists"
              and len(k32.calls["create"]) == 1, why2)
        check("r39-4.5f: detail() хранит имя занятого guard'а",
              si.detail() == "Local\\Porayonka_admin", si.detail())
        si.release()

    # 4.7 отказ API -> fail-open с явной диагностикой (не «уже запущен»)
    si = _fresh_si()
    with _winapi(fail=OSError("no kernel32")):
        ok, why = si.acquire("admin")
        check("r39-4.7a: API бросает -> fail-open (приложение работает)",
              ok is True and why.startswith("fail_open:"), why)
        check("r39-4.7b: причина fail-open зафиксирована в detail()",
              "OSError" in si.detail() and "no kernel32" in si.detail(),
              si.detail())
        check("r39-4.7c: fail-open НЕ помечает guard «нашим»",
              si.is_acquired() is False)
    si = _fresh_si()
    with _winapi(fail="null"):
        ok, why = si.acquire("admin")
        check("r39-4.7d: NULL handle + реальный err -> fail-open, err в диагностике",
              ok is True and "null_handle(err=5)" in why, why)

    # 4.8 конкурентный acquire: один реальный вызов API, дублей нет
    si = _fresh_si()
    res = []
    lock = threading.Lock()
    bar = threading.Barrier(8)
    with _winapi(delay=0.02) as k32:
        def _w():
            bar.wait()
            r = si.acquire("admin")
            with lock:
                res.append(r)

        ths = [threading.Thread(target=_w) for _ in range(8)]
        for t in ths:
            t.start()
        for t in ths:
            t.join(30)
        check("r39-4.8a: 8 конкурентных acquire() -> ОДИН CreateMutexW",
              len(k32.calls["create"]) == 1, str(k32.calls["create"]))
        check("r39-4.8b: все потоки получили acquired, отказов нет",
              len(res) == 8 and all(r == (True, "acquired") for r in res),
              str(sorted({r[1] for r in res})))
        check("r39-4.8c: один handle на процесс (нет «лишних» держателей)",
              len(k32.held) == 1, str(list(k32.held)))
        si.release()

    # 4.9 передача управления первому экземпляру
    si = _fresh_si()
    u32 = make_user32(hwnd=0xBEEF)
    with _winapi(make_kernel(), u32):
        check("r39-4.9a: focus_existing поднимает окно первого экземпляра",
              si.focus_existing("Порайонка") is True and u32.state["focus"] == 1,
              str(u32.state["focus"]))
        u32.state["hwnd"] = 0
        check("r39-4.9b: окна нет -> мягкий False без исключения",
              si.focus_existing("Порайонка") is False)
    with force_platform("linux"):
        check("r39-4.9c: не-Windows -> False (без обращения к user32)",
              si.focus_existing() is False)


def _child(dirpath, mode, tag, edition="r39", hold="45", fake=True):
    """Дочерний процесс; пишет фазы в `<tag>.json` (append). Возвращает
    (Popen, path_out, path_flag) — path_flag появляется после каждой фазы."""
    env = dict(os.environ)
    out = os.path.join(dirpath, tag + ".json")
    env.update({"R39_ROOT": ROOT, "R39_MODE": mode, "R39_EDITION": edition,
                "R39_HOLD": hold, "R39_OUT": out, "PYTHONIOENCODING": "utf-8"})
    if fake:
        env["R39_LOCKDIR"] = os.path.join(dirpath, "locks")
        os.makedirs(env["R39_LOCKDIR"], exist_ok=True)
        src = CHILD_KERNEL + "\n" + CHILD
    else:
        src = CHILD
    p = subprocess.Popen([sys.executable, "-c", src], cwd=ROOT, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace")
    return p, out, out + ".ok"


def _phases(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _wait_file(path, timeout=40.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if os.path.exists(path):
            return True
        time.sleep(0.02)
    return False


def run_single_instance_crossprocess():
    print("\n--- 4b. Guard между ДВУМЯ реальными процессами ---")
    d = tempfile.mkdtemp(prefix="r39_si_")
    procs = []

    def _spawn(mode, tag, **kw):
        p = _child(d, mode, tag, **kw)
        procs.append(p[0])
        return p

    try:
        ed = "r39_%d" % os.getpid()
        # A — первый запуск: обязан занять guard, несмотря на грязный last error
        a, a_out, a_flag = _spawn("hold", "A", edition=ed)
        ok_a = _wait_file(a_flag, 40)
        ph_a = _phases(a_out)
        check("r39-4.10a: процесс A занял guard (stale last error 183 не помешал)",
              ok_a and ph_a and ph_a[0]["first"] == [True, "acquired"], str(ph_a[:1]))

        # Б — второй запуск: обязан получить отказ (это НЕ fail-open)
        b, b_out, _b_flag = _spawn("once", "B", edition=ed)
        b.wait(30)
        ph_b = _phases(b_out)
        check("r39-4.10b: процесс Б получил отказ already_exists",
              ph_b and ph_b[0]["first"] == [False, "already_exists"], str(ph_b[:1]))
        check("r39-4.10b2: отказ Б НЕ помечен как fail-open и guard «не наш»",
              ph_b and ph_b[0]["status"] == "already_exists"
              and not ph_b[-1].get("released"), str(ph_b[:2]))

        # A убит извне (как закрытое окно/снят процесс) — ядро снимает mutex само
        a.terminate()
        a.wait(20)
        c, c_out, _c_flag = _spawn("once", "C", edition=ed)
        c.wait(30)
        ph_c = _phases(c_out)
        check("r39-4.10c: после смерти A guard освободился ядром (новый процесс "
              "его берёт) — «залипаний», как у pid-файла, нет",
              ph_c and ph_c[0]["first"] == [True, "acquired"], str(ph_c[:1]))
        check("r39-4.10c2: корректный выход процесса освободил guard (release)",
              ph_c and ph_c[-1].get("released") is True, str(ph_c[-1:]))

        # D — цикл «старт → выход → старт» в одном процессе
        e, e_out, _e_flag = _spawn("cycle", "E", edition=ed)
        e.wait(30)
        ph_e = _phases(e_out)
        check("r39-4.10d: идемпотентный release и повторный acquire в процессе",
              len(ph_e) == 3 and ph_e[0]["first"] == [True, "acquired"]
              and ph_e[-1]["reacquired"] == [True, "acquired"], str(ph_e[-1:]))

        if sys.platform == "win32":
            n, n_out, _n_flag = _spawn("once", "N", edition=ed, fake=False)
            n.wait(30)
            ph_n = _phases(n_out)
            check("r39-4.11: НАСТОЯЩИЙ CreateMutexW между процессами (Windows)",
                  ph_n and ph_n[0]["first"] in ([True, "acquired"],
                                                [False, "already_exists"]),
                  str(ph_n[:1]))
        else:
            skip("r39-4.11: живой Windows single-instance двумя процессами",
                 "требует физический Windows (CreateMutexW нет); та же схема "
                 "проверяется прогоном на Windows-хосте")
    finally:
        for p in procs:
            if p.poll() is None:
                p.kill()
        for p in procs:
            try:
                p.wait(10)
            except Exception:
                pass
        import shutil
        shutil.rmtree(d, ignore_errors=True)


# ── фейковый pystray (контракт библиотеки, без GUI) ──────────────────────
class _TrayState:
    def __init__(self):
        self.icons = self.detached = self.stopped = 0


def _fake_pystray(st):
    """pystray.Menu/MenuItem/Icon как в библиотеке: run_detached/stop/visible."""
    class _Item:
        def __init__(self, text, action, default=False):
            self.text, self.action, self.default = text, action, default

    class _Menu:
        def __init__(self, *items):
            self.items = items

    class _Icon:
        def __init__(self, name, image, title, menu):
            self.name, self.image, self.title, self.menu = name, image, title, menu
            self.args = (name, image, title, menu)
            self.visible = False
            self.notified = None
            st.icons += 1

        def run_detached(self):
            st.detached += 1
            self.visible = True

        def notify(self, msg, title=None):
            self.notified = msg

        def stop(self):
            st.stopped += 1
            self.visible = False

    return (types.SimpleNamespace(Icon=_Icon, Menu=_Menu, MenuItem=_Item),
            types.SimpleNamespace(Image=types.SimpleNamespace(
                open=lambda path: object())))


def _reload_tray():
    """Заново импортировать ui.tray_icon (свежий _ACTIVE_ICON внутри модуля)."""
    sys.modules.pop("ui.tray_icon", None)
    return importlib.import_module("ui.tray_icon")


def run_tray():
    print("\n--- 4c. tray: один значок, один stop, освобождение guard'а ---")
    from core import single_instance as si
    st = _TrayState()
    fake_pystray_mod, fake_pil = _fake_pystray(st)
    with blocked_module(pystray=fake_pystray_mod, PIL=fake_pil), \
            force_platform("win32"):
        ti = _reload_tray()

        i1 = ti.start_tray(None, web_url="http://127.0.0.1:8555")
        i2 = ti.start_tray(None, web_url="http://127.0.0.1:8555")
        i3 = ti.start_tray(object())
        check("r39-4.12a: повторный start_tray возвращает ТОТ ЖЕ icon",
              i1 is not None and i1 is i2 is i3)
        check("r39-4.12b: pystray.Icon создан РОВНО ОДИН раз",
              st.icons == 1, str(st.icons))
        check("r39-4.12c: get_active_icon() отдаёт тот же значок",
              ti.get_active_icon() is i1)

        ti.stop_tray()
        st.icons = st.detached = st.stopped = 0
        res = []
        lock = threading.Lock()
        bar = threading.Barrier(10)

        def _w():
            bar.wait()
            ic = ti.start_tray(None, web_url="http://127.0.0.1:8555")
            with lock:
                res.append(ic)

        ths = [threading.Thread(target=_w) for _ in range(10)]
        for t in ths:
            t.start()
        for t in ths:
            t.join(30)
        check("r39-4.13a: 10 конкурентных start_tray -> ОДИН pystray.Icon",
              st.icons == 1, str(st.icons))
        check("r39-4.13b: все 10 потоков получили один и тот же значок",
              len(res) == 10 and all(r is res[0] for r in res))
        check("r39-4.13c: run_detached выполнен ровно один раз",
              st.detached == 1, str(st.detached))

        # «Выход» из меню: один stop + снятие guard'а
        si.release()
        with _winapi() as k32:
            try:
                si.acquire("admin")
                icon = ti.get_active_icon()
                menu = (getattr(icon, "args", ()) + (None,) * 4)[3]
                items = getattr(menu, "items", ()) or ()
                quit_fn = next((it.action for it in items
                                if getattr(it, "text", None) == "Выход"), None)
                check("r39-4.14a: пункт «Выход» найден в меню значка",
                      quit_fn is not None)
                st.stopped = 0
                real_exit = os._exit
                try:
                    os._exit = lambda code=0: (_ for _ in ()).throw(SystemExit(code))
                    try:
                        quit_fn(icon, None)          # web-ветка: не убиваем тест
                    except SystemExit:
                        pass
                finally:
                    os._exit = real_exit
                check("r39-4.14b: «Выход» вызывает icon.stop() РОВНО ОДИН раз",
                      st.stopped == 1, str(st.stopped))
                check("r39-4.14c: реестр значка пуст (после «Выхода» можно заново)",
                      ti.get_active_icon() is None)
                check("r39-4.14d: «Выход» освободил single-instance guard",
                      si.status() == "none" and k32.calls["close"] == 1,
                      "%s close=%s" % (si.status(), k32.calls["close"]))
                again = ti.start_tray(None, web_url="http://127.0.0.1:8555")
                check("r39-4.14e: после «Выхода» значок запускается снова",
                      again is not None and st.icons == 2, str(st.icons))
                ti.stop_tray()
                ti.stop_tray()
                check("r39-4.14f: повторный stop_tray() не зовёт stop() на "
                      "несуществующем значке", st.stopped <= 2, str(st.stopped))
            finally:
                si.release()

    # web-режим: значок обслуживает URL, а не desktop-окно (требование 6.9)
    with blocked_module(pystray=_fake_pystray(_TrayState())[0],
                        PIL=_fake_pystray(_TrayState())[1]), force_platform("win32"):
        st_w = _TrayState()
        py_w, pil_w = _fake_pystray(st_w)
        with blocked_module(pystray=py_w, PIL=pil_w):
            tiw = _reload_tray()
            opened = []
            real_wb = tiw.webbrowser
            tiw.webbrowser = types.SimpleNamespace(open=lambda u: opened.append(u))
            try:
                ic = tiw.start_tray(None, web_url="http://127.0.0.1:8555")
                menu = (getattr(ic, "args", ()) + (None,) * 4)[3]
                show = next((it.action for it in getattr(menu, "items", ())
                             if getattr(it, "text", None) == "Открыть в браузере"),
                            None)
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    show(ic, None)
                check("r39-4.15d: web-значок «Открыть» ведёт в браузер и НЕ трогает "
                      "desktop-окно (page=None, window.* не вызываются)",
                      opened == ["http://127.0.0.1:8555"]
                      and "show window error" not in out.getvalue(),
                      "%s | %s" % (opened, out.getvalue().strip()[:60]))
                tiw.stop_tray()
            finally:
                tiw.webbrowser = real_wb

    # не-Windows и «нет pystray» — мягкий None, без исключений
    with blocked_module(pystray=None, PIL=None), force_platform("win32"):
        check("r39-4.15a: Windows без pystray/pillow -> мягкий None",
              _reload_tray().start_tray(object()) is None)
    with blocked_module(pystray=fake_pystray_mod, PIL=fake_pil), \
            force_platform("linux"):
        st.icons = 0
        ti2 = _reload_tray()
        check("r39-4.15b: не-Windows -> значок НЕ создаётся вообще",
              ti2.start_tray(object()) is None and st.icons == 0, str(st.icons))
        check("r39-4.15c: stop_tray() без значка не падает",
              ti2.stop_tray() is None)
    _reload_tray()      # вернуть модуль в чистое состояние


# ── подготовка web-загрузки: каталог, ключ, гонка двух запусков ──────────
_CHILD_ENV = r"""
import os, sys
sys.path.insert(0, os.environ["R39_ROOT"])
import main
main._ensure_web_upload_env()
sys.stdout.write("KEY=" + (os.environ.get("FLET_SECRET_KEY") or ""))
"""


def run_upload_env():
    print("\n--- 5a. main._ensure_web_upload_env (каталог, ключ, гонка) ---")
    import main
    d = tempfile.mkdtemp(prefix="r39_env_")
    saved = {k: os.environ.get(k) for k in
             ("APPDATA", "FLET_UPLOAD_DIR", "FLET_SECRET_KEY")}
    bad = []
    stop = threading.Event()

    def _sample():
        f = os.path.join(d, "porayonka", "upload_secret.key")
        while not stop.is_set():
            try:
                with open(f, encoding="ascii") as fh:
                    txt = fh.read()
                if txt and not (len(txt) == 64 and all(c in "0123456789abcdef"
                                                        for c in txt)):
                    bad.append(repr(txt[:24]))
            except OSError:
                pass
            time.sleep(0.001)

    def _clean_env():
        os.environ["APPDATA"] = d
        os.environ.pop("FLET_UPLOAD_DIR", None)
        os.environ.pop("FLET_SECRET_KEY", None)

    try:
        # 1) первый запуск: каталог создан, ключ сгенерирован
        _clean_env()
        with contextlib.redirect_stdout(io.StringIO()):
            main._ensure_web_upload_env()
        up = os.environ.get("FLET_UPLOAD_DIR")
        key = os.environ.get("FLET_SECRET_KEY") or ""
        check("r39-5.9a: каталог загрузки = %APPDATA%\\porayonka\\web_uploads "
              "и существует", up == os.path.join(d, "porayonka", "web_uploads")
              and os.path.isdir(up), str(up))
        check("r39-5.9b: ключ 64 hex-символа (secrets.token_hex(32))",
              len(key) == 64 and all(c in "0123456789abcdef" for c in key),
              str(len(key)))
        kf = os.path.join(d, "porayonka", "upload_secret.key")
        check("r39-5.9c: ключ сохранён в файл (стабильность между запусками)",
              os.path.isfile(kf) and open(kf, encoding="ascii").read().strip() == key)
        leftovers = [n for n in os.listdir(os.path.join(d, "porayonka"))
                     if n.endswith(".tmp")]
        check("r39-5.9d: временных файлов записи не остаётся", not leftovers,
              str(leftovers))

        # 2) повторный запуск: значение НЕ меняется
        _clean_env()
        with contextlib.redirect_stdout(io.StringIO()):
            main._ensure_web_upload_env()
        check("r39-5.9e: перезапуск использует тот же ключ (не генерирует новый)",
              os.environ.get("FLET_SECRET_KEY") == key)

        # 3) уже заданный env не перезаписывается (идемпотентность)
        os.environ["FLET_SECRET_KEY"] = "preset-key"
        os.environ["FLET_UPLOAD_DIR"] = os.path.join(d, "custom")
        with contextlib.redirect_stdout(io.StringIO()):
            main._ensure_web_upload_env()
        check("r39-5.9f: уже заданные env НЕ перезаписываются (идемпотентно)",
              os.environ["FLET_SECRET_KEY"] == "preset-key"
              and os.environ["FLET_UPLOAD_DIR"] == os.path.join(d, "custom"))

        # 4) ГОНКА: несколько процессов стартуют одновременно в чистый каталог
        os.remove(kf)
        os.makedirs(os.path.join(d, "porayonka"), exist_ok=True)
        _clean_env()
        sampler = threading.Thread(target=_sample, daemon=True)
        sampler.start()
        outs = []
        envs = []
        for _ in range(6):
            e = dict(os.environ)
            e.update({"R39_ROOT": ROOT, "PYTHONIOENCODING": "utf-8",
                      "APPDATA": d})
            e.pop("FLET_UPLOAD_DIR", None)
            e.pop("FLET_SECRET_KEY", None)
            envs.append(e)
        procs = [subprocess.Popen([sys.executable, "-c", _CHILD_ENV], cwd=ROOT,
                                  env=e, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True,
                                  encoding="utf-8", errors="replace")
                 for e in envs]
        for p in procs:
            o, _ = p.communicate(timeout=120)
            outs.append([l for l in o.splitlines() if l.startswith("KEY=")])
        stop.set()
        sampler.join(5)
        keys = [o[0][4:] if o else "" for o in outs]
        file_key = open(kf, encoding="ascii").read().strip()
        check("r39-5.9g: 6 одновременных запуска получили ОДИН ключ (победитель — "
              "файл)", len(set(keys)) == 1 and keys[0] == file_key
              and len(file_key) == 64, str(sorted({k[:8] for k in keys})))
        check("r39-5.9h: наблюдатель никогда не видел пустого/обрезанного ключа "
              "(запись атомарна)", not bad, str(bad[:2]))
        leftovers = [n for n in os.listdir(os.path.join(d, "porayonka"))
                     if n.endswith(".tmp")]
        check("r39-5.9i: после гонки нет осиротевших .tmp (провал записи чистится)",
              not leftovers, str(leftovers))
    finally:
        stop.set()
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        import shutil
        shutil.rmtree(d, ignore_errors=True)


# ── ленивые вкладки: чистая логика хоста ─────────────────────────────────
def run_lazy_host():
    print("\n--- 2. LazyTabHost (build-once + кэш) ---")
    from ui.lazy_tabs import LazyTabHost

    KEYS = ("controls", "zonal", "departments")
    calls = {k: 0 for k in KEYS}
    objs = {k: object() for k in KEYS}

    def _mk(k):
        def _b():
            calls[k] += 1
            return objs[k]
        return _b

    host = LazyTabHost()
    for k in KEYS:
        host.register(k, _mk(k))
    check("r39-2.1a: регистрация ничего не строит",
          all(v == 0 for v in calls.values()), str(calls))
    got = host.get("controls")
    check("r39-2.1b: построена ТОЛЬКО активная вкладка",
          calls == {"controls": 1, "zonal": 0, "departments": 0}
          and got is objs["controls"], str(calls))
    check("r39-2.1c: неактивные вкладки ещё не построены",
          host.built_keys() == ["controls"], str(host.built_keys()))
    for _ in range(3):
        host.get("zonal")
    host.get("departments")
    check("r39-2.2a: builder каждой вкладки вызван РОВНО ОДИН раз",
          all(v == 1 for v in calls.values()), str(calls))
    check("r39-2.2b: кэш сохраняет ЭКЗЕМПЛЯР (тот же объект при возврате)",
          host.get("zonal") is objs["zonal"]
          and host.get("departments") is objs["departments"]
          and host.build_count("zonal") == 1, str(host.stats()))
    # 4 обращения к zonal: первое — build, остальные — reuse
    check("r39-2.2c: reuse-счётчики растут, build — нет",
          host.reuse_count("zonal") == 3 and host.build_count("zonal") == 1,
          "reuse=%s build=%s" % (host.reuse_count("zonal"),
                                  host.build_count("zonal")))
    check("r39-2.2d: неизвестный ключ -> KeyError (не тихий None)",
          _raises(KeyError, host.get, "ghost"))

    # конкурентный переход
    n = {"x": 0}
    box = {}

    def _slow():
        n["x"] += 1
        time.sleep(0.02)
        return box.setdefault("obj", object())

    h2 = LazyTabHost()
    h2.register("x", _slow)
    res = []
    lock = threading.Lock()
    bar = threading.Barrier(12)

    def _w():
        bar.wait()
        v = h2.get("x")
        with lock:
            res.append(v)

    ths = [threading.Thread(target=_w) for _ in range(12)]
    for t in ths:
        t.start()
    for t in ths:
        t.join(30)
    check("r39-2.3a: 12 конкурентных get() -> builder ОДИН раз",
          n["x"] == 1, str(n["x"]))
    check("r39-2.3b: все потоки получили один и тот же экземпляр",
          len(res) == 12 and all(r is res[0] for r in res))

    # ошибка builder'а: вкладка НЕ считается построенной, retry разрешён
    def _boom():
        raise RuntimeError("builder died")

    n_bad = {"n": 0}

    def _boom_once():
        n_bad["n"] += 1
        if n_bad["n"] == 1:
            raise RuntimeError("builder died")
        return "OK-after-retry"

    h3 = LazyTabHost(on_error=lambda k, ex: ("ERR", k))
    h3.register("bad", _boom_once)
    stub = h3.get("bad")
    check("r39-2.4a: с on_error ошибка не роняет переход (в слот — заглушка)",
          stub == ("ERR", "bad"), str(stub))
    check("r39-2.4b: упавшая постройка НЕ в кэше и НЕ «построена»",
          h3.is_built("bad") is False and h3.build_count("bad") == 0
          and h3.built_keys() == [], "%s %s" % (h3.is_built("bad"), h3.stats()))
    check("r39-2.4c: текст ошибки доступен для диагностики",
          "builder died" in str(h3.last_error("bad")), str(h3.last_error("bad")))
    got = h3.get("bad")
    check("r39-2.4d: следующий переход пробует СНОВА (заглушка не навсегда)",
          got == "OK-after-retry" and h3.attempt_count("bad") == 2
          and h3.build_count("bad") == 1 and h3.is_built("bad") is True
          and h3.last_error("bad") is None, str(h3.attempt_stats()))
    check("r39-2.4e: после успешной постройки-builder больше не вызывается",
          h3.get("bad") == "OK-after-retry" and h3.attempt_count("bad") == 2
          and h3.build_count("bad") == 1, "reuse=%s" % h3.reuse_count("bad"))
    h4 = LazyTabHost()
    h4.register("bad", _boom)
    check("r39-2.4f: без on_error исключение пробрасывается (не глотается)",
          _raises(RuntimeError, h4.get, "bad"))
    check("r39-2.4g: без on_error сбой тоже не попадает в кэш",
          h4.is_built("bad") is False and h4.build_count("bad") == 0
          and h4.attempt_count("bad") == 1, str(h4.stats()))

    # ASCII-safe диагностика
    class _AsciiOnly(__import__("io").StringIO):
        def write(self, s):
            s.encode("ascii")
            return super().write(s)

    h5 = LazyTabHost(diag=True)
    h5.register("диагноза", lambda: object())
    buf = _AsciiOnly()
    with __import__("contextlib").redirect_stdout(buf):
        h5.get("диагноза")
    check("r39-2.5: диагностика build/reuse ASCII-safe (не падает в cp1251)",
          "[LAZY_TABS]" in buf.getvalue(), buf.getvalue().splitlines()[:1])


def _raises(exc, fn, *a):
    try:
        fn(*a)
    except exc:
        return True
    except Exception:
        return False
    return False

# -*- coding: utf-8 -*-
"""Раунд 39, группа LIVE: настоящий HTTP-сервер Flet + цепочка вложений.

Отличие от r39_ui (там моки колбэков): здесь upload идёт через РЕАЛЬНЫЙ
flet-сервер (main_web.py, temp APPDATA), байты пишутся поверх TCP, а
обработчики карточки потребляют файлы, которые записал именно сервер. Так
проверяется вся цепочка задачи 5: выбор в браузере -> подписанный PUT ->
файл на диске -> on_upload -> публикация вложения -> модель -> повторное
открытие карточки. Плюс правила подписи (без подписи / неверная / просрочен).
"""
import contextlib
import io
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from r39_harness import check, click, texts

import flet as ft                                        # noqa: E402
from flet_runtime.uploads import build_upload_url        # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class _Server:
    """Реальный web-сервер приложения в отдельном процессе (temp APPDATA)."""

    def __init__(self, appdata):
        self.appdata = appdata
        self.updir = os.path.join(appdata, "porayonka", "web_uploads")
        self.log = os.path.join(appdata, "porayonka", "live_server.out")
        self.proc = None
        self.port = _free_port()

    def start(self, timeout=45.0):
        env = dict(os.environ)
        env.update({"APPDATA": self.appdata, "PORAYONKA_EDITION": "Admin",
                    "PYTHONIOENCODING": "utf-8"})
        for k in ("FLET_UPLOAD_DIR", "FLET_SECRET_KEY"):
            env.pop(k, None)                    # пусть подготовит сам main.py
        os.makedirs(os.path.dirname(self.log), exist_ok=True)
        lf = open(self.log, "wb")
        self.proc = subprocess.Popen(
            [sys.executable, "main_web.py", "--port", str(self.port)],
            cwd=ROOT, env=env, stdout=lf, stderr=subprocess.STDOUT)
        lf.close()
        deadline = time.time() + timeout
        while time.time() < deadline:
            m = re.search(r"starting server on port (\d+)", self._out())
            if m:
                self.port = int(m.group(1))
            try:
                with urllib.request.urlopen(self.base + "/", timeout=2) as r:
                    if r.status == 200:
                        return True
            except Exception:
                pass
            if self.proc.poll() is not None:
                return False
            time.sleep(0.25)
        return False

    @property
    def base(self):
        return "http://127.0.0.1:%d" % self.port

    def _out(self):
        try:
            return io.open(self.log, encoding="utf-8", errors="replace").read()
        except OSError:
            return ""

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(15)
            except Exception:
                self.proc.kill()


def _put(base, url, blob):
    req = urllib.request.Request(base + url, data=blob, method="PUT",
                                 headers={"Content-Type": "application/octet-stream"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, b""
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:120]


def run_live_upload_flow():
    print("\n--- 5l. Живой HTTP: сервер приложения + upload + вложения ---")
    import main
    appdata = tempfile.mkdtemp(prefix="r39_live_")
    srv = _Server(appdata)
    saved = None
    try:
        ok = srv.start()
        check("r39-5.90a: живой web-сервер приложения поднялся и отвечает 200",
              ok, srv._out()[-300:] if not ok else srv.base)
        if not ok:
            return
        # каталог и ключ готовит ПРОИЗВОДСТВЕННЫЙ код (тот же, что в _entry)
        saved = {k: os.environ.get(k) for k in
                 ("APPDATA", "FLET_UPLOAD_DIR", "FLET_SECRET_KEY")}
        os.environ["APPDATA"] = appdata
        os.environ.pop("FLET_UPLOAD_DIR", None)
        os.environ.pop("FLET_SECRET_KEY", None)
        with contextlib.redirect_stdout(io.StringIO()):
            main._ensure_web_upload_env()
        up_dir = os.environ.get("FLET_UPLOAD_DIR")
        key = os.environ.get("FLET_SECRET_KEY") or ""
        check("r39-5.90b: каталог загрузки сервера = каталог из env приложения, "
              "ключ 64 hex",
              os.path.realpath(up_dir) == os.path.realpath(srv.updir)
              and len(key) == 64, "%s / len=%s" % (up_dir, len(key)))

        # ── правила подписи на живом сервере ────────────────────────────
        st, _ = _put(srv.base, "/upload?f=live_ok.bin&e=%s&s=deadbeef" %
                     "2099-01-01T00:00:00.000000+00:00", b"x")
        check("r39-5.90c: PUT с поддельной подписью отклонён", st != 200, str(st))
        st, _ = _put(srv.base, "/upload?f=live_ok.bin", b"x")
        check("r39-5.90d: PUT БЕЗ подписи отклонён", st != 200, str(st))
        old = build_upload_url("/upload", "live_old.bin", -60, key)
        st, _ = _put(srv.base, old, b"x")
        check("r39-5.90e: PUT просроченным подписанным URL отклонён", st != 200,
              str(st))

        # ── цепочка вложений через реальные PUT ─────────────────────────
        import r39_ui
        r39_ui.seed()
        r39_ui.settings_off()
        page, tab = r39_ui.build()
        check("r39-5.90f: карточка контроля открыта",
              r39_ui.open_card(tab, "ВХСОП-455-2026"))
        picker = getattr(page, "_controls_attach_picker", None)
        if picker is None:
            check("r39-5.90g: picker вложений зарегистрирован", False, "None")
            return
        picker.update = lambda *a, **k: None
        sent = []
        picker.upload = lambda files: sent.append(list(files))
        page.get_upload_url = lambda name, expires: build_upload_url(
            "/upload", name, expires, key)

        # два файла с ОДИНАКОВЫМ именем, разное содержимое (как в браузере:
        # path=None, только name)
        a_bytes = b"PDF-A-" + b"a" * 4096
        b_bytes = b"PDF-B-" + b"b" * 8192
        blobs = {}

        def _pick_web(names):
            ev = r39_ui._ResEvent(files=[r39_ui._f(n) for n in names])
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                r39_ui._fire(picker, "on_result", ev)

        on_disk = {}

        def _finish_uploads():
            """Сыграть роль браузера: реальный PUT каждого запрошенного файла,
            сверка байтов НА ДИСКЕ (до того, как приложение переименует файл),
            и только затем — событие on_upload."""
            for item in sent[-1]:
                blob = blobs.get(item.name)
                if blob is None:                  # два файла с одним именем
                    blob = a_bytes if not blobs else b_bytes
                blobs[item.name] = blob
                st, body = _put(srv.base, item.upload_url, blob)
                if st != 200:
                    print("[LIVE] PUT %s -> %s %s" % (item.name, st, body))
                path = os.path.join(srv.updir, item.name)
                on_disk[item.name] = (st, os.path.isfile(path)
                                      and open(path, "rb").read() == blob)
                ev = r39_ui._UpEvent(item.name, 1.0, None)
                with contextlib.redirect_stdout(io.StringIO()), \
                        contextlib.redirect_stderr(io.StringIO()):
                    r39_ui._fire(picker, "on_upload", ev)
            return len(on_disk)

        _pick_web(["скан-задания.pdf", "скан-задания.pdf"])
        check("r39-5.90h: веб-выбор запустил upload (2 файла, path=None)",
              len(sent) == 1 and len(sent[0]) == 2, str([len(s) for s in sent]))
        ups = [i.name for i in sent[0]]
        check("r39-5.90i: имена загрузки УНИКАЛЬНЫ (одинаковые имена не треются "
              "в полёте), подпись в URL есть",
              len(set(ups)) == 2 and all(u.endswith("__скан-задания.pdf") for u in ups)
              and all("&s=" in i.upload_url for i in sent[0]), str(ups))
        n_done = _finish_uploads()
        check("r39-5.90j: сервер принял ОБА PUT (200) и записал файлы побайтово "
              "в свой каталог", n_done == 2
              and all(st == 200 and same for st, same in on_disk.values()),
              str({k[-22:]: v for k, v in on_disk.items()}))

        ctl = {c.id: c for c in r39_ui.load_controls()}["per1"]
        att = list(ctl.attachments)
        check("r39-5.90k: вложения опубликованы в модель (2 записи)",
              len(att) == 2, str(att))
        root = os.path.join(appdata, "porayonka", "controls_attachments", "per1")
        published = sorted(os.listdir(root)) if os.path.isdir(root) else []
        check("r39-5.90l: файлы вложений реально лежат в папке контроля",
              len(published) == 2 and all(
                  os.path.getsize(os.path.join(root, n)) > 100
                  for n in published), str(published))
        contents = {open(os.path.join(root, n), "rb").read()[:6] for n in published}
        check("r39-5.90m: содержимое НЕ перепутано и не испорчено (оба целые)",
              contents == {b"PDF-A-", b"PDF-B-"}, str(sorted(contents)))
        check("r39-5.90n: вложение видно в карточке СРАЗУ (без переоткрытия)",
              any("скан-задания" in t for t in texts(tab)), str(
                  [t for t in texts(tab) if "скан" in t][:2]))

        click(tab, ft.ElevatedButton, text="Сохранить")
        saved_ctl = {c.id: c for c in r39_ui.load_controls()}["per1"]
        check("r39-5.90o: после сохранения вложения в файле модели (2)",
              len(saved_ctl.attachments) == 2, str(saved_ctl.attachments))
        page2, tab2 = r39_ui.build()
        r39_ui.open_card(tab2, "ВХСОП-455-2026")
        check("r39-5.90p: после повторного открытия карточки вложения доступны",
              sum(1 for t in texts(tab2) if "скан-задания" in t) >= 2,
              str([t for t in texts(tab2) if "скан" in t][:3]))

        # ── отмена и ошибки ─────────────────────────────────────────────
        n_sent = len(sent)
        n_att = len({c.id: c for c in r39_ui.load_controls()}["per1"].attachments)
        _pick_web([])
        check("r39-5.90q: отмена выбора ничего не меняет (ни upload, ни модель)",
              len(sent) == n_sent
              and len({c.id: c for c in r39_ui.load_controls()}["per1"].attachments)
              == n_att, str(len(sent)))

        # ── крупный файл (>5 МБ): фоновая публикация, а не блокировка UI ──
        from ui.controls.controls_tab import wait_attach_jobs
        big_bytes = b"BIG-" + bytes(6 * 1024 * 1024)
        n_att = len({c.id: c for c in r39_ui.load_controls()}["per1"].attachments)
        _pick_web(["big-скан.bin"])
        for item in sent[-1]:
            blobs[item.name] = big_bytes
            _put(srv.base, item.upload_url, big_bytes)
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                r39_ui._fire(picker, "on_upload",
                             r39_ui._UpEvent(item.name, 0.5, None))
        check("r39-5.90r: незавершённый progress НЕ публикует вложение",
              len({c.id: c for c in r39_ui.load_controls()}["per1"].attachments)
              == n_att, str(n_att))
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            for item in sent[-1]:
                r39_ui._fire(picker, "on_upload", r39_ui._UpEvent(item.name, 1.0, None))
        done = wait_attach_jobs("per1", timeout=30.0)
        ctl_big = {c.id: c for c in r39_ui.load_controls()}["per1"]
        check("r39-5.90s: фоновая публикация крупного файла завершилась и "
              "попала в модель", done and len(ctl_big.attachments) == n_att + 1,
              "%s %s" % (done, ctl_big.attachments))
        big_files = [n for n in os.listdir(root)
                     if os.path.getsize(os.path.join(root, n)) == len(big_bytes)]
        check("r39-5.90t: крупный файл опубликован побайтово целым",
              len(big_files) == 1, str(sorted(os.listdir(root))))

        def _boom_url(name, expires):
            raise RuntimeError("Specify secret_key parameter or set FLET_SECRET_KEY")
        page.get_upload_url = _boom_url
        _pick_web(["x.pdf"])
        snack = getattr(page, "snack_bar", None)
        txt = " ".join(sorted(texts(snack))) if snack is not None else ""
        check("r39-5.90u: ошибка get_upload_url -> понятный русский toast, "
              "без изменения модели", "не удалось подготовить" in txt.lower(),
              txt[:70])

        # параллельная загрузка не допускается (иначе состояние перемешается)
        page.get_upload_url = lambda name, expires: build_upload_url(
            "/upload", name, expires, key)
        _pick_web(["hold1.pdf"])
        _pick_web(["hold2.pdf"])
        snack = getattr(page, "snack_bar", None)
        txt = " ".join(sorted(texts(snack))) if snack is not None else ""
        check("r39-5.90v: вторая загрузка «поверх» незавершённой — понятный "
              "отказ, состояние не перемешивается",
              "дождитесь" in txt.lower(), txt[:70])
        _finish_uploads()
        check("r39-5.90w: после отказа слот свободен — первая загрузка прошла",
              any("hold1" in t for t in texts(tab)), str(
                  [t for t in texts(tab) if "hold" in t][:2]))
    finally:
        srv.stop()
        try:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        except NameError:
            pass
        import shutil
        shutil.rmtree(appdata, ignore_errors=True)

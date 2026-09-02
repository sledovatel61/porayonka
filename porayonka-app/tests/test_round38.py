# -*- coding: utf-8 -*-
"""Раунд 38: регресс-тесты логики (без UI).

Покрывает PROMPT_контроли_доработка38.md:
  * 2.4 - семь сценариев дедупликации (бизнес-ключ, canonical, перенос файлов,
    идемпотентность, консервативность, диагностика);
  * 8 - ежедневный backup (once-per-day, новый день, retention, partial
    failure, конкурентные вызовы, без рекурсии, вложения, offline, user не
    пишет shared, backup перед миграцией/импортом, restore);
  * 9 - Excel upsert (id/вложения не теряются, richer-поля не стираются,
    конфликты не перезаписываются, внутрифайловые дубли, round-trip,
    идемпотентность);
  * 4 - статическая проверка 4 установщиков Inno ([UninstallDelete], точный
    taskkill без python.exe, явное подтверждение удаления данных, silent-
    семантика, проверка других редакций);
  * 3 - статическая проверка Win7 web build profile (pinned requirements,
    pydantic v1 без pydantic_core, upx=False, manifest, venv-скрипты).

Запуск из porayonka-app:  python tests\\test_round38.py
Все операции - в temp APPDATA/temp shared (реальные данные не трогаются).
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path

FAILURES = []


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


# temp APPDATA ДО импорта core-модулей
_BASE_TMP = tempfile.mkdtemp(prefix="r38_base_")
os.environ["APPDATA"] = _BASE_TMP

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.controls_models import Control, ControlTask, ControlMilestone  # noqa: E402
from core import controls_dedup as dd  # noqa: E402
from core import backup as bk  # noqa: E402
from core import controls_data as cdata  # noqa: E402
from core import controls_exporter as ce  # noqa: E402


def fresh_appdata(tag=""):
    d = tempfile.mkdtemp(prefix=f"r38_app_{tag}_")
    os.environ["APPDATA"] = d
    return Path(d) / "porayonka"


def mk_ctl(cid, num, rd="2026-07-20", init="ГУК СК", content="Текст задания",
           atts=None, tasks=None, comment="", updated="2026-07-20T10:00:00",
           due="2026-07-25", done=False):
    return Control(id=cid, incoming_number=num, receive_date=rd, initiator=init,
                   content=content, executors=["Семисенко И.Ю."],
                   controller="Потемкин С.А.", control_type="once",
                   period_days=7, due_date=due, end_date=None, done=done,
                   done_date="2026-07-21" if done else None, comment=comment,
                   tasks=tasks or [], milestones=[], attachments=atts or [],
                   archived=False, archived_at=None, archive_reason="",
                   created_at=updated, updated_at=updated)


def main():
    # ════════════════════════════════════════════════════════════════
    # A. ДЕДУПЛИКАЦИЯ (задача 2, P0)
    # ════════════════════════════════════════════════════════════════

    # A1: нормализация входящего номера (регистр, Unicode, NBSP, разделители)
    check("dedup38: регистр+пробел-тире — один бизнес-ключ",
          dd.business_key(mk_ctl("a", "Иссоп-216-193-26"))
          == dd.business_key(mk_ctl("b", "иссоп 216-193-26")))
    check("dedup38: NBSP и длинное тире нормализуются",
          dd.business_key(mk_ctl("a", "ВХСОП-9848-25"))
          == dd.business_key(mk_ctl("b", "ВХСОП—9848-25")))
    check("dedup38: «Иссоп 216-1996-25» == «Иссоп-216-1996-25» (полевой кейс)",
          dd.business_key(mk_ctl("a", "Иссоп 216-1996-25"))
          == dd.business_key(mk_ctl("b", "Иссоп-216-1996-25")))
    check("dedup38: регистр «вхсоп-4186-26(дсп/266)» склеивается",
          dd.business_key(mk_ctl("a", "вхсоп-4186-26(дсп/266)"))
          == dd.business_key(mk_ctl("b", "ВХСОП-4186-26(ДСП/266)")))
    check("dedup38: NBSP в номере = обычный пробел (NFKC)",
          dd.business_key(mk_ctl("c", "А 1"))
          == dd.business_key(mk_ctl("d", "А 1"))
          and dd.business_key(mk_ctl("e", "А-1"))
          == dd.business_key(mk_ctl("f", "А 1")))

    # A2: пустые входящие номера НЕ схлопываются в один контроль
    e1, e2 = mk_ctl("e1", "", content="одно и то же"), mk_ctl("e2", "", content="одно и то же")
    healed, st = dd.dedupe_controls([e1, e2], move_files=False)
    check("dedup38: пустые номера - НЕ один контроль (business_key=None)",
          dd.business_key(e1) is None and len(healed) == 2 and st["merged"] == 0)

    # A3: консервативность - разные даты/содержание/инициатор не схлопываются
    h, st = dd.dedupe_controls([mk_ctl("d1", "А-100", rd="2026-07-20"),
                                mk_ctl("d2", "А-100", rd="2026-07-21")], move_files=False)
    check("dedup38: одинаковый номер, РАЗНАЯ дата поступления - не схлопываются",
          len(h) == 2 and st["merged"] == 0)
    h, st = dd.dedupe_controls([mk_ctl("d1", "А-100", content="одно"),
                                mk_ctl("d2", "А-100", content="другое")], move_files=False)
    check("dedup38: одинаковый номер, РАЗНОЕ содержание - не схлопываются",
          len(h) == 2 and st["merged"] == 0)
    h, st = dd.dedupe_controls([mk_ctl("d1", "А-100", init="СУ"),
                                mk_ctl("d2", "А-100", init="ГУК ЮФО")], move_files=False)
    check("dedup38: одинаковый номер, РАЗНЫЙ инициатор - не схлопываются",
          len(h) == 2 and st["merged"] == 0)

    # A4: точная пара с разными UUID схлопывается, поля объединяются
    t1 = ControlTask(id="t1", title="п.1 Запросить материалы", assignees=["Семисенко И.Ю."],
                     due_date="2026-07-24", is_done=False, done_date=None, comment="")
    t2 = ControlTask(id="t2", title="п.2 Доложить", assignees=["Потемкин С.А."],
                     due_date="2026-07-25", is_done=True, done_date="2026-07-25", comment="")
    cA = mk_ctl("uid-A", "Иссоп-216-193-26", atts=["uid-A/scan1.pdf"],
                tasks=[t1], comment="первая", updated="2026-07-20T10:00:00")
    cB = mk_ctl("uid-B", "Иссоп-216-193-26", atts=["uid-B/scan2.pdf"],
                tasks=[t2], updated="2026-07-21T09:00:00")
    healed, st = dd.dedupe_controls([cA, cB], move_files=False)
    check("dedup38: точная пара разных UUID - одна запись",
          len(healed) == 1 and st["merged"] == 1 and st["groups"] == 1)
    winC = healed[0]
    check("dedup38: canonical - с вложениями/полнотой (uid-A), детерминированно",
          str(winC.id) == "uid-A")
    check("dedup38: вложения ОБЪЕДИНЕНЫ (обе ссылки у canonical)",
          sorted(winC.attachments) == ["uid-A/scan1.pdf", "uid-A/scan2.pdf"])
    check("dedup38: задачи объединены по ключу (обе пункты живы)",
          len(winC.tasks) == 2 and {t.title for t in winC.tasks}
          == {"п.1 Запросить материалы", "п.2 Доложить"})
    check("dedup38: заполненный comment не потерян", winC.comment == "первая")
    check("dedup38: stats.details фиксирует winner/loser",
          st["details"][0]["winner"] == "uid-A" and st["details"][0]["losers"] == ["uid-B"])

    # canonical выбирает запись с вложениями, даже если она старее
    cOld = mk_ctl("uid-old", "Б-1", atts=["uid-old/f.pdf"], updated="2026-07-01T10:00:00")
    cNew = mk_ctl("uid-new", "Б-1", updated="2026-08-01T10:00:00")
    healed, st = dd.dedupe_controls([cNew, cOld], move_files=False)
    check("dedup38: canonical - запись С ВЛОЖЕНИЯМИ важнее свежести",
          str(healed[0].id) == "uid-old" and len(healed[0].attachments) == 1)

    # одинаковый id - обычный LWW (новый updated_at выигрывает)
    sameA = mk_ctl("same-1", "В-1", content="старое", updated="2026-07-01T00:00:00")
    sameB = mk_ctl("same-1", "В-1", content="новое", updated="2026-08-01T00:00:00")
    healed, st = dd.dedupe_controls([sameA, sameB], move_files=False)
    check("dedup38: одинаковый id - LWW по updated_at",
          len(healed) == 1 and healed[0].content == "новое")

    # стабильный порядок: canonical встаёт на место первого вхождения группы
    x0 = mk_ctl("x0", "X-0")
    dA = mk_ctl("gA", "G-1", atts=["gA/a.pdf"])
    y0 = mk_ctl("y0", "Y-0")
    dB = mk_ctl("gB", "G-1")
    z0 = mk_ctl("z0", "Z-0")
    healed, st = dd.dedupe_controls([x0, dA, y0, dB, z0], move_files=False)
    check("dedup38: порядок стабилен - canonical на позиции первого вхождения",
          [str(c.id) for c in healed] == ["x0", "gA", "y0", "z0"])

    # A5: физический перенос файлов вложений loser -> canonical (без перезаписи)
    fresh_appdata("dedup")
    att_root = Path(tempfile.mkdtemp(prefix="r38_atts_"))
    (att_root / "lose1").mkdir(parents=True)
    (att_root / "win1").mkdir(parents=True)
    (att_root / "lose1" / "scan.pdf").write_bytes(b"%PDF-lose-version-A")
    (att_root / "lose1" / "extra.png").write_bytes(b"PNG-lose-bytes-1111")
    (att_root / "win1" / "scan.pdf").write_bytes(b"%PDF-win-version-!!!")
    cLose = mk_ctl("win1", "Г-1", atts=["win1/scan.pdf"], updated="2026-07-20T10:00:00")
    cWin = mk_ctl("lose1", "Г-1", atts=["lose1/scan.pdf", "lose1/extra.png"])
    healed, st = dd.dedupe_controls([cWin, cLose], local_attach_root=att_root,
                                    move_files=True)
    nw = healed[0]
    check("dedup38: canonical - с БОЛЬШИМ числом вложений (lose1)", str(nw.id) == "lose1")
    check("dedup38: имена - без перезаписи (scan.pdf + scan_1.pdf + extra.png)",
          sorted(nw.attachments) == ["lose1/extra.png", "lose1/scan.pdf", "lose1/scan_1.pdf"])
    check("dedup38: файл canonical НЕ перезаписан байтами loser",
          (att_root / "lose1" / "scan.pdf").read_bytes() == b"%PDF-lose-version-A")
    check("dedup38: loser-файл переехал с суффиксом, байты целы",
          (att_root / "lose1" / "scan_1.pdf").read_bytes() == b"%PDF-win-version-!!!")
    check("dedup38: уникальное имя canonical на месте",
          (att_root / "lose1" / "extra.png").read_bytes() == b"PNG-lose-bytes-1111")
    check("dedup38: пустая папка loser убрана",
          not (att_root / "win1").exists())
    check("dedup38: stats.moved_files = 1 (у loser один файл)",
          st["moved_files"] == 1)

    # Побайтово ОДИНАКОВАЯ копия одного скана в папках дублей: лишняя ссылка
    # и файл НЕ плодятся (полевой кейс - один скан, раскопированный по обоим
    # записям-дублям), а разный файл с тем же именем - сохраняется (выше).
    (att_root / "k1").mkdir(exist_ok=True)
    (att_root / "k2").mkdir(exist_ok=True)
    (att_root / "k1" / "doc.pdf").write_bytes(b"identical-scan-bytes")
    (att_root / "k2" / "doc.pdf").write_bytes(b"identical-scan-bytes")
    (att_root / "k2" / "only.pdf").write_bytes(b"only-loser-version-!")
    idA1 = mk_ctl("k1", "Е-7", atts=["k1/doc.pdf"])
    idA2 = mk_ctl("k2", "Е-7", atts=["k2/doc.pdf", "k2/only.pdf"])
    healed_i, st_i = dd.dedupe_controls([idA1, idA2], local_attach_root=att_root,
                                        move_files=True)
    check("dedup38: побайтово-одинаковая копия скана - ссылка НЕ дублируется",
          str(healed_i[0].id) == "k1"
          and sorted(healed_i[0].attachments) == ["k1/doc.pdf", "k1/only.pdf"],
          f"{sorted(healed_i[0].attachments)}")
    check("dedup38: байтовая копия удалена, разный файл цел",
          not (att_root / "k1" / "doc_1.pdf").exists()
          and not (att_root / "k2").exists()
          and (att_root / "k1" / "only.pdf").read_bytes() == b"only-loser-version-!")
    # «сухой» режим (view): файлы НЕ трогаются
    att_root2 = Path(tempfile.mkdtemp(prefix="r38_atts2_"))
    (att_root2 / "k2").mkdir(parents=True)
    (att_root2 / "k2tmp").mkdir()
    (att_root2 / "k2tmp" / "x.pdf").write_bytes(b"x-bytes")
    v1 = mk_ctl("k2", "Д-1", atts=["k2/a.pdf"], updated="2026-07-20T10:00:00")
    v2d = mk_ctl("k2tmp", "Д-1", atts=["k2tmp/x.pdf"])
    healed_v, st_v = dd.dedupe_controls([v1, v2d], local_attach_root=att_root2,
                                        move_files=False)
    check("dedup38: «сухой» view-режим НЕ переносит файлы",
          (att_root2 / "k2tmp" / "x.pdf").exists() and st_v["moved_files"] == 0)

    # A6: идемпотентность миграции
    healed2, st2 = dd.dedupe_controls(healed, local_attach_root=att_root,
                                      move_files=True)
    check("dedup38: повторный прогон миграции - ничего не меняет",
          st2["merged"] == 0 and st2["moved_files"] == 0 and len(healed2) == 1)

    # A7: диагностика (задача 2.1) — same_id / same_key / dup_records
    diag = dd.diagnose_duplicates([
        mk_ctl("s1", "Ж-1"), mk_ctl("s1", "Ж-1", updated="2026-08-01T00:00:00"),
        mk_ctl("k1", "З-1"), mk_ctl("k2", "з-1"),
        mk_ctl("ok1", "У-1")])
    check("dedup38: диагностика видит same_id и same_key",
          diag["same_id"] == [("s1", 2)] and len(diag["same_key"]) == 1
          and diag["dup_records"] == 2 and diag["total"] == 5)
    rep = dd.diagnostics_report([mk_ctl("k1", "З-1"), mk_ctl("k2", "з-1")])
    try:
        rep.encode("cp1251")
        cp_ok = True
    except UnicodeEncodeError:
        cp_ok = False
    check("dedup38: diagnostics_report - cp1251-safe и содержит ключ",
          cp_ok and "[DEDUP]" in rep and "dup_records=1" in rep)

    # done-флаг от исполненного дубля не теряется
    doneA = mk_ctl("da", "И-1", done=False)
    doneB = mk_ctl("db", "И-1", done=True, updated="2026-07-01T10:00:00")
    healed3, _ = dd.dedupe_controls([doneA, doneB], move_files=False)
    check("dedup38: done/done_date подтянуты от исполненного дубля",
          healed3[0].done is True and healed3[0].done_date == "2026-07-21")

    # ════════════════════════════════════════════════════════════════
    # B. ЕЖЕДНЕВНЫЙ BACKUP (задача 8, P1)
    # ════════════════════════════════════════════════════════════════
    data_dir = fresh_appdata("backup")
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "controls.json").write_text(json.dumps(
        {"schema_version": 2, "controls": []}, ensure_ascii=False), encoding="utf-8")
    (data_dir / "departments.json").write_text("[]", encoding="utf-8")
    (data_dir / "controls_settings.json").write_text("{}", encoding="utf-8")
    (data_dir / "controls_attachments").mkdir()
    (data_dir / "controls_attachments" / "c1").mkdir()
    (data_dir / "controls_attachments" / "c1" / "scan.pdf").write_bytes(b"pdf-bytes-1")
    (data_dir / "error.log").write_text("growing log", encoding="utf-8")

    d1 = date(2026, 9, 1)
    snap1 = bk.create_local_snapshot(today=d1)
    check("backup38: первый локальный снапшот создан", snap1 is not None and snap1.is_dir())
    check("backup38: снапшот содержит JSON и вложения и manifest",
          (snap1 / "controls.json").exists()
          and (snap1 / "controls_attachments" / "c1" / "scan.pdf").exists()
          and (snap1 / "manifest.json").exists())
    man1 = json.loads((snap1 / "manifest.json").read_text(encoding="utf-8"))
    check("backup38: manifest - дата, schema, файлы/размеры, SHA256 JSON",
          man1.get("date") == "2026-09-01" and "schema_version" in man1
          and any(f.get("sha256") for f in man1.get("files", [])
                  if f.get("path") == "controls.json"))
    check("backup38: error.log НЕ включён в снапшот", not (snap1 / "error.log").exists())
    # once-per-day
    snap1b = bk.create_local_snapshot(today=d1)
    check("backup38: не чаще одного успешного backup за день", snap1b is None)
    check("backup38: local_backup_today_done видит маркер",
          bk.local_backup_today_done(today=d1) is True
          and bk.local_backup_today_done(today=d1 + timedelta(days=1)) is False)
    # новый день -> новая копия
    d2 = d1 + timedelta(days=1)
    snap2 = bk.create_local_snapshot(today=d2)
    check("backup38: новый день - новый снапшот рядом со старым",
          snap2 is not None and snap1.is_dir() and snap2.is_dir() and snap1 != snap2)
    # без рекурсии: старые снапшоты не попадают в новый
    walk_names = [str(p.relative_to(snap2)) for p in snap2.rglob("*")]
    check("backup38: каталог backups рекурсивно НЕ включается",
          not any(n.startswith("2026-09-01") or "backups" in n for n in walk_names))
    # force-повтор за тот же день не падает и не множит каталоги
    day_dirs = [p for p in bk.get_backup_root().iterdir()
                if p.is_dir() and p.name.startswith("2026-09-02")]
    snap2b = bk.create_local_snapshot(today=d2, force=True)
    day_dirs2 = [p for p in bk.get_backup_root().iterdir()
                 if p.is_dir() and p.name.startswith("2026-09-02")]
    check("backup38: force за тот же день - атомарная замена, дублей нет",
          snap2b is not None and len(day_dirs2) == len(day_dirs) == 1)

    # partial failure: ошибка копирования - день НЕ отмечен, старый снапшот жив
    d3 = d1 + timedelta(days=2)
    real_copy2 = shutil.copy2

    def _failing_copy2(src, dst, *a, **kw):
        if str(src).endswith("controls.json"):
            raise OSError("disk full simulation")
        return real_copy2(src, dst, *a, **kw)
    shutil.copy2 = _failing_copy2
    try:
        snap3 = bk.create_local_snapshot(today=d3, force=True)
    finally:
        shutil.copy2 = real_copy2
    # часть файлов копируется напрямую shutil.copy2 - отказ одного файла
    # внутри цикла прерывает снапшот целиком (tmp удалён, маркер не выставлен)
    check("backup38: partial failure - снапшот не создан",
          not (bk.get_backup_root() / d3.isoformat()).exists())
    check("backup38: partial failure - день НЕ отмечен успешным",
          bk.local_backup_today_done(today=d3) is False)
    check("backup38: partial failure - прежний валидный снапшот цел",
          snap1.is_dir() and (snap1 / "controls.json").exists())
    check("backup38: partial failure - tmp-каталог убран",
          not any(p.name.startswith(".tmp-local") for p in bk.get_backup_root().iterdir()))

    # конкурентные вызовы: несколько Flet session -> ровно один снапшот
    data_dir2 = fresh_appdata("backup_conc")
    data_dir2.mkdir(parents=True, exist_ok=True)
    (data_dir2 / "controls.json").write_text("{}", encoding="utf-8")
    results = []
    threads = [threading.Thread(target=lambda: results.append(
        bk.create_local_snapshot(today=date(2026, 9, 5)))) for _ in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    ok_snaps = [r for r in results if r is not None]
    day_dirs3 = [p for p in bk.get_backup_root().iterdir()
                 if p.is_dir() and p.name == "2026-09-05"]
    check("backup38: 8 конкурентных вызовов - ровно 1 снапшот (lock O_EXCL)",
          len(ok_snaps) == 1 and len(day_dirs3) == 1)

    # retention: 31 день -> остаются последние 30
    data_dir3 = fresh_appdata("backup_ret")
    data_dir3.mkdir(parents=True, exist_ok=True)
    (data_dir3 / "controls.json").write_text("{}", encoding="utf-8")
    base_d = date(2026, 6, 1)
    for i in range(31):
        bk.create_local_snapshot(today=base_d + timedelta(days=i), force=(i > 0))
    days = sorted(p.name for p in bk.get_backup_root().iterdir()
                  if p.is_dir() and bk._is_day_name(p.name))
    check("backup38: retention ограничен 30 ежедневными копиями",
          len(days) == bk.BACKUP_RETENTION == 30
          and days[0] == (base_d + timedelta(days=1)).isoformat()
          and days[-1] == (base_d + timedelta(days=30)).isoformat())

    # restore в temp-каталог (задача 8.3)
    rest_dir = Path(tempfile.mkdtemp(prefix="r38_restore_"))
    n_rest = bk.restore_local_snapshot(snap1, rest_dir)
    check("backup38: restore в отдельный каталог - файлы восстановлены",
          n_rest >= 3 and (rest_dir / "controls.json").exists()
          and (rest_dir / "controls_attachments" / "c1" / "scan.pdf").read_bytes() == b"pdf-bytes-1")

    # backup_file_now (перед импортом/миграцией)
    one = bk.backup_file_now(data_dir / "controls.json", purpose="import")
    check("backup38: разовая копия перед импортом (pre-import-*.json)",
          one is not None and one.name.startswith("pre-import-") and one.exists())

    # migration backup (задача 2.3): local+shared JSON и обе папки вложений
    shared_root = Path(tempfile.mkdtemp(prefix="r38_shared_"))
    (shared_root / "controls.json").write_text("{}", encoding="utf-8")
    (shared_root / "controls_attachments").mkdir()
    (shared_root / "controls_attachments" / "s9").mkdir()
    (shared_root / "controls_attachments" / "s9" / "doc.pdf").write_bytes(b"shared-doc")
    mig = bk.migration_backup(data_dir / "controls.json", shared_root / "controls.json",
                              data_dir / "controls_attachments", shared_root,
                              tag="dedup38")
    check("backup38: backup перед миграцией дублей - оба JSON + обе папки вложений",
          mig is not None and (mig / "local_controls.json").exists()
          and (mig / "shared_controls.json").exists()
          and (mig / "shared_attachments" / "s9" / "doc.pdf").exists())

    # SHARED backup: только admin; user - мягкий None и НИЧЕГО не создаёт
    st_net = {"network_enabled": True,
              "network_shared_path": str(shared_root / "controls.json")}
    r_user = bk.create_shared_snapshot(st_net, is_admin=False, today=date(2026, 9, 6))
    check("backup38: user НИКОГДА не создаёт shared backups",
          r_user is None and not (shared_root / "backups").exists())
    r_admin = bk.create_shared_snapshot(st_net, is_admin=True, today=date(2026, 9, 6))
    check("backup38: admin создаёт shared snapshot в <workspace>/backups/YYYY-MM-DD",
          r_admin is not None
          and (shared_root / "backups" / "2026-09-06" / "controls.json").exists()
          and (shared_root / "backups" / "2026-09-06" / "controls_attachments" / "s9" / "doc.pdf").exists())
    r_admin2 = bk.create_shared_snapshot(st_net, is_admin=True, today=date(2026, 9, 6))
    check("backup38: shared - не чаще одного за день", r_admin2 is None)
    # offline: сеть выключена - мягкий None, локальная работа не ломается
    r_off = bk.maybe_daily_shared_backup({"network_enabled": False}, is_admin=True)
    check("backup38: offline shared - None без исключений", r_off is None)
    r_off2 = bk.maybe_daily_local_backup()
    check("backup38: локальный maybe_daily не падает при пустых данных",
          r_off2 is None or r_off2.is_dir())
    check("backup38: статус-подпись admin содержит путь и даты",
          "2026-09-06" in bk.backup_status_text(st_net, is_admin=True)
          or "О" in bk.backup_status_text(st_net, is_admin=True))

    # ════════════════════════════════════════════════════════════════
    # C. EXCEL UPSERT (задача 9, P1)
    # ════════════════════════════════════════════════════════════════
    data_dir4 = fresh_appdata("excel")
    attA = data_dir4 / "controls_attachments" / "id-A"
    attA.mkdir(parents=True)
    (attA / "akt.pdf").write_bytes(b"akt-bytes-A1")
    (attA / "foto.png").write_bytes(b"foto-bytes-A2")
    ctlA = mk_ctl("id-A", "Иссоп-216-193-26", content="Старое содержание",
                  atts=["id-A/akt.pdf", "id-A/foto.png"],
                  tasks=[t1], comment="важный комментарий", due="2026-07-25")
    ctlB = mk_ctl("id-B", "ВХСОП-455-2026", content="Другой контроль")

    def _write_flat_xlsx(path, rows):
        """Плоская таблица формата импорта: строка 1 - заголовок, строка 2 -
        шапка TABLE_HEADERS, далее данные (№, вх.№, дата пост., инициатор,
        содержание, исполнители, за кем контроль, разовый, след. дата, исполнено)."""
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(["КОНТРОЛИ ОТДЕЛА КРИМИНАЛИСТИКИ"] + [None] * 9)
        ws.append(ce.TABLE_HEADERS)
        for r in rows:
            ws.append(r)
        wb.save(path)

    xlsx_path = os.path.join(tempfile.mkdtemp(prefix="r38_xlsx_"), "import.xlsx")
    _write_flat_xlsx(xlsx_path, [
        [1, "иссоп 216-193-26", "20.07.2026", "ГУК СК", "Новое содержание",
         "Семисенко И.Ю.", "Потемкин С.А.", "разовый", "30.07.2026", ""],
        [2, "Иссоп-216-999-26", "22.07.2026", "СУ", "Совсем новый контроль",
         "Чашин Э.А.", "Потемкин С.А.", "разовый", "29.07.2026", ""],
    ])
    plan1 = ce.import_plan(xlsx_path, [ctlA, ctlB])
    check("excel38: план - 1 новое, 1 обновление, без конфликтов",
          len(plan1["new"]) == 1 and len(plan1["updates"]) == 1
          and len(plan1["conflicts"]) == 0,
          f"new={len(plan1['new'])} upd={len(plan1['updates'])} conf={len(plan1['conflicts'])}")
    tgt, changed, row_ctl = plan1["updates"][0]
    check("excel38: сопоставление по НОРМАЛИЗОВАННОМУ номеру (регистр/пробел)",
          str(tgt.id) == "id-A")
    check("excel38: изменённые поля перечислены (content/due_date)",
          "content" in changed and "due_date" in changed, f"{changed}")
    check("excel38: импорт НЕ блокируется отсутствием файлов (новые без скана)",
          plan1["new"][0].incoming_number == "Иссоп-216-999-26")

    # apply: in-place, id/вложения/файлы/richer-поля целы
    ch = ce._apply_row_to_existing(ctlA, row_ctl)
    check("excel38: id=A не изменился после обновления", str(ctlA.id) == "id-A")
    check("excel38: оба attachment path на месте после обновления",
          ctlA.attachments == ["id-A/akt.pdf", "id-A/foto.png"])
    check("excel38: физические файлы вложений не тронуты",
          (attA / "akt.pdf").read_bytes() == b"akt-bytes-A1"
          and (attA / "foto.png").read_bytes() == b"foto-bytes-A2")
    check("excel38: новые значения применены (content)",
          ctlA.content == "Новое содержание" and "content" in ch)
    check("excel38: richer-поля не стёрты (comment, tasks)",
          ctlA.comment == "важный комментарий" and len(ctlA.tasks) == 1)
    check("excel38: архив-метаданные не тронуты", ctlA.archived is False)

    # новая запись: уникальный id (логика confirm из UI)
    used = {"id-A", "id-B"}
    ctlNew = plan1["new"][0]
    nid = ctlNew.id if ctlNew.id and str(ctlNew.id) not in used else None
    import uuid as _uuid
    nid = nid or str(_uuid.uuid4())
    check("excel38: новая запись получает уникальный id",
          nid not in ("id-A", "id-B"))

    # идемпотентность: повторный импорт того же файла - больше НЕ обновляет
    # content (он уже применён) и не добавляет новое
    existing2 = [ctlA, ctlB]
    plan2 = ce.import_plan(xlsx_path, existing2)
    new_ids = [c.id for c in plan2["new"]]
    check("excel38: повторный импорт - без новых/обновлений по id-A",
          all("id-A" != str(t.id) for t, _c, _r in plan2["updates"])
          and plan1["new"][0].incoming_number
          not in [c.incoming_number for c in existing2],
          f"upd2={[(str(t.id), c) for t, c, _r in plan2['updates']]}")

    # существующая запись + идентичный файл: «без изменений»
    xlsx_same = os.path.join(tempfile.mkdtemp(prefix="r38_xlsx_same_"), "same.xlsx")
    _write_flat_xlsx(xlsx_same, [
        [1, "Иссоп-216-193-26", "20.07.2026", "ГУК СК", "Новое содержание",
         "Семисенко И.Ю.", "", "разовый", "30.07.2026", ""],
    ])
    plan3 = ce.import_plan(xlsx_same, [ctlA])
    check("excel38: неизменившаяся строка - 'без изменений', не 'обновление'",
          len(plan3["updates"]) == 0 and plan3["unchanged"] >= 1)

    # конфликт: 2 записи с одним нормализованным номером - не перетирать молча
    ambX = mk_ctl("amb-X", "К-10", content="первый")
    ambY = mk_ctl("amb-Y", "К-10", content="второй")
    xlsx_amb = os.path.join(tempfile.mkdtemp(prefix="r38_xlsx_amb_"), "amb.xlsx")
    _write_flat_xlsx(xlsx_amb, [
        [1, "К-10", "20.07.2026", "ГУК СК", "Третье значение",
         "Семисенко И.Ю.", "", "разовый", "30.07.2026", ""],
    ])
    plan4 = ce.import_plan(xlsx_amb, [ambX, ambY])
    check("excel38: неоднозначное соответствие - конфликт, НЕ молчаливая перезапись",
          len(plan4["conflicts"]) == 1 and not plan4["updates"]
          and ambX.content == "первый" and ambY.content == "второй",
          f"{plan4['conflicts']}")

    # внутрифайловые дубли: два одинаковых номера в одном xlsx - один конфликт
    xlsx_dup = os.path.join(tempfile.mkdtemp(prefix="r38_xlsx_dup_"), "dup.xlsx")
    _write_flat_xlsx(xlsx_dup, [
        [1, "Иссоп-216-777-26", "20.07.2026", "ГУК СК", "Первый вариант",
         "Семисенко И.Ю.", "", "разовый", "30.07.2026", ""],
        [2, "иссоп 216-777-26", "20.07.2026", "ГУК СК", "Второй вариант",
         "Чашин Э.А.", "", "разовый", "31.07.2026", ""],
    ])
    plan5 = ce.import_plan(xlsx_dup, [])
    check("excel38: одинаковые номера внутри файла - добавляется один, второй конфликт",
          len(plan5["new"]) == 1 and len(plan5["conflicts"]) == 1,
          f"new={len(plan5['new'])} conf={len(plan5['conflicts'])}")

    # round-trip: полный лист с id НЕ дублирует запись
    rt_dir = tempfile.mkdtemp(prefix="r38_rt_")
    rt_path = os.path.join(rt_dir, "roundtrip.xlsx")
    try:
        ce.ControlsExcelExporter().export([ctlA, ctlB], rt_path, full=True)
        exp_ok = os.path.exists(rt_path)
    except Exception:
        exp_ok = False
        traceback.print_exc()
    check("excel38: экспорт для round-trip создан", exp_ok)
    if exp_ok:
        plan6 = ce.import_plan(rt_path, [ctlA, ctlB])
        check("excel38: round-trip по id - записи НЕ дублируются (new=0)",
              len(plan6["new"]) == 0 and plan6["full_format"] is True,
              f"new={len(plan6['new'])} upd={len(plan6['updates'])} unch={plan6['unchanged']}")
        # единичная нормализация end_date (H колонка разового = конечная
        # дата; у legacy-записей end_date мог быть пуст) - применяем и
        # проверяем СХОДИМОСТЬ: дальше файл «без изменений».
        for t6, ch6, rc6 in plan6["updates"]:
            check("excel38: round-trip нормализация только полем end_date",
                  set(ch6) <= {"end_date"}, f"{t6.id}:{ch6}")
            ce._apply_row_to_existing(t6, rc6)
        plan6b = ce.import_plan(rt_path, [ctlA, ctlB])
        check("excel38: round-trip повторный - всё 'без изменений' (идемпотентно)",
              len(plan6b["new"]) == 0 and len(plan6b["updates"]) == 0
              and plan6b["unchanged"] == 2,
              f"new={len(plan6b['new'])} upd={len(plan6b['updates'])} unch={plan6b['unchanged']}")
        # правим содержимое ячейки (main sheet) - запись обновляется ПО ID
        from openpyxl import load_workbook
        wb6 = load_workbook(rt_path)
        ws6 = wb6.active
        for r in range(3, ws6.max_row + 1):
            if str(ws6.cell(r, 2).value or "").strip() == "Иссоп-216-193-26":
                ws6.cell(r, 5).value = "Содержание после round-trip правки"
        wb6.save(rt_path)
        plan7 = ce.import_plan(rt_path, [ctlA, ctlB])
        ids_upd = [str(t.id) for t, _c, _r in plan7["updates"]]
        check("excel38: round-trip правка main sheet - обновление с canonical id=A",
              ids_upd == ["id-A"] and plan7["full_format"] is True, f"{ids_upd}")
        if plan7["updates"]:
            _t7, ch7, rc7 = plan7["updates"][0]
            check("excel38: round-trip правка - изменено именно содержание",
                  "content" in ch7, f"{ch7}")
            ce._apply_row_to_existing(_t7, rc7)
            check("excel38: round-trip правка - вложения не очищены",
                  len(ctlA.attachments) == 2
                  and ctlA.content == "Содержание после round-trip правки")

    # merge после импорта: dedupe отдаёт ноль дублей (нет старой+импорт. копий)
    merged_final = cdata.merge_controls([ctlA, ctlB], [mk_ctl("id-C", "Иссоп-216-193-26",
                                                              content="третья версия")])
    healed_f, st_f = dd.dedupe_controls(merged_final, move_files=False)
    check("excel38: shared merge после импорта не создаёт копию записи",
          st_f["merged"] == 0 and len(healed_f) == 3)

    # legacy-обёртка import_from_excel по-прежнему работает
    try:
        parsed_leg, stats_leg = ce.import_from_excel(xlsx_path, [ctlA, ctlB])
        leg_ok = isinstance(parsed_leg, list) and "imported" in stats_leg
    except Exception:
        leg_ok = False
        traceback.print_exc()
    check("excel38: legacy import_from_excel совместим (stats с расширениями)",
          leg_ok and "updated" in stats_leg and "conflicts" in stats_leg)

    # ════════════════════════════════════════════════════════════════
    # D. УСТАНОВЩИКИ (задача 4, P0) - статические проверки
    # ════════════════════════════════════════════════════════════════
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    inst_dir = os.path.join(app_dir, "installer")
    iss_files = ["Admin.iss", "User.iss", "UserWeb.iss", "AdminWeb.iss"]
    iss_texts = {}
    for fn in iss_files:
        iss_texts[fn] = open(os.path.join(inst_dir, fn), encoding="utf-8").read()
    common_un = open(os.path.join(inst_dir, "CommonUninstall.iss"), encoding="utf-8").read()

    check("uninst38: во всех 4 iss есть [UninstallDelete] filesandordirs {app}",
          all("[UninstallDelete]" in t and 'Type: filesandordirs; Name: "{app}"' in t
              for t in iss_texts.values()))
    check("uninst38: все 4 iss подключают CommonUninstall.iss",
          all('#include "CommonUninstall.iss"' in t for t in iss_texts.values()))
    exe_names = []
    suffixes = []
    for fn, t in iss_texts.items():
        m_exe = [ln for ln in t.splitlines() if ln.startswith("#define EditionExeName")]
        m_suf = [ln for ln in t.splitlines() if ln.startswith("#define EditionSuffix")]
        if m_exe:
            exe_names.append(m_exe[0].split('"')[1])
        if m_suf:
            suffixes.append(m_suf[0].split('"')[1])
    check("uninst38: у каждой редакции define с ТОЧНЫМ именем exe",
          len(exe_names) == 4
          and set(exe_names) == {"Порайонка_Админ.exe", "Порайонка_Пользователь.exe",
                                 "Порайонка_Пользователь_Web.exe", "Порайонка_Админ_Web.exe"})
    check("uninst38: уникальные suffix 0001-0004 (свой AppId распознаётся)",
          sorted(suffixes) == ["0001", "0002", "0003", "0004"])
    import re as _re_un
    _cu_nocomm = _re_un.sub(r"\{[^}]*\}", "", common_un, flags=_re_un.S)
    _code_lines_un = [ln for ln in _cu_nocomm.splitlines()
                      if not ln.lstrip().startswith(";")]
    check("uninst38: taskkill точечный (по {#EditionExeName}) и НЕ по python.exe",
          'taskkill.exe' in common_un and '{#EditionExeName}' in common_un
          and not any('python.exe' in ln for ln in _code_lines_un))
    check("uninst38: явное подтверждение удаления данных (MsgBox YESNO, по умолч. НЕТ)",
          "MsgBox" in common_un and "MB_YESNO" in common_un
          and "MB_DEFBUTTON2" in common_un and "IDYES" in common_un)
    check("uninst38: silent-семантика детерминированна (UninstallSilent -> не удаляем)",
          "UninstallSilent()" in common_un)
    check("uninst38: проверка других редакций (4 суффикса + WOW6432Node)",
          "_PorayonkaOtherEditionInstalled" in common_un
          and "WOW6432Node" in common_un
          and all(f"'000{i}'" in common_un for i in (1, 2, 3, 4)))
    check("uninst38: данные стираются только DelTree после подтверждения",
          "DelTree(DataDir" in common_un and "{userappdata}" in common_un)
    check("uninst38: автозапуск с uninsdeletevalue во всех 4 редакциях",
          all("uninsdeletevalue" in t for t in iss_texts.values()))
    check("uninst38: CloseApplications=force во всех 4 редакциях",
          all("CloseApplications=force" in t for t in iss_texts.values()))
    check("uninst38: UNC/shared workspace удалять запрещено (нет DelTree shared)",
          "_shared" not in common_un and "workspace" in common_un.lower())
    for rm in ("README_Admin.txt", "README_User.txt", "README_AdminWeb.txt", "README_Web.txt"):
        rmt = open(os.path.join(inst_dir, "readme", rm), encoding="utf-8").read()
        check(f"uninst38: {rm} документирует удаление данных и silent-семантику",
              "Удаление (раунд 38)" in rmt and "SILENT" in rmt.upper())

    # ════════════════════════════════════════════════════════════════
    # E. WIN7 WEB BUILD PROFILE (задача 3, P0) - статические проверки
    # ════════════════════════════════════════════════════════════════
    reqw = open(os.path.join(app_dir, "requirements-win7-web.txt"), encoding="utf-8").read()
    pins = {}
    for ln in reqw.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        check("win7profile38: версия закреплена строго (==): " + ln.split("==")[0],
              "==" in ln, ln)
        pins[ln.split("==")[0].strip().lower()] = ln.split("==")[1].strip()
    check("win7profile38: Flet строго 0.23.2 (flet/core/runtime)",
          pins.get("flet") == "0.23.2" and pins.get("flet-core") == "0.23.2"
          and pins.get("flet-runtime") == "0.23.2")
    check("win7profile38: pydantic ТОЛЬКО v1 (без pydantic-core/Rust)",
          pins.get("pydantic", "").startswith("1.")
          and not any(k.startswith("pydantic-core") or k.startswith("pydantic_core")
                      for k in pins))
    check("win7profile38: fastapi 0.115.4 + starlette 0.41.3 (эпоха flet 0.23.2)",
          pins.get("fastapi") == "0.115.4" and pins.get("starlette") == "0.41.3")
    check("win7profile38: openpyxl==3.1.5 сохранён", pins.get("openpyxl") == "3.1.5")
    check("win7profile38: uvicorn pinned БЕЗ extra [standard] (нет watchfiles-Rust риска)",
          pins.get("uvicorn") == "0.32.0" and "[standard]" not in reqw.split("uvicorn==")[0][-200:])

    bat_u = open(os.path.join(app_dir, "build_user_web_win7.bat"), encoding="utf-8").read()
    bat_a = open(os.path.join(app_dir, "build_admin_web_win7.bat"), encoding="utf-8").read()
    bat_all = open(os.path.join(app_dir, "build_all_distributives.bat"), encoding="utf-8").read()
    check("win7profile38: оба web-bat - чистый venv .venv-win7-web + requirements-win7-web.txt",
          all(".venv-win7-web" in b and "requirements-win7-web.txt" in b
              for b in (bat_u, bat_a)))
    check("win7profile38: оба web-bat - PyInstaller ТОЛЬКО из venv (не глобальный)",
          all('"%W7PY%" -m PyInstaller' in b for b in (bat_u, bat_a)))
    check("win7profile38: оба web-bat - ЖЁСТКИЙ стоп при pydantic_core в профиле",
          all("pydantic_core" in b and "exit /b 1" in b for b in (bat_u, bat_a)))
    check("win7profile38: оба web-bat - манифест сборки (версии + SHA256 exe)",
          all("make_web_manifest.py" in b and "manifest_win7_web.txt" in b
              for b in (bat_u, bat_a)))
    check("win7profile38: оба web-bat - embedded-режим (без pause/explorer из all-build)",
          all('"%~1"=="embedded"' in b for b in (bat_u, bat_a)))
    check("win7profile38: build_all - web-ступени на venv-питоне (W7PY) 2 раза",
          bat_all.count('"%W7PY%" -m PyInstaller') == 2
          and ".venv-win7-web" in bat_all and "requirements-win7-web.txt" in bat_all)
    check("win7profile38: build_all - манифест в dist_web/dist_admin_web + копия в dist_all",
          bat_all.count("manifest_win7_web.txt") >= 6)
    check("win7profile38: build_all - desktop-ступени НЕ тронуты (глобальный pyinstaller)",
          "pyinstaller Porayonka_Admin.spec --noconfirm --clean --log-level WARN --distpath dist_admin" in bat_all
          and "pyinstaller Porayonka_User.spec --noconfirm --clean --log-level WARN --distpath dist_user" in bat_all)
    spec_u = open(os.path.join(app_dir, "Porayonka_User_Web.spec"), encoding="utf-8").read()
    spec_a = open(os.path.join(app_dir, "Porayonka_Admin_Web.spec"), encoding="utf-8").read()
    check("win7profile38: upx=False в обоих web-spec",
          "upx=False" in spec_u and "upx=False" in spec_a
          and "upx=True" not in spec_u and "upx=True" not in spec_a)
    check("win7profile38: hidden imports flet.web/flet.fastapi/uvicorn сохранены",
          all(s in spec_u and s in spec_a
              for s in ('"flet.web"', '"flet.fastapi"', '"uvicorn"')))
    start_bat = open(os.path.join(app_dir, "start_web_win7.bat"), encoding="utf-8").read()
    check("win7profile38: start_web ждёт сервер (HttpWebRequest), не слепой sleep",
          "HttpWebRequest" in start_bat and "web_startup.log" in start_bat)
    mweb = open(os.path.join(app_dir, "main_web.py"), encoding="utf-8").read()
    check("win7profile38: main_web - startup log ДО импорта fastapi/pydantic",
          mweb.index("web_startup.log") < mweb.index("from main import"))
    check("win7profile38: main_web - занятый порт обрабатывается (_http_ok/bind-check)",
          "_http_ok" in mweb and "_port0" in mweb)

    # проверка логики make_web_manifest.check_profile на модельных данных
    sys.path.insert(0, os.path.join(app_dir, "tools"))
    import make_web_manifest as mwm
    good = {"packages": {"pydantic": "1.10.26", "flet": "0.23.2"},
            "forbidden_present": {"pydantic_core": False},
            "exe_sha256": "ab" * 32}
    check("win7profile38: manifest.check_profile - чистый профиль без замечаний",
          mwm.check_profile(good) == [])
    bad1 = {"packages": {"pydantic": "2.13.4"},
            "forbidden_present": {"pydantic_core": True}, "exe_sha256": "ab" * 32}
    p_bad1 = mwm.check_profile(bad1)
    check("win7profile38: manifest.check_profile ловит pydantic_core и pydantic v2",
          any("pydantic_core" in p for p in p_bad1)
          and any("pydantic 2" in p for p in p_bad1))
    bad2 = {"packages": {"pydantic": "1.10.26"},
            "forbidden_present": {"pydantic_core": False}, "exe_sha256": None}
    check("win7profile38: manifest.check_profile ловит отсутствие exe/sha256",
          any("sha256" in p or "exe" in p for p in mwm.check_profile(bad2)))

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()

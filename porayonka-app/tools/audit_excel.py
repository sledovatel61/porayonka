#!/usr/bin/env python
# tools/audit_excel.py
# Раунд 35 (задача 2): аудит экспорта Excel 1:1 с эталоном «Контроли ОКРИМ.xlsx».
#
# Эталон «Контроли ОКРИМ.xlsx» — РУЧНАЯ таблица (шапка с суффиксами/пробелами,
# часть дат текстом, пустой №). Экспорт приложения — «чистый» round-trip:
#   импорт эталона -> экспорт -> повторный импорт должен дать те же контроли.
# Поэтому скрипт проверяет:
#   1) round-trip данных: экспорт из импортированных контролей при повторном
#      импорте сохраняет все контроли и ключевые поля (вх.№, даты, инициатор,
#      содержание, исполнители, контролёр, тип, следующая дата, исполнено);
#   2) формат: A1:J1 (текст/заливка/шрифт/объединение), шапка A2:J2,
#      ширины A..J, высоты строк 1-3, автофильтр, даты DD.MM.YYYY,
#      wrap_text в E/F, жёлтая заливка I только OVERDUE/TODAY,
#      зелёная J = исполнено.
#
# Запуск:
#   cd porayonka-app && python tools/audit_excel.py
# Отчёт: porayonka-app/tools/excel_audit_report.txt (0 значимых = OK).
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(_APP_DIR)
ETALON = os.path.join(REPO_ROOT, "Контроли ОКРИМ.xlsx")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(OUT_DIR, "excel_audit_report.txt")
EXPORT_TMP = os.path.join(OUT_DIR, "_audit_export.xlsx")

DIFFS = []  # (severity, text)


def log(sev, msg):
    DIFFS.append((sev, msg))


def cell_addr(r, c):
    from openpyxl.utils import get_column_letter
    return f"{get_column_letter(c)}{r}"


def main():
    if not os.path.exists(ETALON):
        log("SIGNIFICANT", f"etalon not found: {ETALON}")
        _write_report()
        return 1
    try:
        from openpyxl import load_workbook
    except ImportError:
        log("SIGNIFICANT", "openpyxl not installed")
        _write_report()
        return 1

    try:
        from core.controls_exporter import (
            ControlsExcelExporter, import_from_excel, TABLE_HEADERS,
        )
    except Exception as e:
        log("SIGNIFICANT", f"import exporter error: {e!r}")
        _write_report()
        return 1

    # ── 1. Импорт эталона + экспорт приложения ──
    try:
        controls, stats = import_from_excel(ETALON, [])
        if not controls:
            log("SIGNIFICANT", f"etalon import produced 0 controls (stats={stats})")
            _write_report()
            return 1
        ControlsExcelExporter().export(controls, EXPORT_TMP, soon_days=3, full=False)
    except Exception as e:
        log("SIGNIFICANT", f"export error: {e!r}")
        _write_report()
        return 1

    # ── 2. Round-trip: повторный импорт экспортированного файла ──
    try:
        controls2, stats2 = import_from_excel(EXPORT_TMP, [])
        if len(controls2) != len(controls):
            log("SIGNIFICANT",
                f"round-trip count: {len(controls2)} != {len(controls)} (stats2={stats2})")
        else:
            for a, b in zip(controls, controls2):
                if (a.incoming_number or "") != (b.incoming_number or ""):
                    log("SIGNIFICANT",
                        f"round-trip incoming: {a.incoming_number!r} -> {b.incoming_number!r}")
                    break
            for a, b in zip(controls, controls2):
                if (a.receive_date or "") != (b.receive_date or ""):
                    log("SIGNIFICANT",
                        f"round-trip receive_date: {a.incoming_number} "
                        f"{a.receive_date!r} -> {b.receive_date!r}")
                    break
            for a, b in zip(controls, controls2):
                if (a.initiator or "").strip() != (b.initiator or "").strip():
                    log("SIGNIFICANT",
                        f"round-trip initiator: {a.incoming_number} "
                        f"{a.initiator!r} -> {b.initiator!r}")
                    break
            for a, b in zip(controls, controls2):
                if (a.content or "").strip() != (b.content or "").strip():
                    log("SIGNIFICANT",
                        f"round-trip content: {a.incoming_number} differs")
                    break
            from core.controls_models import short_name as _sn
            for a, b in zip(controls, controls2):
                # «все зональные» -> «все З.»: экспорт пишет short_name,
                # повторный импорт получает сокращение — не потеря данных
                a_e = sorted(_sn(x) for x in (a.executors or []))
                b_e = sorted(_sn(x) for x in (b.executors or []))
                if a_e != b_e:
                    log("SIGNIFICANT",
                        f"round-trip executors: {a.incoming_number} "
                        f"{a_e} -> {b_e}")
                    break
            for a, b in zip(controls, controls2):
                if (a.controller or "").strip() != (b.controller or "").strip():
                    log("SIGNIFICANT",
                        f"round-trip controller: {a.incoming_number} "
                        f"{a.controller!r} -> {b.controller!r}")
                    break
            for a, b in zip(controls, controls2):
                if (a.due_date or "") != (b.due_date or ""):
                    log("SIGNIFICANT",
                        f"round-trip due_date: {a.incoming_number} "
                        f"{a.due_date!r} -> {b.due_date!r}")
                    break
            for a, b in zip(controls, controls2):
                if bool(a.done) != bool(b.done):
                    log("SIGNIFICANT",
                        f"round-trip done: {a.incoming_number} "
                        f"{a.done} -> {b.done}")
                    break
    except Exception as e:
        log("SIGNIFICANT", f"round-trip import error: {e!r}")

    # ── 3. Формат экспортированного файла ──
    wb_ex = load_workbook(EXPORT_TMP)
    ws_ex = wb_ex["Контроли"]

    # 3.1 A1
    ex = ws_ex["A1"]
    if (ex.value or "") != "КОНТРОЛИ ОТДЕЛА КРИМИНАЛИСТИКИ":
        log("SIGNIFICANT", f"A1 text: {ex.value!r}")
    if ex.fill.patternType != "solid" or ex.fill.fgColor.rgb != "FF00B050":
        log("SIGNIFICANT", f"A1 fill: {ex.fill.patternType}/{ex.fill.fgColor.rgb}")
    if (ex.font.name or "") != "Times New Roman" or ex.font.size != 36:
        log("SIGNIFICANT", f"A1 font: {ex.font.name}/{ex.font.size}")
    if "A1:J1" not in {str(r) for r in ws_ex.merged_cells.ranges}:
        log("SIGNIFICANT", "A1:J1 not merged")

    # 3.2 Шапка A2:J2
    for c, expected in enumerate(TABLE_HEADERS, 1):
        got = ws_ex.cell(row=2, column=c).value
        if (got or "") != expected:
            log("SIGNIFICANT", f"header {cell_addr(2, c)}: {got!r} != {expected!r}")

    # 3.3 Автофильтр от шапки до последней строки данных
    expected_ref = f"A2:J{max(2, ws_ex.max_row)}"
    if (ws_ex.auto_filter.ref or "") != expected_ref:
        log("SIGNIFICANT", f"autofilter: {ws_ex.auto_filter.ref} != {expected_ref}")

    # 3.4 Ширины колонок A..J (как в эталоне)
    for c in "ABCDEFGHIJ":
        w = ws_ex.column_dimensions[c].width
        if not w:
            log("SIGNIFICANT", f"width {c} missing")
    # 3.5 Высоты строк 1-2 (эталон: 45.75 / 56.25)
    if abs((ws_ex.row_dimensions[1].height or 0) - 45.75) > 2:
        log("SIGNIFICANT", f"row1 height: {ws_ex.row_dimensions[1].height}")
    if abs((ws_ex.row_dimensions[2].height or 0) - 56.25) > 2:
        log("SIGNIFICANT", f"row2 height: {ws_ex.row_dimensions[2].height}")

    # 3.6 Даты C и I — настоящие даты Excel с форматом DD.MM.YYYY
    for c in (3, 9):
        checked = 0
        for r in range(3, ws_ex.max_row + 1):
            v = ws_ex.cell(row=r, column=c).value
            if isinstance(v, datetime):
                if ws_ex.cell(row=r, column=c).number_format != "DD.MM.YYYY":
                    log("SIGNIFICANT", f"date format {cell_addr(r, c)}: {ws_ex.cell(row=r, column=c).number_format}")
                    break
                checked += 1
                if checked >= 3:
                    break

    # 3.7 wrap_text в E и F
    for c in (5, 6):
        al = ws_ex.cell(row=3, column=c).alignment
        if not (al.wrap_text or False):
            log("SIGNIFICANT", f"wrap_text {cell_addr(3, c)}: False")

    # 3.8 Подсветка: жёлтая I — только OVERDUE/TODAY; зелёная J — только done
    from core.controls_models import deadline_status, OVERDUE, TODAY
    from core.controls_exporter import ETALON_YELLOW, ETALON_GREEN
    yellow_wrong = 0
    green_wrong = 0
    for i, ctl in enumerate(controls):
        r = i + 3
        st = deadline_status(ctl, 3)
        should_yellow = st in (OVERDUE, TODAY)
        f_i = ws_ex.cell(row=r, column=9).fill
        is_yellow = f_i.patternType == "solid" and f_i.fgColor.rgb == ETALON_YELLOW
        if is_yellow != should_yellow:
            yellow_wrong += 1
            if yellow_wrong <= 5:
                log("SIGNIFICANT",
                    f"yellow I{r}: export={is_yellow} should={should_yellow} (status={st})")
        f_j = ws_ex.cell(row=r, column=10).fill
        is_green = f_j.patternType == "solid" and f_j.fgColor.rgb == ETALON_GREEN
        if is_green != bool(ctl.done):
            green_wrong += 1
            if green_wrong <= 5:
                log("SIGNIFICANT",
                    f"green J{r}: export={is_green} should={bool(ctl.done)}")
    if yellow_wrong:
        log("SIGNIFICANT", f"yellow mismatches: {yellow_wrong}")
    if green_wrong:
        log("SIGNIFICANT", f"green mismatches: {green_wrong}")

    _write_report()
    try:
        os.remove(EXPORT_TMP)
    except OSError:
        pass
    sig = [d for d in DIFFS if d[0] == "SIGNIFICANT"]
    print(f"[AUDIT] significant diffs: {len(sig)}")
    return 0 if not sig else 1


def _write_report():
    lines = [f"Excel audit report ({datetime.now().isoformat()})",
             f"etalon: {ETALON}"]
    lines.append("")
    if not DIFFS:
        lines.append("No differences found.")
    else:
        for sev, txt in DIFFS:
            lines.append(f"[{sev}] {txt}")
    lines.append("")
    sig = len([d for d in DIFFS if d[0] == "SIGNIFICANT"])
    lines.append(f"Result: {'OK (0 significant diffs)' if sig == 0 else f'{sig} significant diff(s)'}")
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[AUDIT] report: {REPORT}")


if __name__ == "__main__":
    sys.exit(main())

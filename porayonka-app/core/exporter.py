# core/exporter.py
# Экспорт данных в Excel (openpyxl) и HTML для печати
# ИЗМЕНЕНИЯ: добавлено подробное логирование

from datetime import datetime
from pathlib import Path
from typing import List
from .models import Department, Status


class ExcelExporter:
    """
    Экспорт списка отделов в .xlsx файл с профессиональным
    форматированием: цветные статусы, границы, автоширина, сводка.
    """

    STATUS_STYLES = {
        Status.RECEIVED: {
            "fill": "27AE60",
            "text": "FFFFFF",
            "label": "Получено",
        },
        Status.IN_PROGRESS: {
            "fill": "F39C12",
            "text": "FFFFFF",
            "label": "В работе",
        },
        Status.EMPTY: {
            "fill": "ECF0F1",
            "text": "7F8C8D",
            "label": "—",
        },
    }

    def export(self, departments: List[Department], filepath: str) -> None:
        """
        Создать и сохранить .xlsx файл.
        :param departments: список отделов
        :param filepath: полный путь для сохранения
        """
        print(f"[EXCEL] Начинаю экспорт Excel, отделов: {len(departments)}")
        print(f"[EXCEL] Целевой файл: {filepath}")

        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
            print("[EXCEL] openpyxl импортирован успешно")
        except ImportError as ie:
            print(f"[EXCEL] [ERROR] ImportError: {ie}")
            raise ImportError(
                "Библиотека openpyxl не установлена.\n"
                "Выполните: pip install openpyxl"
            )

        wb = Workbook()
        ws = wb.active
        ws.title = "Статусы отделов"

        # ── Стили ────────────────────────────────────────────────
        header_fill = PatternFill(
            start_color="2C3E50", end_color="2C3E50", fill_type="solid"
        )
        header_font = Font(bold=True, color="FFFFFF", size=12)
        center_align = Alignment(horizontal="center", vertical="center")
        left_align = Alignment(horizontal="left", vertical="center")
        thin = Side(style="thin")
        thin_border = Border(left=thin, right=thin, top=thin, bottom=thin)

        # ── Заголовки ─────────────────────────────────────────────
        headers = ["№", "Следственный отдел", "Статус", "Обновлено"]
        col_widths = [8, 52, 20, 20]

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_align
            cell.border = thin_border
        ws.row_dimensions[1].height = 22

        # ── Строки данных ──────────────────────────────────────────
        print(f"[EXCEL] Заполняю {len(departments)} строк...")
        for row_idx, dept in enumerate(departments, 2):
            style = self.STATUS_STYLES[dept.status]

            num_cell = ws.cell(
                row=row_idx, column=1,
                value="" if dept.is_ovd else dept.id
            )
            num_cell.alignment = center_align
            num_cell.border = thin_border

            name_cell = ws.cell(row=row_idx, column=2, value=dept.name)
            name_cell.font = Font(italic=dept.is_ovd, size=11)
            name_cell.alignment = left_align
            name_cell.border = thin_border

            status_cell = ws.cell(row=row_idx, column=3, value=style["label"])
            status_cell.fill = PatternFill(
                start_color=style["fill"],
                end_color=style["fill"],
                fill_type="solid",
            )
            status_cell.font = Font(color=style["text"], bold=True, size=11)
            status_cell.alignment = center_align
            status_cell.border = thin_border

            date_str = (
                dept.updated_at.strftime("%d.%m.%Y %H:%M")
                if dept.updated_at else ""
            )
            date_cell = ws.cell(row=row_idx, column=4, value=date_str)
            date_cell.alignment = center_align
            date_cell.border = thin_border

            if row_idx % 2 == 0:
                row_fill = PatternFill(
                    start_color="F8F9FA", end_color="F8F9FA", fill_type="solid"
                )
                num_cell.fill = row_fill
                name_cell.fill = row_fill
                date_cell.fill = row_fill

        # ── Сводка ────────────────────────────────────────────────
        received = sum(1 for d in departments if d.status == Status.RECEIVED)
        in_progress = sum(1 for d in departments if d.status == Status.IN_PROGRESS)
        empty = sum(1 for d in departments if d.status == Status.EMPTY)

        summary_row = len(departments) + 3
        ws.cell(row=summary_row, column=1, value="ИТОГО:").font = Font(bold=True, size=12)
        ws.cell(row=summary_row, column=2,
                value=f"Получено: {received}").font = Font(color="27AE60", bold=True)
        ws.cell(row=summary_row + 1, column=2,
                value=f"В работе: {in_progress}").font = Font(color="F39C12", bold=True)
        ws.cell(row=summary_row + 2, column=2,
                value=f"Не получено: {empty}").font = Font(color="7F8C8D", bold=True)
        ws.cell(row=summary_row + 3, column=2,
                value=f"Всего: {len(departments)}").font = Font(bold=True)

        # ── Ширина столбцов ───────────────────────────────────────
        for col_idx, width in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = width

        # ── Настройки печати ──────────────────────────────────────
        ws.page_setup.orientation = "landscape"
        ws.page_margins.left = 0.5
        ws.page_margins.right = 0.5
        ws.page_margins.top = 0.75
        ws.page_margins.bottom = 0.75
        ws.print_options.horizontalCentered = True

        # ── Сохранить ─────────────────────────────────────────────
        print(f"[EXCEL] Сохраняю файл...")
        wb.save(filepath)
        print(f"[EXCEL] [OK] Файл сохранён: {filepath}")


class HTMLExporter:
    """
    Экспорт в красиво оформленный HTML-файл для печати.
    """

    STATUS_STYLE = {
        Status.RECEIVED: "background:#27AE60;color:#fff;font-weight:600;",
        Status.IN_PROGRESS: "background:#F39C12;color:#fff;font-weight:600;",
        Status.EMPTY: "background:#ECF0F1;color:#7F8C8D;",
    }
    STATUS_LABEL = {
        Status.RECEIVED: "✅ Получено",
        Status.IN_PROGRESS: "🔄 В работе",
        Status.EMPTY: "—",
    }

    def export(self, departments: List[Department], filepath: str) -> None:
        """
        Создать и сохранить .html файл.
        :param departments: список отделов
        :param filepath: полный путь для сохранения
        """
        print(f"[HTML] Начинаю экспорт HTML, отделов: {len(departments)}")
        print(f"[HTML] Целевой файл: {filepath}")

        date_str = datetime.now().strftime("%d.%m.%Y")
        datetime_str = datetime.now().strftime("%d.%m.%Y %H:%M")

        rows_html = ""
        for dept in departments:
            num_html = "" if dept.is_ovd else str(dept.id)
            name_style = "font-style:italic;color:#64748b;" if dept.is_ovd else ""
            status_style = self.STATUS_STYLE[dept.status]
            status_label = self.STATUS_LABEL[dept.status]
            updated = (
                dept.updated_at.strftime("%d.%m.%Y %H:%M")
                if dept.updated_at else ""
            )
            rows_html += f"""
    <tr>
      <td style="text-align:center;padding:10px 12px;border:1px solid #dee2e6;">{num_html}</td>
      <td style="padding:10px 14px;border:1px solid #dee2e6;{name_style}">{dept.name}</td>
      <td style="text-align:center;padding:10px 12px;border:1px solid #dee2e6;{status_style}">{status_label}</td>
      <td style="text-align:center;padding:10px 12px;border:1px solid #dee2e6;color:#64748b;font-size:13px;">{updated}</td>
    </tr>"""

        received = sum(1 for d in departments if d.status == Status.RECEIVED)
        in_progress = sum(1 for d in departments if d.status == Status.IN_PROGRESS)
        empty = sum(1 for d in departments if d.status == Status.EMPTY)
        total = len(departments)

        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Порайонка — {date_str}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #2c3e50; background: #f8f9fa; padding: 30px; }}
    .header {{ background: linear-gradient(135deg, #1e293b, #0f172a); color: white; padding: 20px 30px; border-radius: 12px; margin-bottom: 25px; display: flex; align-items: center; gap: 15px; }}
    .header h1 {{ font-size: 26px; font-weight: 700; }}
    .header p {{ font-size: 14px; color: #94a3b8; margin-top: 4px; }}
    .header .date {{ margin-left: auto; text-align: right; font-size: 13px; color: #94a3b8; }}
    .btn-print {{ display: inline-flex; align-items: center; gap: 8px; padding: 10px 20px; background: #3b82f6; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; margin-bottom: 20px; }}
    .btn-print:hover {{ background: #2563eb; }}
    table {{ border-collapse: collapse; width: 100%; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
    thead tr {{ background: linear-gradient(135deg, #1e293b, #334155); color: white; }}
    th {{ padding: 14px 16px; text-align: left; font-size: 13px; font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; }}
    th:first-child {{ text-align: center; width: 60px; }}
    th:nth-child(3), th:nth-child(4) {{ text-align: center; }}
    tbody tr:nth-child(even) {{ background: #f8faf0; }}
    tbody tr:hover {{ background: #eff6ff; }}
    .summary {{ margin-top: 25px; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); display: flex; gap: 30px; align-items: center; }}
    .footer {{ margin-top: 20px; text-align: center; color: #94a3b8; font-size: 12px; }}
    @media print {{
      body {{ background: white; padding: 10mm; }}
      .no-print {{ display: none !important; }}
      .header {{ border-radius: 0; }}
      table {{ box-shadow: none; }}
    }}
  </style>
</head>
<body>
  <div class="header">
    <div><div style="font-size:36px;">🏛</div></div>
    <div>
      <h1>Порайонка</h1>
      <p>Следственный комитет РФ · Ростовская область</p>
    </div>
    <div class="date">Сформировано<br><strong>{datetime_str}</strong></div>
  </div>
  <div class="no-print">
    <button class="btn-print" onclick="window.print()">🖨️ Распечатать</button>
  </div>
  <table>
    <thead>
      <tr>
        <th style="text-align:center;">№</th>
        <th>Следственный отдел</th>
        <th style="text-align:center;width:160px;">Статус</th>
        <th style="text-align:center;width:160px;">Обновлено</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>
  <div class="summary">
    <strong>ИТОГО:</strong>
    <span style="color:#27AE60;">● Получено: <strong>{received}</strong></span>
    <span style="color:#F39C12;">● В работе: <strong>{in_progress}</strong></span>
    <span style="color:#94a3b8;">● Не получено: <strong>{empty}</strong></span>
    <span style="margin-left:auto;">Всего: <strong>{total}</strong></span>
  </div>
  <div class="footer">Данные сохранены автоматически · 29 отделов · Порайонка v1.0</div>
</body>
</html>"""

        Path(filepath).write_text(html, encoding="utf-8")
        print(f"[HTML] [OK] Файл сохранён: {filepath}")
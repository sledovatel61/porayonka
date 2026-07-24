# core/zonal_exporter.py
# Экспорт зональных данных в Excel
from datetime import datetime
from typing import List, Optional
from .zonal_models import ZonalCollection, ReportItemType, Criminalist
from .zonal_data import get_report_data, get_summary
from .constants import INITIAL_DEPARTMENTS


class ZonalExcelExporter:
    """Экспорт данных зональных криминалистов в Excel"""

    def export(self, collection: ZonalCollection, filepath: str) -> None:
        """Создать и сохранить .xlsx файл с зональными данными"""
        print(f"[ZONAL_EXCEL] Начинаю экспорт, криминалистов: {len(collection.criminalists)}")
        print(f"[ZONAL_EXCEL] Файл: {filepath}")
        print(f"[ZONAL_EXCEL] Режим по отделам: {collection.template.use_departments_mode}")

        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
        except ImportError as e:
            print(f"[ZONAL_EXCEL] ImportError: {e}")
            raise ImportError("Библиотека openpyxl не установлена. Выполните: pip install openpyxl")

        wb = Workbook()
        ws = wb.active
        ws.title = "Зональные"

        # Стили
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        subheader_fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
        crim_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
        alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        green_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        sub_font = Font(bold=True, color="FFFFFF", size=11)
        crim_font = Font(bold=True, color="1E293B", size=11)
        bold_font = Font(bold=True, size=11)
        thin = Side(style="thin")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        center = Alignment(horizontal="center", vertical="center")
        left = Alignment(horizontal="left", vertical="center")

        row = 1

        # Заголовок формы
        ws.merge_cells(f"A{row}:F{row}")
        title_cell = ws.cell(row=row, column=1, value=f"ЗОНАЛЬНЫЕ КРИМИНАЛИСТЫ — {collection.template.name}")
        title_cell.fill = header_fill
        title_cell.font = Font(bold=True, color="FFFFFF", size=14)
        title_cell.alignment = center
        ws.row_dimensions[row].height = 28
        row += 1

        # Дата
        ws.merge_cells(f"A{row}:F{row}")
        date_cell = ws.cell(row=row, column=1,
                            value=f"Сформировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        date_cell.fill = subheader_fill
        date_cell.font = sub_font
        date_cell.alignment = center
        row += 2

        # Карта отделов
        dept_map = {d["id"]: d["name"] for d in INITIAL_DEPARTMENTS}
        items = collection.template.items
        use_dept_mode = collection.template.use_departments_mode

        # Шапка
        headers = ["№", "Криминалист / Пункт", "Значение", "Единица", "Сдано", "Комментарий"]
        for col_i, h in enumerate(headers, 1):
            c = ws.cell(row=row, column=col_i, value=h)
            c.fill = header_fill
            c.font = header_font
            c.alignment = center
            c.border = border
        ws.row_dimensions[row].height = 20
        row += 1

        # Данные по каждому активному криминалисту
        for crim in collection.criminalists:
            if not crim.is_active:
                continue  # Пропускаем неактивных
            # Строка криминалиста
            ws.merge_cells(f"A{row}:F{row}")
            name_val = f"👤 {crim.full_name}"
            if crim.note:
                name_val += f" ({crim.note})"
            crim_cell = ws.cell(row=row, column=1, value=name_val)
            crim_cell.fill = crim_fill
            crim_cell.font = crim_font
            crim_cell.alignment = left
            crim_cell.border = border
            ws.row_dimensions[row].height = 20
            row += 1

            # Зоны обслуживания
            zone_names = [dept_map.get(did, f"Отдел {did}") for did in crim.zone.department_ids]
            ws.merge_cells(f"A{row}:F{row}")
            zone_cell = ws.cell(row=row, column=1,
                                value=f"  Закреплено: {', '.join(zone_names) if zone_names else 'нет'}")
            zone_cell.font = Font(italic=True, color="64748B", size=10)
            zone_cell.alignment = left
            zone_cell.border = border
            row += 1

            # Пункты отчёта
            for item in items:
                rd = None
                for sub in collection.submissions:
                    if sub.criminalist_id == crim.id and sub.template_item_id == item.id:
                        rd = sub
                        break

                fill = alt_fill if items.index(item) % 2 == 0 else PatternFill()

                # Номер пункта
                c1 = ws.cell(row=row, column=1, value=f"{item.order + 1}.")
                c1.alignment = center
                c1.border = border
                c1.fill = fill

                # Название пункта
                c2 = ws.cell(row=row, column=2, value=f"  {item.name}")
                c2.alignment = left
                c2.border = border
                c2.fill = fill

                # 🔥 ИЗМЕНЕНИЕ: если режим по отделам — экспортируем детализацию
                if use_dept_mode and crim.zone.department_ids and item.item_type == ReportItemType.NUMERICAL:
                    # Сначала пишем общее значение
                    total_val = rd.value if rd and rd.value is not None else 0
                    c3 = ws.cell(row=row, column=3, value=total_val)
                    c3.alignment = center
                    c3.border = border
                    c3.fill = fill
                    c3.font = Font(bold=True, color="1D4ED8")

                    c4 = ws.cell(row=row, column=4, value=item.unit)
                    c4.alignment = center
                    c4.border = border
                    c4.fill = fill

                    ws.cell(row=row, column=5, value="").border = border
                    row += 1

                    # Теперь детализация по отделам
                    for dept_id in crim.zone.department_ids:
                        dept_name = dept_map.get(dept_id, f"Отдел {dept_id}")
                        dept_val = rd.department_values.get(dept_id) if rd else None

                        ws.merge_cells(f"A{row}:B{row}")
                        c_dept = ws.cell(row=row, column=1, value=f"    ↳ {dept_name}")
                        c_dept.font = Font(italic=True, size=10, color="64748B")
                        c_dept.alignment = left
                        c_dept.border = border
                        c_dept.fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

                        c_val = ws.cell(row=row, column=3, value=dept_val if dept_val is not None else "—")
                        c_val.alignment = center
                        c_val.border = border
                        c_val.fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

                        c_unit = ws.cell(row=row, column=4, value=item.unit if dept_val is not None else "")
                        c_unit.alignment = center
                        c_unit.border = border
                        c_unit.fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

                        ws.cell(row=row, column=5, value="").border = border
                        row += 1

                    # Не увеличиваем row здесь, так как уже увеличили в цикле
                    continue  # Пропускаем стандартное увеличение row

                elif use_dept_mode and crim.zone.department_ids and item.item_type == ReportItemType.DELIVERABLE:
                    # Для deliverable показываем сколько отделов сдано
                    if rd:
                        submitted_count = sum(1 for v in rd.department_submitted.values() if v)
                        total_depts = len(crim.zone.department_ids)
                        c3 = ws.cell(row=row, column=3, value="—")
                        c3.alignment = center
                        c3.border = border
                        c3.fill = fill

                        c4 = ws.cell(row=row, column=4, value="")
                        c4.alignment = center
                        c4.border = border
                        c4.fill = fill

                        c5 = ws.cell(row=row, column=5, value=f"{submitted_count}/{total_depts}")
                        c5.alignment = center
                        c5.border = border
                        c5.fill = green_fill if submitted_count == total_depts else fill
                        if submitted_count == total_depts:
                            c5.font = Font(bold=True, color="15803D")

                        row += 1

                        # Детализация по отделам
                        for dept_id in crim.zone.department_ids:
                            dept_name = dept_map.get(dept_id, f"Отдел {dept_id}")
                            is_submitted = rd.department_submitted.get(dept_id, False) if rd else False

                            ws.merge_cells(f"A{row}:B{row}")
                            c_dept = ws.cell(row=row, column=1, value=f"    ↳ {dept_name}")
                            c_dept.font = Font(italic=True, size=10, color="64748B")
                            c_dept.alignment = left
                            c_dept.border = border
                            c_dept.fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

                            c_status = ws.cell(row=row, column=5, value="✓" if is_submitted else "✗")
                            c_status.alignment = center
                            c_status.border = border
                            c_status.fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
                            if is_submitted:
                                c_status.font = Font(bold=True, color="15803D")

                            row += 1

                        continue

                # Стандартное отображение (не по отделам)
                if item.item_type == ReportItemType.NUMERICAL:
                    val = rd.value if rd else None
                    c3 = ws.cell(row=row, column=3, value=val if val is not None else "—")
                    c3.alignment = center
                    c3.border = border
                    c3.fill = fill
                    if val is not None:
                        c3.font = Font(bold=True, color="1D4ED8")

                    c4 = ws.cell(row=row, column=4, value=item.unit)
                    c4.alignment = center
                    c4.border = border
                    c4.fill = fill

                    ws.cell(row=row, column=5, value="").border = border
                else:
                    ws.cell(row=row, column=3, value="").border = border
                    ws.cell(row=row, column=4, value="").border = border
                    submitted = rd.is_submitted if rd else False
                    c5 = ws.cell(row=row, column=5, value="Да ✓" if submitted else "Нет")
                    c5.alignment = center
                    c5.border = border
                    c5.fill = green_fill if submitted else fill
                    if submitted:
                        c5.font = Font(bold=True, color="15803D")

                comment = rd.comment if rd else ""
                c6 = ws.cell(row=row, column=6, value=comment)
                c6.alignment = left
                c6.border = border
                c6.fill = fill

                row += 1

            row += 1  # Пустая строка между криминалистами

        # Сводка
        row += 1
        ws.merge_cells(f"A{row}:F{row}")
        
        # Информация о неактивных
        inactive_count = sum(1 for c in collection.criminalists if not c.is_active)
        inactive_note = f" ({inactive_count} неактивных пропущено)" if inactive_count else ""
        sum_title = ws.cell(row=row, column=1, value=f"ОБЩАЯ СВОДКА{inactive_note}")
        sum_title.fill = header_fill
        sum_title.font = header_font
        sum_title.alignment = center
        sum_title.border = border
        row += 1

        summary = get_summary(collection)
        for item_id, data in summary.items():
            item = data["item"]
            c1 = ws.cell(row=row, column=1, value=item.name)
            c1.font = bold_font
            c1.border = border

            if item.item_type == ReportItemType.NUMERICAL:
                c2 = ws.cell(row=row, column=2, value=f"Итого: {data['total_value']} {item.unit}")
                c2.border = border
                c3 = ws.cell(row=row, column=3,
                             value=f"Заполнили: {data['filled_count']} из {data['total_criminalists']}")
                c3.border = border
            else:
                c2 = ws.cell(row=row, column=2,
                             value=f"Сдали: {data['submitted_count']} из {data['total_criminalists']}")
                c2.border = border
                pct = round(data['submitted_count'] / max(data['total_criminalists'], 1) * 100)
                c3 = ws.cell(row=row, column=3, value=f"{pct}%")
                c3.border = border
                c3.font = Font(bold=True, color="15803D" if pct >= 80 else "D97706")

            row += 1

        # Ширина столбцов
        col_widths = [6, 45, 15, 12, 12, 30]
        for i, w in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

        # Настройки печати
        ws.page_setup.orientation = "landscape"
        ws.page_margins.left = 0.5
        ws.page_margins.right = 0.5

        wb.save(filepath)
        print(f"[ZONAL_EXCEL] ✓ Файл сохранён: {filepath}")
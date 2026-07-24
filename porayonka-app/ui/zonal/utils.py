# ui/zonal/utils.py
# Утилиты для вкладки "Зональные"
from typing import List
from core.zonal_models import ZonalCollection, Criminalist, ReportItemType
from core.zonal_data import get_report_data


def get_not_submitted_list(collection: ZonalCollection, dept_map: dict) -> str:
    """
    Сформировать текстовый список криминалистов с заполненностью < 100%.
    Для копирования в буфер обмена (Telegram/Messenger).
    """
    print("[UTILS] Formiruyu spisok ne sdavshih")
    
    active_criminalists = [c for c in collection.criminalists if c.is_active]
    
    if not active_criminalists:
        return "Net aktivnyh kriminalistov"
    
    if not collection.template.items:
        return "Net punktov v shablone"
    
    lines = ["=== NE SDALI FORMU ===", ""]
    
    for crim in active_criminalists:
        filled = 0
        total = len(collection.template.items)
        
        for item in collection.template.items:
            rd = None
            for sub in collection.submissions:
                if sub.criminalist_id == crim.id and sub.template_item_id == item.id:
                    rd = sub
                    break
            
            if item.item_type == ReportItemType.NUMERICAL:
                if rd and rd.value is not None:
                    filled += 1
            else:
                if rd and rd.is_submitted:
                    filled += 1
        
        percent = round(filled / total * 100) if total > 0 else 0
        
        if percent < 100:
            # Зоны компактно
            zone_names = [dept_map.get(did, f"#{did}") for did in crim.zone.department_ids[:3]]
            zones = ", ".join(zone_names)
            if len(crim.zone.department_ids) > 3:
                zones += f" +{len(crim.zone.department_ids) - 3}"
            
            lines.append(f"- {crim.full_name}")
            lines.append(f"  {zones}")
            lines.append(f"  {filled}/{total} ({percent}%)")
            lines.append("")
    
    if len(lines) == 2:
        return "Vse sdelali formu!"
    
    # Добавить итог
    not_submitted_count = sum(
        1 for c in active_criminalists
        if _get_crim_percent(c, collection) < 100
    )
    
    lines.append("---")
    lines.append(f"Ne sdelali: {not_submitted_count} iz {len(active_criminalists)}")
    
    result = "\n".join(lines)
    print(f"[UTILS] Spisok: {len(lines)} strok")
    return result


def _get_crim_percent(criminalist: Criminalist, collection: ZonalCollection) -> float:
    """Подсчёт процента заполненности для криминалиста"""
    if not collection.template.items:
        return 0
    
    filled = 0
    total = len(collection.template.items)
    
    for item in collection.template.items:
        rd = None
        for sub in collection.submissions:
            if sub.criminalist_id == criminalist.id and sub.template_item_id == item.id:
                rd = sub
                break
        
        if item.item_type == ReportItemType.NUMERICAL:
            if rd and rd.value is not None:
                filled += 1
        else:
            if rd and rd.is_submitted:
                filled += 1
    
    return (filled / total * 100) if total > 0 else 0

# ui/zonal/compact_summary.py
# Компактная панель сводки для нового UI
# Показывает: активных криминалистов, пункты сдано, общий прогресс
import flet as ft
from core.zonal_models import ZonalCollection, ReportItemType
from core.zonal_data import get_summary
from core.constants import COLORS


def create_compact_summary(collection: ZonalCollection) -> ft.Container:
    """
    Создать компактную панель сводки в одну строку.
    """
    print("[COMPACT_SUMMARY] Sozdau svodku")
    
    active_criminalists = [c for c in collection.criminalists if c.is_active]
    total_items = len(collection.template.items)
    
    # Подсчёт
    summary = get_summary(collection)
    
    total_filled = 0
    total_deliverable = 0
    
    for item_id, data in summary.items():
        item = data["item"]
        if item.item_type == ReportItemType.NUMERICAL:
            total_filled += data["filled_count"]
        else:
            total_deliverable += data["submitted_count"]
    
    # Прогресс
    if active_criminalists and total_items:
        avg_progress = sum(
            _calc_progress_for_crim(c, collection, summary)
            for c in active_criminalists
        ) / len(active_criminalists)
    else:
        avg_progress = 0
    
    # Цвета
    if avg_progress >= 100:
        progress_color = COLORS["received"]
    elif avg_progress > 0:
        progress_color = COLORS["btn_save"]
    else:
        progress_color = COLORS["text_muted"]
    
    # Элементы сводки
    summary_items = [
        _make_summary_item(
            icon=">>",
            value=str(len(active_criminalists)),
            label="Aktivnyh",
            color=COLORS["btn_save"],
        ),
        _make_summary_item(
            icon="#",
            value=str(total_items),
            label="Punktov",
            color=COLORS["text_secondary"],
        ),
        _make_summary_item(
            icon="+",
            value=f"{int(avg_progress)}%",
            label="Zapolneno",
            color=progress_color,
        ),
    ]
    
    # Прогресс-бар
    progress_bar = ft.ProgressBar(
        value=avg_progress / 100,
        bgcolor=COLORS["primary_light"],
        color=progress_color,
        height=6,
    )
    
    # Вся панель
    panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("=== SVODKA ===", size=12, weight=ft.FontWeight.BOLD, color=COLORS["text_secondary"]),
                        ft.Container(expand=True),
                        ft.Row(controls=summary_items, spacing=20),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=4),
                progress_bar,
            ],
            spacing=4,
        ),
        bgcolor=COLORS["card"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
    )
    
    print(f"[COMPACT_SUMMARY] Progress: {int(avg_progress)}%")
    return panel


def _make_summary_item(icon: str, value: str, label: str, color: str) -> ft.Container:
    """Элемент сводки: иконка + значение + подпись"""
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Text(icon, size=14, color=color),
                ft.Text(value, size=16, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(label, size=11, color=COLORS["text_muted"]),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _calc_progress_for_crim(criminalist, collection: ZonalCollection, summary: dict) -> float:
    """Подсчёт прогресса для одного криминалиста"""
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

# ui/zonal/criminalist_tile.py
# Квадратная плашка криминалиста для сетки
# [DARK THEME] Компактная плашка с индикатором заполненности
import flet as ft
from typing import Callable, Dict
from core.zonal_models import (
    ZonalCollection, Criminalist, ReportItemType,
    ReportData, ReportTemplateItem,
)
from core.zonal_data import get_report_data
from core.constants import COLORS, INITIAL_DEPARTMENTS


def create_criminalist_tile(
    page: ft.Page,
    criminalist: Criminalist,
    collection: ZonalCollection,
    on_click: Callable,          # Клик на плашку (открыть форму)
    on_toggle_active: Callable,  # Переключить активность
    on_edit: Callable,           # Редактировать
    dept_map: Dict[int, str],
) -> ft.Container:
    """
    Создать квадратную плашку криминалиста.
    """
    print(f"[TILE] Создаю плашку: {criminalist.full_name}")
    
    template = collection.template
    
    # ── Расчёт заполненности ──────────────────────────────────
    def calculate_progress() -> tuple:
        """Возвращает (filled_count, total_items, percent)"""
        if not template.items:
            return 0, 0, 0
        
        filled = 0
        for item in template.items:
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
        
        total = len(template.items)
        percent = round(filled / total * 100) if total > 0 else 0
        return filled, total, percent
    
    filled, total, percent = calculate_progress()
    
    # ── Цвета в зависимости от статуса ──────────────────────
    if not criminalist.is_active:
        tile_bg = COLORS["primary_light"]
        tile_border = "#475569"  # Серый для неактивных
        name_color = COLORS["text_muted"]
        progress_color = COLORS["text_muted"]
    elif percent >= 100:
        tile_bg = "#052e16"  # Тёмно-зелёный
        tile_border = COLORS["received"]
        name_color = COLORS["text"]
        progress_color = COLORS["received"]
    elif percent > 0:
        tile_bg = COLORS["card"]
        tile_border = COLORS["btn_save"]
        name_color = COLORS["text"]
        progress_color = COLORS["btn_save"]
    else:
        tile_bg = COLORS["card"]
        tile_border = COLORS["border"]
        name_color = COLORS["text"]
        progress_color = COLORS["text_muted"]
    
    # ── Зоны обслуживания (компактно) ────────────────────────
    zone_names = []
    for did in criminalist.zone.department_ids[:3]:
        short_name = dept_map.get(did, f"#{did}")
        # Сокращаем названия
        if len(short_name) > 15:
            short_name = short_name[:14] + "..."
        zone_names.append(short_name)
    
    zones_text = ", ".join(zone_names)
    if len(criminalist.zone.department_ids) > 3:
        zones_text += f" +{len(criminalist.zone.department_ids) - 3}"
    
    zones_tooltip = "\n".join([
        dept_map.get(did, f"#{did}") 
        for did in criminalist.zone.department_ids
    ]) if criminalist.zone.department_ids else "Нет закреплённых отделов"
    
    # ── Индикатор прогресса ──────────────────────────────────
    progress_bar = ft.ProgressBar(
        value=percent / 100 if total > 0 else 0,
        bgcolor=COLORS["primary_light"],
        color=progress_color,
        height=4,
    )
    
    # ── Статус активности ────────────────────────────────────
    active_chip_text = "Активен" if criminalist.is_active else "Отключён"
    active_chip_color = COLORS["received"] if criminalist.is_active else COLORS["text_muted"]
    
    active_chip = ft.Container(
        content=ft.Text(
            active_chip_text,
            size=10,
            color=COLORS["text_light"],
            weight=ft.FontWeight.W_500,
        ),
        bgcolor=active_chip_color,
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=6, vertical=2),
    )
    
    # ── Кнопки управления ───────────────────────────────────
    toggle_btn = ft.IconButton(
        icon=ft.icons.VISIBILITY if criminalist.is_active else ft.icons.VISIBILITY_OFF,
        icon_size=16,
        icon_color=active_chip_color,
        tooltip="Переключить участие" if criminalist.is_active else "Включить в выборку",
        on_click=lambda e: on_toggle_active(criminalist),
        style=ft.ButtonStyle(padding=ft.padding.all(2)),
    )
    
    edit_btn = ft.IconButton(
        icon=ft.icons.EDIT,
        icon_size=16,
        icon_color=COLORS["btn_save"],
        tooltip="Редактировать",
        on_click=lambda e: on_edit(criminalist),
        style=ft.ButtonStyle(padding=ft.padding.all(2)),
    )
    
    # ── Имя и примечание ────────────────────────────────────
    name_text = ft.Text(
        criminalist.full_name,
        size=13,
        weight=ft.FontWeight.W_600,
        color=name_color,
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    
    note_text = ft.Text(
        f"({criminalist.note})" if criminalist.note else "",
        size=11,
        color=COLORS["text_secondary"],
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
        visible=bool(criminalist.note),
    )
    
    # ── Прогресс-текст ─────────────────────────────────────
    progress_text = ft.Text(
        f"{filled}/{total}" if total > 0 else "Нет пунктов",
        size=20,
        weight=ft.FontWeight.BOLD,
        color=progress_color,
        text_align=ft.TextAlign.CENTER,
    )
    
    progress_label = ft.Text(
        f"{percent}%" if total > 0 else "",
        size=11,
        color=COLORS["text_secondary"],
        text_align=ft.TextAlign.CENTER,
    )
    
    # ── Вся плашка ─────────────────────────────────────────
    tile = ft.Container(
        content=ft.Column(
            controls=[
                # Верхняя строка: имя + кнопки
                ft.Row(
                    controls=[
                        name_text,
                        ft.Container(expand=True),
                        toggle_btn,
                        edit_btn,
                    ],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                # Примечание
                note_text,
                # Зоны
                ft.Container(
                    content=ft.Text(
                        zones_text,
                        size=10,
                        color=COLORS["text_secondary"],
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        tooltip=zones_tooltip,
                    ),
                    padding=ft.padding.only(top=2),
                ),
                # Разделитель
                ft.Divider(height=1, color=COLORS["border"]),
                # Прогресс
                progress_bar,
                ft.Container(height=4),
                # Числа
                ft.Row(
                    controls=[
                        ft.Column(
                            controls=[progress_text, progress_label],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=0,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                # Статус-чип
                ft.Container(
                    content=active_chip,
                    alignment=ft.alignment.center,
                    padding=ft.padding.only(top=4),
                ),
            ],
            spacing=4,
        ),
        bgcolor=tile_bg,
        border=ft.border.all(1.5, tile_border),
        border_radius=10,
        padding=ft.padding.all(12),
        width=220,
        height=180,
        on_click=lambda e: on_click(criminalist),
        animate=ft.animation.Animation(150, ft.AnimationCurve.EASE_IN_OUT),
    )
    
    def on_hover(e):
        if criminalist.is_active:
            tile.bgcolor = COLORS["card_hover"] if e.data == "true" else tile_bg
        else:
            tile.bgcolor = COLORS["primary_light"] if e.data == "true" else tile_bg
        try:
            tile.update()
        except Exception:
            pass
    
    tile.on_hover = on_hover
    
    print(f"[TILE] Плашка создана: {criminalist.full_name}, прогресс={percent}%")
    return tile


def create_tiles_grid(
    page: ft.Page,
    collection: ZonalCollection,
    on_click: Callable,
    on_toggle_active: Callable,
    on_edit: Callable,
    dept_map: Dict[int, str],
    show_inactive: bool = False,
) -> ft.Wrapped:
    """
    Создать сетку плашек.
    Возвращает ft.Wrapped для адаптивной сетки.
    """
    print(f"[TILES_GRID] Создаю сетку, show_inactive={show_inactive}")
    
    tiles = []
    for crim in collection.criminalists:
        if not crim.is_active and not show_inactive:
            continue
        
        tile = create_criminalist_tile(
            page=page,
            criminalist=crim,
            collection=collection,
            on_click=on_click,
            on_toggle_active=on_toggle_active,
            on_edit=on_edit,
            dept_map=dept_map,
        )
        tiles.append(tile)
    
    grid = ft.Wrapped(
        controls=tiles,
        spacing=12,
        run_spacing=12,
    )
    
    print(f"[TILES_GRID] Создано плашек: {len(tiles)}")
    return grid

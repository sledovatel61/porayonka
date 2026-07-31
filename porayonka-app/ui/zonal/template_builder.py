# ui/zonal/template_builder.py
# Конструктор шаблонов — панель настройки сбора данных
# [DARK THEME] Обновлено визуально + исправлено hint_text_color + сворачиваемость
import flet as ft
from typing import Callable, Optional, Dict
from core.zonal_models import (
    ZonalCollection, ReportTemplateItem, ReportItemType,
)
from core.constants import COLORS


def create_template_builder(
    page: ft.Page,
    collection: ZonalCollection,
    on_template_changed: Callable,
    on_save: Callable,        # on_save(name: str)
    on_load: Callable,
    on_clear: Callable,
    on_reset_data: Callable,  # on_reset_data() — сброс данных без потери шаблона
    on_departments_mode_changed: Callable,  # on_departments_mode_changed(bool)
    template_builder_ref: Optional[Dict] = None,
) -> ft.Container:
    """
    Создать панель конструктора шаблонов.
    По умолчанию панель свернута.
    """
    print("[TEMPLATE_BUILDER] Creating template builder")

    is_expanded = False
    if template_builder_ref is not None:
        is_expanded = template_builder_ref.get("is_expanded", False)

    # ── Поле названия формы ──────────────────────────────────────
    name_field = ft.TextField(
        value=collection.template.name,
        hint_text="Название формы (например, Апрель 2026)",
        border_radius=8,
        border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"],  # ТЁМНЫЙ ФОН
        color=COLORS["text"],    # ТЁМНЫЙ ТЕКСТ
        height=44,
        text_size=14,
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
    )

    # ── Список пунктов ───────────────────────────────────────────
    items_column = ft.Column(spacing=8, tight=True)

    def rebuild_items_list():
        """Перестроить список пунктов шаблона"""
        items_column.controls.clear()
        for idx, item in enumerate(collection.template.items):
            items_column.controls.append(
                _make_item_row(item, idx)
            )
        try:
            items_column.update()
        except Exception:
            pass

    def _make_item_row(item: ReportTemplateItem, idx: int) -> ft.Container:
        """Создать строку одного пункта шаблона"""

        # Поле названия пункта
        item_name_field = ft.TextField(
            value=item.name,
            hint_text="Название пункта",
            border_radius=6,
            border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"],  # ТЁМНЫЙ ФОН
            color=COLORS["text"],
            height=38,
            text_size=13,
            expand=True,
            hint_style=ft.TextStyle(color=COLORS["text_muted"]),
            on_change=lambda e, i=item: _on_item_name_change(e, i),
        )

        # Выбор типа
        type_dropdown = ft.Dropdown(
            value=item.item_type.value,
            options=[
                ft.dropdown.Option("numerical", "числовой"),
                ft.dropdown.Option("deliverable", "да/нет"),
            ],
            border_radius=6,
            border_color=COLORS["border"],
            bgcolor=COLORS["card"],  # ТЁМНЫЙ ФОН
            color=COLORS["text"],
            height=38,
            width=140,
            text_size=13,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=8),
            on_change=lambda e, i=item: _on_item_type_change(e, i),
        )

        # Поле единицы измерения
        unit_field = ft.TextField(
            value=item.unit,
            hint_text="ед.",
            border_radius=6,
            border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor=COLORS["card"],  # ТЁМНЫЙ ФОН
            color=COLORS["text"],
            height=38,
            text_size=13,
            width=60,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=8),
            visible=(item.item_type == ReportItemType.NUMERICAL),
            hint_style=ft.TextStyle(color=COLORS["text_muted"]),
            on_change=lambda e, i=item: _on_item_unit_change(e, i),
        )

        # Кнопка удаления
        delete_btn = ft.IconButton(
            icon=ft.icons.CLOSE,
            icon_size=16,
            icon_color="#f87171",  # ТЁМНЫЙ КРАСНЫЙ
            tooltip="Удалить пункт",
            on_click=lambda e, i=item: _delete_item(i),
            style=ft.ButtonStyle(padding=ft.padding.all(4)),
        )

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(f"{idx + 1}.", size=13, color=COLORS["text_secondary"], width=24),
                    item_name_field,
                    type_dropdown,
                    unit_field,
                    delete_btn,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=COLORS["primary_light"],  # ТЁМНЫЙ ФОН СТРОКИ
            border=ft.border.all(1, COLORS["border"]),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
        )

    def _on_item_name_change(e, item: ReportTemplateItem):
        item.name = e.control.value
        on_template_changed()

    def _on_item_type_change(e, item: ReportTemplateItem):
        item.item_type = ReportItemType(e.control.value)
        on_template_changed()
        rebuild_items_list()

    def _on_item_unit_change(e, item: ReportTemplateItem):
        item.unit = e.control.value
        on_template_changed()

    def _delete_item(item: ReportTemplateItem):
        collection.template.items = [i for i in collection.template.items if i.id != item.id]
        # Пересчитать порядок
        for idx, i in enumerate(collection.template.items):
            i.order = idx
        on_template_changed()
        rebuild_items_list()

    def _add_item(e=None):
        """Добавить новый пункт шаблона"""
        new_item = ReportTemplateItem.create(
            name="Новый пункт",
            item_type=ReportItemType.NUMERICAL,
            unit="шт.",
            order=len(collection.template.items),
        )
        collection.template.items.append(new_item)
        on_template_changed()
        rebuild_items_list()

    # Кнопка добавления пункта
    add_btn = ft.TextButton(
        text="Добавить пункт",
        icon=ft.icons.ADD,
        style=ft.ButtonStyle(
            color=COLORS["btn_save"],
        ),
        on_click=_add_item,
    )

    # ── Переключатель режима "По отделам" ────────────────────────
    dept_mode_checkbox = ft.Checkbox(
        label="Работать по отделам (детализация по районам)",
        value=collection.template.use_departments_mode,
        active_color=COLORS["btn_save"],
        label_style=ft.TextStyle(
            size=13,
            color=COLORS["text"],
            weight=ft.FontWeight.W_500,
        ),
        on_change=lambda e: _on_dept_mode_changed(e),
    )

    def _on_dept_mode_changed(e):
        collection.template.use_departments_mode = e.control.value
        on_departments_mode_changed(e.control.value)

    # ── Кнопки управления шаблоном ──────────────────────────────
    def _on_save_click(e):
        name = name_field.value.strip()
        if not name:
            name_field.error_text = "Введите название"
            name_field.update()
            return
        name_field.error_text = None
        name_field.update()
        collection.template.name = name
        on_save(name)

    btn_save = ft.ElevatedButton(
        text="Сохранить форму",
        icon=ft.icons.SAVE,
        bgcolor=COLORS["btn_save"],
        color="white",
        height=38,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=14),
        ),
        on_click=_on_save_click,
    )

    btn_load = ft.OutlinedButton(
        text="Загрузить форму",
        icon=ft.icons.FOLDER_OPEN,
        height=38,
        style=ft.ButtonStyle(
            color=COLORS["text"],
            side=ft.BorderSide(1, COLORS["border"]),
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=14),
        ),
        on_click=lambda e: on_load(),
    )

    btn_clear = ft.OutlinedButton(
        text="Очистить",
        icon=ft.icons.DELETE_OUTLINE,
        height=38,
        style=ft.ButtonStyle(
            color="#f87171",  # ТЁМНЫЙ КРАСНЫЙ
            side=ft.BorderSide(1, "#f87171"),
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=14),
        ),
        on_click=lambda e: on_clear(),
    )

    # Кнопка «Сброс данных» удалена из конструктора шаблона:
    # осталась единственная точка сброса — «Очистить все данные»
    # в тулбаре вкладки «Зональные» (см. AGENTS.md 22).
    # Колбэк on_reset_data всё ещё принимается сигнатурой на случай
    # программного вызова, но UI-кнопки больше нет.

    # Инициальное построение списка
    rebuild_items_list()

    # Адаптивная высота списка пунктов — под высоту окна приложения:
    # в полноэкранном режиме список выше, в оконном — компактнее
    try:
        _win_h = page.window.height or 800
    except Exception:
        _win_h = 800
    items_list_height = max(180, min(560, int(_win_h * 0.42)))

    # ── Сборка панели (без сворачивания, сразу видно) ────────────
    panel = ft.Container(
        content=ft.Column(
            controls=[
                # Название формы
                ft.Text("Название формы:", size=13, weight=ft.FontWeight.W_600,
                        color=COLORS["text"]),
                name_field,
                ft.Container(height=12),
                # Пункты шаблона
                ft.Text("Пункты для сбора:", size=13, weight=ft.FontWeight.W_600,
                        color=COLORS["text"]),
                ft.Container(height=4),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            items_column,
                            ft.Container(height=4),
                            add_btn,
                        ],
                        spacing=4,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    bgcolor=COLORS["primary_light"],
                    border=ft.border.all(1, COLORS["border"]),
                    border_radius=8,
                    padding=ft.padding.all(12),
                    height=items_list_height,
                ),
                ft.Container(height=12),
                # Кнопки
                ft.Row(
                    controls=[btn_save, btn_load, btn_clear],
                    spacing=10,
                    wrap=True,
                ),
                ft.Container(height=8),
                # Переключатель режима
                dept_mode_checkbox,
            ],
            spacing=6,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=ft.padding.all(16),
        bgcolor=COLORS["card"],
        border_radius=10,
        expand=True,
    )

    print("[TEMPLATE_BUILDER] Template builder created")
    return panel

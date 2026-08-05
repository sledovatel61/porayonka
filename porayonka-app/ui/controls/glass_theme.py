# ui/controls/glass_theme.py
# Локальная палитра и хелперы скина «Glass Dark» для вкладки «Контроли».
# Источник истины: design/mockups_portable/photo/README.md, раздел «01 · Glass Dark».
# Правила движка (AGENTS.md §26, §22):
#   - «стекло» — только полупрозрачный bgcolor + границы, БЕЗ теней/gradient/backdrop-filter;
#   - у Container с border_radius рамка равномерная по толщине (все стороны 1 px),
#     верхняя кромка светлее по ЦВЕТУ, не по толщине;
#   - внутри скролл-колонки никаких animate/shadow/gradient/elevation-состояний.
#
# ВАЖНО (Flet 0.23.2 / Flutter): 8-значный hex читается как #AARRGGBB
# (альфа ПЕРВАЯ). Здесь ВСЕ 8-значные цвета записаны в ARGB:
#   #RRGGBBAA → #AARRGGBB  (например "#16213dcc" → "#cc16213d",
#   "#ffffff1a" → "#1affffff"). Динамическая заливка: f"#22{color[1:]}".
import flet as ft

from core.controls_models import (
    OVERDUE, TODAY, SOON, IN_PROGRESS, DONE, COMPLETED, NO_DATE,
)

# ────────────────────────────────────────────────────────────────
# Палитра Glass Dark (все 8-значные — ARGB, alpha first!)
# ────────────────────────────────────────────────────────────────
GLASS = {
    "bg":            "#0a1024",   # фон вкладки
    "surface":       "#cc16213d", # стеклянная поверхность (alpha CC ≈ 80%)
    "surface_solid": "#16213d",   # плотная поверхность (диалоги)
    "field":         "#0d1830",   # вдавленный тон полей
    "field_alt":     "#101c38",   # чуть светлее для списков-обёрток
    "row_alt":       "#6616213d", # чередование строк таблицы (alpha 66 ≈ 40%)
    "border":        "#1affffff", # белый 10% (alpha 1a)
    "border_soft":   "#0fffffff", # белый ~6%
    "border_alt":    "#14ffffff", # белый ~8%
    "edge":          "#2effffff", # светлая кромка сверху панелей (alpha 2e)
    "hover":         "#08ffffff", # hover строки таблицы
    "hover_strong":  "#12ffffff", # hover кнопок/ячеек
    "text":          "#f2f5ff",   # основной текст
    "text_2":        "#93a3c7",   # вторичный текст
    "text_3":        "#5d6b8f",   # приглушённый текст / hint
    "accent":        "#4f8cff",   # акцент
    "export_green":  "#2fd08b",   # зелёная кнопка экспорта
    "export_text":   "#04121f",   # тёмный текст на зелёном
    "danger":        "#ff5c6e",   # просрочено / опасное действие
    "overlay":       "#cc04070f", # затемнение за карточкой (alpha cc)
    "divider":       "#1affffff", # разделитель строк таблицы
}

# Статусы в палитре скина (переопределяет STATUS_COLORS из моделей)
GLASS_STATUS = {
    OVERDUE:      "#ff5c6e",
    TODAY:        "#ffd166",
    SOON:         "#ff9f43",
    IN_PROGRESS:  "#2fd08b",
    DONE:         "#8a94ad",
    COMPLETED:    "#4f8cff",
    NO_DATE:      "#5d6b8f",
}


def _glass_border() -> ft.Border:
    """Рамка панели: все стороны 1 px, верхняя кромка светлее по цвету."""
    return ft.border.only(
        top=ft.BorderSide(1, GLASS["edge"]),
        left=ft.BorderSide(1, GLASS["border"]),
        right=ft.BorderSide(1, GLASS["border"]),
        bottom=ft.BorderSide(1, GLASS["border"]),
    )


def glass_panel(
    content=None,
    width=None,
    height=None,
    radius: int = 12,
    padding=None,
    bgcolor: str = GLASS["surface"],
    border=None,
    alignment=None,
    on_click=None,
    clip_behavior=None,
) -> ft.Container:
    """Стеклянная панель скина: полупрозрачный фон + кромка сверху.

    Без теней и градиентов — «стекло» в Flet 0.23.2 делается только так.
    clip_behavior — обрезать контент по скруглению (для полотна таблицы).
    """
    return ft.Container(
        content=content,
        width=width,
        height=height,
        bgcolor=bgcolor,
        border=border if border is not None else _glass_border(),
        border_radius=radius,
        padding=padding,
        alignment=alignment,
        on_click=on_click,
        clip_behavior=clip_behavior,
    )


def status_pill(status_key: str, label: str, icon=None) -> ft.Container:
    """Пилюля статуса: заливка <color>22 + рамка 1 px <color> + иконка.

    Заливка в ARGB: f"#22{color[1:]}" = alpha 22 + RGB цвета статуса.
    """
    color = GLASS_STATUS.get(status_key, GLASS["text_3"])
    return ft.Container(
        content=ft.Row(controls=[
            ft.Icon(icon, size=12, color=color),
            ft.Text(label, size=11, color=color, weight=ft.FontWeight.BOLD, no_wrap=True),
        ], spacing=3, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=f"#22{color[1:]}",
        border=ft.border.all(1, color),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        alignment=ft.alignment.center,
    )


def glass_button(
    text: str,
    icon=None,
    on_click=None,
    height: int = 40,
    width=None,
    bgcolor: str = GLASS["surface"],
    color: str = GLASS["text"],
    border_color: str = GLASS["border"],
    radius: int = 10,
) -> ft.ElevatedButton:
    """Стеклянная (ghost-стекло) кнопка."""
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        bgcolor=bgcolor,
        color=color,
        height=height,
        width=width,
        on_click=on_click,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=radius),
            side=ft.BorderSide(1, border_color),
            padding=ft.padding.symmetric(horizontal=14),
        ),
    )


def ghost_button(
    text: str,
    on_click=None,
    color: str = GLASS["text"],
    size: int = 12,
) -> ft.TextButton:
    """Прозрачная текстовая кнопка (ghost)."""
    return ft.TextButton(
        content=ft.Text(text, size=size, color=color,
                        weight=ft.FontWeight.W_500, no_wrap=True),
        on_click=on_click,
        style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=8)),
    )


def chip(
    key: str,
    label: str,
    count: int,
    on_click,
    selected: bool,
    height: int = 28,
) -> ft.Container:
    """Чип-счётчик: цветная точка 8 px + подпись + число bold.

    Активный чип — заливка <color>22 + рамка 1 px <color> (пилюля radius height/2).
    «Все» красится акцентом. Заливка в ARGB: f"#22{color[1:]}".
    """
    color = GLASS["accent"] if key == "all" else GLASS_STATUS.get(key, GLASS["text_3"])
    return ft.Container(
        content=ft.Row(controls=[
            ft.Container(width=8, height=8, border_radius=4, bgcolor=color),
            ft.Text(label, size=12, color=GLASS["text"] if selected else GLASS["text_2"],
                    weight=ft.FontWeight.W_600, no_wrap=True),
            ft.Text(str(count), size=12, color=GLASS["text"],
                    weight=ft.FontWeight.BOLD, no_wrap=True),
        ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=height,
        padding=ft.padding.symmetric(horizontal=12),
        border_radius=height // 2,
        alignment=ft.alignment.center,
        bgcolor=f"#22{color[1:]}" if selected else "transparent",
        border=ft.border.all(1, color) if selected else ft.border.all(1, "transparent"),
        ink=True,
        on_click=on_click,
    )

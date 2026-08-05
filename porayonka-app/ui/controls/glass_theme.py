# ui/controls/glass_theme.py
# Палитра Glass Dark — ИСПРАВЛЕНО: Flet 0.23.2 использует #AARRGGBB (альфа ПЕРВАЯ)
import flet as ft

def with_alpha(color_hex: str, alpha_hex: str) -> str:
    c = (color_hex or "").strip()
    if not c.startswith("#"):
        return c
    if len(c) == 7:
        return f"#{alpha_hex}{c[1:]}"
    if len(c) == 4:
        return f"#{alpha_hex}{c[1]*2}{c[2]*2}{c[3]*2}"
    return c

GLASS = {
    "bg": "#0a1024",                 # фон вкладки темно-синий (из README мокапа)
    "surface": "#cc141e33",          # панели #141e33 с alpha cc
    "surface_solid": "#141e33",
    "surface_alt": "#0d1830",
    "surface_alt2": "#101c36",
    "card": "#1e2a44",               # плашка строки #1e2a44 — серо-синяя, на 2 ступени светлее фона
    "card_glass": "#cc1e2a44",       # карточка контроля стекло #cc1e2a44
    "border": "#0dffffff",           # убрать или #0dffffff — отделение цветом
    "border_light": "#2effffff",
    "border_divider": "#1affffff",
    "text": "#f2f5ff",
    "text_secondary": "#93a3c7",
    "text_muted": "#5d6b8f",
    "accent": "#4f8cff",
    "accent_hover": "#6aa0ff",
    "green": "#2fd08b",
    "green_dark_text": "#04121f",
    "overdue": "#ff5c6e",
    "today": "#ffd166",
    "soon": "#ff9f43",
    "in_progress": "#2fd08b",
    "done": "#8a94ad",
    "completed": "#4f8cff",
    "overlay_bg": "#cc04070f",
    "hover": "#28324e",              # единый hover #28324e на всех строках
    "hover_strong": "#12ffffff",
    "row_alt": "#1e2a44",
}

STATUS_COLORS = {
    "overdue": GLASS["overdue"],
    "today": GLASS["today"],
    "soon": GLASS["soon"],
    "in_progress": GLASS["in_progress"],
    "done": GLASS["done"],
    "completed": GLASS["completed"],
    "none": GLASS["text_muted"],
}

def glass_panel(
    content,
    width=None,
    height=None,
    radius=12,
    padding=ft.padding.all(12),
    bgcolor=GLASS["surface"],
    border_color=GLASS["border"],
    top_border_color=GLASS["border_light"],
):
    border = ft.border.only(
        top=ft.BorderSide(1, top_border_color),
        left=ft.BorderSide(1, border_color),
        right=ft.BorderSide(1, border_color),
        bottom=ft.BorderSide(1, border_color),
    )
    return ft.Container(
        content=content,
        width=width,
        height=height,
        bgcolor=bgcolor,
        border=border,
        border_radius=radius,
        padding=padding,
    )

def glass_field_border():
    return ft.border.all(1, GLASS["border"])

def status_dot(color: str) -> ft.Container:
    return ft.Container(width=8, height=8, border_radius=4, bgcolor=color)

def status_pill(label: str, color: str, icon=None, selected=False) -> ft.Container:
    bg = with_alpha(color, "22") if not selected else with_alpha(color, "33")
    border = ft.border.all(1, color)
    txt_color = color
    icon_ctrl = ft.Icon(icon, size=12, color=color) if icon else None
    row_controls = []
    if icon_ctrl:
        row_controls.append(icon_ctrl)
    row_controls.append(ft.Text(label, size=11, weight=ft.FontWeight.W_600, color=txt_color, no_wrap=True))
    return ft.Container(
        content=ft.Row(controls=row_controls, spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=26,
        padding=ft.padding.symmetric(horizontal=10),
        border_radius=13,
        bgcolor=bg,
        border=border,
        alignment=ft.alignment.center,
    )

def chip_counter(label: str, count: int, color: str, icon=None, selected=False, on_click=None) -> ft.Container:
    bg = with_alpha(color, "22") if not selected else with_alpha(color, "33")
    border_col = color
    if label.lower() == "все":
        bg = with_alpha(GLASS['accent'], "22") if not selected else with_alpha(GLASS['accent'], "33")
        border_col = GLASS["accent"]
    else:
        if not selected:
            border_col = with_alpha(color, "44")
    border = ft.border.all(1, border_col)
    dot = status_dot(color if label.lower() != "все" else GLASS["accent"])
    txt = ft.Row(controls=[
        dot,
        ft.Text(label, size=12, color=GLASS["text_secondary"] if not selected else GLASS["text"], no_wrap=True),
        ft.Text(str(count), size=12, weight=ft.FontWeight.W_700, color=GLASS["text"], no_wrap=True),
    ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)
    cont = ft.Container(
        content=txt,
        height=30,
        padding=ft.padding.symmetric(horizontal=12),
        border_radius=15,
        bgcolor=bg,
        border=border,
        alignment=ft.alignment.center,
        ink=True,
        on_click=on_click,
    )
    return cont

def glass_button(text: str, icon=None, bgcolor=GLASS["accent"], color="#ffffff", height=40, radius=10, on_click=None, tooltip=None) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        bgcolor=bgcolor,
        color=color,
        height=height,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=radius),
            padding=ft.padding.symmetric(horizontal=16),
        ),
        on_click=on_click,
        tooltip=tooltip,
    )

def ghost_button(text: str, icon=None, height=40, radius=10, on_click=None, tooltip=None) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        bgcolor=GLASS["surface"],
        color=GLASS["text"],
        height=height,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=radius),
            side=ft.BorderSide(1, GLASS["border"]),
            padding=ft.padding.symmetric(horizontal=14),
        ),
        on_click=on_click,
        tooltip=tooltip,
    )

def green_button(text: str, icon=None, height=40, radius=10, on_click=None) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        bgcolor=GLASS["green"],
        color=GLASS["green_dark_text"],
        height=height,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=radius),
            padding=ft.padding.symmetric(horizontal=16),
        ),
        on_click=on_click,
    )

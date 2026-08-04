# ui/controls/glass_theme.py
# Локальная палитра Glass Dark для вкладки «Контроли»
# + хелперы: glass_panel, status_pill, glass_button, ghost_button, chip
import flet as ft

GLASS = {
    "bg": "#0a1024",
    "surface": "#16213dcc",
    "surface_solid": "#16213d",
    "surface_alt": "#0d1830",
    "surface_alt_2": "#16213d66",
    "border": "#ffffff1a",
    "border_top": "#ffffff2e",
    "text": "#f2f5ff",
    "text_secondary": "#93a3c7",
    "text_muted": "#5d6b8f",
    "accent": "#4f8cff",
    "accent_hover": "#6ea0ff",
    "overdue": "#ff5c6e",
    "today": "#ffd166",
    "soon": "#ff9f43",
    "in_work": "#2fd08b",
    "done": "#8a94ad",
    "completed": "#4f8cff",
    "export_green": "#2fd08b",
    "export_green_text": "#04121f",
    "hover": "#ffffff08",
    "hover_light": "#ffffff12",
    "overlay_dim": "#04070fcc",
    "danger": "#ff5c6e",
    "card": "#16213d",
    "primary_light": "#16213d",  # for compat
}

# Mapping to control model statuses
STATUS_COLORS_GLASS = {
    "overdue": GLASS["overdue"],
    "today": GLASS["today"],
    "soon": GLASS["soon"],
    "in_progress": GLASS["in_work"],
    "done": GLASS["done"],
    "completed": GLASS["completed"],
    "none": GLASS["text_muted"],
}

def glass_border(with_top=True):
    top_c = GLASS["border_top"] if with_top else GLASS["border"]
    return ft.border.only(
        top=ft.BorderSide(1, top_c),
        left=ft.BorderSide(1, GLASS["border"]),
        right=ft.BorderSide(1, GLASS["border"]),
        bottom=ft.BorderSide(1, GLASS["border"]),
    )

def glass_panel(
    content,
    width=None,
    height=None,
    radius=12,
    padding=ft.padding.all(8),
    bgcolor=None,
    with_top=True,
    expand=False,
    alignment=None,
    border=None,
):
    return ft.Container(
        content=content,
        width=width,
        height=height,
        bgcolor=bgcolor or GLASS["surface"],
        border=border or glass_border(with_top),
        border_radius=radius,
        padding=padding,
        expand=expand,
        alignment=alignment,
    )

def status_pill(status_code: str, label: str, icon=None):
    color = STATUS_COLORS_GLASS.get(status_code, GLASS["text_muted"])
    # заливка <color>22  (22 ~ 13% alpha)
    bg = f"{color}22" if len(color) == 7 else color
    ic = []
    if icon:
        ic.append(ft.Icon(icon, size=12, color=color))
    ic.append(ft.Text(label, size=11, weight=ft.FontWeight.W_600, color=color, no_wrap=True))
    return ft.Container(
        content=ft.Row(controls=ic, spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
        height=26,
        padding=ft.padding.symmetric(horizontal=8),
        bgcolor=bg,
        border=ft.border.all(1, color),
        border_radius=12,
        alignment=ft.alignment.center,
    )

def _base_button(text, icon=None, bgcolor=None, text_color=None, border=None, height=40, width=None, on_click=None, tooltip=None):
    controls = []
    if icon:
        controls.append(ft.Icon(icon, size=16, color=text_color or GLASS["text"]))
    if text:
        controls.append(ft.Text(text, size=13, weight=ft.FontWeight.W_600, color=text_color or GLASS["text"], no_wrap=True))
    row = ft.Row(controls=controls, spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER)
    return ft.Container(
        content=row,
        height=height,
        width=width,
        bgcolor=bgcolor or GLASS["surface"],
        border=border or ft.border.all(1, GLASS["border"]),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=14),
        alignment=ft.alignment.center,
        ink=True,
        on_click=on_click,
        tooltip=tooltip,
    )

def glass_button(text, icon=None, on_click=None, height=40, width=None, accent=False, green=False, tooltip=None):
    if accent:
        return _base_button(
            text=text, icon=icon,
            bgcolor=GLASS["accent"],
            text_color="white",
            border=ft.border.all(1, GLASS["accent"]),
            height=height, width=width, on_click=on_click, tooltip=tooltip
        )
    if green:
        return _base_button(
            text=text, icon=icon,
            bgcolor=GLASS["export_green"],
            text_color=GLASS["export_green_text"],
            border=ft.border.all(1, GLASS["export_green"]),
            height=height, width=width, on_click=on_click, tooltip=tooltip
        )
    # ghost glass
    return _base_button(
        text=text, icon=icon,
        bgcolor=GLASS["surface"],
        text_color=GLASS["text"],
        border=ft.border.all(1, GLASS["border"]),
        height=height, width=width, on_click=on_click, tooltip=tooltip
    )

def ghost_button(text, icon=None, on_click=None, height=40, width=None, tooltip=None):
    return _base_button(
        text=text, icon=icon,
        bgcolor=GLASS["surface"],
        text_color=GLASS["text"],
        border=ft.border.all(1, GLASS["border"]),
        height=height, width=width, on_click=on_click, tooltip=tooltip
    )

def chip(label, count: int = 0, color: str = None, active: bool = False, on_click=None, icon=None):
    dot_color = color or GLASS["text_muted"]
    # active => fill <color>22 + border 1px <color>
    if active:
        bg = f"{dot_color}22"
        br = ft.border.all(1, dot_color)
    else:
        bg = "transparent"
        br = ft.border.all(1, GLASS["border"])
    # dot
    dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=dot_color)
    txt = ft.Text(label, size=12, color=GLASS["text_secondary"] if not active else GLASS["text"], no_wrap=True)
    cnt = ft.Text(str(count), size=12, weight=ft.FontWeight.BOLD, color=GLASS["text"] if not active else dot_color, no_wrap=True)
    row = ft.Row(controls=[dot, txt, cnt], spacing=5, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)
    return ft.Container(
        content=row,
        height=30,
        padding=ft.padding.symmetric(horizontal=10),
        bgcolor=bg,
        border=br,
        border_radius=15,
        ink=True,
        on_click=on_click,
    )

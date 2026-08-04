# ui/controls/glass_theme.py
# Glass Dark theme palette and reusable helpers for the Controls tab.
# Source of truth: design/mockups_portable/photo/README.md §01 Glass Dark

import flet as ft

# ── Palette ──────────────────────────────────────────────────────
GLASS = {
    "bg_tab":        "#0a1024",
    "surface":       "#16213dcc",
    "surface_solid": "#16213d",
    "border":        "#ffffff1a",
    "top_edge":      "#ffffff2e",
    "text":          "#f2f5ff",
    "text_secondary": "#93a3c7",
    "text_muted":    "#5d6b8f",
    "accent":        "#4f8cff",
    "overdue":       "#ff5c6e",
    "today":         "#ffd166",
    "soon":          "#ff9f43",
    "in_progress":   "#2fd08b",
    "done":          "#8a94ad",
    "completed":     "#4f8cff",
    "no_date":       "#5d6b8f",

    # Inset fields / inputs
    "inset_bg":      "#0d1830",
    "inset_border":  "#ffffff1a",

    # Buttons
    "btn_accent":    "#4f8cff",
    "btn_accent_text": "#ffffff",
    "btn_green":     "#2fd08b",
    "btn_green_text":"#04121f",

    # Overlay dimmer
    "overlay_dim":   "#04070fcc",
}

_RADIUS = 10
_RADIUS_PANEL = 12
_RADIUS_CARD = 14


# ── Status mapping ───────────────────────────────────────────────
def status_color(status_key: str) -> str:
    """Return GLASS hex for a deadline status key."""
    mapping = {
        "overdue":    GLASS["overdue"],
        "today":      GLASS["today"],
        "soon":       GLASS["soon"],
        "in_progress": GLASS["in_progress"],
        "done":       GLASS["done"],
        "completed":  GLASS["completed"],
        "no_date":    GLASS["no_date"],
    }
    return mapping.get(status_key, GLASS["text_muted"])


# ── Glass panel ──────────────────────────────────────────────────
def glass_panel(
    content: ft.Control,
    *,
    padding: float = 12,
    radius: int = _RADIUS_PANEL,
    bgcolor: str = GLASS["surface"],
    top_edge: str = GLASS["top_edge"],
    border_color: str = GLASS["border"],
    height: int = None,
    width: int = None,
    clip_behavior=None,
) -> ft.Container:
    """A semi-transparent glass panel with top highlight edge."""
    return ft.Container(
        content=content,
        bgcolor=bgcolor,
        border=ft.border.only(
            top=ft.BorderSide(1, top_edge),
            left=ft.BorderSide(1, border_color),
            right=ft.BorderSide(1, border_color),
            bottom=ft.BorderSide(1, border_color),
        ),
        border_radius=radius,
        padding=ft.padding.all(padding),
        height=height,
        width=width,
        clip_behavior=clip_behavior,
    )


# ── Status pill ──────────────────────────────────────────────────
def status_pill(
    label: str,
    color: str,
    *,
    icon=None,
    font_size: int = 11,
) -> ft.Container:
    """A small pill badge for status (e.g. in table rows)."""
    controls = []
    if icon:
        controls.append(ft.Icon(icon, size=12, color=color))
    controls.append(
        ft.Text(label, size=font_size, color=color,
                weight=ft.FontWeight.W_600, no_wrap=True)
    )
    return ft.Container(
        content=ft.Row(controls=controls, spacing=3, tight=True,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=24,
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=8),
        alignment=ft.alignment.center,
        bgcolor=f"{color}22",
        border=ft.border.all(1, color),
    )


# ── Accent button ────────────────────────────────────────────────
def glass_button(
    text: str,
    on_click=None,
    *,
    icon=None,
    bgcolor: str = GLASS["btn_accent"],
    fgcolor: str = GLASS["btn_accent_text"],
    height: int = 40,
    icon_color: str = None,
) -> ft.ElevatedButton:
    """Primary accent button (e.g. 'Добавить контроль')."""
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        bgcolor=bgcolor,
        color=fgcolor,
        height=height,
        icon_color=icon_color or fgcolor,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=_RADIUS),
            padding=ft.padding.symmetric(horizontal=16),
        ),
        on_click=on_click,
    )


# ── Ghost / glass button ────────────────────────────────────────
def ghost_button(
    text: str,
    on_click=None,
    *,
    icon=None,
    height: int = 40,
    compact: bool = False,
) -> ft.ElevatedButton:
    """Semi-transparent ghost button (secondary actions)."""
    pad = ft.padding.symmetric(horizontal=10 if compact else 14)
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        bgcolor=GLASS["surface"],
        color=GLASS["text"],
        height=height,
        icon_color=GLASS["text"],
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=_RADIUS),
            padding=pad,
            side=ft.BorderSide(1, GLASS["border"]),
        ),
        on_click=on_click,
    )


# ── Chip / counter pill ─────────────────────────────────────────
def chip(
    label: str,
    count: int,
    color: str,
    *,
    active: bool = False,
    on_click=None,
    icon=None,
) -> ft.Container:
    """Clickable chip counter (e.g. 'Все 134', 'Просрочено 2')."""
    dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=color)
    badge = ft.Text(str(count), size=11, color=GLASS["text"],
                    weight=ft.FontWeight.W_700, no_wrap=True)
    controls = [dot, ft.Text(label, size=12, color=GLASS["text_secondary"],
                              weight=ft.FontWeight.W_500, no_wrap=True), badge]
    if icon:
        controls.insert(0, ft.Icon(icon, size=13, color=color))

    pill_color = f"{color}22" if active else "transparent"
    pill_border = ft.border.all(1, color) if active else ft.border.all(1, "transparent")

    return ft.Container(
        content=ft.Row(controls=controls, spacing=5, tight=True,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=30,
        border_radius=15,
        padding=ft.padding.symmetric(horizontal=10),
        alignment=ft.alignment.center,
        bgcolor=pill_color,
        border=pill_border,
        ink=True,
        on_click=on_click,
    )

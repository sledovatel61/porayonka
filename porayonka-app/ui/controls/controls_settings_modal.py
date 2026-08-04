# ui/controls/controls_settings_modal.py
# Glass Dark settings modal
import flet as ft
from typing import Callable
from .glass_theme import GLASS
from core.controls_data import DEFAULT_SETTINGS, get_criminalist_names
from core.controls_models import short_name

def create_controls_settings_modal(page: ft.Page, settings: dict, on_apply: Callable[[dict], None]) -> ft.AlertDialog:
    def _glass_tf(label, value="", width=None, expand=False, hint=None):
        return ft.TextField(
            value=value,
            label=label,
            hint_text=hint or "",
            border_radius=10,
            border_color=GLASS["border"],
            focused_border_color=GLASS["accent"],
            bgcolor=GLASS["surface_alt"],
            color=GLASS["text"],
            label_style=ft.TextStyle(color=GLASS["text_secondary"]),
            hint_style=ft.TextStyle(color=GLASS["text_muted"]),
            text_style=ft.TextStyle(size=13, color=GLASS["text"]),
            width=width,
            expand=expand,
            dense=True,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

    def _glass_dd(label, value, options, width=None):
        return ft.Dropdown(
            label=label,
            value=value,
            options=options,
            border_radius=10,
            border_color=GLASS["border"],
            focused_border_color=GLASS["accent"],
            bgcolor=GLASS["surface_alt"],
            color=GLASS["text"],
            label_style=ft.TextStyle(color=GLASS["text_secondary"]),
            hint_style=ft.TextStyle(color=GLASS["text_muted"]),
            text_style=ft.TextStyle(size=13, color=GLASS["text"]),
            width=width,
            dense=True,
        )

    soon_field = ft.TextField(
        value=str(settings.get("soon_days", 3)),
        label="Считать срок «скорым» за (дней)",
        border_radius=10, border_color=GLASS["border"],
        focused_border_color=GLASS["accent"],
        bgcolor=GLASS["surface_alt"], color=GLASS["text"],
        label_style=ft.TextStyle(color=GLASS["text_secondary"]),
        text_style=ft.TextStyle(size=13, color=GLASS["text"]),
        keyboard_type=ft.KeyboardType.NUMBER, width=240, dense=True,
    )

    net_switch = ft.Switch(value=bool(settings.get("network_enabled")), active_color=GLASS["in_work"], label="Сетевой режим", label_style=ft.TextStyle(color=GLASS["text"]))

    role_dd = _glass_dd("Роль", settings.get("network_role", "admin"),
        [ft.dropdown.Option("admin", "Администратор (ведёт контроли)"), ft.dropdown.Option("user", "Пользователь (видит свои задания)")], width=360)
    criminalist_names = get_criminalist_names()
    current_user = settings.get("network_user", "") or ""
    user_dd = _glass_dd("Пользователь (ФИО)", current_user if current_user in criminalist_names else None,
        [ft.dropdown.Option(n, short_name(n)) for n in criminalist_names], width=360)

    path_field = _glass_tf("Путь к общей папке/файлу (например \\\\SERVER\\share\\porayonka\\controls.json)", value=settings.get("network_shared_path", ""), expand=True)
    hint_text = ft.Text("Синхронизация: общий JSON + обновление раз в ~20 сек. Перед перезаписью — резервная копия. Вложения — в общей папке.", size=10, color=GLASS["text_muted"])

    init_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=100)
    init_field = _glass_tf("Новый инициатор", expand=True)

    def _rebuild_init_list():
        init_list.controls.clear()
        cur = list(settings.get("custom_initiators", []) or [])
        if not cur:
            init_list.controls.append(ft.Text("Нет пользовательских инициаторов", size=11, color=GLASS["text_muted"]))
        for name in cur:
            init_list.controls.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Icon(ft.icons.ACCOUNT_CIRCLE_OUTLINED, size=14, color=GLASS["text_secondary"]),
                        ft.Text(name, size=12, color=GLASS["text"], expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, tooltip=name),
                        ft.IconButton(icon=ft.icons.CLOSE, icon_size=14, icon_color=GLASS["overdue"], tooltip="Удалить", on_click=lambda e, n=name: _remove_init(n)),
                    ], spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=8, padding=ft.padding.symmetric(horizontal=8, vertical=4),
                )
            )
        try:
            init_list.update()
        except Exception:
            pass

    def _add_init(e=None):
        name = (init_field.value or "").strip()
        if not name:
            return
        cur = list(settings.get("custom_initiators", []) or [])
        if name not in cur:
            cur.append(name)
        settings["custom_initiators"] = cur
        init_field.value = ""
        try:
            init_field.update()
        except Exception:
            pass
        _rebuild_init_list()

    def _remove_init(name):
        cur = list(settings.get("custom_initiators", []) or [])
        if name in cur:
            cur.remove(name)
        settings["custom_initiators"] = cur
        _rebuild_init_list()

    _rebuild_init_list()

    def _close(e=None):
        try:
            page.close(dialog)
        except Exception:
            dialog.open = False
            try:
                page.update()
            except Exception:
                pass

    def _save(e=None):
        try:
            soon = max(1, int(soon_field.value or "3"))
        except ValueError:
            soon = 3
        merged = dict(DEFAULT_SETTINGS)
        merged.update({
            "soon_days": soon,
            "network_enabled": bool(net_switch.value),
            "network_role": role_dd.value or "admin",
            "network_user": user_dd.value or "",
            "network_shared_path": (path_field.value or "").strip(),
            "custom_initiators": list(settings.get("custom_initiators", []) or []),
        })
        on_apply(merged)
        try:
            page.close(dialog)
        except Exception:
            dialog.open = False
            try:
                page.update()
            except Exception:
                pass

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=GLASS["surface_solid"],
        title=ft.Row(controls=[ft.Icon(ft.icons.SETTINGS_OUTLINED, size=20, color=GLASS["text"]), ft.Text("Настройки контролей", size=16, weight=ft.FontWeight.BOLD, color=GLASS["text"])], spacing=8),
        content=ft.Container(
            width=640,
            content=ft.Column(controls=[
                ft.Container(content=ft.Column(controls=[ft.Text("Уведомления", size=12, weight=ft.FontWeight.BOLD, color=GLASS["text"]), soon_field], spacing=6, tight=True), bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=10, padding=ft.padding.all(12)),
                ft.Container(content=ft.Column(controls=[ft.Text("Сетевой режим (локальная сеть)", size=12, weight=ft.FontWeight.BOLD, color=GLASS["text"]), net_switch, role_dd, user_dd, path_field, hint_text], spacing=8, tight=True), bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=10, padding=ft.padding.all(12)),
                ft.Container(content=ft.Column(controls=[ft.Text("Инициаторы (пользовательские)", size=12, weight=ft.FontWeight.BOLD, color=GLASS["text"]), ft.Row(controls=[init_field, ft.Container(content=ft.Text("Добавить", size=12, color="white", weight=ft.FontWeight.BOLD), height=36, padding=ft.padding.symmetric(horizontal=12), bgcolor=GLASS["accent"], border_radius=10, ink=True, on_click=_add_init, alignment=ft.alignment.center)], spacing=6, tight=True), init_list], spacing=8, tight=True), bgcolor=GLASS["surface_alt"], border=ft.border.all(1, GLASS["border"]), border_radius=10, padding=ft.padding.all(12)),
            ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
        ),
        actions=[
            ft.TextButton("Отмена", on_click=_close, style=ft.ButtonStyle(color=GLASS["text_secondary"])),
            ft.Container(content=ft.Row(controls=[ft.Icon(ft.icons.SAVE, size=16, color="white"), ft.Text("Сохранить", size=13, weight=ft.FontWeight.BOLD, color="white")], spacing=6, tight=True, alignment=ft.MainAxisAlignment.CENTER), height=40, padding=ft.padding.symmetric(horizontal=18), bgcolor=GLASS["accent"], border_radius=10, ink=True, on_click=_save, alignment=ft.alignment.center),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=14),
    )
    return dialog

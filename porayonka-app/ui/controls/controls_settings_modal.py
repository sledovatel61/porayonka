# ui/controls/controls_settings_modal.py
# Настройки вкладки «Контроли»: порог «скоро», сетевой режим,
# пользователь, пользовательские инициаторы.
# Скин «Glass Dark»: палитра — ui/controls/glass_theme.py (логика не менялась).
import flet as ft
from typing import Callable

from core.controls_data import DEFAULT_SETTINGS, get_criminalist_names
from core.controls_models import short_name
from .glass_theme import GLASS, GLASS_STATUS
from core.controls_models import IN_PROGRESS


def create_controls_settings_modal(
    page: ft.Page,
    settings: dict,
    on_apply: Callable[[dict], None],
) -> ft.AlertDialog:
    """Модалка настроек. on_apply(merged_settings) вызывается при сохранении."""

    def _glass_field(**kw):
        opts = dict(
            label_style=ft.TextStyle(color=GLASS["text_2"]),
            border_radius=10,
            border_color=GLASS["border"],
            focused_border_color=GLASS["accent"],
            bgcolor=GLASS["field"],
            color=GLASS["text"],
            hint_style=ft.TextStyle(color=GLASS["text_3"], size=11),
            text_style=ft.TextStyle(size=13, color=GLASS["text"]),
        )
        opts.update(kw)
        return ft.TextField(**opts)

    def _glass_dd(**kw):
        opts = dict(
            label_style=ft.TextStyle(color=GLASS["text_2"]),
            border_radius=10,
            border_color=GLASS["border"],
            focused_border_color=GLASS["accent"],
            bgcolor=GLASS["field"],
            color=GLASS["text"],
            hint_style=ft.TextStyle(color=GLASS["text_3"], size=11),
            text_style=ft.TextStyle(size=13, color=GLASS["text"]),
        )
        opts.update(kw)
        return ft.Dropdown(**opts)

    soon_field = _glass_field(
        value=str(settings.get("soon_days", 3)),
        label="Считать срок «скорым» за (дней)",
        keyboard_type=ft.KeyboardType.NUMBER, width=220,
    )

    net_switch = ft.Switch(
        value=bool(settings.get("network_enabled")),
        active_color=GLASS_STATUS[IN_PROGRESS], label="Сетевой режим",
    )
    role_dd = _glass_dd(
        label="Роль",
        value=settings.get("network_role", "admin"),
        options=[
            ft.dropdown.Option("admin", "Администратор (ведёт контроли)"),
            ft.dropdown.Option("user", "Пользователь (видит свои задания)"),
        ],
        width=340,
    )

    criminalist_names = get_criminalist_names()
    current_user = settings.get("network_user", "") or ""
    user_dd = _glass_dd(
        label="Пользователь (ФИО)",
        value=current_user if current_user in criminalist_names else None,
        options=[ft.dropdown.Option(n, short_name(n)) for n in criminalist_names],
        width=340,
    )
    path_field = _glass_field(
        value=settings.get("network_shared_path", ""),
        label="Путь к общей папке/файлу (например \\\\SERVER\\share\\porayonka\\controls.json)",
        expand=True,
    )
    hint_text = ft.Text(
        "Синхронизация: общий JSON + обновление раз в ~20 сек. "
        "Перед перезаписью — резервная копия. Вложения — в общей папке.",
        size=10, color=GLASS["text_3"],
    )

    # ── Пользовательские инициаторы ─────────────────────────────
    init_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=90)
    init_field = _glass_field(
        label="Новый инициатор",
        expand=True, height=36,
    )

    def _rebuild_init_list():
        init_list.controls.clear()
        cur = list(settings.get("custom_initiators", []) or [])
        if not cur:
            init_list.controls.append(ft.Text("Нет пользовательских инициаторов",
                                              size=11, color=GLASS["text_3"]))
        for name in cur:
            init_list.controls.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Icon(ft.icons.ACCOUNT_CIRCLE_OUTLINED, size=14,
                                color=GLASS["text_2"]),

                        ft.Text(name, size=12, color=GLASS["text"], expand=True,
                                no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
                                tooltip=name),
                        ft.IconButton(icon=ft.icons.CLOSE, icon_size=14,
                                      icon_color=GLASS["danger"], tooltip="Удалить",
                                      on_click=lambda e, n=name: _remove_init(n)),
                    ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       alignment=ft.MainAxisAlignment.START, tight=True),
                    bgcolor=GLASS["surface"], border=ft.border.all(1, GLASS["border"]),
                    border_radius=8, padding=ft.padding.symmetric(horizontal=6, vertical=2),
                )
            )
        try:
            init_list.update()
        except Exception:
            pass

    def _add_init(e=None):
        name = init_field.value.strip()
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
        dialog.open = False
        page.update()

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
        dialog.open = False
        page.update()

    def _section(title: str, content) -> ft.Container:
        return ft.Container(
            content=ft.Column(controls=[
                ft.Text(title, size=12, weight=ft.FontWeight.BOLD, color=GLASS["text"]),
                content,
            ], spacing=8, tight=True),
            bgcolor=GLASS["surface"], border=ft.border.all(1, GLASS["border"]),
            border_radius=10, padding=ft.padding.all(10),
        )

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=GLASS["surface_solid"],
        title=ft.Row(controls=[
            ft.Icon(ft.icons.SETTINGS_OUTLINED, size=20, color=GLASS["accent"]),
            ft.Text("Настройки контролей", size=16, weight=ft.FontWeight.BOLD,
                    color=GLASS["text"]),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        content=ft.Container(
            width=600,
            content=ft.Column(controls=[
                _section("Уведомления", soon_field),
                _section("Сетевой режим (локальная сеть)", ft.Column(controls=[
                    net_switch,
                    role_dd,
                    user_dd,
                    path_field,
                    hint_text,
                ], spacing=8, tight=True)),
                _section("Инициаторы (пользовательские)", ft.Column(controls=[
                    ft.Row(controls=[init_field,
                                     ft.ElevatedButton("Добавить",
                                                       bgcolor=GLASS["accent"],
                                                       color=GLASS["text"],
                                                       height=36,
                                                       on_click=_add_init)],
                           spacing=6, tight=True,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER,
                           alignment=ft.MainAxisAlignment.START),
                    init_list,
                ], spacing=8, tight=True)),
            ], spacing=10, tight=True),
        ),
        actions=[
            ft.TextButton("Отмена", on_click=_close, style=ft.ButtonStyle(color=GLASS["text_2"])),
            ft.ElevatedButton("Сохранить", icon=ft.icons.SAVE, bgcolor=GLASS["accent"],
                              color=GLASS["text"], on_click=_save,
                              style=ft.ButtonStyle(
                                  shape=ft.RoundedRectangleBorder(radius=10),
                                  padding=ft.padding.symmetric(horizontal=20, vertical=8))),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=14),
    )
    return dialog

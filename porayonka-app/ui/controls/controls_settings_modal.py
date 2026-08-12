# ui/controls/controls_settings_modal.py
# Настройки вкладки «Контроли»: порог «скоро», сетевой режим, пользователь,
# пароль администратора.
# Раунд 28 (задача 6): управление справочниками (люди/инициаторы) УБРАНО —
# оно живёт в отдельной модалке «Справочники» из тулбара; значения
# custom_initiators/extra_people здесь лишь прокидываются при сохранении.
import flet as ft
from typing import Callable

from core.constants import COLORS
from core.controls_data import DEFAULT_SETTINGS, get_criminalist_names
from core.controls_models import short_name


def create_controls_settings_modal(
    page: ft.Page,
    settings: dict,
    on_apply: Callable[[dict], None],
) -> ft.AlertDialog:
    """Модалка настроек. on_apply(merged_settings) вызывается при сохранении."""
    soon_field = ft.TextField(
        value=str(settings.get("soon_days", 3)),
        label="Считать срок «скорым» за (дней)",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        keyboard_type=ft.KeyboardType.NUMBER, width=220,
    )
    sound_check = ft.Checkbox(
        label="Звук уведомлений",
        value=bool(settings.get("notify_sound", True)),
        active_color=COLORS["received"],
        label_style=ft.TextStyle(size=12, color=COLORS["text"]),
    )

    net_switch = ft.Switch(
        value=bool(settings.get("network_enabled")),
        active_color=COLORS["received"], label="Сетевой режим",
    )
    role_dd = ft.Dropdown(
        label="Роль",
        value=settings.get("network_role", "admin"),
        options=[
            ft.dropdown.Option("admin", "Администратор (ведёт контроли)"),
            ft.dropdown.Option("user", "Пользователь (видит свои задания)"),
        ],
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"], width=340,
    )

    criminalist_names = get_criminalist_names()
    current_user = settings.get("network_user", "") or ""
    user_dd = ft.Dropdown(
        label="Пользователь (ФИО)",
        value=current_user if current_user in criminalist_names else None,
        options=[ft.dropdown.Option(n, short_name(n)) for n in criminalist_names],
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"], width=340,
    )
    path_field = ft.TextField(
        value=settings.get("network_shared_path", ""),
        label="Путь к общей папке/файлу (например \\\\SERVER\\share\\porayonka\\controls.json)",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        width=556,
    )
    hint_text = ft.Text(
        "Синхронизация: общий JSON + обновление раз в ~20 сек. "
        "Перед перезаписью — резервная копия. Вложения — в общей папке.",
        size=10, color=COLORS["text_muted"],
    )

    # ── Раунд 28 (задача 7): пароль администратора (только admin-редакция) ──
    # Хранится в %APPDATA%/porayonka/edition.json как password_hash
    # (base64 sha256 + соль) — переживает переустановку/обновление exe.
    from core.edition import (  # noqa: E402  (локальный импорт — как в других местах)
        load_edition, admin_password_hash, admin_password_required,
        check_admin_password, save_appdata_password_hash,
    )

    def _pw_has() -> bool:
        try:
            return admin_password_required(load_edition(force=True))
        except Exception:
            return False

    pw_status = ft.Text("", size=12, color=COLORS["text_secondary"])
    pw_err = ft.Text("", size=11, color="#ef4444")
    pw_old = ft.TextField(
        label="Текущий пароль", password=True, width=260, height=40,
        label_style=ft.TextStyle(color=COLORS["text_secondary"], size=11),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
    )
    pw_new = ft.TextField(
        label="Новый пароль", password=True, width=260, height=40,
        label_style=ft.TextStyle(color=COLORS["text_secondary"], size=11),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
    )
    pw_new2 = ft.TextField(
        label="Повторите новый пароль", password=True, width=260, height=40,
        label_style=ft.TextStyle(color=COLORS["text_secondary"], size=11),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
    )
    pw_save_btn = ft.ElevatedButton(
        "Установить пароль", height=34,
        bgcolor=COLORS["btn_save"], color=COLORS["text_light"],
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
    )
    pw_del_btn = ft.TextButton("Удалить пароль")

    def _pw_update(ctl):
        try:
            ctl.update()
        except Exception:
            pass

    def _pw_refresh():
        has = _pw_has()
        pw_status.value = ("Пароль установлен (запрашивается при входе)"
                           if has else "Пароль не установлен")
        pw_save_btn.text = "Сменить пароль" if has else "Установить пароль"
        pw_old.visible = has
        pw_del_btn.visible = has
        for c in (pw_status, pw_save_btn, pw_old, pw_del_btn):
            _pw_update(c)

    def _pw_toast(msg):
        try:
            from ui.toast import show_toast
            show_toast(page, msg, icon=ft.icons.CHECK_CIRCLE_OUTLINE)
        except Exception:
            pass

    def _pw_err(msg):
        pw_err.value = msg
        _pw_update(pw_err)

    def _pw_save(e=None):
        has = _pw_has()
        if has and not check_admin_password(load_edition(), pw_old.value or ""):
            _pw_err("Неверный текущий пароль")
            return
        if (pw_new.value or "") != (pw_new2.value or ""):
            _pw_err("Новый пароль и повтор не совпадают")
            return
        if not (pw_new.value or "").strip():
            _pw_err("Пароль не может быть пустым (для отключения — «Удалить пароль»)")
            return
        if save_appdata_password_hash(admin_password_hash(pw_new.value or "")):
            pw_err.value = ""
            for f in (pw_old, pw_new, pw_new2):
                f.value = ""
                _pw_update(f)
            _pw_refresh()
            _pw_toast("Пароль администратора обновлён")
        else:
            _pw_err("Не удалось сохранить пароль (appdata недоступен)")

    def _pw_delete(e=None):
        def _yes(ev=None):
            save_appdata_password_hash("")
            for f in (pw_old, pw_new, pw_new2):
                f.value = ""
                _pw_update(f)
            _pw_refresh()
            _pw_toast("Пароль администратора удалён")
            try:
                page.close(confirm)
            except Exception:
                pass

        def _no(ev=None):
            try:
                page.close(confirm)
            except Exception:
                pass

        confirm = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["primary_light"],
            title=ft.Text("Удалить пароль?", size=15, weight=ft.FontWeight.BOLD,
                          color=COLORS["text"]),
            content=ft.Text("Вход в администраторскую версию перестанет "
                            "запрашивать пароль.", size=12,
                            color=COLORS["text_secondary"]),
            actions=[
                ft.TextButton("Отмена", on_click=_no),
                ft.ElevatedButton("Удалить", on_click=_yes,
                                  bgcolor="#ef4444", color="#ffffff"),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        try:
            page.open(confirm)
        except Exception:
            pass

    pw_save_btn.on_click = _pw_save
    pw_del_btn.on_click = _pw_delete
    _pw_refresh()

    # секция пароля — только в admin-редакции (в user её вообще нет в дереве)
    _is_admin_edition = False
    try:
        _is_admin_edition = (load_edition().get("role") == "admin")
    except Exception:
        _is_admin_edition = False

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
            "notify_sound": bool(sound_check.value),
            "notify_log": settings.get("notify_log") or {},
            "extra_people": list(settings.get("extra_people", []) or []),
        })
        on_apply(merged)
        dialog.open = False
        page.update()

    _sections = [
        ft.Container(
            content=ft.Column(controls=[
                ft.Text("Уведомления", size=12, weight=ft.FontWeight.BOLD,
                        color=COLORS["text"]),
                soon_field,
                sound_check,
            ], spacing=6, tight=True),
            bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]),
            border_radius=10, padding=ft.padding.all(10),
        ),
        ft.Container(
            content=ft.Column(controls=[
                ft.Text("Сетевой режим (локальная сеть)", size=12,
                        weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                net_switch,
                role_dd,
                user_dd,
                path_field,
                hint_text,
            ], spacing=8, tight=True),
            bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]),
            border_radius=10, padding=ft.padding.all(10),
        ),
    ]
    if _is_admin_edition:
        _sections.append(ft.Container(
            content=ft.Column(controls=[
                ft.Text("Пароль администратора", size=12,
                        weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                pw_status,
                pw_old,
                pw_new,
                pw_new2,
                ft.Row(controls=[pw_save_btn, pw_del_btn], spacing=8,
                       tight=True,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                pw_err,
            ], spacing=8, tight=True),
            bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]),
            border_radius=10, padding=ft.padding.all(10),
        ))

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=COLORS["primary_light"],
        title=ft.Row(controls=[
            ft.Icon(ft.icons.SETTINGS_OUTLINED, size=20, color=COLORS["text"]),
            ft.Text("Настройки контролей", size=16, weight=ft.FontWeight.BOLD,
                    color=COLORS["text"]),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        content=ft.Container(
            width=600,
            height=460,
            content=ft.Column(controls=_sections, spacing=10,
                              scroll=ft.ScrollMode.AUTO),
        ),
        actions=[
            ft.TextButton("Отмена", on_click=_close),
            ft.ElevatedButton("Сохранить", icon=ft.icons.SAVE, bgcolor=COLORS["btn_save"],
                              color=COLORS["text_light"], on_click=_save,
                              style=ft.ButtonStyle(
                                  shape=ft.RoundedRectangleBorder(radius=8),
                                  padding=ft.padding.symmetric(horizontal=20, vertical=8))),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=12),
    )
    return dialog

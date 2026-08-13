# ui/admin_gate.py
# Раунд 26 (задача 5): парольный вход АДМИНСКОЙ редакции.
#
# Правило: если edition.json admin-редакции содержит "password_hash"
# (или plain "password" от установщика) — при старте показывается модальное
# окно ввода пароля ДО построения вкладок. Верный пароль → on_ok() (обычный
# запуск). Неверный — приложение закрывается (требование промпта дословно).
# Пароля нет / редакция не admin — ворот нет (обратная совместимость).
import flet as ft

from core.edition import (
    load_edition, admin_password_required, check_admin_password,
)
from core.constants import COLORS


def _close_app(page) -> None:
    """Закрыть приложение после неверного пароля/отказа (натив и web)."""
    try:
        page.window.destroy()
        return
    except Exception:
        pass
    try:
        page.window.close()
        return
    except Exception:
        pass
    try:
        import os
        import sys
        if getattr(sys, "frozen", False):
            os._exit(0)  # последний фолбэк — только боевую сборку можно убивать
    except Exception:
        pass


def show_admin_password_gate(page, on_ok, ed=None) -> bool:
    """Показать парольный вход (если требуется). Возвращает True, если ворота
    открыты (on_ok будет вызван ПОСЛЕ верного пароля); False — пароль не
    нужен и on_ok уже вызван синхронно."""
    if ed is None:
        ed = load_edition()
    if not admin_password_required(ed):
        on_ok()
        return False

    err_txt = ft.Text("", size=12, color="#ef4444")
    pw_tf = ft.TextField(
        label="Пароль",
        password=True,
        can_reveal_password=True,
        autofocus=True,
        width=280,
    )

    # Раунд 30 (задача 1): защита от ПОВТОРНОГО срабатывания _try. Живой
    # клиент Flet 0.23.2 может прислать событие submit/клик несколько раз
    # подряд (как FilePicker-result в раунде 21) — без флага on_ok вызывался
    # бы повторно и _main_impl строил бы таблицу ВТОРОЙ раз («тускло/дважды»,
    # см. design/screenshots/13.08.2026/Пароль не принимается.png).
    _submitted = {"v": False}

    def _try(e=None):
        if _submitted["v"]:
            return
        ok = False
        try:
            ok = check_admin_password(ed, pw_tf.value or "")
        except Exception:
            ok = False
        if ok:
            _submitted["v"] = True
            try:
                page.close(dlg)
                # Раунд 30 (задача 1): page.update() ПОСЛЕ close гарантирует,
                # что команда закрытия модального диалога ушла на клиент ДО
                # построения UI: иначе _main_impl своими update() мог
                # «перекрыть» закрытие, и таблица рисовалась тусклой под
                # диалогом.
                page.update()
            except Exception:
                pass
            on_ok()
        else:
            # «Если пароль неверный — приложение закрывается» (промпт, задача 5)
            _submitted["v"] = True
            print("[AUTH] nevernyj parol - vyhod")
            try:
                page.close(dlg)
                page.update()
            except Exception:
                pass
            _close_app(page)

    def _quit(e=None):
        if _submitted["v"]:
            return
        _submitted["v"] = True
        print("[AUTH] otkaza ot vvoda - vyhod")
        try:
            page.close(dlg)
            page.update()
        except Exception:
            pass
        _close_app(page)

    pw_tf.on_submit = _try
    dlg = ft.AlertDialog(
        modal=True,
        bgcolor=COLORS["primary_light"],
        title=ft.Row(
            controls=[
                ft.Icon(ft.icons.LOCK_OUTLINE, size=18, color=COLORS["btn_save"]),
                ft.Text("Вход: администраторская редакция", size=15,
                        weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ],
            spacing=8,
            tight=True,
        ),
        content=ft.Container(
            width=340,
            content=ft.Column(
                controls=[
                    ft.Text("Для этой копии «Порайонки» задан пароль администратора.",
                            size=12, color=COLORS["text_secondary"]),
                    pw_tf,
                    err_txt,
                ],
                spacing=8,
                tight=True,
            ),
        ),
        actions=[
            ft.TextButton("Выход", on_click=_quit),
            ft.ElevatedButton("Войти", on_click=_try,
                              bgcolor=COLORS["btn_save"], color="#ffffff"),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=12),
    )
    try:
        page.open(dlg)
        page.update()
    except Exception:
        try:
            page.overlay.append(dlg)
            dlg.open = True
            page.update()
        except Exception as ex:
            print(f"[AUTH] dialog error: {ex}")
    return True

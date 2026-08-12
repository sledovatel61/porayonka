# ui/tray_icon.py
# Раунд 23 (задача 2): значок в системном трее — «приложение находится в трее
# и работает всегда» (пользователи не забывают запустить после включения ПК).
# Раунд 24 (задача 4): трей запускается ТОЛЬКО в frozen-сборке на Windows.
# Раунд 26 (задача 2): трей работает и в WEB-режиме (Win7): браузер можно
# закрыть — сервер остаётся в трее, «Открыть» поднимает вкладку браузера,
# алармы сроков дублируются balloon-уведомлением (notify()).
#
# pystray — ОПЦИОНАЛЬНАЯ зависимость (только для сборки дистрибутивов):
#   pip install pystray pillow
# Библиотека чисто ctypes-ная → работает и на Win7. Если её нет — приложение
# спокойно работает без трея (один print в лог), ничего не ломается.
import os
import sys
import webbrowser
from pathlib import Path

_ACTIVE_ICON = None  # процесс-одиночка (в web-режиме main() создаётся на сессию)


def _icon_path() -> Path:
    if getattr(sys, "frozen", False):
        p = Path(getattr(sys, "_MEIPASS", "")) / "assets" / "icon.png"
        if p.exists():
            return p
    return Path(__file__).resolve().parent.parent / "assets" / "icon.png"


def get_active_icon():
    """Уже запущенный трей-значок процесса (или None)."""
    return _ACTIVE_ICON


def notify(message: str, title: str = "Пораёнка — Контроли") -> bool:
    """Раунд 26 (задача 2): balloon-уведомление из трея (Shell_NotifyIcon
    NIF_INFO на Windows; на Win7 работает). pystray не даёт колбэк клика по
    balloon — поэтому текст подсказывает открыть приложение через значок,
    а сам значок («Открыть», double-click) уже открывает приложение/вкладку.
    Без трея/pystray — мягкий False, ничего не ломается."""
    ic = _ACTIVE_ICON
    if ic is None:
        return False
    try:
        fn = getattr(ic, "notify", None)
        if not callable(fn):
            return False
        try:
            fn(message, title=title)
        except TypeError:
            fn(message)
        print("[TRAY] balloon shown")
        return True
    except Exception as e:
        print(f"[TRAY] notify error: {e}")
        return False


def start_tray(page=None, title: str = "Пораёнка — Контроли",
               web_url: str = None) -> object:
    """Запустить иконку в трее (daemon-поток pystray). Возвращает Icon|None.

    page/web_url:
      - нативный клиент: start_tray(page) — «Открыть» показывает окно;
      - web-режим (Win7): start_tray(None, web_url="http://127.0.0.1:8555") —
        «Открыть» поднимает вкладку браузера с сервером (main.py передаёт URL).
    Меню: «Открыть» и «Выход».
    """
    global _ACTIVE_ICON
    # Раунд 24 (задача 4): ТОЛЬКО frozen Windows-сборка (dev-запуски — мимо).
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        print("[TRAY] skip (tray tolko v frozen Windows-sborke)")
        return None
    if _ACTIVE_ICON is not None:
        # Раунд 26 (задача 2): web-режим — main() вызывается на каждую
        # браузерную сессию; второй значок трея не нужен.
        return _ACTIVE_ICON
    try:
        import pystray
        from PIL import Image
    except ImportError:
        print("[TRAY] pystray/pillow ne ustanovleny — tray otklyuchen "
              "(pip install pystray pillow)")
        return None

    def _show(icon=None, item=None):
        # Открыть/на передний план. Web (Win7): новая вкладка браузера с
        # адресом сервера; натив: показать окно.
        try:
            if web_url:
                webbrowser.open(web_url)
                return
        except Exception as e:
            print(f"[TRAY] open browser error: {e}")
            return
        try:
            page.window.visible = True
            page.window.to_front()
            page.update()
        except Exception as e:
            print(f"[TRAY] show window error: {e}")

    def _quit(icon, item):
        try:
            icon.stop()
        except Exception:
            pass
        if web_url or os.environ.get("PORAYONKA_WEB"):
            # Раунд 26 (задача 2): web-режим — «окна» нет, процесс = сервер.
            try:
                os._exit(0)
            except Exception:
                pass
            return
        try:
            page.window.destroy()
        except Exception:
            try:
                page.window.close()
            except Exception as e:
                print(f"[TRAY] close window error: {e}")

    try:
        image = Image.open(_icon_path())
    except Exception as e:
        print(f"[TRAY] icon load error: {e}")
        return None

    open_label = "Открыть в браузере" if web_url else "Открыть"
    menu = pystray.Menu(
        pystray.MenuItem(open_label, _show, default=True),
        pystray.MenuItem("Выход", _quit),
    )
    icon = pystray.Icon("porayonka", image, title, menu)
    try:
        icon.run_detached()  # daemon-поток; умирает вместе с процессом
        _ACTIVE_ICON = icon
        print("[TRAY] icon started" + (" (web: " + web_url + ")" if web_url else ""))
        return icon
    except Exception as e:
        print(f"[TRAY] start error: {e}")
        return None

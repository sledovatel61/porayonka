# ui/tray_icon.py
# Раунд 23 (задача 2): значок в системном трее — «приложение находится в трее
# и работает всегда» (пользователи не забывают запустить после включения ПК).
#
# pystray — ОПЦИОНАЛЬНАЯ зависимость (только для сборки дистрибутивов):
#   pip install pystray pillow
# Библиотека чисто ctypes-ная → работает и на Win7. Если её нет — приложение
# спокойно работает без трея (один print в лог), ничего не ломается.
import sys
from pathlib import Path


def _icon_path() -> Path:
    if getattr(sys, "frozen", False):
        p = Path(getattr(sys, "_MEIPASS", "")) / "assets" / "icon.png"
        if p.exists():
            return p
    return Path(__file__).resolve().parent.parent / "assets" / "icon.png"


def start_tray(page, title: str = "Пораёнка — Контроли") -> object:
    """Запустить иконку в трее (daemon-поток pystray). Возвращает Icon|None.

    Меню: «Открыть» (показать окно/в фокус) и «Выход»."""
    try:
        import pystray
        from PIL import Image
    except ImportError:
        print("[TRAY] pystray/pillow ne ustanovleny — tray otklyuchen "
              "(pip install pystray pillow)")
        return None

    def _show(icon=None, item=None):
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

    menu = pystray.Menu(
        pystray.MenuItem("Открыть", _show, default=True),
        pystray.MenuItem("Выход", _quit),
    )
    icon = pystray.Icon("porayonka", image, title, menu)
    try:
        icon.run_detached()  # daemon-поток; умирает вместе с процессом
        print("[TRAY] icon started")
        return icon
    except Exception as e:
        print(f"[TRAY] start error: {e}")
        return None

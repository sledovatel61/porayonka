# core/autostart.py
# Раунд 23 (задача 2): автозапуск приложения при входе в Windows —
# «пользователи не забывали запускать после включения ПК».
# Только winreg (stdlib), работает и на Win7. Вне Windows — no-op.
import sys

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_VALUE = "PorayonkaControls"


def _exe_command() -> str:
    """Команда автозапуска: только упакованная сборка (sys.frozen);
    для dev-запуска автозапуск не прописываем (иначе сломаем Run-ключ)."""
    exe = sys.executable
    return f'"{exe}"'


def is_supported() -> bool:
    return sys.platform == "win32"


def autostart_enabled() -> bool:
    if not is_supported():
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_QUERY_VALUE) as key:
            try:
                winreg.QueryValueEx(key, APP_VALUE)
                return True
            except OSError:
                return False
    except Exception as e:
        print(f"[AUTOSTART] query error: {e}")
        return False


def enable_autostart() -> bool:
    """Прописать в автозапуск текущий exe (только frozen-сборка и Windows)."""
    if not is_supported():
        return False
    if not getattr(sys, "frozen", False):
        # dev-режим: python.exe в автозапуск не пишем
        print("[AUTOSTART] dev-run: skip (not frozen)")
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_VALUE, 0, winreg.REG_SZ, _exe_command())
        print("[AUTOSTART] enabled")
        return True
    except Exception as e:
        print(f"[AUTOSTART] enable error: {e}")
        return False


def disable_autostart() -> bool:
    if not is_supported():
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, APP_VALUE)
            except OSError:
                pass
        return True
    except Exception as e:
        print(f"[AUTOSTART] disable error: {e}")
        return False

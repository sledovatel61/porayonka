# ui/sound_alert.py
# Раунд 23 (задача 2): «злой» звуковой аларм срока контроля — визжащая свинья.
#
# Файл: porayonka-app/assets/pig.wav (синтезирован tools/make_pig_sound.py
# из-за TLS-фильтра песочницы, бинарные скачки резались). ПОДМЕНА: положите
# настоящий звук (напр. infected_p.wav из дистрибутива Касперского) как
#   %APPDATA%/porayonka/pig.wav        (приоритет)
# или замените assets/pig.wav в сборке — приложение возьмёт его.
#
# Воспроизведение — winsound (stdlib), работает и на Win7. Вне Windows — тихо.
import os
import sys
from pathlib import Path
from typing import Optional


def pig_sound_candidates():
    base = Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "frozen", False) else None
    cands = []
    appdata = os.getenv("APPDATA", str(Path.home() / ".config"))
    cands.append(Path(appdata) / "porayonka" / "pig.wav")       # пользовательская подмена
    if base:
        cands.append(base / "assets" / "pig.wav")               # PyInstaller bundle
    cands.append(Path(__file__).resolve().parent.parent / "assets" / "pig.wav")
    return cands


def find_pig_sound() -> Optional[Path]:
    for c in pig_sound_candidates():
        try:
            if c.exists():
                return c
        except OSError:
            continue
    return None


def play_alarm_sound(enabled: bool = True) -> bool:
    """Проиграть «визжащую свинью» асинхронно (один раз; повтор — на следующем
    тике аларма). True, если файл реально запущен в воспроизведение."""
    if not enabled:
        return False
    if sys.platform != "win32":
        print("[ALARM] pig sound (non-Windows, silent)")
        return False
    path = find_pig_sound()
    try:
        import winsound
        if path:
            winsound.PlaySound(
                str(path),
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
            )
            return True
        # файла нет — хотя бы системный сигнал
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception as e:
        print(f"[ALARM] sound error: {e}")
    return False


def stop_alarm_sound() -> None:
    """Остановить звучащий аларм (на будущее, если включим SND_LOOP)."""
    if sys.platform != "win32":
        return
    try:
        import winsound
        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception:
        pass

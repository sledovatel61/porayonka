# ui/sound_alert.py
# Раунд 23 (задача 2): «злой» звуковой аларм срока контроля — визжащая свинья.
# Раунд 24 (задача 3): РЕАЛЬНЫЙ звук — assets/pig.mp3 (MP3 через Windows MCI,
# stdlib ctypes → winmm.mciSendStringW — играет на Win7+ без новых
# зависимостей). pig.wav остаётся для обратной совместимости.
#
# Приоритет файлов (find_pig_sound / play_alarm_sound):
#   1) %APPDATA%/porayonka/pig.wav  — пользовательская подмена WAV (совм.)
#   2) %APPDATA%/porayonka/pig.mp3  — пользовательская подмена MP3
#   3) <bundle>/assets/pig.mp3      — PyInstaller (_MEIPASS) — наш реальный
#   4) <dev>/assets/pig.mp3         — рядом с исходниками
#   5) <bundle>/assets/pig.wav      — синтез раунда 23 (крайний fallback)
#   6) <dev>/assets/pig.wav
#
# Воспроизведение: WAV — winsound (stdlib), MP3 — MCI. Вне Windows — тихо.
import os
import sys
from pathlib import Path
from typing import Optional

MCI_ALIAS = "porayonka_pig"


def pig_sound_candidates():
    """Кандидаты звукового файла в порядке приоритета (см. шапку модуля)."""
    base = Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "frozen", False) else None
    appdata = Path(os.getenv("APPDATA", str(Path.home() / ".config"))) / "porayonka"
    dev = Path(__file__).resolve().parent.parent / "assets"
    cands = [
        appdata / "pig.wav",            # 1) пользовательская подмена WAV
        appdata / "pig.mp3",            # 2) пользовательская подмена MP3
    ]
    if base:
        cands.append(base / "assets" / "pig.mp3")   # 3) бандл
    cands.append(dev / "pig.mp3")                   # 4) dev
    if base:
        cands.append(base / "assets" / "pig.wav")   # 5) бандл (синтез)
    cands.append(dev / "pig.wav")                   # 6) dev (синтез)
    return cands


def find_pig_sound() -> Optional[Path]:
    for c in pig_sound_candidates():
        try:
            if c.exists():
                return c
        except OSError:
            continue
    return None


def _play_mp3_mci(path: Path) -> bool:
    """Раунд 24 (задача 3): воспроизвести MP3 через Windows MCI.

    mciSendStringW (winmm.dll) — часть Windows начиная с Win95, MP3
    (type mpegvideo) играет и на Win7. ctypes — stdlib, зависимостей нет.
    `play` без `wait` — асинхронно: аларм звучит, UI не виснет. Повторный
    вызов сначала закрывает прежний alias (антиспам 2 ч/24 ч подаст снова).
    """
    try:
        import ctypes
        winmm = ctypes.windll.winmm
    except Exception:
        return False
    try:
        buf = ctypes.create_unicode_buffer(260)
        # закрыть предыдущий экземпляр (если аларм ещё звучал) — ошибку игнорим
        winmm.mciSendStringW(f"close {MCI_ALIAS}", buf, 260, None)
        rc = winmm.mciSendStringW(
            f'open "{path}" type mpegvideo alias {MCI_ALIAS}', buf, 260, None)
        if rc != 0:
            print(f"[ALARM] MCI open error: rc={rc}")
            return False
        rc = winmm.mciSendStringW(f"play {MCI_ALIAS}", buf, 260, None)
        if rc != 0:
            print(f"[ALARM] MCI play error: rc={rc}")
            winmm.mciSendStringW(f"close {MCI_ALIAS}", buf, 260, None)
            return False
        return True
    except Exception as e:
        print(f"[ALARM] MCI error: {e}")
        return False


def _stop_mp3_mci() -> None:
    try:
        import ctypes
        ctypes.windll.winmm.mciSendStringW(
            f"close {MCI_ALIAS}", ctypes.create_unicode_buffer(260), 260, None)
    except Exception:
        pass


def play_alarm_sound(enabled: bool = True) -> bool:
    """Проиграть «визжащую свинью» асинхронно (один раз; повтор — на следующем
    тике аларма). True, если файл реально запущен в воспроизведение."""
    if not enabled:
        return False
    if sys.platform != "win32":
        print("[ALARM] pig sound (non-Windows, silent)")
        return False
    for path in pig_sound_candidates():
        try:
            if not path.exists():
                continue
        except OSError:
            continue
        try:
            if path.suffix.lower() == ".mp3":
                if _play_mp3_mci(path):  # Раунд 24: реальный звук
                    return True
            else:
                import winsound
                winsound.PlaySound(
                    str(path),
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                )
                return True
        except Exception as e:
            print(f"[ALARM] sound error ({path.name}): {e}")
    try:
        # файла нет (или ничего не заиграло) — хотя бы системный сигнал
        import winsound
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception as e:
        print(f"[ALARM] beep error: {e}")
    return False


def stop_alarm_sound() -> None:
    """Остановить звучащий аларм (на будущее, если включим цикл)."""
    if sys.platform != "win32":
        return
    try:
        import winsound
        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception:
        pass
    _stop_mp3_mci()

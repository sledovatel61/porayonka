# core/controls_data.py
# Загрузка/сохранение контролей, настроек и сетевая синхронизация.
import json
import os
import shutil
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Callable

from .controls_models import Control, ONE_TIME, PERIODIC

# Версия схемы — используется для миграции при изменении формата
SCHEMA_VERSION = 1

DEFAULT_CONTROLLERS = ["Потемкин С.А.", "Чашин Э.А."]
DEFAULT_INITIATORS = [
    "СУ", "ГУК СК", "ГУК ЮФО", "СК РФ", "ПСК", "ГСУ", "ОКРИМ",
]

DEFAULT_SETTINGS = {
    "soon_days": 3,          # за сколько дней считать срок «скорым»
    "network_enabled": False,
    "network_role": "admin",     # admin | user
    "network_user": "",          # имя компьютера/пользователя (по-фамильно)
    "network_shared_path": "",   # путь к общей папке/файлу
}


# ────────────────────────────────────────────────
# ПУТИ
# ────────────────────────────────────────────────

def get_data_path() -> Path:
    appdata = os.getenv("APPDATA", str(Path.home() / ".config"))
    data_path = Path(appdata) / "porayonka"
    data_path.mkdir(parents=True, exist_ok=True)
    return data_path


def get_controls_file() -> Path:
    return get_data_path() / "controls.json"


def get_settings_file() -> Path:
    return get_data_path() / "controls_settings.json"


# ────────────────────────────────────────────────
# ЗАГРУЗКА / СОХРАНЕНИЕ КОНТРОЛЕЙ
# ────────────────────────────────────────────────

def load_controls() -> List[Control]:
    file_path = get_controls_file()
    if not file_path.exists():
        save_controls([])
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        version = data.get("schema_version", 0)
        controls = [Control.from_dict(d) for d in data.get("controls", [])]
        _migrate(version, controls)
        return controls
    except (json.JSONDecodeError, OSError, ValueError) as e:
        print(f"[CONTROLS_DATA] Oshibka zagruzki controls.json: {e}")
        return []


def save_controls(controls: List[Control]) -> str:
    """Сохранить контроли локально. Возвращает ISO-время сохранения."""
    file_path = get_controls_file()
    now = datetime.now().isoformat()
    data = {
        "schema_version": SCHEMA_VERSION,
        "last_saved": now,
        "controls": [c.to_dict() for c in controls],
    }
    # Резервная копия перед перезаписью (защита от конфликтов)
    _make_backup(file_path)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return now
    except (PermissionError, OSError) as e:
        print(f"[CONTROLS_DATA] Oshibka sohraneniya: {e}")
        raise


def _make_backup(file_path: Path, keep: int = 3) -> None:
    """Создать .bak копию перед перезаписью (last-write-wins + резерв)."""
    try:
        if file_path.exists():
            backups = sorted(file_path.parent.glob("controls.json.bak*"))
            for old in backups[:max(0, len(backups) - keep + 1)]:
                try:
                    old.unlink()
                except OSError:
                    pass
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(file_path, file_path.with_name(f"controls.json.bak.{stamp}"))
    except OSError as e:
        print(f"[CONTROLS_DATA] Backup error: {e}")


def _migrate(version: int, controls: List[Control]) -> None:
    """Точка расширения для миграции формата при будущих версиях схемы."""
    if version < 1:
        # Первичная миграция не требуется — поля уже обрабатываются с дефолтами.
        pass


# ────────────────────────────────────────────────
# НАСТРОЙКИ
# ────────────────────────────────────────────────

def load_settings() -> dict:
    file_path = get_settings_file()
    settings = dict(DEFAULT_SETTINGS)
    if not file_path.exists():
        return settings
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k in DEFAULT_SETTINGS:
            if k in data:
                settings[k] = data[k]
        return settings
    except (json.JSONDecodeError, OSError) as e:
        print(f"[CONTROLS_DATA] Oshibka zagruzki settings: {e}")
        return settings


def save_settings(settings: dict) -> None:
    merged = dict(DEFAULT_SETTINGS)
    merged.update(settings or {})
    file_path = get_settings_file()
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[CONTROLS_DATA] Oshibka sohraneniya settings: {e}")
        raise


# ────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ────────────────────────────────────────────────

def next_control_number(controls: List[Control]) -> int:
    """Следующий порядковый номер (№)."""
    return len(controls) + 1


def get_criminalist_names() -> List[str]:
    """Список ФИО криминалистов из вкладки «Зональные»."""
    try:
        from .zonal_data import load_criminalists
        names = [c.full_name for c in load_criminalists() if c.full_name]
        # Объединяем с дефолтными контролерами
        for n in DEFAULT_CONTROLLERS:
            if n not in names:
                names.append(n)
        return names
    except Exception:
        return list(DEFAULT_CONTROLLERS)


def get_initiators() -> List[str]:
    return list(DEFAULT_INITIATORS)


# ────────────────────────────────────────────────
# СЕТЕВАЯ СИНХРОНИЗАЦИЯ (SHARED JSON + POLLING)
# ────────────────────────────────────────────────

def _parse_shared_path(settings: dict) -> Optional[Path]:
    """Путь к общему файлу. Принимает путь к файлу или к папке."""
    if not settings.get("network_enabled"):
        return None
    raw = (settings.get("network_shared_path") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    if p.suffix.lower() == ".json":
        return p
    return p / "controls.json"


def shared_file_exists(settings: dict) -> bool:
    p = _parse_shared_path(settings)
    return bool(p and p.exists())


def read_shared_controls(settings: dict) -> List[Control]:
    """Прочитать контроли из общего сетевого файла."""
    p = _parse_shared_path(settings)
    if not p or not p.exists():
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [Control.from_dict(d) for d in data.get("controls", [])]
    except (json.JSONDecodeError, OSError, ValueError) as e:
        print(f"[CONTROLS_DATA] Oshibka chteniya obshego fayla: {e}")
        return []


def write_shared_controls(controls: List[Control], settings: dict) -> bool:
    """Записать контроли в общий сетевой файл. Возвращает успех."""
    p = _parse_shared_path(settings)
    if not p:
        return False
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "schema_version": SCHEMA_VERSION,
            "last_saved": datetime.now().isoformat(),
            "controls": [c.to_dict() for c in controls],
        }
        # Резервная копия перед перезаписью общего файла
        if p.exists():
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(p, p.with_name(f"controls.json.bak.{stamp}"))
        tmp = p.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)  # атомарная замена
        return True
    except OSError as e:
        print(f"[CONTROLS_DATA] Oshibka zapisi v obshiy fayl: {e}")
        return False


def get_shared_mtime(settings: dict) -> Optional[float]:
    """mtime общего файла для отслеживания изменений."""
    p = _parse_shared_path(settings)
    if not p or not p.exists():
        return None
    try:
        return p.stat().st_mtime
    except OSError:
        return None

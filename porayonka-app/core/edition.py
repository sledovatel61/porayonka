# core/edition.py
# Раунд 23 (задача 2): редакция дистрибутива — «admin» (полная) / «user»
# (просмотр + уведомления). Редакция задаётся при сборке/установке, а не в
# настройках пользователя: её нельзя переопределить изнутри приложения.
import json
import os
import sys
from pathlib import Path
from typing import Optional

EDITION_ADMIN = "admin"
EDITION_USER = "user"

_cache: Optional[dict] = None


def _app_dir() -> Path:
    """Папка программы (рядом с exe в frozen-сборке / рядом с main.py в dev)."""
    if getattr(sys, "frozen", False):
        try:
            return Path(sys.executable).resolve().parent
        except Exception:
            pass
    return Path(__file__).resolve().parent.parent


def _appdata_edition_file() -> Path:
    appdata = os.getenv("APPDATA", str(Path.home() / ".config"))
    return Path(appdata) / "porayonka" / "edition.json"


def edition_file_candidates():
    """Кандидаты файла редакции (первый существующий побеждает).

    Установщик кладёт `edition.json` рядом с exe; в dev-режиме — рядом с
    main.py; переопределение на уровне пользователя — %APPDATA%/porayonka.
    """
    return [
        _app_dir() / "edition.json",
        _appdata_edition_file(),
    ]


def _read_edition_file(path: Path) -> Optional[dict]:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except (OSError, ValueError) as e:
        print(f"[EDITION] Oshibka chteniya {path}: {e}")
    return None


def load_edition(force: bool = False) -> dict:
    """Вернуть редакцию: {"role": "admin"|"user", "user_name": "Фамилия И.О."}.

    Источники в порядке приоритета:
      1) переменные окружения PORAYONKA_EDITION / PORAYONKA_USER (dev/test);
      2) edition.json рядом с программой;
      3) edition.json в %APPDATA%/porayonka (записывается, напр., первым
         запуском user-редакции после выбора ФИО);
      4) умолчание — admin (обратная совместимость со старыми установками).

    Роль (edition) берётся из самого приоритетного источника, а ФИО — из
    самого приоритетного источника, где оно НЕПУСТОЕ: установщик кладёт рядом
    с exe edition.json только с ролью, а выбранное при первом запуске ФИО
    живёт в %APPDATA% — без такого слияния диалог «Кто вы?» спрашивал бы
    снова при каждом запуске.
    """
    global _cache
    if _cache is not None and not force:
        return _cache
    role: Optional[str] = None
    user_name = ""
    env_role = (os.getenv("PORAYONKA_EDITION") or "").strip().lower()
    if env_role in (EDITION_ADMIN, EDITION_USER):
        role = env_role
        user_name = (os.getenv("PORAYONKA_USER") or "").strip()
    for path in edition_file_candidates():
        if role is not None and user_name:
            break
        data = _read_edition_file(path)
        if not data:
            continue
        if role is None:
            r = str(data.get("role") or "").strip().lower()
            if r in (EDITION_ADMIN, EDITION_USER):
                role = r
        if not user_name:
            user_name = str(data.get("user_name") or "").strip()
    if role is None:
        role = EDITION_ADMIN
    _cache = {"role": role, "user_name": user_name}
    return _cache


def is_user_edition() -> bool:
    return load_edition().get("role") == EDITION_USER


def save_appdata_edition(role: str, user_name: str = "") -> bool:
    """Записать редакцию в %APPDATA% (выбор ФИО пользователем при первом
    запуске user-редакции — чтобы не спрашивать снова)."""
    path = _appdata_edition_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"role": role, "user_name": user_name}, f,
                      ensure_ascii=False, indent=2)
        load_edition(force=True)
        return True
    except OSError as e:
        print(f"[EDITION] Oshibka zapisi {path}: {e}")
        return False


def apply_edition_to_settings(settings: dict) -> bool:
    """Перенести редакцию в настройки вкладки (role->network_role, ФИО ->
    network_user). Возвращает True, если settings изменились.

    user-редакция ПРИНУДИТЕЛЬНО переводит сетевую роль в «user» — обойти
    read-only правкой controls_settings.json нельзя."""
    changed = False
    ed = load_edition()
    if ed.get("role") == EDITION_USER:
        if settings.get("network_role") != "user":
            settings["network_role"] = "user"
            changed = True
        nm = (ed.get("user_name") or "").strip()
        if nm and (settings.get("network_user") or "").strip() != nm:
            settings["network_user"] = nm
            changed = True
    return changed

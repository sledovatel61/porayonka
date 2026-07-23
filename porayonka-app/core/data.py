# core/data.py
# Загрузка и сохранение данных в JSON (%APPDATA%\porayonka\departments.json)

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .models import Department, Status
from .constants import INITIAL_DEPARTMENTS


def get_data_path() -> Path:
    """
    Вернуть путь к папке данных приложения.
    Windows: %APPDATA%\\porayonka
    Linux/Mac: ~/.config/porayonka
    Создаёт папку, если не существует.
    """
    appdata = os.getenv("APPDATA", str(Path.home() / ".config"))
    data_path = Path(appdata) / "porayonka"
    data_path.mkdir(parents=True, exist_ok=True)
    return data_path


def get_file_path() -> Path:
    """Полный путь к файлу departments.json"""
    return get_data_path() / "departments.json"


def _make_default_departments() -> List[Department]:
    """Создать список отделов с дефолтными значениями"""
    return [
        Department(
            id=d["id"],
            name=d["name"],
            status=Status.EMPTY,
            updated_at=None,
            is_ovd=d["is_ovd"],
        )
        for d in INITIAL_DEPARTMENTS
    ]


def load_departments() -> List[Department]:
    """
    Загрузить список отделов из JSON-файла.
    Если файл не существует или повреждён — создать дефолтный и сохранить.
    Автоматически добавляет новые отделы, если их не было в файле.
    """
    file_path = get_file_path()

    # Файл не существует → создать дефолтные
    if not file_path.exists():
        departments = _make_default_departments()
        save_departments(departments)
        return departments

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        departments: List[Department] = []
        for d in data.get("departments", []):
            try:
                dept = Department(
                    id=d["id"],
                    name=d["name"],
                    status=Status(d.get("status", "empty")),
                    updated_at=(
                        datetime.fromisoformat(d["updated_at"])
                        if d.get("updated_at")
                        else None
                    ),
                    is_ovd=d.get("is_ovd", False),
                )
                departments.append(dept)
            except (KeyError, ValueError) as e:
                print(f"[data.py] Пропуск записи из-за ошибки: {e}")
                continue

        # Добавить отделы, которые появились в INITIAL_DEPARTMENTS позже
        existing_ids = {d.id for d in departments}
        for d in INITIAL_DEPARTMENTS:
            if d["id"] not in existing_ids:
                departments.append(
                    Department(
                        id=d["id"],
                        name=d["name"],
                        status=Status.EMPTY,
                        is_ovd=d["is_ovd"],
                    )
                )

        # Всегда сортируем по id
        departments.sort(key=lambda x: x.id)
        return departments

    except (json.JSONDecodeError, OSError) as e:
        print(f"[data.py] Ошибка загрузки файла: {e}. Используем дефолтные данные.")
        departments = _make_default_departments()
        save_departments(departments)
        return departments


def save_departments(departments: List[Department]) -> str:
    """
    Сохранить список отделов в JSON-файл.
    Возвращает ISO-строку времени сохранения.
    Выбрасывает OSError при ошибке записи.
    """
    file_path = get_file_path()
    now = datetime.now()

    data = {
        "departments": [
            {
                "id": d.id,
                "name": d.name,
                "status": d.status.value,
                "updated_at": d.updated_at.isoformat() if d.updated_at else None,
                "is_ovd": d.is_ovd,
            }
            for d in departments
        ],
        "last_saved": now.isoformat(),
    }

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return now.isoformat()
    except (PermissionError, OSError) as e:
        print(f"[data.py] Ошибка сохранения: {e}")
        raise


def get_last_save_date() -> Optional[datetime]:
    """
    Получить дату и время последнего сохранения из JSON.
    Возвращает None, если файл не найден или не содержит метку.
    """
    file_path = get_file_path()

    if not file_path.exists():
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        last_saved = data.get("last_saved")
        return datetime.fromisoformat(last_saved) if last_saved else None
    except Exception:
        return None


def reset_departments() -> List[Department]:
    """
    Сбросить все статусы к начальным значениям (Status.EMPTY).
    Сохраняет результат в JSON.
    Возвращает новый список отделов.
    """
    departments = _make_default_departments()
    save_departments(departments)
    return departments


def get_stats(departments: List[Department]) -> dict:
    """
    Подсчитать статистику по статусам.
    Возвращает словарь: received, in_progress, empty, total, percent.
    """
    received = sum(1 for d in departments if d.status == Status.RECEIVED)
    in_progress = sum(1 for d in departments if d.status == Status.IN_PROGRESS)
    empty = sum(1 for d in departments if d.status == Status.EMPTY)
    total = len(departments)
    percent = round((received + in_progress) / total * 100) if total > 0 else 0

    return {
        "received": received,
        "in_progress": in_progress,
        "empty": empty,
        "total": total,
        "percent": percent,
    }

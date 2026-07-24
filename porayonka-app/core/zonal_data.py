# core/zonal_data.py
# Загрузка и сохранение данных зональных криминалистов
# Разделённое хранение: шаблон, данные, криминалисты — отдельно
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .zonal_models import (
    ReportTemplate, ReportTemplateItem, ReportItemType,
    ReportData, ZonalCollection, Criminalist, CriminalistZone,
)
from .zonal_constants import get_initial_criminalists


# ────────────────────────────────────────────────────────────
# ПУТИ К ФАЙЛАМ
# ────────────────────────────────────────────────────────────

def get_data_path() -> Path:
    """Путь к папке данных: %APPDATA%\\porayonka"""
    appdata = os.getenv("APPDATA", str(Path.home() / ".config"))
    data_path = Path(appdata) / "porayonka"
    data_path.mkdir(parents=True, exist_ok=True)
    return data_path


def get_templates_path() -> Path:
    """Путь к папке шаблонов: %APPDATA%\\porayonka\\templates"""
    path = get_data_path() / "templates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_collection_file() -> Path:
    """Путь к старому файлу сбора данных (для миграции)"""
    return get_data_path() / "zonal_collection.json"


def get_template_file() -> Path:
    """Путь к файлу текущего шаблона"""
    return get_data_path() / "zonal_template.json"


def get_submissions_file() -> Path:
    """Путь к файлу данных отчётов"""
    return get_data_path() / "zonal_submissions.json"


def get_criminalists_file() -> Path:
    """Путь к файлу криминалистов"""
    return get_data_path() / "zonal_criminalists.json"


# ────────────────────────────────────────────────────────────
# СЕРИАЛИЗАЦИЯ / ДЕСЕРИАЛИЗАЦИЯ
# ────────────────────────────────────────────────────────────

def _template_item_to_dict(item: ReportTemplateItem) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "item_type": item.item_type.value,
        "unit": item.unit,
        "order": item.order,
    }


def _template_item_from_dict(d: dict) -> ReportTemplateItem:
    return ReportTemplateItem(
        id=d["id"],
        name=d["name"],
        item_type=ReportItemType(d.get("item_type", "numerical")),
        unit=d.get("unit", ""),
        order=d.get("order", 0),
    )


def _template_to_dict(template: ReportTemplate) -> dict:
    return {
        "name": template.name,
        "items": [_template_item_to_dict(i) for i in template.items],
        "created_at": template.created_at.isoformat(),
        "use_departments_mode": template.use_departments_mode,
    }


def _template_from_dict(d: dict) -> ReportTemplate:
    return ReportTemplate(
        name=d.get("name", "Без названия"),
        items=[_template_item_from_dict(i) for i in d.get("items", [])],
        created_at=datetime.fromisoformat(d["created_at"]) if d.get("created_at") else datetime.now(),
        use_departments_mode=d.get("use_departments_mode", False),
    )


def _report_data_to_dict(rd: ReportData) -> dict:
    return {
        "criminalist_id": rd.criminalist_id,
        "template_item_id": rd.template_item_id,
        "value": rd.value,
        "is_submitted": rd.is_submitted,
        "comment": rd.comment,
        "updated_at": rd.updated_at.isoformat() if rd.updated_at else None,
        "department_values": {str(k): v for k, v in rd.department_values.items()},
        "department_submitted": {str(k): v for k, v in rd.department_submitted.items()},
    }


def _report_data_from_dict(d: dict) -> ReportData:
    return ReportData(
        criminalist_id=d["criminalist_id"],
        template_item_id=d["template_item_id"],
        value=d.get("value"),
        is_submitted=d.get("is_submitted", False),
        comment=d.get("comment", ""),
        updated_at=datetime.fromisoformat(d["updated_at"]) if d.get("updated_at") else None,
        department_values={int(k): v for k, v in d.get("department_values", {}).items()},
        department_submitted={int(k): v for k, v in d.get("department_submitted", {}).items()},
    )


def _criminalist_to_dict(c: Criminalist) -> dict:
    return {
        "id": c.id,
        "full_name": c.full_name,
        "note": c.note,
        "is_active": c.is_active,
        "zone": {
            "criminalist_id": c.zone.criminalist_id,
            "department_ids": c.zone.department_ids,
        },
    }


def _criminalist_from_dict(d: dict) -> Criminalist:
    zone_data = d.get("zone", {})
    return Criminalist(
        id=d["id"],
        full_name=d["full_name"],
        note=d.get("note", ""),
        is_active=d.get("is_active", True),  # Для обратной совместимости
        zone=CriminalistZone(
            criminalist_id=zone_data.get("criminalist_id", d["id"]),
            department_ids=zone_data.get("department_ids", []),
        ),
    )


# ────────────────────────────────────────────────────────────
# ШАБЛОНЫ
# ────────────────────────────────────────────────────────────

def load_zonal_templates() -> List[ReportTemplate]:
    """Загрузить список сохранённых шаблонов из папки templates/"""
    templates = []
    templates_path = get_templates_path()
    try:
        for file in sorted(templates_path.glob("*.json")):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                template = _template_from_dict(data)
                templates.append(template)
                print(f"[ZONAL_DATA] Загружен шаблон: {template.name} ({file.name})")
            except Exception as e:
                print(f"[ZONAL_DATA] Ошибка загрузки шаблона {file.name}: {e}")
    except Exception as e:
        print(f"[ZONAL_DATA] Ошибка чтения папки шаблонов: {e}")
    print(f"[ZONAL_DATA] Всего шаблонов: {len(templates)}")
    return templates


def save_zonal_template(template: ReportTemplate) -> str:
    """Сохранить шаблон в JSON. Возвращает путь к файлу."""
    templates_path = get_templates_path()
    # Имя файла из названия шаблона (очищаем спецсимволы)
    safe_name = "".join(c for c in template.name if c.isalnum() or c in " _-").strip()
    safe_name = safe_name.replace(" ", "_") or "template"
    filename = f"{safe_name}.json"
    filepath = templates_path / filename
    try:
        data = _template_to_dict(template)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[ZONAL_DATA] Шаблон сохранён: {filepath}")
        return str(filepath)
    except Exception as e:
        print(f"[ZONAL_DATA] Ошибка сохранения шаблона: {e}")
        raise


def delete_zonal_template(template_name: str) -> None:
    """Удалить шаблон по имени"""
    templates_path = get_templates_path()
    safe_name = "".join(c for c in template_name if c.isalnum() or c in " _-").strip()
    safe_name = safe_name.replace(" ", "_") or "template"
    filepath = templates_path / f"{safe_name}.json"
    try:
        if filepath.exists():
            filepath.unlink()
            print(f"[ZONAL_DATA] Шаблон удалён: {filepath}")
    except Exception as e:
        print(f"[ZONAL_DATA] Ошибка удаления шаблона: {e}")


# ────────────────────────────────────────────────────────────
# ТЕКУЩИЙ ШАБЛОН (РАЗДЕЛЁННОЕ ХРАНЕНИЕ)
# ────────────────────────────────────────────────────────────

def load_zonal_template() -> ReportTemplate:
    """Загрузить текущий активный шаблон из zonal_template.json"""
    filepath = get_template_file()
    if not filepath.exists():
        print("[ZONAL_DATA] Файл шаблона не найден, создаю пустой")
        return ReportTemplate(name="Новая форма")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        template = _template_from_dict(data)
        print(f"[ZONAL_DATA] Шаблон загружен: {template.name}, пунктов: {len(template.items)}")
        return template
    except Exception as e:
        print(f"[ZONAL_DATA] Ошибка загрузки шаблона: {e}")
        return ReportTemplate(name="Новая форма")


def save_zonal_template_to_file(template: ReportTemplate) -> None:
    """Сохранить текущий шаблон в zonal_template.json"""
    filepath = get_template_file()
    try:
        data = _template_to_dict(template)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[ZONAL_DATA] Шаблон сохранён: {filepath}")
    except Exception as e:
        print(f"[ZONAL_DATA] Ошибка сохранения шаблона: {e}")
        raise


# ────────────────────────────────────────────────────────────
# ДАННЫЕ ОТЧЁТОВ / SUBMISSIONS (РАЗДЕЛЁННОЕ ХРАНЕНИЕ)
# ────────────────────────────────────────────────────────────

def load_zonal_submissions() -> List[ReportData]:
    """Загрузить данные отчётов из zonal_submissions.json"""
    filepath = get_submissions_file()
    if not filepath.exists():
        print("[ZONAL_DATA] Файл данных не найден, будет создан пустой")
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        submissions = [_report_data_from_dict(s) for s in data.get("submissions", [])]
        print(f"[ZONAL_DATA] Загружено данных: {len(submissions)}")
        return submissions
    except Exception as e:
        print(f"[ZONAL_DATA] Ошибка загрузки данных: {e}")
        return []


def save_zonal_submissions(submissions: List[ReportData]) -> None:
    """Сохранить данные отчётов в zonal_submissions.json"""
    filepath = get_submissions_file()
    try:
        data = {"submissions": [_report_data_to_dict(s) for s in submissions]}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[ZONAL_DATA] Данные сохранены ({len(submissions)} записей): {filepath}")
    except Exception as e:
        print(f"[ZONAL_DATA] Ошибка сохранения данных: {e}")
        raise


def clear_zonal_submissions() -> None:
    """Очистить все данные отчётов (сброс данных) с резервной копией."""
    filepath = get_submissions_file()
    try:
        if filepath.exists():
            # Backup перед удалением с уникальным именем, чтобы не конфликтовать
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = get_data_path() / f"zonal_submissions_backup_{timestamp}.json"
            filepath.rename(backup_path)
            print(f"[ZONAL_DATA] Данные перемещены в backup: {backup_path}")
        data = {"submissions": []}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[ZONAL_DATA] Данные очищены: {filepath}")
    except Exception as e:
        print(f"[ZONAL_DATA] Ошибка очистки данных: {e}")
        # Если backup не удался, просто записываем пустой файл
        data = {"submissions": []}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ────────────────────────────────────────────────────────────
# КРИМИНАЛИСТЫ (РАЗДЕЛЁННОЕ ХРАНЕНИЕ)
# ────────────────────────────────────────────────────────────

def load_criminalists() -> List[Criminalist]:
    """Загрузить список криминалистов (из файла или дефолтный)"""
    filepath = get_criminalists_file()
    if not filepath.exists():
        print("[ZONAL_DATA] Файл криминалистов не найден, используем дефолтный")
        return get_initial_criminalists()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        criminalists = [_criminalist_from_dict(c) for c in data.get("criminalists", [])]
        print(f"[ZONAL_DATA] Загружено криминалистов: {len(criminalists)}")
        return criminalists if criminalists else get_initial_criminalists()
    except Exception as e:
        print(f"[ZONAL_DATA] Ошибка загрузки криминалистов: {e}")
        return get_initial_criminalists()


def save_criminalists(criminalists: List[Criminalist]) -> None:
    """Сохранить список криминалистов"""
    filepath = get_criminalists_file()
    try:
        data = {"criminalists": [_criminalist_to_dict(c) for c in criminalists]}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[ZONAL_DATA] Криминалисты сохранены: {len(criminalists)}")
    except Exception as e:
        print(f"[ZONAL_DATA] Ошибка сохранения криминалистов: {e}")
        raise


# ────────────────────────────────────────────────────────────
# КОЛЛЕКЦИЯ (ОБЪЕДИНЯЕТ ВСЕ ЧАСТИ)
# ────────────────────────────────────────────────────────────

def _migrate_old_collection() -> bool:
    """
    Миграция старого zonal_collection.json в новые файлы.
    Возвращает True, если миграция выполнена.
    """
    old_file = get_collection_file()
    if not old_file.exists():
        return False
    
    print("[ZONAL_DATA] Обнаружен старый формат данных, выполняю миграцию...")
    try:
        with open(old_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Миграция шаблона
        template_data = data.get("template", {"name": "Новая форма"})
        template = _template_from_dict(template_data)
        save_zonal_template_to_file(template)
        
        # Миграция submissions
        submissions_data = data.get("submissions", [])
        submissions = [_report_data_from_dict(s) for s in submissions_data]
        save_zonal_submissions(submissions)
        
        # Миграция криминалистов
        criminalists_data = data.get("criminalists", [])
        if criminalists_data:
            criminalists = [_criminalist_from_dict(c) for c in criminalists_data]
        else:
            criminalists = get_initial_criminalists()
        save_criminalists(criminalists)
        
        # Backup старого файла
        backup_path = old_file.with_suffix(".json.old")
        old_file.rename(backup_path)
        print(f"[ZONAL_DATA] Миграция завершена. Старый файл: {backup_path}")
        return True
        
    except Exception as e:
        print(f"[ZONAL_DATA] Ошибка миграции: {e}")
        return False


def load_zonal_collection() -> Optional[ZonalCollection]:
    """
    Загрузить текущий сбор данных.
    Автоматически выполняет миграцию при наличии старого формата.
    """
    # Проверяем миграцию
    _migrate_old_collection()
    
    # Загружаем из раздельных файлов
    template = load_zonal_template()
    submissions = load_zonal_submissions()
    criminalists = load_criminalists()
    
    # Если нет данных — создаём новую коллекцию
    if not criminalists:
        criminalists = get_initial_criminalists()
        save_criminalists(criminalists)
    
    # Получаем время последнего сохранения из submissions
    last_saved = None
    for sub in submissions:
        if sub.updated_at and (last_saved is None or sub.updated_at > last_saved):
            last_saved = sub.updated_at
    
    collection = ZonalCollection(
        template=template,
        submissions=submissions,
        last_saved=last_saved,
        criminalists=criminalists,
    )
    print(f"[ZONAL_DATA] Коллекция загружена: {template.name}, "
          f"submissions: {len(submissions)}, криминалистов: {len(criminalists)}")
    return collection


def save_zonal_collection(collection: ZonalCollection) -> None:
    """
    Сохранить сбор данных в раздельные файлы.
    """
    try:
        # Сохраняем шаблон
        save_zonal_template_to_file(collection.template)
        
        # Сохраняем submissions
        save_zonal_submissions(collection.submissions)
        
        # Сохраняем криминалистов
        save_criminalists(collection.criminalists)
        
        print(f"[ZONAL_DATA] Коллекция сохранена")
    except Exception as e:
        print(f"[ZONAL_DATA] Ошибка сохранения коллекции: {e}")
        raise


# ────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ────────────────────────────────────────────────────────────

def get_report_data(
    collection: ZonalCollection,
    criminalist_id: int,
    template_item_id: str,
) -> ReportData:
    """Получить данные отчёта (или создать новый если нет)"""
    for submission in collection.submissions:
        if (submission.criminalist_id == criminalist_id and
                submission.template_item_id == template_item_id):
            return submission
    # Создаём новый
    new_data = ReportData(
        criminalist_id=criminalist_id,
        template_item_id=template_item_id,
    )
    collection.submissions.append(new_data)
    return new_data


def get_summary(collection: ZonalCollection) -> dict:
    """
    Подсчитать сводку по активным криминалистам.
    Неактивные исключаются из подсчёта.
    """
    summary = {}
    
    # Фильтруем только активных криминалистов
    active_criminalists = [c for c in collection.criminalists if c.is_active]
    total_active = len(active_criminalists)
    
    for item in collection.template.items:
        total_value = 0
        submitted_count = 0
        filled_count = 0
        
        for crim in active_criminalists:
            rd = None
            for sub in collection.submissions:
                if sub.criminalist_id == crim.id and sub.template_item_id == item.id:
                    rd = sub
                    break
            if rd is None:
                continue
            if item.item_type == ReportItemType.NUMERICAL:
                if rd.value is not None:
                    total_value += rd.value
                    filled_count += 1
            elif item.item_type == ReportItemType.DELIVERABLE:
                if rd.is_submitted:
                    submitted_count += 1
                    filled_count += 1
        
        summary[item.id] = {
            "item": item,
            "total_value": total_value,
            "submitted_count": submitted_count,
            "filled_count": filled_count,
            "total_criminalists": total_active,  # Только активные
            "total_all": len(collection.criminalists),  # Все (для информации)
        }
    return summary

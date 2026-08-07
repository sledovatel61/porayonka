# core/controls_data.py
# Загрузка/сохранение контролей, настроек, вложений и сетевая синхронизация.
import json
import os
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .controls_models import Control, short_name

# Версия схемы — используется для миграции при изменении формата
SCHEMA_VERSION = 2

DEFAULT_CONTROLLERS = ["Потемкин С.А.", "Чашин Э.А."]
DEFAULT_INITIATORS = [
    "СУ", "ГУК СК", "ГУК ЮФО", "СК РФ", "ПСК", "ГСУ", "ОКРИМ",
]

DEFAULT_SETTINGS = {
    "soon_days": 3,          # за сколько дней считать срок «скорым»
    "network_enabled": False,
    "network_role": "admin",     # admin | user
    "network_user": "",          # имя пользователя (по-фамильно), из списка криминалистов
    "network_shared_path": "",   # путь к общей папке/файлу
    "custom_initiators": [],     # список пользовательских инициаторов (v2)
    "notify_log": {},            # журнал уведомлений: {"<control_id>:<status>": "YYYY-MM-DD"}
    "notify_sound": True,        # звук уведомлений (winsound.MessageBeep)
}

# Максимальный размер вложения, при котором показывается предупреждение
ATTACHMENT_WARN_MB = 20
ATTACHMENT_ALLOWED_EXT = (".pdf", ".png", ".jpg", ".jpeg")


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


def get_attachments_path() -> Path:
    """Локальная папка вложений: %APPDATA%\\porayonka\\controls_attachments."""
    path = get_data_path() / "controls_attachments"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_attachment_dir(control_id: str) -> Path:
    """Папка вложений конкретного контроля (локально)."""
    path = get_attachments_path() / control_id
    path.mkdir(parents=True, exist_ok=True)
    return path


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
    """Миграция формата при будущих версиях схемы."""
    # Поля schema v2 (end_date, milestones, attachments, archived, ...)
    # обрабатываются Control.from_dict с дефолтами, отдельная миграция не нужна.
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
        # Раунд 7: сохраняем ВСЕ ключи из файла, включая дополнительные
        # (например, col_widths — иначе ширины колонок терялись при перезапуске)
        for k, v in data.items():
            settings[k] = v
        return settings
    except (json.JSONDecodeError, OSError) as e:
        print(f"[CONTROLS_DATA] Oshibka zagruzki settings: {e}")
        return settings


def save_settings(settings: dict) -> None:
    merged = dict(DEFAULT_SETTINGS)
    merged.update(settings or {})
    # журнал уведомлений: при сохранении подрезать записи старше 30 дней
    try:
        prune_notify_log(merged.setdefault("notify_log", {}))
    except Exception as e:
        print(f"[CONTROLS_DATA] notify log prune error: {e}")
    file_path = get_settings_file()
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[CONTROLS_DATA] Oshibka sohraneniya settings: {e}")
        raise


# ────────────────────────────────────────────────
# ЖУРНАЛ УВЕДОМЛЕНИЙ (антиспам)
# ────────────────────────────────────────────────

def _should_notify(log: dict, control_id: str, status: str, today: str) -> bool:
    """Надо ли уведомлять сейчас (по антиспам-журналу `notify_log`).

    - status == "new": один раз вообще (ключ `<control_id>:new`);
    - остальные статусы: не чаще одного раза в день на контроль на статус
      (ключ `<control_id>:<status>`, значение — дата последнего уведомления).
    """
    last = (log or {}).get(f"{control_id}:{status}")
    if status == "new":
        return last is None
    return last != today


def prune_notify_log(log: dict, today: Optional[str] = None, days: int = 30) -> dict:
    """Удалить записи журнала уведомлений старше `days` дней.

    Мутирует и возвращает `log`. Битые/неразбираемые значения тоже подрезаются.
    """
    if not log:
        return log
    try:
        base = date.fromisoformat(today) if today else date.today()
        limit = base - timedelta(days=days)
    except (ValueError, TypeError):
        return log
    for key in [k for k in log.keys()]:
        val = (log.get(key) or "").strip()
        try:
            d = date.fromisoformat(val)
        except (ValueError, TypeError):
            del log[key]
            continue
        if d < limit:
            del log[key]
    return log


def add_custom_initiator(settings: dict, name: str) -> None:
    """Добавить пользовательский инициатор в настройки."""
    name = (name or "").strip()
    if not name:
        return
    custom = list(settings.get("custom_initiators", []) or [])
    if name not in custom and name not in DEFAULT_INITIATORS:
        custom.append(name)
    settings["custom_initiators"] = custom
    save_settings(settings)


def remove_custom_initiator(settings: dict, name: str) -> None:
    """Удалить пользовательский инициатор из настроек."""
    custom = list(settings.get("custom_initiators", []) or [])
    if name in custom:
        custom.remove(name)
    settings["custom_initiators"] = custom
    save_settings(settings)


# ────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ────────────────────────────────────────────────

def next_control_number(controls: List[Control]) -> int:
    """Следующий порядковый номер (№)."""
    return len(controls) + 1


def get_criminalist_names() -> List[str]:
    """Список ФИО криминалистов из вкладки «Зональные» + дефолтные контролеры."""
    try:
        from .zonal_data import load_criminalists
        names = [c.full_name for c in load_criminalists() if c.full_name]
        for n in DEFAULT_CONTROLLERS:
            if n not in names:
                names.append(n)
        return names
    except Exception:
        return list(DEFAULT_CONTROLLERS)


def get_criminalists_only() -> List[str]:
    """Канонический список криминалистов (полные ФИО), без дефолтных контролёров.
    Отсортирован по фамилии."""
    try:
        from .zonal_data import load_criminalists
        names = [c.full_name for c in load_criminalists() if c.full_name]
    except Exception:
        names = []
    return sorted(names, key=lambda n: (n.split()[0].casefold() if n.strip() else "", n.casefold()))


def get_controller_names() -> List[str]:
    """Канонический список контролёров: криминалисты + дефолтные контролёры
    (Потемкин С.А., Чашин Э.А.), без дублей по фамилии. Отсортирован по фамилии."""
    out = []
    seen = set()
    for n in get_criminalists_only() + list(DEFAULT_CONTROLLERS):
        surname = (n.strip().split()[0] if n.strip() else "").casefold()
        if not surname or surname in seen:
            continue
        seen.add(surname)
        out.append(n)
    return out


# ────────────────────────────────────────────────
# ИНИЦИАТОРЫ: КАНОНИЧЕСКАЯ КЛАСТЕРИЗАЦИЯ (фильтр)
# ────────────────────────────────────────────────

# Токены-«шум» в хвосте инициатора: не меняют каноническую группу
_INITIATOR_NOISE = {"ск", "с", "рф", "у", "к"}


def _initiator_tokens(raw: str) -> List[str]:
    """Токены инициатора: casefold, разделители → пробелы, точки убраны."""
    s = (raw or "").casefold().replace(".", " ").replace("/", " ").replace("-", " ").replace(",", " ")
    return [t for t in s.split() if t]


def canonical_initiator_group(raw: str) -> str:
    """Каноническая «группа» инициатора (нижний регистр, токены через пробел).

    Схлопывает варианты написания одного инициатора:
      «ГУК С.», «ГУК СК», «ГУК С.Т.С.А.С.И.Ю.» → «гук»;
      «СУ/СК», «СУ СК» → «су»;
      «ГУК ЮФО» остаётся «гук юфо» (не схлопывается в «гук»).
    Значения, не похожие ни на один известный шаблон, возвращаются как есть
    (нормализованные) — они становятся собственными канонами фильтра.
    """
    rt = _initiator_tokens(raw)
    if not rt:
        return ""
    first = rt[0]
    tail = rt[1:]
    # «ГУК …»: хвост из одиночных букв/шумовых токенов → «гук»
    if first == "гук":
        if not tail:
            return "гук"
        if all(len(t) == 1 or t in _INITIATOR_NOISE for t in tail):
            return "гук"
        return " ".join(rt)
    # «СУ/СК», «СУ СК» → «су»
    if first == "су" and all(t in ("ск", "с") for t in tail):
        return "су"
    # общее правило: первый токен + хвост из одиночных букв → первый токен
    if tail and all(len(t) == 1 for t in tail):
        return first
    return " ".join(rt)


def initiator_filter_options(raw_values) -> List[str]:
    """Канонические опции фильтра «Инициаторы» (заглавными, без дублей, по алфавиту).

    Принимает все исходные значения (дефолтные + custom + distinct из данных),
    кластеризует их в группы и возвращает display-форму (upper).
    """
    groups = {}
    for v in raw_values or []:
        g = canonical_initiator_group(v)
        if not g:
            continue
        # display: «гук юфо» → «ГУК ЮФО»
        display = " ".join(t.upper() for t in g.split())
        if display not in groups:
            groups[display] = True
    return sorted(groups.keys())


def get_criminalist_short_names() -> List[str]:
    """Сокращённые ФИО криминалистов («Семисенко И.Ю.»)."""
    return [short_name(n) for n in get_criminalist_names()]


def get_initiators(settings: dict) -> List[str]:
    """Список инициаторов: встроенные + пользовательские из настроек."""
    return list(DEFAULT_INITIATORS) + list(settings.get("custom_initiators", []) or [])


# ────────────────────────────────────────────────
# АРХИВ
# ────────────────────────────────────────────────

def archive_control(control: Control, reason: str) -> None:
    """Переместить контроль в архив."""
    control.archived = True
    control.archived_at = datetime.now().isoformat()
    control.archive_reason = reason
    control.updated_at = datetime.now().isoformat()


def restore_control(control: Control) -> None:
    """Вернуть контроль из архива в активные."""
    control.archived = False
    control.archived_at = None
    control.archive_reason = ""
    control.updated_at = datetime.now().isoformat()


# ────────────────────────────────────────────────
# ВЛОЖЕНИЯ (СКАНЫ)
# ────────────────────────────────────────────────

def get_attachment_source_path(control_id: str, rel_path: str) -> Optional[Path]:
    """Локальный абсолютный путь вложения по относительному пути."""
    safe = Path(rel_path).name
    return get_attachment_dir(control_id) / safe if safe else None


def copy_attachment_to_local(control_id: str, source_path: str) -> Optional[str]:
    """Скопировать файл в локальную папку вложений контроля.

    Возвращает относительный путь (`<control_id>/<filename>`) или None.
    """
    try:
        src = Path(source_path)
        if not src.exists():
            return None
        target_dir = get_attachment_dir(control_id)
        filename = _unique_filename(target_dir, src.name)
        shutil.copy2(src, target_dir / filename)
        return f"{control_id}/{filename}"
    except OSError as e:
        print(f"[CONTROLS_DATA] copy attachment error: {e}")
        return None


def copy_attachment_to_shared(control_id: str, source_path: str, settings: dict) -> Optional[str]:
    """Скопировать файл в общую сетевую папку вложений.

    Возвращает относительный путь или None. Shared-папка определяется как
    родитель общей папки/файла (shared_dir/controls_attachments/...).
    """
    shared_dir = _shared_dir(settings)
    if shared_dir is None:
        return None
    try:
        src = Path(source_path)
        if not src.exists():
            return None
        target_dir = shared_dir / "controls_attachments" / control_id
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = _unique_filename(target_dir, src.name)
        shutil.copy2(src, target_dir / filename)
        return f"{control_id}/{filename}"
    except OSError as e:
        print(f"[CONTROLS_DATA] copy attachment to shared error: {e}")
        return None


def _unique_filename(target_dir: Path, name: str) -> str:
    """Уникальное имя файла при коллизии: `name`, `name_1`, `name_2`, ..."""
    candidate = Path(name)
    stem, suffix = candidate.stem, candidate.suffix
    if not (target_dir / candidate.name).exists():
        return candidate.name
    i = 1
    while (target_dir / f"{stem}_{i}{suffix}").exists():
        i += 1
    return f"{stem}_{i}{suffix}"


def open_attachment(control_id: str, rel_path: str) -> Optional[Path]:
    """Найти абсолютный путь вложения (локально, затем в общей папке).

    При сетевом режиме вложения открываются из общей папки, если их нет локально.
    """
    local = get_attachment_source_path(control_id, rel_path)
    if local and local.exists():
        return local
    return None


def resolve_attachment(control_id: str, rel_path: str, settings: dict) -> Optional[Path]:
    """Разрешить путь вложения: сначала общая папка, затем локально."""
    shared_dir = _shared_dir(settings)
    if shared_dir is not None:
        cand = shared_dir / "controls_attachments" / control_id / Path(rel_path).name
        if cand.exists():
            return cand
    local = get_attachment_source_path(control_id, rel_path)
    if local and local.exists():
        return local
    return None


def delete_attachment(control_id: str, rel_path: str, settings: dict) -> None:
    """Удалить файл вложения (локально и из общей папки)."""
    local = get_attachment_source_path(control_id, rel_path)
    if local and local.exists():
        try:
            local.unlink()
        except OSError:
            pass
    shared_dir = _shared_dir(settings)
    if shared_dir is not None:
        cand = shared_dir / "controls_attachments" / control_id / Path(rel_path).name
        if cand.exists():
            try:
                cand.unlink()
            except OSError:
                pass


def delete_all_attachments(control_id: str, settings: dict) -> None:
    """Удалить папку вложений контроля (локально и в общей папке)."""
    local_dir = get_attachment_dir(control_id)
    try:
        shutil.rmtree(local_dir, ignore_errors=True)
    except OSError:
        pass
    shared_dir = _shared_dir(settings)
    if shared_dir is not None:
        cand = shared_dir / "controls_attachments" / control_id
        try:
            shutil.rmtree(cand, ignore_errors=True)
        except OSError:
            pass


def attachment_abs(rel_path: str) -> Path:
    """Абсолютный путь локального вложения по относительному пути."""
    parts = rel_path.split("/")
    if len(parts) == 2:
        return get_attachment_dir(parts[0]) / parts[1]
    return get_attachments_path() / rel_path


def _shared_dir(settings: dict) -> Optional[Path]:
    """Общая сетевая папка (родитель controls.json / пути)."""
    raw = (settings.get("network_shared_path") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    if p.suffix.lower() == ".json":
        return p.parent
    return p


# ────────────────────────────────────────────────
# СЕТЕВАЯ СИНХРОНИЗАЦИЯ (SHARED JSON + POLLING)
# ────────────────────────────────────────────────

def _updated_sort_key(control: Control) -> tuple:
    """Ключ сравнения updated_at: валидная ISO-строка новее пустого/битого значения."""
    raw = (control.updated_at or "").strip()
    if not raw:
        return (0, "", "")
    try:
        return (1, datetime.fromisoformat(raw).timestamp(), raw)
    except (ValueError, TypeError):
        return (1, -1, raw)


def merge_controls(local: List[Control], shared: List[Control]) -> List[Control]:
    """Union по id. При конфликте версий одного контроля побеждает более новый updated_at.
    Контроль, есть только на одной стороне, — сохраняется.
    Порядок результата: порядок local, новые из shared — в конец (порядок стабилен для UI).

    Сравнение updated_at: ISO-строки сравнимы лексикографически (нормализуются через
    datetime); пустое/битое значение считается старее.

    Оговорка: контроль, удалённый «навсегда» локально (delete_forever), но живой в
    shared, воскреснет при merge. Приемлемо — физическое удаление редкая ручная
    операция админа; tombstones не вводим.
    """
    by_id: Dict[str, Control] = {}
    for c in local:
        by_id[c.id] = c
    for c in shared:
        cur = by_id.get(c.id)
        if cur is None or _updated_sort_key(c) > _updated_sort_key(cur):
            by_id[c.id] = c
    result: List[Control] = []
    seen = set()
    for c in local:
        if c.id in by_id:
            result.append(by_id[c.id])
            seen.add(c.id)
    for c in shared:
        if c.id not in seen:
            result.append(by_id[c.id])
    return result


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


def sync_attachments_from_shared(control_id: str, rel_paths: List[str], settings: dict) -> None:
    """Подтянуть недостающие вложения из общей папки локально."""
    shared_dir = _shared_dir(settings)
    if shared_dir is None:
        return
    for rel in rel_paths:
        shared_file = shared_dir / "controls_attachments" / control_id / Path(rel).name
        if not shared_file.exists():
            continue
        local = get_attachment_dir(control_id) / Path(rel).name
        if local.exists():
            continue
        try:
            shutil.copy2(shared_file, local)
        except OSError:
            pass

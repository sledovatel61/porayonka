# core/controls_data.py
# Загрузка/сохранение контролей, настроек, вложений и сетевая синхронизация.
import json
import os
import threading
import shutil
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from .controls_models import Control, short_name

# Версия схемы — используется для миграции при изменении формата
SCHEMA_VERSION = 2

DEFAULT_CONTROLLERS = ["Потемкин С.А.", "Чашин Э.А."]
DEFAULT_INITIATORS = [
    "СУ", "ГУК СК", "ГУК ЮФО", "СК РФ", "ПСК", "ГСУ", "ОКРИМ",
]

# Раунд 29 (задача 4): общий сетевой путь по умолчанию — чтобы на каждом ПК
# не вводить вручную, достаточно включить сетевой режим. Подставляется,
# когда в настройках network_shared_path пустой.
DEFAULT_NETWORK_PATH = r"\\192.168.0.60\общая\Гайнутдинов\Porayonka workspace"

DEFAULT_SETTINGS = {
    "soon_days": 3,          # за сколько дней считать срок «скорым»
    # Раунд 35: сетевой режим ВКЛЮЧЁН по умолчанию (синхронизация — основная
    # функция; раньше был False, и пользователю приходилось включать вручную)
    "network_enabled": True,
    "network_role": "admin",     # admin | user
    "network_user": "",          # имя пользователя (по-фамильно), из списка криминалистов
    "network_shared_path": DEFAULT_NETWORK_PATH,  # путь к общей папке/файлу
    "custom_initiators": [],     # список пользовательских инициаторов (v2)
    "notify_log": {},            # журнал уведомлений: {"<control_id>:<status>": "YYYY-MM-DD"}
    "notify_sound": True,        # звук уведомлений (winsound.MessageBeep)
    "extra_people": [],          # раунд 8: доп. ФИО в канонический справочник людей (редактируется в настройках)
    # Раунд 18 (задача 4): назначение людей в категории «исполнитель»/«контролёр».
    # {"Фамилия И.О.": ["executor"] | ["controller"] | ["executor", "controller"]}
    "person_roles": {},
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
        raw_controls = list(data.get("controls", []) or [])
        healed = _heal_missing_ids(raw_controls)
        controls = [Control.from_dict(d) for d in raw_controls]
        _migrate(version, controls)
        if healed:
            # Раунд 22: вылеченные id фиксируем сразу, иначе from_dict выдавал
            # бы случайный uuid на КАЖДОМ запуске и вложения отвязывались вновь.
            try:
                save_controls(controls)
            except (PermissionError, OSError) as e:
                print(f"[CONTROLS_DATA] healed ids save error: {e}")
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


def _make_backup(file_path: Path, keep: int = 3, prefix: Optional[str] = None) -> None:
    """Создать .bak копию перед перезаписью (last-write-wins + резерв).

    Аудит сети (раунд 30): штемпель с микросекундами (%f) — два клиента,
    писавшие в shared в одну секунду, больше не «перетирают» бэкап друг друга;
    перед копированием старые бэкапы подрезаются до `keep` штук (раньше в
    общей папке они копились бесконечно на каждой записи каждого админа).
    """
    try:
        if file_path.exists():
            prefix = prefix or f"{file_path.name}.bak"
            backups = sorted(file_path.parent.glob(f"{prefix}.*"))
            for old in backups[:max(0, len(backups) - keep + 1)]:
                try:
                    old.unlink()
                except OSError:
                    pass
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            for attempt in range(3):
                try:
                    shutil.copy2(file_path, file_path.with_name(f"{prefix}.{stamp}"))
                    break
                except OSError:
                    if attempt == 2:
                        raise
                    time.sleep(0.1)
    except OSError as e:
        print(f"[CONTROLS_DATA] Backup error: {e}")


def _migrate(version: int, controls: List[Control]) -> None:
    """Миграция формата при будущих версиях схемы."""
    # Поля schema v2 (end_date, milestones, attachments, archived, ...)
    # обрабатываются Control.from_dict с дефолтами, отдельная миграция не нужна.
    pass


def _attachments_prefix(attachments) -> Optional[str]:
    """Общий префикс-папка вложений вида `<id>/<файл>` (или None, если его нет
    или префиксы различаются). Раунд 22: у контроля без id папка уже создана —
    переиспользуем её имя как id, чтобы уже скопированные файлы не «потерялись»."""
    prefixes = []
    for rel in attachments or []:
        parts = str(rel).split("/")
        if len(parts) >= 2 and parts[0]:
            prefixes.append(parts[0])
    uniq = sorted(set(prefixes))
    return uniq[0] if len(uniq) == 1 else None


def _heal_missing_ids(raw_controls: List[dict]) -> bool:
    """Раунд 22 (задачи 2/3/5): импорт раундов ≤21 добавлял контроли с
    id=None («будет сгенерирован» — но нигде не генерировался). Такой контроль:
    - ломал вложения (TypeError Path/None, файл копировался в папку случайного
      uuid из detail_state и потом «не находился»);
    - «задваивал» строки при сохранении (state-поиск `x.id == c.id` матчил
      ПЕРВЫЙ None с None — чужую карточку);
    - блокировал «Сохранить» вместе с пустой датой поступления.
    Здесь id назначается: из общей папки вложений, если она есть (файлы
    остаются на месте и вновь связаны с контролем), иначе — новый uuid.
    Возвращает True, если хотя бы один id назначен (вызывающий сохраняет).
    """
    if not isinstance(raw_controls, list):
        return False
    used = set()
    for d in raw_controls:
        cid = (d or {}).get("id") if isinstance(d, dict) else None
        if cid:
            used.add(str(cid))
    changed = False
    for d in raw_controls:
        if not isinstance(d, dict) or d.get("id"):
            continue
        cand = _attachments_prefix(d.get("attachments"))
        if not cand or cand in used:
            cand = str(uuid4())
        d["id"] = cand
        used.add(cand)
        changed = True
    return changed


def ensure_control_id(control: Control) -> bool:
    """Раунд 22: контролю БЕЗ id присвоить id (из папки вложений — файлы
    остаются связанными — либо новый uuid). True, если id был назначен.

    Используется UI как страховка (открытие/сохранение карточки): в persisted
    данных None-контроли лечатся в load_controls (_heal_missing_ids), здесь —
    живые объекты, добавленные старым импортом в текущей сессии."""
    if control is None or control.id:
        return False
    control.id = _attachments_prefix(control.attachments) or str(uuid4())
    return True


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
        # Раунд 35 (задача 1.2): сетевой режим включаем по умолчанию.
        # Ключ ОТСУТСТВУЕТ в файле (старая установка) -> True и сохранить.
        # Явный False в файле (в т.ч. тестовые изоляции) НЕ перезаписываем —
        # пользователь мог осознанно отключить сеть, а тесты полагаются
        # на изоляцию.
        if "network_enabled" not in settings:
            settings["network_enabled"] = True
            try:
                save_settings(settings)
            except Exception:
                pass
        # Раунд 29 (задача 4) + раунд 31 (задача 2): ПУСТОЙ путь или путь
        # внутри локального хранилища приложения (%APPDATA%\porayonka) —
        # подставить дефолтный сетевой путь и СОХРАНИТЬ настройки (миграция).
        # Произвольные локальные пути (`C:\\SomeFolder\\share`) НЕ трогаем:
        # они могут быть тестовыми temp-каталогами или намеренным выбором
        # пользователя. Явный UNC-путь (`\\\\server\\share\\...`) сохраняем.
        sp = (settings.get("network_shared_path") or "").strip()
        _data_dir = str(get_data_path()).lower().rstrip("\\/") + os.sep
        _sp_lower = sp.lower()
        _is_appdata_local = bool(sp and _sp_lower.startswith(_data_dir))
        if not sp or _is_appdata_local:
            settings["network_shared_path"] = DEFAULT_NETWORK_PATH
            try:
                save_settings(settings)
            except Exception:
                pass
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


def get_all_people_names(settings: Optional[dict] = None) -> List[str]:
    """Полный канонический список людей справочника:
    криминалисты + дефолтные контролёры + доп. ФИО из настроек (`extra_people`),
    без дублей по фамилии.
    Раунд 13: базовые ФИО, переименованные/удалённые через справочники,
    исключаются списком `hidden_people`.
    Раунд 18 (задача 4): роли НЕ фильтруются здесь — это объединение;
    разделённые списки — get_executor_names()/get_controller_names()."""
    extra = []
    hidden = set()
    if settings:
        extra = list(settings.get("extra_people", []) or [])
        # Раунд 21 (задача 1): сравнение с нормализацией пробелов (`_person_norm`)
        # — двойной пробел в записи hidden_people больше не даёт «вечную» скрытую
        # запись, которую невозможно снять добавлением.
        hidden = {_person_norm(h).casefold() for h in (settings.get("hidden_people", []) or [])}
    out = []
    seen = set()
    for n in get_criminalists_only() + list(DEFAULT_CONTROLLERS) + extra:
        if _person_norm(n).casefold() in hidden:
            continue
        surname = (n.strip().split()[0] if n.strip() else "").casefold()
        if not surname or surname in seen:
            continue
        seen.add(surname)
        out.append(n)
    return out


# ── Раунд 18 (задача 4): роли «исполнитель/контролёр» ─────────────────────
VALID_PERSON_ROLES = ("executor", "controller")


def _role_key(roles: dict, name: str) -> Optional[str]:
    """Найти ключ словаря ролей по имени без учёта регистра."""
    cf = (name or "").strip().casefold()
    for k in roles:
        if (k or "").strip().casefold() == cf:
            return k
    return None


def get_person_roles(settings: Optional[dict]) -> dict:
    """Эффективные роли всех людей справочника: {ФИО: ["executor", "controller"]}.

    Дефолты (если в person_roles записи нет) — ПО ФАМИЛИИ, роли источников
    суммируются: человек может быть одновременно в нескольких источниках
    (напр., криминалист «Чашин Эдуард Александрович» и дефолтный контролёр
    «Чашин Э.А.» — одно лицо; get_all_people_names дедуплицирует их по фамилии
    в одну запись):
      - базовые криминалисты        -> роль "executor"
      - дефолтные контролёры        -> роль "controller"
      - доп. ФИО (`extra_people`)   -> роль "executor" (раунд 30, задача 3:
        раньше «обе роли» — из-за этого импортированные исполнители попадали
        в dropdown «За кем контроль»; контролёрская роль — только ЯВНЫМ
        назначением в справочнике или DEFAULT_CONTROLLERS)
    Без дефолта (теоретически) — обе роли. Явные назначения из
    settings["person_roles"] (по точному имени записи справочника) перекрывают
    дефолты полностью — так снимается и роль-умолчание.
    """
    settings = settings or {}
    defaults: Dict[str, List[str]] = {}

    def _put(name: str, role: str) -> None:
        nm = (name or "").strip()
        if not nm:
            return
        sur = nm.split()[0].casefold()
        if not sur:
            return
        cur = defaults.setdefault(sur, [])
        if role not in cur:
            cur.append(role)

    for n in get_criminalists_only():
        _put(n, "executor")
    for n in DEFAULT_CONTROLLERS:
        _put(n, "controller")
    for n in (settings.get("extra_people", []) or []):
        # Раунд 30 (задача 3): extra_people по умолчанию — ТОЛЬКО исполнитель.
        # Контролёр — только явным назначением person_roles (backward
        # compatibility: явные назначения ниже перекрывают дефолт).
        _put(n, "executor")
    out = {}
    # порядок канонический — как в get_all_people_names
    for n in get_all_people_names(settings):
        nm = n.strip()
        sur = nm.split()[0].casefold() if nm else ""
        out[n] = list(defaults.get(sur) or ["executor", "controller"])
    for k, v in (settings.get("person_roles") or {}).items():
        ck = (k or "").strip().casefold()
        if not ck:
            continue
        clean = [r for r in (v or []) if r in VALID_PERSON_ROLES]
        for name in out:
            if name.strip().casefold() == ck:
                out[name] = clean
                break
    return out


def set_person_roles(settings: dict, name: str, roles: List[str]) -> bool:
    """Назначить роли человеку и сохранить настройки (пишем всегда — даже пустой
    список, чтобы явный сброс дефолта переживал рестарт)."""
    name = (name or "").strip()
    if not name:
        return False
    clean = [r for r in dict.fromkeys(roles or []) if r in VALID_PERSON_ROLES]
    pr = dict(settings.get("person_roles") or {})
    # ключ — с точным написанием существующей записи, если есть (не плодим дубли)
    existing_key = _role_key(pr, name)
    if existing_key is not None and existing_key != name:
        pr.pop(existing_key, None)
    pr[name] = clean
    settings["person_roles"] = pr
    save_settings(settings)
    return True


def get_executor_names(settings: Optional[dict] = None) -> List[str]:
    """Раунд 18: канонический список ИСПОЛНИТЕЛЕЙ (роль executor)."""
    return [n for n, r in get_person_roles(settings).items() if "executor" in r]


def get_controller_names(settings: Optional[dict] = None) -> List[str]:
    """Канонический список КОНТРОЛЁРОВ (роль controller).

    До раунда 18 возвращал объединённый справочник людей; теперь — только
    контролёров. Умолчания: дефолтные контролёры + extra_people; криминалист,
    чья фамилия совпадает с дефолтным контролёром («Чашин Эдуард Александрович»
    / «Чашин Э.А.»), получает обе роли одной записью (см. get_person_roles).
    """
    return [n for n, r in get_person_roles(settings).items() if "controller" in r]


def rename_person(settings: dict, old: str, new: str) -> bool:
    """Раунд 13: переименовать запись справочника людей.

    Если `old` — доп. ФИО (extra_people), заменяется там. Если `old` — базовое
    ФИО (криминалист/контролёр), новое значение добавляется в extra_people,
    а базовое скрывается через hidden_people. Сохраняет настройки.
    """
    old = (old or "").strip()
    new = (new or "").strip()
    if not old or not new or old.casefold() == new.casefold():
        return False
    cur = list(settings.get("extra_people", []) or [])
    hidden = list(settings.get("hidden_people", []) or [])
    replaced = False
    nxt = []
    for x in cur:
        if not replaced and (x or "").strip().casefold() == old.casefold():
            nxt.append(new)
            replaced = True
        else:
            nxt.append(x)
    if replaced:
        hidden = [h for h in hidden if (h or "").strip().casefold() != old.casefold()]
    else:
        if not any((x or "").strip().casefold() == new.casefold() for x in nxt):
            nxt.append(new)
        if not any((h or "").strip().casefold() == old.casefold() for h in hidden):
            hidden.append(old)
    settings["extra_people"] = nxt
    settings["hidden_people"] = hidden
    # Раунд 18 (задача 4): назначенные роли переезжают на новое имя
    pr = dict(settings.get("person_roles") or {})
    old_key = _role_key(pr, old)
    if old_key is not None:
        roles_of_old = pr.pop(old_key)
        new_key = _role_key(pr, new)
        if new_key is None:
            pr[new] = roles_of_old
        settings["person_roles"] = pr
    save_settings(settings)
    return True


def remove_person(settings: dict, name: str) -> bool:
    """Раунд 13: убрать ФИО из справочника людей: доп. — из extra_people,
    базовое — в hidden_people. Сохраняет настройки."""
    name = (name or "").strip()
    if not name:
        return False
    cur = list(settings.get("extra_people", []) or [])
    nxt = [x for x in cur if (x or "").strip().casefold() != name.casefold()]
    hidden = list(settings.get("hidden_people", []) or [])
    if len(nxt) != len(cur):
        hidden = [h for h in hidden if (h or "").strip().casefold() != name.casefold()]
    elif not any((h or "").strip().casefold() == name.casefold() for h in hidden):
        hidden.append(name)
    else:
        return False
    settings["extra_people"] = nxt
    settings["hidden_people"] = hidden
    # Раунд 18 (задача 4): вычищаем назначение ролей удалённого человека
    pr = dict(settings.get("person_roles") or {})
    old_key = _role_key(pr, name)
    if old_key is not None:
        pr.pop(old_key, None)
        settings["person_roles"] = pr
    save_settings(settings)
    return True


def rename_initiator(settings: dict, old: str, new: str) -> bool:
    """Раунд 13: переименовать запись справочника инициаторов.

    Пользовательский (custom_initiators) заменяется напрямую. Производный
    канонический кластер («ГУК» из «ГУК СК» и т.п.) переименовывается на
    уровне отображения: settings["init_renames"][old] = new — опции фильтра
    показывают new, а сопоставление контролей идёт по канону old
    (см. initiator_filter_group). Сохраняет настройки.
    """
    old = (old or "").strip()
    new = (new or "").strip()
    if not old or not new or old == new:
        return False
    cur = list(settings.get("custom_initiators", []) or [])
    if old in cur:
        settings["custom_initiators"] = [new if x == old else x for x in cur]
        save_settings(settings)
        return True
    renames = dict(settings.get("init_renames", {}) or {})
    # повторное переименование уже переименованного — тянем исходный ключ
    for k, v in list(renames.items()):
        if v == old:
            del renames[k]
            old = k
            break
    renames[old] = new
    settings["init_renames"] = renames
    save_settings(settings)
    return True


def remove_initiator(settings: dict, name: str) -> bool:
    """Раунд 13: убрать инициатор из справочника: пользовательский — из
    custom_initiators; производный кластер — скрывается через
    hidden_init_groups. Сохраняет настройки."""
    name = (name or "").strip()
    if not name:
        return False
    cur = list(settings.get("custom_initiators", []) or [])
    if name in cur:
        settings["custom_initiators"] = [x for x in cur if x != name]
        save_settings(settings)
        return True
    hidden = list(settings.get("hidden_init_groups", []) or [])
    renames = dict(settings.get("init_renames", {}) or {})
    renames.pop(name, None)
    if name not in hidden:
        hidden.append(name)
    settings["hidden_init_groups"] = hidden
    settings["init_renames"] = renames
    save_settings(settings)
    return True


def _person_norm(name: str) -> str:
    """Нормализация ФИО для сравнений: схлопнуть множественные пробелы, trim."""
    return " ".join((name or "").split())


def add_extra_person(settings: dict, name: str) -> bool:
    """Добавить ФИО в справочник людей (`extra_people`). True, если человек
    появился в справочнике (добавлен в extra ИЛИ снято скрытие с базового).

    Раунд 20 (задача 4): добавление СНИМАЕТ скрытие (`hidden_people`) с того же
    ФИО.
    Раунд 21 (задача 1): скрытие снимается СНАЧАЛА — до проверки дубликата.
    На машине пользователя сложилась пара «ФИО есть в extra_people И то же ФИО
    в hidden_people» (добавление раундом 19, когда unhide ещё не было): dupe-
    check возвращал False ДО снятия скрытия — восстановить «Гайнутдинова
    Станислава Игоревича» через «Добавить» было невозможно («физически
    добавляешь, но в списке не появляется»). Короткая форма «Гайнутдинов С.И.»
    добавлялась — дубликата/скрытия для неё не было, что и подтвердило
    механику. Плюс нормализация пробелов (`_person_norm`) в сравнениях —
    случайный двойной пробел больше не обходит скрытие."""
    name = _person_norm(name)
    if not name:
        return False
    changed = False
    hidden = list(settings.get("hidden_people", []) or [])
    nxt_hidden = [h for h in hidden if _person_norm(h).casefold() != name.casefold()]
    if len(nxt_hidden) != len(hidden):
        settings["hidden_people"] = nxt_hidden
        changed = True
    cur = list(settings.get("extra_people", []) or [])
    if not any(name.casefold() == _person_norm(x).casefold() for x in cur):
        cur.append(name)
        settings["extra_people"] = cur
        changed = True
    if changed:
        save_settings(settings)
        return True
    return False


def remove_extra_person(settings: dict, name: str) -> bool:
    """Убрать ФИО из справочника людей. True, если удалено."""
    cur = list(settings.get("extra_people", []) or [])
    nxt = [x for x in cur if x.strip().casefold() != (name or "").strip().casefold()]
    if len(nxt) == len(cur):
        return False
    settings["extra_people"] = nxt
    save_settings(settings)
    return True


# ────────────────────────────────────────────────
# ИНИЦИАТОРЫ: КАНОНИЧЕСКАЯ КЛАСТЕРИЗАЦИЯ (фильтр)
# ────────────────────────────────────────────────

# Токены-«шум» в хвосте инициатора: не меняют каноническую группу
_INITIATOR_NOISE = {"ск", "с", "рф", "у", "к"}


def _initiator_tokens(raw: str) -> List[str]:
    """Токены инициатора: casefold, разделители → пробелы, точки убраны."""
    s = (raw or "").casefold().replace(".", " ").replace("/", " ").replace("-", " ").replace(",", " ")
    return [t for t in s.split() if t]


# Известные канонические инициаторы (для разбиения склеек и приоритета)
_KNOWN_INITIATOR_ROOTS = ["гук", "су", "ск", "пск", "гсу", "окрим", "мвд", "следственный комитет",
                          "гук юфо", "гук ск", "гук рф", "ск рф", "следком"]


def canonical_initiator_group(raw: str) -> str:
    """Каноническая «группа» инициатора (нижний регистр, токены через пробел).

    Схлопывает варианты написания одного инициатора:
      «ГУК С.», «ГУК СК», «ГУК С.Т.С.А.С.И.Ю.» → «гук»;
      «СУ/СК», «СУ СК» → «су»;
      «ГУК ЮФО» остаётся «гук юфо» (не схлопывается в «гук»).
    Склейки нескольких инициаторов («ГУК СК ГУК ЮФО», «ГСУ ГУК») разбиваются
    на составляющие: возвращается список канонов через запятую (это значение
    используется в опциях фильтра как отдельные пункты).
    Значения, не похожие ни на один известный шаблон, возвращаются как есть
    (нормализованные) — они становятся собственными канонами фильтра.
    """
    rt = _initiator_tokens(raw)
    if not rt:
        return ""

    def _canon_one(tokens: List[str]) -> str:
        first = tokens[0]
        tail = tokens[1:]
        if first == "гук":
            if not tail:
                return "гук"
            if all(len(t) == 1 or t in _INITIATOR_NOISE for t in tail):
                return "гук"
            # «гук юфо» / «гук ск» — составной, но осмысленный канон
            return " ".join(tokens)
        if first == "су" and all(t in ("ск", "с") for t in tail):
            return "су"
        if tail and all(len(t) == 1 for t in tail):
            return first
        return " ".join(tokens)

    # Разбиение склейки: ищем в списке токенов позиции, где начинается
    # известный корень инициатора (длина >= 2, чтобы не резать «ГУК С.»).
    groups = []
    cur = []
    for t in rt:
        if cur and t in ("гук", "су", "пск", "гсу", "окрим", "мвд") and len(t) >= 2:
            groups.append(_canon_one(cur))
            cur = [t]
        else:
            cur.append(t)
    if cur:
        groups.append(_canon_one(cur))
    if len(groups) > 1:
        # «ГСУ ГУК» → «гсу,гук»; «ГУК СК ГУК ЮФО» → «гук,гук юфо»
        return ",".join(dict.fromkeys(groups))
    return groups[0] if groups else ""


def initiator_filter_options(raw_values, settings=None) -> List[str]:
    """Канонические опции фильтра «Инициаторы» (заглавными, без дублей, по алфавиту).

    Принимает все исходные значения (дефолтные + custom + distinct из данных),
    кластеризует их в группы и возвращает display-форму (upper).
    Склейки разбиваются на отдельные каноны («ГУК СК ГУК ЮФО» → «ГУК», «ГУК ЮФО»).
    Раунд 13: при переданных settings применяются правки справочника —
    скрытые кластеры (hidden_init_groups) убираются, переименованные
    (init_renames) показываются под новым именем.
    """
    groups = {}
    for v in raw_values or []:
        g = canonical_initiator_group(v)
        if not g:
            continue
        for part in g.split(","):
            part = part.strip()
            if not part:
                continue
            display = " ".join(t.upper() for t in part.split())
            if display not in groups:
                groups[display] = True
    if settings:
        hidden = set(settings.get("hidden_init_groups", []) or [])
        renames = dict(settings.get("init_renames", {}) or {})
        out = set()
        for display in groups:
            if display in hidden:
                continue
            out.add(renames.get(display, display))
        return sorted(out)
    return sorted(groups.keys())


def initiator_filter_group(value: str, settings=None) -> str:
    """Раунд 13: каноническая группа для ВЫБРАННОГО значения фильтра с учётом
    переименований справочника: новое display-имя сопоставляется по канону
    исходного кластера («ГУК РОСТОВ» -> канон «ГУК»)."""
    val = (value or "").strip()
    if settings and val:
        renames = dict(settings.get("init_renames", {}) or {})
        for old, new in renames.items():
            if val == (new or "").strip():
                return canonical_initiator_group(old)
    return canonical_initiator_group(val)


def get_criminalist_short_names() -> List[str]:
    """Сокращённые ФИО криминалистов («Семисенко И.Ю.»)."""
    return [short_name(n) for n in get_criminalist_names()]


def get_initiators(settings: dict) -> List[str]:
    """Список инициаторов: встроенные + пользовательские из настроек.
    Раунд 13: правки справочника (переименование/скрытие кластеров) применяются
    на уровне опций фильтра — см. initiator_filter_options(settings=...)."""
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
    """Локальный абсолютный путь вложения по относительному пути.

    Раунд 22 (задача 5): пустой/None control_id — сразу None: раньше здесь
    падал TypeError Path/None при работе с контролем без id (лог пользователя:
    delete_attachment -> get_attachment_dir(None))."""
    if not control_id:
        return None
    safe = Path(rel_path).name
    return get_attachment_dir(control_id) / safe if safe else None


def _win_sharing_error(e: OSError) -> bool:
    """True — ошибка «файл временно занят» (Windows: антивирус/индексатор
    держит свежесозданный файл): PermissionError, WinError 5/32/33.

    На Windows с Windows Defender/антивирусом свежий tmp-файл на короткое
    время (десятки-сотни мс) открывается сторонним процессом эксклюзивно:
    os.replace() и unlink() над ним падают PermissionError (WinError 32).
    Именно этот отказ рождал детект stress-аудита раунда 38 (Windows,
    4 из 4): shared-публикация не прошла, copy_attachment_to_shared вернул
    None, вызывающая сторона ушла в ЛОКАЛЬНЫЙ фолбэк — вложение появилось
    в модели, а в shared остался осиротевший .tmp и не было финального
    файла. PermissionError на других ОС тоже ретраим (NFS-глитчи).
    """
    if isinstance(e, PermissionError):
        return True
    return getattr(e, "winerror", None) in (5, 32, 33)


def _try_unlink(tmp: Path) -> None:
    """Удалить tmp с ограниченными ретраями (Windows sharing-ошибки).

    Если удалить не удалось — не фатально: файл остаётся под скрытым
    tmp-именем (не повреждает финальное имя), а подчистит его sweeper
    (_sweep_stale_tmp) при следующих копированиях в ту же папку.
    """
    for pause in (0.0, 0.05, 0.15, 0.3):
        if pause:
            time.sleep(pause)
        try:
            tmp.unlink()
            return
        except FileNotFoundError:
            return
        except OSError as e:
            if not _win_sharing_error(e):
                return
    print(f"[CONTROLS_DATA] tmp left for sweeper: {tmp.name}")


# Осиротевшие tmp старше этого возраста — реликты прерванных внешне копий
# (kill процесса, обрыв сети). Активные tmp другого клиента младше порога
# не трогаем.
_TMP_SWEEP_AGE_SEC = 600


def _sweep_stale_tmp(target_dir: Path,
                     older_than_sec: int = _TMP_SWEEP_AGE_SEC) -> None:
    """Удалить старые осиротевшие .tmp в папке вложений (best effort)."""
    try:
        now = time.time()
        for p in target_dir.glob(".*.tmp"):
            try:
                if now - p.stat().st_mtime > older_than_sec:
                    p.unlink()
            except OSError:
                pass
    except OSError:
        pass


def _copy_atomic(src: Path, target_dir: Path, filename: str) -> bool:
    """Скопировать файл в target_dir АТОМАРНО: tmp-файл + os.replace.

    Аудит сети (раунд 30): раньше копия шла сразу под финальным именем —
    оборванная на полпути (сеть упала) копия оставляла БИТЫЙ файл, который
    resolve_attachment показывал вместо полного локального (shared приоритетнее
    локального). Теперь при сбое tmp удаляется, битого файла под финальным
    именем не остаётся. True — файл на месте и цел.

    Раунд 38 (fix stress 5c): os.replace и удаление tmp — с ОГРАНИЧЕННЫМИ
    ретраями при sharing-ошибках Windows (антивирус держит свежий tmp;
    см. _win_sharing_error). Паузы суммарно < ~1.6 c и потому допустимы:
    крупные файлы копируются в фоновом потоке (см. _ATTACH_ASYNC_MB), а
    ретрай нужен только при реальном отказе. Без ретраев единичный отказ
    антивируса откатывал публикацию в shared и уводил вложение в локальную
    копию, оставляя в shared осиротевший .tmp (модель опережала публикацию).
    """
    tmp = target_dir / f".{filename}.{uuid4().hex}.tmp"
    try:
        shutil.copy2(src, tmp)
    except OSError as e:
        print(f"[CONTROLS_DATA] copy attachment error: {e}")
        _try_unlink(tmp)
        return False
    last: Optional[OSError] = None
    for pause in (0.0, 0.05, 0.1, 0.2, 0.4, 0.8):
        if pause:
            time.sleep(pause)
        try:
            os.replace(tmp, target_dir / filename)
            return True
        except OSError as e:
            last = e
            if not _win_sharing_error(e):
                break
    print(f"[CONTROLS_DATA] publish attachment error: {last}")
    _try_unlink(tmp)
    return False


def copy_attachment_to_local(control_id: str, source_path: str) -> Optional[str]:
    """Скопировать файл в локальную папку вложений контроля.

    Возвращает относительный путь (`<control_id>/<filename>`) или None.
    Раунд 13: пустой control_id — сразу None (защита от TypeError Path/None).
    """
    if not control_id:
        return None
    try:
        src = Path(source_path)
        if not src.exists():
            return None
        target_dir = get_attachment_dir(control_id)
        _sweep_stale_tmp(target_dir)
        filename = _unique_filename(target_dir, src.name)
        if not _copy_atomic(src, target_dir, filename):
            return None
        return f"{control_id}/{filename}"
    except OSError as e:
        print(f"[CONTROLS_DATA] copy attachment error: {e}")
        return None


def copy_attachment_to_shared_ex(control_id: str, source_path: str,
                                 settings: dict) -> tuple:
    """Копирование в shared с ЯВНОЙ причиной отказа.

    Возвращает (rel_path | None, reason), reason:
      "ok"      — файл опубликован в shared (copy2 + os.replace прошли);
      "offline" — shared-папка недоступна (путь не задан / каталог
                  недостижим): вызывающая сторона вправе уйти в локальный
                  фолбэк (офлайн-режим, вложение доедет синхронизацией);
      "error"   — сеть ДОСТУПНА (каталог есть), но копия/публикация не
                  удалась: вложение НЕ прикреплять никуда — модель не
                  должна ссылаться на неопубликованный файл, а в shared не
                  должно оставаться осиротевшего .tmp (раунд 38, root cause
                  падения stress 5c на Windows: без различения причин
                  единичный отказ антивируса уводил вложение в локальную
                  копию, оставляя общий файл неопубликованным).
    """
    if not control_id:
        return None, "error"
    shared_dir = _shared_dir(settings)
    if shared_dir is None:
        return None, "offline"
    try:
        src = Path(source_path)
        target_dir = shared_dir / "controls_attachments" / control_id
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"[CONTROLS_DATA] shared attachments dir unavailable: {e}")
        return None, "offline"
    try:
        if not src.exists():
            return None, "error"
        _sweep_stale_tmp(target_dir)
        filename = _unique_filename(target_dir, src.name)
        if not _copy_atomic(src, target_dir, filename):
            return None, "error"
        return f"{control_id}/{filename}", "ok"
    except OSError as e:
        print(f"[CONTROLS_DATA] copy attachment to shared error: {e}")
        return None, "error"


def copy_attachment_to_shared(control_id: str, source_path: str, settings: dict) -> Optional[str]:
    """Скопировать файл в общую сетевую папку вложений.

    Возвращает относительный путь или None. Shared-папка определяется как
    родитель общей папки/файла (shared_dir/controls_attachments/...).
    Раунд 13: пустой control_id или недоступная shared-папка — сразу None,
    вызывающая сторона переходит на локальное копирование (без TypeError).
    Аудит сети: копирование атомарное (_copy_atomic) — обрыв сети на полпути
    не оставляет битого файла под финальным именем. Нужна причина отказа —
    см. copy_attachment_to_shared_ex.
    """
    rel, _reason = copy_attachment_to_shared_ex(control_id, source_path, settings)
    return rel


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
    """Разрешить путь вложения: сначала общая папка, затем локально.

    Раунд 22 (задача 5): без id контроля — None (никаких TypeError)."""
    if not control_id:
        return None
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
    """Удалить файл вложения (локально и из общей папки).

    Раунд 22 (задача 5): без id контроля файл на диске определить нельзя —
    молча выходим (UI при этом убирает вложение из списка)."""
    if not control_id:
        return
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
    """Удалить папку вложений контроля (локально и в общей папке).

    Раунд 22 (задача 5): без id — молча выходим (TypeError Path/None)."""
    if not control_id:
        return
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
    """Ключ сравнения updated_at: валидная ISO-строка новее пустого/битого значения.

    Аудит сети (раунд 30): naive-ISO (datetime.now().isoformat()) трактуется
    как UTC, а не как ЛОКАЛЬНОЕ время машины. Раньше каждая машина считала
    epoch по своему часовому поясу: один и тот же файл давал разные результаты
    merge на разных ПК (недетерминизм при рассинхроне часовых поясов). В одном
    поясе поведение не изменилось (все сдвиги одинаковы, порядок сохраняется).
    """
    raw = (control.updated_at or "").strip()
    if not raw:
        return (0, "", "")
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (1, dt.timestamp(), raw)
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
    data = None
    last_err = None
    for attempt in range(3):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            break
        except (json.JSONDecodeError, OSError, ValueError) as e:
            last_err = e
            if attempt == 2:
                break
            time.sleep(0.1)
    if data is None:
        if last_err is not None:
            print(f"[CONTROLS_DATA] Oshibka chteniya obshego fayla: {last_err}")
        return []
    try:
        return [Control.from_dict(d) for d in data.get("controls", [])]
    except (ValueError, TypeError) as e:
        print(f"[CONTROLS_DATA] Oshibka chteniya obshego fayla: {e}")
        return []


_SHARED_WRITE_LOCK = threading.RLock()


def write_shared_controls(controls: List[Control], settings: dict) -> bool:
    """Записать контроли в общий сетевой файл. Возвращает успех.

    Аудит сети (раунд 30): tmp-файл УНИКАЛЕН (uuid) — раньше все клиенты
    писали в один и тот же `controls.json.tmp`: при одновременной записи двух
    админов открытие файла вторым усекало данные первого, а os.replace мог
    переименовать tmp, пока второй ещё писал в него (запись молча уходила в
    «никуда», хотя функция возвращала True). Атомарность os.replace
    сохранена. Бэкапы подрезаются до 5 (см. _make_backup).

    На Windows `os.replace` может вернуть WinError 5 (Access denied), если
    целевой файл в этот момент читается/блокируется другим клиентом или
    антивирусом. Поэтому — 3 попытки с короткой задержкой.
    """
    p = _parse_shared_path(settings)
    if not p:
        return False
    # В одном экземпляре приложения запись может прийти одновременно из UI и
    # polling-потока. Сериализация охватывает backup и replace: иначе Windows
    # иногда возвращает WinError 5 при взаимном открытии целевого файла.
    # Межпроцессный контур сохраняется: уникальный tmp + retry ниже.
    with _SHARED_WRITE_LOCK:
        tmp = None
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "schema_version": SCHEMA_VERSION,
                "last_saved": datetime.now().isoformat(),
                "controls": [c.to_dict() for c in controls],
            }
            if p.exists():
                _make_backup(p, keep=5)
            tmp = p.with_name(f"{p.name}.{uuid4().hex}.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            for attempt in range(3):
                try:
                    os.replace(tmp, p)  # атомарная замена
                    return True
                except OSError:
                    if attempt == 2:
                        raise
                    time.sleep(0.15)
        except OSError as e:
            print(f"[CONTROLS_DATA] Oshibka zapisi v obshiy fayl: {e}")
            if tmp is not None:
                try:
                    tmp.unlink()
                except OSError:
                    pass
            return False
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
    """Подтянуть недостающие вложения из общей папки локально.

    Аудит сети: копирование атомарное (_copy_atomic) — обрыв сети на полпути
    не оставляет битого локального файла.
    """
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
        _copy_atomic(shared_file, get_attachment_dir(control_id), Path(rel).name)


# Раунд 30 (задача 5): порог предупреждения о расхождении часов. Сравнение
# идёт не с «возрастом» файла, а между mtime и last_saved внутри JSON (см.
# check_time_skew): при точных часах расхождение ~0 даже если файл давно не
# менялся; при сбитых часах — заметно больше порога.
TIME_SKEW_WARN_SEC = 1800.0  # 30 минут


def check_time_skew(settings: dict,
                    tolerance_sec: float = TIME_SKEW_WARN_SEC) -> Optional[float]:
    """Раунд 29 (задача 7) + раунд 30 (задача 5): расхождение часов ЭТОГО ПК
    с часами машины, писавшей общий файл (секунды, по модулю), или None, если
    проверка невозможна (сеть выключена, shared отсутствует/недоступен, нет
    last_saved в файле).

    КАК РАБОТАЕТ: сравниваются НЕ `now` и mtime (это давало false positive:
    файл, который просто давно не менялся, выглядел как «сбитые часы» — скрин
    «Сообщение о неверном времени, хотя по факту время правильное.png»), а:
      - mtime файла — время последней записи в шкале ЭТОГО ПК;
      - last_saved (ISO внутри controls.json) — время той же записи по часам
        машины-писателя.
    При точных часах (и одном часовом поясе — обычная локальная сеть отдела)
    обе величины совпадают с точностью до секунд — предупреждения нет, даже
    если файл не менялся сутками. Если часы ПК сбиты — расхождение заметно
    превышает порог (удваивается из-за интерпретации naive-ISO в локальной
    шкале, поэтому порог 30 минут: плавающие ±2–3 минуты не тревожат).

    last_saved отсутствует (файл старого формата) — None: надёжно проверить
    нельзя, не блокируем запуск.
    """
    if not settings.get("network_enabled"):
        return None
    p = _parse_shared_path(settings)
    if not p or not p.exists():
        return None
    try:
        mtime = p.stat().st_mtime
    except OSError:
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        last_saved = (data or {}).get("last_saved") or ""
        if not last_saved:
            return None
        dt = datetime.fromisoformat(str(last_saved))
        if dt.tzinfo is not None:
            last_ts = dt.timestamp()
        else:
            # naive-ISO: локальное время писавшего ПК; в одной организации
            # пояса совпадают — интерпретация в НАШЕЙ локальной шкале даёт
            # сравнимую с mtime величину
            last_ts = dt.timestamp()
        return abs(mtime - last_ts)
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        return None


def sync_local_attachments_to_shared(controls: List["Control"], settings: dict) -> int:
    """Раунд 29 (задача 9): выгрузить в общую папку локальные вложения,
    которых там ещё нет (прикреплённые, пока сеть была недоступна).

    Проходит по спискам вложений контролей; если файл есть локально, но
    отсутствует в shared/controls_attachments/<id>/ — копирует. Возвращает
    число выгруженных файлов. Shared недоступен / сеть выключена — мягкий 0.
    """
    if not settings.get("network_enabled"):
        return 0
    shared_dir = _shared_dir(settings)
    if shared_dir is None:
        return 0
    uploaded = 0
    for c in controls or []:
        cid = getattr(c, "id", None)
        if not cid:
            continue
        for rel in (c.attachments or []):
            name = Path(str(rel)).name
            if not name:
                continue
            try:
                shared_file = shared_dir / "controls_attachments" / cid / name
                if shared_file.exists():
                    continue
                local = get_attachment_source_path(cid, rel)
                if not (local and local.exists()):
                    continue
                shared_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(local, shared_file)
                uploaded += 1
            except OSError:
                # сеть отвалилась на середине — догрузим в следующий цикл
                return uploaded
    return uploaded

# core/backup.py
# Раунд 38 (P1, задача 8): ежедневное резервное копирование БЕЗ заморозки UI.
#
# Прежний _make_backup() создавал лишь 3/5 копий JSON перед перезаписью —
# это не ежедневный полный backup и не защищает вложения.
#
# Здесь:
#   * maybe_daily_local_backup()  — полный локальный снапшот пользовательских
#     JSON (departments, zonal, настройки, edition, контроли) + папок
#     templates/ и controls_attachments/. Не чаще одной УСПЕШНОЙ копии за
#     календарный день; вызывать при старте и периодически (приложение может
#     жить в трее несколько дней).
#   * maybe_daily_shared_backup(settings, is_admin) — централизованный снапшот
#     shared controls.json + controls_attachments в <workspace>/backups/
#     ТОЛЬКО у admin-редакции (user никогда не создаёт и не удаляет общие
#     резервные копии).
#   * Снапшот пишется во временный каталог и АТОМАРНО публикуется
#     (os.replace/переименование); частичная ошибка — день НЕ отмечается
#     успешным, предыдущий валидный снапшот не трогается.
#   * manifest.json: дата, версия схемы, список файлов/размеров + SHA256
#     критичных JSON.
#   * Межпроцессный lock (.lock-файл O_EXCL) — одновременный backup из
#     нескольких Flet-session web-процесса не запускается.
#   * Retention: 30 ежедневных копий (BACKUP_RETENTION), сам каталог backups/
#     рекурсивно не включается, temp/lock/лог-файлы не копируются.
import hashlib
import json
import os
import shutil
import time
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from .controls_data import SCHEMA_VERSION, get_data_path, _shared_dir

BACKUP_RETENTION = 30           # ежедневных копий на машину
_LOCK_STALE_SEC = 2 * 3600      # lock старше 2 часов считаем «мёртвым»

# Пользовательские JSON-файлы, входящие в локальный снапшот
_LOCAL_JSON = [
    "departments.json",
    "zonal_collection.json",
    "zonal_criminalists.json",
    "controls.json",
    "controls_settings.json",
    "edition.json",
]
# Каталоги локального снапшота
_LOCAL_DIRS = ["templates", "controls_attachments"]
# Логи/служебные — НЕ копируем (бесконечно растут и не являются данными)
_SKIP_FILES = {"error.log", "web_startup.log", "edition_debug.log"}


# ────────────────────────────────────────────────
# ВНУТРЕННИЕ УТИЛИТЫ
# ────────────────────────────────────────────────

def _sha256(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _today_str(today: Optional[date]) -> str:
    return (today or date.today()).isoformat()


def _acquire_lock(lock_path: Path) -> bool:
    """Межпроцессный lock через O_EXCL. Мёртвый lock (>2ч) перезахватываем."""
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    for _ in range(2):
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, json.dumps({
                    "pid": os.getpid(),
                    "ts": time.time(),
                }).encode("ascii"))
            finally:
                os.close(fd)
            return True
        except FileExistsError:
            try:
                stale = time.time() - lock_path.stat().st_mtime > _LOCK_STALE_SEC
            except OSError:
                stale = False
            if stale:
                try:
                    lock_path.unlink()
                    continue
                except OSError:
                    pass
            return False
        except OSError:
            return False
    return False


def _release_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except OSError:
        pass


def _collect_manifest(base: Path, stamp: str) -> dict:
    """Манифест опубликованного снапшота: дата, схема, файлы/размеры, SHA256
    критичных JSON."""
    files: List[dict] = []
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(base).as_posix()
        try:
            size = p.stat().st_size
        except OSError:
            size = -1
        entry = {"path": rel, "size": size}
        if p.suffix.lower() == ".json":
            entry["sha256"] = _sha256(p)
        files.append(entry)
    return {
        "date": stamp,
        "created_at": datetime.now().isoformat(),
        "schema_version": SCHEMA_VERSION,
        "app": "porayonka",
        "files": files,
    }


def _publish_snapshot(tmp_dir: Path, target_dir: Path) -> bool:
    """Атомарная публикация: переименование tmp -> target."""
    try:
        if target_dir.exists():
            # повторный снапшот того же дня (маркер утерян) — заменяем целиком
            shutil.rmtree(target_dir)
        os.replace(str(tmp_dir), str(target_dir))
        return True
    except OSError as e:
        print(f"[BACKUP] publish error: {e}")
        try:
            shutil.rmtree(tmp_dir)
        except OSError:
            pass
        return False


def _enforce_retention(root: Path, keep: int = BACKUP_RETENTION) -> None:
    """Оставить не более keep дневных снапшотов (YYYY-MM-DD)."""
    try:
        days = sorted(p.name for p in root.iterdir()
                      if p.is_dir() and _is_day_name(p.name))
    except OSError:
        return
    for old in days[:max(0, len(days) - keep)]:
        try:
            shutil.rmtree(root / old)
        except OSError as e:
            print(f"[BACKUP] retention error: {e}")


def _is_day_name(name: str) -> bool:
    try:
        date.fromisoformat(name)
        return len(name) == 10
    except (ValueError, TypeError):
        return False


def _copy_tree_filtered(src: Path, dst: Path, skip_names: set) -> None:
    """copytree с пропуском служебных файлов/каталогов (tmp, lock, логи)."""
    dst.mkdir(parents=True, exist_ok=True)
    for item in sorted(src.iterdir()):
        if item.name in skip_names:
            continue
        if item.name.startswith(".tmp-") or item.name.endswith(".lock"):
            continue
        target = dst / item.name
        if item.is_dir():
            if item.name in ("backups", "__pycache__"):
                continue  # защита от рекурсивного self-backup
            _copy_tree_filtered(item, target, skip_names)
        else:
            try:
                shutil.copy2(str(item), str(target))
            except OSError as e:
                print(f"[BACKUP] copy error {item.name}: {e}")
                raise


# ────────────────────────────────────────────────
# ЛОКАЛЬНЫЙ ЕЖЕДНЕВНЫЙ СНАПШОТ
# ────────────────────────────────────────────────

def get_backup_root() -> Path:
    """%APPDATA%/porayonka/backups"""
    root = get_data_path() / "backups"
    root.mkdir(parents=True, exist_ok=True)
    return root


def local_backup_today_done(today: Optional[date] = None) -> bool:
    marker = get_backup_root() / ".last_local_ok"
    try:
        return marker.read_text(encoding="ascii").strip() == _today_str(today)
    except OSError:
        return False


def create_local_snapshot(today: Optional[date] = None,
                          force: bool = False) -> Optional[Path]:
    """Создать локальный ежедневный снапшот. Путь к снапшоту или None
    (уже сделан сегодня / ошибка / другой процесс)."""
    stamp = _today_str(today)
    root = get_backup_root()
    marker = root / ".last_local_ok"
    if not force and local_backup_today_done(today):
        return None
    lock = root / ".local.lock"
    if not _acquire_lock(lock):
        return None
    if not force and local_backup_today_done(today):
        _release_lock(lock)
        return None
    tmp_dir = root / f".tmp-local-{os.getpid()}"
    try:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True)
        data = get_data_path()
        any_copied = False
        for name in _LOCAL_JSON:
            src = data / name
            if src.exists():
                shutil.copy2(str(src), str(tmp_dir / name))
                any_copied = True
        for name in _LOCAL_DIRS:
            src = data / name
            if src.is_dir():
                _copy_tree_filtered(src, tmp_dir / name, _SKIP_FILES)
                any_copied = True
        if not any_copied:
            shutil.rmtree(tmp_dir)
            return None
        manifest = _collect_manifest(tmp_dir, stamp)
        (tmp_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8")
        target = root / stamp
        if not _publish_snapshot(tmp_dir, target):
            return None
        try:
            marker.write_text(stamp, encoding="ascii")
        except OSError:
            pass
        _enforce_retention(root)
        print(f"[BACKUP] local snapshot ok: {target.name}")
        return target
    except OSError as e:
        print(f"[BACKUP] local snapshot error: {e}")
        try:
            shutil.rmtree(tmp_dir)
        except OSError:
            pass
        return None
    finally:
        _release_lock(lock)


def maybe_daily_local_backup() -> Optional[Path]:
    """Не чаще одной УСПЕШНОЙ копии за календарный день (idempotent)."""
    try:
        return create_local_snapshot()
    except Exception as e:  # backup не должен ронять приложение
        print(f"[BACKUP] daily local error: {e}")
        return None


# ────────────────────────────────────────────────
# SHARED ЕЖЕДНЕВНЫЙ СНАПШОТ (ТОЛЬКО ADMIN)
# ────────────────────────────────────────────────

def get_shared_backup_root(settings: dict) -> Optional[Path]:
    """<workspace>/backups или None (сеть выключена/paths не настроен)."""
    if not settings.get("network_enabled"):
        return None
    sdir = _shared_dir(settings)
    if sdir is None:
        return None
    return sdir / "backups"


def shared_backup_today_done(settings: dict, today: Optional[date] = None) -> bool:
    root = get_shared_backup_root(settings)
    if root is None:
        return False
    try:
        return (root / ".last_shared_ok").read_text(
            encoding="ascii").strip() == _today_str(today)
    except OSError:
        return False


def create_shared_snapshot(settings: dict, is_admin: bool,
                           today: Optional[date] = None) -> Optional[Path]:
    """Снапшот shared controls.json + controls_attachments в
    <workspace>/backups/YYYY-MM-DD. Только admin; user — мягкий None,
    ничего не создаёт и не удаляет в общей папке."""
    if not is_admin:
        return None
    stamp = _today_str(today)
    root = get_shared_backup_root(settings)
    if root is None:
        return None
    sdir = _shared_dir(settings)
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"[BACKUP] shared root error: {e}")
        return None
    if shared_backup_today_done(settings, today):
        return None
    lock = root / ".shared.lock"
    if not _acquire_lock(lock):
        return None
    if shared_backup_today_done(settings, today):
        _release_lock(lock)
        return None
    tmp_dir = root / f".tmp-shared-{os.getpid()}"
    try:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True)
        any_copied = False
        src_json = sdir / "controls.json"
        if src_json.exists():
            shutil.copy2(str(src_json), str(tmp_dir / "controls.json"))
            any_copied = True
        src_atts = sdir / "controls_attachments"
        if src_atts.is_dir():
            _copy_tree_filtered(src_atts, tmp_dir / "controls_attachments",
                                 _SKIP_FILES)
            any_copied = True
        if not any_copied:
            shutil.rmtree(tmp_dir)
            return None
        manifest = _collect_manifest(tmp_dir, stamp)
        (tmp_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8")
        target = root / stamp
        if not _publish_snapshot(tmp_dir, target):
            return None
        try:
            (root / ".last_shared_ok").write_text(stamp, encoding="ascii")
        except OSError:
            pass
        _enforce_retention(root)
        print(f"[BACKUP] shared snapshot ok: {stamp}")
        return target
    except OSError as e:
        print(f"[BACKUP] shared snapshot error: {e}")
        try:
            shutil.rmtree(tmp_dir)
        except OSError:
            pass
        return None
    finally:
        _release_lock(lock)


def maybe_daily_shared_backup(settings: dict, is_admin: bool) -> Optional[Path]:
    """Обёртка с защитой от исключений (сетевой сбой не ломает работу)."""
    try:
        return create_shared_snapshot(settings, is_admin)
    except Exception as e:
        print(f"[BACKUP] daily shared error: {e}")
        return None


# ────────────────────────────────────────────────
# РАЗОВЫЕ И СТАТУСНЫЕ ОПЕРАЦИИ
# ────────────────────────────────────────────────

def backup_file_now(path: Path, purpose: str = "manual") -> Optional[Path]:
    """Разовая копия одного файла (например, controls.json ПЕРЕД импортом
    Excel или лечением дублей): backups/pre-<purpose>-<ts>.json."""
    try:
        src = Path(path)
        if not src.exists():
            return None
        root = get_backup_root()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = root / f"pre-{purpose}-{stamp}.json"
        shutil.copy2(str(src), str(target))
        return target
    except OSError as e:
        print(f"[BACKUP] one-shot error: {e}")
        return None


def migration_backup(controls_file: Path, shared_file: Optional[Path],
                     local_atts: Path, shared_dir: Optional[Path],
                     tag: str = "dedup38") -> Optional[Path]:
    """Раунд 38 (задача 2.3): backup local/shared JSON и папок вложений ПЕРЕД
    первой миграцией-лечением дублей. Кладётся в backups/migration-<tag>-<ts>/.
    Выполняется один раз (проверка маркера вызывающим)."""
    try:
        root = get_backup_root()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = root / f"migration-{tag}-{stamp}"
        target.mkdir(parents=True)
        copied = False
        cf = Path(controls_file)
        if cf.exists():
            shutil.copy2(str(cf), str(target / "local_controls.json"))
            copied = True
        if shared_file and Path(shared_file).exists():
            shutil.copy2(str(shared_file), str(target / "shared_controls.json"))
            copied = True
        la = Path(local_atts)
        if la.is_dir():
            _copy_tree_filtered(la, target / "local_attachments", _SKIP_FILES)
            copied = True
        if shared_dir:
            sa = Path(shared_dir) / "controls_attachments"
            if sa.is_dir():
                _copy_tree_filtered(sa, target / "shared_attachments",
                                     _SKIP_FILES)
                copied = True
        if not copied:
            shutil.rmtree(target)
            return None
        (target / "manifest.json").write_text(json.dumps(
            _collect_manifest(target, stamp), ensure_ascii=False, indent=2),
            encoding="utf-8")
        print(f"[BACKUP] migration backup ok: {target.name}")
        return target
    except OSError as e:
        print(f"[BACKUP] migration backup error: {e}")
        return None


def last_local_snapshot() -> Optional[Path]:
    """Последний валидный локальный снапшот (по дате) или None."""
    root = get_backup_root()
    try:
        days = sorted(p.name for p in root.iterdir()
                      if p.is_dir() and _is_day_name(p.name))
    except OSError:
        return None
    return root / days[-1] if days else None


def backup_status_text(settings: dict, is_admin: bool) -> str:
    """Короткий статус для UI (tooltip сетевого индикатора у admin):
    даты последних успешных локальной/общей копий и путь."""
    local = last_local_snapshot()
    local_txt = local.name if local else "-"
    shared_txt = "-"
    if is_admin:
        sroot = get_shared_backup_root(settings)
        if sroot is not None:
            try:
                days = sorted(p.name for p in sroot.iterdir()
                              if p.is_dir() and _is_day_name(p.name))
                if days:
                    shared_txt = days[-1]
            except OSError:
                pass
    try:
        root_str = str(get_backup_root())
    except Exception:
        root_str = ""
    return (f"Локальная копия: {local_txt} · Общая: {shared_txt}\n"
            f"{root_str}").strip()


def restore_local_snapshot(snapshot_dir: Path, target_dir: Path) -> int:
    """Восстановить содержимое снапшота в target_dir (для ручного
    восстановления в отдельный каталог — НЕ перезаписывает рабочую базу
    само по себе). Возвращает число скопированных файлов."""
    src = Path(snapshot_dir)
    dst = Path(target_dir)
    if not src.is_dir():
        return 0
    count = 0
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*"):
        if not item.is_file() or item.name == "manifest.json":
            continue
        rel = item.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(item), str(target))
        count += 1
    return count

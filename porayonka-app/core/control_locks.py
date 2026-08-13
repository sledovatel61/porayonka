# core/control_locks.py
# Раунд 29 (задача 6): блокировка одновременного редактирования контроля
# двумя администраторами через lock-файлы в общей папке.
#
# Механика: при открытии карточки контроля создаётся файл
#   <shared>/.locks/<control_id>.lock
# с JSON {"user": ФИО, "machine": имя ПК, "since": ISO}. Пока карточка
# открыта, фоновый цикл «подогревает» lock (touch: обновляет since/mtime),
# чтобы он не протухал. При закрытии/сохранении карточки lock удаляется.
# Чужой активный lock -> диалог «редактируется <ФИО> с <время>».
# Lock старше LOCK_STALE_MIN минут считается «мёртвым» (приложение аварийно
# завершилось, не сняв блокировку) и не мешает открытию.
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from .controls_data import _shared_dir

# «Мёртвый» lock — старше 10 минут (по промпту).
LOCK_STALE_MIN = 10

# Допуск на рассинхрон часов ПК: файл «из будущего» (свежее since по часам
# создателя при отстающих часах проверяющего) считаем АКТИВНЫМ — эпизодический
# перезахват чужой карточки хуже ложного «открыто редактирование», поэтому
# отрицательный возраст клампим в 0.
_FUTURE_GRACE_SEC = 120.0


def _locks_dir(settings: dict) -> Optional[Path]:
    """Папка lock-файлов в общей сетевой папке (None, если сеть выключена)."""
    if not settings.get("network_enabled"):
        return None
    sd = _shared_dir(settings)
    if sd is None:
        return None
    return sd / ".locks"


def _lock_file(settings: dict, control_id: str) -> Optional[Path]:
    d = _locks_dir(settings)
    if d is None or not control_id:
        return None
    safe = "".join(ch for ch in str(control_id) if ch.isalnum() or ch in "-_")
    if not safe:
        return None
    return d / f"{safe}.lock"


def _read_info(path: Path) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    return None


def _age_seconds(info: dict, path: Path) -> Optional[float]:
    """Возраст lock'а (сек) по полю since; fallback — mtime файла."""
    raw = (info or {}).get("since") or ""
    if raw:
        try:
            return time.time() - datetime.fromisoformat(raw).timestamp()
        except (ValueError, TypeError, OSError):
            pass
    try:
        return time.time() - path.stat().st_mtime
    except OSError:
        return None


def _is_stale(info: dict, path: Path) -> bool:
    age = _age_seconds(info, path)
    if age is None:
        return False
    if age < 0:
        # Файл «из будущего» — часы создателя впереди; активен, если свежий.
        return (-age) > _FUTURE_GRACE_SEC + LOCK_STALE_MIN * 60
    return age > LOCK_STALE_MIN * 60


def lock_owner(settings: dict, control_id: str) -> Optional[dict]:
    """Информация о владельце АКТИВНОГО lock'а {"user", "machine", "since"}
    или None (нет lock'а, битый lock — удаляется, «мёртвый» — игнорируется)."""
    path = _lock_file(settings, control_id)
    if path is None or not path.exists():
        return None
    info = _read_info(path)
    if info is None:
        # битый lock-файл не должен вечно блокировать редактирование
        try:
            path.unlink()
        except OSError:
            pass
        return None
    if _is_stale(info, path):
        try:
            path.unlink()  # подчистить мёртвый заодно
        except OSError:
            pass
        return None
    return {"user": str(info.get("user") or "?").strip() or "?",
            "machine": str(info.get("machine") or "").strip(),
            "since": str(info.get("since") or "").strip()}


def acquire_lock(settings: dict, control_id: str, user: str) -> Tuple[bool, Optional[dict]]:
    """Попытаться заблокировать контроль для редактирования.

    Возвращает (True, None) — lock наш (создан или уже наш); иначе
    (False, owner_info) — редактирует другой админ. «Мёртвые» lock'и
    перезахватываются. Сеть выключена/недоступна — (True, None): офлайн-
    работу не блокируем.
    """
    owner = lock_owner(settings, control_id)
    if owner is not None and owner.get("user") != (user or ""):
        return False, owner
    path = _lock_file(settings, control_id)
    if path is None:
        return True, None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        info = {"user": user or "", "machine": _machine_name(),
                "since": datetime.now().isoformat()}
        tmp = path.with_suffix(".lock.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False)
        os.replace(tmp, path)  # атомарная замена
        return True, None
    except OSError as e:
        print(f"[LOCKS] Oshibka sozdaniya lock-fayla: {e}")
        return True, None  # не мешаем работе при проблемах с сетевой ФС


def touch_lock(settings: dict, control_id: str, user: str) -> None:
    """«Подогреть» свой lock (метка времени), пока карточка открыта — чтобы
    фоновый stale-рубеж в 10 мин не отпускал lock действующего редактора."""
    path = _lock_file(settings, control_id)
    if path is None:
        return
    try:
        if not path.exists():
            # lock пропал (другой админ перезахватил? сеть мигнула) — вернуть
            acquire_lock(settings, control_id, user)
            return
        info = _read_info(path) or {}
        if (info.get("user") or "") != (user or ""):
            return  # чужой lock не трогаем
        info["since"] = datetime.now().isoformat()
        tmp = path.with_suffix(".lock.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError:
        pass


def release_lock(settings: dict, control_id: str, user: str) -> None:
    """Снять lock (закрытие/сохранение карточки). Удаляем ТОЛЬКО свой lock —
    если пользователь на этой машине сменился, а файл остался от прежнего,
    не чужой же: совпадение проверяется по ФИО владельца."""
    path = _lock_file(settings, control_id)
    if path is None or not path.exists():
        return
    try:
        info = _read_info(path) or {}
        if (info.get("user") or "") != (user or ""):
            return
        path.unlink()
    except OSError:
        pass


def refresh_locks(settings: dict, active: List[Tuple[str, str]],
                  user: str) -> None:
    """Фоновая серия (~раз в минуту): touch переданных (control_id, ...),
    принадлежащих нам. Сверх stale-рубежа это держит lock живым, пока
    карточка реально открыта; упавшее приложение перестаёт «подогревать» —
    lock протухает сам."""
    for cid, owner in active or []:
        if not cid:
            continue
        if (owner or "") != (user or ""):
            continue
        try:
            touch_lock(settings, cid, user)
        except Exception:
            pass


def _machine_name() -> str:
    """Имя ПК для диагностики lock'а (сокет — stdlib, без зависимостей)."""
    try:
        import socket
        return (socket.gethostname() or "").strip()
    except Exception:
        return os.getenv("COMPUTERNAME", "") or ""

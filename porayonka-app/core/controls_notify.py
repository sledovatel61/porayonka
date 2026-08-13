# core/controls_notify.py
# Раунд 23 (задача 2): «злые» уведомления о наступившем сроке контроля.
#
# Правила пользователя:
#  - срабатывают на статус «просрочен»/«сегодня»;
#  - ПОЛЬЗОВАТЕЛЬ (user-редакция): повтор каждые 2 часа, пока админ не отметит
#    исполнение (после done контроль сам выпадает из списка; статусы едут по
#    сети через shared json — существующая синхронизация);
#  - АДМИН: достаточно одного раза в день;
#  - user получает алармы ТОЛЬКО по своим контролям (исполнитель / ответственный
#    по пункту / контролёр).
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .controls_models import (
    OVERDUE, TODAY, deadline_status, user_deadline_status, name_matches,
)

ALARM_INTERVAL_USER_HOURS = 2
ALARM_INTERVAL_ADMIN_HOURS = 24
ALARM_STATUSES = (OVERDUE, TODAY)
ALARM_LOG_KEEP_DAYS = 30


def alarm_interval_hours(is_user: bool) -> int:
    """Интервал повтора «злого» аларма: пользователь — 2 ч, админ — 24 ч."""
    return ALARM_INTERVAL_USER_HOURS if is_user else ALARM_INTERVAL_ADMIN_HOURS


def control_belongs_to(control, person: str) -> bool:
    """True, если person (ФИО пользователя) задействован в контроле:
    исполнитель, ответственный по пункту или «за кем контроль»."""
    p = (person or "").strip()
    if not p:
        return False
    if name_matches(p, getattr(control, "controller", "") or ""):
        return True
    names = list(getattr(control, "executors", []) or [])
    for t in getattr(control, "tasks", []) or []:
        names.extend(getattr(t, "assignees", []) or [])
    return any(name_matches(p, n) for n in names if n)


def collect_alarm_controls(controls, soon_days: int,
                           user_name: str = "") -> list:
    """Контроли с наступившим сроком (просрочен/сегодня), активные.
    `user_name` задан (user-редакция) — только контроли этого человека, и
    статус считается по ЕГО пунктам (user_deadline_status, раунд 31 задача 5):
    чужой просроченный пункт в том же контроле не будит аларм пользователя."""
    base = [c for c in controls or []
            if not getattr(c, "done", False) and not getattr(c, "archived", False)]
    if (user_name or "").strip():
        base = [c for c in base if control_belongs_to(c, user_name)]
        return [c for c in base
                if user_deadline_status(c, user_name, soon_days) in ALARM_STATUSES]
    return [c for c in base
            if deadline_status(c, soon_days) in ALARM_STATUSES]


def _parse_dt(val: Optional[str]) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(val) if val else None
    except (ValueError, TypeError):
        return None


def due_alarms(alarms, alarm_log: Dict[str, str], now: Optional[datetime],
               interval_hours: int) -> Tuple[list, Dict[str, str]]:
    """Отфильтровать контроли, по которым ПОРА алармить (по `alarm_log`), и
    вернуть (список, обновлённый журнал) — журнал НЕ записан в настройки, это
    делает вызывающая сторона (когда аларм реально показан).

    Значения журнала — ISO datetime (в отличие от дневного notify_log)."""
    now = now or datetime.now()
    log = dict(alarm_log or {})
    out = []
    for c in alarms:
        if not getattr(c, "id", None):
            continue
        last = _parse_dt(log.get(c.id))
        if last is None or (now - last) >= timedelta(hours=interval_hours):
            out.append(c)
            log[c.id] = now.isoformat()
    return out, log


def prune_alarm_log(alarm_log: Dict[str, str],
                    now: Optional[datetime] = None) -> Dict[str, str]:
    """Подрезать журнал алармов: записи старше 30 дней."""
    log = dict(alarm_log or {})
    if not log:
        return log
    limit = (now or datetime.now()) - timedelta(days=ALARM_LOG_KEEP_DAYS)
    for key in [k for k in log.keys()]:
        d = _parse_dt(log.get(key))
        if d is None or d < limit:
            log.pop(key, None)
    return log

"""Запросы к PostgreSQL: постраничный список, карточка чтения, сводные счётчики."""
from __future__ import annotations

from typing import Any

import psycopg

_LIST_SELECT = """
SELECT c.id::text                AS id,
       c.incoming_number,
       c.receive_date,
       c.due_date,
       c.done,
       c.archived,
       c.control_type,
       c.initiator,
       c.executor,
       c.controller,
       c.department,
       c.priority,
       (SELECT count(*) FROM control_tasks t WHERE t.control_id = c.id)                    AS tasks_total,
       (SELECT count(*) FROM control_tasks t WHERE t.control_id = c.id AND t.done)         AS tasks_done,
       (SELECT count(*) FROM attachments a WHERE a.control_id = c.id)                      AS attachments_total
FROM controls c
"""

# порядок сортировки обязан совпадать с индексом controls_list_order_idx (стабильная пагинация)
_ORDER_BY = """
ORDER BY c.receive_date DESC NULLS LAST,
         c.incoming_number DESC NULLS LAST,
         c.id DESC
"""

_SEARCH_COLUMNS = (
    "incoming_number",
    "initiator",
    "content",
    "executor",
    "controller",
    "department",
)


def escape_like(term: str) -> str:
    """Экранирование служебных символов LIKE, чтобы поиск был буквальным."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _where(search: str | None, include_archived: bool) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if not include_archived:
        clauses.append("c.archived = false")
    if search:
        pattern = f"%{escape_like(search.strip())}%"
        clauses.append("(" + " OR ".join(f"c.{col} ILIKE %s" for col in _SEARCH_COLUMNS) + ")")
        params.extend([pattern] * len(_SEARCH_COLUMNS))
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def count_controls(conn: psycopg.Connection, *, search: str | None = None, include_archived: bool = False) -> int:
    where, params = _where(search, include_archived)
    sql = f"SELECT count(*) AS total FROM controls c {where}"
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    return int(row["total"]) if row else 0


def list_controls(
    conn: psycopg.Connection,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
    include_archived: bool = False,
) -> list[dict[str, Any]]:
    where, params = _where(search, include_archived)
    offset = (max(page, 1) - 1) * page_size
    sql = f"{_LIST_SELECT}{where}{_ORDER_BY} LIMIT %s OFFSET %s"
    with conn.cursor() as cur:
        cur.execute(sql, [*params, page_size, offset])
        return list(cur.fetchall())


def get_control(conn: psycopg.Connection, control_id: str) -> dict[str, Any] | None:
    sql = """
    SELECT c.id::text AS id, c.incoming_number, c.receive_date, c.due_date, c.done, c.archived,
           c.control_type, c.initiator, c.content, c.executor, c.controller, c.department,
           c.priority, c.note, c.created_at, c.updated_at
    FROM controls c
    WHERE c.id = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (control_id,))
        control = cur.fetchone()
        if not control:
            return None
        cur.execute(
            """
            SELECT t.id::text AS id, t.position, t.text, t.due_date, t.done
            FROM control_tasks t WHERE t.control_id = %s ORDER BY t.position, t.id
            """,
            (control_id,),
        )
        tasks = list(cur.fetchall())
        cur.execute(
            """
            SELECT a.id::text AS id, a.control_id::text AS control_id, a.rel_path, a.file_name,
                   a.size_bytes, a.sha256, a.content_type, a.created_at
            FROM attachments a WHERE a.control_id = %s ORDER BY a.created_at, a.id
            """,
            (control_id,),
        )
        attachments = list(cur.fetchall())
    control["tasks"] = tasks
    control["attachments"] = attachments
    return control


def summary(conn: psycopg.Connection) -> dict[str, int]:
    sql = """
    SELECT count(*)                                                              AS total,
           count(*) FILTER (WHERE archived = false AND done = false)             AS active,
           count(*) FILTER (WHERE archived = true)                               AS archived,
           count(*) FILTER (WHERE done = true)                                   AS done,
           count(*) FILTER (WHERE due_date IS NOT NULL AND due_date < CURRENT_DATE
                            AND done = false AND archived = false)               AS overdue,
           count(*) FILTER (WHERE EXISTS (SELECT 1 FROM attachments a
                                          WHERE a.control_id = controls.id))     AS with_attachments
    FROM controls
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
    return {key: int(value) for key, value in (row or {}).items()}

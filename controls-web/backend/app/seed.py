"""Детерминированное наполнение стенда синтетическими контролями (W01).

Все данные вымышленные: совпадения с реальными ФИО, организациями, входящими
номерами и документами исключены намеренно. Реальные рабочие данные в стенд не
загружаются (запрет миграции до W06).

Воспроизводимость: одинаковые --seed и --count дают одинаковый набор строк и
одинаковый digest (sha256), который пишется в таблицу seed_meta.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Sequence

import psycopg

from . import db

DEFAULT_SEED = 20260917
DEFAULT_COUNT = 10_000
NAMESPACE = uuid.UUID("2f6d3a1e-0000-5000-8000-000000000001")

# --- синтетические справочники (не имеют отношения к реальным лицам) ---
SURNAMES = (
    "Синтетиков", "Тестов", "Учебный", "Пробин", "Макетов", "Шаблонный",
    "Опытный", "Условный", "Бутафорский", "Демонстрационный", "Лабораторный",
    "Черновиков", "Заготовкин", "Модельный",
)
INITIALS = "АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЩЭЮЯ"
ORGANIZATIONS = (
    "Учебное управление", "Тестовый отдел", "Лабораторная служба",
    "Демонстрационный департамент", "Пробная инспекция", "Макетная канцелярия",
)
DEPARTMENTS = (
    "Группа А (стенд)", "Группа Б (стенд)", "Группа В (стенд)",
    "Канцелярия стенда", "Архив стенда",
)
CONTROL_TYPES = ("Входящее письмо", "Поручение", "Обращение", "Распоряжение", "Резолюция")
PRIORITIES = ("обычный", "важный", "срочный", "особый контроль")
CONTENT_TEMPLATES = (
    "Рассмотреть обращение и подготовить сводку по форме стенда к {d1}. Ответ направить инициатору.",
    "Организовать проверку по перечню, утверждённому инициатором. Промежуточный доклад представить {d1}, итоговый — {d2}.",
    "Подготовить проект ответа на обращение и согласовать его с профильной группой стенда в срок до {d1}.",
    "Обеспечить исполнение пунктов плана: 1) собрать сведения к {d1}; 2) свести таблицу к {d2}; 3) направить отчёт инициатору.",
    "Провести совещание рабочей группы стенда и зафиксировать решения протоколом не позднее {d1}.",
    "Проверить комплектность приложенных документов и при необходимости запросить недостающие сведения до {d2}.",
)
TASK_TEMPLATES = (
    "Собрать сведения по перечню стенда",
    "Подготовить проект ответа",
    "Согласовать проект с профильной группой",
    "Направить отчёт инициатору",
    "Подшить подтверждающие документы",
    "Проверить сроки исполнения пунктов",
)


@dataclass(frozen=True)
class ControlRow:
    id: uuid.UUID
    incoming_number: str
    receive_date: date
    due_date: date | None
    done: bool
    archived: bool
    control_type: str
    initiator: str
    content: str
    executor: str
    controller: str
    department: str
    priority: str
    note: str
    created_at: datetime
    updated_at: datetime
    legacy_raw: str


@dataclass(frozen=True)
class TaskRow:
    id: uuid.UUID
    control_id: uuid.UUID
    position: int
    text: str
    due_date: date | None
    done: bool


def _person(rng: random.Random) -> str:
    return f"{rng.choice(SURNAMES)} {rng.choice(INITIALS)}."


def _d(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def generate(seed: int = DEFAULT_SEED, count: int = DEFAULT_COUNT) -> tuple[list[ControlRow], list[TaskRow], str]:
    """Детерминированная генерация: (контроли, пункты, digest)."""
    rng = random.Random(seed)
    controls: list[ControlRow] = []
    tasks: list[TaskRow] = []
    digest = hashlib.sha256()
    start = date(2023, 1, 1)
    span_days = (date(2026, 9, 1) - start).days

    for index in range(count):
        control_id = uuid.uuid5(NAMESPACE, f"control:{seed}:{index}")
        receive_date = start + timedelta(days=rng.randint(0, span_days))
        has_due = rng.random() > 0.05
        due_date = receive_date + timedelta(days=rng.randint(7, 120)) if has_due else None
        done = rng.random() < 0.15
        archived = rng.random() < 0.05
        d1 = receive_date + timedelta(days=rng.randint(5, 40))
        d2 = receive_date + timedelta(days=rng.randint(41, 90))
        content = rng.choice(CONTENT_TEMPLATES).format(d1=_d(d1), d2=_d(d2))
        created_at = datetime(
            receive_date.year, receive_date.month, receive_date.day, 9, 0, tzinfo=timezone.utc
        ) + timedelta(minutes=rng.randint(0, 480))
        updated_at = created_at + timedelta(hours=rng.randint(0, 720))
        row = ControlRow(
            id=control_id,
            incoming_number=f"СТЕНД-{index + 1:06d}",
            receive_date=receive_date,
            due_date=due_date,
            done=done,
            archived=archived,
            control_type=rng.choice(CONTROL_TYPES),
            initiator=rng.choice(ORGANIZATIONS),
            content=content,
            executor=_person(rng),
            controller=_person(rng),
            department=rng.choice(DEPARTMENTS),
            priority=rng.choice(PRIORITIES),
            note="Синтетическая запись стенда W01." if rng.random() < 0.2 else "",
            created_at=created_at,
            updated_at=updated_at,
            legacy_raw=json.dumps(
                {
                    "stand_seed": seed,
                    "stand_index": index,
                    "legacy_extra_field": "значение неизвестного поля legacy сохраняется",
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
        controls.append(row)

        task_count = rng.choice((0, 1, 1, 2, 2, 3))
        for position in range(task_count):
            task_due = receive_date + timedelta(days=rng.randint(3, 90))
            task_done = rng.random() < (0.6 if done else 0.2)
            task = TaskRow(
                id=uuid.uuid5(NAMESPACE, f"task:{seed}:{index}:{position}"),
                control_id=control_id,
                position=position + 1,
                text=f"{TASK_TEMPLATES[rng.randrange(len(TASK_TEMPLATES))]}",
                due_date=task_due,
                done=task_done,
            )
            tasks.append(task)

        digest.update(
            "|".join(
                (
                    str(row.id),
                    row.incoming_number,
                    row.receive_date.isoformat(),
                    row.due_date.isoformat() if row.due_date else "",
                    str(int(row.done)),
                    str(int(row.archived)),
                    row.executor,
                    row.controller,
                    row.content,
                    str(task_count),
                )
            ).encode("utf-8")
        )
        digest.update(b"\n")
        for task in tasks[-task_count:] if task_count else ():
            digest.update(f"{task.id}:{task.position}:{task.text}:{task.due_date}:{int(task.done)}\n".encode("utf-8"))

    return controls, tasks, digest.hexdigest()


_CONTROL_COLUMNS = (
    "id", "incoming_number", "receive_date", "due_date", "done", "archived",
    "control_type", "initiator", "content", "executor", "controller", "department",
    "priority", "note", "created_at", "updated_at", "legacy_raw",
)
_TASK_COLUMNS = ("id", "control_id", "position", "text", "due_date", "done")


def _rows(items: Iterable[Any], columns: Sequence[str]) -> Iterable[tuple]:
    for item in items:
        yield tuple(getattr(item, col) for col in columns)


def load(conn: psycopg.Connection, *, seed: int = DEFAULT_SEED, count: int = DEFAULT_COUNT,
         reset: bool = True) -> dict[str, Any]:
    """Наполнение БД. reset=True очищает таблицы стенда перед наполнением."""
    db.apply_schema(conn)
    controls, tasks, digest = generate(seed=seed, count=count)
    if reset:
        conn.execute("TRUNCATE attachments, control_tasks, controls, seed_meta RESTART IDENTITY CASCADE")
    with conn.cursor() as cur:
        with cur.copy(f"COPY controls ({', '.join(_CONTROL_COLUMNS)}) FROM STDIN") as copy:
            for row in _rows(controls, _CONTROL_COLUMNS):
                copy.write_row(row)
        with cur.copy(f"COPY control_tasks ({', '.join(_TASK_COLUMNS)}) FROM STDIN") as copy:
            for row in _rows(tasks, _TASK_COLUMNS):
                copy.write_row(row)
        cur.execute(
            "INSERT INTO seed_meta (seed, requested_count, controls_count, tasks_count, digest) "
            "VALUES (%s, %s, %s, %s, %s)",
            (seed, count, len(controls), len(tasks), digest),
        )
    return {
        "seed": seed,
        "requested_count": count,
        "controls": len(controls),
        "tasks": len(tasks),
        "digest": digest,
    }


def verify(conn: psycopg.Connection, *, seed: int = DEFAULT_SEED, count: int = DEFAULT_COUNT) -> dict[str, Any]:
    """Сверка фактического содержимого БД с детерминированной генерацией."""
    controls, tasks, digest = generate(seed=seed, count=count)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) AS n FROM controls")
        db_controls = int(cur.fetchone()["n"])
        cur.execute("SELECT count(*) AS n FROM control_tasks")
        db_tasks = int(cur.fetchone()["n"])
        cur.execute(
            "SELECT digest, seed, controls_count, tasks_count FROM seed_meta ORDER BY id DESC LIMIT 1"
        )
        meta = cur.fetchone()
    return {
        "expected_controls": len(controls),
        "db_controls": db_controls,
        "expected_tasks": len(tasks),
        "db_tasks": db_tasks,
        "expected_digest": digest,
        "meta": meta,
        "ok": bool(
            db_controls == len(controls) == count
            and db_tasks == len(tasks)
            and meta
            and meta["digest"] == digest
            and int(meta["seed"]) == seed
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Наполнение стенда controls-web (W01)")
    parser.add_argument("--dsn", default=None, help="DSN PostgreSQL (по умолчанию из CONTROLS_WEB_DSN)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--reset", action="store_true", help="очистить таблицы стенда перед наполнением")
    parser.add_argument("--verify", action="store_true", help="только сверка, без записи")
    args = parser.parse_args(argv)

    from .config import load_settings

    dsn = args.dsn or load_settings().dsn
    with db.connection(dsn) as conn:
        if args.verify:
            report = verify(conn, seed=args.seed, count=args.count)
            print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
            return 0 if report["ok"] else 1
        report = load(conn, seed=args.seed, count=args.count, reset=args.reset)
        check = verify(conn, seed=args.seed, count=args.count)
        print(json.dumps({"loaded": report, "verify": check}, ensure_ascii=False, indent=2, default=str))
        return 0 if check["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

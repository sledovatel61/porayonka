"""Воспроизводимость наполнения и синтетичность данных (нет реальных ФИО/адресов)."""
from __future__ import annotations

import re
import uuid

import pytest
from fastapi.testclient import TestClient

from app import seed


def test_same_seed_produces_identical_dataset() -> None:
    controls_a, tasks_a, digest_a = seed.generate(seed=20260917, count=500)
    controls_b, tasks_b, digest_b = seed.generate(seed=20260917, count=500)
    assert digest_a == digest_b
    assert [str(c.id) for c in controls_a] == [str(c.id) for c in controls_b]
    assert [c.incoming_number for c in controls_a] == [c.incoming_number for c in controls_b]
    assert [(t.id, t.text, t.due_date, t.done) for t in tasks_a] == [
        (t.id, t.text, t.due_date, t.done) for t in tasks_b
    ]


def test_different_seed_produces_different_dataset() -> None:
    _, _, digest_a = seed.generate(seed=20260917, count=500)
    _, _, digest_b = seed.generate(seed=20260918, count=500)
    assert digest_a != digest_b


def test_uuids_are_deterministic_uuid5() -> None:
    controls, _, _ = seed.generate(seed=20260917, count=3)
    expected = uuid.uuid5(seed.NAMESPACE, "control:20260917:0")
    assert controls[0].id == expected
    assert controls[0].id.version == 5


def test_database_matches_generated_digest(conn) -> None:
    report = seed.verify(conn, seed=seed.DEFAULT_SEED, count=10_000)
    assert report["ok"] is True, report
    assert report["db_controls"] == 10_000
    assert report["db_tasks"] == report["expected_tasks"] > 0
    assert report["meta"]["digest"] == report["expected_digest"]


def test_reseeding_restores_identical_state(conn) -> None:
    first = seed.verify(conn, seed=seed.DEFAULT_SEED, count=10_000)
    reloaded = seed.load(conn, seed=seed.DEFAULT_SEED, count=10_000, reset=True)
    second = seed.verify(conn, seed=seed.DEFAULT_SEED, count=10_000)
    assert reloaded["digest"] == first["expected_digest"] == second["expected_digest"]
    assert second["db_controls"] == 10_000


def test_data_is_synthetic_and_has_no_real_identifiers(conn) -> None:
    """Данные стенда синтетические: фамилии только из справочника стенда, номера с префиксом
    «СТЕНД-», в текстах нет IP-адресов, UNC-путей и ссылок на рабочие файлы.

    Настоящие ФИО, номера и адреса в тесте намеренно не перечисляются: проверка построена
    по белому списку, поэтому ничего реального в репозиторий не попадает.
    """
    rows = conn.execute(
        "SELECT incoming_number, initiator, content, executor, controller, department, note "
        "FROM controls ORDER BY incoming_number LIMIT 2000"
    ).fetchall()
    assert rows
    ip_pattern = re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")
    for row in rows:
        for column in ("executor", "controller"):
            surname = str(row[column]).split(" ")[0]
            assert surname in seed.SURNAMES, f"несинтетическая фамилия в {column}: {surname!r}"
        assert row["incoming_number"].startswith("СТЕНД-"), "номер должен иметь стендовый префикс"
        assert row["initiator"] in seed.ORGANIZATIONS
        assert row["department"] in seed.DEPARTMENTS
        joined = " ".join(str(value) for value in row.values())
        assert not ip_pattern.search(joined), f"в данных найден IP-подобный адрес: {joined[:80]}"
        for marker in ("\\\\", "%APPDATA%", ".xlsx", "file://", "smb://"):
            assert marker not in joined, f"в данных найден маркер рабочего ресурса {marker!r}"


def test_incoming_numbers_unique(conn) -> None:
    row = conn.execute(
        "SELECT count(*) AS total, count(DISTINCT incoming_number) AS uniq FROM controls"
    ).fetchone()
    assert row["total"] == row["uniq"] == 10_000


def test_legacy_raw_is_preserved(conn) -> None:
    row = conn.execute(
        "SELECT legacy_raw FROM controls ORDER BY incoming_number LIMIT 1"
    ).fetchone()
    assert row["legacy_raw"]["legacy_extra_field"]
    assert row["legacy_raw"]["stand_seed"] == seed.DEFAULT_SEED


def test_counts_exposed_via_api(client: TestClient) -> None:
    body = client.get("/api/meta/summary").json()
    assert body["total"] == 10_000
    assert body["with_attachments"] >= 0


@pytest.mark.parametrize("count", [0, 1, 7])
def test_generator_handles_small_counts(count: int) -> None:
    controls, tasks, digest = seed.generate(seed=20260917, count=count)
    assert len(controls) == count
    assert len(digest) == 64
    assert all(task.control_id in {c.id for c in controls} for task in tasks)

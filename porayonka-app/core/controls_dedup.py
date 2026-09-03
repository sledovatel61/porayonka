# core/controls_dedup.py
# Раунд 38 (P0, задача 1): защита от ЛОГИЧЕСКИХ дублей контролей.
#
# Полевой симптом: у пользовательской desktop-редакции контроли задваивались
# парами (совпадали вх. номер, содержание, исполнители, контролёр, сроки) —
# одна и та же запись исторически получила РАЗНЫЕ UUID (повторный импорт,
# старый локальный кэш, прежняя миграция). merge_controls() делает union
# только по `id`, поэтому обе записи выживали.
#
# Здесь — нормализованный business identity (fingerprint), диагностика и
# консервативное схлопывание точных дублей с объединением (не потерей)
# вложений, пунктов и заполненных полей.
#
# Консерватизм:
#   * записи с ПУСТЫМ вх. номером никогда не считаются одним контролем;
#   * равный нормализованный номер + равная дата поступления + равная
#     каноническая группа инициатора + равное нормализованное содержание —
#     доказанный дубль одной бумажной записи; похожие, но реально разные
#     контроли (другая дата, другой инициатор, другое содержание) НЕ
#     схлопываются;
#   * одинаковый валидный `id` остаётся главным identity обычного LWW merge.
import hashlib
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .controls_models import Control

# Варианты тире/дефисов, встречающиеся в реальных вх. номерах после вставки
# из Word/Excel: длинное/короткое тире, минус, неразрывный дефис.
_DASH_CHARS = "—–−‐‒―"
_DASH_TRANS = {ord(c): "-" for c in _DASH_CHARS}

# Символы-разделители, приравниваемые к пробелу до схлопывания (затем пробелы
# убираются вовсе — номер сравнивается без пробелов вокруг тире/слешей).
_SEP_CHARS = {"/", "\\", "|", "_"}


def _nfkc(s: str) -> str:
    """Unicode NFKC + NBSP -> пробел (NBSP из Excel ломал визуально равные
    строки)."""
    s = unicodedata.normalize("NFKC", s or "")
    return s.replace(" ", " ").replace(" ", " ")


def normalize_incoming_number(raw: str) -> str:
    """Нормализованный входящий номер для business-сравнения.

    Правила: NFKC, casefold, все варианты тире -> '-', разделители '/\\|_'
    и ПРОБЕЛЫ -> '-' («Иссоп-216-193-26», «иссоп 216 - 193-26»,
    «Иссоп 216-1996-25» равны своим дефисным вариантам — именно такие пары
    были на полевом скриншоте), повторные тире схлопываются.
    Пустой номер -> "".
    """
    s = _nfkc(raw).casefold()
    s = s.translate(_DASH_TRANS)
    for ch in _SEP_CHARS:
        s = s.replace(ch, "-")
    # все пробельные последовательности -> один дефис
    s = "-".join(s.split())
    # схлопнуть повторные тире
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")


def normalize_content(raw: str) -> str:
    """Нормализация содержания для fingerprint: NFKC, casefold, схлопнуть
    пробелы, убрать висячие знаки по краям."""
    s = _nfkc(raw).casefold()
    return " ".join(s.split()).strip(" ,;.")


def _canon_initiator(raw: str) -> str:
    """Канон группы инициатора («ГУК С.» == «ГУК СК»); при ошибке — простая
    нормализация. Импорт локальный, чтобы не тянуть цикл наверх."""
    try:
        from .controls_data import canonical_initiator_group
        return canonical_initiator_group(raw or "") or ""
    except Exception:
        return " ".join(_nfkc(raw or "").casefold().split())


def business_key(ctl: Control) -> Optional[tuple]:
    """Business identity контроля или None (пустой номер — дедуп не применяем).

    Кортеж: (нормализованный номер, дата поступления ISO или "",
    канон инициатора, хэш нормализованного содержания). Содержание хэшируем,
    чтобы key был компактным, но детерминированным.
    """
    num = normalize_incoming_number(getattr(ctl, "incoming_number", "") or "")
    if not num:
        return None
    receive = (getattr(ctl, "receive_date", None) or "").strip()
    init = _canon_initiator(getattr(ctl, "initiator", "") or "")
    content = normalize_content(getattr(ctl, "content", "") or "")
    content_hash = hashlib.sha1(content.encode("utf-8")).hexdigest()[:12]
    return (num, receive, init, content_hash)


def _filled_scalar_score(ctl: Control) -> int:
    """Полнота заполнения значимых полей (для выбора canonical-записи)."""
    score = 0
    for attr in ("incoming_number", "receive_date", "initiator", "content",
                 "controller", "control_type", "due_date", "end_date",
                 "comment", "done_date"):
        if getattr(ctl, attr, None):
            score += 1
    if getattr(ctl, "executors", None):
        score += 1
    if getattr(ctl, "tasks", None):
        score += 1
    if getattr(ctl, "milestones", None):
        score += 1
    return score


def _updated_ts(ctl: Control) -> float:
    """updated_at в epoch (битое/пустое -> 0)."""
    raw = (getattr(ctl, "updated_at", "") or "").strip()
    if not raw:
        return 0.0
    try:
        return datetime.fromisoformat(raw).timestamp()
    except (ValueError, TypeError):
        return 0.0


def _created_ts(ctl: Control) -> float:
    raw = (getattr(ctl, "created_at", "") or "").strip()
    if not raw:
        return float("inf")  # неизвестная дата создания — «младше всех»
    try:
        return datetime.fromisoformat(raw).timestamp()
    except (ValueError, TypeError):
        return float("inf")


def pick_canonical(group: List[Control]) -> Control:
    """Детерминированный выбор canonical-записи среди дублей.

    Приоритет: 1) есть вложения; 2) полнота заполнения; 3) новее updated_at;
    4) лексикографически меньший id (стабильный tie-break).
    """
    def _sort_key(c: Control):
        return (
            0 if (c.attachments or []) else 1,
            -_filled_scalar_score(c),
            -_updated_ts(c),
            str(getattr(c, "id", "") or ""),
        )
    return sorted(group, key=_sort_key)[0]


def _task_key(t) -> tuple:
    return ((getattr(t, "title", "") or "").strip().casefold(),
            (getattr(t, "due_date", None) or ""),
            bool(getattr(t, "is_done", False)),
            tuple(sorted(a.strip().casefold() for a in (getattr(t, "assignees", None) or []))))


def _milestone_key(m) -> tuple:
    return ((getattr(m, "date", None) or ""),
            (getattr(m, "note", "") or "").strip().casefold(),
            bool(getattr(m, "is_done", False)))


def merge_duplicate_group(canonical: Control, losers: List[Control]) -> None:
    """Объединить дубли В canonical (убыточное не выбрасывается молча).

    - attachments: union по ОТНОСИТЕЛЬНОМУ ПУТИ (<id>/<имя>) — два РАЗНЫХ
      файла с одинаковым именем не теряются (переезд/переименование и снятие
      побайтово одинаковых копий — в dedupe_controls при переносе файлов);
    - tasks: union по id, затем по содержимому (title+дата+статус+ответственные);
    - milestones: union по (дата, заметка, статус);
    - executors/controller/скаляры: ПУСТЫЕ поля canonical добираются из
      losers (свежие версии первыми); заполненные — не перетираются;
    - done/done_date: если canonical не исполнен, а loser исполнен — принять.
    Физический перенос папок вложений выполняет вызывающий (dedupe_controls).
    """
    losers_sorted = sorted(losers, key=_updated_ts, reverse=True)

    # Вложения: union по относительному пути (разные id-папки = разные файлы)
    seen_paths = {str(a).replace("\\", "/") for a in (canonical.attachments or [])}
    merged_atts = list(canonical.attachments or [])
    for lc in losers_sorted:
        for rel in (lc.attachments or []):
            k = str(rel).replace("\\", "/")
            if k and k not in seen_paths:
                seen_paths.add(k)
                merged_atts.append(rel)
    canonical.attachments = merged_atts

    # Пункты задания: union
    by_id = {t.id: t for t in (canonical.tasks or [])}
    tasks = list(canonical.tasks or [])
    seen_keys = {_task_key(t) for t in tasks}
    for lc in losers_sorted:
        for t in (lc.tasks or []):
            if t.id in by_id or _task_key(t) in seen_keys:
                continue
            tasks.append(t)
            by_id[t.id] = t
            seen_keys.add(_task_key(t))
    canonical.tasks = tasks

    # Промежуточные точки: union
    miles = list(canonical.milestones or [])
    seen_m = {_milestone_key(m) for m in miles}
    for lc in losers_sorted:
        for m in (lc.milestones or []):
            if _milestone_key(m) in seen_m:
                continue
            miles.append(m)
            seen_m.add(_milestone_key(m))
    canonical.milestones = miles

    # Исполнители: union по ФИО без учёта регистра (порядок canonical первым)
    execs = list(canonical.executors or [])
    seen_e = {(e or "").strip().casefold() for e in execs}
    for lc in losers_sorted:
        for e in (lc.executors or []):
            k = (e or "").strip().casefold()
            if k and k not in seen_e:
                seen_e.add(k)
                execs.append(e)
    canonical.executors = execs

    # Скалярные «одиночные» поля: добрать ПУСТЫЕ у canonical
    for attr in ("initiator", "content", "controller", "receive_date",
                 "due_date", "end_date", "comment"):
        if not getattr(canonical, attr, None):
            for lc in losers_sorted:
                val = getattr(lc, attr, None)
                if val:
                    setattr(canonical, attr, val)
                    break
    if not canonical.control_type:
        for lc in losers_sorted:
            if lc.control_type:
                canonical.control_type = lc.control_type
                break
    if not canonical.period_days:
        canonical.period_days = next((lc.period_days for lc in losers_sorted
                                      if lc.period_days), 7)
    # Исполнение: если canonical не исполнен — принять от исполненного дубля
    if not canonical.done:
        for lc in losers_sorted:
            if lc.done:
                canonical.done = True
                canonical.done_date = lc.done_date or lc.updated_at
                break

    # created_at — самая ранняя; updated_at — сейчас (лечение должно выиграть
    # LWW-merge и распространиться по сети)
    created_candidates = [_created_ts(c) for c in [canonical] + list(losers_sorted)]
    best_created = min(created_candidates)
    if best_created != float("inf"):
        canonical.created_at = datetime.fromtimestamp(best_created).isoformat()
    canonical.updated_at = datetime.now().isoformat()


def _same_bytes(a: Path, b: Path) -> bool:
    """Байт-в-байт сравнение двух файлов (для распознавания физически
    одной и той же копии вложения в папках дублей)."""
    try:
        if a.stat().st_size != b.stat().st_size:
            return False
        with open(a, "rb") as fa, open(b, "rb") as fb:
            while True:
                ca = fa.read(65536)
                cb = fb.read(65536)
                if ca != cb:
                    return False
                if not ca:
                    return True
    except OSError:
        return False


def _move_attachment_files(from_id: str, to_id: str,
                           roots: List[Path]) -> Tuple[int, Dict[str, str], set]:
    """Перенести файлы controls_attachments/<from_id> -> <to_id> в каждом root.

    Коллизии имён разрешаются суффиксом _1/_2 (без перезаписи); файл,
    ПОБАЙТОВО ОДИНАКОВЫЙ с уже существующим в <to_id>, копией не считается —
    источник просто удаляется (возвращается в множестве identical, чтобы
    вызывающий снял лишнюю ссылку из списка вложений). Возвращает
    (число обработанных файлов, мапа переименований {старое_имя: новое_имя},
    множество имён, признанных идентичными копиями).
    """
    moved = 0
    renamed: Dict[str, str] = {}
    identical: set = set()
    if not from_id or not to_id or from_id == to_id:
        return moved, renamed, identical
    for root in roots:
        try:
            src_dir = Path(root) / from_id
            if not src_dir.is_dir():
                continue
            dst_dir = Path(root) / to_id
            dst_dir.mkdir(parents=True, exist_ok=True)
            for f in sorted(src_dir.iterdir()):
                if not f.is_file():
                    continue
                target = dst_dir / f.name
                if target.exists():
                    if _same_bytes(f, target):
                        # физическая копия того же файла — лишнюю не плодим
                        try:
                            f.unlink()
                            identical.add(f.name)
                            moved += 1
                        except OSError as e:
                            print(f"[DEDUP] identical attachment remove error: {e}")
                        continue
                    stem, suffix = f.stem, f.suffix
                    i = 1
                    while (dst_dir / f"{stem}_{i}{suffix}").exists():
                        i += 1
                    target = dst_dir / f"{stem}_{i}{suffix}"
                    renamed.setdefault(f.name, target.name)
                ok = False
                try:
                    shutil.move(str(f), str(target))
                    ok = True
                except OSError:
                    # междисковый/сетевой перенос: copy + remove
                    try:
                        shutil.copy2(str(f), str(target))
                        f.unlink()
                        ok = True
                    except OSError as e:
                        print(f"[DEDUP] move attachment error: {e}")
                if ok:
                    moved += 1
            try:
                src_dir.rmdir()  # удалить, только если пуста
            except OSError:
                pass
        except OSError as e:
            print(f"[DEDUP] move attachment dir error: {e}")
    return moved, renamed, identical


def dedupe_controls(controls: List[Control],
                    local_attach_root: Optional[Path] = None,
                    shared_dir: Optional[Path] = None,
                    move_files: bool = True) -> Tuple[List[Control], dict]:
    """Лечение списка от логических дублей (разный id, одна запись).

    Возвращает (исцелённый_список, stats):
      stats = {"merged": N_схлопнутых_записей, "groups": N_групп,
               "moved_files": N, "details": [{"key", "winner", "losers"}]}
    Последовательность стабильна: порядок исходного списка сохранён, canonical
    занимает позицию первого вхождения своей группы. Идемпотентна: повторный
    запуск над результатом возвращает stats["merged"] == 0.

    move_files=False — «сухой» режим для пути чтения (view): папки вложений НЕ
    переносятся, а относительные пути loser-вложений НЕ переписываются под
    canonical id, чтобы не отвязать файлы, которые физически не переехали.
    Используется в user-режиме и в read-view merge; физическое лечение делает
    admin при записи (move_files=True).
    """
    stats = {"merged": 0, "groups": 0, "moved_files": 0, "details": []}
    if not controls:
        return list(controls or []), stats

    # 1) union по id (дубль с ТЕМ ЖЕ id схлопывается, свежий updated_at выигрывает)
    by_id: Dict[str, Control] = {}
    order: List[str] = []
    for c in controls:
        cid = str(getattr(c, "id", "") or "")
        if not cid:
            # Без id не дедуплицируем (защита от потери данных; такие записи
            # лечит _heal_missing_ids на уровне загрузки).
            continue
        if cid not in by_id:
            by_id[cid] = c
            order.append(cid)
        else:
            cur = by_id[cid]
            if _updated_ts(c) > _updated_ts(cur):
                by_id[cid] = c
    uniq = [by_id[cid] for cid in order]

    # 2) группы по business_key
    groups: Dict[tuple, List[Control]] = {}
    rest: List[Control] = []
    for c in uniq:
        key = business_key(c)
        if key is None:
            rest.append(c)
            continue
        groups.setdefault(key, []).append(c)

    healed: List[Control] = []
    for key, group in groups.items():
        if len(group) == 1:
            healed.append(group[0])
            continue
        canonical = pick_canonical(group)
        losers = [c for c in group if c is not canonical]
        merge_duplicate_group(canonical, losers)
        moved = 0
        renamed_map: Dict[tuple, str] = {}
        identical_refs: set = set()
        if move_files:
            roots = []
            if local_attach_root:
                roots.append(Path(local_attach_root))
            if shared_dir:
                roots.append(Path(shared_dir) / "controls_attachments")
            for lc in losers:
                _mv, _ren, _ident = _move_attachment_files(
                    str(lc.id), str(canonical.id), roots)
                moved += _mv
                for nm_old, nm_new in _ren.items():
                    renamed_map[(str(lc.id), nm_old)] = nm_new
                for nm_id in _ident:
                    identical_refs.add((str(lc.id), nm_id))
        # Переписать относительные пути loser-вложений под canonical id
        # (в «сухом» режиме префикс всё равно правим — иначе scan-бейдж и
        # скачивание смотрели бы в папку loser id, которой больше не будет
        # после admin-лечения; файлы допереносит синк вложений). Ссылки,
        # чьи файлы оказались ПОБАЙТОВО теми же копиями, снимаются — в
        # списке не остаётся мусорных дублей одного скана.
        fixed = []
        loser_ids = {str(lc.id) for lc in losers}
        for rel in (canonical.attachments or []):
            parts = str(rel).split("/")
            if len(parts) == 2 and parts[0] in loser_ids:
                nm = parts[1]
                if (parts[0], nm) in identical_refs:
                    continue
                if move_files:
                    nm = renamed_map.get((parts[0], nm), nm)
                fixed.append(f"{canonical.id}/{nm}")
            else:
                fixed.append(rel)
        canonical.attachments = fixed
        healed.append(canonical)
        stats["merged"] += len(losers)
        stats["groups"] += 1
        stats["moved_files"] += moved
        stats["details"].append({
            "key": key[0],
            "winner": str(canonical.id),
            "losers": [str(lc.id) for lc in losers],
        })

    # 3) стабильный итоговый порядок: canonical занимает позицию ПЕРВОГО
    # вхождения своей группы, одиночные записи — свою исходную позицию.
    slot_pos: Dict[tuple, int] = {}

    def _slot_key(c: Control) -> tuple:
        k = business_key(c)
        if k is not None and k in groups and len(groups[k]) > 1:
            return ("g", k)
        return ("s", str(getattr(c, "id", "") or ""))

    for i, c in enumerate(uniq):
        slot_pos.setdefault(_slot_key(c), i)
    result_sorted = sorted(healed + rest,
                           key=lambda c: slot_pos.get(_slot_key(c), 10 ** 9))
    return result_sorted, stats


def diagnose_duplicates(controls: List[Control]) -> dict:
    """Раунд 38 (задача 2.1): диагностический отчёт по базе (без изменений).

    Возвращает:
      {"same_id": [(id, count)], "same_key": [(key_number, [id...])],
       "total": N, "dup_records": N_лишних}
    ФИО/содержание в отчёт не входят — только идентификаторы и вх. номера.
    """
    same_id: Dict[str, int] = {}
    for c in controls or []:
        cid = str(getattr(c, "id", "") or "")
        if cid:
            same_id[cid] = same_id.get(cid, 0) + 1
    id_dups = sorted((cid, n) for cid, n in same_id.items() if n > 1)

    by_key: Dict[tuple, List[str]] = {}
    for c in controls or []:
        k = business_key(c)
        if k is None:
            continue
        by_key.setdefault(k, []).append(str(getattr(c, "id", "") or ""))
    key_dups = []
    extra = 0
    for k, ids in by_key.items():
        uniq_ids = sorted(set(ids))
        if len(uniq_ids) > 1:
            key_dups.append((k[0], uniq_ids))
            extra += len(uniq_ids) - 1
    return {
        "same_id": id_dups,
        "same_key": sorted(key_dups, key=lambda x: x[0]),
        "total": len(controls or []),
        "dup_records": extra + sum(n - 1 for _, n in id_dups),
    }


def diagnostics_report(controls: List[Control],
                       source_updates: Optional[Dict[str, str]] = None) -> str:
    """ASCII-текст диагностики для лога (без персональных данных).

    source_updates: необязательная карта {control_id: updated_at} — источник
    и свежесть версий (для ручного анализа админом)."""
    rep = diagnose_duplicates(controls)
    lines = [
        f"[DEDUP] total={rep['total']} dup_records={rep['dup_records']} "
        f"same_id_groups={len(rep['same_id'])} same_key_groups={len(rep['same_key'])}"
    ]
    for num, ids in rep["same_key"]:
        lines.append(f"[DEDUP] key='{num}' ids={','.join(ids)}")
    for cid, n in rep["same_id"]:
        lines.append(f"[DEDUP] same_id {cid} x{n}")
    return "\n".join(lines)

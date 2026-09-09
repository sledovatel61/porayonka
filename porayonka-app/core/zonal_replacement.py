# core/zonal_replacement.py
# Фаза 40 — взаимозаменяемость зональных криминалистов.
#
# Связи хранятся стабильными числовыми ID (Criminalist.replacement_ids),
# а НЕ строками ФИО. Логика связей вынесена в core, чтобы её можно было
# тестировать отдельно от Flet-дерева и извлекать детерминированные пары
# для печатной PDF-выгрузки.
from typing import Iterable, List, Optional, Tuple


def _coerce_int(value) -> Optional[int]:
    """Преобразовать значение в int; bool/None/мусор отбрасываются."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clean_ids(
    values: Iterable,
    self_id: int,
    valid_ids: set,
) -> List[int]:
    """Очистить список связей: int, без себя, без дублей, без dangling."""
    seen = set()
    out = []
    for value in values or []:
        cid = _coerce_int(value)
        if cid is None:
            continue
        if cid == self_id or cid not in valid_ids or cid in seen:
            continue
        seen.add(cid)
        out.append(cid)
    return sorted(out)


def normalize_zonal_criminalists(criminalists: List) -> List:
    """
    Нормализовать связи на всём списке и сделать их симметричными.

    Инварианты:
      * только числовые ID;
      * без собственного ID и дублей;
      * без ссылок на отсутствующих криминалистов;
      * если A ссылается на B, то B ссылается на A;
      * детерминированный порядок (возрастание ID).
    """
    by_id = {c.id: c for c in criminalists if getattr(c, "id", None) is not None}
    valid_ids = set(by_id.keys())

    for c in criminalists:
        c.replacement_ids = _clean_ids(
            getattr(c, "replacement_ids", None) or [],
            c.id,
            valid_ids,
        )

    # Симметрия: вторая половина пары пишется, даже если её не было в JSON.
    for c in criminalists:
        for rid in list(c.replacement_ids):
            other = by_id.get(rid)
            if other is not None and c.id not in other.replacement_ids:
                other.replacement_ids.append(c.id)

    for c in criminalists:
        c.replacement_ids = _clean_ids(
            c.replacement_ids, c.id, valid_ids,
        )
    return criminalists


def apply_replacement_selection(
    criminalists: List,
    target_id: int,
    selected_ids: Iterable,
) -> List:
    """
    Применить выбор взаимозаменяемости для одного человека.

    Удаление пары с ЛЮБОЙ стороны убирает обе половины: если в выборе
    target больше нет other.id, то и у other удаляется target.id.
    Добавление pair пишет обе стороны. Затем всё нормализуется.
    """
    by_id = {c.id: c for c in criminalists if getattr(c, "id", None) is not None}
    target = by_id.get(target_id)
    if target is None:
        return criminalists
    valid_ids = set(by_id.keys())
    selected = set(_clean_ids(selected_ids, target_id, valid_ids))
    old = set(getattr(target, "replacement_ids", None) or [])

    target.replacement_ids = sorted(selected)

    removed = old - selected
    for other in criminalists:
        if other.id == target_id:
            continue
        if other.id in selected:
            if target_id not in other.replacement_ids:
                other.replacement_ids.append(target_id)
        elif target_id in other.replacement_ids:
            other.replacement_ids = [
                rid for rid in other.replacement_ids if rid != target_id
            ]
    normalize_zonal_criminalists(criminalists)
    return criminalists


def remove_criminalist_and_clean(criminalists: List, target_id: int) -> List:
    """
    Удалить криминалиста и очистить его ID у всех остальных.
    Возвращает тот же список (пересозданный без удалённого).
    """
    target_id = _coerce_int(target_id) if target_id is not None else None
    if target_id is None:
        return criminalists
    by_id = {c.id: c for c in criminalists if c.id != target_id}
    kept = [c for c in criminalists if c.id != target_id]
    valid_ids = set(by_id.keys())
    for c in kept:
        c.replacement_ids = _clean_ids(c.replacement_ids, c.id, valid_ids)
        # Вторая половина любой оставшейся пары уже очистилась в by_id.
    return kept


def unique_replacement_pairs(criminalists: List) -> List[Tuple[object, object]]:
    """
    Уникальные неориентированные пары в текущем порядке списка.

    Порядок: по порядку карточек/ID (индекс в collection.criminalists),
    каждая пара выводится ровно один раз.
    """
    pairs = []
    for i, left in enumerate(criminalists):
        left_ids = set(getattr(left, "replacement_ids", None) or [])
        for right in criminalists[i + 1:]:
            if right.id in left_ids or left.id in getattr(right, "replacement_ids", None) or []:
                pairs.append((left, right))
    return pairs


def short_name(full_name: str) -> str:
    """Сократить ФИО: 'Агеев Олег Владимирович' -> 'Агеев О.В.'."""
    parts = [p for p in str(full_name or "").strip().split() if p]
    if not parts:
        return str(full_name or "").strip()
    surname = parts[0]
    initials = "".join(f"{p[0]}." for p in parts[1:] if p)
    return surname + (f" {initials}" if initials else "")


def format_replacement_pair(left, right) -> str:
    """Строка пары для PDF: 'Иванов И.И. (1) ↔ Петров П.П. (2)'."""
    return (
        f"{short_name(left.full_name)} ({left.id}) ↔ "
        f"{short_name(right.full_name)} ({right.id})"
    )

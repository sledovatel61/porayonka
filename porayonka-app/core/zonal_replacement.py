# core/zonal_replacement.py
# Фаза 40: взаимозаменяемость зональных криминалистов.
#
# Семантика (см. PROMPT_зональные_взаимозаменяемость_и_PDF_фаза40.md, §4.2):
#   * связь НЕОРИЕНТИРОВАННАЯ и ПОПАРНАЯ: A ↔ B автоматически означает
#     B ↔ A; отношение НЕ транзитивно;
#   * человек не взаимозаменяем сам с собой;
#   * связи хранятся стабильными числовыми ID (не строками ФИО);
#   * удаление человека очищает его ID у всех остальных;
#   * смена ФИО/порядка/активности/зон связь не ломает.
#
# Модуль содержит только чистые функции над списком Criminalist — никакого
# Flet/Page/файлового ввода-вывода. Сериализация живёт в core/zonal_data.py.
from typing import List, Optional


def parse_replacement_ids(raw, own_id: int, known_ids) -> List[int]:
    """Преобразовать «сырое» значение replacement_ids в валидный список int.

    - значения приводятся к int, строковый мусор и bool отбрасываются;
    - собственный ID и дубликаты исключаются;
    - ссылки на отсутствующих криминалистов (dangling) исключаются;
    - результат детерминированно упорядочен (sorted).
    """
    if raw is None:
        return []
    if isinstance(raw, (int, float, str, bool)):
        raw = [raw]
    result: List[int] = []
    seen = set()
    for item in raw:
        try:
            value = int(item)
        except (TypeError, ValueError):
            continue
        if isinstance(item, bool):      # bool — подкласс int, это НЕ id
            continue
        if value == own_id or value in seen:
            continue
        if known_ids is not None and value not in known_ids:
            continue
        seen.add(value)
        result.append(value)
    return sorted(result)


def normalize_replacement_links(criminalists: List) -> None:
    """Привести связи списка к инвариантам фазы 40 (in-place).

    Вызывается ПОСЛЕ загрузки старых/ручных JSON и ПЕРЕД сохранением:
    - каждый список чистится (self-link, дубли, строковый мусор, dangling);
    - неориентированность восстанавливается: если A указывает на B,
      то B получает A (иначе пара существовала бы только «в одну сторону»);
    - порядок ID детерминированный (sorted).
    Функция идемпотентна и не трогает остальные поля.
    """
    if not criminalists:
        return
    known_ids = {c.id for c in criminalists}
    # Шаг 1: локальная чистка каждого списка.
    for c in criminalists:
        c.replacement_ids = parse_replacement_ids(
            c.replacement_ids, c.id, known_ids)
    # Шаг 2: симметрия — для каждой пары (a, b), где a ссылается на b,
    # гарантировать ссылку a в списке b.
    for c in criminalists:
        for partner_id in list(c.replacement_ids):
            partner = _find_by_id(criminalists, partner_id)
            if partner is None:
                continue
            if c.id not in partner.replacement_ids:
                partner.replacement_ids = sorted(
                    set(partner.replacement_ids) | {c.id})


def set_replacement_partners(criminalists: List,
                             criminalist_id: int,
                             partner_ids,
                             known_ids: Optional[set] = None) -> List[int]:
    """Установить партнёров по взаимозаменяемости для одного человека.

    Полная «замена множества» — то, что делает сохранение формы
    добавления/редактирования криминалиста:
      1. список партнёров чистится и упорядочивается;
      2. у ВСЕХ остальных удаляется ссылка на criminalist_id (пара удаляется
         с любой стороны);
      3. каждый новый партнёр получает ссылку на criminalist_id
         (симметричность);
      4. у criminalist_id сохраняется ровно очищенный список.

    Возвращает итоговый детерминированный список партнёров.
    """
    if known_ids is None and criminalists is not None:
        known_ids = {c.id for c in criminalists}
    clean = parse_replacement_ids(partner_ids, criminalist_id, known_ids)

    me = _find_by_id(criminalists, criminalist_id)
    if me is None:
        # Субъекта нет в списке (в UI не случается: добавляемый человек
        # попадает в список ДО вызова). Ничего не меняем — иначе партнёры
        # получили бы ссылку на отсутствующего человека (dangling).
        return clean
    for c in criminalists:
        if c.id == criminalist_id:
            continue
        if criminalist_id in c.replacement_ids:
            c.replacement_ids = [p for p in c.replacement_ids
                                 if p != criminalist_id]
        if c.id in clean and criminalist_id not in c.replacement_ids:
            c.replacement_ids = sorted(c.replacement_ids + [criminalist_id])
    me.replacement_ids = clean
    return clean


def remove_criminalist_links(criminalists: List, removed_id: int) -> None:
    """Удалить ВСЕ ссылки на removed_id у остальных (при удалении человека)."""
    for c in criminalists:
        if c.id == removed_id:
            continue
        if removed_id in c.replacement_ids:
            c.replacement_ids = [p for p in c.replacement_ids
                                 if p != removed_id]


def _find_by_id(criminalists: List, criminalist_id: int):
    for c in criminalists:
        if c.id == criminalist_id:
            return c
    return None


# ────────────────────────────────────────────────────────────────
# ЧИСТЫЕ ХЕЛПЕРЫ ДЛЯ PDF/UI
# ────────────────────────────────────────────────────────────────

def unique_pairs(criminalists: List):
    """Все уникальные неориентированные пары в порядке карточек.

    Возвращает список кортежей (a, b) — объекты Criminalist в порядке их
    появления в collection.criminalists (для каждой пары первым идёт тот,
    кто стоит раньше в списке). Каждая пара встречается РОВНО один раз,
    направление детерминировано. Пара учитывается только если ОБЕ стороны
    присутствуют в списке (гарантируется normalize_replacement_links).
    """
    by_id = {c.id: c for c in criminalists}
    index = {c.id: i for i, c in enumerate(criminalists)}
    pairs = []
    seen = set()
    for c in criminalists:
        for partner_id in c.replacement_ids:
            partner = by_id.get(partner_id)
            if partner is None:
                continue
            key = (min(c.id, partner_id), max(c.id, partner_id))
            if key in seen:
                continue
            seen.add(key)
            # Направление по позиции в списке, а не по тому, чья сторона
            # «записала» связь (важно для асимметричных/ручных JSON).
            first, second = ((c, partner) if index[c.id] < index[partner.id]
                             else (partner, c))
            pairs.append((first, second))
    return pairs


def short_full_name(full_name: str) -> str:
    """«Иванов Иван Иванович» → «Иванов И.И.» (для строк пар PDF).

    - одна часть слова → как есть;
    - если имя уже сокращено (встречается точка) → как есть;
    - иначе фамилия + инициалы остальных частей.
    """
    name = (full_name or "").strip()
    if not name:
        return ""
    parts = [p for p in name.replace("\u00a0", " ").split(" ") if p]
    if len(parts) <= 1 or any("." in p for p in parts[1:]):
        return name
    initials = "".join(p[0].upper() + "." for p in parts[1:])
    return f"{parts[0]} {initials}"

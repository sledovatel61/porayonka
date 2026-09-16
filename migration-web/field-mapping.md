# field-mapping.md — поля legacy → proposed схема

База: SHA `b5f24ab58c642fafb5cca616aa8b4e16d3a3de3f`, код `porayonka-app/`.
Пометки **[Код]** / **[Пред]** / **[Владелец]** — как в `requirements-matrix.md`.

Таблицы описывают ПОЛНЫЙ перенос без потерь: ни одно поле моделей не удаляется
«за неупотреблением»; «не переносить» допускается только для полей инфраструктуры (сеть,
редакция), и это помечено явно. Типы в новой системе ориентировочные (PostgreSQL);
окончательная DDL — W02. Здесь нет утверждённой схемы — здесь соответствие и правила.

Соглашения:
- `date` — календарная дата без времени (в legacy — строка `YYYY-MM-DD`);
- `timestamptz` — момент (в legacy — naive `datetime.now().isoformat()`, пояс потерян);
- `person_id` — суррогатный ключ справочника людей новой системы;
- «пустое» = `None` / `""` / `[]` в JSON (в `from_dict` они не различаются **[Код]**).

## 1. `Control` — 22 поля

Источник: `core/controls_models.py:362–438` (`Control` `:362`, `to_dict` `:387`,
`from_dict` `:414–438`).

| Legacy-поле / тип / default | Новая сущность.поле / тип | Null / пустое | Преобразование | Валидация | Проверка сохранности | Источник |
|---|---|---|---|---|---|---|
| `id: str` / default нет (`from_dict` выдаёт `uuid4`) | `control.id uuid pk` | отсутствует → лечится (F-02) | сохранить как есть, НЕ перевыдавать | canonical UUID | сравнение множеств id; счёт дублей | `:416`, `controls_data.py:182–212` |
| `incoming_number: str` / `""` | `control.incoming_number text` + `incoming_number_norm` | `""` разрешён (дедуп не применяем) | нормализация — только в `*_norm`, оригинал не правится | ≤255; НЕ unique (D-17) | `norm` совпадает после round-trip | `controls_dedup.py:48–67` |
| `receive_date: date-str` / `None` | `control.receive_date date null` | `None` → NULL | ISO | валидная дата; невалидная → NULL + строка отчёта | 100 % непустых совпадают | `controls_models.py:28–36` |
| `initiator: str` / `""` | `control.initiator_id fk → initiator` + `initiator_text` | `""` → NULL | сопоставление по канону кластера (F-11); неизвестное имя = запись справочника `from_data` | ≤120 | число записей на кластер до/после | `controls_data.py:717–813` |
| `content: str` / `""` | `control.content text` | `""` → `""` | без изменений (парсер при миграции НЕ запускать — F-12) | — | побайтовое сравнение | `controls_models.py:368` |
| `executors: List[str]` / `[]` | `control_executor(control_id, person_id, ordinal)` | `[]` | ФИО → `person_id` по таблице соответствий (F-06); неразрешённые → `unresolved_assignee` | без дубля `person_id` | число связей + список неразрешённых | `:369` |
| `controller: str` / `""` | `control.controller_id fk null` + `controller_text` | `""` → NULL | как `executors`, один элемент | роль `controller` не обязательна (F-14) | то же | `:370` |
| `control_type: "once" / "periodic"` / `"once"` | `control.control_type enum` | неизвестное → `once` + `legacy_invalid_type` | словарь 1-в-1 | enum | распределение по типам | `:11–12`, `:423` |
| `period_days: int` / `7` | `control.period_days int` | `0`/null → `NULL` (7 — UI-дефолт, не данные) | ничего: это ДНИ (30 ≠ месяц, 91 ≠ квартал, 182 ≠ полугодие календарное) | 1…3650 при создании; исторические 0/7 сохраняются | сравнение значений + отчёт нестандартных | `:372`, `controls_tab.py:216–226` |
| `due_date: date-str` / `None` | `control.due_date date null` | `None` → NULL (это «без срока») | ISO | валидная дата | сверка NULL-паттерна | `:373` |
| `end_date: date-str` / `None` | `control.end_date date null` (для обоих типов) | `None` → NULL | ISO; у разового = «срок разового контроля», не удалять (R05) | если задан — ≥ `receive_date` или предупреждение **[Владелец]** | сверка значений | `:374`, `controls_exporter.py:90–104` |
| `done: bool` / `False` | `control.done bool` | — | 1-в-1 | — | число `done` совпадает | `:375` |
| `done_date: date-str` / `None` | `control.done_date date null` | `None` допустимо при `done=True` (в legacy бывает) | ISO | `done=True ⇒ done_date` — рекомендовано, не обязательно (см. `_done_text`) | сверка пар | `:376`, `controls_exporter.py:112–121` |
| `comment: str` / `""` | `control.comment text` | `""` → `""` | без изменений | — | побайтовое сравнение | `:377` |
| `tasks: List[ControlTask]` / `[]` | `control_task(...)` + `ordinal` | `[]` | см. §2 | см. §2 | число пунктов и порядок | `:378` |
| `milestones: List[ControlMilestone]` / `[]` | `control_milestone(...)` + `ordinal` | `[]` | см. §3 | см. §3 | число точек | `:379` |
| `attachments: List[str]` (`"<control_id>/<имя>"`) / `[]` | `control_attachment(id, control_id, filename, size, sha256, ordinal, storage_key, created_at, created_by)` | `[]` | см. §4 и F-15 | существование файла в хранилище | побайтовая сверка + нет сирот | `:380`, `controls_data.py:963–1053` |
| `archived: bool` / `False` | `control.archived_at timestamptz null` (+ `archive_reason`) | — | флаг + дата + причина сворачиваются в «архив = дата не NULL» **[Пред]** | `archived=true, archived_at` пустой → NULL + пометка | число архивных и разбивка по причинам | `:381–383`, `controls_data.py:831–846` |
| `archived_at: datetime-str` / `None` | `control.archived_at timestamptz null` | `None` | naive → пояс организации (F-08) | — | сверка | `:382` |
| `archive_reason: "done" / "deleted" / ""` / `""` | `control.archive_reason enum(done, deleted, none)` | `""` → `none` | 1-в-1; неизвестная строка → `none` + флаг | enum | распределение | `:24–25`, `:383` |
| `created_at: datetime-str` / now | `control.created_at timestamptz` | отсутствующее в legacy = «сейчас» при загрузке → `created_at_source='backfilled'` | naive → tz (пометить `tz_assumed`) | — | сравнение дат + отчёт backfilled | `:384`, `:436` |
| `updated_at: datetime-str` / now | `control.updated_at timestamptz` + `control.revision int default 0` | см. выше | историческое значение — «данные»; `revision` с 0, НЕ выводить из `updated_at` | — | контрольная выборка 20 записей | `:385`, `controls_data.py:1149–1169` |

Дополнительно **[Пред]**: `control.legacy_raw jsonb` — исходный объект JSON целиком (страховка
от потери неизвестных ключей, R02); `control.created_via enum(manual, import, migrated)` и
производный признак `missing_scan` (F-10).

## 2. `ControlTask` — 7 полей

Источник: `core/controls_models.py:119–155`.

| Legacy | Новая | Null / пустое | Преобразование | Валидация | Проверка | Источник |
|---|---|---|---|---|---|---|
| `id: uuid-str` (перевыдаётся при загрузке, если отсутствовал) | `control_task.id uuid pk` | `None` → uuid + флаг | сохранить существующий | canonical UUID | сверка id, где они были | `:121`, `:141–155` |
| `title: str` | `control_task.title text` | `""` — в legacy пункт МОЛЧА не сохраняется | без изменений | не пустой **[Пред: 422]** | сравнение непустых | `:122`, `controls_tab.py:3766–3769` |
| `assignees: List[str]` | `control_task_assignee(task_id, person_id, ordinal)` | `[]` (пункт без ответственного легален) | ФИО → `person_id` (F-06) | — | число связей | `:123` |
| `due_date: date-str` | `control_task.due_date date null` | `None` → NULL | ISO | валидная дата | сверка | `:124` |
| `is_done: bool` | `control_task.is_done bool` | — | 1-в-1 | — | распределение | `:125` |
| `done_date: date-str` | `control_task.done_date date null` | `None` | ISO | `is_done=false ⇒ done_date=NULL` (нормализовать с пометкой) | контрольная выборка | `:126`, `controls_tab.py:2907–2913` |
| `comment: str` | `control_task.comment text` | `""` | без изменений | длина (предложение ≤2000) | побайтовое | `:127` |
| — (порядок = позиция в списке) | `control_task.ordinal smallint` | — | `enumerate` при миграции | unique `(control_id, ordinal)` | сверка порядков | **[Код]** поля нет; `:378` |

## 3. `ControlMilestone` — 4 поля

Источник: `core/controls_models.py:336–360`.

| Legacy | Новая | Null / пустое | Преобразование | Валидация | Проверка | Источник |
|---|---|---|---|---|---|---|
| `id: uuid-str` | `control_milestone.id uuid pk` | — | **перевыдаётся при каждом сохранении карточки** (`controls_tab.py:3784`) → при миграции присвоить ОДИН id и больше не менять | canonical UUID | повторное сохранение не меняет id | `:338` |
| `date: date-str` | `control_milestone.date date null` | `None` легально, если есть `note` | ISO | валидная дата | сверка | `:339` |
| `note: str` | `control_milestone.note text` | `""` | без изменений | — | побайтовое | `:340` |
| `is_done: bool` | `control_milestone.is_done bool` | — | 1-в-1 | — | распределение | `:341` |
| — | `control_milestone.ordinal smallint` | — | позиция при миграции | unique | — | **[Код]** поля порядка нет |

Строка без даты и без примечания в legacy не сохраняется (`controls_tab.py:3781–3783`); при
миграции такие (если встретятся в JSON) переносятся с пометкой в отчёте, а не удаляются.

## 4. Вложения: относительные пути → хранилище

**[Код]** `Control.attachments` — список строк `"<control_id>/<filename>"`
(`copy_attachment_to_local` `core/controls_data.py:963–984`,
`copy_attachment_to_shared_ex` `:986–1026`). Файлы лежат в двух местах:
`%APPDATA%\porayonka\controls_attachments\<id>\` и
`<shared>\controls_attachments\<id>\`, при чтении приоритет shared
(`resolve_attachment` `:1066–1082`). Коллизия имён — суффикс `_1`, `_2`
(`_unique_filename` `:1043–1053`); дедуп при слиянии дублей удаляет побайтовые копии
(`_same_bytes` `controls_dedup.py:265–281`).

| Legacy | Новая | Правила |
|---|---|---|
| элемент `attachments[i]` | `control_attachment` (id, control_id, filename, ordinal, size, sha256, content_type, storage_key, created_at, created_by) | `filename` = базовое имя; `ordinal` = позиция; `sha256` считается при импорте |
| физический файл (shared и/или локально) | объект закрытого хранилища сервера, имя генерирует сервер (`storage_key`) | брать версию из shared, если есть, иначе локальную; при РАЗЛИЧИИ байтов — shared как канон + строка отчёта **[Пред]** |
| `<id>/<имя>`, файла нет | `control_attachment.missing=true`, пустой файл не создавать | битые ссылки переносятся как признак проблемы, не удаляются молча |
| файл в папке контроля, которого нет в списке | `orphan` → отчёт; в хранилище не публикуется до решения **[Владелец]** | в legacy чистятся только `.tmp` старше 600 с (`_sweep_stale_tmp`) |

Ограничения legacy, которые нельзя потерять: расширения `.pdf .png .jpg .jpeg`
(`controls_data.py:47`), предупреждение >20 МБ (`:46`), отсутствие жёсткого лимита и MIME-проверки
**[Код]**.

## 5. Настройки (`controls_settings.json`)

**[Код]** `DEFAULT_SETTINGS` `core/controls_data.py:28–45`; `load_settings` `:231–275`
(сохраняет ВСЕ ключи, включая неизвестные), `save_settings` `:276–294`.

| Ключ / тип / default | Назначение в legacy | Куда в новой системе | Примечание |
|---|---|---|---|
| `soon_days: int = 3` | порог «Скоро» | `settings_department.soon_days` (admin) | в статусе `max(0, …)`, в модалке `max(1, …)` — зафиксировать одно **[Пред]** |
| `network_enabled: bool = True` | сетевой режим | **не переносить** | инфраструктура (D-01/N-01) |
| `network_role: "admin" / "user"` | роль | **не переносить** | роль из аутентификации |
| `network_user: str` | «кто я» по ФИО | **не переносить** | привязка по `person_id` |
| `network_shared_path: str` | UNC общей папки (дефолт `DEFAULT_NETWORK_PATH` `:25`) | **не переносить** | содержит реальный хост/каталог — не воспроизводить |
| `custom_initiators: List[str]` | пользовательские инициаторы | `initiator` (admin) | + значения «из данных» (F-11) |
| `extra_people: List[str]` | доп. ФИО | `person` (`source='extra'`) | роль по умолчанию `executor` |
| `hidden_people: List[str]` | скрытые базовые ФИО | `person.is_active=false` | не удалять, иначе потеряем переименования |
| `person_roles: {ФИО: [roles]}` | роли «И»/«К» | `person_role(person_id, role)` | неизвестные роли отбрасываются (F-13) |
| `init_renames: {стар: нов}` | переименование кластера | `initiator.name` + `initiator_alias` | сопоставление по старому канону (F-11) |
| `hidden_init_groups: List[str]` | скрытые кластеры | `initiator.is_active=false` | — |
| `notify_log: {"<id>:<status>": "YYYY-MM-DD"}` | антиспам персональных | `notification_state(user_id, control_id, kind, last_at)` **[Пред]** | сегодня журнал на машину → дубли (R20) |
| `notify_sound: bool` | звук | `user_pref.sound_enabled` | у user-редакции принудительно включён (`controls_settings_modal.py:186–196`) |
| `alarm_log: {<id>: iso-dt}` (нет в дефолтах) | журнал «злого» аларма | `notification_state` + интервалы | 2 ч / 24 ч — `settings_department` **[Пред]** |
| `alarm_enabled` (читается, не пишется) | вкл/выкл аларма | реализовать в UI или удалить | **[Код]** `controls_tab.py:5701` |
| `col_widths: {col: px}` | ширины колонок | `user_pref` / localStorage | клиентское предпочтение, не в БД **[Пред]** |
| `card_width`, `card_height` | размер карточки | `user_pref.card_size` | то же |
| `refs_width`, `refs_height` | размер окна справочников | `user_pref.refs_size` | то же |
| посторонние ключи | любые | `settings_legacy_raw jsonb` | **[Код]** `load_settings` сохраняет, `Control.from_dict` — нет |

## 6. Специальные правила переноса

**F-01. Существующие UUID.** `control.id`, `control_task.id`, `control_milestone.id`
переносятся как есть. Предпроверки: валидность формата, уникальность, число записей без
`id`. Основание: legacy уже «лечил» отсутствующие id по рабочим данным
(`core/controls_data.py:182–212`)**[Код]**, повторять лечение при каждой миграции нельзя —
можно отвязать вложения.

**F-02. Пустые и дублирующиеся `id`.** (a) `id` отсутствует → брать значение из общего
префикса папки вложений (`_attachments_prefix` `:169–180`), иначе новый uuid, и записать в
отчёт; (b) одинаковый `id` у нескольких записей → union по `id` с приоритетом большего
`updated_at` (`controls_dedup.py:369–381`, `controls_data.py:1170–1199`) + строка отчёта
`duplicate_id`; (c) `id` не-UUID → сохранить строку в `legacy_id_raw`, выдать новый uuid,
связь не терять. UNIQUE в новой схеме — только на `control.id`.

**F-03. Порядок записей.** В legacy — позиция в массиве JSON (`save_controls` пишет список
как есть) и она сохраняется при merge («local-порядок, новые из shared — в конец»,
`controls_data.py:1170–1199`). **[Не проверено]**, значим ли порядок для пользователя;
предложение — ordinal не переносить, сортировка явная (R10).

**F-04. Порядок пунктов и точек.** Определяется позицией в списке **[Код]**
(`Control.tasks` `:378`, `Control.milestones` `:379`; UI пересобирает без сортировки).
При миграции `ordinal = i`; при операциях — явное изменение порядка (перетаскивание
**[Пред]**). Слияние дублей добавляло пункты loser-записей в конец
(`controls_dedup.py:196–209`) — это уже применённое состояние, повторно не делать.

**F-05. Колонка «№».** **[Код]** позиция в отфильтрованном списке
(`for i, ctl in enumerate(visible, 1)`, `controls_tab.py:1477–1479`), stored-поля нет;
`next_control_number` (`controls_data.py:359`) — мёртвый код, нигде не вызывается.
Переносить нечего; в новой системе «№» — номер в пределах страницы, не идентификатор.

**F-06. Строки ФИО → `person_id`.** Канон источника: `get_all_people_names`
(`controls_data.py:388–419`) = криминалисты зональной вкладки
(`core/zonal_data.py:309` → `Criminalist.full_name`, `id` — целый номер
`core/zonal_models.py:60–64`, NOT stable across departments) + `DEFAULT_CONTROLLERS`
(`:18`) + `extra_people` минус `hidden_people`. Алгоритм миграции **[Пред]**:

1. нормализация строки (`_person_norm` + casefold + `_norm_person_name`
   `controls_models.py:193–199`);
2. уникальное совпадение → автоматическая привязка;
3. совпадений нет → создать `person` (`source='from_data'`, `confirmed=false`) + строка
   отчёта; НЕ привязывать к первому похожему;
4. совпадений >1 → `unresolved_assignment`, применяется только после решения админа;
5. нечёткое совпадение (`name_matches` `:89–116`) — только подсказка в отчёте; никогда не
   участвует в решениях о доступе.

**F-07. Однофамильцы.** **[Код]** справочник дедуплицируется ПО ФАМИЛИИ
(`controls_data.py:410–417`) — второй «Кузнецов» исчезает из справочника; плюс `name_matches`
матчит по подстроке фамилии → «Кузнецов А.А.» матчит «Кузнецов Б.Б.». Требование:
различать людей по `person_id`, при коллизии — уточняющее отображение; миграция обязана
разрешить коллизии до переключения (W02 — схема, W07 — отчёт, W08 — приёмка).

**F-08. `timestamptz` vs `date`.**
- календарные сроки (`*_date`) — тип `date`, НЕ конвертируются в UTC и не зависят от пояса
  пользователя **[Пред]**;
- моменты (`created_at`, `updated_at`, `archived_at`) — в legacy naive `datetime.now()`;
  при миграции интерпретировать как локальное время организации (предложение
  `Europe/Moscow`, **[Владелец]**) и помечать `tz_assumed=true`;
- `merge_controls` трактовал naive-ISO как UTC (`controls_data.py:1149–1169`) — это касалось
  только порядка слияния, в новой системе слияния нет;
- `notify_log` хранит ДАТУ, `alarm_log` — datetime **[Код]**: при переносе не смешивать.

**F-09. Статусы не хранятся.** Все семь вычисляются (`deadline_status`,
`user_deadline_status`) **[Код]**. В новой БД — производные; для сортировки/фильтрации
допустим вычисляемый индекс, но не поле-источник.

**F-10. Признак «Без скана».** **[Код]** в UI выводится из
`not attachments and not archived and not done and не user-редакция`
(`controls_tab.py:1305`). В новой системе — производный по `count(attachments)=0`; обязателен
`control.created_via`, чтобы корректно применить скан-гард (R13) и отчёт.

**F-11. Инициаторы: кластеры и переименования.** **[Код]**
`canonical_initiator_group` (`controls_data.py:717–766`) схлопывает варианты, склейки
разбивает; `init_renames` меняет только отображение (`initiator_filter_group`
`:802–813`). Миграция **[Пред]**: `initiator(id, name, is_active)` +
`initiator_alias(initiator_id, legacy_text, canon)`; контроль хранит `initiator_id` +
`initiator_text`. Правило фильтра «значение = канон группы» сохраняется, иначе счётчики
съедут.

**F-12. Содержание и распознанные пункты.** **[Код]** при импорте содержание МУТИРУЕТСЯ
парсером: вырезается весь диапазон между первым и последним потреблённым фрагментом, включая
нераспознанный текст (`controls_models.py:301–304`; подтверждено прогоном — R18, S-16).
Требование к миграции: переносить `content` из `controls.json` ТАК, как он лежит (парсер не
запускать — он уже применялся), расхождения выводить в отчёт «в содержании есть признаки
пунктов» **[Пред]**.

**F-13. Неизвестные роли и поля.** **[Код]** `get_person_roles` отбрасывает роли вне
`VALID_PERSON_ROLES = ("executor", "controller")` (`controls_data.py:420`, `:430–488`);
`Control.from_dict` отбрасывает неизвестные ключи JSON молча. Требование:
`person_role.role` — enum; неизвестное значение → строка отчёта `unknown_role`;
неизвестные ключи → `control.legacy_raw`.

**F-14. Контролёр вне справочника.** **[Код]** `get_controller_names` (`:512–521`) возвращает
только лица с ролью `controller`, но текущее значение контроля всегда добавляется опцией,
иначе оно терялось бы при сохранении (`controls_tab.py:2700–2712`). Требование:
`controller_text` + опциональный `controller_id`; UI предлагает «завести в справочник», не
стирая значение **[Пред]**.

**F-15. Относительные пути файлов и одинаковые имена.** **[Код]** путь —
`<control_id>/<filename>`; разрешается ТОЛЬКО базовым именем
(`Path(rel).name` `controls_data.py:859`, `:1073`) — traversal закрыт; одно имя в папке
контроля = «уже прикреплено» (`controls_tab.py:371–389`), разные файлы получают
`имя_1.ext`. Требования миграции: `storage_key` — серверное имя (sha256 или uuid),
`filename` — оригинал (кириллица, пробелы); два файла с одинаковым именем и разными байтами =
две записи; идентичные байты = одна. Путы вида `<другой_id>/<имя>` (остались после
`merge_duplicate_group`) разрешать по факту существования файла, а не по префиксу **[Пред]**.

**F-16. Архивные и удалённые записи.** **[Код]** hard delete удаляет и файлы, и запись
(`controls_tab.py:4431–4456`); «удалённые» помеченных записей в JSON нет. Отличить
«удалено навсегда» от «потеряно» можно только по `.bak`/снапшотам
(`controls_data.py:132–160`, `backup.py:219–274`). Нужна ли история удалений — **[Владелец]**;
по умолчанию — только отчёт по снапшотам.

**F-17. Что не переносим.** Обёртку файла (`schema_version`, `last_saved`), поля редакции
(`role`, `user_name`, `password`, `password_hash` в `edition.json`,
`core/edition.py:251–444`), `network_*`. Переносить пароли/хеши из `edition.json` в аккаунты
НЕЛЬЗЯ: там допускается plain-text и base64(sha256(фиксированная соль|пароль))
(`:541–571`)**[Код]**; сервер — штатный хеш (D-06).

## 7. Контрольные сверки (критерии полноты переноса)

1. Число записей `controls`, `tasks`, `milestones`, `attachments` совпадает с источником за
   вычетом ЯВНО перечисленных слияний (каждое — строка отчёта).
2. Для 100 % записей: 22 поля = значение из legacy (или NULL/пустое, если было пустым).
3. Ни одно непустое текстовое значение не стало пустым; ни один `id` не перевыдан
   (кроме F-02(a) с пометкой).
4. Число неразрешённых ФИО = 0 после ручного разбора; до переключения — блокирующий отчёт.
5. Для каждого вложения: файл существует, `sha256` совпадает, `filename` совпадает побайтово.
6. Распределения `control_type`, `period_days`, `done`, `archived`/`archive_reason` совпадают.
7. Обратный контроль: полный Excel-экспорт мигрированной базы ↔ экспорт legacy по 19
   колонкам (за вычетом F-12 и S-07).
8. Повторный запуск миграции идемпотентен (0 изменений) — условие W07.

-- controls-web: схема стенда W01 (синтетические данные).
-- Это НЕ рабочая схема миграции: полный mapping полей и миграции legacy-данных — W02+.
-- Состав полей выбран по migration-web/field-mapping.md, чтобы W02 не переделывал структуру.

CREATE TABLE IF NOT EXISTS controls (
    id               uuid PRIMARY KEY,
    incoming_number  text NOT NULL,
    receive_date     date,
    due_date         date,
    done             boolean NOT NULL DEFAULT false,
    archived         boolean NOT NULL DEFAULT false,
    control_type     text NOT NULL DEFAULT '',
    initiator        text NOT NULL DEFAULT '',
    content          text NOT NULL DEFAULT '',
    executor         text NOT NULL DEFAULT '',
    controller       text NOT NULL DEFAULT '',
    department       text NOT NULL DEFAULT '',
    priority         text NOT NULL DEFAULT 'обычный',
    note             text NOT NULL DEFAULT '',
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    -- исходный словарь legacy сохраняется целиком (правило field-mapping.md: unknown-поля не терять)
    legacy_raw       jsonb
);

CREATE TABLE IF NOT EXISTS control_tasks (
    id          uuid PRIMARY KEY,
    control_id  uuid NOT NULL REFERENCES controls(id) ON DELETE CASCADE,
    position    integer NOT NULL,
    text        text NOT NULL,
    due_date    date,
    done        boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS attachments (
    id            uuid PRIMARY KEY,
    control_id    uuid REFERENCES controls(id) ON DELETE CASCADE,
    rel_path      text NOT NULL,
    file_name     text NOT NULL,
    size_bytes    bigint NOT NULL,
    sha256        text NOT NULL,
    content_type  text NOT NULL DEFAULT 'application/octet-stream',
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (control_id, rel_path)
);

-- журнал наполнения: подтверждение воспроизводимости seed
CREATE TABLE IF NOT EXISTS seed_meta (
    id               integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    seed             bigint NOT NULL,
    requested_count  integer NOT NULL,
    controls_count   integer NOT NULL,
    tasks_count      integer NOT NULL,
    digest           text NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now()
);

-- порядок сортировки списка должен совпадать с ORDER BY запроса, иначе пагинация нестабильна
CREATE INDEX IF NOT EXISTS controls_list_order_idx
    ON controls (receive_date DESC NULLS LAST, incoming_number DESC NULLS LAST, id DESC);
CREATE INDEX IF NOT EXISTS controls_incoming_number_idx ON controls (incoming_number);
CREATE INDEX IF NOT EXISTS controls_done_archived_idx ON controls (done, archived);
CREATE INDEX IF NOT EXISTS control_tasks_control_idx ON control_tasks (control_id, position);
CREATE INDEX IF NOT EXISTS attachments_control_idx ON attachments (control_id);

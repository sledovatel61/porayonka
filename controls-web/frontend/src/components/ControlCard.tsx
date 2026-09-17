import { useState } from 'react';
import type { ControlCardData } from '../types';
import { formatBytes, formatDateLong, formatDateTime, statusLabel } from '../format';

interface Props {
  card: ControlCardData | null;
  loading: boolean;
  uploadEnabled: boolean;
  onClose: () => void;
  onUploaded: () => void;
}

/** Карточка записи. Только чтение; загрузка PDF — временная функция стенда W01. */
export default function ControlCard({ card, loading, uploadEnabled, onClose, onUploaded }: Props) {
  const [message, setMessage] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  if (loading && !card) {
    return (
      <aside className="card-panel">
        <div className="card-placeholder">Загрузка карточки…</div>
      </aside>
    );
  }
  if (!card) {
    return (
      <aside className="card-panel">
        <div className="card-placeholder">
          Выберите запись в списке, чтобы открыть карточку для чтения.
        </div>
      </aside>
    );
  }

  const fields: Array<[string, string]> = [
    ['Номер', card.incoming_number],
    ['Статус', statusLabel({ ...card, tasks_total: card.tasks.length, tasks_done: 0, attachments_total: card.attachments.length })],
    ['Тип', card.control_type],
    ['Получено', formatDateLong(card.receive_date)],
    ['Срок', formatDateLong(card.due_date)],
    ['Приоритет', card.priority],
    ['Инициатор', card.initiator],
    ['Исполнитель', card.executor],
    ['Контролёр', card.controller],
    ['Подразделение', card.department],
    ['Создано', formatDateTime(card.created_at)],
    ['Изменено', formatDateTime(card.updated_at)],
  ];

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    setUploading(true);
    setMessage(null);
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('control_id', card!.id);
      const response = await fetch('/api/w01-test/uploads', { method: 'POST', body: form });
      const body = await response.json();
      if (!response.ok) {
        const text = body && body.error ? body.error.message : `Ошибка ${response.status}`;
        setMessage(`Файл не принят: ${text}`);
      } else {
        const name = body.attachment ? body.attachment.file_name : file.name;
        setMessage(`Файл «${name}» ${body.created ? 'загружен' : 'уже был загружен ранее'}.`);
        onUploaded();
      }
    } catch {
      setMessage('Не удалось передать файл: нет связи со стендом.');
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  }

  return (
    <aside className="card-panel">
      <header className="card-header">
        <h2 className="card-title">{card.incoming_number}</h2>
        <button type="button" className="btn btn-ghost" onClick={onClose} aria-label="Закрыть карточку">
          Закрыть
        </button>
      </header>

      <dl className="card-fields">
        {fields.map(([label, value]) => (
          <div className="card-field" key={label}>
            <dt>{label}</dt>
            <dd>{value || '—'}</dd>
          </div>
        ))}
      </dl>

      <section className="card-section">
        <h3>Содержание</h3>
        <p className="card-content">{card.content || '—'}</p>
        {card.note ? <p className="card-note">Примечание: {card.note}</p> : null}
      </section>

      <section className="card-section">
        <h3>Пункты ({card.tasks.length})</h3>
        {card.tasks.length === 0 ? (
          <p className="card-empty">Пункты не заданы.</p>
        ) : (
          <ol className="tasks">
            {card.tasks.map((task) => (
              <li key={task.id} className={task.done ? 'task done' : 'task'}>
                <span className="task-text">{task.position}) {task.text}</span>
                <span className="task-meta">
                  {formatDateLong(task.due_date)}
                  {task.done ? ' · исполнено' : ''}
                </span>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="card-section">
        <h3>Вложения ({card.attachments.length})</h3>
        {card.attachments.length === 0 ? (
          <p className="card-empty">Вложений нет.</p>
        ) : (
          <ul className="files">
            {card.attachments.map((attachment) => (
              <li key={attachment.id}>
                <a className="file-link" href={attachment.download_url || '#'} download={attachment.file_name}>
                  {attachment.file_name}
                </a>
                <span className="file-meta">
                  {formatBytes(attachment.size_bytes)} · sha256 {attachment.sha256.slice(0, 12)}…
                </span>
              </li>
            ))}
          </ul>
        )}

        {uploadEnabled ? (
          <div className="stand-block">
            <p className="stand-warning">
              Временная функция стенда W01: загрузка синтетического PDF. Будет удалена до передачи W02.
            </p>
            <label className="file-input" htmlFor="upload-pdf">
              Выбрать PDF и загрузить
              <input
                id="upload-pdf"
                type="file"
                accept="application/pdf,.pdf"
                disabled={uploading}
                onChange={handleUpload}
              />
            </label>
            <a className="btn" href="/api/w01-test/sample-pdf">
              Скачать синтетический PDF
            </a>
            {message ? <p className="stand-message">{message}</p> : null}
          </div>
        ) : null}
      </section>
    </aside>
  );
}

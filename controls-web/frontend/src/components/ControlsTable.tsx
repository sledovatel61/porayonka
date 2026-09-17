import type { ControlListItem } from '../types';
import { dueLabel, dueStatus, formatDate, statusLabel } from '../format';

interface Props {
  items: ControlListItem[];
  loading: boolean;
  selectedId: string | null;
  today: Date;
  onSelect: (item: ControlListItem) => void;
}

export default function ControlsTable({ items, loading, selectedId, today, onSelect }: Props) {
  if (loading && items.length === 0) {
    return <div className="table-placeholder">Загрузка списка…</div>;
  }
  if (items.length === 0) {
    return <div className="table-placeholder">Записи не найдены. Измените поиск или снимите фильтр архива.</div>;
  }

  return (
    <div className="table-wrap" aria-busy={loading}>
      <table className="table">
        <thead>
          <tr>
            <th scope="col" className="col-number">Номер</th>
            <th scope="col" className="col-date">Получено</th>
            <th scope="col" className="col-date">Срок</th>
            <th scope="col" className="col-type">Тип</th>
            <th scope="col" className="col-initiator">Инициатор</th>
            <th scope="col" className="col-person">Исполнитель</th>
            <th scope="col" className="col-person">Контролёр</th>
            <th scope="col" className="col-tasks">Пункты</th>
            <th scope="col" className="col-files">Файлы</th>
            <th scope="col" className="col-status">Статус</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.id}
              className={item.id === selectedId ? 'row selected' : 'row'}
              onClick={() => onSelect(item)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  onSelect(item);
                }
              }}
              tabIndex={0}
              role="button"
              aria-pressed={item.id === selectedId}
            >
              <td className="col-number mono">{item.incoming_number}</td>
              <td className="col-date">{formatDate(item.receive_date)}</td>
              <td className={`col-date due-${dueStatus(item, today)}`}>{dueLabel(item, today)}</td>
              <td className="col-type">{item.control_type}</td>
              <td className="col-initiator">{item.initiator}</td>
              <td className="col-person">{item.executor}</td>
              <td className="col-person">{item.controller}</td>
              <td className="col-tasks">
                {item.tasks_total > 0 ? `${item.tasks_done}/${item.tasks_total}` : '—'}
              </td>
              <td className="col-files">{item.attachments_total > 0 ? item.attachments_total : '—'}</td>
              <td className="col-status">{statusLabel(item)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

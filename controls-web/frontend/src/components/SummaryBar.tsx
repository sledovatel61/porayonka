import type { Summary } from '../types';
import { pluralRu } from '../format';

interface Props {
  summary: Summary | null;
  loading: boolean;
}

export default function SummaryBar({ summary, loading }: Props) {
  const items: Array<{ label: string; value: number | null; tone: string }> = [
    { label: 'Всего', value: summary ? summary.total : null, tone: 'neutral' },
    { label: 'В работе', value: summary ? summary.active : null, tone: 'accent' },
    { label: 'Исполнено', value: summary ? summary.done : null, tone: 'ok' },
    { label: 'Просрочено', value: summary ? summary.overdue : null, tone: 'danger' },
    { label: 'В архиве', value: summary ? summary.archived : null, tone: 'muted' },
    { label: 'С вложениями', value: summary ? summary.with_attachments : null, tone: 'muted' },
  ];

  return (
    <div className="summary" aria-busy={loading}>
      {items.map((item) => (
        <div className={`summary-item tone-${item.tone}`} key={item.label}>
          <span className="summary-value">{item.value === null ? '…' : item.value}</span>
          <span className="summary-label">{item.label}</span>
        </div>
      ))}
      <div className="summary-note">
        {summary
          ? `${pluralRu(summary.total, 'запись', 'записи', 'записей')} в базе стенда`
          : 'Загрузка счётчиков…'}
      </div>
    </div>
  );
}

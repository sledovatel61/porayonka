/** Форматирование дат и статусов для русского интерфейса. */
import type { ControlListItem } from './types';

const MONTHS_GENITIVE = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
];

/** ISO-дата (YYYY-MM-DD) -> DD.MM.YYYY; пустое значение -> «Без срока». */
export function formatDate(value: string | null): string {
  if (!value) return '—';
  const parts = value.split('-');
  if (parts.length !== 3) return value;
  return `${parts[2]}.${parts[1]}.${parts[0]}`;
}

export function formatDateLong(value: string | null): string {
  if (!value) return '—';
  const parts = value.split('-');
  if (parts.length !== 3) return value;
  const day = Number(parts[2]);
  const monthIndex = Number(parts[1]) - 1;
  const month = MONTHS_GENITIVE[monthIndex];
  return month ? `${day} ${month} ${parts[0]}` : value;
}

export function formatDateTime(value: string | null): string {
  if (!value) return '—';
  return value.replace('T', ' ').slice(0, 19);
}

export function formatBytes(value: number): string {
  if (value < 1024) return `${value} Б`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} КБ`;
  return `${(value / (1024 * 1024)).toFixed(1)} МБ`;
}

export type DueStatus = 'none' | 'done' | 'overdue' | 'today' | 'week' | 'future';

export function dueStatus(item: ControlListItem, today: Date): DueStatus {
  if (item.done) return 'done';
  if (!item.due_date) return 'none';
  const parts = item.due_date.split('-');
  const due = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
  const midnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const days = Math.round((due.getTime() - midnight.getTime()) / 86400000);
  if (days < 0) return 'overdue';
  if (days === 0) return 'today';
  if (days <= 7) return 'week';
  return 'future';
}

export function dueLabel(item: ControlListItem, today: Date): string {
  const status = dueStatus(item, today);
  if (status === 'none') return 'Без срока';
  if (status === 'done') return 'Исполнено';
  if (status === 'overdue') return 'Просрочено';
  if (status === 'today') return 'Сегодня';
  return formatDate(item.due_date);
}

export function statusLabel(item: ControlListItem): string {
  if (item.archived) return 'В архиве';
  if (item.done) return 'Исполнено';
  return 'В работе';
}

export function pluralRu(count: number, one: string, few: string, many: string): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few;
  return many;
}

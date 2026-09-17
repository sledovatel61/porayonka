/** Клиент API стенда. Таймаут 15 с (паритет с legacy), ошибки — на русском. */
import type { ControlCardData, ControlsPage, Health, ListQuery, Summary } from './types';

export const REQUEST_TIMEOUT_MS = 15000;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export interface ApiResult<T> {
  data: T;
  serverMs: number | null;
}

async function request<T>(path: string): Promise<ApiResult<T>> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(path, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    });
  } catch (error) {
    const reason = error instanceof Error && error.name === 'AbortError' ? 'timeout' : 'network';
    throw new ApiError(
      0,
      reason,
      reason === 'timeout'
        ? 'Сервер не ответил за 15 секунд. Проверьте подключение к стенду.'
        : 'Нет связи со стендом. Проверьте сеть и повторите запрос.',
    );
  } finally {
    clearTimeout(timer);
  }

  const header = response.headers.get('X-Process-Time-Ms');
  const serverMs = header ? Number.parseFloat(header) : null;

  if (!response.ok) {
    let message = `Сервер вернул ошибку ${response.status}.`;
    let code = 'http_error';
    try {
      const body = (await response.json()) as { error?: { code?: string; message?: string } };
      if (body && body.error) {
        message = body.error.message || message;
        code = body.error.code || code;
      }
    } catch {
      /* тело ошибки не JSON — оставляем стандартное сообщение */
    }
    throw new ApiError(response.status, code, message);
  }

  const data = (await response.json()) as T;
  return { data, serverMs: serverMs !== null && Number.isFinite(serverMs) ? serverMs : null };
}

export function listControls(query: ListQuery): Promise<ApiResult<ControlsPage>> {
  const params = new URLSearchParams();
  params.set('page', String(query.page));
  params.set('page_size', String(query.pageSize));
  if (query.search.trim()) params.set('search', query.search.trim());
  if (query.includeArchived) params.set('include_archived', 'true');
  return request<ControlsPage>(`/api/controls?${params.toString()}`);
}

export function getControl(id: string): Promise<ApiResult<ControlCardData>> {
  return request<ControlCardData>(`/api/controls/${encodeURIComponent(id)}`);
}

export function getSummary(): Promise<ApiResult<Summary>> {
  return request<Summary>('/api/meta/summary');
}

export function getHealth(): Promise<ApiResult<Health>> {
  return request<Health>('/api/health');
}

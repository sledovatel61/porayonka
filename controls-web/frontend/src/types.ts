/** Типы ответов стенда W01 (соответствуют backend/app/models.py). */

export interface ControlListItem {
  id: string;
  incoming_number: string;
  receive_date: string | null;
  due_date: string | null;
  done: boolean;
  archived: boolean;
  control_type: string;
  initiator: string;
  executor: string;
  controller: string;
  department: string;
  priority: string;
  tasks_total: number;
  tasks_done: number;
  attachments_total: number;
}

export interface ControlsPage {
  items: ControlListItem[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
  search: string | null;
  include_archived: boolean;
}

export interface TaskItem {
  id: string;
  position: number;
  text: string;
  due_date: string | null;
  done: boolean;
}

export interface AttachmentItem {
  id: string;
  control_id: string | null;
  rel_path: string;
  file_name: string;
  size_bytes: number;
  sha256: string;
  content_type: string;
  created_at: string | null;
  download_url: string | null;
}

export interface ControlCardData {
  id: string;
  incoming_number: string;
  receive_date: string | null;
  due_date: string | null;
  done: boolean;
  archived: boolean;
  control_type: string;
  initiator: string;
  content: string;
  executor: string;
  controller: string;
  department: string;
  priority: string;
  note: string;
  created_at: string | null;
  updated_at: string | null;
  tasks: TaskItem[];
  attachments: AttachmentItem[];
}

export interface Summary {
  total: number;
  active: number;
  archived: number;
  done: number;
  overdue: number;
  with_attachments: number;
}

export interface Health {
  status: 'ok' | 'degraded';
  database: 'ok' | 'unavailable';
  postgres_version: string | null;
  app_version: string;
  stand: string;
}

export interface ListQuery {
  page: number;
  pageSize: number;
  search: string;
  includeArchived: boolean;
}

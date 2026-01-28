import type { Dayjs } from 'dayjs';

export interface EventFormData {
  title: string;
  description?: string;
  start_date: Dayjs;
  end_date?: Dayjs;
  all_day: boolean;
  event_type: string;
  priority: number;
  location?: string;
  document_id?: number;
  assigned_user_id?: number;
  reminder_enabled?: boolean;
  reminder_minutes?: number;
}

export interface CalendarEventData {
  id: number;
  title: string;
  description?: string;
  start_date: string;
  end_date?: string;
  all_day: boolean;
  event_type: string;
  priority: string | number;
  location?: string;
  document_id?: number;
  doc_number?: string;
  assigned_user_id?: number;
}

export interface DocumentOption {
  id: number;
  doc_number: string;
  subject: string;
}

export interface EventFormModalProps {
  visible: boolean;
  mode: 'create' | 'edit';
  event?: CalendarEventData | null;
  onClose: () => void;
  onSuccess: () => void;
}

export const EVENT_TYPE_OPTIONS = [
  { value: 'deadline', label: '截止提醒' },
  { value: 'meeting', label: '會議安排' },
  { value: 'review', label: '審核提醒' },
  { value: 'reminder', label: '一般提醒' },
  { value: 'reference', label: '參考事件' },
] as const;

export const PRIORITY_OPTIONS = [
  { value: 1, label: '緊急', color: '#f5222d' },
  { value: 2, label: '重要', color: '#fa8c16' },
  { value: 3, label: '普通', color: '#1890ff' },
  { value: 4, label: '低', color: '#52c41a' },
  { value: 5, label: '最低', color: '#d9d9d9' },
] as const;

export interface ReminderConfig {
  minutes_before: number;
  notification_type: 'email' | 'system';
}

export interface DocumentInfo {
  id: number;
  doc_number?: string;
  subject?: string;
  doc_date?: string;
  send_date?: string;
  receive_date?: string;
  sender?: string;
  receiver?: string;
  assignee?: string;
  priority_level?: string;
  doc_type?: string;
  content?: string;
  notes?: string;
  contract_case?: string;
}

export interface IntegratedEventModalProps {
  visible: boolean;
  document?: DocumentInfo | null;
  onClose: () => void;
  onSuccess?: (eventId: number) => void;
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

export const REMINDER_TIME_OPTIONS = [
  { value: 0, label: '事件開始時' },
  { value: 5, label: '5 分鐘前' },
  { value: 15, label: '15 分鐘前' },
  { value: 30, label: '30 分鐘前' },
  { value: 60, label: '1 小時前' },
  { value: 120, label: '2 小時前' },
  { value: 480, label: '8 小時前' },
  { value: 1440, label: '1 天前' },
  { value: 2880, label: '2 天前' },
  { value: 10080, label: '1 週前' },
] as const;

export const REMINDER_TYPE_OPTIONS = [
  { value: 'system' as const, label: '系統通知' },
  { value: 'email' as const, label: '郵件通知' },
] as const;

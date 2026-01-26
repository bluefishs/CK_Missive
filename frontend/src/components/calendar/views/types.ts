/**
 * 行事曆視圖共用型別定義
 */

import type { Dayjs } from 'dayjs';

/**
 * 行事曆事件型別 - 增強版組件專用
 */
export interface CalendarEvent {
  id: number;
  title: string;
  description?: string;
  start_date: string;
  end_date: string;
  all_day?: boolean;
  event_type: 'deadline' | 'meeting' | 'review' | 'reminder' | 'reference';
  priority: number;
  status: 'pending' | 'completed' | 'cancelled';
  document_id?: number;
  assigned_user_id?: number;
  google_event_id?: string;
  google_sync_status?: 'pending' | 'synced' | 'failed';
  reminder_enabled: boolean;
  reminders?: EventReminder[];
}

/** 事件提醒 */
export interface EventReminder {
  id: number;
  reminder_time: string;
  notification_type: 'email' | 'system';
  status: 'pending' | 'sent' | 'failed';
  is_sent: boolean;
  retry_count: number;
}

/** 篩選狀態 */
export interface FilterState {
  eventTypes: string[];
  priorities: number[];
  statuses: string[];
  dateRange: [Dayjs, Dayjs] | null;
  searchText: string;
  assignedUserId?: number;
  hasReminders?: boolean;
}

/** 快速篩選類型 */
export type QuickFilterType = 'all' | 'today' | 'thisWeek' | 'upcoming' | 'overdue' | null;

/** 視圖模式 */
export type ViewMode = 'month' | 'week' | 'list' | 'timeline';

/** 統計數據 */
export interface CalendarStatistics {
  total: number;
  today: number;
  thisWeek: number;
  upcoming: number;
  overdue: number;
}

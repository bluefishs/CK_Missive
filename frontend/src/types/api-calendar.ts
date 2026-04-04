/** api-calendar — 行事曆事件/Google Calendar/統計型別 */

// ============================================================================
// 行事曆事件相關型別
// ============================================================================

/** 行事曆事件提醒 */
export interface CalendarEventReminder {
  id: number;
  reminder_time: string;
  notification_type: 'email' | 'system';
  status: 'pending' | 'sent' | 'failed';
  is_sent: boolean;
  retry_count: number;
}

/** 行事曆事件（後端 API 格式） */
export interface CalendarEvent {
  id: number;
  document_id?: number;
  title: string;
  description?: string;
  start_date: string;
  end_date?: string;
  all_day?: boolean;
  event_type?: 'deadline' | 'meeting' | 'review' | 'reminder' | 'reference' | string;
  priority?: number | string;
  location?: string;
  assigned_user_id?: number;
  created_by?: number;
  created_at?: string;
  updated_at?: string;
  // Google Calendar 整合
  google_event_id?: string;
  google_sync_status?: 'pending' | 'synced' | 'failed';
  // 提醒功能
  status?: 'pending' | 'completed' | 'cancelled';
  reminder_enabled?: boolean;
  reminders?: CalendarEventReminder[];
  // 關聯公文
  doc_number?: string;
}

/** 行事曆事件（前端 UI 格式，使用 datetime 欄位名稱） */
export interface CalendarEventUI {
  id: number;
  title: string;
  description?: string;
  start_datetime: string;
  end_datetime: string;
  all_day?: boolean;  // 全天事件
  document_id?: number;
  doc_number?: string;
  contract_project_name?: string;  // 承攬案件名稱
  event_type?: string;
  priority?: number | string;
  status?: 'pending' | 'completed' | 'cancelled';  // 事件狀態
  location?: string;
  google_event_id?: string;
  google_sync_status?: 'pending' | 'synced' | 'failed';
}

// ============================================================================
// 行事曆 API 型別 (從 calendarApi.ts 遷移)
// ============================================================================

/** Google Calendar 狀態 */
export interface GoogleCalendarStatus {
  google_calendar_available: boolean;
  connection_status: {
    status: string;
    message: string;
    calendars?: Array<{
      id: string;
      summary: string;
      primary: boolean;
    }>;
  };
  service_type: string;
  supported_event_types: Array<{
    type: string;
    name: string;
    color: string;
  }>;
  features: string[];
}

/** 事件分類 */
export interface EventCategory {
  value: string;
  label: string;
  color: string;
}

/** 行事曆統計 */
export interface CalendarStats {
  total_events: number;
  today_events: number;
  this_week_events: number;
  this_month_events: number;
  upcoming_events: number;
}

/** 行事曆完整回應 */
export interface CalendarDataResponse {
  events: CalendarEventUI[];
  googleStatus: GoogleCalendarStatus;
}

/**
 * 行事曆事件原始 API 回應格式
 * 後端回傳的原始格式，欄位名稱為 start_date/end_date
 * 用於 calendarApi 內部轉換為 CalendarEventUI
 */
export interface RawCalendarEventResponse {
  id: number;
  title: string;
  description?: string;
  start_date: string;
  end_date: string;
  all_day?: boolean;
  document_id?: number;
  doc_number?: string;
  contract_project_name?: string;
  event_type?: string;
  priority?: number | string;
  status?: 'pending' | 'completed' | 'cancelled';
  location?: string;
  google_event_id?: string;
  google_sync_status?: 'pending' | 'synced' | 'failed';
}

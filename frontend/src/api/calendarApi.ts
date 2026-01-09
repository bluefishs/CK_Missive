/**
 * 行事曆 API
 *
 * 提供行事曆事件與 Google Calendar 整合功能
 */

import { apiClient, API_BASE_URL } from './client';
import { authService } from '../services/authService';
import dayjs from 'dayjs';
import { API_ENDPOINTS } from './endpoints';

// ============================================================================
// 型別定義
// ============================================================================

/** 行事曆事件 */
export interface CalendarEvent {
  id: number;
  title: string;
  description?: string;
  start_datetime: string;
  end_datetime: string;
  document_id?: number;
  doc_number?: string;
  event_type?: string;
  priority?: number | string;
  location?: string;
  google_event_id?: string;
  google_sync_status?: 'pending' | 'synced' | 'failed';
}

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
  events: CalendarEvent[];
  googleStatus: GoogleCalendarStatus;
}

// 預設事件分類
export const DEFAULT_CATEGORIES: EventCategory[] = [
  { value: 'reminder', label: '提醒', color: '#faad14' },
  { value: 'deadline', label: '截止日期', color: '#f5222d' },
  { value: 'meeting', label: '會議', color: '#722ed1' },
  { value: 'review', label: '審查', color: '#1890ff' },
];

// ============================================================================
// API 方法
// ============================================================================

export const calendarApi = {
  /**
   * 取得行事曆事件
   */
  async getEvents(): Promise<CalendarEvent[]> {
    try {
      const api = authService.getAxiosInstance();
      const userInfo = authService.getUserInfo();
      const userId = userInfo?.id || 1;

      // 日期範圍：前2個月到後2個月
      const now = dayjs();
      const startDate = now.subtract(2, 'month').format('YYYY-MM-DD');
      const endDate = now.add(2, 'month').format('YYYY-MM-DD');

      const response = await api.post(API_ENDPOINTS.CALENDAR.USER_EVENTS, {
        user_id: userId,
        start_date: startDate,
        end_date: endDate,
      });

      const data = response.data;
      if (data && Array.isArray(data.events)) {
        return data.events.map((event: any) => ({
          id: event.id,
          title: event.title,
          description: event.description,
          start_datetime: event.start_date,
          end_datetime: event.end_date,
          document_id: event.document_id,
          doc_number: event.doc_number,
          event_type: event.event_type,
          priority: event.priority,
          location: event.location,
          google_event_id: event.google_event_id,
          google_sync_status: event.google_sync_status || 'pending',
        }));
      } else if (Array.isArray(data)) {
        return data;
      }
      return [];
    } catch (error) {
      console.warn('無法載入行事曆事件:', error);
      return [];
    }
  },

  /**
   * 取得 Google Calendar 狀態
   */
  async getGoogleStatus(): Promise<GoogleCalendarStatus> {
    try {
      const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.PUBLIC.CALENDAR_STATUS}`);
      if (response.ok) {
        const data = await response.json();
        return {
          google_calendar_available: data.google_calendar_integration || false,
          connection_status: {
            status: data.google_status?.configured ? 'connected' : 'disconnected',
            message: data.message || '狀態未知',
            calendars: data.google_status?.calendar_id
              ? [
                  {
                    id: data.google_status.calendar_id,
                    summary: 'Primary Calendar',
                    primary: true,
                  },
                ]
              : [],
          },
          service_type: data.endpoint_type || 'basic',
          supported_event_types: DEFAULT_CATEGORIES.map((c) => ({
            type: c.value,
            name: c.label,
            color: c.color,
          })),
          features: data.features || ['本地行事曆', '事件提醒'],
        };
      } else {
        return {
          google_calendar_available: false,
          connection_status: {
            status: response.status === 403 ? 'auth_required' : 'service_unavailable',
            message:
              response.status === 403
                ? '需要登入才能存取行事曆功能'
                : '行事曆服務暫時無法使用',
          },
          service_type: '行事曆管理系統',
          supported_event_types: DEFAULT_CATEGORIES.map((c) => ({
            type: c.value,
            name: c.label,
            color: c.color,
          })),
          features: ['基本行事曆檢視', '事件提醒功能', '本地事件儲存'],
        };
      }
    } catch (error) {
      console.error('獲取 Google Calendar 狀態失敗:', error);
      return {
        google_calendar_available: false,
        connection_status: { status: 'error', message: '無法連接到行事曆服務' },
        service_type: '行事曆管理系統',
        supported_event_types: DEFAULT_CATEGORIES.map((c) => ({
          type: c.value,
          name: c.label,
          color: c.color,
        })),
        features: ['基本行事曆檢視', '事件提醒功能', '本地事件儲存'],
      };
    }
  },

  /**
   * 更新事件 (POST 機制，符合資安要求)
   */
  async updateEvent(eventId: number, updates: Partial<CalendarEvent>): Promise<void> {
    try {
      const api = authService.getAxiosInstance();
      const response = await api.post(API_ENDPOINTS.CALENDAR.EVENTS_UPDATE, {
        event_id: eventId,
        title: updates.title,
        description: updates.description,
        start_date: updates.start_datetime,
        end_date: updates.end_datetime,
        event_type: updates.event_type,
        priority: updates.priority,
        location: updates.location,
        document_id: updates.document_id,
      });

      // 檢查後端回傳的 success 欄位
      if (response.data && response.data.success === false) {
        throw new Error(response.data.message || '更新事件失敗');
      }
    } catch (error) {
      console.error('更新事件失敗:', error);
      throw error;
    }
  },

  /**
   * 刪除事件
   */
  async deleteEvent(eventId: number): Promise<void> {
    try {
      const api = authService.getAxiosInstance();
      const response = await api.post(API_ENDPOINTS.CALENDAR.EVENTS_DELETE, {
        event_id: eventId,
        confirm: true,  // 後端需要 confirm: true 才會執行刪除
      });

      // 檢查後端回傳的 success 欄位
      if (response.data && response.data.success === false) {
        throw new Error(response.data.message || '刪除事件失敗');
      }
    } catch (error) {
      console.error('刪除事件失敗:', error);
      throw error;
    }
  },

  /**
   * 同步到 Google Calendar (批次同步所有未同步事件)
   */
  async bulkSync(): Promise<{ success: boolean; message: string; synced_count: number; failed_count: number }> {
    try {
      const api = authService.getAxiosInstance();
      const response = await api.post(API_ENDPOINTS.CALENDAR.EVENTS_BULK_SYNC, {
        sync_all_pending: true,
      });
      return response.data;
    } catch (error) {
      console.error('批次同步失敗:', error);
      throw error;
    }
  },

  /**
   * 同步單一事件到 Google Calendar
   */
  async syncEvent(eventId: number, forceSync: boolean = false): Promise<{ success: boolean; message: string; google_event_id?: string }> {
    try {
      const api = authService.getAxiosInstance();
      const response = await api.post(API_ENDPOINTS.CALENDAR.EVENTS_SYNC, {
        event_id: eventId,
        force_sync: forceSync,
      });
      return response.data;
    } catch (error) {
      console.error('同步事件失敗:', error);
      throw error;
    }
  },
};

export default calendarApi;

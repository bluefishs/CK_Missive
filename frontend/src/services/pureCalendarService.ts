/**
 * 純粹行事曆服務
 * 從公文系統中抽離的獨立行事曆功能
 */

import { httpClient } from './httpClient';

export interface PureCalendarEvent {
  id?: number;
  title: string;
  description?: string;
  start_datetime: string;
  end_datetime: string;
  location?: string;
  is_all_day?: boolean;
  category?: string;
  priority?: 'low' | 'normal' | 'high';
  user_id?: number;
  created_at?: string;
  updated_at?: string;
}

export interface CalendarEventCreate {
  title: string;
  description?: string;
  start_datetime: string;
  end_datetime: string;
  location?: string;
  is_all_day?: boolean;
  category?: string;
  priority?: 'low' | 'normal' | 'high';
}

export interface CalendarEventUpdate {
  title?: string;
  description?: string;
  start_datetime?: string;
  end_datetime?: string;
  location?: string;
  is_all_day?: boolean;
  category?: string;
  priority?: 'low' | 'normal' | 'high';
}

export interface CalendarStats {
  total_events: number;
  today_events: number;
  this_week_events: number;
  this_month_events: number;
  upcoming_events: number;
}

export interface EventCategory {
  value: string;
  label: string;
  color: string;
}

class PureCalendarService {
  private baseUrl = '/pure-calendar';

  /**
   * 獲取事件列表
   */
  async getEvents(params?: {
    start_date?: string;
    end_date?: string;
    category?: string;
  }): Promise<{ events: PureCalendarEvent[]; count: number; user_id: number }> {
    const queryParams = new URLSearchParams();

    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);
    if (params?.category) queryParams.append('category', params.category);

    const url = `${this.baseUrl}/events${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;

    const response = await httpClient.get(url);
    return response.data;
  }

  /**
   * 創建新事件
   */
  async createEvent(event: CalendarEventCreate): Promise<PureCalendarEvent> {
    const response = await httpClient.post(`${this.baseUrl}/events`, event);
    return response.data;
  }

  /**
   * 更新事件
   */
  async updateEvent(eventId: number, eventUpdate: CalendarEventUpdate): Promise<PureCalendarEvent> {
    const response = await httpClient.put(`${this.baseUrl}/events/${eventId}`, eventUpdate);
    return response.data;
  }

  /**
   * 刪除事件
   */
  async deleteEvent(eventId: number): Promise<{ message: string }> {
    const response = await httpClient.delete(`${this.baseUrl}/events/${eventId}`);
    return response.data;
  }

  /**
   * 獲取統計資訊
   */
  async getStats(): Promise<CalendarStats> {
    // 在開發模式下直接返回 fallback 數據，避免 404 錯誤
    const isDevelopment = import.meta.env.DEV;
    if (isDevelopment) {
      console.log('🔧 Development mode: using fallback calendar stats');
      return {
        total_events: 0,
        month_events: 0,
        today_events: 0,
        active_documents: 0
      };
    }

    try {
      const response = await httpClient.get(`${this.baseUrl}/stats`);
      return response.data;
    } catch (error) {
      // 如果後端端點不可用，返回預設統計資料
      console.warn('Calendar stats endpoint not available, using fallback data');
      return {
        total_events: 0,
        month_events: 0,
        today_events: 0,
        active_documents: 0
      };
    }
  }

  /**
   * 獲取服務狀態
   */
  async getStatus(): Promise<{
    service_available: boolean;
    service_type: string;
    total_events: number;
    features: string[];
  }> {
    const response = await httpClient.get(`${this.baseUrl}/status`);
    return response.data;
  }

  /**
   * 獲取事件分類
   */
  async getCategories(): Promise<{ categories: EventCategory[] }> {
    // 在開發模式下直接返回 fallback 數據，避免 404 錯誤
    const isDevelopment = import.meta.env.DEV;
    if (isDevelopment) {
      console.log('🔧 Development mode: using fallback calendar categories');
      return {
        categories: [
          {"value": "general", "label": "一般", "color": "#1890ff"},
          {"value": "work", "label": "工作", "color": "#52c41a"},
          {"value": "personal", "label": "個人", "color": "#faad14"},
          {"value": "meeting", "label": "會議", "color": "#722ed1"},
          {"value": "deadline", "label": "截止日期", "color": "#f5222d"},
          {"value": "reminder", "label": "提醒", "color": "#13c2c2"}
        ]
      };
    }

    try {
      const response = await httpClient.get(`${this.baseUrl}/categories`);
      return response.data;
    } catch (error) {
      // 如果後端端點不可用，返回預設分類
      console.warn('Calendar categories endpoint not available, using fallback data');
      return {
        categories: [
          {"value": "general", "label": "一般", "color": "#1890ff"},
          {"value": "work", "label": "工作", "color": "#52c41a"},
          {"value": "personal", "label": "個人", "color": "#faad14"},
          {"value": "meeting", "label": "會議", "color": "#722ed1"},
          {"value": "deadline", "label": "截止日期", "color": "#f5222d"},
          {"value": "reminder", "label": "提醒", "color": "#13c2c2"}
        ]
      };
    }
  }

  /**
   * 格式化日期時間為 ISO 字符串
   */
  formatDateTime(date: Date): string {
    return date.toISOString();
  }

  /**
   * 解析 ISO 字符串為 Date 對象
   */
  parseDateTime(dateString: string): Date {
    return new Date(dateString);
  }

  /**
   * 檢查事件是否在指定日期範圍內
   */
  isEventInRange(event: PureCalendarEvent, startDate: Date, endDate: Date): boolean {
    const eventStart = this.parseDateTime(event.start_datetime);
    const eventEnd = this.parseDateTime(event.end_datetime);

    return (eventStart >= startDate && eventStart <= endDate) ||
           (eventEnd >= startDate && eventEnd <= endDate) ||
           (eventStart <= startDate && eventEnd >= endDate);
  }

  /**
   * 獲取事件持續時間（分鐘）
   */
  getEventDuration(event: PureCalendarEvent): number {
    const start = this.parseDateTime(event.start_datetime);
    const end = this.parseDateTime(event.end_datetime);
    return Math.floor((end.getTime() - start.getTime()) / (1000 * 60));
  }

  /**
   * 檢查事件時間衝突
   */
  hasConflict(event1: PureCalendarEvent, event2: PureCalendarEvent): boolean {
    const start1 = this.parseDateTime(event1.start_datetime);
    const end1 = this.parseDateTime(event1.end_datetime);
    const start2 = this.parseDateTime(event2.start_datetime);
    const end2 = this.parseDateTime(event2.end_datetime);

    return (start1 < end2) && (end1 > start2);
  }
}

export const pureCalendarService = new PureCalendarService();
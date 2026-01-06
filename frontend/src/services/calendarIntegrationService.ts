/**
 * 行事曆整合服務
 * 統一處理公文與行事曆的整合功能，避免重複代碼
 */

import { Document } from '../types';
import { API_BASE_URL } from '../api/client';

export interface CalendarEventData {
  title: string;
  description: string;
  start_date: string;
  end_date: string;
  all_day: boolean;
  event_type: 'deadline' | 'meeting' | 'review' | 'reminder' | 'reference';
  priority: number;
  reminder_enabled: boolean;
  reminder_minutes: number;
}

export interface CalendarIntegrationResult {
  success: boolean;
  local_event_id?: number;
  google_event_id?: string;
  message: string;
}

class CalendarIntegrationService {
  private static instance: CalendarIntegrationService;

  private constructor() {}

  public static getInstance(): CalendarIntegrationService {
    if (!CalendarIntegrationService.instance) {
      CalendarIntegrationService.instance = new CalendarIntegrationService();
    }
    return CalendarIntegrationService.instance;
  }

  /**
   * 將公文轉換為行事曆事件數據
   */
  private convertDocumentToEventData(document: Document): CalendarEventData {
    // 根據公文類型和內容智能判斷事件類型
    const eventType = this.determineEventType(document);

    // 構建事件描述
    const description = this.buildEventDescription(document);

    // 確定事件日期
    const eventDate = this.determineEventDate(document);

    return {
      title: `公文提醒: ${document.subject}`,
      description,
      start_date: eventDate,
      end_date: eventDate,
      all_day: true,
      event_type: eventType,
      priority: this.determinePriority(document),
      reminder_enabled: true,
      reminder_minutes: this.getDefaultReminderMinutes(eventType),
    };
  }

  /**
   * 根據公文類型和內容判斷事件類型
   */
  private determineEventType(document: Document): CalendarEventData['event_type'] {
    const content = (document.content || '').toLowerCase();
    const subject = (document.subject || '').toLowerCase();
    const docType = (document.doc_type || '').toLowerCase();

    // 會議相關關鍵字
    if (docType.includes('會議') || docType.includes('開會') ||
        content.includes('會議') || content.includes('開會') ||
        subject.includes('會議') || subject.includes('開會')) {
      return 'meeting';
    }

    // 審查相關關鍵字
    if (content.includes('審查') || content.includes('審核') || content.includes('檢討') ||
        subject.includes('審查') || subject.includes('審核')) {
      return 'review';
    }

    // 截止期限相關
    if (content.includes('截止') || content.includes('期限') || content.includes('到期') ||
        subject.includes('截止') || subject.includes('期限')) {
      return 'deadline';
    }

    // 默認為提醒事件
    return 'reminder';
  }

  /**
   * 構建事件描述
   */
  private buildEventDescription(document: Document): string {
    const parts = [
      `公文字號: ${document.doc_number}`,
      `主旨: ${document.subject}`,
      `發文單位: ${document.sender || '未知'}`,
    ];

    if (document.receiver) {
      parts.push(`受文者: ${document.receiver}`);
    }

    if (document.contract_case) {
      parts.push(`關聯案件: ${document.contract_case}`);
    }

    if (document.assignee) {
      parts.push(`業務同仁: ${document.assignee}`);
    }

    if (document.notes) {
      parts.push(`備註: ${document.notes}`);
    }

    return parts.join('\n');
  }

  /**
   * 確定事件日期
   */
  private determineEventDate(document: Document): string {
    // 優先使用發送日期作為提醒日期
    if (document.send_date) {
      return new Date(document.send_date).toISOString();
    }

    // 其次使用收文日期
    if (document.receive_date) {
      return new Date(document.receive_date).toISOString();
    }

    // 最後使用發文日期
    if (document.doc_date) {
      return new Date(document.doc_date).toISOString();
    }

    // 如果都沒有，使用當前日期
    return new Date().toISOString();
  }

  /**
   * 根據公文屬性確定優先級
   */
  private determinePriority(document: Document): number {
    // 如果公文有設定優先級，轉換字串為數字
    if (document.priority_level) {
      const priorityNum = parseInt(document.priority_level, 10);
      if (priorityNum >= 1 && priorityNum <= 5) {
        return priorityNum;
      }
    }

    // 根據公文類型判斷優先級
    const docType = (document.doc_type || '').toLowerCase();

    if (docType.includes('急件') || docType.includes('特急')) {
      return 1; // 最高優先級
    }

    if (docType.includes('會議') || docType.includes('開會')) {
      return 2; // 高優先級
    }

    return 3; // 中等優先級
  }

  /**
   * 獲取默認提醒時間
   */
  private getDefaultReminderMinutes(eventType: CalendarEventData['event_type']): number {
    const reminderMap = {
      deadline: 60 * 24,  // 截止日期前1天
      meeting: 60,        // 會議前1小時
      review: 60 * 8,     // 審核前8小時
      reminder: 60 * 24,  // 提醒前1天
      reference: 0        // 參考事件不提醒
    };

    return reminderMap[eventType] || 60;
  }

  /**
   * 獲取認證標頭
   */
  private getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem('auth_token');
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    return headers;
  }

  /**
   * 將公文添加到行事曆
   */
  async addDocumentToCalendar(document: Document): Promise<CalendarIntegrationResult> {
    try {
      const eventData = this.convertDocumentToEventData(document);

      // 發送到正確的端點
      const response = await fetch(
        `${API_BASE_URL}/document-calendar/documents/${document.id}/local-events`,
        {
          method: 'POST',
          headers: this.getAuthHeaders(),
          body: JSON.stringify(eventData)
        }
      );

      // 處理響應
      if (response.ok) {
        const result = await response.json();

        // 不在這裡顯示 message，讓調用者決定是否顯示
        const successMessage = result.message || `公文 ${document.doc_number || document.id} 已成功添加到行事曆`;

        return {
          success: true,
          message: successMessage,
          local_event_id: result.event_id || result.id,
          google_event_id: result.google_event_id || null
        };
      } else {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail || `新增日曆事件失敗 (HTTP ${response.status})`;
        throw new Error(errorMessage);
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '新增至日曆失敗';
      console.error('新增至日曆失敗:', error);

      // 不在這裡顯示 message，讓調用者決定是否顯示
      return {
        success: false,
        message: errorMessage
      };
    }
  }

  /**
   * 批量將公文添加到行事曆
   */
  async batchAddDocumentsToCalendar(documents: Document[]): Promise<{
    successCount: number;
    failedCount: number;
    results: CalendarIntegrationResult[];
    summaryMessage: string;
  }> {
    const results: CalendarIntegrationResult[] = [];
    let successCount = 0;
    let failedCount = 0;

    for (const document of documents) {
      try {
        const result = await this.addDocumentToCalendar(document);
        results.push(result);

        if (result.success) {
          successCount++;
        } else {
          failedCount++;
        }
      } catch (error) {
        failedCount++;
        results.push({
          success: false,
          message: `公文 ${document.doc_number} 加入日曆失敗`
        });
      }
    }

    // 構建摘要訊息，讓調用者決定是否顯示
    let summaryMessage = '';
    if (successCount > 0 && failedCount > 0) {
      summaryMessage = `成功將 ${successCount} 個公文加入日曆，${failedCount} 個失敗`;
    } else if (successCount > 0) {
      summaryMessage = `成功將 ${successCount} 個公文加入日曆`;
    } else if (failedCount > 0) {
      summaryMessage = `${failedCount} 個公文加入日曆失敗`;
    }

    return { successCount, failedCount, results, summaryMessage };
  }

  /**
   * 檢查公文是否已經在日曆中
   */
  async isDocumentInCalendar(documentId: number): Promise<boolean> {
    try {
      const response = await fetch(
        `${API_BASE_URL}/document-calendar/documents/${documentId}/events`,
        {
          method: 'GET',
          headers: this.getAuthHeaders(),
        }
      );

      if (response.ok) {
        const events = await response.json();
        return Array.isArray(events) && events.length > 0;
      }

      return false;
    } catch (error) {
      console.error('檢查公文日曆狀態失敗:', error);
      return false;
    }
  }

  /**
   * 從日曆中移除公文事件
   */
  async removeDocumentFromCalendar(documentId: number): Promise<{
    success: boolean;
    message: string;
  }> {
    try {
      const response = await fetch(
        `${API_BASE_URL}/document-calendar/documents/${documentId}/events`,
        {
          method: 'DELETE',
          headers: this.getAuthHeaders(),
        }
      );

      if (response.ok) {
        return {
          success: true,
          message: '已從日曆中移除相關事件'
        };
      } else {
        return {
          success: false,
          message: '從日曆移除事件失敗'
        };
      }
    } catch (error) {
      console.error('從日曆移除事件失敗:', error);
      return {
        success: false,
        message: '從日曆移除事件失敗'
      };
    }
  }
}

// 導出單例實例
export const calendarIntegrationService = CalendarIntegrationService.getInstance();
export default calendarIntegrationService;
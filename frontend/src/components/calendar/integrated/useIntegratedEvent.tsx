/**
 * 整合式事件建立 Hook
 *
 * 管理表單狀態、提醒設定、重複檢查、提交邏輯。
 */

import { useState, useEffect, useCallback } from 'react';
import { Form, App, Grid } from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { apiClient } from '../../../api/client';
import type { ReminderConfig, DocumentInfo } from './types';
import { REMINDER_TIME_OPTIONS } from './types';

const { useBreakpoint } = Grid;

/** 根據公文內容判斷事件類型 */
function determineEventType(doc: DocumentInfo): string {
  const content = (doc.content || '').toLowerCase();
  const subject = (doc.subject || '').toLowerCase();
  const docType = (doc.doc_type || '').toLowerCase();

  if (docType.includes('會議') || content.includes('會議') || subject.includes('會議')) return 'meeting';
  if (content.includes('審查') || content.includes('審核') || subject.includes('審查')) return 'review';
  if (content.includes('截止') || content.includes('期限') || subject.includes('截止')) return 'deadline';
  return 'reminder';
}

/** 根據公文內容判斷優先級 */
function determinePriority(doc: DocumentInfo): number {
  if (doc.priority_level) {
    const num = parseInt(doc.priority_level, 10);
    if (num >= 1 && num <= 5) return num;
  }
  const docType = (doc.doc_type || '').toLowerCase();
  if (docType.includes('急件') || docType.includes('特急')) return 1;
  if (docType.includes('會議')) return 2;
  return 3;
}

/** 確定事件日期 */
function determineEventDate(doc: DocumentInfo): Dayjs {
  if (doc.send_date) return dayjs(doc.send_date);
  if (doc.receive_date) return dayjs(doc.receive_date);
  if (doc.doc_date) return dayjs(doc.doc_date);
  return dayjs();
}

/** 構建事件描述 */
function buildDescription(doc: DocumentInfo): string {
  const parts = [
    `公文字號: ${doc.doc_number || '未指定'}`,
    `主旨: ${doc.subject || '未指定'}`,
    `發文單位: ${doc.sender || '未知'}`,
  ];
  if (doc.receiver) parts.push(`受文者: ${doc.receiver}`);
  if (doc.contract_case) parts.push(`關聯案件: ${doc.contract_case}`);
  if (doc.assignee) parts.push(`業務同仁: ${doc.assignee}`);
  if (doc.notes) parts.push(`備註: ${doc.notes}`);
  return parts.join('\n');
}

export function useIntegratedEvent(
  visible: boolean,
  document: DocumentInfo | null | undefined,
  onClose: () => void,
  onSuccess?: (eventId: number) => void,
) {
  const [form] = Form.useForm();
  const { notification, modal } = App.useApp();

  const screens = useBreakpoint();
  const isMobile = !screens.md;

  const [loading, setLoading] = useState(false);
  const [allDay, setAllDay] = useState(true);
  const [reminderEnabled, setReminderEnabled] = useState(true);
  const [syncToGoogle, setSyncToGoogle] = useState(false);
  const [reminders, setReminders] = useState<ReminderConfig[]>([
    { minutes_before: 1440, notification_type: 'system' },
  ]);
  const [newReminderMinutes, setNewReminderMinutes] = useState<number>(60);
  const [newReminderType, setNewReminderType] = useState<'email' | 'system'>('system');
  const [existingEvents, setExistingEvents] = useState<Array<{ id: number; title: string; start_date: string }>>([]);

  // === 重複檢查 ===

  const checkDocumentEvents = useCallback(async (documentId: number) => {
    try {
      const response = await apiClient.post<{
        has_events: boolean;
        event_count: number;
        events: Array<{ id: number; title: string; start_date: string }>;
        message: string;
      }>('/calendar/events/check-document', { document_id: documentId });

      if (response.has_events && response.event_count > 0) {
        setExistingEvents(response.events);
        modal.warning({
          title: '公文已有行事曆事件',
          content: (
            <div>
              <p>此公文已有 <strong>{response.event_count}</strong> 筆行事曆事件：</p>
              <div style={{
                background: '#fffbe6',
                padding: 12,
                borderRadius: 4,
                marginBottom: 12,
                maxHeight: 150,
                overflowY: 'auto',
              }}>
                {response.events.map(e => (
                  <div key={e.id} style={{ marginBottom: 8 }}>
                    <div style={{ fontWeight: 500 }}>
                      {dayjs(e.start_date).format('YYYY-MM-DD HH:mm')}
                    </div>
                    <div style={{ fontSize: 12, color: '#666' }}>
                      {e.title.length > 50 ? e.title.slice(0, 50) + '...' : e.title}
                    </div>
                  </div>
                ))}
              </div>
              <p style={{ color: '#fa8c16' }}>
                如果日期輸入錯誤，建議先編輯現有事件，而非建立新事件。
              </p>
            </div>
          ),
          okText: '我了解，繼續新增',
          width: 480,
        });
      } else {
        setExistingEvents([]);
      }
    } catch (error) {
      console.error('檢查公文事件失敗:', error);
    }
  }, [modal]);

  // === 初始化表單 ===

  useEffect(() => {
    if (visible && document) {
      const eventType = determineEventType(document);
      const eventDate = determineEventDate(document);

      form.setFieldsValue({
        title: `公文提醒: ${document.subject || document.doc_number || '未命名'}`,
        description: buildDescription(document),
        start_date: eventDate,
        end_date: eventDate,
        all_day: true,
        event_type: eventType,
        priority: determinePriority(document),
        location: '',
      });

      setAllDay(true);
      setReminderEnabled(true);

      const defaultMinutes = eventType === 'deadline' ? 1440 :
                            eventType === 'meeting' ? 60 :
                            eventType === 'review' ? 480 : 1440;
      setReminders([{ minutes_before: defaultMinutes, notification_type: 'system' }]);

      setExistingEvents([]);
      checkDocumentEvents(document.id);
    } else if (visible && !document) {
      form.resetFields();
      form.setFieldsValue({
        event_type: 'reminder',
        priority: 3,
        all_day: true,
        start_date: dayjs(),
      });
      setAllDay(true);
      setReminders([{ minutes_before: 60, notification_type: 'system' }]);
      setExistingEvents([]);
    }
  }, [visible, document, form, checkDocumentEvents]);

  // === 提醒管理 ===

  const handleAddReminder = () => {
    const exists = reminders.some(
      r => r.minutes_before === newReminderMinutes && r.notification_type === newReminderType
    );
    if (exists) {
      notification.warning({ message: '此提醒設定已存在' });
      return;
    }
    setReminders([...reminders, {
      minutes_before: newReminderMinutes,
      notification_type: newReminderType,
    }]);
  };

  const handleRemoveReminder = (index: number) => {
    setReminders(reminders.filter((_, i) => i !== index));
  };

  const getReminderLabel = (minutes: number): string => {
    const option = REMINDER_TIME_OPTIONS.find(o => o.value === minutes);
    return option?.label || `${minutes} 分鐘前`;
  };

  // === 提交 ===

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      const submitData = {
        title: values.title,
        description: values.description || null,
        start_date: values.start_date.toISOString(),
        end_date: values.end_date?.toISOString() || values.start_date.toISOString(),
        all_day: values.all_day || false,
        event_type: values.event_type,
        priority: values.priority,
        location: values.location || null,
        document_id: document?.id || null,
        reminder_enabled: reminderEnabled,
        reminders: reminderEnabled ? reminders : [],
        sync_to_google: syncToGoogle,
      };

      const response = await apiClient.post<{
        success: boolean;
        message: string;
        event_id?: number;
        google_event_id?: string;
      }>('/calendar/events/create-with-reminders', submitData);

      if (response.success) {
        notification.success({
          message: '事件建立成功',
          description: response.google_event_id
            ? '已同步至 Google Calendar'
            : '事件已建立，提醒已設定',
        });
        onSuccess?.(response.event_id!);
        onClose();
      } else {
        throw new Error(response.message || '建立失敗');
      }
    } catch (error: unknown) {
      console.error('建立事件失敗:', error);
      notification.error({
        message: '建立事件失敗',
        description: error instanceof Error ? error.message : '請稍後再試',
      });
    } finally {
      setLoading(false);
    }
  };

  return {
    form,
    isMobile,
    loading,
    allDay,
    setAllDay,
    reminderEnabled,
    setReminderEnabled,
    syncToGoogle,
    setSyncToGoogle,
    reminders,
    newReminderMinutes,
    setNewReminderMinutes,
    newReminderType,
    setNewReminderType,
    existingEvents,
    handleAddReminder,
    handleRemoveReminder,
    getReminderLabel,
    handleSubmit,
  };
}

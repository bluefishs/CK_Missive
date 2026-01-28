/**
 * 事件表單 Hook
 *
 * 管理表單狀態、公文搜尋、重複檢查、提交邏輯。
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Form, App, Grid } from 'antd';
import dayjs from 'dayjs';
import { apiClient } from '../../../api/client';
import debounce from 'lodash/debounce';
import type { CalendarEventData, DocumentOption } from './types';

const { useBreakpoint } = Grid;

export function useEventForm(
  visible: boolean,
  mode: 'create' | 'edit',
  event: CalendarEventData | null | undefined,
  onClose: () => void,
  onSuccess: () => void,
) {
  const [form] = Form.useForm();
  const { notification, modal } = App.useApp();

  const screens = useBreakpoint();
  const isMobile = !screens.md;

  const [loading, setLoading] = useState(false);
  const [allDay, setAllDay] = useState(false);
  const [documentOptions, setDocumentOptions] = useState<DocumentOption[]>([]);
  const [documentSearchError, setDocumentSearchError] = useState<string | null>(null);
  const [existingEventsWarning, setExistingEventsWarning] = useState<string | null>(null);
  const [existingEventsDetail, setExistingEventsDetail] = useState<Array<{ id: number; title: string; start_date: string }>>([]);
  const [duplicateConfirmed, setDuplicateConfirmed] = useState(false);
  const [documentSearching, setDocumentSearching] = useState(false);

  // === 重複檢查 ===

  const checkDocumentEvents = async (documentId: number) => {
    try {
      const response = await apiClient.post<{
        has_events: boolean;
        event_count: number;
        events: Array<{ id: number; title: string; start_date: string; status?: string }>;
        message: string;
      }>('/calendar/events/check-document', { document_id: documentId });

      if (response.has_events && response.event_count > 0) {
        setExistingEventsDetail(response.events);
        setDuplicateConfirmed(false);

        setExistingEventsWarning(
          `此公文已有 ${response.event_count} 筆行事曆事件`
        );

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
          onOk: () => setDuplicateConfirmed(true),
          width: 480,
        });
      } else {
        setExistingEventsWarning(null);
        setExistingEventsDetail([]);
        setDuplicateConfirmed(true);
      }
    } catch (error) {
      console.error('檢查公文事件失敗:', error);
      setDuplicateConfirmed(true);
    }
  };

  // === 公文搜尋 ===

  const handleDocumentChange = (value: number | undefined) => {
    setExistingEventsWarning(null);
    setExistingEventsDetail([]);
    setDuplicateConfirmed(false);
    if (value && mode === 'create') {
      checkDocumentEvents(value);
    } else if (!value) {
      setDuplicateConfirmed(true);
    }
  };

  const searchDocuments = useCallback(
    debounce(async (keyword: string) => {
      setDocumentSearchError(null);

      if (!keyword || keyword.length < 2) {
        setDocumentOptions([]);
        return;
      }

      setDocumentSearching(true);
      try {
        const response = await apiClient.post<{
          success: boolean;
          items: Array<{
            id: number;
            doc_number: string;
            subject?: string;
          }>;
        }>('/documents-enhanced/list', {
          keyword,
          limit: 20,
          page: 1,
        });

        if (response.success && response.items) {
          setDocumentOptions(response.items.map(doc => ({
            id: doc.id,
            doc_number: doc.doc_number,
            subject: doc.subject || '',
          })));
          if (response.items.length === 0) {
            setDocumentSearchError('找不到符合的公文');
          }
        } else {
          setDocumentSearchError('搜尋失敗，請稍後再試');
        }
      } catch (error) {
        console.error('搜尋公文失敗:', error);
        setDocumentSearchError('搜尋時發生錯誤');
        notification.error({
          message: '搜尋公文失敗',
          description: '請檢查網路連線或稍後再試',
          duration: 3,
        });
      } finally {
        setDocumentSearching(false);
      }
    }, 300),
    [notification]
  );

  // === 初始化表單 ===

  useEffect(() => {
    if (visible && mode === 'edit' && event) {
      form.setFieldsValue({
        title: event.title,
        description: event.description,
        start_date: dayjs(event.start_date),
        end_date: event.end_date ? dayjs(event.end_date) : undefined,
        all_day: event.all_day,
        event_type: event.event_type,
        priority: typeof event.priority === 'string' ? parseInt(event.priority) : event.priority,
        location: event.location,
        document_id: event.document_id,
        assigned_user_id: event.assigned_user_id,
      });
      setAllDay(event.all_day);
      if (event.document_id) {
        setDocumentOptions([{
          id: event.document_id,
          doc_number: event.doc_number || `公文 #${event.document_id}`,
          subject: '',
        }]);
      }
    } else if (visible && mode === 'create') {
      form.resetFields();
      form.setFieldsValue({
        event_type: 'reminder',
        priority: 3,
        all_day: false,
        start_date: dayjs(),
      });
      setAllDay(false);
      setDocumentOptions([]);
      setExistingEventsWarning(null);
      setExistingEventsDetail([]);
      setDuplicateConfirmed(true);
    }
  }, [visible, mode, event, form]);

  // === 提交 ===

  const handleSubmit = async () => {
    try {
      const currentValues = form.getFieldsValue();

      if (mode === 'create' && existingEventsDetail.length > 0 && !duplicateConfirmed) {
        notification.warning({
          message: '請確認重複事件警告',
          description: '請先在彈出的警告對話框中確認後再提交。',
        });
        checkDocumentEvents(currentValues.document_id);
        return;
      }

      const values = await form.validateFields();
      setLoading(true);

      const submitData = {
        title: values.title,
        description: values.description || null,
        start_date: values.start_date.toISOString(),
        end_date: values.end_date?.toISOString() || null,
        all_day: values.all_day || false,
        event_type: values.event_type,
        priority: values.priority,
        location: values.location || null,
        document_id: values.document_id || null,
        assigned_user_id: values.assigned_user_id || null,
      };

      if (mode === 'create') {
        const response = await apiClient.post<{ success: boolean; message: string }>(
          '/calendar/events',
          submitData
        );
        if (response.success) {
          notification.success({ message: '事件建立成功' });
          onSuccess();
          onClose();
        } else {
          throw new Error(response.message || '建立失敗');
        }
      } else if (mode === 'edit' && event) {
        const response = await apiClient.post<{ success: boolean; message: string; event?: any }>(
          '/calendar/events/update',
          { event_id: event.id, ...submitData }
        );
        if (response.success) {
          notification.success({ message: '事件更新成功' });
          onSuccess();
          onClose();
        } else {
          throw new Error(response.message || '更新失敗');
        }
      }
    } catch (error: any) {
      console.error('[EventFormModal] 提交失敗:', error);

      if (error.errorFields) {
        const errorMessages = error.errorFields.map((f: any) => `${f.name.join('.')}: ${f.errors.join(', ')}`).join('\n');
        notification.error({
          message: '表單驗證失敗',
          description: errorMessages,
          duration: 5,
        });
      } else {
        notification.error({
          message: mode === 'create' ? '建立事件失敗' : '更新事件失敗',
          description: error.response?.data?.detail || error.message || '請稍後再試',
        });
      }
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
    documentOptions,
    documentSearchError,
    existingEventsWarning,
    documentSearching,
    searchDocuments,
    handleDocumentChange,
    handleSubmit,
  };
}

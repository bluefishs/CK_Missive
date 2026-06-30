/**
 * 事件表單 Hook
 *
 * 管理表單狀態、公文搜尋、重複檢查、提交邏輯。
 */

import { useState, useEffect, useCallback } from 'react';
import { Form, App, Grid } from 'antd';
import dayjs from 'dayjs';
import { apiClient } from '../../../api/client';
import { API_ENDPOINTS } from '../../../api/endpoints';
import debounce from 'lodash/debounce';
import type { CalendarEventData, DocumentOption } from './types';
import { logger } from '../../../services/logger';

const { useBreakpoint } = Grid;

export function useEventForm(
  open: boolean,
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
      }>(API_ENDPOINTS.CALENDAR.EVENTS_CHECK_DOCUMENT, { document_id: documentId });

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
      logger.error('檢查公文事件失敗:', error);
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

  // eslint-disable-next-line react-hooks/exhaustive-deps -- debounce returns a new function; dependencies are managed internally
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
        }>(API_ENDPOINTS.DOCUMENTS.LIST, {
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
        logger.error('搜尋公文失敗:', error);
        setDocumentSearchError('搜尋時發生錯誤');
        notification.error({
          title: '搜尋公文失敗',
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
    if (open && mode === 'edit' && event) {
      form.setFieldsValue({
        title: event.title,
        description: event.description,
        // 2026-06-30 統一：僅截止日期/時間（end_date），無開始；舊資料 fallback 取 start_date
        end_date: dayjs(event.end_date || event.start_date),
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
    } else if (open && mode === 'create') {
      form.resetFields();
      form.setFieldsValue({
        event_type: 'reminder',
        priority: 3,
        all_day: false,
        end_date: dayjs(),
      });
      setAllDay(false);
      setDocumentOptions([]);
      setExistingEventsWarning(null);
      setExistingEventsDetail([]);
      setDuplicateConfirmed(true);
    }
  }, [open, mode, event, form]);

  // === 提交 ===

  const handleSubmit = async () => {
    try {
      const currentValues = form.getFieldsValue();

      if (mode === 'create' && existingEventsDetail.length > 0 && !duplicateConfirmed) {
        notification.warning({
          title: '請確認重複事件警告',
          description: '請先在彈出的警告對話框中確認後再提交。',
        });
        checkDocumentEvents(currentValues.document_id);
        return;
      }

      const values = await form.validateFields();
      setLoading(true);

      // v6.10.1 (2026-05-20): 時區漂移修法 — 不用 toISOString（會轉 UTC 減 8h），
      // 改 dayjs.format 保留本地時間。DB 是 timestamp WITHOUT time zone，
      // 一致使用本地時間語意（用戶輸入 5/22 18:00 = 存 5/22 18:00 = 顯示 5/22 18:00）。
      // 觸發案例：事件 1081 顯示提前 1 日（用戶輸入 5/22 變顯示 5/21）。
      // 2026-06-30 統一：僅截止日期/時間（end_date）；start_date 自動 = end_date（DB 保留兩欄相容）
      const endIso = values.end_date.format('YYYY-MM-DDTHH:mm:ss');
      const submitData = {
        title: values.title,
        description: values.description || null,
        start_date: endIso,
        end_date: endIso,
        all_day: values.all_day || false,
        event_type: values.event_type,
        priority: values.priority,
        location: values.location || null,
        document_id: values.document_id || null,
        assigned_user_id: values.assigned_user_id || null,
      };

      if (mode === 'create') {
        const response = await apiClient.post<{ success: boolean; message: string }>(
          API_ENDPOINTS.CALENDAR.EVENTS_CREATE,
          submitData
        );
        if (response.success) {
          notification.success({ title: '事件建立成功' });
          onSuccess();
          onClose();
        } else {
          throw new Error(response.message || '建立失敗');
        }
      } else if (mode === 'edit' && event) {
        const response = await apiClient.post<{ success: boolean; message: string; event?: CalendarEventData }>(
          API_ENDPOINTS.CALENDAR.EVENTS_UPDATE,
          { event_id: event.id, ...submitData }
        );
        if (response.success) {
          notification.success({ title: '事件更新成功' });
          onSuccess();
          onClose();
        } else {
          throw new Error(response.message || '更新失敗');
        }
      }
    } catch (error: unknown) {
      logger.error('[EventFormModal] 提交失敗:', error);

      // 定義 Ant Design Form 驗證錯誤的型別
      interface FormFieldError {
        name: (string | number)[];
        errors: string[];
      }
      interface FormValidationError {
        errorFields: FormFieldError[];
      }

      const isFormValidationError = (err: unknown): err is FormValidationError => {
        return typeof err === 'object' && err !== null && 'errorFields' in err;
      };

      if (isFormValidationError(error)) {
        const errorMessages = error.errorFields.map((f) => `${f.name.join('.')}: ${f.errors.join(', ')}`).join('\n');
        notification.error({
          title: '表單驗證失敗',
          description: errorMessages,
          duration: 5,
        });
      } else {
        // 處理 API 錯誤
        const errorMessage = error instanceof Error ? error.message : '請稍後再試';
        notification.error({
          title: mode === 'create' ? '建立事件失敗' : '更新事件失敗',
          description: errorMessage,
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

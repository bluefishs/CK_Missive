/**
 * Calendar Event Form Hook
 *
 * Extracted from CalendarEventFormPage.tsx to reduce main file size.
 * Manages form state, queries, mutations, and document search.
 */

import { useState, useMemo, useEffect } from 'react';
import { useParams, useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { Form, App } from 'antd';
import dayjs from 'dayjs';
import debounce from 'lodash/debounce';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../config/queryConfig';
import { logger } from '../services/logger';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import type { CalendarEvent } from '../api/calendarApi';

interface DocumentOption {
  id: number;
  doc_number: string;
  subject: string;
}

export function useCalendarEventForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [form] = Form.useForm();
  const { message, notification } = App.useApp();
  const queryClient = useQueryClient();

  const isNew = !id;
  const returnTo = (location.state as { returnTo?: string })?.returnTo;
  const presetDocumentId = searchParams.get('documentId');

  const [allDay, setAllDay] = useState(false);
  const [documentOptions, setDocumentOptions] = useState<DocumentOption[]>([]);
  const [documentSearching, setDocumentSearching] = useState(false);
  const [documentSearchError, setDocumentSearchError] = useState<string | null>(null);

  // Query event data (edit mode only)
  const { data: event, isLoading } = useQuery({
    queryKey: ['calendar-event', id],
    queryFn: async () => {
      const response = await apiClient.post<{
        success: boolean;
        event: Record<string, unknown>;
      }>(API_ENDPOINTS.CALENDAR.EVENTS_DETAIL, { event_id: parseInt(id || '0', 10) });
      const raw = response.event;
      return {
        ...raw,
        start_datetime: raw.start_date as string,
        end_datetime: raw.end_date as string,
      } as CalendarEvent;
    },
    enabled: !isNew && !!id,
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: async (data: Record<string, unknown>) => {
      const response = await apiClient.post<{ success: boolean; message: string; event_id?: number }>(
        API_ENDPOINTS.CALENDAR.EVENTS_CREATE,
        data
      );
      if (!response.success) throw new Error(response.message || '建立失敗');
      return response;
    },
    onSuccess: () => {
      message.success('事件建立成功');
      queryClient.invalidateQueries({ queryKey: ['calendar', 'events'] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardCalendar.all });
      handleBack();
    },
    onError: (error: Error) => {
      notification.error({ title: '建立事件失敗', description: error.message || '請稍後再試' });
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: async (data: Record<string, unknown>) => {
      const response = await apiClient.post<{ success: boolean; message: string }>(
        API_ENDPOINTS.CALENDAR.EVENTS_UPDATE,
        { event_id: parseInt(id || '0', 10), ...data }
      );
      if (!response.success) throw new Error(response.message || '更新失敗');
      return response;
    },
    onSuccess: () => {
      message.success('事件更新成功');
      queryClient.invalidateQueries({ queryKey: ['calendar', 'events'] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardCalendar.all });
      handleBack();
    },
    onError: (error: Error) => {
      notification.error({ title: '更新事件失敗', description: error.message || '請稍後再試' });
    },
  });

  const saveMutation = isNew ? createMutation : updateMutation;

  // Initialize form (edit mode)
  useEffect(() => {
    if (event && !isNew) {
      form.setFieldsValue({
        title: event.title,
        description: event.description,
        start_date: dayjs(event.start_datetime),
        end_date: event.end_datetime ? dayjs(event.end_datetime) : undefined,
        all_day: event.all_day ?? false,
        event_type: event.event_type || 'reminder',
        priority: typeof event.priority === 'string'
          ? parseInt(event.priority, 10)
          : (event.priority ?? 3),
        location: event.location,
        document_id: event.document_id,
      });
      setAllDay(event.all_day ?? false);
      if (event.document_id) {
        setDocumentOptions([{
          id: event.document_id,
          doc_number: event.doc_number || `公文 #${event.document_id}`,
          subject: '',
        }]);
      }
    }
  }, [event, form, isNew]);

  // Preset document from query param
  const presetDocId = isNew && presetDocumentId ? parseInt(presetDocumentId, 10) : NaN;
  const { data: presetDocument } = useQuery({
    queryKey: ['preset-document', presetDocId],
    queryFn: async () => {
      const response = await apiClient.post<{
        success: boolean;
        items: Array<{ id: number; doc_number: string; subject?: string }>;
      }>(API_ENDPOINTS.DOCUMENTS.LIST, { keyword: '', limit: 1, page: 1, id: presetDocId });
      const firstItem = response.items?.[0];
      if (response.success && firstItem) {
        return { id: firstItem.id, doc_number: firstItem.doc_number, subject: firstItem.subject || '' };
      }
      return { id: presetDocId, doc_number: `公文 #${presetDocId}`, subject: '' };
    },
    enabled: isNew && !isNaN(presetDocId),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  useEffect(() => {
    if (presetDocument && isNew) {
      form.setFieldsValue({ document_id: presetDocument.id });
      setDocumentOptions([presetDocument]);
    }
  }, [presetDocument, isNew, form]);

  // Document search
  // eslint-disable-next-line react-hooks/exhaustive-deps -- debounce returns a new function each render; stable reference via useMemo
  const searchDocuments = useMemo(
    () => debounce(async (keyword: string) => {
      setDocumentSearchError(null);
      if (!keyword || keyword.length < 2) {
        setDocumentOptions([]);
        return;
      }
      setDocumentSearching(true);
      try {
        const response = await apiClient.post<{
          success: boolean;
          items: Array<{ id: number; doc_number: string; subject?: string }>;
        }>(API_ENDPOINTS.DOCUMENTS.LIST, { keyword, limit: 20, page: 1 });
        if (response.success && response.items) {
          setDocumentOptions(response.items.map(doc => ({
            id: doc.id,
            doc_number: doc.doc_number,
            subject: doc.subject || '',
          })));
          if (response.items.length === 0) setDocumentSearchError('找不到符合的公文');
        } else {
          setDocumentSearchError('搜尋失敗，請稍後再試');
        }
      } catch (error) {
        logger.error('搜尋公文失敗:', error);
        setDocumentSearchError('搜尋時發生錯誤');
      } finally {
        setDocumentSearching(false);
      }
    }, 300),
    []
  );

  const handleBack = () => {
    navigate(returnTo || '/calendar');
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
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
      };
      saveMutation.mutate(submitData);
    } catch {
      // form validation error
    }
  };

  return {
    form,
    isNew,
    isLoading,
    allDay,
    setAllDay,
    documentOptions,
    documentSearching,
    documentSearchError,
    searchDocuments,
    saveMutation,
    handleBack,
    handleSave,
  };
}

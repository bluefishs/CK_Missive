/**
 * WorkRecordFormPage — 表單邏輯 Hook
 *
 * 管理 mutations, 表單初始化, 前序紀錄選項, 儲存
 *
 * @version 1.0.0
 * @date 2026-03-18
 */

import { useCallback, useEffect, useMemo } from 'react';
import type { FormInstance } from 'antd';
import dayjs from 'dayjs';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { workflowApi } from '../../api/taoyuan';
import { queryKeys } from '../../config/queryConfig';
import type {
  WorkRecordCreate,
  WorkRecordUpdate,
  WorkRecord,
  DispatchDocumentLink,
} from '../../types/taoyuan';
import { getCategoryLabel } from '../../components/taoyuan/workflow';
import { logger } from '../../services/logger';

interface UseWorkRecordFormLogicParams {
  dispatchOrderId: number;
  workRecordId: number | undefined;
  isNew: boolean;
  form: FormInstance;
  message: { success: (msg: string) => void; error: (msg: string) => void };
  navigate: (path: string) => void;
  returnPath: string;
  urlDocumentId: string | null;
  urlParentRecordId: string | null;
  urlWorkCategory: string | null;
  linkedDocs: DispatchDocumentLink[] | undefined;
  searchedDocsResult: { items?: Array<{ id: number; subject?: string | null }> } | undefined;
}

export function useWorkRecordFormLogic({
  dispatchOrderId,
  workRecordId,
  isNew,
  form,
  message,
  navigate,
  returnPath,
  urlDocumentId,
  urlParentRecordId,
  urlWorkCategory,
  linkedDocs,
  searchedDocsResult,
}: UseWorkRecordFormLogicParams) {
  const queryClient = useQueryClient();

  // 查詢現有紀錄
  const { data: record, isLoading } = useQuery({
    queryKey: ['dispatch-work-record', workRecordId],
    queryFn: () => workflowApi.getDetail(workRecordId!),
    enabled: !isNew && !!workRecordId,
  });

  const { data: existingRecordsData } = useQuery({
    queryKey: queryKeys.workRecords.dispatch(dispatchOrderId),
    queryFn: () => workflowApi.listByDispatchOrder(dispatchOrderId),
    enabled: dispatchOrderId > 0,
  });

  const existingRecords = useMemo(
    () => (existingRecordsData?.items ?? []) as WorkRecord[],
    [existingRecordsData?.items],
  );

  // 前序紀錄選項
  const parentRecordOptions = useMemo(() => {
    const sorted = [...existingRecords].sort((a, b) => {
      if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order;
      return (a.record_date || '').localeCompare(b.record_date || '');
    });

    const seqMap = new Map<number, number>();
    sorted.forEach((r, i) => seqMap.set(r.id, i + 1));

    return sorted
      .filter((r) => r.id !== workRecordId)
      .map((r) => {
        const seq = seqMap.get(r.id) ?? r.sort_order;
        const catLabel = getCategoryLabel(r);
        const docNum = r.document?.doc_number || r.incoming_doc?.doc_number || r.outgoing_doc?.doc_number || '';
        return {
          value: r.id,
          label: `#${seq} ${catLabel}${docNum ? ` — ${docNum}` : ''}${r.record_date ? ` (${r.record_date})` : ''}`,
        };
      });
  }, [existingRecords, workRecordId]);

  // 公文選擇時自動帶入主旨
  const handleDocumentChange = useCallback(
    (docId: number | undefined) => {
      if (!docId) return;
      const linkedDoc = linkedDocs?.find((d) => d.document_id === docId);
      const searchedDoc = searchedDocsResult?.items?.find((d) => d.id === docId);
      const subject = linkedDoc?.subject || searchedDoc?.subject;
      if (subject) {
        const currentDesc = form.getFieldValue('description');
        if (!currentDesc) {
          form.setFieldsValue({ description: subject });
        }
      }
    },
    [linkedDocs, searchedDocsResult?.items, form],
  );

  // 編輯模式：填入現有資料
  useEffect(() => {
    if (record) {
      let desc = record.description;
      if (!desc && record.document?.subject) {
        desc = record.document.subject;
      }
      form.setFieldsValue({
        work_category: record.work_category,
        document_id: record.document_id,
        parent_record_id: record.parent_record_id,
        deadline_date: record.deadline_date ? dayjs(record.deadline_date) : undefined,
        status: record.status,
        description: desc,
        incoming_doc_id: record.incoming_doc_id,
        outgoing_doc_id: record.outgoing_doc_id,
        milestone_type: record.milestone_type,
      });
    }
  }, [record, form]);

  // 新建模式：預設值
  useEffect(() => {
    if (isNew) {
      const defaults: Record<string, unknown> = {
        status: 'in_progress',
      };

      if (urlDocumentId) {
        const parsed = parseInt(urlDocumentId, 10);
        if (!isNaN(parsed)) {
          defaults.document_id = parsed;
          const doc = linkedDocs?.find((d) => d.document_id === parsed);
          if (doc?.subject) {
            defaults.description = doc.subject;
          }
        }
      }
      if (urlParentRecordId) {
        const parsed = parseInt(urlParentRecordId, 10);
        if (!isNaN(parsed)) defaults.parent_record_id = parsed;
      }
      if (urlWorkCategory) {
        defaults.work_category = urlWorkCategory;
      }

      if (!urlParentRecordId && existingRecords.length > 0) {
        const lastRecord = existingRecords[existingRecords.length - 1];
        if (lastRecord) defaults.parent_record_id = lastRecord.id;
      }

      form.setFieldsValue(defaults);
    }
  }, [isNew, form, urlDocumentId, urlParentRecordId, urlWorkCategory, existingRecords, linkedDocs]);

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: WorkRecordCreate) => workflowApi.create(data),
    onSuccess: () => {
      message.success('作業紀錄建立成功');
      queryClient.invalidateQueries({ queryKey: queryKeys.workRecords.dispatch(dispatchOrderId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.workRecords.projectAll });
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
      navigate(returnPath);
    },
    onError: (error: Error) => {
      logger.error('[WorkRecordForm] 建立失敗:', error);
      message.error('建立失敗，請稍後再試');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: WorkRecordUpdate }) =>
      workflowApi.update(id, data),
    onSuccess: () => {
      message.success('作業紀錄更新成功');
      queryClient.invalidateQueries({ queryKey: queryKeys.workRecords.dispatch(dispatchOrderId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.workRecords.projectAll });
      // 作業紀錄狀態變更會影響派工單列表的「作業進度」欄位
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
      navigate(returnPath);
    },
    onError: (error: Error) => {
      logger.error('[WorkRecordForm] 更新失敗:', error);
      message.error('更新失敗，請稍後再試');
    },
  });

  const formatDate = (val: unknown): string | undefined => {
    if (!val) return undefined;
    if (typeof val === 'object' && val !== null && 'format' in val) {
      return (val as { format: (f: string) => string }).format('YYYY-MM-DD');
    }
    if (typeof val === 'string') return val;
    return undefined;
  };

  const handleSave = useCallback(async () => {
    try {
      const values = await form.validateFields();

      const payload: Record<string, unknown> = {
        work_category: values.work_category,
        document_id: values.document_id ?? null,
        parent_record_id: values.parent_record_id ?? null,
        deadline_date: formatDate(values.deadline_date) ?? null,
        status: values.status,
        description: values.description || null,
        milestone_type: values.milestone_type || 'other',
      };

      if (isNew) {
        payload.dispatch_order_id = dispatchOrderId;
        createMutation.mutate(payload as unknown as WorkRecordCreate);
      } else if (workRecordId) {
        updateMutation.mutate({ id: workRecordId, data: payload as unknown as WorkRecordUpdate });
      }
    } catch {
      // form validation failed
    }
  }, [form, isNew, dispatchOrderId, workRecordId, createMutation, updateMutation]);

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return {
    record,
    isLoading,
    parentRecordOptions,
    handleDocumentChange,
    handleSave,
    isSaving,
  };
}

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
import { useDispatchCacheInvalidator } from '../../hooks/taoyuan/useDispatchCacheInvalidator';
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
  const dispatchCache = useDispatchCacheInvalidator();

  // 查詢現有紀錄
  // 2026-08-28：編輯表單必須拿最新值 —— 全域 staleTime 2 分鐘曾讓
  // 使用者在儲存成功後重開表單看到舊快照，再存一次就把舊值整包寫回
  // （「所屬作業怎麼指定都不生效」的真因，backend log 三次 200 中間零 GET）。
  const { data: record, isLoading } = useQuery({
    queryKey: queryKeys.workRecords.detail(workRecordId ?? 0),
    queryFn: () => workflowApi.getDetail(workRecordId!),
    enabled: !isNew && !!workRecordId,
    staleTime: 0,
    refetchOnMount: 'always',
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

    // 2026-08-07：排除**自己的下游**，不只排除自己。
    //
    // owner 實測：編輯 #8 時把前序選成 #9 或 #10，後端回 400
    //「鏈式紀錄存在循環: record_id=369」——那個判斷是對的（不能把自己的子孫
    // 設成前序），但**下拉一開始就不該提供這些選項**：使用者只能靠試錯才知道
    // 哪些能選，而錯誤訊息還指向他正在編輯的那筆、不是他挑的那筆。
    const descendants = new Set<number>();
    if (workRecordId !== undefined) {
      let changed = true;
      while (changed) {
        changed = false;
        for (const r of existingRecords) {
          if (r.parent_record_id === undefined || r.parent_record_id === null) continue;
          if (descendants.has(r.id)) continue;
          if (r.parent_record_id === workRecordId || descendants.has(r.parent_record_id)) {
            descendants.add(r.id);
            changed = true;
          }
        }
      }
    }

    return sorted
      .filter((r) => r.id !== workRecordId && !descendants.has(r.id))
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
        work_type_id: record.work_type_id,
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

      // 2026-08-07：**不再自動預設前序紀錄**。
      //
      // 原本每次新增都把「最後一筆」填進前序，不管兩者語意上有沒有關係。
      // 使用者若沒注意到欄位已預填就送出，紀錄就被串進一條不該存在的鏈。
      // owner 實測結果：派工單 2 被串成
      //   派工通知(01-15) → 作業成果(02-05) → 會議通知(07-03) → 會議紀錄(07-27) → 作業成果(08-07)
      // ——作業成果不該是五個月後那場會議通知的前序，那是兩件不同的事。
      //
      // 後果不只難看：縮排的用途正是**看出事件斷點**，鏈錯了就等於把兩件事
      // 畫成同一件；而且時間軸也會跟著看起來亂（長鏈橫跨數月，下一條鏈接上去像倒退）。
      //
      // 關聯資料猜錯比不猜更糟：錯的鏈會誤導閱讀，還要人工回頭修。
      // 留空由使用者明確選擇；真的是承接前一筆時，下拉第一眼就看得到。

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
      dispatchCache.invalidateWorkRecord();
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
    onSuccess: (_data, variables) => {
      message.success('作業紀錄更新成功');
      // 單筆快取一併作廢 —— 只作廢清單而漏掉單筆，正是舊值回寫事故的成因
      queryClient.invalidateQueries({ queryKey: queryKeys.workRecords.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.workRecords.dispatch(dispatchOrderId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.workRecords.projectAll });
      dispatchCache.invalidateWorkRecord();
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
        work_type_id: values.work_type_id ?? null,
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

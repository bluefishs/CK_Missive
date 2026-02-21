/**
 * useDocumentForm Hook
 *
 * 管理 DocumentOperations 元件的表單邏輯
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import { useEffect, useCallback, useRef } from 'react';
import type { FormInstance } from 'antd';
import type { MessageInstance } from 'antd/es/message/interface';
import dayjs from 'dayjs';
import { Document, ProjectStaff } from '../../../types';
import { logger } from '../../../utils/logger';
import type { OperationMode, CriticalChangeModalState } from './types';
import { parseAssignee, formatAssignee, detectCriticalChanges } from './documentOperationsUtils';

// ============================================================================
// Types
// ============================================================================

/** 表單值型別 */
export interface DocumentFormValues {
  doc_type?: string;
  doc_number: string;
  subject: string;
  sender?: string;
  receiver?: string;
  doc_date?: dayjs.Dayjs | null;
  receive_date?: dayjs.Dayjs | null;
  send_date?: dayjs.Dayjs | null;
  priority?: number;
  status?: string;
  contract_project_id?: number | null;
  assignee?: string[];
  content?: string;
  notes?: string;
  ck_note?: string;
  delivery_method?: string;
}

/** Hook 參數 */
export interface UseDocumentFormProps {
  form: FormInstance<DocumentFormValues>;
  document: Document | null;
  operation: OperationMode | null;
  visible: boolean;
  message: MessageInstance;
  // 依賴項 - 從 useDocumentOperations 注入
  fetchAttachments: (documentId: number) => Promise<void>;
  fetchProjectStaff: (projectId: number) => Promise<ProjectStaff[]>;
  setSelectedProjectId: (id: number | null) => void;
  setCriticalChangeModal: React.Dispatch<React.SetStateAction<CriticalChangeModalState>>;
  setExistingAttachments: (attachments: never[]) => void;
  setFileList: (files: never[]) => void;
}

/** Hook 回傳介面 */
export interface UseDocumentFormReturn {
  handleProjectChange: (projectId: number | null | undefined) => Promise<void>;
  handleSubmit: (
    onSave: (data: Partial<Document>) => Promise<Document | void>,
    performSave: (data: Partial<Document>) => Promise<void>
  ) => Promise<void>;
  initializeForm: () => void;
  getFormData: () => Partial<Document>;
}

// ============================================================================
// Hook Implementation
// ============================================================================

export const useDocumentForm = ({
  form,
  document,
  operation,
  visible,
  message,
  fetchAttachments,
  fetchProjectStaff,
  setSelectedProjectId,
  setCriticalChangeModal,
  setExistingAttachments,
  setFileList,
}: UseDocumentFormProps): UseDocumentFormReturn => {
  // 專案同仁快取 ref（避免閉包問題）
  const projectStaffCacheRef = useRef<Record<number, ProjectStaff[]>>({});

  // 追蹤已載入附件的文件 ID，防止重複請求
  const loadedAttachmentsDocIdRef = useRef<number | null>(null);

  const isCreate = operation === 'create';
  const isCopy = operation === 'copy';

  // ============================================================================
  // 專案變更處理
  // ============================================================================

  const handleProjectChange = useCallback(async (projectId: number | null | undefined) => {
    logger.debug('[handleProjectChange] 選擇專案:', projectId);

    const effectiveProjectId = projectId ?? null;
    form.setFieldsValue({ contract_project_id: effectiveProjectId });

    if (!effectiveProjectId) {
      setSelectedProjectId(null);
      form.setFieldsValue({ assignee: [] });
      return;
    }

    const staffList = await fetchProjectStaff(effectiveProjectId);
    logger.debug('[handleProjectChange] 取得業務同仁:', staffList);

    // 快取專案人員
    projectStaffCacheRef.current[effectiveProjectId] = staffList;

    if (!staffList || staffList.length === 0) {
      setSelectedProjectId(effectiveProjectId);
      message.info('此專案尚無指派業務同仁');
      return;
    }

    const allStaffNames = staffList.map((s) => s.user_name).filter((name): name is string => !!name);
    logger.debug('[handleProjectChange] 準備填入:', allStaffNames);

    setSelectedProjectId(effectiveProjectId);

    setTimeout(() => {
      const currentStaff = projectStaffCacheRef.current[effectiveProjectId];
      if (currentStaff && currentStaff.length > 0) {
        const names = currentStaff.map((s) => s.user_name).filter((name): name is string => !!name);
        form.setFieldsValue({ assignee: names });
        logger.debug('[handleProjectChange] 已填入業務同仁:', names);
        message.success(`已自動填入 ${names.length} 位業務同仁`);
      }
    }, 150);
  }, [form, fetchProjectStaff, setSelectedProjectId, message]);

  // ============================================================================
  // 表單初始化
  // ============================================================================

  const initializeForm = useCallback(() => {
    if (visible && document) {
      const assigneeArray = parseAssignee(document.assignee);

      const formValues: DocumentFormValues = {
        ...document,
        doc_date: document.doc_date ? dayjs(document.doc_date) : null,
        receive_date: document.receive_date ? dayjs(document.receive_date) : null,
        send_date: document.send_date ? dayjs(document.send_date) : null,
        assignee: assigneeArray,
      };

      if (isCopy) {
        const formValuesWithId = formValues as { id?: number };
        delete formValuesWithId.id;
        formValues.doc_number = `${document.doc_number}-副本`;
      }

      form.setFieldsValue(formValues);

      const projectId = document.contract_project_id;
      if (projectId) {
        setSelectedProjectId(projectId);
        fetchProjectStaff(projectId).then(staffList => {
          projectStaffCacheRef.current[projectId] = staffList;
          if (staffList && staffList.length > 0 && assigneeArray.length === 0) {
            const allStaffNames = staffList.map((s) => s.user_name).filter((name): name is string => !!name);
            setTimeout(() => {
              form.setFieldsValue({ assignee: allStaffNames });
              logger.debug('[載入公文] 自動填入專案業務同仁:', allStaffNames);
            }, 100);
          }
        });
      } else {
        setSelectedProjectId(null);
      }

      // 防止重複載入同一文件的附件
      if (document.id && !isCopy && loadedAttachmentsDocIdRef.current !== document.id) {
        loadedAttachmentsDocIdRef.current = document.id;
        fetchAttachments(document.id);
      }
    } else if (visible && isCreate) {
      form.resetFields();
      setSelectedProjectId(null);
      setExistingAttachments([]);
      setFileList([]);
      // 重置追蹤 ref
      loadedAttachmentsDocIdRef.current = null;
    } else if (!visible) {
      // Modal 關閉時重置追蹤，以便下次開啟能重新載入
      loadedAttachmentsDocIdRef.current = null;
    }
  }, [
    visible,
    document,
    form,
    isCreate,
    isCopy,
    fetchAttachments,
    fetchProjectStaff,
    setSelectedProjectId,
    setExistingAttachments,
    setFileList,
  ]);

  // 監聽 visible 和 document 變化自動初始化
  useEffect(() => {
    initializeForm();
  }, [initializeForm]);

  // ============================================================================
  // 取得表單資料
  // ============================================================================

  const getFormData = useCallback((): Partial<Document> => {
    const values = form.getFieldsValue();

    let assigneeStr = '';
    if (Array.isArray(values.assignee)) {
      assigneeStr = formatAssignee(values.assignee);
    } else if (values.assignee) {
      assigneeStr = String(values.assignee);
    }

    // 處理 contract_project_id: null -> undefined
    const contractProjectId = values.contract_project_id === null ? undefined : values.contract_project_id;

    return {
      ...values,
      doc_date: values.doc_date?.format('YYYY-MM-DD'),
      receive_date: values.receive_date?.format('YYYY-MM-DD'),
      send_date: values.send_date?.format('YYYY-MM-DD'),
      assignee: assigneeStr,
      contract_project_id: contractProjectId,
    };
  }, [form]);

  // ============================================================================
  // 表單提交
  // ============================================================================

  const handleSubmit = useCallback(async (
    _onSave: (data: Partial<Document>) => Promise<Document | void>,
    performSave: (data: Partial<Document>) => Promise<void>
  ) => {
    try {
      const values = await form.validateFields();

      let assigneeStr = '';
      if (Array.isArray(values.assignee)) {
        assigneeStr = formatAssignee(values.assignee);
      } else if (values.assignee) {
        assigneeStr = String(values.assignee);
      }

      // 處理 contract_project_id: null -> undefined
      const contractProjectId = values.contract_project_id === null ? undefined : values.contract_project_id;

      const documentData: Partial<Document> = {
        ...values,
        doc_date: values.doc_date?.format('YYYY-MM-DD'),
        receive_date: values.receive_date?.format('YYYY-MM-DD'),
        send_date: values.send_date?.format('YYYY-MM-DD'),
        assignee: assigneeStr,
        contract_project_id: contractProjectId,
      };

      // 編輯模式：檢查關鍵欄位變更
      if (operation === 'edit' && document) {
        const criticalChanges = detectCriticalChanges(
          document as unknown as Record<string, unknown>,
          documentData as unknown as Record<string, unknown>
        );

        if (criticalChanges.length > 0) {
          setCriticalChangeModal({
            visible: true,
            changes: criticalChanges,
            pendingData: documentData,
          });
          return;
        }
      }

      await performSave(documentData);
    } catch (error) {
      logger.error('Form validation failed:', error);
    }
  }, [form, operation, document, setCriticalChangeModal]);

  return {
    handleProjectChange,
    handleSubmit,
    initializeForm,
    getFormData,
  };
};

export default useDocumentForm;

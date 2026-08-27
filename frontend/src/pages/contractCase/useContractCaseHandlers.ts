/**
 * 承攬案件詳情頁 CRUD Handlers
 *
 * 從 ContractCaseDetailPage 拆分，集中管理所有實體操作 handler
 *
 * @version 1.0.0
 * @date 2026-03-29
 */

import { App } from 'antd';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';
import { useState, useCallback } from 'react';
import { ROUTES } from '../../router/types';
import { queryKeys } from '../../config/queryConfig';
import { projectsApi } from '../../api/projectsApi';
import { filesApi } from '../../api/filesApi';
import { logger } from '../../utils/logger';
import type { QueryClient } from '@tanstack/react-query';
import { getErrorMessage } from '../../utils/apiErrorParser';
import type {
  CaseInfoFormValues,  LocalGroupedAttachment,
  ApiErrorResponse,} from './tabs';

interface UseContractCaseHandlersOptions {
  projectId: number;
  queryClient: QueryClient;
  backRoute?: string;
  // Form instances
  // Modal state setters
  setIsEditingCaseInfo: (v: boolean) => void;
}

export function useContractCaseHandlers(opts: UseContractCaseHandlersOptions) {
  const {
    projectId, queryClient, backRoute, setIsEditingCaseInfo,
  } = opts;

  const navigate = useNavigate();
  const { message } = App.useApp();
  const [deleting, setDeleting] = useState(false);

  const handleBack = useCallback(() => navigate(backRoute || ROUTES.CONTRACT_CASES), [navigate, backRoute]);
  const handleEdit = useCallback(() => navigate(`${ROUTES.CONTRACT_CASES}/${projectId}/edit`), [navigate, projectId]);

  const handleDelete = useCallback(async () => {
    setDeleting(true);
    try {
      await projectsApi.deleteProject(projectId);
      queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
      message.success('案件已刪除');
      navigate(backRoute || ROUTES.CONTRACT_CASES);
    } catch (error) {
      const axiosError = error as { response?: { data?: ApiErrorResponse } };
      message.error(axiosError.response?.data?.detail as string || '刪除案件失敗，可能仍有關聯資料');
    } finally {
      setDeleting(false);
    }
  }, [projectId, queryClient, message, navigate, backRoute]);

  const handleSaveCaseInfo = useCallback(async (values: CaseInfoFormValues) => {
    try {
      const autoProgress = values.status === '已結案' ? 100 : values.progress;
      const startDate = values.date_range?.[0] ? dayjs(values.date_range[0] as unknown as string).format('YYYY-MM-DD') : undefined;
      const endDate = values.date_range?.[1] ? dayjs(values.date_range[1] as unknown as string).format('YYYY-MM-DD') : undefined;
      const updateData = {
        project_name: values.project_name, year: values.year,
        client_agency: values.client_agency || undefined,
        contract_doc_number: values.contract_doc_number || undefined,
        project_code: values.project_code || undefined,
        category: values.category || undefined,
        case_nature: values.case_nature || undefined,
        contract_amount: values.contract_amount || undefined,
        winning_amount: values.winning_amount || undefined,
        start_date: startDate, end_date: endDate,
        status: values.status || undefined,
        progress: autoProgress ?? undefined,
        project_path: values.project_path || undefined,
        notes: values.notes || undefined,
        has_dispatch_management: values.has_dispatch_management,
      };
      await projectsApi.updateProject(projectId, updateData as Parameters<typeof projectsApi.updateProject>[1]);
      queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
      queryClient.invalidateQueries({ queryKey: ['taoyuan-dispatch-orders', 'contract-projects'] });
      queryClient.invalidateQueries({ queryKey: ['contract-case-detail', projectId] });
      setIsEditingCaseInfo(false);
      message.success('案件資訊已更新');
    } catch (error) {
      logger.error('更新案件資訊失敗:', error);
      const axiosError = error as { response?: { data?: ApiErrorResponse } };
      message.error(axiosError.response?.data?.detail as string || '更新案件資訊失敗');
    }
  }, [projectId, queryClient, message, setIsEditingCaseInfo]);

  const handleDownloadAttachment = useCallback(async (attachmentId: number, filename: string) => {
    try { await filesApi.downloadAttachment(attachmentId, filename); }
    catch (e) { message.error(getErrorMessage(e, '下載附件失敗'), 8); }
  }, [message]);

  const handlePreviewAttachment = useCallback(async (attachmentId: number, filename: string) => {
    try {
      const blob = await filesApi.getAttachmentBlob(attachmentId);
      const previewUrl = window.URL.createObjectURL(blob);
      window.open(previewUrl, '_blank');
      setTimeout(() => window.URL.revokeObjectURL(previewUrl), 10000);
    } catch (e) { message.error(getErrorMessage(e, `預覽 ${filename} 失敗`), 8); }
  }, [message]);

  const handleDownloadAllAttachments = useCallback(async (group: LocalGroupedAttachment) => {
    message.loading({ content: `正在下載 ${group.file_count} 個檔案...`, key: 'download-all' });
    for (const att of group.attachments) {
      try { await filesApi.downloadAttachment(att.id, att.filename); }
      catch (error) { logger.error(`下載 ${att.filename} 失敗:`, error); }
    }
    message.success({ content: '下載完成', key: 'download-all' });
  }, [message]);

  return {
    deleting,
    handleBack,
    handleEdit,
    handleDelete,
    handleSaveCaseInfo,
    handleDownloadAttachment,
    handlePreviewAttachment,
    handleDownloadAllAttachments,
  };
}

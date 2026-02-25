/**
 * useAutoMatch - 自動匹配公文 Hook
 *
 * 從 DispatchWorkflowTab 拆分，管理自動匹配公文的狀態與操作。
 *
 * @version 1.0.0
 * @date 2026-02-25
 */

import { useState, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { queryKeys } from '../../../../config/queryConfig';
import { dispatchOrdersApi } from '../../../../api/taoyuanDispatchApi';
import type { DocumentHistoryItem } from '../../../../types/taoyuan';
import type { LinkType } from '../../../../types/api';

interface UseAutoMatchOptions {
  dispatchOrderId: number;
  projectName?: string;
  linkedDocIds: number[];
  onRefetchDispatch?: () => void;
}

export function useAutoMatch({
  dispatchOrderId,
  projectName,
  linkedDocIds,
  onRefetchDispatch,
}: UseAutoMatchOptions) {
  const queryClient = useQueryClient();
  const { message } = App.useApp();

  const [modalOpen, setModalOpen] = useState(false);
  const [results, setResults] = useState<{
    agency: DocumentHistoryItem[];
    company: DocumentHistoryItem[];
  }>({ agency: [], company: [] });
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const autoMatchMutation = useMutation({
    mutationFn: () => dispatchOrdersApi.matchDocuments(projectName || '', dispatchOrderId),
    onSuccess: (result) => {
      if (!result.success) {
        message.warning('匹配失敗');
        return;
      }
      const agency = result.agency_documents.filter((d) => !linkedDocIds.includes(d.id));
      const company = result.company_documents.filter((d) => !linkedDocIds.includes(d.id));
      if (agency.length === 0 && company.length === 0) {
        message.info('所有匹配公文皆已關聯，無需再新增');
        return;
      }
      setResults({ agency, company });
      setSelectedIds(new Set([...agency, ...company].map((d) => d.id)));
      setModalOpen(true);
    },
    onError: () => message.error('自動匹配失敗'),
  });

  const batchLinkMutation = useMutation({
    mutationFn: async (items: { documentId: number; linkType: LinkType }[]) => {
      let successCount = 0;
      let failCount = 0;
      for (const item of items) {
        try {
          await dispatchOrdersApi.linkDocument(dispatchOrderId, {
            document_id: item.documentId,
            link_type: item.linkType,
          });
          successCount++;
        } catch {
          failCount++;
        }
      }
      return { successCount, failCount };
    },
    onSuccess: ({ successCount, failCount }) => {
      if (failCount === 0) {
        message.success(`批次關聯完成，共 ${successCount} 筆`);
      } else {
        message.warning(`${successCount} 筆關聯成功，${failCount} 筆失敗`);
      }
      setModalOpen(false);
      setResults({ agency: [], company: [] });
      setSelectedIds(new Set());
      onRefetchDispatch?.();
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
      queryClient.invalidateQueries({ queryKey: ['dispatch-work-records', dispatchOrderId] });
    },
    onError: () => message.error('批次關聯失敗'),
  });

  const handleConfirm = useCallback(() => {
    const items: { documentId: number; linkType: LinkType }[] = [];
    for (const doc of results.agency) {
      if (selectedIds.has(doc.id)) {
        items.push({ documentId: doc.id, linkType: 'agency_incoming' });
      }
    }
    for (const doc of results.company) {
      if (selectedIds.has(doc.id)) {
        items.push({ documentId: doc.id, linkType: 'company_outgoing' });
      }
    }
    if (items.length === 0) {
      message.warning('請至少勾選一筆公文');
      return;
    }
    batchLinkMutation.mutate(items);
  }, [results, selectedIds, batchLinkMutation, message]);

  return {
    modalOpen,
    results,
    selectedIds,
    setSelectedIds,
    isPending: autoMatchMutation.isPending,
    batchLinkPending: batchLinkMutation.isPending,
    trigger: () => autoMatchMutation.mutate(),
    handleConfirm,
    closeModal: () => setModalOpen(false),
  };
}

/**
 * 派工單公文關聯 Hook
 *
 * 從 DispatchWorkflowTab 拆分，負責公文搜尋查詢 + link/unlink mutations
 *
 * @version 1.0.0
 * @date 2026-03-29
 */

import { useState, useMemo, useCallback } from 'react';
import { App } from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../../../config/queryConfig';
import { dispatchOrdersApi } from '../../../../api/taoyuanDispatchApi';
import type { DispatchDocumentLink, LinkType } from '../../../../types/api';
import { detectLinkType } from '../../../../components/taoyuan/workflow/useDispatchWorkData';

interface LinkableDocumentOption {
  id: number;
  doc_number: string | null;
  subject: string | null;
  doc_date: string | null;
  category: string | null;
  sender: string | null;
  receiver: string | null;
}

interface UseDispatchDocLinkingOptions {
  dispatchOrderId: number;
  linkedDocuments: DispatchDocumentLink[];
  contractProjectId?: number;
  onRefetchDispatch?: () => void;
}

export function useDispatchDocLinking({
  dispatchOrderId,
  linkedDocuments,
  contractProjectId,
  onRefetchDispatch,
}: UseDispatchDocLinkingOptions) {
  const queryClient = useQueryClient();
  const { message } = App.useApp();

  const [docSearchKeyword, setDocSearchKeyword] = useState('');
  const [selectedDocId, setSelectedDocId] = useState<number>();
  const [selectedLinkType, setSelectedLinkType] = useState<LinkType>('agency_incoming');

  const linkedDocIds = useMemo(
    () => linkedDocuments.map((d) => d.document_id),
    [linkedDocuments],
  );

  const { data: searchedDocsResult, isLoading: searchingDocs } = useQuery({
    queryKey: [
      'documents-for-dispatch-link',
      docSearchKeyword,
      linkedDocIds,
      selectedLinkType,
      contractProjectId,
    ],
    queryFn: async () => {
      if (!docSearchKeyword.trim()) return { items: [] };
      return dispatchOrdersApi.searchLinkableDocuments(
        docSearchKeyword,
        20,
        linkedDocIds.length > 0 ? linkedDocIds : undefined,
        selectedLinkType,
        contractProjectId,
      );
    },
    enabled: !!docSearchKeyword.trim(),
  });

  const availableDocs = useMemo(
    () => (searchedDocsResult?.items || []) as LinkableDocumentOption[],
    [searchedDocsResult?.items],
  );

  const linkDocMutation = useMutation({
    mutationFn: (data: { documentId: number; linkType: LinkType }) =>
      dispatchOrdersApi.linkDocument(dispatchOrderId, {
        document_id: data.documentId,
        link_type: data.linkType,
      }),
    onSuccess: () => {
      message.success('公文關聯成功');
      setSelectedDocId(undefined);
      setDocSearchKeyword('');
      onRefetchDispatch?.();
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.workRecords.dispatch(dispatchOrderId) });
    },
    onError: () => message.error('關聯失敗'),
  });

  const unlinkDocMutation = useMutation({
    mutationFn: (linkId: number) =>
      dispatchOrdersApi.unlinkDocument(dispatchOrderId, linkId),
    onSuccess: () => {
      message.success('已移除公文關聯');
      onRefetchDispatch?.();
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.workRecords.dispatch(dispatchOrderId) });
    },
    onError: () => message.error('移除關聯失敗'),
  });

  const handleLinkDocument = useCallback(() => {
    if (!selectedDocId) {
      message.warning('請先選擇要關聯的公文');
      return;
    }
    linkDocMutation.mutate({
      documentId: selectedDocId,
      linkType: selectedLinkType,
    });
  }, [selectedDocId, selectedLinkType, linkDocMutation, message]);

  const handleUnlinkDocument = useCallback(
    (linkId: number | undefined) => {
      if (linkId === undefined || linkId === null) {
        message.error('關聯資料缺少 link_id，請重新整理頁面');
        onRefetchDispatch?.();
        return;
      }
      unlinkDocMutation.mutate(linkId);
    },
    [unlinkDocMutation, message, onRefetchDispatch],
  );

  const handleDocumentChange = useCallback(
    (docId: number | undefined) => {
      setSelectedDocId(docId);
      if (docId) {
        const selectedDoc = availableDocs.find((d) => d.id === docId);
        if (selectedDoc?.doc_number) {
          const detected = detectLinkType(selectedDoc.doc_number);
          if (detected !== selectedLinkType) {
            const label = detected === 'company_outgoing' ? '乾坤發文' : '機關來函';
            message.info(`依公文字號建議為「${label}」，已自動切換`);
            setSelectedLinkType(detected);
          }
        }
      }
    },
    [availableDocs, selectedLinkType, message],
  );

  return {
    docSearchKeyword,
    setDocSearchKeyword,
    selectedDocId,
    selectedLinkType,
    setSelectedLinkType,
    linkedDocIds,
    availableDocs,
    searchingDocs,
    linkDocMutation,
    unlinkDocMutation,
    handleLinkDocument,
    handleUnlinkDocument,
    handleDocumentChange,
  };
}

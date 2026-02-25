/**
 * 公文對照 Tab（統一公文關聯 + 作業歷程）
 *
 * 整合原「公文關聯」Tab 與「作業歷程」Tab，以公文對照矩陣為核心：
 * - 公文對照視圖：已指派公文（對應作業紀錄）+ 未指派公文（待建立紀錄）
 * - 表格視圖：里程碑平面列表
 * - 行內公文搜尋：直接在 Tab 內搜尋並關聯新公文
 * - 迷你統計：紀錄數 / 關聯公文 / 未指派 / 來文 / 發文
 * - 跨頁導航：前往工程總覽（高亮本派工單）
 * - CRUD：新增/編輯（導航）、刪除（行內）、關聯/解除公文
 * - 匯出：公文對照矩陣 Excel 匯出
 *
 * @version 6.0.0 - 矩陣匯出 + hooks 拆分（useAutoMatch, useWorkflowColumns）
 * @date 2026-02-25
 */

import React, { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Button,
  Empty,
  App,
} from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../../config/queryConfig';

import { workflowApi } from '../../../api/taoyuan';
import { dispatchOrdersApi } from '../../../api/taoyuanDispatchApi';
import type { WorkRecord } from '../../../types/taoyuan';
import type { DispatchDocumentLink, LinkType } from '../../../types/api';
import { logger } from '../../../services/logger';
import { exportCorrespondenceMatrix } from '../../../utils/dispatchExportUtils';

import { CorrespondenceBody, ChainTimeline } from '../../../components/taoyuan/workflow';
import {
  useDispatchWorkData,
  detectLinkType,
} from '../../../components/taoyuan/workflow/useDispatchWorkData';

import { StatsCards } from './workflow/StatsCards';
import { WorkflowToolBar } from './workflow/WorkflowToolBar';
import { InlineDocumentSearch } from './workflow/InlineDocumentSearch';
import { UnassignedDocumentsList } from './workflow/UnassignedDocumentsList';
import { AutoMatchModal } from './workflow/AutoMatchModal';
import { useWorkflowColumns } from './workflow/useWorkflowColumns';
import { useAutoMatch } from './workflow/useAutoMatch';

// =============================================================================
// Types
// =============================================================================

type ViewMode = 'chain' | 'correspondence' | 'table';

/** 可關聯公文選項 */
interface LinkableDocumentOption {
  id: number;
  doc_number: string | null;
  subject: string | null;
  doc_date: string | null;
  category: string | null;
  sender: string | null;
  receiver: string | null;
}

export interface DispatchWorkflowTabProps {
  /** 派工單 ID */
  dispatchOrderId: number;
  /** 是否可編輯 */
  canEdit?: boolean;
  /** 關聯的工程 (用於「查看工程總覽」導航) */
  linkedProjects?: { project_id: number; project_name?: string }[];
  /** 已關聯的公文列表 (從派工單詳情取得) */
  linkedDocuments?: DispatchDocumentLink[];
  /** 重新取得派工單資料的 callback */
  onRefetchDispatch?: () => void;
  /** 工程名稱（用於自動匹配公文） */
  projectName?: string;
  /** 派工單號（用於匯出檔名） */
  dispatchNo?: string;
}

// =============================================================================
// 主元件
// =============================================================================

export const DispatchWorkflowTab: React.FC<DispatchWorkflowTabProps> = ({
  dispatchOrderId,
  canEdit = true,
  linkedProjects,
  linkedDocuments = [],
  onRefetchDispatch,
  projectName,
  dispatchNo,
}) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = App.useApp();

  const [viewMode, setViewMode] = useState<ViewMode>('chain');

  // 公文搜尋相關狀態
  const [docSearchKeyword, setDocSearchKeyword] = useState('');
  const [selectedDocId, setSelectedDocId] = useState<number>();
  const [selectedLinkType, setSelectedLinkType] = useState<LinkType>('agency_incoming');

  // ===========================================================================
  // 統一資料
  // ===========================================================================

  const {
    records,
    stats,
    correspondenceData,
    matrixRows,
    unassignedDocs,
    isLoading,
  } = useDispatchWorkData({
    dispatchOrderId,
    linkedDocuments,
  });

  // ===========================================================================
  // 公文搜尋 Query
  // ===========================================================================

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
    ],
    queryFn: async () => {
      if (!docSearchKeyword.trim()) return { items: [] };
      return dispatchOrdersApi.searchLinkableDocuments(
        docSearchKeyword,
        20,
        linkedDocIds.length > 0 ? linkedDocIds : undefined,
        selectedLinkType,
      );
    },
    enabled: !!docSearchKeyword.trim(),
  });

  const availableDocs = useMemo(
    () => (searchedDocsResult?.items || []) as LinkableDocumentOption[],
    [searchedDocsResult?.items],
  );

  // ===========================================================================
  // Mutations
  // ===========================================================================

  const deleteMutation = useMutation({
    mutationFn: (id: number) => workflowApi.delete(id),
    onSuccess: () => {
      message.success('作業紀錄已刪除');
      queryClient.invalidateQueries({
        queryKey: ['dispatch-work-records', dispatchOrderId],
      });
      queryClient.invalidateQueries({
        queryKey: ['project-work-records'],
      });
    },
    onError: (error: Error) => {
      logger.error('[WorkflowTab] 刪除失敗:', error);
      message.error('刪除失敗，請稍後再試');
    },
  });

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
      queryClient.invalidateQueries({ queryKey: ['dispatch-work-records', dispatchOrderId] });
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
      queryClient.invalidateQueries({ queryKey: ['dispatch-work-records', dispatchOrderId] });
    },
    onError: () => message.error('移除關聯失敗'),
  });

  // ===========================================================================
  // 自動匹配公文（拆分至 useAutoMatch）
  // ===========================================================================

  const autoMatch = useAutoMatch({
    dispatchOrderId,
    projectName,
    linkedDocIds,
    onRefetchDispatch,
  });

  // ===========================================================================
  // Handlers
  // ===========================================================================

  const handleAdd = useCallback(() => {
    navigate(`/taoyuan/dispatch/${dispatchOrderId}/workflow/create`);
  }, [navigate, dispatchOrderId]);

  const handleEdit = useCallback(
    (record: WorkRecord) => {
      navigate(
        `/taoyuan/dispatch/${dispatchOrderId}/workflow/${record.id}/edit`,
      );
    },
    [navigate, dispatchOrderId],
  );

  const handleDocClick = useCallback(
    (docId: number) => {
      navigate(`/documents/${docId}`);
    },
    [navigate],
  );

  const handleGoToProjectOverview = useCallback(
    (projectId: number) => {
      navigate(
        `/taoyuan/project/${projectId}?tab=overview&highlight=${dispatchOrderId}`,
      );
    },
    [navigate, dispatchOrderId],
  );

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

  const handleQuickCreateRecord = useCallback(
    (doc: DispatchDocumentLink) => {
      navigate(
        `/taoyuan/dispatch/${dispatchOrderId}/workflow/create?document_id=${doc.document_id}`,
      );
    },
    [navigate, dispatchOrderId],
  );

  const handleViewModeChange = useCallback((mode: ViewMode) => {
    setViewMode(mode);
  }, []);

  const handleExport = useCallback(() => {
    try {
      exportCorrespondenceMatrix({
        matrixRows,
        records,
        stats,
        dispatchNo,
        projectName,
      });
      message.success('矩陣匯出成功');
    } catch (err) {
      logger.error('[WorkflowTab] 匯出矩陣失敗:', err);
      message.error('匯出失敗，請稍後再試');
    }
  }, [matrixRows, records, stats, dispatchNo, projectName, message]);

  // ===========================================================================
  // Table Columns（拆分至 useWorkflowColumns）
  // ===========================================================================

  const columns = useWorkflowColumns({
    canEdit,
    onEdit: handleEdit,
    onDocClick: handleDocClick,
    onDelete: (id) => deleteMutation.mutate(id),
  });

  // ===========================================================================
  // 公文對照視圖
  // ===========================================================================

  const hasUnassigned = unassignedDocs.incoming.length > 0 || unassignedDocs.outgoing.length > 0;
  const hasCorrespondence =
    correspondenceData.incomingDocs.length > 0 ||
    correspondenceData.outgoingDocs.length > 0;

  const renderCorrespondenceView = () => {
    if (matrixRows.length === 0 && linkedDocuments.length === 0) {
      return (
        <Empty
          description="尚無公文關聯與作業紀錄"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          style={{ padding: '40px 0' }}
        />
      );
    }

    return (
      <CorrespondenceBody
        data={correspondenceData}
        matrixRows={matrixRows}
        onDocClick={handleDocClick}
        onEditRecord={canEdit ? handleEdit : undefined}
        onQuickCreateRecord={canEdit ? handleQuickCreateRecord : undefined}
        canEdit={canEdit}
      />
    );
  };

  // ===========================================================================
  // Render
  // ===========================================================================

  return (
    <div>
      {/* 迷你統計 */}
      <StatsCards stats={stats} />

      {/* 工具列 */}
      <WorkflowToolBar
        viewMode={viewMode}
        onViewModeChange={handleViewModeChange}
        canEdit={canEdit}
        onAdd={handleAdd}
        linkedProjects={linkedProjects}
        onGoToProjectOverview={handleGoToProjectOverview}
        onExport={matrixRows.length > 0 ? handleExport : undefined}
      />

      {/* 視圖內容 */}
      {viewMode === 'chain' ? (
        <ChainTimeline
          records={records}
          onDocClick={handleDocClick}
          onEditRecord={canEdit ? handleEdit : undefined}
          onDeleteRecord={canEdit ? (id) => deleteMutation.mutate(id) : undefined}
          canEdit={canEdit}
        />
      ) : viewMode === 'correspondence' ? (
        renderCorrespondenceView()
      ) : (
        <Table<WorkRecord>
          columns={columns}
          dataSource={records}
          rowKey="id"
          loading={isLoading}
          size="small"
          pagination={false}
          scroll={{ x: 1100 }}
          locale={{
            emptyText: (
              <Empty
                description="尚無作業歷程紀錄"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ),
          }}
        />
      )}

      {/* 未指派公文列表（所有視圖通用） */}
      {viewMode !== 'correspondence' && hasUnassigned && (
        <UnassignedDocumentsList
          unassignedDocs={unassignedDocs}
          hasCorrespondence={hasCorrespondence}
          canEdit={canEdit}
          unlinkPending={unlinkDocMutation.isPending}
          onDocClick={handleDocClick}
          onQuickCreateRecord={handleQuickCreateRecord}
          onUnlinkDocument={handleUnlinkDocument}
        />
      )}

      {/* 行內公文搜尋區（所有視圖通用） */}
      {canEdit && (
        <InlineDocumentSearch
          availableDocs={availableDocs}
          selectedDocId={selectedDocId}
          selectedLinkType={selectedLinkType}
          docSearchKeyword={docSearchKeyword}
          searchingDocs={searchingDocs}
          linkingDoc={linkDocMutation.isPending}
          onDocumentChange={handleDocumentChange}
          onSearchKeywordChange={setDocSearchKeyword}
          onLinkTypeChange={setSelectedLinkType}
          onLinkDocument={handleLinkDocument}
        />
      )}

      {/* 自動匹配公文按鈕 */}
      {canEdit && projectName && (
        <div style={{ marginTop: 12, textAlign: 'right' }}>
          <Button
            icon={<ThunderboltOutlined />}
            onClick={autoMatch.trigger}
            loading={autoMatch.isPending}
          >
            自動匹配公文
          </Button>
        </div>
      )}

      {/* 自動匹配結果 Modal */}
      <AutoMatchModal
        open={autoMatch.modalOpen}
        projectName={projectName || ''}
        agencyDocs={autoMatch.results.agency}
        companyDocs={autoMatch.results.company}
        selectedIds={autoMatch.selectedIds}
        onSelectedIdsChange={autoMatch.setSelectedIds}
        onConfirm={autoMatch.handleConfirm}
        onCancel={autoMatch.closeModal}
        loading={autoMatch.batchLinkPending}
      />
    </div>
  );
};

export default DispatchWorkflowTab;

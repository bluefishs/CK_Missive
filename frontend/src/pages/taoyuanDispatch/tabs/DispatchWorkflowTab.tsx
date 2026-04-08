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
 * @version 7.0.0 - 共用模組化（WorkRecordStatsCard, useWorkRecordColumns, useDeleteWorkRecord）
 * @date 2026-02-25
 */

import React, { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Button,
  Empty,
  App,
} from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import { queryKeys } from '../../../config/queryConfig';

import type { WorkRecord } from '../../../types/taoyuan';
import type { DispatchDocumentLink } from '../../../types/api';
import { logger } from '../../../services/logger';
import { exportCorrespondenceMatrix } from '../../../utils/dispatchExportUtils';

import {
  CorrespondenceBody,
  ChainTimeline,
  WorkRecordStatsCard,
  useWorkRecordColumns,
  useDeleteWorkRecord,
} from '../../../components/taoyuan/workflow';
import {
  useDispatchWorkData,
} from '../../../components/taoyuan/workflow/useDispatchWorkData';

import { WorkflowToolBar } from './workflow/WorkflowToolBar';
import { InlineDocumentSearch } from './workflow/InlineDocumentSearch';
import { UnassignedDocumentsList } from './workflow/UnassignedDocumentsList';
import { AutoMatchModal } from './workflow/AutoMatchModal';
import { useAutoMatch } from './workflow/useAutoMatch';
import { useDispatchDocLinking } from './workflow/useDispatchDocLinking';

// =============================================================================
// Types
// =============================================================================

type ViewMode = 'chain' | 'correspondence' | 'table';

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
  /** 承攬案件 ID（用於搜尋可關聯公文時篩選對應專案） */
  contractProjectId?: number;
  /** 工程名稱（用於自動匹配公文） */
  projectName?: string;
  /** 派工單號（用於匯出檔名） */
  dispatchNo?: string;
  /** 作業類別（用於統計卡片顯示） */
  workType?: string;
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
  contractProjectId,
  projectName,
  dispatchNo,
  workType,
}) => {
  const navigate = useNavigate();
  const { message } = App.useApp();

  const [viewMode, setViewMode] = useState<ViewMode>('chain');

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
  // 公文關聯 (搜尋 + link/unlink mutations)
  // ===========================================================================

  const docLinking = useDispatchDocLinking({
    dispatchOrderId,
    linkedDocuments,
    contractProjectId,
    onRefetchDispatch,
  });

  // ===========================================================================
  // Mutations
  // ===========================================================================

  const deleteMutation = useDeleteWorkRecord({
    invalidateKeys: [
      queryKeys.workRecords.dispatch(dispatchOrderId),
      queryKeys.workRecords.projectAll,
      queryKeys.taoyuanDispatch.all,
    ],
    logPrefix: 'WorkflowTab',
  });

  // ===========================================================================
  // 自動匹配公文
  // ===========================================================================

  const autoMatch = useAutoMatch({
    dispatchOrderId,
    projectName,
    linkedDocIds: docLinking.linkedDocIds,
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

  const handleQuickCreateRecord = useCallback(
    (doc: DispatchDocumentLink) => {
      navigate(
        `/taoyuan/dispatch/${dispatchOrderId}/workflow/create?document_id=${doc.document_id}`,
      );
    },
    [navigate, dispatchOrderId],
  );

  const handleDelete = useCallback(
    (id: number) => {
      deleteMutation.mutate(id);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [deleteMutation.mutate],
  );

  const handleViewModeChange = useCallback((mode: ViewMode) => {
    setViewMode(mode);
  }, []);

  const handleExport = useCallback(async () => {
    try {
      await exportCorrespondenceMatrix({
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
  // Table Columns（共用 useWorkRecordColumns）
  // ===========================================================================

  const columns = useWorkRecordColumns({
    canEdit,
    onEdit: handleEdit,
    onDelete: handleDelete,
    onDocClick: handleDocClick,
    showDeadlineColumn: true,
    showOutgoingDocColumn: true,
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
      {/* 迷你統計（共用元件） */}
      <WorkRecordStatsCard
        mode="dispatch"
        stats={stats}
        onHold={stats.onHold}
        linkedDocCount={stats.linkedDocCount}
        unassignedDocCount={stats.unassignedDocCount}
        workType={workType}
      />

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
          onDeleteRecord={canEdit ? handleDelete : undefined}
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

      {/* 未指派公文列表（所有視圖通用，含公文對照模式） */}
      {hasUnassigned && (
        <UnassignedDocumentsList
          unassignedDocs={unassignedDocs}
          hasCorrespondence={hasCorrespondence}
          canEdit={canEdit}
          unlinkPending={docLinking.unlinkDocMutation.isPending}
          onDocClick={handleDocClick}
          onQuickCreateRecord={handleQuickCreateRecord}
          onUnlinkDocument={docLinking.handleUnlinkDocument}
        />
      )}

      {/* 行內公文搜尋區（所有視圖通用） */}
      {canEdit && (
        <InlineDocumentSearch
          availableDocs={docLinking.availableDocs}
          selectedDocId={docLinking.selectedDocId}
          selectedLinkType={docLinking.selectedLinkType}
          docSearchKeyword={docLinking.docSearchKeyword}
          searchingDocs={docLinking.searchingDocs}
          linkingDoc={docLinking.linkDocMutation.isPending}
          onDocumentChange={docLinking.handleDocumentChange}
          onSearchKeywordChange={docLinking.setDocSearchKeyword}
          onLinkTypeChange={docLinking.setSelectedLinkType}
          onLinkDocument={docLinking.handleLinkDocument}
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

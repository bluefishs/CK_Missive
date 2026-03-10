/**
 * ProjectWorkOverviewTab - 作業總覽整合 Tab
 *
 * 四視圖統一：公文對照表 + 時間軸 + 表格 + 看板
 *
 * 交互：看板卡片點擊 → 切換到公文對照並高亮目標派工單
 *
 * @version 2.0.0 - 模組化：使用共用 WorkRecordStatsCard / useWorkRecordColumns / useDeleteWorkRecord
 * @date 2026-03-04
 */

import React, { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Segmented,
  Select,
  Button,
  Space,
  Empty,
  Table,
} from 'antd';
import {
  PlusOutlined,
  FileTextOutlined,
  OrderedListOutlined,
  ApartmentOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';

import type {
  WorkRecord,
  ProjectDispatchLinkItem,
} from '../../../types/taoyuan';

import {
  useProjectWorkData,
  CorrespondenceMatrix,
  WorkflowTimelineView,
  WorkflowKanbanView,
  WorkRecordStatsCard,
  useWorkRecordColumns,
  useDeleteWorkRecord,
} from '../../../components/taoyuan/workflow';
import { queryKeys } from '../../../config/queryConfig';

// ============================================================================
// Props
// ============================================================================

export interface ProjectWorkOverviewTabProps {
  projectId: number;
  contractProjectId?: number;
  linkedDispatches: ProjectDispatchLinkItem[];
  canEdit?: boolean;
  /** 從 URL 帶入的高亮派工單 ID（跨頁導航用） */
  initialHighlightDispatchId?: number;
}

// ============================================================================
// View mode type
// ============================================================================

type ViewMode = 'correspondence' | 'timeline' | 'table' | 'kanban';

// ============================================================================
// 主元件
// ============================================================================

export const ProjectWorkOverviewTab: React.FC<ProjectWorkOverviewTabProps> = ({
  projectId,
  contractProjectId,
  linkedDispatches,
  canEdit = true,
  initialHighlightDispatchId,
}) => {
  const navigate = useNavigate();

  const [viewMode, setViewMode] = useState<ViewMode>('correspondence');
  const [selectedDispatchId, setSelectedDispatchId] = useState<number>();
  const [highlightDispatchId, setHighlightDispatchId] = useState<number | undefined>(
    initialHighlightDispatchId,
  );

  // ===========================================================================
  // 統一資料
  // ===========================================================================

  const {
    records,
    stats,
    batchGroups,
    kanbanColumns,
    correspondenceGroups,
    isLoading,
  } = useProjectWorkData({
    projectId,
    contractProjectId,
    linkedDispatches,
  });

  // ===========================================================================
  // 共用 Mutations
  // ===========================================================================

  const deleteMutation = useDeleteWorkRecord({
    invalidateKeys: [
      queryKeys.workRecords.project(projectId),
      queryKeys.workRecords.dispatchAll,
    ],
    logPrefix: 'ProjectWorkOverview',
  });

  // ===========================================================================
  // Handlers
  // ===========================================================================

  const returnTo = encodeURIComponent(
    `/taoyuan/project/${projectId}?tab=overview`,
  );

  const handleAdd = useCallback(() => {
    if (!selectedDispatchId) return;
    navigate(
      `/taoyuan/dispatch/${selectedDispatchId}/workflow/create?returnTo=${returnTo}`,
    );
  }, [navigate, selectedDispatchId, returnTo]);

  const handleEditRecord = useCallback(
    (record: WorkRecord) => {
      navigate(
        `/taoyuan/dispatch/${record.dispatch_order_id}/workflow/${record.id}/edit?returnTo=${returnTo}`,
      );
    },
    [navigate, returnTo],
  );

  const handleDeleteRecord = useCallback(
    (recordId: number) => {
      deleteMutation.mutate(recordId);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [deleteMutation.mutate],
  );

  // 看板卡片點擊 → 切到公文對照並高亮
  const handleKanbanCardClick = useCallback(
    (dispatchId: number) => {
      setHighlightDispatchId(dispatchId);
      setViewMode('correspondence');
    },
    [],
  );

  // 導航到派工單詳情
  const handleDispatchNavigate = useCallback(
    (dispatchId: number) => {
      navigate(`/taoyuan/dispatch/${dispatchId}?tab=correspondence`);
    },
    [navigate],
  );

  // 導航到公文詳情
  const handleDocNavigate = useCallback(
    (docId: number) => {
      navigate(`/documents/${docId}`);
    },
    [navigate],
  );

  // 看板新增派工
  const handleAddDispatch = useCallback(
    (workType: string) => {
      navigate('/taoyuan/dispatch/create', {
        state: {
          contract_project_id: contractProjectId,
          work_type: workType,
        },
      });
    },
    [navigate, contractProjectId],
  );

  // ===========================================================================
  // 共用表格欄位
  // ===========================================================================

  const tableColumns = useWorkRecordColumns({
    canEdit,
    onEdit: handleEditRecord,
    onDelete: handleDeleteRecord,
    showDispatchColumn: true,
  });

  // ===========================================================================
  // 派工單下拉選項
  // ===========================================================================

  const dispatchOptions = useMemo(
    () =>
      linkedDispatches.map((d) => ({
        value: d.dispatch_order_id,
        label: `${d.dispatch_no}${d.work_type ? ` - ${d.work_type}` : ''}`,
      })),
    [linkedDispatches],
  );

  // ===========================================================================
  // Render
  // ===========================================================================

  return (
    <div>
      {/* 統計儀表板（共用元件） */}
      <WorkRecordStatsCard
        mode="project"
        stats={stats}
        dispatchCount={stats.dispatchCount}
        workTypeStages={stats.workTypeStages}
      />

      {/* 工具列 */}
      <div
        style={{
          marginBottom: 16,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        {canEdit && (
          <Space>
            <Select
              placeholder="選擇派工單"
              style={{ width: 280 }}
              value={selectedDispatchId}
              onChange={setSelectedDispatchId}
              options={dispatchOptions}
              allowClear
            />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAdd}
              disabled={!selectedDispatchId}
            >
              新增紀錄
            </Button>
          </Space>
        )}
        <Segmented
          value={viewMode}
          onChange={(val) => {
            setViewMode(val as ViewMode);
            if (val !== 'correspondence') {
              setHighlightDispatchId(undefined);
            }
          }}
          options={[
            {
              value: 'correspondence',
              label: '公文對照',
              icon: <FileTextOutlined />,
            },
            {
              value: 'timeline',
              label: '時間軸',
              icon: <ApartmentOutlined />,
            },
            {
              value: 'table',
              label: '表格',
              icon: <OrderedListOutlined />,
            },
            {
              value: 'kanban',
              label: '看板',
              icon: <AppstoreOutlined />,
            },
          ]}
        />
      </div>

      {/* 視圖內容 */}
      {linkedDispatches.length === 0 ? (
        <Empty
          description="尚未關聯任何派工單"
          style={{ padding: '60px 0' }}
        />
      ) : viewMode === 'correspondence' ? (
        <CorrespondenceMatrix
          groups={correspondenceGroups}
          highlightDispatchId={highlightDispatchId}
          onDispatchClick={handleDispatchNavigate}
          onDocClick={handleDocNavigate}
          onEditRecord={canEdit ? handleEditRecord : undefined}
          canEdit={canEdit}
        />
      ) : viewMode === 'timeline' ? (
        <WorkflowTimelineView
          batchGroups={batchGroups}
          canEdit={canEdit}
          onEditRecord={handleEditRecord}
          onDeleteRecord={handleDeleteRecord}
        />
      ) : viewMode === 'table' ? (
        <Table<WorkRecord>
          columns={tableColumns}
          dataSource={records}
          rowKey="id"
          loading={isLoading}
          size="small"
          pagination={false}
          scroll={{ x: 1100 }}
        />
      ) : (
        <WorkflowKanbanView
          columns={kanbanColumns}
          isLoading={isLoading}
          canEdit={canEdit}
          onCardClick={handleKanbanCardClick}
          onAddNew={handleAddDispatch}
        />
      )}
    </div>
  );
};

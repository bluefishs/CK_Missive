/**
 * KanbanBoardTab - 看板視圖 Tab
 *
 * 以作業類別為欄位、派工單為卡片的 Kanban 看板。
 * 桌面：水平滾動 10 欄；手機：Collapse 摺疊面板。
 *
 * @version 1.1.0 - 修復：手機版新增按鈕、theme token、memo
 * @date 2026-02-13
 */

import React, { useCallback, useMemo, useState } from 'react';
import { Collapse, Spin, Empty, Badge, Button, Typography, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ROUTES } from '../../../router/types';

import { useResponsive } from '../../../hooks/utility/useResponsive';
import { useKanbanData } from '../../../components/taoyuan/kanban/useKanbanData';
import { KanbanColumn } from '../../../components/taoyuan/kanban/KanbanColumn';
import { KanbanCard } from '../../../components/taoyuan/kanban/KanbanCard';
import { getWorkTypeColor, type KanbanColumnData } from '../../../components/taoyuan/kanban/kanbanConstants';
import type { ProjectDispatchLinkItem, WorkRecordStatus } from '../../../types/taoyuan';
import { workflowApi } from '../../../api/taoyuan';

const { Text } = Typography;

interface KanbanBoardTabProps {
  projectId: number;
  contractProjectId?: number;
  linkedDispatches: ProjectDispatchLinkItem[];
  canEdit?: boolean;
}

export const KanbanBoardTab: React.FC<KanbanBoardTabProps> = ({
  projectId,
  contractProjectId,
  linkedDispatches,
  canEdit,
}) => {
  const navigate = useNavigate();
  const { isMobile } = useResponsive();

  const queryClient = useQueryClient();
  const [messageApi, contextHolder] = message.useMessage();
  const [updatingDispatchId, setUpdatingDispatchId] = useState<number | null>(null);

  const { columns, isLoading, refetch } = useKanbanData({
    projectId,
    contractProjectId,
    linkedDispatches,
  });

  // Quick status toggle mutation: update all work records for a dispatch
  const statusMutation = useMutation({
    mutationFn: async ({ recordIds, newStatus }: { dispatchId: number; recordIds: number[]; newStatus: WorkRecordStatus }) => {
      // Update all records in parallel
      await Promise.all(
        recordIds.map((id) => workflowApi.update(id, { status: newStatus })),
      );
    },
    onMutate: ({ dispatchId }) => {
      setUpdatingDispatchId(dispatchId);
    },
    onSuccess: () => {
      messageApi.success('狀態已更新');
      refetch();
      queryClient.invalidateQueries({ queryKey: ['kanban-workflow', projectId] });
    },
    onError: () => {
      messageApi.error('狀態更新失敗');
    },
    onSettled: () => {
      setUpdatingDispatchId(null);
    },
  });

  const handleStatusChange = useCallback(
    (dispatchId: number, recordIds: number[], newStatus: WorkRecordStatus) => {
      statusMutation.mutate({ dispatchId, recordIds, newStatus });
    },
    [statusMutation],
  );

  const handleCardClick = useCallback(
    (dispatchId: number) => {
      navigate(`/taoyuan/dispatch/${dispatchId}`);
    },
    [navigate],
  );

  const handleAddNew = useCallback(
    (workType: string) => {
      navigate(ROUTES.TAOYUAN_DISPATCH_CREATE, {
        state: {
          contract_project_id: contractProjectId,
          work_type: workType,
        },
      });
    },
    [navigate, contractProjectId],
  );

  // 統計：有卡片的欄位
  const totalCards = useMemo(
    () => columns.reduce((sum, col) => sum + col.cards.length, 0),
    [columns],
  );

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 0' }}>
        <Spin>
          <div style={{ padding: 20 }}>
            <Text type="secondary">載入看板資料...</Text>
          </div>
        </Spin>
      </div>
    );
  }

  if (linkedDispatches.length === 0) {
    return (
      <Empty
        description="尚未關聯任何派工單"
        style={{ padding: '60px 0' }}
      />
    );
  }

  if (totalCards === 0) {
    return (
      <Empty
        description="關聯的派工單尚無作業類別分配"
        style={{ padding: '60px 0' }}
      />
    );
  }

  // 手機：Collapse 摺疊
  if (isMobile) {
    return (
      <>
        {contextHolder}
        <MobileKanban
          columns={columns}
          onCardClick={handleCardClick}
          onAddNew={canEdit ? handleAddNew : undefined}
          onStatusChange={canEdit ? handleStatusChange : undefined}
          updatingDispatchId={updatingDispatchId}
        />
      </>
    );
  }

  // 桌面：水平滾動
  return (
    <>
      {contextHolder}
      <div
        style={{
          display: 'flex',
          gap: 12,
          overflowX: 'auto',
          paddingBottom: 8,
          alignItems: 'flex-start',
          maxHeight: 'calc(100vh - 300px)',
        }}
      >
        {columns
          .filter((col) => col.cards.length > 0)
          .map((col) => (
            <KanbanColumn
              key={col.workType}
              data={col}
              onCardClick={handleCardClick}
              onAddNew={handleAddNew}
              onStatusChange={canEdit ? handleStatusChange : undefined}
              updatingDispatchId={updatingDispatchId}
              canEdit={canEdit}
            />
          ))}
      </div>
    </>
  );
};

// ============================================================================
// 手機版：Collapse 摺疊面板
// ============================================================================

interface MobileKanbanProps {
  columns: KanbanColumnData[];
  onCardClick: (dispatchId: number) => void;
  onAddNew?: (workType: string) => void;
  onStatusChange?: (dispatchId: number, recordIds: number[], newStatus: WorkRecordStatus) => void;
  updatingDispatchId?: number | null;
}

const MobileKanbanInner: React.FC<MobileKanbanProps> = ({ columns, onCardClick, onAddNew, onStatusChange, updatingDispatchId }) => {
  // 預設展開有卡片的欄位
  const defaultActive = useMemo(
    () => columns.filter((c) => c.cards.length > 0).map((c) => c.workType),
    [columns],
  );

  const items = useMemo(
    () =>
      columns
        .filter((col) => col.cards.length > 0)
        .map((col) => {
          const color = getWorkTypeColor(col.workType);
          return {
            key: col.workType,
            label: (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 4, height: 16, borderRadius: 2, background: color }} />
                <Text strong style={{ color }}>{col.workType}</Text>
                <Badge count={col.cards.length} style={{ backgroundColor: color }} />
              </div>
            ),
            children: (
              <div style={{ padding: '4px 0' }}>
                {col.cards.map((card) => (
                  <KanbanCard
                    key={card.dispatch.id}
                    data={card}
                    onClick={onCardClick}
                    onStatusChange={onStatusChange}
                    isUpdating={updatingDispatchId === card.dispatch.id}
                  />
                ))}
                {onAddNew && (
                  <Button
                    type="text"
                    icon={<PlusOutlined />}
                    onClick={() => onAddNew(col.workType)}
                    block
                    style={{
                      marginTop: 4,
                      color: '#8c8c8c',
                      borderRadius: 6,
                      height: 32,
                      fontSize: 12,
                    }}
                  >
                    新增派工
                  </Button>
                )}
              </div>
            ),
          };
        }),
    [columns, onCardClick, onAddNew, onStatusChange, updatingDispatchId],
  );

  return (
    <Collapse
      defaultActiveKey={defaultActive}
      ghost
      items={items}
    />
  );
};

const MobileKanban = React.memo(MobileKanbanInner);

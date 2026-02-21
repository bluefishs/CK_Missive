/**
 * WorkflowKanbanView - 看板視圖 (薄 wrapper)
 *
 * 復用 kanban/ 下的 KanbanColumn + KanbanCard 元件。
 * 與 KanbanBoardTab 不同之處：不自行查詢資料，接收 kanbanColumns prop。
 *
 * @version 1.0.0
 * @date 2026-02-13
 */

import React, { useMemo } from 'react';
import { Collapse, Badge, Button, Typography, Empty, Spin } from 'antd';
import { PlusOutlined } from '@ant-design/icons';

import { useResponsive } from '../../../hooks/utility/useResponsive';
import { KanbanColumn } from '../kanban/KanbanColumn';
import { KanbanCard } from '../kanban/KanbanCard';
import { getWorkTypeColor, type KanbanColumnData } from '../kanban/kanbanConstants';

const { Text } = Typography;

// ============================================================================
// Props
// ============================================================================

interface WorkflowKanbanViewProps {
  columns: KanbanColumnData[];
  isLoading?: boolean;
  canEdit?: boolean;
  /** 卡片點擊：切換到公文對照並高亮（而非導航離開） */
  onCardClick: (dispatchId: number) => void;
  onAddNew?: (workType: string) => void;
}

// ============================================================================
// 主元件
// ============================================================================

const WorkflowKanbanViewInner: React.FC<WorkflowKanbanViewProps> = ({
  columns,
  isLoading,
  canEdit,
  onCardClick,
  onAddNew,
}) => {
  const { isMobile } = useResponsive();

  const populatedColumns = useMemo(
    () => columns.filter((col) => col.cards.length > 0),
    [columns],
  );

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

  if (totalCards === 0) {
    return (
      <Empty
        description="關聯的派工單尚無作業類別分配"
        style={{ padding: '60px 0' }}
      />
    );
  }

  if (isMobile) {
    return (
      <MobileKanban
        columns={populatedColumns}
        onCardClick={onCardClick}
        onAddNew={canEdit ? onAddNew : undefined}
      />
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        gap: 12,
        overflowX: 'auto',
        paddingBottom: 8,
        alignItems: 'flex-start',
      }}
    >
      {populatedColumns.map((col) => (
        <KanbanColumn
          key={col.workType}
          data={col}
          onCardClick={onCardClick}
          onAddNew={onAddNew}
          canEdit={canEdit}
        />
      ))}
    </div>
  );
};

export const WorkflowKanbanView = React.memo(WorkflowKanbanViewInner);

// ============================================================================
// 手機版
// ============================================================================

interface MobileKanbanProps {
  columns: KanbanColumnData[];
  onCardClick: (dispatchId: number) => void;
  onAddNew?: (workType: string) => void;
}

const MobileKanbanInner: React.FC<MobileKanbanProps> = ({
  columns,
  onCardClick,
  onAddNew,
}) => {
  const defaultActive = useMemo(
    () => columns.filter((c) => c.cards.length > 0).map((c) => c.workType),
    [columns],
  );

  const items = useMemo(
    () =>
      columns.map((col) => {
        const color = getWorkTypeColor(col.workType);
        return {
          key: col.workType,
          label: (
            <div
              style={{ display: 'flex', alignItems: 'center', gap: 8 }}
            >
              <div
                style={{
                  width: 4,
                  height: 16,
                  borderRadius: 2,
                  background: color,
                }}
              />
              <Text strong style={{ color }}>
                {col.workType}
              </Text>
              <Badge
                count={col.cards.length}
                style={{ backgroundColor: color }}
              />
            </div>
          ),
          children: (
            <div style={{ padding: '4px 0' }}>
              {col.cards.map((card) => (
                <KanbanCard
                  key={card.dispatch.id}
                  data={card}
                  onClick={onCardClick}
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
    [columns, onCardClick, onAddNew],
  );

  return <Collapse defaultActiveKey={defaultActive} ghost items={items} />;
};

const MobileKanban = React.memo(MobileKanbanInner);

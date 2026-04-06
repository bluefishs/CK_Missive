/**
 * DispatchOverviewTab - 派工總覽看板
 *
 * 以作業類別為欄位、派工單為卡片的 Kanban 看板總覽。
 * 直接從承攬案件的所有派工單產生看板資料，不需要關聯工程。
 *
 * 桌面：水平滾動看板欄；手機：Collapse 摺疊面板。
 *
 * @version 1.0.0
 * @date 2026-04-05
 */

import React, { useCallback, useMemo } from 'react';
import {
  Collapse,
  Spin,
  Empty,
  Badge,
  Button,
  Typography,
  Row,
  Col,
  Statistic,
  Card,
} from 'antd';
import {
  PlusOutlined,
  SendOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../router/types';

import { useResponsive } from '../../hooks/utility/useResponsive';
import { useTaoyuanDispatchOrders } from '../../hooks';
import { KanbanColumn } from './kanban/KanbanColumn';
import { KanbanCard } from './kanban/KanbanCard';
import {
  ALL_WORK_TYPES,
  getWorkTypeColor,
  getWorkTypes,
  type KanbanColumnData,
  type KanbanCardData,
} from './kanban/kanbanConstants';
import type { DispatchOrder, WorkRecordStatus } from '../../types/taoyuan';

const { Text } = Typography;

// ============================================================================
// Types
// ============================================================================

interface DispatchOverviewTabProps {
  contractProjectId: number;
}

// ============================================================================
// Hook: build kanban data from dispatch orders
// ============================================================================

function useDispatchOverviewKanban(contractProjectId: number) {
  const {
    dispatchOrders,
    total,
    isLoading,
    refetch,
  } = useTaoyuanDispatchOrders({
    contract_project_id: contractProjectId,
    limit: 200,
  });

  const columns = useMemo<KanbanColumnData[]>(() => {
    const columnMap = new Map<string, KanbanCardData[]>();

    for (const dispatch of dispatchOrders) {
      const workTypes = getWorkTypes(dispatch);
      const card: KanbanCardData = {
        dispatch,
        computedStatus: inferStatusFromDispatch(dispatch),
        recordCount: 0, // No work records at this overview level
        recordIds: [],
      };

      if (workTypes.length === 0) {
        // No work type assigned -- put in first column
        const first = ALL_WORK_TYPES[0] as string;
        const list = columnMap.get(first) || [];
        list.push(card);
        columnMap.set(first, list);
      } else {
        for (const wt of workTypes) {
          const list = columnMap.get(wt) || [];
          list.push(card);
          columnMap.set(wt, list);
        }
      }
    }

    return ALL_WORK_TYPES.map((wt) => ({
      workType: wt,
      color: getWorkTypeColor(wt),
      cards: columnMap.get(wt) || [],
    }));
  }, [dispatchOrders]);

  // Summary stats — derived from same inferStatusFromDispatch logic
  const stats = useMemo(() => {
    let completed = 0;
    let inProgress = 0;
    let overdue = 0;
    let pending = 0;
    const workTypeSet = new Set<string>();

    for (const d of dispatchOrders) {
      const status = inferStatusFromDispatch(d);
      if (status === 'completed') completed++;
      else if (status === 'overdue') overdue++;
      else if (status === 'in_progress') inProgress++;
      else pending++;

      for (const wt of getWorkTypes(d)) {
        workTypeSet.add(wt);
      }
    }

    return {
      total,
      completed,
      inProgress,
      overdue,
      pending,
      workTypeCount: workTypeSet.size,
    };
  }, [dispatchOrders, total]);

  return { columns, stats, isLoading, refetch };
}

/**
 * Infer dispatch status from multiple signals (not just batch_no).
 *
 * Priority: batch_no(結案) > deadline逾期 > company_doc(已覆文=進行中)
 *           > linked_documents(有關聯公文=進行中) > agency_doc(有來文=進行中) > pending
 */
function inferStatusFromDispatch(dispatch: DispatchOrder): WorkRecordStatus {
  // 1. 已結案 (有結案批次)
  if (dispatch.batch_no != null && dispatch.batch_no > 0) return 'completed';

  // 2. 逾期 (有期限且已過)
  if (dispatch.deadline) {
    const dl = new Date(dispatch.deadline);
    if (dl < new Date()) return 'overdue';
  }

  // 3. 進行中 — 已發覆文
  if (dispatch.company_doc_id) return 'in_progress';

  // 4. 進行中 — 有關聯公文
  if (dispatch.linked_documents && dispatch.linked_documents.length > 0) return 'in_progress';

  // 5. 進行中 — 有機關來文 (表示已啟動)
  if (dispatch.agency_doc_id) return 'in_progress';

  // 6. 未開始
  return 'pending';
}

// ============================================================================
// Stats summary
// ============================================================================

const OverviewStats: React.FC<{
  stats: {
    total: number;
    completed: number;
    inProgress: number;
    overdue: number;
    pending: number;
    workTypeCount: number;
  };
}> = ({ stats }) => (
  <Card size="small" style={{ marginBottom: 16 }}>
    <Row gutter={[16, 8]} align="middle">
      <Col xs={12} sm={6} md={4}>
        <Statistic
          title="派工總數"
          value={stats.total}
          prefix={<SendOutlined />}
        />
      </Col>
      <Col xs={12} sm={6} md={4}>
        <Statistic
          title="已結案"
          value={stats.completed}
          prefix={<CheckCircleOutlined />}
          valueStyle={{ color: '#52c41a' }}
        />
      </Col>
      <Col xs={12} sm={6} md={4}>
        <Statistic
          title="進行中"
          value={stats.inProgress}
          prefix={<ClockCircleOutlined />}
          valueStyle={{ color: '#1677ff' }}
        />
      </Col>
      {stats.overdue > 0 && (
        <Col xs={12} sm={6} md={4}>
          <Statistic
            title="已逾期"
            value={stats.overdue}
            valueStyle={{ color: '#ff4d4f' }}
          />
        </Col>
      )}
      {stats.pending > 0 && (
        <Col xs={12} sm={6} md={4}>
          <Statistic
            title="未開始"
            value={stats.pending}
            valueStyle={{ color: '#8c8c8c' }}
          />
        </Col>
      )}
      <Col xs={12} sm={6} md={4}>
        <Statistic
          title="作業類別"
          value={stats.workTypeCount}
          prefix={<AppstoreOutlined />}
        />
      </Col>
    </Row>
  </Card>
);

// ============================================================================
// Main component
// ============================================================================

export const DispatchOverviewTab: React.FC<DispatchOverviewTabProps> = ({
  contractProjectId,
}) => {
  const navigate = useNavigate();
  const { isMobile } = useResponsive();
  const { columns, stats, isLoading } = useDispatchOverviewKanban(contractProjectId);

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

  const totalCards = useMemo(
    () => columns.reduce((sum, col) => sum + col.cards.length, 0),
    [columns],
  );

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 0' }}>
        <Spin>
          <div style={{ padding: 20 }}>
            <Text type="secondary">載入派工總覽...</Text>
          </div>
        </Spin>
      </div>
    );
  }

  if (totalCards === 0) {
    return (
      <Empty
        description="尚無派工紀錄"
        style={{ padding: '60px 0' }}
      />
    );
  }

  return (
    <>
      <OverviewStats stats={stats} />

      {isMobile ? (
        <MobileOverviewKanban
          columns={columns}
          onCardClick={handleCardClick}
          onAddNew={handleAddNew}
        />
      ) : (
        <div
          style={{
            display: 'flex',
            gap: 12,
            overflowX: 'auto',
            paddingBottom: 8,
            alignItems: 'flex-start',
            maxHeight: 'calc(100vh - 360px)',
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
                canEdit
              />
            ))}
        </div>
      )}
    </>
  );
};

// ============================================================================
// Mobile: Collapse panels
// ============================================================================

interface MobileOverviewKanbanProps {
  columns: KanbanColumnData[];
  onCardClick: (dispatchId: number) => void;
  onAddNew: (workType: string) => void;
}

const MobileOverviewKanbanInner: React.FC<MobileOverviewKanbanProps> = ({
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
                  />
                ))}
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
              </div>
            ),
          };
        }),
    [columns, onCardClick, onAddNew],
  );

  return (
    <Collapse
      defaultActiveKey={defaultActive}
      ghost
      items={items}
    />
  );
};

const MobileOverviewKanban = React.memo(MobileOverviewKanbanInner);

export default DispatchOverviewTab;

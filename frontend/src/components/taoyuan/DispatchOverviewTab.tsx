/**
 * DispatchOverviewTab - 派工總覽（看板 + 表格雙模式）
 *
 * 方案 C 整合：統一使用 morning-status API 的 display_status
 * - Segmented 切換：看板模式 / 表格模式
 * - 統計卡片共用 display_status（唯一狀態來源）
 * - 看板卡片標示 display_status Badge
 * - 表格模式 = 原晨報追蹤功能（排序/篩選/搜尋）
 *
 * @version 2.0.0 — 方案 C 整合
 * @date 2026-04-16
 */

import React, { useCallback, useMemo, useState } from 'react';
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
  Segmented,
} from 'antd';
import {
  PlusOutlined,
  CheckCircleOutlined,
  CalendarOutlined,
  SyncOutlined,
  WarningOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ROUTES } from '../../router/types';
import { apiClient } from '../../api/client';
import { TAOYUAN_DISPATCH_ENDPOINTS } from '../../api/endpoints';

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
import { MorningReportTrackingTable, type MorningStatusResponse } from './MorningReportTrackingTable';
import type { WorkRecordStatus } from '../../types/taoyuan';

const { Text } = Typography;

// ============================================================================
// Types
// ============================================================================

interface DispatchOverviewTabProps {
  contractProjectId: number;
}

// display_status → WorkRecordStatus 映射（供看板 Tag 相容）
const STATUS_TO_WRS: Record<string, WorkRecordStatus> = {
  '已交付': 'completed',
  '已結案': 'completed',
  '排程中': 'in_progress',
  '進行中': 'in_progress',
  '逾期': 'overdue',
  '闕漏紀錄': 'pending',
  '待結案': 'completed',
};

// ============================================================================
// Hook: build kanban data from dispatch orders + morning-status
// ============================================================================

function useDispatchOverviewKanban(contractProjectId: number) {
  const {
    dispatchOrders,
    total,
    isLoading: ordersLoading,
    refetch,
  } = useTaoyuanDispatchOrders({
    contract_project_id: contractProjectId,
    limit: 200,
  });

  // 同時 fetch morning-status 用 display_status 統一狀態（project scoped）
  const { data: morningData, isLoading: morningLoading } = useQuery({
    queryKey: ['dispatch-morning-status', contractProjectId],
    queryFn: () =>
      apiClient.post<MorningStatusResponse>(
        TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_MORNING_STATUS,
        { contract_project_id: contractProjectId },
      ),
    staleTime: 60_000,
  });

  const isLoading = ordersLoading || morningLoading;

  // 建立 id → display_status 查找表
  const statusMap = useMemo(() => {
    const map = new Map<number, string>();
    for (const item of (morningData?.items ?? []) as { id: number; display_status: string }[]) {
      map.set(item.id, item.display_status);
    }
    return map;
  }, [morningData]);

  const columns = useMemo<KanbanColumnData[]>(() => {
    const columnMap = new Map<string, KanbanCardData[]>();

    for (const dispatch of dispatchOrders) {
      const workTypes = getWorkTypes(dispatch);
      const displayStatus = statusMap.get(dispatch.id) || '進行中';
      const wrs = STATUS_TO_WRS[displayStatus] || 'in_progress';
      const wp = dispatch.work_progress;
      const card: KanbanCardData = {
        dispatch: { ...dispatch, _displayStatus: displayStatus } as typeof dispatch,
        computedStatus: wrs,
        recordCount: wp?.total ?? 0,
        recordIds: [],
      };

      if (workTypes.length === 0) {
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
  }, [dispatchOrders, statusMap]);

  return { columns, morningData, total, isLoading, refetch };
}

// ============================================================================
// Stats summary — 統一使用 morning-status display_status
// ============================================================================

const OverviewStats: React.FC<{
  summary: Record<string, number>;
  total: number;
  onFilter: (status: string | undefined) => void;
  activeFilter: string | undefined;
}> = ({ summary, total, onFilter, activeFilter }) => {
  const done = (summary['已交付'] ?? 0) + (summary['已結案'] ?? 0);
  const scheduled = summary['排程中'] ?? 0;
  const inProgress = summary['進行中'] ?? 0;
  const overdue = summary['逾期'] ?? 0;
  const missing = summary['闕漏紀錄'] ?? 0;
  const actionNeeded = overdue + missing;

  const toggle = (s: string) => onFilter(activeFilter === s ? undefined : s);

  return (
    <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
      <Col xs={12} sm={6}>
        <Card size="small" hoverable onClick={() => toggle('已交付')}
              style={{ borderTop: activeFilter === '已交付' ? '3px solid #52c41a' : undefined }}>
          <Statistic title="已完成/交付" value={done} valueStyle={{ color: '#52c41a' }}
                     prefix={<CheckCircleOutlined />}
                     suffix={<Text type="secondary" style={{ fontSize: 12 }}>/{total}</Text>} />
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card size="small" hoverable onClick={() => toggle('排程中')}
              style={{ borderTop: activeFilter === '排程中' ? '3px solid #1890ff' : undefined }}>
          <Statistic title="排程中" value={scheduled} valueStyle={{ color: '#1890ff' }}
                     prefix={<CalendarOutlined />} suffix="筆" />
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card size="small" hoverable onClick={() => toggle('進行中')}
              style={{ borderTop: activeFilter === '進行中' ? '3px solid #fa8c16' : undefined }}>
          <Statistic title="進行中" value={inProgress} valueStyle={{ color: '#fa8c16' }}
                     prefix={<SyncOutlined />} suffix="筆" />
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card size="small" hoverable onClick={() => toggle('__action_needed__')}
              style={{ borderTop: activeFilter === '__action_needed__' ? '3px solid #cf1322' : undefined }}>
          <Statistic title="需處理" value={actionNeeded}
                     valueStyle={{ color: actionNeeded > 0 ? '#cf1322' : '#999' }}
                     prefix={<WarningOutlined />}
                     suffix={missing > 0
                       ? <Text type="secondary" style={{ fontSize: 11 }}>逾期{overdue}+闕漏{missing}</Text>
                       : '筆'} />
        </Card>
      </Col>
    </Row>
  );
};

// ============================================================================
// Main component
// ============================================================================

export const DispatchOverviewTab: React.FC<DispatchOverviewTabProps> = ({
  contractProjectId,
}) => {
  const navigate = useNavigate();
  const { isMobile } = useResponsive();
  const { columns, morningData, total, isLoading } = useDispatchOverviewKanban(contractProjectId);
  const [viewMode, setViewMode] = useState<'kanban' | 'table'>('table');
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  const handleCardClick = useCallback(
    (dispatchId: number) => navigate(`/taoyuan/dispatch/${dispatchId}`),
    [navigate],
  );

  const handleAddNew = useCallback(
    (workType: string) => {
      navigate(ROUTES.TAOYUAN_DISPATCH_CREATE, {
        state: { contract_project_id: contractProjectId, work_type: workType },
      });
    },
    [navigate, contractProjectId],
  );

  const summary = useMemo(() => morningData?.summary ?? {}, [morningData]);

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 0' }}>
        <Spin><div style={{ padding: 20 }}><Text type="secondary">載入派工總覽...</Text></div></Spin>
      </div>
    );
  }

  return (
    <>
      {/* 統一統計卡片 */}
      <OverviewStats
        summary={summary}
        total={morningData?.total ?? total}
        onFilter={setStatusFilter}
        activeFilter={statusFilter}
      />

      {/* Segmented 切換 */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <Segmented
          value={viewMode}
          onChange={(v) => setViewMode(v as 'kanban' | 'table')}
          options={[
            { value: 'kanban', icon: <AppstoreOutlined />, label: isMobile ? '' : '看板' },
            { value: 'table', icon: <UnorderedListOutlined />, label: isMobile ? '' : '表格' },
          ]}
          size={isMobile ? 'small' : 'middle'}
        />
      </div>

      {viewMode === 'table' ? (
        <MorningReportTrackingTable
          data={morningData}
          isLoading={false}
          externalFilter={statusFilter}
        />
      ) : (
        (() => {
          // 看板模式：依 statusFilter 過濾卡片（與統計卡片互動）
          const filteredColumns = statusFilter
            ? columns.map(col => ({
                ...col,
                cards: col.cards.filter(c => {
                  const ds = (c.dispatch as unknown as Record<string, unknown>)._displayStatus as string;
                  if (statusFilter === '已交付') return ds === '已交付' || ds === '已結案';
                  if (statusFilter === '__action_needed__') return ds === '逾期' || ds === '闕漏紀錄';
                  return ds === statusFilter;
                }),
              }))
            : columns;
          const filteredTotal = filteredColumns.reduce((s, col) => s + col.cards.length, 0);

          return filteredTotal === 0 ? (
            <Empty description={statusFilter ? `「${statusFilter}」無符合項目` : '尚無派工紀錄'} style={{ padding: '60px 0' }} />
          ) : isMobile ? (
            <MobileOverviewKanban columns={filteredColumns} onCardClick={handleCardClick} onAddNew={handleAddNew} />
          ) : (
            <div style={{ display: 'flex', gap: 12, overflowX: 'auto', overflowY: 'hidden', paddingBottom: 8, alignItems: 'flex-start' }}>
              {filteredColumns.filter((col) => col.cards.length > 0).map((col) => (
                <KanbanColumn key={col.workType} data={col} onCardClick={handleCardClick} onAddNew={handleAddNew} canEdit />
              ))}
          </div>
          );
        })()
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
                  <KanbanCard key={card.dispatch.id} data={card} onClick={onCardClick} />
                ))}
                <Button type="text" icon={<PlusOutlined />} onClick={() => onAddNew(col.workType)} block
                  style={{ marginTop: 4, color: '#8c8c8c', borderRadius: 6, height: 32, fontSize: 12 }}>
                  新增派工
                </Button>
              </div>
            ),
          };
        }),
    [columns, onCardClick, onAddNew],
  );

  return <Collapse defaultActiveKey={defaultActive} ghost items={items} />;
};

const MobileOverviewKanban = React.memo(MobileOverviewKanbanInner);

export default DispatchOverviewTab;

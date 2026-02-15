/**
 * ProjectWorkOverviewTab - 作業總覽整合 Tab
 *
 * 三視圖統一：公文對照表 + 時間軸 + 看板
 * - 公文對照：對應 Excel 矩陣，以派工單為主軸顯示收發文對照
 * - 時間軸：批次分組 Timeline，顯示里程碑進度
 * - 看板：作業類別 Kanban，顯示派工分佈
 *
 * 交互：看板卡片點擊 → 切換到公文對照並高亮目標派工單
 *
 * @version 1.0.0
 * @date 2026-02-13
 */

import React, { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Row,
  Col,
  Statistic,
  Segmented,
  Select,
  Button,
  Space,
  Empty,
  Table,
  App,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  PlusOutlined,
  FileTextOutlined,
  SendOutlined,
  OrderedListOutlined,
  ApartmentOutlined,
  AppstoreOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  RocketOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { Tag, Tooltip, Popconfirm, Typography } from 'antd';

import { workflowApi } from '../../../api/taoyuan';
import type {
  WorkRecord,
  MilestoneType,
  WorkRecordStatus,
  ProjectDispatchLinkItem,
} from '../../../types/taoyuan';
import { logger } from '../../../services/logger';

import {
  useProjectWorkData,
  CorrespondenceMatrix,
  WorkflowTimelineView,
  WorkflowKanbanView,
  milestoneLabel,
  milestoneColor,
  statusLabel,
  statusColor,
} from '../../../components/taoyuan/workflow';

const { Text } = Typography;

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
  const queryClient = useQueryClient();
  const { message } = App.useApp();

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
  // Mutations
  // ===========================================================================

  const deleteMutation = useMutation({
    mutationFn: (id: number) => workflowApi.delete(id),
    onSuccess: () => {
      message.success('作業紀錄已刪除');
      queryClient.invalidateQueries({
        queryKey: ['project-work-records', projectId],
      });
      queryClient.invalidateQueries({
        queryKey: ['dispatch-work-records'],
      });
    },
    onError: (error: Error) => {
      logger.error('[ProjectWorkOverview] 刪除失敗:', error);
      message.error('刪除失敗，請稍後再試');
    },
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
    [deleteMutation],
  );

  // 看板卡片點擊 → 切到公文對照並高亮
  const handleKanbanCardClick = useCallback(
    (dispatchId: number) => {
      setHighlightDispatchId(dispatchId);
      setViewMode('correspondence');
    },
    [],
  );

  // 導航到派工單詳情（直接跳到作業歷程 Tab）
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
  // 表格欄位定義（平面表格視圖）
  // ===========================================================================

  const tableColumns: ColumnsType<WorkRecord> = useMemo(
    () => [
      {
        title: '批次',
        key: 'batch',
        width: 90,
        render: (_: unknown, record: WorkRecord) =>
          record.batch_no ? (
            <Tag color="blue">
              {record.batch_label || `第${record.batch_no}批`}
            </Tag>
          ) : (
            <Text type="secondary">-</Text>
          ),
      },
      {
        title: '序號',
        dataIndex: 'sort_order',
        key: 'sort_order',
        width: 60,
        align: 'center' as const,
      },
      {
        title: '派工單',
        dataIndex: 'dispatch_subject',
        key: 'dispatch_subject',
        width: 150,
        ellipsis: true,
        render: (val: string) => val || '-',
      },
      {
        title: '里程碑',
        dataIndex: 'milestone_type',
        key: 'milestone_type',
        width: 110,
        render: (type: MilestoneType) => (
          <Tag color={milestoneColor(type)}>{milestoneLabel(type)}</Tag>
        ),
      },
      {
        title: '說明',
        dataIndex: 'description',
        key: 'description',
        ellipsis: true,
      },
      {
        title: '紀錄日期',
        dataIndex: 'record_date',
        key: 'record_date',
        width: 110,
        render: (val: string) =>
          val ? dayjs(val).format('YYYY-MM-DD') : '-',
      },
      {
        title: '狀態',
        dataIndex: 'status',
        key: 'status',
        width: 90,
        render: (status: WorkRecordStatus) => (
          <Tag color={statusColor(status)}>{statusLabel(status)}</Tag>
        ),
      },
      {
        title: '來文',
        key: 'incoming_doc',
        width: 120,
        render: (_: unknown, record: WorkRecord) =>
          record.incoming_doc?.doc_number ? (
            <Tooltip title={record.incoming_doc.subject}>
              <Text ellipsis style={{ maxWidth: 100 }}>
                <FileTextOutlined style={{ marginRight: 4 }} />
                {record.incoming_doc.doc_number}
              </Text>
            </Tooltip>
          ) : (
            '-'
          ),
      },
      ...(canEdit
        ? [
            {
              title: '操作',
              key: 'action',
              width: 100,
              fixed: 'right' as const,
              render: (_: unknown, record: WorkRecord) => (
                <Space size="small">
                  <Tooltip title="編輯">
                    <Button
                      type="link"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => handleEditRecord(record)}
                    />
                  </Tooltip>
                  <Popconfirm
                    title="確定要刪除此紀錄嗎？"
                    onConfirm={() => handleDeleteRecord(record.id)}
                    okText="確定"
                    cancelText="取消"
                  >
                    <Tooltip title="刪除">
                      <Button
                        type="link"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                      />
                    </Tooltip>
                  </Popconfirm>
                </Space>
              ),
            },
          ]
        : []),
    ],
    [canEdit, handleEditRecord, handleDeleteRecord],
  );

  // ===========================================================================
  // Render
  // ===========================================================================

  return (
    <div>
      {/* 統計儀表板 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 8]}>
          <Col xs={12} sm={8} md={3}>
            <Statistic
              title="派工數"
              value={stats.dispatchCount}
              prefix={<OrderedListOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={3}>
            <Statistic
              title="紀錄數"
              value={stats.total}
              prefix={<OrderedListOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={3}>
            <Statistic
              title="已完成"
              value={stats.completed}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={3}>
            <Statistic
              title="進行中"
              value={stats.inProgress}
              valueStyle={{ color: '#1890ff' }}
              prefix={<ClockCircleOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={3}>
            <Statistic
              title="逾期"
              value={stats.overdue}
              valueStyle={stats.overdue > 0 ? { color: '#ff4d4f' } : undefined}
              prefix={<ExclamationCircleOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={3}>
            <Statistic
              title="來文"
              value={stats.incomingDocs}
              prefix={<FileTextOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={3}>
            <Statistic
              title="發文"
              value={stats.outgoingDocs}
              prefix={<SendOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={3}>
            <Statistic
              title="當前階段"
              value={stats.currentStage}
              prefix={<RocketOutlined />}
              valueStyle={{ fontSize: 14 }}
            />
          </Col>
        </Row>
      </Card>

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

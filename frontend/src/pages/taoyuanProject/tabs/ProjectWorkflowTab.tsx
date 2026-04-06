/**
 * 工程作業歷程 Tab 元件 - 批次分組時間軸視圖
 *
 * v2.1.0 重構：拆分 WorkflowStatsCard + WorkflowTimeline
 *
 * @version 2.1.0
 * @date 2026-03-18
 */

import React, { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Button,
  Tag,
  Space,
  Empty,
  Popconfirm,
  Tooltip,
  Typography,
  Select,
  App,
  Segmented,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
  OrderedListOutlined,
  ApartmentOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';

import { workflowApi } from '../../../api/taoyuan';
import { queryKeys } from '../../../config/queryConfig';
import type {
  WorkRecord,
  WorkRecordStatus,
  ProjectDispatchLink,
  DocBrief,
} from '../../../types/taoyuan';
import {
  getCategoryLabel,
  getCategoryColor,
  getStatusLabel,
  getStatusColor,
  isOutgoingDocNumber,
  computeDocStats,
  computeCurrentStage,
} from '../../../components/taoyuan/workflow';
import { logger } from '../../../services/logger';
import { WorkflowStatsCard } from './WorkflowStatsCard';
import type { WorkflowStats } from './WorkflowStatsCard';
import { WorkflowTimeline } from './WorkflowTimeline';

const { Text } = Typography;

// =============================================================================
// Props
// =============================================================================

export interface ProjectWorkflowTabProps {
  projectId: number;
  linkedDispatches: ProjectDispatchLink[];
  canEdit?: boolean;
}

// =============================================================================
// 批次分組輔助
// =============================================================================

interface BatchGroup {
  batchNo: number | null;
  label: string;
  records: WorkRecord[];
  completedCount: number;
  totalCount: number;
}

function groupByBatch(records: WorkRecord[]): BatchGroup[] {
  const completed = records.filter((r) => r.status === 'completed').length;
  return [{
    batchNo: null,
    label: '未分批',
    records: [...records].sort((a, b) => a.sort_order - b.sort_order),
    completedCount: completed,
    totalCount: records.length,
  }];
}

// =============================================================================
// 主元件
// =============================================================================

export const ProjectWorkflowTab: React.FC<ProjectWorkflowTabProps> = ({
  projectId,
  linkedDispatches,
  canEdit = true,
}) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [selectedDispatchId, setSelectedDispatchId] = useState<number>();
  const [viewMode, setViewMode] = useState<string>('timeline');

  // 資料查詢
  const {
    data: workRecordData,
    isLoading,
  } = useQuery({
    queryKey: queryKeys.workRecords.project(projectId),
    queryFn: () => workflowApi.listByProject(projectId),
    enabled: projectId > 0,
  });

  const records = useMemo(
    () => workRecordData?.items ?? [],
    [workRecordData?.items],
  );

  // 統計資料
  const stats = useMemo((): WorkflowStats => {
    const total = records.length;
    const completed = records.filter((r) => r.status === 'completed').length;
    const inProgress = records.filter((r) => r.status === 'in_progress').length;
    const overdue = records.filter((r) => r.status === 'overdue').length;
    const { incomingDocs, outgoingDocs } = computeDocStats(records);
    const currentStage = computeCurrentStage(records);

    return { total, completed, inProgress, overdue, incomingDocs, outgoingDocs, currentStage };
  }, [records]);

  const batchGroups = useMemo(() => groupByBatch(records), [records]);

  // Mutations
  const deleteMutation = useMutation({
    mutationFn: (id: number) => workflowApi.delete(id),
    onSuccess: () => {
      message.success('作業紀錄已刪除');
      queryClient.invalidateQueries({ queryKey: queryKeys.workRecords.project(projectId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.workRecords.dispatchAll });
    },
    onError: (error: Error) => {
      logger.error('[ProjectWorkflowTab] 刪除失敗:', error);
      message.error('刪除失敗，請稍後再試');
    },
  });

  // Handlers
  const returnTo = encodeURIComponent(`/taoyuan/project/${projectId}?tab=workflow`);

  const handleAdd = useCallback(() => {
    if (!selectedDispatchId) return;
    navigate(`/taoyuan/dispatch/${selectedDispatchId}/workflow/create?returnTo=${returnTo}`);
  }, [navigate, selectedDispatchId, returnTo]);

  const handleEdit = useCallback(
    (record: WorkRecord) => {
      navigate(`/taoyuan/dispatch/${record.dispatch_order_id}/workflow/${record.id}/edit?returnTo=${returnTo}`);
    },
    [navigate, returnTo],
  );

  // Table Columns
  const dispatchOptions = useMemo(
    () =>
      linkedDispatches.map((d) => ({
        value: d.dispatch_order_id,
        label: `${d.dispatch_no}${d.project_name ? ` - ${d.project_name}` : ''}`,
      })),
    [linkedDispatches],
  );

  const columns: ColumnsType<WorkRecord> = useMemo(
    () => [
      {
        title: '批次',
        key: 'batch',
        width: 90,
        render: () => (
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
        title: '作業類別',
        key: 'work_category',
        width: 110,
        render: (_: unknown, record: WorkRecord) => (
          <Tag color={getCategoryColor(record)}>{getCategoryLabel(record)}</Tag>
        ),
      },
      {
        title: '說明',
        key: 'description',
        width: 220,
        ellipsis: { showTitle: false },
        render: (_: unknown, record: WorkRecord) => {
          const doc = record.document || record.incoming_doc || record.outgoing_doc;
          const text = record.description || doc?.subject;
          return text ? (
            <Tooltip title={text} placement="topLeft">
              <span>{text}</span>
            </Tooltip>
          ) : '-';
        },
      },
      {
        title: '紀錄日期',
        dataIndex: 'record_date',
        key: 'record_date',
        width: 110,
        render: (val: string) => val ? dayjs(val).format('YYYY-MM-DD') : '-',
      },
      {
        title: '狀態',
        dataIndex: 'status',
        key: 'status',
        width: 90,
        render: (status: WorkRecordStatus) => (
          <Tag color={getStatusColor(status)}>{getStatusLabel(status)}</Tag>
        ),
      },
      {
        title: '關聯公文',
        key: 'linked_doc',
        width: 140,
        render: (_: unknown, record: WorkRecord) => {
          const doc: DocBrief | undefined = record.document || record.incoming_doc || record.outgoing_doc;
          if (!doc?.doc_number) return '-';
          const isOutgoing = isOutgoingDocNumber(doc.doc_number);
          return (
            <Tooltip title={doc.subject}>
              <Text ellipsis style={{ maxWidth: 120 }}>
                <FileTextOutlined style={{ marginRight: 4, color: isOutgoing ? '#52c41a' : '#1677ff' }} />
                {doc.doc_number}
              </Text>
            </Tooltip>
          );
        },
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
                      onClick={() => handleEdit(record)}
                    />
                  </Tooltip>
                  <Popconfirm
                    title="確定要刪除此紀錄嗎？"
                    onConfirm={() => deleteMutation.mutate(record.id)}
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
    [canEdit, handleEdit, deleteMutation],
  );

  // Render
  return (
    <div>
      <WorkflowStatsCard stats={stats} />

      {/* 工具列 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
        {canEdit && (
          <Space>
            <Select
              placeholder="選擇派工單"
              style={{ width: 300 }}
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
              新增作業紀錄
            </Button>
          </Space>
        )}
        <Segmented
          value={viewMode}
          onChange={(val) => setViewMode(val as string)}
          options={[
            { value: 'timeline', label: '時間軸', icon: <ApartmentOutlined /> },
            { value: 'table', label: '表格', icon: <OrderedListOutlined /> },
          ]}
        />
      </div>

      {/* 視圖內容 */}
      {records.length === 0 ? (
        <Empty
          description="尚無作業歷程紀錄"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : viewMode === 'timeline' ? (
        <WorkflowTimeline
          batchGroups={batchGroups}
          canEdit={canEdit}
          onEdit={handleEdit}
          onDelete={(id) => deleteMutation.mutate(id)}
        />
      ) : (
        <Table<WorkRecord>
          columns={columns}
          dataSource={records}
          rowKey="id"
          loading={isLoading}
          size="small"
          pagination={false}
          scroll={{ x: 1100 }}
        />
      )}
    </div>
  );
};

export default ProjectWorkflowTab;

/**
 * 工程作業歷程 Tab 元件 - 批次分組時間軸視圖
 *
 * v2.0.0 重構：
 * - 整合儀表板：統計總派工數、來文數、發文數、完成里程碑數、當前階段
 * - 批次分組視圖：依 batch_no 分組，未指定批次歸為「未分批」
 * - 時間軸佈局：每個批次以 Timeline 呈現里程碑進度
 * - 保留平面表格作為切換選項
 *
 * @version 2.0.0
 * @date 2026-02-13
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
  Card,
  Row,
  Col,
  Statistic,
  Timeline,
  Segmented,
  Collapse,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
  OrderedListOutlined,
  ApartmentOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';

import { workflowApi } from '../../../api/taoyuan';
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
} from '../../../components/taoyuan/workflow/chainConstants';
import { isOutgoingDocNumber } from '../../../components/taoyuan/workflow/chainUtils';
import { logger } from '../../../services/logger';

const { Text, Title } = Typography;

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
  const groups = new Map<number | null, WorkRecord[]>();

  for (const r of records) {
    const key = r.batch_no ?? null;
    const arr = groups.get(key) ?? [];
    arr.push(r);
    groups.set(key, arr);
  }

  const result: BatchGroup[] = [];

  // 有批次的先排序
  const sortedKeys = Array.from(groups.keys()).sort((a, b) => {
    if (a === null) return 1;
    if (b === null) return -1;
    return a - b;
  });

  for (const key of sortedKeys) {
    const recs = groups.get(key) ?? [];
    const completed = recs.filter((r) => r.status === 'completed').length;
    result.push({
      batchNo: key,
      label: key !== null
        ? (recs[0]?.batch_label || `第${key}批結案`)
        : '未分批',
      records: recs.sort((a, b) => a.sort_order - b.sort_order),
      completedCount: completed,
      totalCount: recs.length,
    });
  }

  return result;
}

// =============================================================================
// 時間軸 dot 顏色
// =============================================================================

function timelineDotColor(status: WorkRecordStatus): string {
  switch (status) {
    case 'completed': return 'green';
    case 'in_progress': return 'blue';
    case 'overdue': return 'red';
    default: return 'gray';
  }
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

  // ===========================================================================
  // 資料查詢
  // ===========================================================================

  const {
    data: workRecordData,
    isLoading,
  } = useQuery({
    queryKey: ['project-work-records', projectId],
    queryFn: () => workflowApi.listByProject(projectId),
    enabled: projectId > 0,
  });

  const records = useMemo(
    () => workRecordData?.items ?? [],
    [workRecordData?.items],
  );

  // ===========================================================================
  // 統計資料 (Task #8: 整合儀表板)
  // ===========================================================================

  const stats = useMemo(() => {
    const total = records.length;
    const completed = records.filter((r) => r.status === 'completed').length;
    const inProgress = records.filter((r) => r.status === 'in_progress').length;
    const overdue = records.filter((r) => r.status === 'overdue').length;
    // 統計來文/發文數（新舊格式兼容）
    const incomingIds = new Set<number>();
    const outgoingIds = new Set<number>();
    for (const r of records) {
      if (r.incoming_doc_id) incomingIds.add(r.incoming_doc_id);
      if (r.outgoing_doc_id) outgoingIds.add(r.outgoing_doc_id);
      if (r.document_id) {
        if (isOutgoingDocNumber(r.document?.doc_number)) {
          outgoingIds.add(r.document_id);
        } else {
          incomingIds.add(r.document_id);
        }
      }
    }
    const incomingDocs = incomingIds.size;
    const outgoingDocs = outgoingIds.size;

    // 最新階段：取最後一筆非 completed 紀錄
    let currentStage = '尚未開始';
    for (let i = records.length - 1; i >= 0; i--) {
      const rec = records[i];
      if (rec && rec.status !== 'completed') {
        currentStage = getCategoryLabel(rec);
        break;
      }
    }
    // 若全部完成
    if (total > 0 && completed === total) {
      currentStage = '全部完成';
    }

    return { total, completed, inProgress, overdue, incomingDocs, outgoingDocs, currentStage };
  }, [records]);

  // 批次分組
  const batchGroups = useMemo(() => groupByBatch(records), [records]);

  // ===========================================================================
  // Mutations
  // ===========================================================================

  const deleteMutation = useMutation({
    mutationFn: (id: number) => workflowApi.delete(id),
    onSuccess: () => {
      message.success('作業紀錄已刪除');
      queryClient.invalidateQueries({ queryKey: ['project-work-records', projectId] });
      queryClient.invalidateQueries({ queryKey: ['dispatch-work-records'] });
    },
    onError: (error: Error) => {
      logger.error('[ProjectWorkflowTab] 刪除失敗:', error);
      message.error('刪除失敗，請稍後再試');
    },
  });

  // ===========================================================================
  // Handlers
  // ===========================================================================

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

  // ===========================================================================
  // Table Columns (平面視圖)
  // ===========================================================================

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
        render: (_: unknown, record: WorkRecord) =>
          record.batch_no ? (
            <Tag color="blue">{record.batch_label || `第${record.batch_no}批`}</Tag>
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
        ellipsis: true,
        render: (_: unknown, record: WorkRecord) => {
          const doc = record.document || record.incoming_doc || record.outgoing_doc;
          const text = record.description || doc?.subject;
          return text ? (
            <Tooltip title={text}>
              <Text ellipsis style={{ maxWidth: 200 }}>{text}</Text>
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

  // ===========================================================================
  // 時間軸渲染
  // ===========================================================================

  const renderTimeline = useCallback(
    (group: BatchGroup) => (
      <Timeline
        items={group.records.map((r) => ({
          color: timelineDotColor(r.status),
          children: (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <Space size="small" wrap>
                  <Tag color={getCategoryColor(r)}>
                    {getCategoryLabel(r)}
                  </Tag>
                  <Tag color={getStatusColor(r.status)}>
                    {getStatusLabel(r.status)}
                  </Tag>
                  {r.record_date && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {dayjs(r.record_date).format('YYYY-MM-DD')}
                    </Text>
                  )}
                </Space>
                {r.description && (
                  <div style={{ marginTop: 4 }}>
                    <Text>{r.description}</Text>
                  </div>
                )}
                {r.dispatch_subject && (
                  <div style={{ marginTop: 2 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      派工: {r.dispatch_subject}
                    </Text>
                  </div>
                )}
                {(() => {
                  // 新舊格式公文顯示兼容
                  const docs: { doc: DocBrief; isOutgoing: boolean }[] = [];
                  if (r.incoming_doc?.doc_number) {
                    docs.push({ doc: r.incoming_doc, isOutgoing: false });
                  }
                  if (r.outgoing_doc?.doc_number) {
                    docs.push({ doc: r.outgoing_doc, isOutgoing: true });
                  }
                  if (docs.length === 0 && r.document?.doc_number) {
                    docs.push({
                      doc: r.document,
                      isOutgoing: isOutgoingDocNumber(r.document.doc_number),
                    });
                  }
                  if (docs.length === 0) return null;
                  return (
                    <div style={{ marginTop: 2 }}>
                      {docs.map((d, idx) => (
                        <Tooltip key={idx} title={d.doc.subject}>
                          <Tag
                            icon={<FileTextOutlined />}
                            color={d.isOutgoing ? 'blue' : undefined}
                            style={{ fontSize: 11 }}
                          >
                            {d.isOutgoing ? '覆文' : '來文'}: {d.doc.doc_number}
                          </Tag>
                        </Tooltip>
                      ))}
                    </div>
                  );
                })()}
              </div>
              {canEdit && (
                <Space size="small" style={{ flexShrink: 0, marginLeft: 8 }}>
                  <Button
                    type="link"
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => handleEdit(r)}
                  />
                  <Popconfirm
                    title="確定要刪除此紀錄嗎？"
                    onConfirm={() => deleteMutation.mutate(r.id)}
                    okText="確定"
                    cancelText="取消"
                  >
                    <Button type="link" size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </Space>
              )}
            </div>
          ),
        }))}
      />
    ),
    [canEdit, handleEdit, deleteMutation],
  );

  // ===========================================================================
  // Render
  // ===========================================================================

  return (
    <div>
      {/* 整合儀表板 (Task #8) */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 8]}>
          <Col xs={12} sm={8} md={4}>
            <Statistic
              title="總紀錄數"
              value={stats.total}
              prefix={<OrderedListOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Statistic
              title="已完成"
              value={stats.completed}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Statistic
              title="進行中"
              value={stats.inProgress}
              valueStyle={{ color: '#1890ff' }}
              prefix={<ClockCircleOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Statistic
              title="逾期"
              value={stats.overdue}
              valueStyle={stats.overdue > 0 ? { color: '#ff4d4f' } : undefined}
              prefix={<ExclamationCircleOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Statistic title="關聯來文" value={stats.incomingDocs} prefix={<FileTextOutlined />} />
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Statistic
              title="當前階段"
              value={stats.currentStage}
              prefix={<RocketOutlined />}
              valueStyle={{ fontSize: 16 }}
            />
          </Col>
        </Row>
      </Card>

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
        /* 批次分組時間軸視圖 (Task #6) */
        <Collapse
          defaultActiveKey={batchGroups.map((_, i) => String(i))}
          items={batchGroups.map((group, idx) => ({
            key: String(idx),
            label: (
              <Space>
                <Title level={5} style={{ margin: 0 }}>
                  {group.label}
                </Title>
                <Badge
                  count={`${group.completedCount}/${group.totalCount}`}
                  style={{
                    backgroundColor: group.completedCount === group.totalCount ? '#52c41a' : '#1890ff',
                  }}
                />
              </Space>
            ),
            children: renderTimeline(group),
          }))}
        />
      ) : (
        /* 平面表格視圖 */
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

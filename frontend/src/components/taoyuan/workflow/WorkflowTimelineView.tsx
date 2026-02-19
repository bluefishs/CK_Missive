/**
 * WorkflowTimelineView - 批次分組時間軸視圖
 *
 * 以 batch_no 分組、Timeline 呈現里程碑。
 *
 * @version 1.0.0
 * @date 2026-02-13
 */

import React, { useCallback } from 'react';
import {
  Collapse,
  Timeline,
  Tag,
  Space,
  Button,
  Tooltip,
  Typography,
  Popconfirm,
  Badge,
  Empty,
} from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import type { WorkRecord, DocBrief } from '../../../types/taoyuan';
import type { BatchGroup } from './useProjectWorkData';
import {
  statusLabel,
  statusColor,
} from './useProjectWorkData';
import {
  getCategoryLabel,
  getCategoryColor,
} from './chainConstants';
import { isOutgoingDocNumber } from './chainUtils';

const { Text, Title } = Typography;

// ============================================================================
// Props
// ============================================================================

interface WorkflowTimelineViewProps {
  batchGroups: BatchGroup[];
  canEdit?: boolean;
  onEditRecord?: (record: WorkRecord) => void;
  onDeleteRecord?: (recordId: number) => void;
}

// ============================================================================
// Timeline dot color
// ============================================================================

function timelineDotColor(status: string): string {
  switch (status) {
    case 'completed':
      return 'green';
    case 'in_progress':
      return 'blue';
    case 'overdue':
      return 'red';
    default:
      return 'gray';
  }
}

// ============================================================================
// 主元件
// ============================================================================

const WorkflowTimelineViewInner: React.FC<WorkflowTimelineViewProps> = ({
  batchGroups,
  canEdit,
  onEditRecord,
  onDeleteRecord,
}) => {
  const renderTimeline = useCallback(
    (group: BatchGroup) => (
      <Timeline
        items={group.records.map((r) => ({
          color: timelineDotColor(r.status),
          children: (
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
              }}
            >
              <div>
                <Space size="small" wrap>
                  <Tag color={getCategoryColor(r)}>
                    {getCategoryLabel(r)}
                  </Tag>
                  <Tag color={statusColor(r.status)}>
                    {statusLabel(r.status)}
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
                  // 新格式（僅在無舊格式時）
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
                <Space
                  size="small"
                  style={{ flexShrink: 0, marginLeft: 8 }}
                >
                  {onEditRecord && (
                    <Button
                      type="link"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => onEditRecord(r)}
                      aria-label="編輯"
                    />
                  )}
                  {onDeleteRecord && (
                    <Popconfirm
                      title="確定要刪除此紀錄嗎？"
                      onConfirm={() => onDeleteRecord(r.id)}
                      okText="確定"
                      cancelText="取消"
                    >
                      <Button
                        type="link"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        aria-label="刪除"
                      />
                    </Popconfirm>
                  )}
                </Space>
              )}
            </div>
          ),
        }))}
      />
    ),
    [canEdit, onEditRecord, onDeleteRecord],
  );

  if (batchGroups.length === 0) {
    return (
      <Empty
        description="尚無作業歷程紀錄"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  return (
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
                backgroundColor:
                  group.completedCount === group.totalCount
                    ? '#52c41a'
                    : '#1890ff',
              }}
            />
          </Space>
        ),
        children: renderTimeline(group),
      }))}
    />
  );
};

export const WorkflowTimelineView = React.memo(WorkflowTimelineViewInner);

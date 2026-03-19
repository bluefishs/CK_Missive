import React, { useCallback } from 'react';
import {
  Button,
  Tag,
  Space,
  Popconfirm,
  Tooltip,
  Typography,
  Timeline,
  Collapse,
  Badge,
} from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import type {
  WorkRecord,
  WorkRecordStatus,
  DocBrief,
} from '../../../types/taoyuan';
import {
  getCategoryLabel,
  getCategoryColor,
  getStatusLabel,
  getStatusColor,
  isOutgoingDocNumber,
} from '../../../components/taoyuan/workflow';

const { Text, Title } = Typography;

interface BatchGroup {
  batchNo: number | null;
  label: string;
  records: WorkRecord[];
  completedCount: number;
  totalCount: number;
}

function timelineDotColor(status: WorkRecordStatus): string {
  switch (status) {
    case 'completed': return 'green';
    case 'in_progress': return 'blue';
    case 'overdue': return 'red';
    default: return 'gray';
  }
}

interface WorkflowTimelineProps {
  batchGroups: BatchGroup[];
  canEdit: boolean;
  onEdit: (record: WorkRecord) => void;
  onDelete: (id: number) => void;
}

export const WorkflowTimeline: React.FC<WorkflowTimelineProps> = ({
  batchGroups,
  canEdit,
  onEdit,
  onDelete,
}) => {
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
                    onClick={() => onEdit(r)}
                    aria-label="編輯"
                  />
                  <Popconfirm
                    title="確定要刪除此紀錄嗎？"
                    onConfirm={() => onDelete(r.id)}
                    okText="確定"
                    cancelText="取消"
                  >
                    <Button type="link" size="small" danger icon={<DeleteOutlined />} aria-label="刪除" />
                  </Popconfirm>
                </Space>
              )}
            </div>
          ),
        }))}
      />
    ),
    [canEdit, onEdit, onDelete],
  );

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
                backgroundColor: group.completedCount === group.totalCount ? '#52c41a' : '#1890ff',
              }}
            />
          </Space>
        ),
        children: renderTimeline(group),
      }))}
    />
  );
};

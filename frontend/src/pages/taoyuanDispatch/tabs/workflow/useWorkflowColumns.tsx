/**
 * useWorkflowColumns - 作業歷程表格欄位定義
 *
 * 從 DispatchWorkflowTab 拆分，降低主元件行數。
 *
 * @version 1.0.0
 * @date 2026-02-25
 */

import React, { useMemo } from 'react';
import {
  Tag,
  Space,
  Button,
  Tooltip,
  Typography,
  Popconfirm,
} from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import type { WorkRecord, WorkRecordStatus } from '../../../../types/taoyuan';
import {
  milestoneLabel,
  milestoneColor,
  statusLabel,
  statusColor,
  getEffectiveDoc,
  getDocDirection,
  getCategoryLabel,
  getCategoryColor,
} from '../../../../components/taoyuan/workflow';

const { Text } = Typography;

interface UseWorkflowColumnsOptions {
  canEdit: boolean;
  onEdit: (record: WorkRecord) => void;
  onDocClick: (docId: number) => void;
  onDelete: (id: number) => void;
}

export function useWorkflowColumns({
  canEdit,
  onEdit,
  onDocClick,
  onDelete,
}: UseWorkflowColumnsOptions): ColumnsType<WorkRecord> {
  return useMemo(
    () => [
      {
        title: '序號',
        dataIndex: 'sort_order',
        key: 'sort_order',
        width: 50,
        align: 'center' as const,
      },
      {
        title: '類別',
        key: 'category',
        width: 90,
        render: (_: unknown, record: WorkRecord) =>
          record.work_category ? (
            <Tag color={getCategoryColor(record)}>{getCategoryLabel(record)}</Tag>
          ) : (
            <Tag color={milestoneColor(record.milestone_type)}>{milestoneLabel(record.milestone_type)}</Tag>
          ),
      },
      {
        title: '說明',
        key: 'description',
        ellipsis: true,
        render: (_: unknown, record: WorkRecord) => {
          const doc = getEffectiveDoc(record);
          const text = record.description || doc?.subject;
          if (!text) return '-';
          return (
            <Tooltip title={text}>
              <Text ellipsis style={{ maxWidth: 200 }}>{text}</Text>
            </Tooltip>
          );
        },
      },
      {
        title: '紀錄日期',
        dataIndex: 'record_date',
        key: 'record_date',
        width: 100,
        render: (val: string) => (val ? dayjs(val).format('YYYY-MM-DD') : '-'),
      },
      {
        title: '期限',
        dataIndex: 'deadline_date',
        key: 'deadline_date',
        width: 95,
        render: (val: string) => (val ? dayjs(val).format('YYYY-MM-DD') : '-'),
      },
      {
        title: '狀態',
        dataIndex: 'status',
        key: 'status',
        width: 80,
        render: (status: WorkRecordStatus) => (
          <Tag color={statusColor(status)}>{statusLabel(status)}</Tag>
        ),
      },
      {
        title: '來文',
        key: 'incoming_doc',
        width: 155,
        render: (_: unknown, record: WorkRecord) => {
          if (record.incoming_doc?.doc_number) {
            return (
              <Tooltip title={record.incoming_doc.subject}>
                <Text
                  ellipsis
                  style={{ maxWidth: 135, cursor: 'pointer', color: '#1677ff' }}
                  onClick={() => record.incoming_doc?.id && onDocClick(record.incoming_doc.id)}
                >
                  <FileTextOutlined style={{ marginRight: 4 }} />
                  {record.incoming_doc.doc_number}
                </Text>
              </Tooltip>
            );
          }
          const doc = getEffectiveDoc(record);
          const dir = getDocDirection(record);
          if (doc?.doc_number && dir === 'incoming') {
            return (
              <Tooltip title={doc.subject}>
                <Text
                  ellipsis
                  style={{ maxWidth: 135, cursor: 'pointer', color: '#1677ff' }}
                  onClick={() => doc.id && onDocClick(doc.id)}
                >
                  <FileTextOutlined style={{ marginRight: 4 }} />
                  {doc.doc_number}
                </Text>
              </Tooltip>
            );
          }
          return '-';
        },
      },
      {
        title: '覆文',
        key: 'outgoing_doc',
        width: 155,
        render: (_: unknown, record: WorkRecord) => {
          if (record.outgoing_doc?.doc_number) {
            return (
              <Tooltip title={record.outgoing_doc.subject}>
                <Text
                  ellipsis
                  style={{ maxWidth: 135, cursor: 'pointer', color: '#1677ff' }}
                  onClick={() => record.outgoing_doc?.id && onDocClick(record.outgoing_doc.id)}
                >
                  <FileTextOutlined style={{ marginRight: 4 }} />
                  {record.outgoing_doc.doc_number}
                </Text>
              </Tooltip>
            );
          }
          const doc = getEffectiveDoc(record);
          const dir = getDocDirection(record);
          if (doc?.doc_number && dir === 'outgoing') {
            return (
              <Tooltip title={doc.subject}>
                <Text
                  ellipsis
                  style={{ maxWidth: 135, cursor: 'pointer', color: '#1677ff' }}
                  onClick={() => doc.id && onDocClick(doc.id)}
                >
                  <FileTextOutlined style={{ marginRight: 4 }} />
                  {doc.doc_number}
                </Text>
              </Tooltip>
            );
          }
          return '-';
        },
      },
      ...(canEdit
        ? [
            {
              title: '操作',
              key: 'action',
              width: 80,
              fixed: 'right' as const,
              render: (_: unknown, record: WorkRecord) => (
                <Space size="small">
                  <Tooltip title="編輯">
                    <Button
                      type="link"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => onEdit(record)}
                    />
                  </Tooltip>
                  <Popconfirm
                    title="確定要刪除此紀錄嗎？"
                    onConfirm={() => onDelete(record.id)}
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
    [canEdit, onEdit, onDocClick, onDelete],
  );
}

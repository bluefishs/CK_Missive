/**
 * useWorkRecordColumns - 作業紀錄表格欄位 統一 Hook
 *
 * 合併 dispatch useWorkflowColumns 和 project 內聯 tableColumns，
 * 透過選項參數化控制顯示欄位。
 *
 * @version 1.0.0
 * @date 2026-03-04
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

import type { WorkRecord, WorkRecordStatus } from '../../../types/taoyuan';
import { getCategoryLabel, getCategoryColor, statusLabel, statusColor } from './workCategoryConstants';
import { getEffectiveDoc, getDocDirection } from './chainUtils';

const { Text } = Typography;

// ============================================================================
// Types
// ============================================================================

export interface UseWorkRecordColumnsOptions {
  canEdit: boolean;
  onEdit: (record: WorkRecord) => void;
  onDelete: (id: number) => void;
  /** 公文點擊回呼（有則可點擊導航，無則純顯示） */
  onDocClick?: (docId: number) => void;
  /** 顯示「派工單」欄位（專案總覽需要，派工單詳情不需要） */
  showDispatchColumn?: boolean;
  /** 顯示「期限」欄位 */
  showDeadlineColumn?: boolean;
  /** 顯示「覆文」欄位 */
  showOutgoingDocColumn?: boolean;
}

// ============================================================================
// 內部 render helpers
// ============================================================================

function renderDocCell(
  record: WorkRecord,
  direction: 'incoming' | 'outgoing',
  onDocClick?: (docId: number) => void,
): React.ReactNode {
  // 舊格式直接欄位
  const directDoc = direction === 'incoming' ? record.incoming_doc : record.outgoing_doc;
  if (directDoc?.doc_number) {
    return (
      <Tooltip title={directDoc.subject}>
        <Text
          ellipsis
          style={{
            maxWidth: 135,
            ...(onDocClick ? { cursor: 'pointer', color: '#1677ff' } : {}),
          }}
          onClick={() => onDocClick && directDoc.id && onDocClick(directDoc.id)}
        >
          <FileTextOutlined style={{ marginRight: 4 }} />
          {directDoc.doc_number}
        </Text>
      </Tooltip>
    );
  }

  // 新格式：document + direction 判斷
  const doc = getEffectiveDoc(record);
  const dir = getDocDirection(record);
  if (doc?.doc_number && dir === direction) {
    return (
      <Tooltip title={doc.subject}>
        <Text
          ellipsis
          style={{
            maxWidth: 135,
            ...(onDocClick ? { cursor: 'pointer', color: '#1677ff' } : {}),
          }}
          onClick={() => onDocClick && doc.id && onDocClick(doc.id)}
        >
          <FileTextOutlined style={{ marginRight: 4 }} />
          {doc.doc_number}
        </Text>
      </Tooltip>
    );
  }

  return '-';
}

// ============================================================================
// Hook
// ============================================================================

export function useWorkRecordColumns({
  canEdit,
  onEdit,
  onDelete,
  onDocClick,
  showDispatchColumn = false,
  showDeadlineColumn = false,
  showOutgoingDocColumn = false,
}: UseWorkRecordColumnsOptions): ColumnsType<WorkRecord> {
  return useMemo(() => {
    const columns: ColumnsType<WorkRecord> = [
      {
        title: '序號',
        dataIndex: 'sort_order',
        key: 'sort_order',
        width: 50,
        align: 'center' as const,
      },
    ];

    // 派工單欄位（專案總覽用）
    if (showDispatchColumn) {
      columns.push({
        title: '派工單',
        dataIndex: 'dispatch_subject',
        key: 'dispatch_subject',
        width: 150,
        ellipsis: true,
        render: (val: string) => val || '-',
      });
    }

    // 作業類別
    columns.push({
      title: '作業類別',
      key: 'category',
      width: 100,
      render: (_: unknown, record: WorkRecord) => (
        <Tag color={getCategoryColor(record)}>{getCategoryLabel(record)}</Tag>
      ),
    });

    // 說明（dispatch 版有 getEffectiveDoc fallback）
    columns.push({
      title: '說明',
      key: 'description',
      width: 220,
      ellipsis: { showTitle: false },
      render: (_: unknown, record: WorkRecord) => {
        const doc = getEffectiveDoc(record);
        const text = record.description || doc?.subject;
        if (!text) return '-';
        return (
          <Tooltip title={text} placement="topLeft">
            <span>{text}</span>
          </Tooltip>
        );
      },
    });

    // 紀錄日期
    columns.push({
      title: '紀錄日期',
      dataIndex: 'record_date',
      key: 'record_date',
      width: 100,
      render: (val: string) => (val ? dayjs(val).format('YYYY-MM-DD') : '-'),
    });

    // 期限（可選）
    if (showDeadlineColumn) {
      columns.push({
        title: '期限',
        dataIndex: 'deadline_date',
        key: 'deadline_date',
        width: 95,
        render: (val: string) => (val ? dayjs(val).format('YYYY-MM-DD') : '-'),
      });
    }

    // 狀態
    columns.push({
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: WorkRecordStatus) => (
        <Tag color={statusColor(status)}>{statusLabel(status)}</Tag>
      ),
    });

    // 來文
    columns.push({
      title: '來文',
      key: 'incoming_doc',
      width: 155,
      render: (_: unknown, record: WorkRecord) =>
        renderDocCell(record, 'incoming', onDocClick),
    });

    // 覆文（可選）
    if (showOutgoingDocColumn) {
      columns.push({
        title: '覆文',
        key: 'outgoing_doc',
        width: 155,
        render: (_: unknown, record: WorkRecord) =>
          renderDocCell(record, 'outgoing', onDocClick),
      });
    }

    // 操作欄
    if (canEdit) {
      columns.push({
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
      });
    }

    return columns;
  }, [canEdit, onEdit, onDelete, onDocClick, showDispatchColumn, showDeadlineColumn, showOutgoingDocColumn]);
}

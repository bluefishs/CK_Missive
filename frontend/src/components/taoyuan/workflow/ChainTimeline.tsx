/**
 * ChainTimeline - 鏈式時間軸元件
 *
 * 將作業歷程紀錄以鏈式方式呈現：
 * - 有 parent_record_id → 連接線
 * - 來文 藍色左框線，發文 綠色左框線
 * - 無公文 灰色虛線框 + "待關聯公文"
 *
 * @version 1.0.0
 * @date 2026-02-13
 */

import React, { useMemo } from 'react';
import {
  Tag,
  Typography,
  Button,
  Tooltip,
  Empty,
  Popconfirm,
  theme,
} from 'antd';
import {
  FileTextOutlined,
  SendOutlined,
  EditOutlined,
  DeleteOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import type { WorkRecord } from '../../../types/taoyuan';
import { buildChains, flattenChains, getEffectiveDoc, getDocDirection } from './chainUtils';
import type { ChainNode } from './chainUtils';
import { getCategoryLabel, getCategoryColor, getStatusLabel, getStatusColor } from './chainConstants';

const { Text } = Typography;

// ============================================================================
// Props
// ============================================================================

export interface ChainTimelineProps {
  records: WorkRecord[];
  onDocClick?: (docId: number) => void;
  onEditRecord?: (record: WorkRecord) => void;
  onDeleteRecord?: (recordId: number) => void;
  canEdit?: boolean;
}

// ============================================================================
// RecordCard - 單筆紀錄卡片
// ============================================================================

interface RecordCardProps {
  node: ChainNode;
  index: number;
  isLast: boolean;
  onDocClick?: (docId: number) => void;
  onEditRecord?: (record: WorkRecord) => void;
  onDeleteRecord?: (recordId: number) => void;
  canEdit?: boolean;
}

const RecordCardInner: React.FC<RecordCardProps> = ({
  node,
  index,
  isLast,
  onDocClick,
  onEditRecord,
  onDeleteRecord,
  canEdit,
}) => {
  const { token } = theme.useToken();
  const { record, depth } = node;
  const doc = getEffectiveDoc(record);
  const direction = getDocDirection(record);
  const hasDoc = !!doc;

  const borderColor = direction === 'outgoing' ? '#52c41a' : direction === 'incoming' ? '#1677ff' : token.colorBorderSecondary;
  const borderStyle = hasDoc ? 'solid' : 'dashed';
  const dateStr = doc?.doc_date ? dayjs(doc.doc_date).format('YYYY.MM.DD') : record.record_date ? dayjs(record.record_date).format('YYYY.MM.DD') : '';

  return (
    <div style={{ position: 'relative', paddingLeft: depth > 0 ? 24 : 0 }}>
      {/* 連接線 */}
      {depth > 0 && (
        <div
          style={{
            position: 'absolute',
            left: depth > 0 ? 12 : 0,
            top: -8,
            width: 2,
            height: 16,
            background: token.colorBorderSecondary,
          }}
        />
      )}

      {/* 卡片 */}
      <div
        style={{
          borderRadius: 6,
          border: `1px ${borderStyle} ${token.colorBorderSecondary}`,
          borderLeftWidth: 3,
          borderLeftColor: borderColor,
          borderLeftStyle: borderStyle,
          padding: '8px 12px',
          marginBottom: isLast ? 0 : 4,
          background: token.colorBgContainer,
        }}
      >
        {/* 第一行：序號 + 類別 + 狀態 + 操作 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            <Text strong style={{ fontSize: 12, color: token.colorTextSecondary }}>
              #{index + 1}
            </Text>
            <Tag color={getCategoryColor(record)} style={{ fontSize: 11, lineHeight: '18px', margin: 0 }}>
              {getCategoryLabel(record)}
            </Tag>
            <Tag color={getStatusColor(record.status)} style={{ fontSize: 11, lineHeight: '18px', margin: 0 }}>
              {getStatusLabel(record.status)}
            </Tag>
          </div>
          {canEdit && (
            <div style={{ display: 'flex', gap: 2, flexShrink: 0 }}>
              {onEditRecord && (
                <Tooltip title="編輯">
                  <Button type="text" size="small" icon={<EditOutlined />} onClick={() => onEditRecord(record)} aria-label="編輯" />
                </Tooltip>
              )}
              {onDeleteRecord && (
                <Popconfirm
                  title="確定刪除此紀錄？"
                  onConfirm={() => onDeleteRecord(record.id)}
                  okText="刪除"
                  cancelText="取消"
                >
                  <Tooltip title="刪除">
                    <Button type="text" size="small" danger icon={<DeleteOutlined />} aria-label="刪除" />
                  </Tooltip>
                </Popconfirm>
              )}
            </div>
          )}
        </div>

        {/* 第二行：公文資訊 */}
        {hasDoc ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
            {direction === 'outgoing' ? (
              <SendOutlined style={{ color: '#52c41a', fontSize: 12 }} />
            ) : (
              <FileTextOutlined style={{ color: '#1677ff', fontSize: 12 }} />
            )}
            {doc.doc_number ? (
              <Text
                style={{
                  fontSize: 12,
                  cursor: onDocClick && doc.id ? 'pointer' : 'default',
                  color: onDocClick && doc.id ? token.colorPrimary : undefined,
                }}
                onClick={() => doc.id && onDocClick?.(doc.id)}
              >
                {doc.doc_number}
              </Text>
            ) : (
              <Text type="secondary" style={{ fontSize: 12 }}>(無文號)</Text>
            )}
            {dateStr && (
              <Text type="secondary" style={{ fontSize: 11 }}>{dateStr}</Text>
            )}
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <LinkOutlined style={{ color: token.colorTextDisabled, fontSize: 12 }} />
            <Text type="secondary" style={{ fontSize: 12, fontStyle: 'italic' }}>
              待關聯公文
            </Text>
            {dateStr && (
              <Text type="secondary" style={{ fontSize: 11 }}>{dateStr}</Text>
            )}
          </div>
        )}

        {/* 第三行：主旨 / 描述 */}
        {(record.description || doc?.subject) && (
          <Text
            type="secondary"
            ellipsis={{ tooltip: record.description || doc?.subject }}
            style={{ display: 'block', fontSize: 12, marginTop: 2 }}
          >
            {record.description || doc?.subject}
          </Text>
        )}

        {/* 第四行：期限 */}
        {record.deadline_date && (
          <Text type="secondary" style={{ fontSize: 11, marginTop: 2, display: 'block' }}>
            期限: {dayjs(record.deadline_date).format('YYYY.MM.DD')}
          </Text>
        )}
      </div>

      {/* 節點間連接線 */}
      {!isLast && (
        <div
          style={{
            width: 2,
            height: 8,
            background: token.colorBorderSecondary,
            marginLeft: 12,
          }}
        />
      )}
    </div>
  );
};

const RecordCard = React.memo(RecordCardInner);

// ============================================================================
// ChainTimeline
// ============================================================================

const ChainTimelineInner: React.FC<ChainTimelineProps> = ({
  records,
  onDocClick,
  onEditRecord,
  onDeleteRecord,
  canEdit,
}) => {
  const flatNodes = useMemo(() => {
    const chains = buildChains(records);
    return flattenChains(chains);
  }, [records]);

  if (flatNodes.length === 0) {
    return (
      <Empty
        description="尚無作業紀錄"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        style={{ padding: '24px 0' }}
      />
    );
  }

  return (
    <div style={{ padding: '4px 0' }}>
      {flatNodes.map((node, i) => (
        <RecordCard
          key={node.record.id}
          node={node}
          index={i}
          isLast={i === flatNodes.length - 1}
          onDocClick={onDocClick}
          onEditRecord={onEditRecord}
          onDeleteRecord={onDeleteRecord}
          canEdit={canEdit}
        />
      ))}
    </div>
  );
};

export const ChainTimeline = React.memo(ChainTimelineInner);

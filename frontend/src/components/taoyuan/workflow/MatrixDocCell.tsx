/**
 * MatrixDocCell - 單筆公文儲存格內容 + DocEntry 向下相容元件
 *
 * 從 CorrespondenceBody.tsx 提取，負責：
 * - 單筆公文的顯示（文號、日期、主旨、類別、狀態）
 * - DocEntry 向下相容介面（供 CorrespondenceMatrix 使用）
 *
 * @version 1.0.0
 */

import React from 'react';
import {
  Badge,
  Tag,
  Typography,
  Tooltip,
  Button,
  theme,
} from 'antd';
import {
  FileTextOutlined,
  SendOutlined,
  EditOutlined,
  PlusOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import type { WorkRecord, DocBrief } from '../../../types/taoyuan';
import type { DispatchDocumentLink } from '../../../types/api';
import type { MatrixDocItem } from './chainUtils';
import {
  statusLabel,
  statusColor,
  getCategoryLabel,
  getCategoryColor,
} from './workCategoryConstants';

const { Text } = Typography;

// ============================================================================
// MatrixDocCell
// ============================================================================

export interface MatrixDocCellProps {
  item?: MatrixDocItem;
  direction: 'incoming' | 'outgoing';
  onDocClick?: (docId: number) => void;
  onEditRecord?: (record: WorkRecord) => void;
  onQuickCreateRecord?: (doc: DispatchDocumentLink) => void;
  canEdit?: boolean;
}

const MatrixDocCellInner: React.FC<MatrixDocCellProps> = ({
  item,
  direction,
  onDocClick,
  onEditRecord,
  onQuickCreateRecord,
  canEdit,
}) => {
  const { token } = theme.useToken();
  const isIncoming = direction === 'incoming';

  if (!item) {
    return (
      <Text type="secondary" style={{ fontSize: 12, fontStyle: 'italic' }}>
        {isIncoming ? '(無對應來文)' : '(尚無覆文)'}
      </Text>
    );
  }

  const dateStr = item.docDate ? dayjs(item.docDate).format('YYYY.MM.DD') : '';
  const icon = isIncoming
    ? <FileTextOutlined style={{ color: token.colorPrimary, fontSize: 12 }} />
    : <SendOutlined style={{ color: token.colorSuccess, fontSize: 12 }} />;

  return (
    <div>
      {/* 第一行：icon + 文號 + 日期 + 未指派標記 + 操作 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        {icon}
        {item.docNumber ? (
          <Text
            style={{
              fontSize: 12,
              fontWeight: 500,
              cursor: onDocClick ? 'pointer' : 'default',
              color: onDocClick ? token.colorPrimary : undefined,
            }}
            onClick={() => onDocClick?.(item.docId)}
          >
            {item.docNumber}
          </Text>
        ) : (
          <Text type="secondary" style={{ fontSize: 12 }}>(無文號)</Text>
        )}
        {dateStr && (
          <Text type="secondary" style={{ fontSize: 11 }}>{dateStr}</Text>
        )}
        {item.isUnassigned && item.linkedDoc?.linked_dispatch_count && item.linkedDoc.linked_dispatch_count > 1 ? (
          <Tooltip title={`已關聯 ${item.linkedDoc.linked_dispatch_count} 個派工單（含本單）`}>
            <Badge
              count={item.linkedDoc.linked_dispatch_count}
              size="small"
              style={{ backgroundColor: token.colorTextQuaternary, fontSize: 10 }}
            />
          </Tooltip>
        ) : item.isUnassigned ? (
          <Tooltip title="未指派到作業紀錄">
            <ExclamationCircleOutlined style={{ color: token.colorWarning, fontSize: 11 }} />
          </Tooltip>
        ) : null}
        <span style={{ flex: 1 }} />
        {canEdit && item.record && onEditRecord && (
          <Tooltip title="編輯紀錄">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined style={{ fontSize: 12 }} />}
              onClick={() => onEditRecord(item.record!)}
              style={{ width: 22, height: 22, minWidth: 22 }}
            />
          </Tooltip>
        )}
        {canEdit && item.isUnassigned && item.linkedDoc && onQuickCreateRecord && (
          <Tooltip title="新增作業紀錄">
            <Button
              type="text"
              size="small"
              icon={<PlusOutlined style={{ fontSize: 12 }} />}
              onClick={() => onQuickCreateRecord(item.linkedDoc!)}
              style={{ width: 22, height: 22, minWidth: 22 }}
            />
          </Tooltip>
        )}
      </div>

      {/* 第二行：主旨 */}
      {item.subject && (
        <Text
          type="secondary"
          ellipsis={{ tooltip: item.subject }}
          style={{ display: 'block', fontSize: 11, marginTop: 1, lineHeight: '16px', wordBreak: 'break-all' }}
        >
          {item.subject}
        </Text>
      )}

      {/* 第三行：類別+狀態 Tag（僅已指派） */}
      {item.record && (
        <div style={{ marginTop: 2 }}>
          <Tag
            color={getCategoryColor(item.record)}
            style={{ fontSize: 10, lineHeight: '16px', marginBottom: 0 }}
          >
            {getCategoryLabel(item.record)}
          </Tag>
          <Tag
            color={statusColor(item.record.status)}
            style={{ fontSize: 10, lineHeight: '16px', marginBottom: 0 }}
          >
            {statusLabel(item.record.status)}
          </Tag>
        </div>
      )}
    </div>
  );
};

export const MatrixDocCell = React.memo(MatrixDocCellInner);

// ============================================================================
// DocEntry - 保留舊 API 供 CorrespondenceMatrix（工程總覽）使用
// ============================================================================

export interface DocEntryProps {
  doc: DocBrief;
  record: WorkRecord;
  direction: 'incoming' | 'outgoing';
  onDocClick?: (docId: number) => void;
  onEditRecord?: (record: WorkRecord) => void;
  canEdit?: boolean;
}

const DocEntryInner: React.FC<DocEntryProps> = (props) => {
  const item: MatrixDocItem = {
    docId: props.doc.id,
    docNumber: props.doc.doc_number,
    docDate: props.doc.doc_date,
    subject: props.record.description || props.doc.subject,
    record: props.record,
    isUnassigned: false,
  };
  return (
    <div style={{ padding: '6px 8px', borderBottom: '1px solid #f0f0f0' }}>
      <MatrixDocCell
        item={item}
        direction={props.direction}
        onDocClick={props.onDocClick}
        onEditRecord={props.onEditRecord}
        canEdit={props.canEdit}
      />
    </div>
  );
};

export const DocEntry = React.memo(DocEntryInner);

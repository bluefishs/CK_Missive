/**
 * CorrespondenceBody - 公文對照矩陣（配對行式）
 *
 * 以 HTML table 確保左右儲存格等高對齊：
 * - 左欄：機關來文
 * - 右欄：公司覆文
 * - 行號 + 箭頭指示對應關係
 *
 * @version 2.1.0 - table 排版修正 + 對應邏輯修正
 * @date 2026-02-25
 */

import React, { useMemo, useState } from 'react';
import {
  Tag,
  Typography,
  Empty,
  Badge,
  Tooltip,
  Button,
  theme,
} from 'antd';
import {
  FileTextOutlined,
  SendOutlined,
  EditOutlined,
  PlusOutlined,
  ArrowRightOutlined,
  DownOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import type { WorkRecord, DocBrief } from '../../../types/taoyuan';
import type { DispatchDocumentLink } from '../../../types/api';
import type { CorrespondenceMatrixRow, MatrixDocItem } from './chainUtils';
import {
  statusLabel,
  statusColor,
} from './useProjectWorkData';
import {
  getCategoryLabel,
  getCategoryColor,
} from './chainConstants';

const { Text } = Typography;

// ============================================================================
// MatrixDocCell - 單筆公文儲存格內容
// ============================================================================

interface MatrixDocCellProps {
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
        {item.isUnassigned && (
          <Tooltip title="未指派到作業紀錄">
            <ExclamationCircleOutlined style={{ color: token.colorWarning, fontSize: 11 }} />
          </Tooltip>
        )}
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

const MatrixDocCell = React.memo(MatrixDocCellInner);

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

// ============================================================================
// MatrixTable - table 排版核心
// ============================================================================

interface MatrixTableProps {
  rows: CorrespondenceMatrixRow[];
  totalIncoming: number;
  totalOutgoing: number;
  onDocClick?: (docId: number) => void;
  onEditRecord?: (record: WorkRecord) => void;
  onQuickCreateRecord?: (doc: DispatchDocumentLink) => void;
  canEdit?: boolean;
  defaultVisibleCount: number;
}

const MatrixTableInner: React.FC<MatrixTableProps> = ({
  rows,
  totalIncoming,
  totalOutgoing,
  onDocClick,
  onEditRecord,
  onQuickCreateRecord,
  canEdit,
  defaultVisibleCount,
}) => {
  const { token } = theme.useToken();
  const [expanded, setExpanded] = useState(false);

  const limit = defaultVisibleCount > 0 ? defaultVisibleCount : Infinity;
  const visibleRows = expanded ? rows : rows.slice(0, limit);
  const hasMore = rows.length > limit;

  // 共用 td 樣式
  const cellPad = '6px 10px';
  const borderColor = token.colorBorderSecondary;

  return (
    <div
      style={{
        borderRadius: 6,
        border: `1px solid ${borderColor}`,
        overflow: 'hidden',
      }}
    >
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          tableLayout: 'fixed',
        }}
      >
        <colgroup>
          <col style={{ width: 28 }} />
          <col />
          <col style={{ width: 24 }} />
          <col />
        </colgroup>

        {/* 表頭 */}
        <thead>
          <tr>
            <th
              style={{
                padding: '5px 0',
                background: token.colorBgLayout,
                borderBottom: `1px solid ${borderColor}`,
                borderRight: `1px solid ${borderColor}`,
                fontSize: 11,
                color: token.colorTextSecondary,
                textAlign: 'center',
              }}
            >
              #
            </th>
            <th
              style={{
                padding: '5px 10px',
                background: token.colorPrimaryBg,
                borderBottom: `1px solid ${borderColor}`,
                borderRight: `1px solid ${borderColor}`,
                textAlign: 'left',
              }}
            >
              <span style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text strong style={{ fontSize: 12, color: token.colorPrimary }}>
                  <FileTextOutlined /> 機關來文
                </Text>
                <Badge count={totalIncoming} style={{ backgroundColor: token.colorPrimary }} size="small" />
              </span>
            </th>
            <th
              style={{
                padding: 0,
                background: token.colorBgLayout,
                borderBottom: `1px solid ${borderColor}`,
                borderRight: `1px solid ${borderColor}`,
                textAlign: 'center',
                fontSize: 10,
                color: token.colorTextSecondary,
              }}
            >
              <ArrowRightOutlined />
            </th>
            <th
              style={{
                padding: '5px 10px',
                background: token.colorSuccessBg,
                borderBottom: `1px solid ${borderColor}`,
                textAlign: 'left',
              }}
            >
              <span style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text strong style={{ fontSize: 12, color: token.colorSuccess }}>
                  <SendOutlined /> 公司覆文
                </Text>
                <Badge count={totalOutgoing} style={{ backgroundColor: token.colorSuccess }} size="small" />
              </span>
            </th>
          </tr>
        </thead>

        {/* 資料行 */}
        <tbody>
          {visibleRows.map((row, i) => {
            const hasBoth = !!row.incoming && !!row.outgoing;
            const rowBg =
              row.incoming?.isUnassigned || row.outgoing?.isUnassigned
                ? token.colorBgTextHover
                : i % 2 === 1
                  ? token.colorBgLayout
                  : undefined;

            return (
              <tr key={`${row.incoming?.docId ?? 'x'}-${row.outgoing?.docId ?? 'x'}-${i}`} style={{ background: rowBg }}>
                {/* 行號 */}
                <td
                  style={{
                    padding: '4px 0',
                    borderRight: `1px solid ${borderColor}`,
                    borderBottom: `1px solid ${borderColor}`,
                    textAlign: 'center',
                    verticalAlign: 'top',
                  }}
                >
                  <Text type="secondary" style={{ fontSize: 11 }}>{i + 1}</Text>
                </td>

                {/* 來文 */}
                <td
                  style={{
                    padding: cellPad,
                    borderRight: `1px solid ${borderColor}`,
                    borderBottom: `1px solid ${borderColor}`,
                    verticalAlign: 'top',
                    overflow: 'hidden',
                  }}
                >
                  <MatrixDocCell
                    item={row.incoming}
                    direction="incoming"
                    onDocClick={onDocClick}
                    onEditRecord={onEditRecord}
                    onQuickCreateRecord={onQuickCreateRecord}
                    canEdit={canEdit}
                  />
                </td>

                {/* 箭頭 */}
                <td
                  style={{
                    padding: 0,
                    borderRight: `1px solid ${borderColor}`,
                    borderBottom: `1px solid ${borderColor}`,
                    textAlign: 'center',
                    verticalAlign: 'middle',
                    color: token.colorTextSecondary,
                    fontSize: 10,
                  }}
                >
                  {hasBoth ? <ArrowRightOutlined /> : '—'}
                </td>

                {/* 覆文 */}
                <td
                  style={{
                    padding: cellPad,
                    borderBottom: `1px solid ${borderColor}`,
                    verticalAlign: 'top',
                    overflow: 'hidden',
                  }}
                >
                  <MatrixDocCell
                    item={row.outgoing}
                    direction="outgoing"
                    onDocClick={onDocClick}
                    onEditRecord={onEditRecord}
                    onQuickCreateRecord={onQuickCreateRecord}
                    canEdit={canEdit}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* 展開更多 */}
      {hasMore && !expanded && (
        <div style={{ padding: '6px', textAlign: 'center', borderTop: `1px solid ${borderColor}` }}>
          <Button type="link" size="small" icon={<DownOutlined />} onClick={() => setExpanded(true)}>
            展開全部 ({rows.length} 列)
          </Button>
        </div>
      )}
    </div>
  );
};

const MatrixTable = React.memo(MatrixTableInner);

// ============================================================================
// CorrespondenceBody - 主元件
// ============================================================================

export interface CorrespondenceBodyData {
  incomingDocs: { record: WorkRecord; doc: DocBrief }[];
  outgoingDocs: { record: WorkRecord; doc: DocBrief }[];
}

export interface CorrespondenceBodyProps {
  /** 傳統分組資料（向下相容，CorrespondenceMatrix 使用） */
  data: CorrespondenceBodyData;
  /** 矩陣配對行（優先使用，派工單公文對照 Tab 傳入） */
  matrixRows?: CorrespondenceMatrixRow[];
  onDocClick?: (docId: number) => void;
  onEditRecord?: (record: WorkRecord) => void;
  onQuickCreateRecord?: (doc: DispatchDocumentLink) => void;
  canEdit?: boolean;
  /** 預設顯示上限，0 = 不限制 */
  defaultVisibleCount?: number;
}

const DEFAULT_VISIBLE_COUNT = 15;

const CorrespondenceBodyInner: React.FC<CorrespondenceBodyProps> = ({
  data,
  matrixRows,
  onDocClick,
  onEditRecord,
  onQuickCreateRecord,
  canEdit,
  defaultVisibleCount = DEFAULT_VISIBLE_COUNT,
}) => {
  // ---- 矩陣模式（優先） ----
  if (matrixRows) {
    if (matrixRows.length === 0) {
      return (
        <Empty
          description="尚無關聯公文紀錄"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          style={{ padding: '16px 0' }}
        />
      );
    }
    const totalIn = matrixRows.filter((r) => r.incoming).length;
    const totalOut = matrixRows.filter((r) => r.outgoing).length;

    return (
      <MatrixTable
        rows={matrixRows}
        totalIncoming={totalIn}
        totalOutgoing={totalOut}
        onDocClick={onDocClick}
        onEditRecord={onEditRecord}
        onQuickCreateRecord={onQuickCreateRecord}
        canEdit={canEdit}
        defaultVisibleCount={defaultVisibleCount}
      />
    );
  }

  // ---- 傳統模式（向下相容 CorrespondenceMatrix 工程總覽） ----
  const { incomingDocs, outgoingDocs } = data;

  if (incomingDocs.length === 0 && outgoingDocs.length === 0) {
    return (
      <Empty
        description="尚無關聯公文紀錄"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        style={{ padding: '16px 0' }}
      />
    );
  }

  // 傳統分組轉矩陣行（index 配對，工程總覽用）
  const legacyRows: CorrespondenceMatrixRow[] = useMemo(() => {
    const maxLen = Math.max(incomingDocs.length, outgoingDocs.length);
    const result: CorrespondenceMatrixRow[] = [];
    for (let i = 0; i < maxLen; i++) {
      const inDoc = incomingDocs[i];
      const outDoc = outgoingDocs[i];
      result.push({
        incoming: inDoc
          ? { docId: inDoc.doc.id, docNumber: inDoc.doc.doc_number, docDate: inDoc.doc.doc_date, subject: inDoc.record.description || inDoc.doc.subject, record: inDoc.record, isUnassigned: false }
          : undefined,
        outgoing: outDoc
          ? { docId: outDoc.doc.id, docNumber: outDoc.doc.doc_number, docDate: outDoc.doc.doc_date, subject: outDoc.record.description || outDoc.doc.subject, record: outDoc.record, isUnassigned: false }
          : undefined,
      });
    }
    return result;
  }, [incomingDocs, outgoingDocs]);

  return (
    <MatrixTable
      rows={legacyRows}
      totalIncoming={incomingDocs.length}
      totalOutgoing={outgoingDocs.length}
      onDocClick={onDocClick}
      onEditRecord={onEditRecord}
      canEdit={canEdit}
      defaultVisibleCount={defaultVisibleCount}
    />
  );
};

export const CorrespondenceBody = React.memo(CorrespondenceBodyInner);

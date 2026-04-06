/**
 * MatrixTable - 公文對照矩陣 table 排版核心
 *
 * 從 CorrespondenceBody.tsx 提取，負責：
 * - HTML table 排版確保左右儲存格等高對齊
 * - 行號 + 箭頭指示對應關係
 * - 信心度顯示與確認配對操作
 * - 展開/收合控制
 *
 * @version 1.0.0
 */

import React, { useState } from 'react';
import {
  Tag,
  Typography,
  Tooltip,
  Button,
  theme,
} from 'antd';
import {
  FileTextOutlined,
  SendOutlined,
  ArrowRightOutlined,
  DownOutlined,
  CheckOutlined,
  CheckCircleFilled,
} from '@ant-design/icons';
import { Badge } from 'antd';

import type { WorkRecord } from '../../../types/taoyuan';
import type { DispatchDocumentLink } from '../../../types/api';
import type { CorrespondenceMatrixRow, MatchConfidence } from './chainUtils';
import { MatrixDocCell } from './MatrixDocCell';

const { Text } = Typography;

// ============================================================================
// 信心度工具
// ============================================================================

// eslint-disable-next-line react-refresh/only-export-components
export function confidenceTooltip(c?: MatchConfidence, sharedEntities?: string[]): string {
  let base: string;
  switch (c) {
    case 'confirmed': base = '已確認配對（作業紀錄鏈式關聯）'; break;
    case 'high': base = '高信心度（主旨關鍵字匹配）'; break;
    case 'medium': base = '中信心度（日期鄰近 30 天內）'; break;
    case 'low': base = '低信心度（未配對）'; break;
    default: base = '配對';
  }
  if (sharedEntities && sharedEntities.length > 0) {
    base += `\n共享實體: ${sharedEntities.slice(0, 5).join('、')}`;
    if (sharedEntities.length > 5) base += `...等 ${sharedEntities.length} 個`;
  }
  return base;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any, react-refresh/only-export-components
export function confidenceColor(c: MatchConfidence | undefined, token: any): string {
  switch (c) {
    case 'confirmed': return token.colorSuccess;
    case 'high': return token.colorPrimary;
    case 'medium': return token.colorWarning;
    default: return token.colorTextSecondary;
  }
}

// ============================================================================
// MatrixTable
// ============================================================================

export interface MatrixTableProps {
  rows: CorrespondenceMatrixRow[];
  totalIncoming: number;
  totalOutgoing: number;
  onDocClick?: (docId: number) => void;
  onEditRecord?: (record: WorkRecord) => void;
  onQuickCreateRecord?: (doc: DispatchDocumentLink) => void;
  onConfirmPair?: (incomingDocId: number, outgoingDocId: number) => void;
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
  onConfirmPair,
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
          {(() => {
            // Pre-compute group spans for rowSpan rendering
            const groupSpans = new Map<number, number>();
            visibleRows.forEach((row) => {
              if (row.groupId !== undefined) {
                groupSpans.set(row.groupId, (groupSpans.get(row.groupId) || 0) + 1);
              }
            });
            const renderedGroupHeaders = new Set<number>();
            // Track logical row number (groups share one number)
            let logicalRowNum = 0;
            const rowNumbers: number[] = [];
            visibleRows.forEach((row) => {
              if (row.groupId !== undefined && groupSpans.has(row.groupId)) {
                if (!renderedGroupHeaders.has(row.groupId)) {
                  logicalRowNum++;
                  renderedGroupHeaders.add(row.groupId);
                }
              } else {
                logicalRowNum++;
              }
              rowNumbers.push(logicalRowNum);
            });
            // Reset for actual render pass
            renderedGroupHeaders.clear();

            return visibleRows.map((row, i) => {
              const isGrouped = row.groupId !== undefined && (groupSpans.get(row.groupId) || 0) > 1;
              const isGroupHeader = isGrouped && !renderedGroupHeaders.has(row.groupId!);
              const span = isGrouped ? groupSpans.get(row.groupId!) || 1 : 1;
              if (isGroupHeader) renderedGroupHeaders.add(row.groupId!);
              const isGroupMember = isGrouped && !isGroupHeader;

              // For grouped rows, determine hasBoth based on group having incoming + this row's outgoing
              const hasBoth = isGrouped
                ? !!row.outgoing // Group always has an incoming (on the header)
                : !!row.incoming && !!row.outgoing;

              const rowBg =
                row.incoming?.isUnassigned || row.outgoing?.isUnassigned
                  ? token.colorBgTextHover
                  : i % 2 === 1
                    ? token.colorBgLayout
                    : undefined;

              return (
                <tr key={`${row.incoming?.docId ?? 'x'}-${row.outgoing?.docId ?? 'x'}-${i}`} style={{ background: rowBg }}>
                  {/* 行號 — rowSpan for group header, skip for group members */}
                  {!isGroupMember && (
                    <td
                      rowSpan={isGroupHeader ? span : 1}
                      style={{
                        padding: '4px 0',
                        borderRight: `1px solid ${borderColor}`,
                        borderBottom: `1px solid ${borderColor}`,
                        textAlign: 'center',
                        verticalAlign: 'top',
                      }}
                    >
                      <Text type="secondary" style={{ fontSize: 11 }}>{rowNumbers[i]}</Text>
                    </td>
                  )}

                  {/* 來文 — rowSpan for group header, skip for group members */}
                  {!isGroupMember && (
                    <td
                      rowSpan={isGroupHeader ? span : 1}
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
                      {isGroupHeader && span > 1 && (
                        <Tag color="blue" style={{ fontSize: 11, marginTop: 4 }}>
                          1 &rarr; {span}
                        </Tag>
                      )}
                    </td>
                  )}

                  {/* 箭頭 — rowSpan for group header, skip for group members */}
                  {!isGroupMember && (
                    <td
                      rowSpan={isGroupHeader ? span : 1}
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
                      {hasBoth ? (
                        <Tooltip title={confidenceTooltip(row.confidence, row.sharedEntities)}>
                          <span style={{ color: confidenceColor(row.confidence, token), display: 'inline-flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                            <ArrowRightOutlined />
                            {row.confidence === 'confirmed' && !row.incoming?.isUnassigned && !row.outgoing?.isUnassigned ? (
                              <CheckCircleFilled style={{ fontSize: 10, color: token.colorSuccess }} />
                            ) : (row.confidence === 'high' || row.confidence === 'medium' || row.confidence === 'confirmed') && canEdit && onConfirmPair && row.incoming && row.outgoing ? (
                              <Button
                                type="text"
                                size="small"
                                icon={<CheckOutlined style={{ fontSize: 10 }} />}
                                onClick={() => onConfirmPair(row.incoming!.docId, row.outgoing!.docId)}
                                style={{ width: 18, height: 18, minWidth: 18, padding: 0, color: token.colorSuccess }}
                              />
                            ) : null}
                          </span>
                        </Tooltip>
                      ) : row.docTypeLabel ? (
                        <Tooltip title={`業務類型: ${row.docTypeLabel}`}>
                          <Tag style={{ fontSize: 9, padding: '0 3px', margin: 0, lineHeight: '16px' }} color="default">
                            {row.docTypeLabel.slice(0, 2)}
                          </Tag>
                        </Tooltip>
                      ) : '—'}
                    </td>
                  )}

                  {/* 覆文 — always individual (one per row) */}
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
            });
          })()}
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

export const MatrixTable = React.memo(MatrixTableInner);

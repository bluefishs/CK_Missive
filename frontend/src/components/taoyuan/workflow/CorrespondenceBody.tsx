/**
 * CorrespondenceBody - 公文對照矩陣（配對行式）
 *
 * 以 HTML table 確保左右儲存格等高對齊：
 * - 左欄：機關來文
 * - 右欄：公司覆文
 * - 行號 + 箭頭指示對應關係
 *
 * 子元件：
 * - MatrixDocCell.tsx - 單筆公文儲存格 + DocEntry 向下相容
 * - MatrixTable.tsx   - table 排版核心 + 信心度工具
 *
 * @version 3.0.0 - 拆分為 3 個檔案
 * @date 2026-03-18
 */

import React, { useMemo } from 'react';
import { Empty } from 'antd';
import { Typography } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';

import type { WorkRecord, DocBrief } from '../../../types/taoyuan';
import type { DispatchDocumentLink } from '../../../types/api';
import type { CorrespondenceMatrixRow } from './chainUtils';
import { MatrixTable } from './MatrixTable';

// Re-export sub-components for backward compatibility
export { DocEntry } from './MatrixDocCell';
export type { DocEntryProps } from './MatrixDocCell';

const { Text } = Typography;

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
  onConfirmPair?: (incomingDocId: number, outgoingDocId: number) => void;
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
  onConfirmPair,
  canEdit,
  defaultVisibleCount = DEFAULT_VISIBLE_COUNT,
}) => {
  // 傳統分組轉矩陣行（index 配對，工程總覽用） — must be before early returns
  const incomingDocs = useMemo(() => matrixRows ? [] : (data?.incomingDocs ?? []), [matrixRows, data?.incomingDocs]);
  const outgoingDocs = useMemo(() => matrixRows ? [] : (data?.outgoingDocs ?? []), [matrixRows, data?.outgoingDocs]);
  const legacyRows: CorrespondenceMatrixRow[] = useMemo(() => {
    if (matrixRows) return [];
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
  }, [matrixRows, incomingDocs, outgoingDocs]);

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

    // 分離配對行（confirmed/high）和未配對行（low）
    const pairedRows = matrixRows.filter((r) => r.confidence === 'confirmed' || r.confidence === 'high');
    const unpairedRows = matrixRows.filter((r) => r.confidence !== 'confirmed' && r.confidence !== 'high');
    const totalIn = matrixRows.filter((r) => r.incoming).length;
    const totalOut = matrixRows.filter((r) => r.outgoing).length;

    return (
      <div>
        {/* 配對矩陣（有明確對應的公文） */}
        {pairedRows.length > 0 && (
          <MatrixTable
            rows={pairedRows}
            totalIncoming={totalIn}
            totalOutgoing={totalOut}
            onDocClick={onDocClick}
            onEditRecord={onEditRecord}
            onQuickCreateRecord={onQuickCreateRecord}
            onConfirmPair={onConfirmPair}
            canEdit={canEdit}
            defaultVisibleCount={defaultVisibleCount}
          />
        )}

        {/* 未配對公文（按業務類型分組的時間線） */}
        {unpairedRows.length > 0 && (
          <div style={{ marginTop: pairedRows.length > 0 ? 12 : 0 }}>
            {pairedRows.length > 0 && (
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
                <ExclamationCircleOutlined style={{ marginRight: 4 }} />
                其他關聯公文（未配對，按類型分組）
              </Text>
            )}
            <MatrixTable
              rows={unpairedRows}
              totalIncoming={unpairedRows.filter((r) => r.incoming).length}
              totalOutgoing={unpairedRows.filter((r) => r.outgoing).length}
              onDocClick={onDocClick}
              onEditRecord={onEditRecord}
              onQuickCreateRecord={onQuickCreateRecord}
              canEdit={canEdit}
              defaultVisibleCount={pairedRows.length > 0 ? 5 : defaultVisibleCount}
            />
          </div>
        )}

        {/* 無任何配對時的空狀態 */}
        {pairedRows.length === 0 && unpairedRows.length === 0 && (
          <Empty description="尚無關聯公文紀錄" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ padding: '16px 0' }} />
        )}
      </div>
    );
  }

  // ---- 傳統模式（向下相容 CorrespondenceMatrix 工程總覽） ----
  if (incomingDocs.length === 0 && outgoingDocs.length === 0) {
    return (
      <Empty
        description="尚無關聯公文紀錄"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        style={{ padding: '16px 0' }}
      />
    );
  }

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

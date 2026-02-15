/**
 * useDispatchWorkData - 派工單作業歷程 + 公文對照 統一資料 Hook
 *
 * 整合公文關聯與作業歷程：
 * - 作業紀錄查詢 + 公文對照分組
 * - 未指派公文偵測（已關聯但未對應作業紀錄的公文）
 * - 迷你統計（紀錄數、完成、來文、發文、未指派）
 *
 * @version 2.0.0 - 整合公文關聯
 * @date 2026-02-13
 */

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import { workflowApi } from '../../../api/taoyuan';
import type {
  WorkRecord,
  DocBrief,
} from '../../../types/taoyuan';
import type { DispatchDocumentLink, LinkType } from '../../../types/api';
import type { CorrespondenceBodyData } from './CorrespondenceBody';
import { getDocDirection, isOutgoingDocNumber, buildDocPairs } from './chainUtils';
import { getCategoryLabel } from './chainConstants';

// ============================================================================
// detectLinkType - 根據公文字號自動判斷關聯類型
// ============================================================================

/**
 * 根據公文字號自動判斷關聯類型
 *
 * 分類規則：
 * - 「乾坤」開頭 (乾坤測字、乾坤估字等) -> 乾坤發文 (company_outgoing)
 * - 「桃工」、「府工」等開頭 -> 機關來函 (agency_incoming)
 * - 其他政府機關字號 -> 機關來函 (agency_incoming)
 * - 無法識別 -> 預設為機關來函 (agency_incoming)
 */
export const detectLinkType = (docNumber?: string | null): LinkType => {
  if (!docNumber) return 'agency_incoming';

  if (isOutgoingDocNumber(docNumber)) {
    return 'company_outgoing';
  }

  return 'agency_incoming';
};

// ============================================================================
// Types
// ============================================================================

export interface DispatchWorkStats {
  total: number;
  completed: number;
  inProgress: number;
  overdue: number;
  onHold: number;
  incomingDocs: number;
  outgoingDocs: number;
  linkedDocCount: number;
  unassignedDocCount: number;
  currentStage: string;
}

export interface UnassignedDocsData {
  incoming: DispatchDocumentLink[];
  outgoing: DispatchDocumentLink[];
}

// ============================================================================
// Hook
// ============================================================================

interface UseDispatchWorkDataParams {
  dispatchOrderId: number;
  linkedDocuments?: DispatchDocumentLink[];
}

export function useDispatchWorkData({
  dispatchOrderId,
  linkedDocuments = [],
}: UseDispatchWorkDataParams) {
  const {
    data: workRecordData,
    isLoading,
  } = useQuery({
    queryKey: ['dispatch-work-records', dispatchOrderId],
    queryFn: () => workflowApi.listByDispatchOrder(dispatchOrderId),
    enabled: dispatchOrderId > 0,
  });

  const records = useMemo(
    () => workRecordData?.items ?? [],
    [workRecordData?.items],
  );

  // 已被作業紀錄引用的 document_id 集合（新舊格式都支援）
  const assignedDocIds = useMemo(() => {
    const ids = new Set<number>();
    for (const r of records) {
      if (r.document_id) ids.add(r.document_id);
      if (r.incoming_doc_id) ids.add(r.incoming_doc_id);
      if (r.outgoing_doc_id) ids.add(r.outgoing_doc_id);
    }
    return ids;
  }, [records]);

  // 未指派公文：已關聯到派工單但未被任何作業紀錄引用
  const unassignedDocs = useMemo<UnassignedDocsData>(() => {
    const incoming: DispatchDocumentLink[] = [];
    const outgoing: DispatchDocumentLink[] = [];

    for (const doc of linkedDocuments) {
      if (!doc.document_id) continue;
      if (!assignedDocIds.has(doc.document_id)) {
        const type = doc.link_type || detectLinkType(doc.doc_number);
        if (type === 'company_outgoing') {
          outgoing.push(doc);
        } else {
          incoming.push(doc);
        }
      }
    }

    // 按日期排序（最新在前）
    const sortByDate = (a: DispatchDocumentLink, b: DispatchDocumentLink) => {
      if (!a.doc_date && !b.doc_date) return 0;
      if (!a.doc_date) return 1;
      if (!b.doc_date) return -1;
      return new Date(b.doc_date).getTime() - new Date(a.doc_date).getTime();
    };
    incoming.sort(sortByDate);
    outgoing.sort(sortByDate);

    return { incoming, outgoing };
  }, [linkedDocuments, assignedDocIds]);

  // 統計
  const stats = useMemo<DispatchWorkStats>(() => {
    const total = records.length;
    const completed = records.filter((r) => r.status === 'completed').length;
    const inProgress = records.filter((r) => r.status === 'in_progress').length;
    const overdue = records.filter((r) => r.status === 'overdue').length;
    const onHold = records.filter((r) => r.status === 'on_hold').length;
    // 統計來文/發文數（新舊格式兼容）
    const incomingIds = new Set<number>();
    const outgoingIds = new Set<number>();
    for (const r of records) {
      if (r.incoming_doc_id) incomingIds.add(r.incoming_doc_id);
      if (r.outgoing_doc_id) outgoingIds.add(r.outgoing_doc_id);
      if (r.document_id) {
        const dir = getDocDirection(r);
        if (dir === 'outgoing') outgoingIds.add(r.document_id);
        else if (dir === 'incoming') incomingIds.add(r.document_id);
      }
    }
    const incomingDocs = incomingIds.size;
    const outgoingDocs = outgoingIds.size;

    const linkedDocCount = linkedDocuments.length;
    const unassignedDocCount = unassignedDocs.incoming.length + unassignedDocs.outgoing.length;

    let currentStage = '尚未開始';
    for (let i = records.length - 1; i >= 0; i--) {
      const rec = records[i];
      if (rec && rec.status !== 'completed') {
        currentStage = getCategoryLabel(rec);
        break;
      }
    }
    if (total > 0 && completed === total) {
      currentStage = '全部完成';
    }

    return {
      total, completed, inProgress, overdue, onHold,
      incomingDocs, outgoingDocs,
      linkedDocCount, unassignedDocCount,
      currentStage,
    };
  }, [records, linkedDocuments.length, unassignedDocs]);

  // 公文對照資料（只含已指派到作業紀錄的公文）
  const correspondenceData = useMemo<CorrespondenceBodyData>(() => {
    const sortedRecords = [...records].sort((a, b) => {
      const dateA = a.record_date || '';
      const dateB = b.record_date || '';
      if (dateA !== dateB) return dateA.localeCompare(dateB);
      return a.sort_order - b.sort_order;
    });

    return buildDocPairs(sortedRecords);
  }, [records]);

  return {
    records,
    stats,
    correspondenceData,
    unassignedDocs,
    assignedDocIds,
    isLoading,
  };
}

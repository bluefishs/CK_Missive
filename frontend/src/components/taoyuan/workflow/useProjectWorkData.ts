/**
 * useProjectWorkData - 工程作業統一資料 Hook
 *
 * 合併作業歷程 + 看板的資料查詢，提供三種視圖所需的衍生資料：
 * - correspondenceGroups: 公文對照表（派工單為主軸）
 * - batchGroups: 時間軸（批次分組）
 * - kanbanColumns: 看板（作業類別分組）
 *
 * @version 1.0.0
 * @date 2026-02-13
 */

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import { dispatchOrdersApi, workflowApi } from '../../../api/taoyuan';
import type {
  DispatchOrder,
  WorkRecord,
  WorkRecordStatus,
  MilestoneType,
  ProjectDispatchLinkItem,
  DocBrief,
} from '../../../types/taoyuan';
import {
  ALL_WORK_TYPES,
  getWorkTypeColor,
  getWorkTypes,
  computeDispatchStatus,
  type KanbanColumnData,
  type KanbanCardData,
} from '../kanban/kanbanConstants';
import { isOutgoingDocNumber, buildDocPairs } from './chainUtils';

// ============================================================================
// Types
// ============================================================================

export interface DispatchCorrespondenceGroup {
  dispatch: DispatchOrder;
  index: number;
  batchNo: number | null;
  batchLabel: string;
  keyDates: { date: string; label: string }[];
  incomingDocs: { record: WorkRecord; doc: DocBrief }[];
  outgoingDocs: { record: WorkRecord; doc: DocBrief }[];
  allRecords: WorkRecord[];
  computedStatus: WorkRecordStatus;
  stats: { total: number; completed: number };
}

export interface BatchGroup {
  batchNo: number | null;
  label: string;
  records: WorkRecord[];
  completedCount: number;
  totalCount: number;
}

export interface WorkOverviewStats {
  total: number;
  completed: number;
  inProgress: number;
  overdue: number;
  incomingDocs: number;
  outgoingDocs: number;
  currentStage: string;
  dispatchCount: number;
}

// ============================================================================
// 批次色帶（對應 Excel 底部色帶）
// ============================================================================

export const BATCH_COLORS: Record<number, { bg: string; border: string; tag: string }> = {
  1: { bg: '#fffbe6', border: '#faad14', tag: 'gold' },
  2: { bg: '#f6ffed', border: '#52c41a', tag: 'green' },
  3: { bg: '#e6f4ff', border: '#1677ff', tag: 'blue' },
  4: { bg: '#fff7e6', border: '#fa8c16', tag: 'orange' },
  5: { bg: '#fff0f6', border: '#eb2f96', tag: 'magenta' },
};

export function getBatchColor(batchNo: number | null) {
  if (batchNo === null) return { bg: '#fafafa', border: '#d9d9d9', tag: 'default' as const };
  return BATCH_COLORS[batchNo] || { bg: '#fafafa', border: '#d9d9d9', tag: 'default' as const };
}

// ============================================================================
// 里程碑 helpers
// ============================================================================

const MILESTONE_LABELS: Record<string, string> = {
  dispatch: '派工',
  survey: '會勘',
  site_inspection: '查估檢視',
  submit_result: '送件',
  revision: '修正',
  review_meeting: '審查',
  negotiation: '協議',
  final_approval: '定稿',
  boundary_survey: '土地鑑界',
  closed: '結案',
  other: '其他',
};

const MILESTONE_COLORS: Record<string, string> = {
  dispatch: 'blue',
  survey: 'cyan',
  site_inspection: 'geekblue',
  submit_result: 'purple',
  revision: 'orange',
  review_meeting: 'magenta',
  negotiation: 'volcano',
  final_approval: 'gold',
  boundary_survey: 'lime',
  closed: 'green',
  other: 'default',
};

const STATUS_LABELS: Record<string, string> = {
  pending: '待處理',
  in_progress: '進行中',
  completed: '已完成',
  overdue: '逾期',
  on_hold: '已暫緩',
};

const STATUS_COLORS: Record<string, string> = {
  pending: 'default',
  in_progress: 'processing',
  completed: 'success',
  overdue: 'error',
  on_hold: 'warning',
};

// 新格式作業類別標籤
// NOTE: 此處刻意重複 chainConstants.WORK_CATEGORY_LABELS，因為
// chainConstants.ts 已 import { milestoneLabel } from './useProjectWorkData'，
// 若本檔反向 import chainConstants 會產生循環引用。
const WORK_CATEGORY_LABELS_INLINE: Record<string, string> = {
  dispatch_notice: '派工通知',
  work_result: '作業成果',
  meeting_notice: '會議通知',
  meeting_record: '會議紀錄',
  survey_notice: '會勘通知',
  survey_record: '會勘紀錄',
  other: '其他',
};

export function milestoneLabel(type: MilestoneType | string): string {
  return MILESTONE_LABELS[type] || type;
}

export function milestoneColor(type: MilestoneType | string): string {
  return MILESTONE_COLORS[type] || 'default';
}

export function statusLabel(status: WorkRecordStatus | string): string {
  return STATUS_LABELS[status] || status;
}

export function statusColor(status: WorkRecordStatus | string): string {
  return STATUS_COLORS[status] || 'default';
}

// ============================================================================
// 批次分組（時間軸視圖用）
// ============================================================================

function groupByBatch(records: WorkRecord[]): BatchGroup[] {
  const groups = new Map<number | null, WorkRecord[]>();

  for (const r of records) {
    const key = r.batch_no ?? null;
    const arr = groups.get(key) ?? [];
    arr.push(r);
    groups.set(key, arr);
  }

  const sortedKeys = Array.from(groups.keys()).sort((a, b) => {
    if (a === null) return 1;
    if (b === null) return -1;
    return a - b;
  });

  return sortedKeys.map((key) => {
    const recs = groups.get(key) ?? [];
    const completed = recs.filter((r) => r.status === 'completed').length;
    return {
      batchNo: key,
      label:
        key !== null
          ? recs[0]?.batch_label || `第${key}批結案`
          : '未分批',
      records: recs.sort((a, b) => a.sort_order - b.sort_order),
      completedCount: completed,
      totalCount: recs.length,
    };
  });
}

// ============================================================================
// 公文對照分組（對照表視圖用）
// ============================================================================

function buildCorrespondenceGroups(
  dispatches: DispatchOrder[],
  records: WorkRecord[],
  linkedDispatchIds: Set<number>,
): DispatchCorrespondenceGroup[] {
  const linkedDispatches = dispatches.filter((d) => linkedDispatchIds.has(d.id));

  // WorkRecords 依 dispatch_order_id 分組
  const recordsByDispatch = new Map<number, WorkRecord[]>();
  for (const rec of records) {
    const list = recordsByDispatch.get(rec.dispatch_order_id) || [];
    list.push(rec);
    recordsByDispatch.set(rec.dispatch_order_id, list);
  }

  return linkedDispatches.map((dispatch, idx) => {
    const dispatchRecords = (recordsByDispatch.get(dispatch.id) || []).sort(
      (a, b) => {
        const dateA = a.record_date || '';
        const dateB = b.record_date || '';
        if (dateA !== dateB) return dateA.localeCompare(dateB);
        return a.sort_order - b.sort_order;
      },
    );

    // 從 WorkRecords 推算批次
    const batchNos = dispatchRecords
      .map((r) => r.batch_no)
      .filter((b): b is number => b !== undefined && b !== null);
    const batchNo = batchNos.length > 0 ? Math.max(...batchNos) : null;
    const batchLabel =
      batchNo !== null
        ? dispatchRecords.find((r) => r.batch_no === batchNo)?.batch_label ||
          `第${batchNo}批結案`
        : '未分批';

    // 提取有關聯公文的紀錄（新舊格式兼容，使用共用 buildDocPairs）
    const { incomingDocs, outgoingDocs } = buildDocPairs(dispatchRecords);

    // 關鍵日期（送件/修正里程碑 + 新格式作業成果）
    const keyDates = dispatchRecords
      .filter(
        (r) =>
          r.milestone_type === 'submit_result' ||
          r.milestone_type === 'revision' ||
          r.work_category === 'work_result',
      )
      .map((r) => ({
        date: r.record_date,
        label: r.work_category
          ? (WORK_CATEGORY_LABELS_INLINE[r.work_category] || milestoneLabel(r.milestone_type))
          : milestoneLabel(r.milestone_type),
      }));

    const completed = dispatchRecords.filter(
      (r) => r.status === 'completed',
    ).length;

    return {
      dispatch,
      index: idx + 1,
      batchNo,
      batchLabel,
      keyDates,
      incomingDocs,
      outgoingDocs,
      allRecords: dispatchRecords,
      computedStatus: computeDispatchStatus(dispatchRecords),
      stats: { total: dispatchRecords.length, completed },
    };
  });
}

// ============================================================================
// Main Hook
// ============================================================================

interface UseProjectWorkDataParams {
  projectId: number;
  contractProjectId?: number;
  linkedDispatches: ProjectDispatchLinkItem[];
}

export function useProjectWorkData({
  projectId,
  contractProjectId,
  linkedDispatches,
}: UseProjectWorkDataParams) {
  const linkedDispatchIds = useMemo(
    () => new Set(linkedDispatches.map((d) => d.dispatch_order_id)),
    [linkedDispatches],
  );

  // Query 1: 全部 WorkRecords
  const { data: workflowData, isLoading: isLoadingWorkflow } = useQuery({
    queryKey: ['project-work-records', projectId],
    queryFn: () => workflowApi.listByProject(projectId, 1, 500),
    enabled: projectId > 0,
  });

  // Query 2: 全部 DispatchOrders（同承攬案件下）
  const { data: dispatchData, isLoading: isLoadingDispatches } = useQuery({
    queryKey: ['kanban-dispatches', contractProjectId],
    queryFn: () =>
      dispatchOrdersApi.getList({
        contract_project_id: contractProjectId,
        limit: 200,
      }),
    enabled: !!contractProjectId && linkedDispatches.length > 0,
  });

  const records = useMemo(
    () => workflowData?.items ?? [],
    [workflowData?.items],
  );

  const allDispatches = useMemo(
    () => dispatchData?.items ?? [],
    [dispatchData?.items],
  );

  // 統計
  const stats = useMemo<WorkOverviewStats>(() => {
    const total = records.length;
    const completed = records.filter((r) => r.status === 'completed').length;
    const inProgress = records.filter((r) => r.status === 'in_progress').length;
    const overdue = records.filter((r) => r.status === 'overdue').length;
    // 統計來文/發文數（新舊格式兼容）
    const incomingIds = new Set<number>();
    const outgoingIds = new Set<number>();
    for (const r of records) {
      if (r.incoming_doc_id) incomingIds.add(r.incoming_doc_id);
      if (r.outgoing_doc_id) outgoingIds.add(r.outgoing_doc_id);
      if (r.document_id) {
        if (isOutgoingDocNumber(r.document?.doc_number)) {
          outgoingIds.add(r.document_id);
        } else {
          incomingIds.add(r.document_id);
        }
      }
    }
    const incomingDocs = incomingIds.size;
    const outgoingDocs = outgoingIds.size;

    let currentStage = '尚未開始';
    for (let i = records.length - 1; i >= 0; i--) {
      const rec = records[i];
      if (rec && rec.status !== 'completed') {
        // 新格式 work_category 優先，fallback milestone_type
        currentStage = rec.work_category
          ? (WORK_CATEGORY_LABELS_INLINE[rec.work_category] || milestoneLabel(rec.milestone_type))
          : milestoneLabel(rec.milestone_type);
        break;
      }
    }
    if (total > 0 && completed === total) {
      currentStage = '全部完成';
    }

    return {
      total,
      completed,
      inProgress,
      overdue,
      incomingDocs,
      outgoingDocs,
      currentStage,
      dispatchCount: linkedDispatches.length,
    };
  }, [records, linkedDispatches.length]);

  // 批次分組
  const batchGroups = useMemo(() => groupByBatch(records), [records]);

  // 看板欄位
  const kanbanColumns = useMemo<KanbanColumnData[]>(() => {
    const linkedList = allDispatches.filter((d: DispatchOrder) =>
      linkedDispatchIds.has(d.id),
    );

    const recordsByDispatch = new Map<number, WorkRecord[]>();
    for (const rec of records) {
      const list = recordsByDispatch.get(rec.dispatch_order_id) || [];
      list.push(rec);
      recordsByDispatch.set(rec.dispatch_order_id, list);
    }

    const columnMap = new Map<string, KanbanCardData[]>();
    for (const dispatch of linkedList) {
      const workTypes = getWorkTypes(dispatch);
      const dRecords = recordsByDispatch.get(dispatch.id) || [];
      const card: KanbanCardData = {
        dispatch,
        computedStatus: computeDispatchStatus(dRecords),
        recordCount: dRecords.length,
      };

      if (workTypes.length === 0) {
        const first = ALL_WORK_TYPES[0] as string;
        const list = columnMap.get(first) || [];
        list.push(card);
        columnMap.set(first, list);
      } else {
        for (const wt of workTypes) {
          const list = columnMap.get(wt) || [];
          list.push(card);
          columnMap.set(wt, list);
        }
      }
    }

    return ALL_WORK_TYPES.map((wt) => ({
      workType: wt,
      color: getWorkTypeColor(wt),
      cards: columnMap.get(wt) || [],
    }));
  }, [allDispatches, records, linkedDispatchIds]);

  // 公文對照分組
  const correspondenceGroups = useMemo(
    () => buildCorrespondenceGroups(allDispatches, records, linkedDispatchIds),
    [allDispatches, records, linkedDispatchIds],
  );

  const isLoading = isLoadingWorkflow || isLoadingDispatches;

  return {
    records,
    stats,
    batchGroups,
    kanbanColumns,
    correspondenceGroups,
    isLoading,
  };
}

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
import { queryKeys } from '../../../config/queryConfig';
import type {
  DispatchOrder,
  WorkRecord,
  WorkRecordStatus,
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
import {
  buildDocPairs,
  buildCorrespondenceMatrix,
  filterBlankRecords,
  computeDocStats,
  computeCurrentStage,
} from './chainUtils';
import type { CorrespondenceMatrixRow } from './chainUtils';
import {
  getCategoryLabel,
} from './workCategoryConstants';

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
  /** 矩陣配對行（3 階段匹配：parent_record_id → 日期鄰近 → 剩餘） */
  matrixRows: CorrespondenceMatrixRow[];
  allRecords: WorkRecord[];
  computedStatus: WorkRecordStatus;
  stats: { total: number; completed: number };
}

export interface BatchGroup {
  batchNo: number | null;
  label: string;
  dispatchNo?: string;
  dispatchId?: number;
  records: WorkRecord[];
  completedCount: number;
  totalCount: number;
}

/** 單一作業類別的階段進度 */
export interface WorkTypeStageInfo {
  workType: string;           // e.g., "01.地上物查估作業"
  stage: string;              // e.g., "作業成果"
  status: WorkRecordStatus;   // e.g., "in_progress"
  total: number;
  completed: number;
}

export interface WorkOverviewStats {
  total: number;
  completed: number;
  inProgress: number;
  overdue: number;
  incomingDocs: number;
  outgoingDocs: number;
  currentStage: string;
  workTypeStages: WorkTypeStageInfo[];
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

// 里程碑/狀態/作業類別 helpers 已統一移至 workCategoryConstants.ts
// 此處 re-export 維持向下相容

// ============================================================================
// 批次分組（時間軸視圖用）
// ============================================================================

function groupByBatch(
  records: WorkRecord[],
  dispatches: DispatchOrder[],
): BatchGroup[] {
  // 建立 dispatch 查詢表
  const dispatchMap = new Map<number, DispatchOrder>();
  for (const d of dispatches) {
    dispatchMap.set(d.id, d);
  }

  // 按派工單分組
  const groupsByDispatch = new Map<number, WorkRecord[]>();
  for (const r of records) {
    const list = groupsByDispatch.get(r.dispatch_order_id) ?? [];
    list.push(r);
    groupsByDispatch.set(r.dispatch_order_id, list);
  }

  // 轉換為 BatchGroup，按 batch_no 排序（null 在最後），同批次按 dispatch_no 排序
  const groups: BatchGroup[] = [];
  for (const [dispatchId, recs] of groupsByDispatch) {
    const dispatch = dispatchMap.get(dispatchId);
    const batchNo = dispatch?.batch_no ?? null;
    const completed = recs.filter((r) => r.status === 'completed').length;

    let batchPrefix = '未分批';
    if (batchNo !== null) {
      batchPrefix = dispatch?.batch_label || `第${batchNo}批結案`;
    }
    const dispatchNo = dispatch?.dispatch_no || `派工單#${dispatchId}`;
    const label = `${batchPrefix} — ${dispatchNo}`;

    groups.push({
      batchNo,
      label,
      dispatchNo,
      dispatchId,
      records: recs.sort((a, b) => a.sort_order - b.sort_order),
      completedCount: completed,
      totalCount: recs.length,
    });
  }

  // 排序：batch_no ASC (null 在最後)，同批次按 dispatchNo 排序
  groups.sort((a, b) => {
    if (a.batchNo === null && b.batchNo === null) return (a.dispatchNo ?? '').localeCompare(b.dispatchNo ?? '');
    if (a.batchNo === null) return 1;
    if (b.batchNo === null) return -1;
    if (a.batchNo !== b.batchNo) return a.batchNo - b.batchNo;
    return (a.dispatchNo ?? '').localeCompare(b.dispatchNo ?? '');
  });

  return groups;
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

    // 批次直接從派工單讀取
    const batchNo = dispatch.batch_no ?? null;
    const batchLabel =
      batchNo !== null
        ? dispatch.batch_label || `第${batchNo}批結案`
        : '未分批';

    // 提取有關聯公文的紀錄（新舊格式兼容，使用共用 buildDocPairs）
    const docPairs = buildDocPairs(dispatchRecords);
    const { incomingDocs, outgoingDocs } = docPairs;

    // 使用 3 階段匹配建構矩陣（與派工單層級一致）
    // 未指派公文暫傳空陣列（列表 API 不含 linked_documents）
    const matrixRows = buildCorrespondenceMatrix(docPairs, [], []);

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
        label: getCategoryLabel(r),
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
      matrixRows,
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
    queryKey: queryKeys.workRecords.project(projectId),
    queryFn: () => workflowApi.listByProject(projectId, 1, 200),
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

  // 過濾空白紀錄（共用邏輯）
  const records = useMemo(
    () => filterBlankRecords(workflowData?.items ?? []),
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
    const { incomingDocs, outgoingDocs } = computeDocStats(records);
    const currentStage = computeCurrentStage(records);

    // 按作業類別分組，以派工單為單位計算各自的階段進度
    const workTypeStages: WorkTypeStageInfo[] = (() => {
      // 建立 dispatch → records 映射
      const recordsByDispatch = new Map<number, WorkRecord[]>();
      for (const r of records) {
        const list = recordsByDispatch.get(r.dispatch_order_id) ?? [];
        list.push(r);
        recordsByDispatch.set(r.dispatch_order_id, list);
      }

      // 建立 dispatch 查詢表
      const dispatchMap = new Map<number, DispatchOrder>();
      for (const d of allDispatches) {
        dispatchMap.set(d.id, d);
      }

      // 聚合：workType → dispatches[] (以派工單為計算單位)
      const wtDispatches = new Map<string, { dispatch: DispatchOrder; records: WorkRecord[] }[]>();
      for (const dispatchId of linkedDispatchIds) {
        const dispatch = dispatchMap.get(dispatchId);
        if (!dispatch) continue;
        const workTypes = getWorkTypes(dispatch);
        const dRecords = recordsByDispatch.get(dispatchId) ?? [];
        if (workTypes.length === 0) continue;
        for (const wt of workTypes) {
          const list = wtDispatches.get(wt) ?? [];
          list.push({ dispatch, records: dRecords });
          wtDispatches.set(wt, list);
        }
      }

      // 轉換為 WorkTypeStageInfo[]
      const stages: WorkTypeStageInfo[] = [];
      for (const [wt, entries] of wtDispatches) {
        const wtTotal = entries.length; // 派工單數
        const wtCompleted = entries.filter((e) => {
          // 派工單「已完成」= 有紀錄且全部 completed
          return e.records.length > 0 && e.records.every((r) => r.status === 'completed');
        }).length;
        const allRecords = entries.flatMap((e) => e.records);
        const wtStatus = computeDispatchStatus(allRecords);

        // 找出此作業類別下最新的進行中階段（共用函數）
        const stage = computeCurrentStage(allRecords);

        stages.push({
          workType: wt,
          stage,
          status: wtStatus,
          total: wtTotal,
          completed: wtCompleted,
        });
      }

      // 依 ALL_WORK_TYPES 順序排序
      const orderMap = new Map(ALL_WORK_TYPES.map((wt, i) => [wt, i]));
      stages.sort((a, b) => (orderMap.get(a.workType) ?? 99) - (orderMap.get(b.workType) ?? 99));
      return stages;
    })();

    return {
      total,
      completed,
      inProgress,
      overdue,
      incomingDocs,
      outgoingDocs,
      currentStage,
      workTypeStages,
      dispatchCount: linkedDispatches.length,
    };
  }, [records, linkedDispatches.length, allDispatches, linkedDispatchIds]);

  // 批次分組（從派工單讀取批次）
  const batchGroups = useMemo(
    () => groupByBatch(records, allDispatches),
    [records, allDispatches],
  );

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

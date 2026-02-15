/**
 * useKanbanData - Kanban 看板資料 Hook
 *
 * 取得派工單列表與作業紀錄，依作業類別分組成看板欄位資料。
 *
 * @version 1.0.0
 * @date 2026-02-13
 */

import { useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import { dispatchOrdersApi, workflowApi } from '../../../api/taoyuan';
import type { DispatchOrder, WorkRecord, ProjectDispatchLinkItem } from '../../../types/taoyuan';
import {
  ALL_WORK_TYPES,
  getWorkTypeColor,
  getWorkTypes,
  computeDispatchStatus,
  type KanbanColumnData,
  type KanbanCardData,
} from './kanbanConstants';

interface UseKanbanDataParams {
  projectId: number;
  contractProjectId?: number;
  linkedDispatches: ProjectDispatchLinkItem[];
}

export function useKanbanData({ projectId, contractProjectId, linkedDispatches }: UseKanbanDataParams) {
  const linkedDispatchIds = useMemo(
    () => new Set(linkedDispatches.map((d) => d.dispatch_order_id)),
    [linkedDispatches],
  );

  // 取得所有派工單（同一承攬案件下）
  const {
    data: dispatchData,
    isLoading: isLoadingDispatches,
    refetch: refetchDispatches,
  } = useQuery({
    queryKey: ['kanban-dispatches', contractProjectId],
    queryFn: () =>
      dispatchOrdersApi.getList({
        contract_project_id: contractProjectId,
        limit: 200,
      }),
    enabled: !!contractProjectId && linkedDispatches.length > 0,
  });

  // 取得工程的所有作業紀錄
  const {
    data: workflowData,
    isLoading: isLoadingWorkflow,
    refetch: refetchWorkflow,
  } = useQuery({
    queryKey: ['kanban-workflow', projectId],
    queryFn: () => workflowApi.listByProject(projectId, 1, 500),
    enabled: projectId > 0,
  });

  const columns = useMemo<KanbanColumnData[]>(() => {
    const allDispatches = dispatchData?.items || [];
    const allRecords = workflowData?.items || [];

    // 只保留已關聯的派工單
    const linkedList = allDispatches.filter((d: DispatchOrder) => linkedDispatchIds.has(d.id));

    // 建立 dispatch_order_id → WorkRecord[] 映射
    const recordsByDispatch = new Map<number, WorkRecord[]>();
    for (const rec of allRecords) {
      const list = recordsByDispatch.get(rec.dispatch_order_id) || [];
      list.push(rec);
      recordsByDispatch.set(rec.dispatch_order_id, list);
    }

    // 依作業類別分組（M:N → 同一派工單可出現在多欄）
    const columnMap = new Map<string, KanbanCardData[]>();

    for (const dispatch of linkedList) {
      const workTypes = getWorkTypes(dispatch);
      const records = recordsByDispatch.get(dispatch.id) || [];
      const card: KanbanCardData = {
        dispatch,
        computedStatus: computeDispatchStatus(records),
        recordCount: records.length,
      };

      if (workTypes.length === 0) {
        // 無作業類別 → 放入第一欄
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

    // 依固定順序生成所有 10 欄
    return ALL_WORK_TYPES.map((wt) => ({
      workType: wt,
      color: getWorkTypeColor(wt),
      cards: columnMap.get(wt) || [],
    }));
  }, [dispatchData, workflowData, linkedDispatchIds]);

  const isLoading = isLoadingDispatches || isLoadingWorkflow;

  const refetch = useCallback(() => {
    refetchDispatches();
    refetchWorkflow();
  }, [refetchDispatches, refetchWorkflow]);

  return { columns, isLoading, refetch };
}

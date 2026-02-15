/**
 * Kanban 看板常數與工具函數
 *
 * 作業類別色彩映射、狀態配置、派工單狀態計算
 *
 * @version 1.0.0
 * @date 2026-02-13
 */

import type { WorkRecord, WorkRecordStatus, DispatchOrder, DispatchWorkTypeItem } from '../../../types/taoyuan';
import { TAOYUAN_WORK_TYPES } from '../../../types/taoyuan';

// ============================================================================
// 作業類別色彩映射 (10 種)
// ============================================================================

export const WORK_TYPE_COLORS: Record<string, string> = {
  '#0.專案行政作業': '#722ed1',   // purple
  '00.專案會議': '#eb2f96',       // magenta
  '01.地上物查估作業': '#52c41a', // green
  '02.土地協議市價查估作業': '#13c2c2', // cyan
  '03.土地徵收市價查估作業': '#1677ff', // blue
  '04.相關計畫書製作': '#2f54eb', // geekblue
  '05.測量作業': '#fa8c16',       // orange
  '06.樁位測釘作業': '#faad14',   // gold
  '07.辦理教育訓練': '#a0d911',   // lime
  '08.作業提繳事項': '#fa541c',   // volcano
};

/** 取得作業類別色彩，預設為灰色 */
export function getWorkTypeColor(workType: string): string {
  return WORK_TYPE_COLORS[workType] || '#8c8c8c';
}

// ============================================================================
// 狀態配置
// ============================================================================

export const STATUS_CONFIG: Record<WorkRecordStatus, { label: string; color: string }> = {
  pending: { label: '未開始', color: '#d9d9d9' },
  in_progress: { label: '進行中', color: '#1677ff' },
  completed: { label: '已完成', color: '#52c41a' },
  overdue: { label: '已逾期', color: '#ff4d4f' },
  on_hold: { label: '已暫緩', color: '#faad14' },
};

// ============================================================================
// 工具函數
// ============================================================================

/**
 * 從派工單取得作業類別列表
 *
 * 優先使用正規化的 work_type_items，退回到 work_type 字串分割
 */
export function getWorkTypes(dispatch: DispatchOrder): string[] {
  if (dispatch.work_type_items && dispatch.work_type_items.length > 0) {
    return dispatch.work_type_items
      .sort((a: DispatchWorkTypeItem, b: DispatchWorkTypeItem) => a.sort_order - b.sort_order)
      .map((item: DispatchWorkTypeItem) => item.work_type);
  }

  if (dispatch.work_type) {
    return dispatch.work_type
      .split(',')
      .map((t: string) => t.trim())
      .filter(Boolean);
  }

  return [];
}

/**
 * 依作業紀錄計算派工單狀態
 *
 * 優先順序：overdue > in_progress > completed > pending
 */
export function computeDispatchStatus(records: WorkRecord[]): WorkRecordStatus {
  if (records.length === 0) return 'pending';

  const hasOverdue = records.some((r) => r.status === 'overdue');
  if (hasOverdue) return 'overdue';

  const hasInProgress = records.some((r) => r.status === 'in_progress');
  if (hasInProgress) return 'in_progress';

  const allCompleted = records.every((r) => r.status === 'completed');
  if (allCompleted) return 'completed';

  return 'pending';
}

// ============================================================================
// Kanban 資料型別
// ============================================================================

export interface KanbanCardData {
  dispatch: DispatchOrder;
  computedStatus: WorkRecordStatus;
  recordCount: number;
}

export interface KanbanColumnData {
  workType: string;
  color: string;
  cards: KanbanCardData[];
}

/** 所有作業類別（保持排序） */
export const ALL_WORK_TYPES: readonly string[] = TAOYUAN_WORK_TYPES;

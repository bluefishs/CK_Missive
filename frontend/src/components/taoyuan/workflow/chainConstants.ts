/**
 * chainConstants - 鏈式時間軸常數與顯示函數
 *
 * 作業類別 (WorkCategory) 分組、狀態選項、統一顯示函數
 * 相容新格式 (work_category) 與舊格式 (milestone_type)
 *
 * @version 2.0.0 - 重構：常數移至 workCategoryConstants.ts（解循環依賴）
 * @date 2026-03-04
 */

import type { WorkRecordStatus } from '../../../types/taoyuan';

// ============================================================================
// 鏈式狀態選項 (新格式，3 種)
// ============================================================================

export const CHAIN_STATUS_OPTIONS: {
  value: WorkRecordStatus;
  label: string;
  color: string;
}[] = [
  { value: 'in_progress', label: '辦理中', color: 'processing' },
  { value: 'completed', label: '已完成', color: 'success' },
  { value: 'on_hold', label: '暫緩', color: 'warning' },
];

// ============================================================================
// 鏈式狀態映射（含舊格式，「辦理中」用於鏈式視圖）
// ============================================================================

const CHAIN_STATUS_LABELS: Record<string, string> = {
  pending: '待處理',
  in_progress: '辦理中',
  completed: '已完成',
  overdue: '逾期',
  on_hold: '暫緩',
};

const CHAIN_STATUS_COLORS: Record<string, string> = {
  pending: 'default',
  in_progress: 'processing',
  completed: 'success',
  overdue: 'error',
  on_hold: 'warning',
};

/** 取得鏈式視圖的狀態標籤（「辦理中」而非「進行中」） */
export function getStatusLabel(status: WorkRecordStatus | string): string {
  return CHAIN_STATUS_LABELS[status] || status;
}

/** 取得鏈式視圖的狀態顏色 */
export function getStatusColor(status: WorkRecordStatus | string): string {
  return CHAIN_STATUS_COLORS[status] || 'default';
}

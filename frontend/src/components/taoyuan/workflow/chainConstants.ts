/**
 * chainConstants - 鏈式時間軸常數與顯示函數
 *
 * 作業類別 (WorkCategory) 分組、狀態選項、統一顯示函數
 * 相容新格式 (work_category) 與舊格式 (milestone_type)
 *
 * @version 1.0.0
 * @date 2026-02-13
 */

import type { WorkRecord, WorkCategory, WorkRecordStatus } from '../../../types/taoyuan';
import { milestoneLabel, milestoneColor } from './useProjectWorkData';

// ============================================================================
// 作業類別分組 (OptGroup 用)
// ============================================================================

export interface WorkCategoryItem {
  value: WorkCategory;
  label: string;
  color: string;
}

export interface WorkCategoryGroup {
  group: string;
  items: WorkCategoryItem[];
}

export const WORK_CATEGORY_GROUPS: WorkCategoryGroup[] = [
  {
    group: '派工作業',
    items: [
      { value: 'dispatch_notice', label: '派工通知', color: 'blue' },
      { value: 'work_result', label: '作業成果', color: 'cyan' },
    ],
  },
  {
    group: '開會(審查)作業',
    items: [
      { value: 'meeting_notice', label: '會議通知', color: 'purple' },
      { value: 'meeting_record', label: '會議紀錄', color: 'geekblue' },
    ],
  },
  {
    group: '會勘作業',
    items: [
      { value: 'survey_notice', label: '會勘通知', color: 'orange' },
      { value: 'survey_record', label: '會勘紀錄', color: 'gold' },
    ],
  },
  {
    group: '其他',
    items: [
      { value: 'other', label: '其他', color: 'default' },
    ],
  },
];

// 扁平查找表
export const WORK_CATEGORY_LABELS: Record<string, string> = {};
export const WORK_CATEGORY_COLORS: Record<string, string> = {};

for (const group of WORK_CATEGORY_GROUPS) {
  for (const item of group.items) {
    WORK_CATEGORY_LABELS[item.value] = item.label;
    WORK_CATEGORY_COLORS[item.value] = item.color;
  }
}

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
  { value: 'on_hold', label: '已暫緩', color: 'warning' },
];

// ============================================================================
// 統一顯示函數（新舊格式相容）
// ============================================================================

/** 取得紀錄的類別標籤（先查 work_category，fallback milestone_type） */
export function getCategoryLabel(record: WorkRecord): string {
  if (record.work_category) {
    const label = WORK_CATEGORY_LABELS[record.work_category];
    if (label) return label;
  }
  return milestoneLabel(record.milestone_type);
}

/** 取得紀錄的類別顏色 */
export function getCategoryColor(record: WorkRecord): string {
  if (record.work_category) {
    const color = WORK_CATEGORY_COLORS[record.work_category];
    if (color) return color;
  }
  return milestoneColor(record.milestone_type);
}

// 完整狀態映射（含舊格式）
const ALL_STATUS_LABELS: Record<string, string> = {
  pending: '待處理',
  in_progress: '辦理中',
  completed: '已完成',
  overdue: '逾期',
  on_hold: '已暫緩',
};

const ALL_STATUS_COLORS: Record<string, string> = {
  pending: 'default',
  in_progress: 'processing',
  completed: 'success',
  overdue: 'error',
  on_hold: 'warning',
};

/** 取得紀錄的狀態標籤 */
export function getStatusLabel(status: WorkRecordStatus | string): string {
  return ALL_STATUS_LABELS[status] || status;
}

/** 取得紀錄的狀態顏色 */
export function getStatusColor(status: WorkRecordStatus | string): string {
  return ALL_STATUS_COLORS[status] || 'default';
}

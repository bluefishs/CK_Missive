/**
 * workCategoryConstants - 作業類別/里程碑/狀態 統一常數
 *
 * 所有顯示用的 label/color 映射集中於此檔案（leaf node，無 workflow/ 內部 import）。
 * chainConstants.ts 和 useProjectWorkData.ts 皆從此檔匯入，避免循環依賴。
 *
 * @version 1.0.0
 * @date 2026-03-04
 */

import type { WorkRecord, WorkCategory, WorkRecordStatus, MilestoneType } from '../../../types/taoyuan';

// ============================================================================
// 里程碑 (legacy 格式)
// ============================================================================

export const MILESTONE_LABELS: Record<string, string> = {
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

export const MILESTONE_COLORS: Record<string, string> = {
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

export function milestoneLabel(type: MilestoneType | string): string {
  return MILESTONE_LABELS[type] || type;
}

export function milestoneColor(type: MilestoneType | string): string {
  return MILESTONE_COLORS[type] || 'default';
}

// ============================================================================
// 狀態
// ============================================================================

export const STATUS_LABELS: Record<string, string> = {
  pending: '待處理',
  in_progress: '進行中',
  completed: '已完成',
  overdue: '逾期',
  on_hold: '暫緩',
};

export const STATUS_COLORS: Record<string, string> = {
  pending: 'default',
  in_progress: 'processing',
  completed: 'success',
  overdue: 'error',
  on_hold: 'warning',
};

export function statusLabel(status: WorkRecordStatus | string): string {
  return STATUS_LABELS[status] || status;
}

export function statusColor(status: WorkRecordStatus | string): string {
  return STATUS_COLORS[status] || 'default';
}

// ============================================================================
// 作業類別 (v2 新格式)
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
    group: '行政作業',
    items: [
      { value: 'admin_notice', label: '行政通知', color: 'volcano' },
    ],
  },
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

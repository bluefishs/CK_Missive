/**
 * 承攬案件相關常數定義
 *
 * 集中管理專案/案件相關的選項常數
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

// 案件狀態選項
export const PROJECT_STATUS_OPTIONS = [
  '待執行',
  '執行中',
  '已結案',
  '未得標',
] as const;

export type ProjectStatus = (typeof PROJECT_STATUS_OPTIONS)[number];

// 案件類別選項
export const PROJECT_CATEGORY_OPTIONS = [
  { value: '01委辦案件', label: '01委辦案件' },
  { value: '02協力計畫', label: '02協力計畫' },
  { value: '03小額採購', label: '03小額採購' },
  { value: '04其他類別', label: '04其他類別' },
] as const;

export const PROJECT_CATEGORY_VALUES = [
  '01委辦案件',
  '02協力計畫',
  '03小額採購',
  '04其他類別',
] as const;

export type ProjectCategory = (typeof PROJECT_CATEGORY_VALUES)[number];

// 案件性質選項
export const CASE_NATURE_OPTIONS = [
  { value: '01測量案', label: '01測量案' },
  { value: '02資訊案', label: '02資訊案' },
  { value: '03複合案', label: '03複合案' },
] as const;

export const CASE_NATURE_VALUES = [
  '01測量案',
  '02資訊案',
  '03複合案',
] as const;

export type CaseNature = (typeof CASE_NATURE_VALUES)[number];

// 協力廠商角色選項
export const VENDOR_ROLE_OPTIONS = [
  '測量業務',
  '系統業務',
  '查估業務',
  '其他類別',
] as const;

export type VendorRole = (typeof VENDOR_ROLE_OPTIONS)[number];

// 狀態顏色映射
export const PROJECT_STATUS_COLORS: Record<string, string> = {
  '待執行': 'orange',
  '執行中': 'processing',
  '已結案': 'success',
  '未得標': 'default',
};

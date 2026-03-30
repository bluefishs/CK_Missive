/**
 * 承攬案件相關常數定義
 *
 * 集中管理專案/案件相關的選項常數
 *
 * @version 2.0.0
 * @date 2026-03-30
 */

// 案件狀態選項
export const PROJECT_STATUS_OPTIONS = [
  '待執行',
  '執行中',
  '已結案',
  '未得標',
] as const;

export type ProjectStatus = (typeof PROJECT_STATUS_OPTIONS)[number];

// 計畫類別選項 (v2.0)
export const PROJECT_CATEGORY_OPTIONS = [
  { value: '01委辦招標', label: '01委辦招標' },
  { value: '02承攬報價', label: '02承攬報價' },
] as const;

export const PROJECT_CATEGORY_VALUES = [
  '01委辦招標',
  '02承攬報價',
] as const;

export type ProjectCategory = (typeof PROJECT_CATEGORY_VALUES)[number];

// 作業性質選項 (v2.0 — 11 類)
export const CASE_NATURE_OPTIONS = [
  { value: '01地面測量', label: '01地面測量' },
  { value: '02LiDAR掃描', label: '02LiDAR掃描' },
  { value: '03UAV空拍', label: '03UAV空拍' },
  { value: '04航空測量', label: '04航空測量' },
  { value: '05安全檢測', label: '05安全檢測' },
  { value: '06建物保存', label: '06建物保存' },
  { value: '07建築線測量', label: '07建築線測量' },
  { value: '08透地雷達', label: '08透地雷達' },
  { value: '09資訊系統', label: '09資訊系統' },
  { value: '10技師簽證', label: '10技師簽證' },
  { value: '11其他類別', label: '11其他類別' },
] as const;

export const CASE_NATURE_VALUES = [
  '01地面測量', '02LiDAR掃描', '03UAV空拍', '04航空測量',
  '05安全檢測', '06建物保存', '07建築線測量', '08透地雷達',
  '09資訊系統', '10技師簽證', '11其他類別',
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

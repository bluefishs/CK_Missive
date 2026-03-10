/**
 * 員工相關常數定義
 *
 * 集中管理承辦同仁相關的選項常數
 *
 * @version 2.0.0
 * @date 2026-03-06
 * @changes 部門選項改為 DB 驅動（useDepartments hook），移除硬編碼
 */

// 同仁角色選項
export const STAFF_ROLE_OPTIONS = [
  '計畫主持',
  '計畫協同',
  '專案PM',
  '職安主管',
] as const;

export type StaffRole = (typeof STAFF_ROLE_OPTIONS)[number];

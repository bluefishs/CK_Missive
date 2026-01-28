/**
 * 員工相關常數定義
 *
 * 集中管理承辦同仁相關的選項常數
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

// 部門選項
export const DEPARTMENT_OPTIONS = [
  '空間資訊部',
  '測量部',
  '管理部',
] as const;

export type Department = (typeof DEPARTMENT_OPTIONS)[number];

// 同仁角色選項
export const STAFF_ROLE_OPTIONS = [
  '計畫主持',
  '計畫協同',
  '專案PM',
  '職安主管',
] as const;

export type StaffRole = (typeof STAFF_ROLE_OPTIONS)[number];

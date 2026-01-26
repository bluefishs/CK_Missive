/**
 * 機關相關常數定義
 *
 * 集中管理機關單位相關的選項常數
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

// 機關分類選項（三大分類）
export const AGENCY_CATEGORY_OPTIONS = [
  { value: '政府機關', label: '政府機關', color: 'blue' },
  { value: '民間企業', label: '民間企業', color: 'purple' },
  { value: '其他單位', label: '其他單位', color: 'orange' },
] as const;

export const AGENCY_CATEGORY_VALUES = [
  '政府機關',
  '民間企業',
  '其他單位',
] as const;

export type AgencyCategory = (typeof AGENCY_CATEGORY_VALUES)[number];

// 機關類型選項（與後端 AGENCY_TYPE_OPTIONS 一致）
export const AGENCY_TYPE_OPTIONS = [
  { value: '中央機關', label: '中央機關' },
  { value: '地方機關', label: '地方機關' },
  { value: '民間單位', label: '民間單位' },
  { value: '其他', label: '其他' },
] as const;

export const AGENCY_TYPE_VALUES = [
  '中央機關',
  '地方機關',
  '民間單位',
  '其他',
] as const;

export type AgencyType = (typeof AGENCY_TYPE_VALUES)[number];

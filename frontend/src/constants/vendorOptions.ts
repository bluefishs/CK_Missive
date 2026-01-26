/**
 * 廠商相關常數定義
 *
 * 集中管理協力廠商相關的選項常數
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

// 營業項目選項
export const BUSINESS_TYPE_OPTIONS = [
  { value: '測量業務', label: '測量業務', color: 'blue' },
  { value: '資訊系統', label: '資訊系統', color: 'cyan' },
  { value: '系統業務', label: '系統業務', color: 'geekblue' },
  { value: '查估業務', label: '查估業務', color: 'orange' },
  { value: '不動產估價', label: '不動產估價', color: 'purple' },
  { value: '大地工程', label: '大地工程', color: 'gold' },
  { value: '其他類別', label: '其他類別', color: 'default' },
] as const;

export const BUSINESS_TYPE_VALUES = [
  '測量業務',
  '資訊系統',
  '系統業務',
  '查估業務',
  '不動產估價',
  '大地工程',
  '其他類別',
] as const;

export type BusinessType = (typeof BUSINESS_TYPE_VALUES)[number];

// 取得營業項目標籤顏色
export const getBusinessTypeColor = (type?: string): string => {
  const option = BUSINESS_TYPE_OPTIONS.find(opt => opt.value === type);
  return option?.color || 'default';
};

// 評價選項
export const RATING_OPTIONS = [
  { value: 5, label: '5星', color: 'green' },
  { value: 4, label: '4星', color: 'lime' },
  { value: 3, label: '3星', color: 'orange' },
  { value: 2, label: '2星', color: 'volcano' },
  { value: 1, label: '1星', color: 'red' },
] as const;

// 取得評價顏色
export const getRatingColor = (rating?: number): string => {
  if (!rating) return 'default';
  if (rating >= 4) return 'green';
  if (rating >= 3) return 'orange';
  return 'red';
};

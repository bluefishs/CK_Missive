/**
 * ContractCasePage 常數與工具函數
 *
 * 案件類別映射、正規化、標籤顏色/文字
 * CATEGORY_OPTIONS 與 tabs/constants.ts 保持一致
 *
 * @version 1.0.0
 * @date 2026-03-18
 */

import { CATEGORY_OPTIONS, STATUS_OPTIONS } from './tabs/constants';

export { CATEGORY_OPTIONS };

// 類別映射表 (處理舊資料格式)
const CATEGORY_MAP: Record<string, string> = {
  '01': '01', '委辦案件': '01', '01委辦案件': '01',
  '02': '02', '協力計畫': '02', '02協力計畫': '02',
  '03': '03', '小額採購': '03', '03小額採購': '03',
  '04': '04', '其他類別': '04', '04其他類別': '04',
};

/** 取得標準化類別代碼 */
export const normalizeCategory = (category?: string): string => {
  if (!category) return '';
  return CATEGORY_MAP[category] || category;
};

/** 取得類別標籤顏色 */
export const getCategoryTagColor = (category?: string) => {
  const normalized = normalizeCategory(category);
  const option = CATEGORY_OPTIONS.find(c => c.value === normalized);
  return option?.color || 'default';
};

/** 取得類別標籤文字 */
export const getCategoryTagText = (category?: string) => {
  const normalized = normalizeCategory(category);
  const option = CATEGORY_OPTIONS.find(c => c.value === normalized);
  return option?.label || category || '未分類';
};

/** 取得狀態顏色 */
export const getStatusColor = (status?: string) => {
  switch (status) {
    case '執行中': return 'processing';
    case '已結案': return 'success';
    case '未得標': return 'error';
    case '暫停': return 'error';  // 舊資料相容
    default: return 'default';
  }
};

/** 取得狀態顯示標籤（暫停 → 未得標） */
export const getStatusLabel = (status?: string) => {
  if (!status) return '未設定';
  const option = STATUS_OPTIONS.find(opt => opt.value === status);
  return option?.label || status;
};

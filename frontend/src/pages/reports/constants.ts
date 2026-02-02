/**
 * 統計報表 - 共用常數與工具函數
 *
 * @version 1.1.0 - 機關名稱處理函數移至 utils/agencyUtils
 * @date 2026-02-02
 */

// ============================================================================
// 機關名稱處理函數 - 從 utils/agencyUtils 重導出
// ============================================================================
export {
  normalizeName,
  extractAgencyName,
  formatAgencyDisplay,
  extractAgencyList
} from '../../utils/agencyUtils';

// ============================================================================
// 報表專用常數
// ============================================================================

// 圖表顏色配置
export const COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16'];

// 不納入經費統計的狀態（待執行、未得標）
export const EXCLUDED_STATUSES = ['待執行', '未得標', '暫停'];  // 包含舊資料「暫停」

// 狀態顯示名稱對照（舊資料相容）
export const STATUS_DISPLAY_MAP: Record<string, string> = {
  '暫停': '未得標',  // 舊資料相容
};

// 案件類別代碼對照表
export const CATEGORY_LABEL_MAP: Record<string, string> = {
  '01': '01委辦案件',
  '02': '02協力計畫',
  '03': '03小額採購',
  '04': '04其他類別',
};

// ============================================================================
// 報表專用工具函數
// ============================================================================

// 格式化金額
export const formatCurrency = (value: number | null | undefined): string => {
  if (value === null || value === undefined || isNaN(value)) {
    return '0';
  }
  if (value >= 100000000) {
    return `${(value / 100000000).toFixed(2)} 億`;
  }
  if (value >= 10000) {
    return `${(value / 10000).toFixed(1)} 萬`;
  }
  return value.toLocaleString();
};

// 取得狀態顯示名稱
export const getStatusDisplayName = (status: string): string => {
  return STATUS_DISPLAY_MAP[status] || status;
};

// 取得類別顯示名稱
export const getCategoryDisplayName = (category: string): string => {
  return CATEGORY_LABEL_MAP[category] || category;
};

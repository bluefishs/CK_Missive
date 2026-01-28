/**
 * DocumentFilter 元件 - 向後相容匯出
 *
 * 此檔案保留以維持向後相容性
 * 實際實作已移至 ./DocumentFilter/ 目錄
 *
 * @deprecated 請直接從 './DocumentFilter' 目錄匯入
 * @version 2.0.0
 * @date 2026-01-26
 */

// 重新匯出所有內容
export {
  DocumentFilter,
  type DocumentFilterProps,
  // 子元件
  PrimaryFilters,
  AdvancedFilters,
  FilterActions,
  FilterFieldWrapper,
  // Hooks
  useFilterOptions,
  useAutocompleteSuggestions,
  // 常數
  DOC_TYPE_OPTIONS,
  DELIVERY_METHOD_OPTIONS,
  STATUS_OPTIONS,
} from './DocumentFilter/index';

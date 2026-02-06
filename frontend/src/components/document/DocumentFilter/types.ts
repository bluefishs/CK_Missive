/**
 * DocumentFilter 元件型別定義
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import { DocumentFilter as DocumentFilterType } from '../../../types';

// ============================================================================
// API 回應型別
// ============================================================================

/** 下拉選單選項 */
export interface DropdownOption {
  value: string;
  label: string;
}

/** 機關下拉選項 API 回應 */
export interface AgenciesDropdownResponse {
  options: DropdownOption[];
}

/** 承攬案件下拉選項 API 回應 */
export interface ContractProjectsDropdownResponse {
  options: DropdownOption[];
}

/** 年度選項 API 回應 */
export interface YearsResponse {
  years: (number | string)[];
}

// ============================================================================
// 元件 Props 型別
// ============================================================================

/** 主 DocumentFilter 元件 Props */
export interface DocumentFilterProps {
  filters: DocumentFilterType;
  onFiltersChange: (filters: DocumentFilterType) => void;
  onReset: () => void;
}

/** 篩選選項資料 */
export interface FilterOptionsData {
  yearOptions: DropdownOption[];
  contractCaseOptions: DropdownOption[];
  senderOptions: DropdownOption[];
  receiverOptions: DropdownOption[];
  isLoading: boolean;
}

/** 主要篩選區塊 Props */
export interface PrimaryFiltersProps {
  localFilters: DocumentFilterType;
  isMobile: boolean;
  contractCaseOptions: DropdownOption[];
  onFilterChange: <K extends keyof DocumentFilterType>(field: K, value: DocumentFilterType[K]) => void;
  onMultipleFilterChange?: (updates: Partial<DocumentFilterType>) => void;
  onApplyFilters: () => void;
}

/** 進階篩選區塊 Props */
export interface AdvancedFiltersProps {
  localFilters: DocumentFilterType;
  isMobile: boolean;
  yearOptions: DropdownOption[];
  senderOptions: DropdownOption[];
  receiverOptions: DropdownOption[];
  dateRange: [import('dayjs').Dayjs | null, import('dayjs').Dayjs | null] | null;
  onFilterChange: <K extends keyof DocumentFilterType>(field: K, value: DocumentFilterType[K]) => void;
  onMultipleFilterChange: (updates: Partial<DocumentFilterType>) => void;
  onDateRangeChange: (dates: [import('dayjs').Dayjs | null, import('dayjs').Dayjs | null] | null) => void;
  onApplyFilters: () => void;
}

/** 操作按鈕區塊 Props */
export interface FilterActionsProps {
  isMobile: boolean;
  hasActiveFilters: boolean;
  activeFilterCount: number;
  onReset: () => void;
  onApplyFilters: () => void;
}

/** 欄位包裝器 Props */
export interface FilterFieldWrapperProps {
  label: string;
  tooltip: string;
  isMobile: boolean;
  children: React.ReactNode;
}

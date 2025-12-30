// 承攬案件相關類型定義

export interface ContractCase {
  id: number;
  year: string; // 年度別
  project_name: string; // 專案名稱
  client_unit: string; // 委託單位
  contract_period_start: string; // 契約履歷期程開始
  contract_period_end: string; // 契約履歷期程結束
  responsible_staff: string; // 承辦同仁
  partner_vendor: string; // 協力廠商
  case_type: ContractCaseType; // 案件性質
  case_status: ContractCaseStatus; // 案件狀態
  contract_amount?: number; // 契約金額
  description?: string; // 案件說明
  notes?: string; // 備註
  created_at: string;
  updated_at: string;
}

// 案件性質分類
export enum ContractCaseType {
  INNOVATION = 0, // 創新專案
  COMMISSION = 1, // 委辦計畫
  COOPERATION = 2, // 協辦計畫
  EXTENSION = 3, // 委辦擴充
  SMALL_PURCHASE = 4, // 小額採購
}

// 案件性質標籤
export const CONTRACT_CASE_TYPE_LABELS = {
  [ContractCaseType.INNOVATION]: '創新專案',
  [ContractCaseType.COMMISSION]: '委辦計畫',
  [ContractCaseType.COOPERATION]: '協辦計畫',
  [ContractCaseType.EXTENSION]: '委辦擴充',
  [ContractCaseType.SMALL_PURCHASE]: '小額採購',
} as const;

// 案件性質顏色
export const CONTRACT_CASE_TYPE_COLORS = {
  [ContractCaseType.INNOVATION]: 'purple',
  [ContractCaseType.COMMISSION]: 'blue',
  [ContractCaseType.COOPERATION]: 'green',
  [ContractCaseType.EXTENSION]: 'orange',
  [ContractCaseType.SMALL_PURCHASE]: 'cyan',
} as const;

// 案件狀態
export enum ContractCaseStatus {
  PLANNED = 'planned', // 規劃中
  IN_PROGRESS = 'in_progress', // 執行中
  COMPLETED = 'completed', // 已完成
  SUSPENDED = 'suspended', // 暫停
  CANCELLED = 'cancelled', // 已取消
}

// 案件狀態標籤
export const CONTRACT_CASE_STATUS_LABELS = {
  [ContractCaseStatus.PLANNED]: '規劃中',
  [ContractCaseStatus.IN_PROGRESS]: '執行中',
  [ContractCaseStatus.COMPLETED]: '已完成',
  [ContractCaseStatus.SUSPENDED]: '暫停',
  [ContractCaseStatus.CANCELLED]: '已取消',
} as const;

// 案件狀態顏色
export const CONTRACT_CASE_STATUS_COLORS = {
  [ContractCaseStatus.PLANNED]: 'default',
  [ContractCaseStatus.IN_PROGRESS]: 'processing',
  [ContractCaseStatus.COMPLETED]: 'success',
  [ContractCaseStatus.SUSPENDED]: 'warning',
  [ContractCaseStatus.CANCELLED]: 'error',
} as const;

// 篩選條件
export interface ContractCaseFilter {
  search?: string;
  year?: string;
  case_type?: ContractCaseType;
  case_status?: ContractCaseStatus;
  client_unit?: string;
  responsible_staff?: string;
  partner_vendor?: string;
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

// 列表參數
export interface ContractCaseListParams {
  page?: number;
  limit?: number;
  filters?: ContractCaseFilter;
}

// 列表響應
export interface ContractCaseListResponse {
  items: ContractCase[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

// 視圖模式
export type ViewMode = 'board' | 'list';

// 看板項目
export interface BoardItem extends ContractCase {
  progress?: number; // 進度百分比
}
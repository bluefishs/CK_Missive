/**
 * ERP 費用報銷/帳本/財務彙總/電子發票 React Query Hooks
 *
 * Phase 4 前端整合：涵蓋 20 個後端 API 端點
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { expensesApi, ledgerApi, financialSummaryApi, einvoiceSyncApi } from '../../api/erp';
import { defaultQueryOptions } from '../../config/queryConfig';
import type {
  ExpenseInvoiceCreate,
  ExpenseInvoiceUpdate,
  ExpenseInvoiceQuery,
  ExpenseInvoiceRejectRequest,
  ExpenseInvoiceQRScanRequest,
  LedgerCreate,
  LedgerQuery,
  LedgerBalanceRequest,
  LedgerCategoryBreakdownRequest,
  AllProjectsSummaryRequest,
  CompanyOverviewRequest,
  MonthlyTrendRequest,
  BudgetRankingRequest,
  ExportExpensesRequest,
  ExportLedgerRequest,
  EInvoiceSyncRequest,
  EInvoiceSyncLogQuery,
  PendingReceiptQuery,
} from '../../types/erp';

// ============================================================================
// Query Keys
// ============================================================================

export const erpFinanceKeys = {
  expenses: {
    all: ['erp-expenses'] as const,
    lists: () => [...erpFinanceKeys.expenses.all, 'list'] as const,
    list: (filters: object) => [...erpFinanceKeys.expenses.lists(), filters] as const,
    details: () => [...erpFinanceKeys.expenses.all, 'detail'] as const,
    detail: (id: number) => [...erpFinanceKeys.expenses.details(), id] as const,
  },
  ledger: {
    all: ['erp-ledger'] as const,
    lists: () => [...erpFinanceKeys.ledger.all, 'list'] as const,
    list: (filters: object) => [...erpFinanceKeys.ledger.lists(), filters] as const,
    details: () => [...erpFinanceKeys.ledger.all, 'detail'] as const,
    detail: (id: number) => [...erpFinanceKeys.ledger.details(), id] as const,
    balance: (caseCode: string) => [...erpFinanceKeys.ledger.all, 'balance', caseCode] as const,
    categoryBreakdown: (params: object) => [...erpFinanceKeys.ledger.all, 'category-breakdown', params] as const,
  },
  financialSummary: {
    all: ['erp-financial-summary'] as const,
    project: (caseCode: string) => [...erpFinanceKeys.financialSummary.all, 'project', caseCode] as const,
    projects: (params?: object) => [...erpFinanceKeys.financialSummary.all, 'projects', params] as const,
    company: (params?: object) => [...erpFinanceKeys.financialSummary.all, 'company', params] as const,
    monthlyTrend: (params?: object) => [...erpFinanceKeys.financialSummary.all, 'monthly-trend', params] as const,
    budgetRanking: (params?: object) => [...erpFinanceKeys.financialSummary.all, 'budget-ranking', params] as const,
  },
  einvoiceSync: {
    all: ['erp-einvoice-sync'] as const,
    pendingList: (params?: object) => [...erpFinanceKeys.einvoiceSync.all, 'pending', params] as const,
    syncLogs: (params?: object) => [...erpFinanceKeys.einvoiceSync.all, 'logs', params] as const,
  },
};

// ============================================================================
// 費用報銷 Hooks
// ============================================================================

/** 費用發票列表 */
export const useExpenses = (params?: ExpenseInvoiceQuery) => {
  return useQuery({
    queryKey: erpFinanceKeys.expenses.list(params || {}),
    queryFn: () => expensesApi.list(params),
    ...defaultQueryOptions.list,
  });
};

/** 費用發票詳情 */
export const useExpenseDetail = (id: number | null | undefined) => {
  return useQuery({
    queryKey: erpFinanceKeys.expenses.detail(id ?? 0),
    queryFn: () => expensesApi.detail(id!),
    ...defaultQueryOptions.detail,
    enabled: !!id,
  });
};

/** 建立報銷發票 */
export const useCreateExpense = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ExpenseInvoiceCreate) => expensesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.expenses.all });
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.financialSummary.all });
    },
  });
};

/** 更新報銷發票 */
export const useUpdateExpense = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ExpenseInvoiceUpdate }) =>
      expensesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.expenses.all });
    },
  });
};

/** 審核通過 (approve → 自動寫入帳本) */
export const useApproveExpense = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => expensesApi.approve(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.expenses.all });
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.ledger.all });
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.financialSummary.all });
    },
  });
};

/** 駁回報銷 */
export const useRejectExpense = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ExpenseInvoiceRejectRequest) => expensesApi.reject(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.expenses.all });
    },
  });
};

/** QR Code 掃描建立 */
export const useQRScanExpense = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ExpenseInvoiceQRScanRequest) => expensesApi.qrScan(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.expenses.all });
    },
  });
};

/** OCR 辨識發票影像 */
export const useOCRParseExpense = () => {
  return useMutation({
    mutationFn: (file: File) => expensesApi.ocrParse(file),
  });
};

// ============================================================================
// 統一帳本 Hooks
// ============================================================================

/** 帳本列表 */
export const useLedger = (params?: LedgerQuery) => {
  return useQuery({
    queryKey: erpFinanceKeys.ledger.list(params || {}),
    queryFn: () => ledgerApi.list(params),
    ...defaultQueryOptions.list,
  });
};

/** 帳本詳情 */
export const useLedgerDetail = (id: number | null | undefined) => {
  return useQuery({
    queryKey: erpFinanceKeys.ledger.detail(id ?? 0),
    queryFn: () => ledgerApi.detail(id!),
    ...defaultQueryOptions.detail,
    enabled: !!id,
  });
};

/** 手動記帳 */
export const useCreateLedger = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: LedgerCreate) => ledgerApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.ledger.all });
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.financialSummary.all });
    },
  });
};

/** 刪除帳本記錄 (僅手動記帳) */
export const useDeleteLedger = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => ledgerApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.ledger.all });
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.financialSummary.all });
    },
  });
};

/** 專案收支餘額 */
export const useLedgerBalance = (caseCode: string | null | undefined) => {
  return useQuery({
    queryKey: erpFinanceKeys.ledger.balance(caseCode ?? ''),
    queryFn: () => ledgerApi.balance({ case_code: caseCode! } as LedgerBalanceRequest),
    ...defaultQueryOptions.detail,
    enabled: !!caseCode,
  });
};

/** 帳本分類拆解 */
export const useLedgerCategoryBreakdown = (params?: LedgerCategoryBreakdownRequest) => {
  return useQuery({
    queryKey: erpFinanceKeys.ledger.categoryBreakdown(params || {}),
    queryFn: () => ledgerApi.categoryBreakdown(params || {}),
    ...defaultQueryOptions.statistics,
  });
};

// ============================================================================
// 財務彙總 Hooks
// ============================================================================

/** 單一專案財務彙總 */
export const useProjectFinancialSummary = (caseCode: string | null | undefined) => {
  return useQuery({
    queryKey: erpFinanceKeys.financialSummary.project(caseCode ?? ''),
    queryFn: () => financialSummaryApi.project({ case_code: caseCode! }),
    ...defaultQueryOptions.statistics,
    enabled: !!caseCode,
  });
};

/** 所有專案財務一覽 */
export const useAllProjectsSummary = (params?: AllProjectsSummaryRequest) => {
  return useQuery({
    queryKey: erpFinanceKeys.financialSummary.projects(params),
    queryFn: () => financialSummaryApi.projects(params),
    ...defaultQueryOptions.list,
  });
};

/** 全公司財務總覽 */
export const useCompanyFinancialOverview = (params?: CompanyOverviewRequest) => {
  return useQuery({
    queryKey: erpFinanceKeys.financialSummary.company(params),
    queryFn: () => financialSummaryApi.company(params),
    ...defaultQueryOptions.statistics,
  });
};

/** 月度收支趨勢 */
export const useMonthlyTrend = (params?: MonthlyTrendRequest) => {
  return useQuery({
    queryKey: erpFinanceKeys.financialSummary.monthlyTrend(params),
    queryFn: () => financialSummaryApi.monthlyTrend(params),
    ...defaultQueryOptions.statistics,
  });
};

/** 預算使用率排行 */
export const useBudgetRanking = (params?: BudgetRankingRequest) => {
  return useQuery({
    queryKey: erpFinanceKeys.financialSummary.budgetRanking(params),
    queryFn: () => financialSummaryApi.budgetRanking(params),
    ...defaultQueryOptions.statistics,
  });
};

/** 匯出費用報銷 Excel */
export const useExportExpenses = () => {
  return useMutation({
    mutationFn: (params?: ExportExpensesRequest) => financialSummaryApi.exportExpenses(params),
    onSuccess: (blob) => {
      downloadBlob(blob, `expenses_${new Date().toISOString().slice(0, 10)}.xlsx`);
    },
  });
};

/** 匯出帳本 Excel */
export const useExportLedger = () => {
  return useMutation({
    mutationFn: (params?: ExportLedgerRequest) => financialSummaryApi.exportLedger(params),
    onSuccess: (blob) => {
      downloadBlob(blob, `ledger_${new Date().toISOString().slice(0, 10)}.xlsx`);
    },
  });
};

/** 下載 Blob 檔案輔助 */
function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ============================================================================
// 電子發票同步 Hooks
// ============================================================================

/** 手動觸發同步 */
export const useSyncEInvoice = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params?: EInvoiceSyncRequest) => einvoiceSyncApi.sync(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.expenses.all });
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.einvoiceSync.all });
    },
  });
};

/** 待核銷清單 */
export const useEInvoicePendingList = (params?: PendingReceiptQuery) => {
  return useQuery({
    queryKey: erpFinanceKeys.einvoiceSync.pendingList(params),
    queryFn: () => einvoiceSyncApi.pendingList(params),
    ...defaultQueryOptions.list,
  });
};

/** 上傳收據照片 (電子發票同步流程: pending_receipt → pending) */
export const useUploadReceipt = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ invoiceId, file, caseCode, category }: {
      invoiceId: number; file: File; caseCode?: string; category?: string;
    }) => einvoiceSyncApi.uploadReceipt(invoiceId, file, caseCode, category),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.expenses.all });
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.einvoiceSync.all });
    },
  });
};

/** 上傳收據影像至費用發票 (一般費用: 僅附加圖片，不變更狀態) */
export const useUploadExpenseReceipt = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ invoiceId, file }: { invoiceId: number; file: File }) =>
      expensesApi.uploadReceipt(invoiceId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.expenses.all });
    },
  });
};

/** 同步歷史記錄 */
export const useEInvoiceSyncLogs = (params?: EInvoiceSyncLogQuery) => {
  return useQuery({
    queryKey: erpFinanceKeys.einvoiceSync.syncLogs(params),
    queryFn: () => einvoiceSyncApi.syncLogs(params),
    ...defaultQueryOptions.list,
  });
};

/**
 * ERP 費用報銷/帳本/財務彙總/電子發票 React Query Hooks
 *
 * Phase 4 前端整合：涵蓋 20 個後端 API 端點
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { expensesApi, ledgerApi, financialSummaryApi, einvoiceSyncApi } from '../../api/erp';
import { apiClient } from '../../api/client';
import { ERP_ENDPOINTS } from '../../api/endpoints';
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
  AgingAnalysisRequest,
  InvoiceSummaryRequest,
  InvoiceSummaryItem,
  AccountListRequest,
  VendorAccountSummaryItem,
  VendorAccountDetail,
  ClientAccountSummaryItem,
  ClientAccountDetail,
  Asset,
  AssetLog,
  AssetStats,
  AssetListRequest,
  AssetLogCreateRequest,
  AssetBatchInventoryRequest,
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
    aging: (params?: object) => [...erpFinanceKeys.financialSummary.all, 'aging', params] as const,
  },
  einvoiceSync: {
    all: ['erp-einvoice-sync'] as const,
    pendingList: (params?: object) => [...erpFinanceKeys.einvoiceSync.all, 'pending', params] as const,
    syncLogs: (params?: object) => [...erpFinanceKeys.einvoiceSync.all, 'logs', params] as const,
  },
  vendorAccounts: {
    all: ['erp-vendor-accounts'] as const,
    summary: (params: object) => [...erpFinanceKeys.vendorAccounts.all, 'summary', params] as const,
    detail: (vendorId: number | null, year?: number) => [...erpFinanceKeys.vendorAccounts.all, 'detail', vendorId, year] as const,
  },
  clientAccounts: {
    all: ['erp-client-accounts'] as const,
    summary: (params: object) => [...erpFinanceKeys.clientAccounts.all, 'summary', params] as const,
    detail: (vendorId: number | null, year?: number) => [...erpFinanceKeys.clientAccounts.all, 'detail', vendorId, year] as const,
  },
  invoices: {
    all: ['erp-invoices'] as const,
    summary: (params: object) => ['erp-invoices', 'summary', params] as const,
  },
  assets: {
    all: ['erp-assets'] as const,
    lists: () => [...erpFinanceKeys.assets.all, 'list'] as const,
    list: (filters: object) => [...erpFinanceKeys.assets.lists(), filters] as const,
    details: () => [...erpFinanceKeys.assets.all, 'detail'] as const,
    detail: (id: number) => [...erpFinanceKeys.assets.details(), id] as const,
    stats: () => [...erpFinanceKeys.assets.all, 'stats'] as const,
    logs: (assetId: number | null, action?: string) => [...erpFinanceKeys.assets.all, 'logs', assetId, action] as const,
    detailFull: (id: number) => [...erpFinanceKeys.assets.all, 'detail-full', id] as const,
  },
};

// ============================================================================
// ERP Hub 總覽 Hooks
// ============================================================================

/** ERP 模組快速統計 (Hub 頁面用) */
export function useERPOverview() {
  return useQuery<Record<string, number>>({
    queryKey: ['erp-overview'],
    queryFn: async () => {
      const res = await apiClient.post<{ data: Record<string, number> }>(
        ERP_ENDPOINTS.FINANCIAL_SUMMARY_ERP_OVERVIEW, {}
      );
      return res.data ?? {};
    },
    staleTime: 60_000,
  });
}

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

/** 匯入費用報銷 Excel */
export function useImportExpenses() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiClient.postForm<{ data: { total: number; created: number; skipped: number; errors: Array<{ row: number; error: string }> } }>(
        ERP_ENDPOINTS.EXPENSES_IMPORT, formData
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: erpFinanceKeys.expenses.all });
    },
  });
}

/** 下載費用報銷匯入範本 Excel */
export function useDownloadExpenseTemplate() {
  return useMutation({
    mutationFn: async () => {
      const blob = await apiClient.postBlob(ERP_ENDPOINTS.EXPENSES_IMPORT_TEMPLATE);
      downloadBlob(blob, 'expense_import_template.xlsx');
    },
  });
}

/** 自動關聯電子發票 */
export function useAutoLinkEinvoice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiClient.post(ERP_ENDPOINTS.EXPENSES_AUTO_LINK_EINVOICE, { id }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: erpFinanceKeys.expenses.all });
    },
  });
}

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

/** 帳齡分析 */
export const useAgingAnalysis = (params: AgingAnalysisRequest) => {
  return useQuery({
    queryKey: erpFinanceKeys.financialSummary.aging(params),
    queryFn: () => financialSummaryApi.aging(params),
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

// ============================================================================
// 跨案件發票彙總 Hooks
// ============================================================================

/** 跨案件發票彙總 */
export function useInvoiceSummary(params: InvoiceSummaryRequest) {
  return useQuery<{ items: InvoiceSummaryItem[]; total: number }>({
    queryKey: erpFinanceKeys.invoices.summary(params),
    queryFn: async () => {
      const res = await apiClient.post<{ data: { items: InvoiceSummaryItem[]; total: number } }>(
        ERP_ENDPOINTS.INVOICES_SUMMARY, params
      );
      return res.data ?? { items: [], total: 0 };
    },
    ...defaultQueryOptions.list,
  });
}

// ============================================================================
// 廠商帳款 Hooks
// ============================================================================

/** 廠商帳款彙總 */
export function useVendorAccountSummary(params: AccountListRequest) {
  return useQuery<{ items: VendorAccountSummaryItem[]; total: number }>({
    queryKey: erpFinanceKeys.vendorAccounts.summary(params),
    queryFn: async () => {
      const res = await apiClient.post<{ data: { items: VendorAccountSummaryItem[]; total: number } }>(
        ERP_ENDPOINTS.VENDOR_ACCOUNTS_SUMMARY, params
      );
      return res.data ?? { items: [], total: 0 };
    },
    ...defaultQueryOptions.statistics,
  });
}

/** 廠商帳款明細 */
export function useVendorAccountDetail(vendorId: number | null, year?: number) {
  return useQuery<VendorAccountDetail | null>({
    queryKey: erpFinanceKeys.vendorAccounts.detail(vendorId, year),
    queryFn: async () => {
      const res = await apiClient.post<{ data: VendorAccountDetail | null }>(
        ERP_ENDPOINTS.VENDOR_ACCOUNTS_DETAIL, { vendor_id: vendorId, year }
      );
      return res.data ?? null;
    },
    enabled: !!vendorId,
    ...defaultQueryOptions.statistics,
  });
}

// ============================================================================
// 委託單位帳款 Hooks
// ============================================================================

/** 委託單位帳款彙總 */
export function useClientAccountSummary(params: AccountListRequest) {
  return useQuery<{ items: ClientAccountSummaryItem[]; total: number }>({
    queryKey: erpFinanceKeys.clientAccounts.summary(params),
    queryFn: async () => {
      const res = await apiClient.post<{ data: { items: ClientAccountSummaryItem[]; total: number } }>(
        ERP_ENDPOINTS.CLIENT_ACCOUNTS_SUMMARY, params
      );
      return res.data ?? { items: [], total: 0 };
    },
    ...defaultQueryOptions.statistics,
  });
}

/** 委託單位帳款明細 */
export function useClientAccountDetail(vendorId: number | null, year?: number) {
  return useQuery<ClientAccountDetail | null>({
    queryKey: erpFinanceKeys.clientAccounts.detail(vendorId, year),
    queryFn: async () => {
      const res = await apiClient.post<{ data: ClientAccountDetail | null }>(
        ERP_ENDPOINTS.CLIENT_ACCOUNTS_DETAIL, { vendor_id: vendorId, year }
      );
      return res.data ?? null;
    },
    enabled: !!vendorId,
    ...defaultQueryOptions.statistics,
  });
}

// ============================================================================
// 資產管理 Hooks
// ============================================================================

/** 資產列表 */
export function useAssetList(params: AssetListRequest) {
  return useQuery<{ items: Asset[]; total: number }>({
    queryKey: erpFinanceKeys.assets.list(params),
    queryFn: async () => {
      const res = await apiClient.post<{ data: { items: Asset[]; total: number } }>(
        ERP_ENDPOINTS.ASSETS_LIST, params
      );
      return res.data ?? { items: [], total: 0 };
    },
    ...defaultQueryOptions.list,
  });
}

/** 資產詳情 */
export function useAssetDetail(assetId: number | null) {
  return useQuery<Asset | null>({
    queryKey: erpFinanceKeys.assets.detail(assetId ?? 0),
    queryFn: async () => {
      const res = await apiClient.post<{ data: Asset | null }>(
        ERP_ENDPOINTS.ASSETS_DETAIL, { id: assetId }
      );
      return res.data ?? null;
    },
    enabled: !!assetId,
    ...defaultQueryOptions.detail,
  });
}

/** 資產統計 */
export function useAssetStats() {
  return useQuery<AssetStats>({
    queryKey: erpFinanceKeys.assets.stats(),
    queryFn: async () => {
      const res = await apiClient.post<{ data: AssetStats }>(
        ERP_ENDPOINTS.ASSETS_STATS, {}
      );
      return res.data ?? {} as AssetStats;
    },
    ...defaultQueryOptions.statistics,
  });
}

/** 資產異動記錄列表 */
export function useAssetLogs(assetId: number | null, action?: string) {
  return useQuery<{ items: AssetLog[]; total: number }>({
    queryKey: erpFinanceKeys.assets.logs(assetId, action),
    queryFn: async () => {
      const res = await apiClient.post<{ data: { items: AssetLog[]; total: number } }>(
        ERP_ENDPOINTS.ASSET_LOGS_LIST, { asset_id: assetId, action }
      );
      return res.data ?? { items: [], total: 0 };
    },
    enabled: !!assetId,
    ...defaultQueryOptions.list,
  });
}

/** 建立資產 */
export function useCreateAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Asset>) =>
      apiClient.post(ERP_ENDPOINTS.ASSETS_CREATE, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.assets.all });
    },
  });
}

/** 更新資產 */
export function useUpdateAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { id: number } & Partial<Asset>) =>
      apiClient.post(ERP_ENDPOINTS.ASSETS_UPDATE, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.assets.all });
    },
  });
}

/** 刪除資產 */
export function useDeleteAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiClient.post(ERP_ENDPOINTS.ASSETS_DELETE, { id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.assets.all });
    },
  });
}

/** 資產完整詳情 (含關聯發票+案件) */
export interface AssetDetailFull {
  asset: Asset;
  invoice: {
    id: number;
    inv_num: string;
    date: string | null;
    amount: string;
    seller_ban: string | null;
    category: string | null;
    status: string;
    source: string;
  } | null;
  case_quotation: {
    id: number;
    case_code: string;
    case_name: string | null;
    total_price: string;
    status: string;
  } | null;
}

export function useAssetDetailFull(assetId: number | null) {
  return useQuery<AssetDetailFull | null>({
    queryKey: erpFinanceKeys.assets.detailFull(assetId ?? 0),
    queryFn: async () => {
      const res = await apiClient.post<{ data: AssetDetailFull | null }>(
        ERP_ENDPOINTS.ASSETS_DETAIL_FULL, { id: assetId }
      );
      return res.data ?? null;
    },
    enabled: !!assetId,
    ...defaultQueryOptions.detail,
  });
}

/** 匯出資產清單 Excel */
export function useExportAssets() {
  return useMutation({
    mutationFn: async () => {
      const blob = await apiClient.postBlob(ERP_ENDPOINTS.ASSETS_EXPORT);
      downloadBlob(blob, `assets_${new Date().toISOString().slice(0, 10)}.xlsx`);
    },
  });
}

/** 依發票查詢關聯資產 */
export function useAssetsByInvoice(expenseInvoiceId: number | null) {
  return useQuery<Asset[]>({
    queryKey: [...erpFinanceKeys.assets.all, 'by-invoice', expenseInvoiceId],
    queryFn: async () => {
      const res = await apiClient.post<{ data: Asset[] }>(
        ERP_ENDPOINTS.ASSETS_BY_INVOICE, { id: expenseInvoiceId }
      );
      return res.data ?? [];
    },
    enabled: !!expenseInvoiceId,
  });
}

/** 批次盤點 */
export function useBatchInventory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AssetBatchInventoryRequest) =>
      apiClient.post(ERP_ENDPOINTS.ASSETS_BATCH_INVENTORY, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.assets.all });
    },
  });
}

/** 匯出盤點報表 Excel */
export function useExportInventory() {
  return useMutation({
    mutationFn: async () => {
      const blob = await apiClient.postBlob(ERP_ENDPOINTS.ASSETS_EXPORT_INVENTORY);
      downloadBlob(blob, `inventory_${new Date().toISOString().slice(0, 10)}.xlsx`);
    },
  });
}

/** 匯入資產清單 Excel */
export function useImportAssets() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiClient.postForm<{ data: { total_rows: number; created: number; updated: number; errors: Array<{ row: number; error: string }> } }>(
        ERP_ENDPOINTS.ASSETS_IMPORT, formData
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.assets.all });
    },
  });
}

/** 下載資產匯入範本 Excel */
export function useDownloadAssetTemplate() {
  return useMutation({
    mutationFn: async () => {
      const blob = await apiClient.postBlob(ERP_ENDPOINTS.ASSETS_IMPORT_TEMPLATE);
      downloadBlob(blob, 'asset_import_template.xlsx');
    },
  });
}

/** 建立資產異動記錄 */
export function useCreateAssetLog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AssetLogCreateRequest) =>
      apiClient.post(ERP_ENDPOINTS.ASSET_LOGS_CREATE, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpFinanceKeys.assets.all });
    },
  });
}

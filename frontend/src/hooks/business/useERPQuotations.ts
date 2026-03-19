/**
 * ERP 報價/成本管理 React Query Hooks
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { erpQuotationsApi, erpInvoicesApi, erpBillingsApi, erpVendorPayablesApi } from '../../api/erp';
import { defaultQueryOptions } from '../../config/queryConfig';
import type {
  ERPQuotationCreate, ERPQuotationUpdate, ERPQuotationListParams,
  ERPInvoiceCreate, ERPInvoiceUpdate,
  ERPBillingCreate, ERPBillingUpdate,
  ERPVendorPayableCreate, ERPVendorPayableUpdate,
} from '../../types/erp';

// Query keys
const erpKeys = {
  quotations: {
    all: ['erp-quotations'] as const,
    lists: () => [...erpKeys.quotations.all, 'list'] as const,
    list: (filters: object) => [...erpKeys.quotations.lists(), filters] as const,
    details: () => [...erpKeys.quotations.all, 'detail'] as const,
    detail: (id: number) => [...erpKeys.quotations.details(), id] as const,
    profitSummary: (params?: object) => ['erp-quotations', 'profit-summary', params] as const,
  },
  invoices: {
    all: ['erp-invoices'] as const,
    byQuotation: (quotationId: number) => ['erp-invoices', quotationId] as const,
  },
  billings: {
    all: ['erp-billings'] as const,
    byQuotation: (quotationId: number) => ['erp-billings', quotationId] as const,
  },
  vendorPayables: {
    all: ['erp-vendor-payables'] as const,
    byQuotation: (quotationId: number) => ['erp-vendor-payables', quotationId] as const,
  },
};

// ============================================================================
// 報價 Hooks
// ============================================================================

/** 取得報價列表 */
export const useERPQuotations = (params?: ERPQuotationListParams) => {
  return useQuery({
    queryKey: erpKeys.quotations.list(params || {}),
    queryFn: () => erpQuotationsApi.list(params),
    ...defaultQueryOptions.list,
  });
};

/** 取得報價詳情 */
export const useERPQuotation = (id: number | null | undefined) => {
  return useQuery({
    queryKey: erpKeys.quotations.detail(id ?? 0),
    queryFn: () => erpQuotationsApi.detail(id!),
    ...defaultQueryOptions.detail,
    enabled: !!id,
  });
};

/** 取得損益摘要 */
export const useERPProfitSummary = (params?: { year?: number }) => {
  return useQuery({
    queryKey: erpKeys.quotations.profitSummary(params),
    queryFn: () => erpQuotationsApi.profitSummary(params),
    ...defaultQueryOptions.statistics,
  });
};

/** 取得損益趨勢 (多年度) */
export const useERPProfitTrend = () => {
  return useQuery({
    queryKey: ['erp-quotations', 'profit-trend'] as const,
    queryFn: () => erpQuotationsApi.profitTrend(),
    ...defaultQueryOptions.statistics,
  });
};

/** 建立報價 */
export const useCreateERPQuotation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ERPQuotationCreate) => erpQuotationsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpKeys.quotations.all });
    },
  });
};

/** 更新報價 */
export const useUpdateERPQuotation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ERPQuotationUpdate }) =>
      erpQuotationsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpKeys.quotations.all });
    },
  });
};

/** 刪除報價 */
export const useDeleteERPQuotation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => erpQuotationsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpKeys.quotations.all });
    },
  });
};

// ============================================================================
// 發票 Hooks
// ============================================================================

/** 取得發票列表 (by quotation) */
export const useERPInvoices = (quotationId: number | null | undefined) => {
  return useQuery({
    queryKey: erpKeys.invoices.byQuotation(quotationId ?? 0),
    queryFn: () => erpInvoicesApi.list(quotationId!),
    ...defaultQueryOptions.detail,
    enabled: !!quotationId,
  });
};

/** 建立發票 */
export const useCreateERPInvoice = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ERPInvoiceCreate) => erpInvoicesApi.create(data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: erpKeys.invoices.byQuotation(variables.erp_quotation_id) });
      queryClient.invalidateQueries({ queryKey: erpKeys.quotations.all });
    },
  });
};

/** 更新發票 */
export const useUpdateERPInvoice = (quotationId: number) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ERPInvoiceUpdate }) =>
      erpInvoicesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpKeys.invoices.byQuotation(quotationId) });
      queryClient.invalidateQueries({ queryKey: erpKeys.quotations.all });
    },
  });
};

/** 刪除發票 */
export const useDeleteERPInvoice = (quotationId: number) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => erpInvoicesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpKeys.invoices.byQuotation(quotationId) });
      queryClient.invalidateQueries({ queryKey: erpKeys.quotations.all });
    },
  });
};

// ============================================================================
// 請款 Hooks
// ============================================================================

/** 取得請款列表 (by quotation) */
export const useERPBillings = (quotationId: number | null | undefined) => {
  return useQuery({
    queryKey: erpKeys.billings.byQuotation(quotationId ?? 0),
    queryFn: () => erpBillingsApi.list(quotationId!),
    ...defaultQueryOptions.detail,
    enabled: !!quotationId,
  });
};

/** 建立請款 */
export const useCreateERPBilling = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ERPBillingCreate) => erpBillingsApi.create(data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: erpKeys.billings.byQuotation(variables.erp_quotation_id) });
      queryClient.invalidateQueries({ queryKey: erpKeys.quotations.all });
    },
  });
};

/** 更新請款 */
export const useUpdateERPBilling = (quotationId: number) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ERPBillingUpdate }) =>
      erpBillingsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpKeys.billings.byQuotation(quotationId) });
      queryClient.invalidateQueries({ queryKey: erpKeys.quotations.all });
    },
  });
};

/** 刪除請款 */
export const useDeleteERPBilling = (quotationId: number) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => erpBillingsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpKeys.billings.byQuotation(quotationId) });
      queryClient.invalidateQueries({ queryKey: erpKeys.quotations.all });
    },
  });
};

// ============================================================================
// 廠商應付 Hooks
// ============================================================================

/** 取得廠商應付列表 (by quotation) */
export const useERPVendorPayables = (quotationId: number | null | undefined) => {
  return useQuery({
    queryKey: erpKeys.vendorPayables.byQuotation(quotationId ?? 0),
    queryFn: () => erpVendorPayablesApi.list(quotationId!),
    ...defaultQueryOptions.detail,
    enabled: !!quotationId,
  });
};

/** 建立廠商應付 */
export const useCreateERPVendorPayable = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ERPVendorPayableCreate) => erpVendorPayablesApi.create(data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: erpKeys.vendorPayables.byQuotation(variables.erp_quotation_id) });
      queryClient.invalidateQueries({ queryKey: erpKeys.quotations.all });
    },
  });
};

/** 更新廠商應付 */
export const useUpdateERPVendorPayable = (quotationId: number) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ERPVendorPayableUpdate }) =>
      erpVendorPayablesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpKeys.vendorPayables.byQuotation(quotationId) });
      queryClient.invalidateQueries({ queryKey: erpKeys.quotations.all });
    },
  });
};

/** 刪除廠商應付 */
export const useDeleteERPVendorPayable = (quotationId: number) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => erpVendorPayablesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: erpKeys.vendorPayables.byQuotation(quotationId) });
      queryClient.invalidateQueries({ queryKey: erpKeys.quotations.all });
    },
  });
};

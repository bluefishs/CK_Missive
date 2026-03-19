/**
 * ERP 財務管理 API 服務
 */
import { apiClient } from './client';
import type { PaginatedResponse, SuccessResponse } from './types';
import type { ERPQuotation, ERPQuotationCreate, ERPQuotationUpdate, ERPProfitSummary, ERPProfitTrendItem, ERPVendorPayable } from '../types/api';
import type { ERPQuotationListParams } from '../types/erp';
import { ERP_ENDPOINTS } from './endpoints';

export const erpQuotationsApi = {
  async list(params?: ERPQuotationListParams): Promise<PaginatedResponse<ERPQuotation>> {
    return apiClient.postList<ERPQuotation>(ERP_ENDPOINTS.QUOTATIONS_LIST, params || {});
  },

  async detail(id: number): Promise<SuccessResponse<ERPQuotation>> {
    return apiClient.post<SuccessResponse<ERPQuotation>>(ERP_ENDPOINTS.QUOTATIONS_DETAIL, { id });
  },

  async create(data: ERPQuotationCreate): Promise<SuccessResponse<ERPQuotation>> {
    return apiClient.post<SuccessResponse<ERPQuotation>>(ERP_ENDPOINTS.QUOTATIONS_CREATE, data);
  },

  async update(id: number, data: ERPQuotationUpdate): Promise<SuccessResponse<ERPQuotation>> {
    return apiClient.post<SuccessResponse<ERPQuotation>>(ERP_ENDPOINTS.QUOTATIONS_UPDATE, { id, ...data });
  },

  async remove(id: number): Promise<SuccessResponse<null>> {
    return apiClient.post<SuccessResponse<null>>(ERP_ENDPOINTS.QUOTATIONS_DELETE, { id });
  },

  async profitSummary(): Promise<SuccessResponse<ERPProfitSummary>> {
    return apiClient.post<SuccessResponse<ERPProfitSummary>>(ERP_ENDPOINTS.PROFIT_SUMMARY, {});
  },

  async profitTrend(): Promise<SuccessResponse<ERPProfitTrendItem[]>> {
    return apiClient.post<SuccessResponse<ERPProfitTrendItem[]>>(ERP_ENDPOINTS.PROFIT_TREND, {});
  },

  async vendorPayables(erpQuotationId: number): Promise<SuccessResponse<ERPVendorPayable[]>> {
    return apiClient.post<SuccessResponse<ERPVendorPayable[]>>(ERP_ENDPOINTS.VENDOR_PAYABLES_LIST, { erp_quotation_id: erpQuotationId });
  },
};

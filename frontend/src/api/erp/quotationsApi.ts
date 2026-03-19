/**
 * ERP 報價/成本主檔 API 服務
 */

import { apiClient } from '../client';
import type { PaginatedResponse, SuccessResponse, DeleteResponse } from '../types';
import type {
  ERPQuotation,
  ERPQuotationCreate,
  ERPQuotationUpdate,
  ERPQuotationListParams,
  ERPProfitSummary,
  ERPProfitTrendItem,
} from '../../types/erp';
import { ERP_ENDPOINTS } from '../endpoints';

export const erpQuotationsApi = {
  /** 取得報價列表 */
  async list(params?: ERPQuotationListParams): Promise<PaginatedResponse<ERPQuotation>> {
    const queryParams: Record<string, unknown> = {
      page: params?.page ?? 1,
      limit: params?.limit ?? 20,
      sort_by: params?.sort_by ?? 'created_at',
      sort_order: params?.sort_order ?? 'desc',
    };
    if (params?.search) queryParams.search = params.search;
    if (params?.year) queryParams.year = params.year;
    if (params?.status) queryParams.status = params.status;
    if (params?.case_code) queryParams.case_code = params.case_code;

    return await apiClient.postList<ERPQuotation>(ERP_ENDPOINTS.QUOTATIONS_LIST, queryParams);
  },

  /** 取得報價詳情 */
  async detail(id: number): Promise<ERPQuotation> {
    const response = await apiClient.post<SuccessResponse<ERPQuotation>>(
      ERP_ENDPOINTS.QUOTATIONS_DETAIL,
      { id }
    );
    return response.data!;
  },

  /** 建立報價 */
  async create(data: ERPQuotationCreate): Promise<ERPQuotation> {
    const response = await apiClient.post<SuccessResponse<ERPQuotation>>(
      ERP_ENDPOINTS.QUOTATIONS_CREATE,
      data
    );
    return response.data!;
  },

  /** 更新報價 */
  async update(id: number, data: ERPQuotationUpdate): Promise<ERPQuotation> {
    const response = await apiClient.post<SuccessResponse<ERPQuotation>>(
      ERP_ENDPOINTS.QUOTATIONS_UPDATE,
      { id, data }
    );
    return response.data!;
  },

  /** 刪除報價 */
  async delete(id: number): Promise<DeleteResponse> {
    return await apiClient.post<DeleteResponse>(ERP_ENDPOINTS.QUOTATIONS_DELETE, { id });
  },

  /** 取得損益摘要 */
  async profitSummary(params?: { year?: number }): Promise<ERPProfitSummary> {
    const response = await apiClient.post<SuccessResponse<ERPProfitSummary>>(
      ERP_ENDPOINTS.PROFIT_SUMMARY,
      params ?? {}
    );
    return response.data!;
  },

  /** 取得損益趨勢 */
  async profitTrend(): Promise<ERPProfitTrendItem[]> {
    const response = await apiClient.post<SuccessResponse<ERPProfitTrendItem[]>>(
      ERP_ENDPOINTS.PROFIT_TREND,
      {}
    );
    return response.data!;
  },

  /** 匯出 CSV */
  async exportCsv(params?: { year?: number }): Promise<Blob> {
    return apiClient.postBlob(ERP_ENDPOINTS.EXPORT, params ?? {});
  },

  /** 產生案號 */
  async generateCode(params: { year: number; category?: string }): Promise<string> {
    const response = await apiClient.post<SuccessResponse<{ case_code: string }>>(
      ERP_ENDPOINTS.GENERATE_CODE,
      { year: params.year, category: params.category ?? '01' }
    );
    return response.data!.case_code;
  },
};

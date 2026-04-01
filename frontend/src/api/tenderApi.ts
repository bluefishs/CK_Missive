/**
 * 標案檢索 API
 */
import { apiClient } from './client';
import { TENDER_ENDPOINTS } from './endpoints';
import type { SuccessResponse } from '../types';
import type {
  TenderSearchResult,
  TenderDetail,
  TenderRecommendResult,
  TenderSearchParams,
} from '../types/tender';

export const tenderApi = {
  /** 搜尋標案 */
  async search(params: TenderSearchParams): Promise<TenderSearchResult> {
    const res = await apiClient.post<SuccessResponse<TenderSearchResult>>(
      TENDER_ENDPOINTS.SEARCH, params,
    );
    return res.data!;
  },

  /** 標案詳情 */
  async getDetail(unitId: string, jobNumber: string): Promise<TenderDetail | null> {
    const res = await apiClient.post<SuccessResponse<TenderDetail | null>>(
      TENDER_ENDPOINTS.DETAIL, { unit_id: unitId, job_number: jobNumber },
    );
    return res.data ?? null;
  },

  /** 廠商搜尋 */
  async searchByCompany(companyName: string, page = 1): Promise<TenderSearchResult> {
    const res = await apiClient.post<SuccessResponse<TenderSearchResult>>(
      TENDER_ENDPOINTS.SEARCH_COMPANY, { company_name: companyName, page },
    );
    return res.data!;
  },

  /** 智能推薦 */
  async recommend(keywords?: string[]): Promise<TenderRecommendResult> {
    const res = await apiClient.post<SuccessResponse<TenderRecommendResult>>(
      TENDER_ENDPOINTS.RECOMMEND, { keywords },
    );
    return res.data!;
  },

  /** 從標案建立 PM Case */
  async createCase(params: {
    unit_id: string; job_number: string; title: string;
    unit_name?: string; budget?: string; category?: string;
  }): Promise<{ case_code: string; pm_case_id: number; quotation_id: number; message: string }> {
    const res = await apiClient.post<SuccessResponse<{ case_code: string; pm_case_id: number; quotation_id: number; message: string }>>(
      TENDER_ENDPOINTS.CREATE_CASE, params,
    );
    return res.data!;
  },
};

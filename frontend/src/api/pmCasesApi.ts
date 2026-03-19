/**
 * PM 專案管理 API 服務
 */
import { apiClient } from './client';
import type { PaginatedResponse, SuccessResponse } from './types';
import type { PMCase, PMCaseCreate, PMCaseUpdate, PMCaseSummary, PMYearlyTrendItem, PMCrossLookup } from '../types/api';
import type { PMCaseListParams } from '../types/pm';
import { PM_ENDPOINTS } from './endpoints';

export const pmCasesApi = {
  async list(params?: PMCaseListParams): Promise<PaginatedResponse<PMCase>> {
    return apiClient.postList<PMCase>(PM_ENDPOINTS.CASES_LIST, params || {});
  },

  async detail(id: number): Promise<SuccessResponse<PMCase>> {
    return apiClient.post<SuccessResponse<PMCase>>(PM_ENDPOINTS.CASES_DETAIL, { id });
  },

  async create(data: PMCaseCreate): Promise<SuccessResponse<PMCase>> {
    return apiClient.post<SuccessResponse<PMCase>>(PM_ENDPOINTS.CASES_CREATE, data);
  },

  async update(id: number, data: PMCaseUpdate): Promise<SuccessResponse<PMCase>> {
    return apiClient.post<SuccessResponse<PMCase>>(PM_ENDPOINTS.CASES_UPDATE, { id, ...data });
  },

  async remove(id: number): Promise<SuccessResponse<null>> {
    return apiClient.post<SuccessResponse<null>>(PM_ENDPOINTS.CASES_DELETE, { id });
  },

  async summary(): Promise<SuccessResponse<PMCaseSummary>> {
    return apiClient.post<SuccessResponse<PMCaseSummary>>(PM_ENDPOINTS.CASES_SUMMARY, {});
  },

  async yearlyTrend(): Promise<SuccessResponse<PMYearlyTrendItem[]>> {
    return apiClient.post<SuccessResponse<PMYearlyTrendItem[]>>(PM_ENDPOINTS.YEARLY_TREND, {});
  },

  async crossLookup(caseCode: string): Promise<SuccessResponse<PMCrossLookup>> {
    return apiClient.post<SuccessResponse<PMCrossLookup>>(PM_ENDPOINTS.CROSS_LOOKUP, { case_code: caseCode });
  },
};

/**
 * PM 案件管理 API 服務
 */

import { apiClient } from '../client';
import type { PaginatedResponse, SuccessResponse, DeleteResponse } from '../types';
import type {
  PMCase,
  PMCaseCreate,
  PMCaseUpdate,
  PMCaseListParams,
  PMCaseSummary,
  PMLinkedDocument,
  PMYearlyTrendItem,
  CrossModuleLookupResult,
} from '../../types/pm';
import { PM_ENDPOINTS } from '../endpoints';

export const pmCasesApi = {
  /** 取得案件列表 */
  async list(params?: PMCaseListParams): Promise<PaginatedResponse<PMCase>> {
    const queryParams: Record<string, unknown> = {
      page: params?.page ?? 1,
      limit: params?.limit ?? 20,
      sort_by: params?.sort_by ?? 'created_at',
      sort_order: params?.sort_order ?? 'desc',
    };
    if (params?.search) queryParams.search = params.search;
    if (params?.year) queryParams.year = params.year;
    if (params?.status) queryParams.status = params.status;
    if (params?.category) queryParams.category = params.category;
    if (params?.client_name) queryParams.client_name = params.client_name;

    return await apiClient.postList<PMCase>(PM_ENDPOINTS.CASES_LIST, queryParams);
  },

  /** 取得案件詳情 */
  async detail(id: number): Promise<PMCase> {
    const response = await apiClient.post<SuccessResponse<PMCase>>(
      PM_ENDPOINTS.CASES_DETAIL,
      { id }
    );
    return response.data!;
  },

  /** 建立案件 */
  async create(data: PMCaseCreate): Promise<PMCase> {
    const response = await apiClient.post<SuccessResponse<PMCase>>(
      PM_ENDPOINTS.CASES_CREATE,
      data
    );
    return response.data!;
  },

  /** 更新案件 */
  async update(id: number, data: PMCaseUpdate): Promise<PMCase> {
    const response = await apiClient.post<SuccessResponse<PMCase>>(
      PM_ENDPOINTS.CASES_UPDATE,
      { id, data }
    );
    return response.data!;
  },

  /** 刪除案件 */
  async delete(id: number): Promise<DeleteResponse> {
    return await apiClient.post<DeleteResponse>(PM_ENDPOINTS.CASES_DELETE, { id });
  },

  /** 取得案件統計摘要 */
  async summary(params?: { year?: number }): Promise<PMCaseSummary> {
    const response = await apiClient.post<SuccessResponse<PMCaseSummary>>(
      PM_ENDPOINTS.CASES_SUMMARY,
      params ?? {}
    );
    return response.data!;
  },

  /** 產生案號 */
  async generateCode(params: { year: number; category?: string }): Promise<string> {
    const response = await apiClient.post<SuccessResponse<{ case_code: string }>>(
      PM_ENDPOINTS.GENERATE_CODE,
      { year: params.year, category: params.category ?? '01' }
    );
    return response.data!.case_code;
  },

  /** 重新計算進度 (根據里程碑完成率) */
  async recalculateProgress(id: number): Promise<number> {
    const response = await apiClient.post<SuccessResponse<{ progress: number }>>(
      PM_ENDPOINTS.RECALCULATE_PROGRESS,
      { id }
    );
    return response.data!.progress;
  },

  /** 取得案件甘特圖 (Mermaid Gantt) */
  async gantt(id: number): Promise<string> {
    const response = await apiClient.post<SuccessResponse<{ gantt_mermaid: string }>>(
      PM_ENDPOINTS.GANTT,
      { id }
    );
    return response.data!.gantt_mermaid;
  },

  /** 案號關聯公文查詢 */
  async linkedDocuments(caseCode: string, limit?: number): Promise<PMLinkedDocument[]> {
    const response = await apiClient.post<SuccessResponse<PMLinkedDocument[]>>(
      PM_ENDPOINTS.LINKED_DOCUMENTS,
      { case_code: caseCode, limit: limit ?? 20 }
    );
    return response.data!;
  },

  /** 匯出 CSV */
  async exportCsv(params?: { year?: number }): Promise<Blob> {
    return apiClient.postBlob(PM_ENDPOINTS.EXPORT, params ?? {});
  },

  /** 多年度案件趨勢 */
  async yearlyTrend(): Promise<PMYearlyTrendItem[]> {
    const response = await apiClient.post<SuccessResponse<PMYearlyTrendItem[]>>(
      PM_ENDPOINTS.YEARLY_TREND,
      {}
    );
    return response.data!;
  },

  /** 跨模組案號查詢 */
  async crossLookup(caseCode: string): Promise<CrossModuleLookupResult> {
    const response = await apiClient.post<SuccessResponse<CrossModuleLookupResult>>(
      PM_ENDPOINTS.CROSS_LOOKUP,
      { case_code: caseCode }
    );
    return response.data!;
  },
};

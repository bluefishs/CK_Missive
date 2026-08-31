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
    // ⚠️ 2026-08-31：這裡**必須用 `!== undefined`，不能用 truthy 判斷**。
    //
    // 這個參數的有效值就是 `false`（收斂範圍＝不列已成案），而
    // `if (params?.include_converted)` 會把 `false` 當成「沒給」丟掉 ⇒
    // 後端收到空的 ⇒ 用預設 `true` ⇒ 列表回全部。
    //
    // owner 2026-08-31 回報「/pm/cases 為何還有 72 筆已承攬」正是這個：
    // 型別、hook、頁面、後端四層都改好了，**而這一層的手寫白名單沒有複製它**，
    // 於是那個 false 從來沒有離開過瀏覽器。後端量出來列表與卡片完全一致
    // （四種組合都對）—— 因為兩邊收到的都是 `true`，一致地錯。
    //
    // ⇒ 新增查詢參數時，這個白名單是**第五層**，很容易漏。
    if (params?.include_converted !== undefined) {
      queryParams.include_converted = params.include_converted;
    }

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

  /** 更新並回傳完整回應 —— 後端把「自動成案未完成」寫在 message 裡，
   *  只回 data 的 update() 會把它丟掉（M1，2026-08-29）。編輯表單要用這支。 */
  async updateWithMessage(
    id: number, data: PMCaseUpdate,
  ): Promise<{ data: PMCase; message?: string }> {
    const response = await apiClient.post<SuccessResponse<PMCase>>(
      PM_ENDPOINTS.CASES_UPDATE,
      { id, data }
    );
    return { data: response.data!, message: response.message };
  },

  /** 刪除案件 */
  async delete(id: number): Promise<DeleteResponse> {
    return await apiClient.post<DeleteResponse>(PM_ENDPOINTS.CASES_DELETE, { id });
  },

  /** 取得案件統計摘要 */
  // `include_converted` 必須在型別裡（2026-08-31）。它原本不在，而呼叫端有傳 ——
  // TypeScript 對「變數傳給較窄的參數型別」不做多餘屬性檢查，所以編譯通過、
  // 執行時因為 `params ?? {}` 也真的送出去了。**能動，但沒有人在保證它會繼續能動。**
  // 這就是為什麼摘要（卡片）是對的而列表是錯的：兩條路徑的參數處理各寫一套。
  async summary(params?: { year?: number; include_converted?: boolean }): Promise<PMCaseSummary> {
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

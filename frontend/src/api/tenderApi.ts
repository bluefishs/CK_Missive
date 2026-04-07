/**
 * 標案檢索 API
 */
import { apiClient } from './client';
import { TENDER_ENDPOINTS } from './endpoints';
import type { SuccessResponse } from '../types';
import type {
  TenderSearchResult,
  TenderDetail,
  TenderRecord,
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

  /** 標案完整戰情 (詳情+戰情室+機關生態) */
  async getDetailFull(unitId: string, jobNumber: string): Promise<{
    detail: TenderDetail | null;
    battle_room: { similar_tenders?: Array<{ title: string; date: string; unit_name: string; winner_names?: string[] }>; competitors?: Array<{ name: string; count: number; win_rate?: number }> };
    org_tenders: TenderRecord[];
    org_total: number;
  } | null> {
    const res = await apiClient.post<SuccessResponse<{
      detail: TenderDetail | null;
      battle_room: { similar_tenders?: Array<{ title: string; date: string; unit_name: string; winner_names?: string[] }>; competitors?: Array<{ name: string; count: number; win_rate?: number }> };
      org_tenders: TenderRecord[];
      org_total: number;
    } | null>>(
      TENDER_ENDPOINTS.DETAIL_FULL, { unit_id: unitId, job_number: jobNumber },
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

  // ========== 訂閱 ==========

  /** 標案知識圖譜 */
  async getGraph(query: string, maxTenders = 20): Promise<{
    query: string;
    nodes: Array<{ id: string; name: string; type: string; category?: string; date?: string }>;
    edges: Array<{ source: string; target: string; relation: string }>;
    stats: { tenders: number; agencies: number; companies: number; edges: number };
  }> {
    const res = await apiClient.post<SuccessResponse<{
      query: string;
      nodes: Array<{ id: string; name: string; type: string; category?: string; date?: string }>;
      edges: Array<{ source: string; target: string; relation: string }>;
      stats: { tenders: number; agencies: number; companies: number; edges: number };
    }>>(TENDER_ENDPOINTS.GRAPH, { query, max_tenders: maxTenders });
    return res.data!;
  },

  /** 同機關標案 (用搜尋 API 帶 unit_name) */
  async searchByUnit(unitName: string, page = 1): Promise<TenderSearchResult> {
    return this.search({ query: unitName, page });
  },

  async listSubscriptions(): Promise<Array<{ id: number; keyword: string; category: string | null; is_active: boolean; notify_line: boolean; notify_system: boolean; last_checked_at: string | null; last_count: number; last_diff: number; last_new_titles: string[] }>> {
    const res = await apiClient.post<SuccessResponse<Array<{ id: number; keyword: string; category: string | null; is_active: boolean; notify_line: boolean; notify_system: boolean; last_checked_at: string | null; last_count: number; last_diff: number; last_new_titles: string[] }>>>(
      TENDER_ENDPOINTS.SUBSCRIPTIONS_LIST, {},
    );
    return res.data ?? [];
  },

  async createSubscription(params: { keyword: string; category?: string; notify_line?: boolean; notify_system?: boolean }): Promise<{ id: number; keyword: string }> {
    const res = await apiClient.post<SuccessResponse<{ id: number; keyword: string }>>(
      TENDER_ENDPOINTS.SUBSCRIPTIONS_CREATE, params,
    );
    return res.data!;
  },

  async updateSubscription(params: { id: number; keyword?: string; category?: string; is_active?: boolean; notify_line?: boolean; notify_system?: boolean }): Promise<{ id: number; keyword: string }> {
    const res = await apiClient.post<SuccessResponse<{ id: number; keyword: string }>>(
      TENDER_ENDPOINTS.SUBSCRIPTIONS_UPDATE, params,
    );
    return res.data!;
  },

  async deleteSubscription(id: number): Promise<void> {
    await apiClient.post(TENDER_ENDPOINTS.SUBSCRIPTIONS_DELETE, { id });
  },

  // ========== 書籤 ==========

  async listBookmarks(): Promise<Array<{ id: number; unit_id: string; job_number: string; title: string; unit_name: string | null; budget: string | null; deadline: string | null; status: string; case_code: string | null; notes: string | null; created_at: string | null }>> {
    const res = await apiClient.post<SuccessResponse<Array<{ id: number; unit_id: string; job_number: string; title: string; unit_name: string | null; budget: string | null; deadline: string | null; status: string; case_code: string | null; notes: string | null; created_at: string | null }>>>(
      TENDER_ENDPOINTS.BOOKMARKS_LIST, {},
    );
    return res.data ?? [];
  },

  async createBookmark(params: { unit_id: string; job_number: string; title: string; unit_name?: string; budget?: string; deadline?: string; notes?: string }): Promise<{ id: number; title: string }> {
    const res = await apiClient.post<SuccessResponse<{ id: number; title: string }>>(
      TENDER_ENDPOINTS.BOOKMARKS_CREATE, params,
    );
    return res.data!;
  },

  async updateBookmark(params: { id: number; status?: string; case_code?: string; notes?: string }): Promise<{ id: number; status: string }> {
    const res = await apiClient.post<SuccessResponse<{ id: number; status: string }>>(
      TENDER_ENDPOINTS.BOOKMARKS_UPDATE, params,
    );
    return res.data!;
  },

  async deleteBookmark(id: number): Promise<void> {
    await apiClient.post(TENDER_ENDPOINTS.BOOKMARKS_DELETE, { id });
  },

  // ========== 建案 ==========

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

/**
 * 發文字號管理 API
 *
 * @deprecated 此模組已棄用，請改用 documentsApi 並設定 category='send'
 *
 * 遷移指南：
 * - documentNumbersApi.query() → documentsApi.getDocuments({ category: 'send' })
 * - documentNumbersApi.getStats() → documentsApi.getStatistics()
 * - documentNumbersApi.create() → documentsApi.createDocument({ doc_type: '發文' })
 * - documentNumbersApi.update() → documentsApi.updateDocument()
 * - documentNumbersApi.delete() → documentsApi.deleteDocument()
 *
 * @see documentsApi
 * @version 1.0.0 (DEPRECATED)
 * @date 2026-01-06
 */

import { apiClient } from './client';

// =============================================================================
// 型別定義
// =============================================================================

/** 發文字號項目 */
export interface DocumentNumber {
  id: number;
  doc_prefix: string;
  year: number;
  sequence_number: number;
  full_number: string;
  subject: string;
  contract_case: string;
  contract_case_id: number | null;
  receiver: string;
  doc_date: string | null;
  status: string;
  created_at: string | null;
}

/** 分頁回應（與後端對應） */
export interface DocumentNumberListResponse {
  items: DocumentNumber[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

/** 查詢請求參數 */
export interface DocumentNumberQueryParams {
  page?: number;
  limit?: number;
  year?: number;
  status?: string;
  keyword?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

/** 年度統計 */
export interface YearlyStats {
  year: number;
  count: number;
}

/** 年度範圍 */
export interface YearRange {
  min_year: number | null;
  max_year: number | null;
}

/** 統計資料 */
export interface DocumentNumberStats {
  total_count: number;
  draft_count: number;
  sent_count: number;
  archived_count: number;
  max_sequence: number;
  year_range: YearRange;
  yearly_stats: YearlyStats[];
}

/** 下一個字號回應 */
export interface NextNumberResponse {
  full_number: string;
  year: number;
  roc_year: number;
  sequence_number: number;
  previous_max: number;
  prefix: string;
}

/** 建立請求 */
export interface DocumentNumberCreateRequest {
  subject: string;
  receiver: string;
  contract_case_id?: number | null;
  doc_date?: string | null;
  status?: string;
}

/** 更新請求 */
export interface DocumentNumberUpdateRequest {
  subject?: string;
  receiver?: string;
  contract_case_id?: number | null;
  doc_date?: string | null;
  status?: string;
}

// =============================================================================
// API 函數 (POST-only)
// =============================================================================

/**
 * 查詢發文字號列表
 */
export async function queryDocumentNumbers(
  params: DocumentNumberQueryParams = {}
): Promise<DocumentNumberListResponse> {
  return apiClient.post<DocumentNumberListResponse>(
    '/document-numbers/query',
    {
      page: params.page || 1,
      limit: params.limit || 20,
      year: params.year,
      status: params.status,
      keyword: params.keyword,
      sort_by: params.sort_by || 'doc_date',
      sort_order: params.sort_order || 'desc',
    }
  );
}

/**
 * 取得統計資料
 */
export async function getDocumentNumberStats(): Promise<DocumentNumberStats> {
  return apiClient.post<DocumentNumberStats>('/document-numbers/stats');
}

/**
 * 取得下一個可用字號
 */
export async function getNextDocumentNumber(
  prefix?: string,
  year?: number
): Promise<NextNumberResponse> {
  return apiClient.post<NextNumberResponse>('/document-numbers/next-number', {
    prefix,
    year,
  });
}

/**
 * 建立發文字號
 */
export async function createDocumentNumber(
  data: DocumentNumberCreateRequest
): Promise<DocumentNumber> {
  return apiClient.post<DocumentNumber>('/document-numbers/create', data);
}

/**
 * 更新發文字號
 */
export async function updateDocumentNumber(
  id: number,
  data: DocumentNumberUpdateRequest
): Promise<DocumentNumber> {
  return apiClient.post<DocumentNumber>(
    `/document-numbers/update/${id}`,
    data
  );
}

/**
 * 刪除發文字號 (軟刪除)
 */
export async function deleteDocumentNumber(
  id: number
): Promise<{ success: boolean; message: string }> {
  return apiClient.post<{ success: boolean; message: string }>(
    `/document-numbers/delete/${id}`
  );
}

// =============================================================================
// 匯出
// =============================================================================

/**
 * 發文字號管理 API (已棄用)
 *
 * @deprecated 請改用 documentsApi 並設定 category='send'
 */
export const documentNumbersApi = {
  query: queryDocumentNumbers,
  getStats: getDocumentNumberStats,
  getNextNumber: getNextDocumentNumber,
  create: createDocumentNumber,
  update: updateDocumentNumber,
  delete: deleteDocumentNumber,
};

export default documentNumbersApi;

/**
 * 公文管理 API 服務
 *
 * 使用統一的 API Client 和型別定義
 */

import { apiClient, ApiException, API_BASE_URL } from './client';
import {
  PaginatedResponse,
  PaginationParams,
  SortParams,
  DeleteResponse,
  normalizePaginatedResponse,
  LegacyListResponse,
} from './types';
import { API_ENDPOINTS } from './endpoints';

// 從 types/ 匯入統一的公文型別 (SSOT)
import type {
  OfficialDocument,
  DocumentCreate,
  DocumentUpdate,
  DocumentTrendsResponse,
  DocumentEfficiencyResponse,
  DocumentStatistics,
  NextSendNumberResponse,
  DropdownOption,
} from '../types/api';
import { logger } from '../services/logger';

// ============================================================================
// 型別 re-export — 向後相容，定義位於 types/api.ts (SSOT)
// ============================================================================

/** Document 是 OfficialDocument 的別名 */
export type Document = OfficialDocument;

// 重新匯出型別供外部使用
export type {
  OfficialDocument, DocumentCreate, DocumentUpdate,
  DocumentStatistics, NextSendNumberResponse, DropdownOption,
};

/** 公文列表查詢參數 */
export interface DocumentListParams extends PaginationParams, SortParams {
  search?: string;
  keyword?: string;
  doc_number?: string;
  doc_type?: string;
  year?: number | string;
  status?: string;
  category?: string;
  contract_case?: string;
  sender?: string;
  receiver?: string;
  delivery_method?: string;
  doc_date_from?: string;
  doc_date_to?: string;
  date_from?: string;
  date_to?: string;
}

// 文件附件型別請直接從 filesApi 匯入
// import type { FileAttachment, DocumentAttachment } from './filesApi';

// ============================================================================
// API 方法
// ============================================================================

/**
 * 公文 API 服務
 */
export const documentsApi = {
  /**
   * 取得公文列表
   *
   * @param params 查詢參數（分頁、搜尋、排序）
   * @returns 分頁公文列表
   */
  async getDocuments(
    params?: DocumentListParams
  ): Promise<PaginatedResponse<Document>> {
    // 合併 search 和 keyword，優先順序：keyword > search
    // doc_number 作為獨立參數發送，僅搜尋公文字號欄位
    const keywordValue = params?.keyword || params?.search || undefined;

    // 處理年度值（可能是字串或數字）
    const yearValue = params?.year ? Number(params.year) || undefined : undefined;

    const queryParams = {
      page: params?.page ?? 1,
      limit: params?.limit ?? 20,
      // 關鍵字搜尋（主旨、說明、備註）
      keyword: keywordValue,
      // 公文字號專用篩選（僅搜尋 doc_number 欄位）
      doc_number: params?.doc_number || undefined,
      // 類型篩選
      doc_type: params?.doc_type || undefined,
      year: yearValue,
      status: params?.status || undefined,
      category: params?.category || undefined,
      // 進階篩選
      contract_case: params?.contract_case || undefined,
      sender: params?.sender || undefined,
      receiver: params?.receiver || undefined,
      delivery_method: params?.delivery_method || undefined,
      // 日期篩選（支援兩種格式）
      doc_date_from: params?.doc_date_from || params?.date_from || undefined,
      doc_date_to: params?.doc_date_to || params?.date_to || undefined,
      // 排序
      sort_by: params?.sort_by ?? 'updated_at',
      sort_order: params?.sort_order ?? 'desc',
    };

    try {
      // 使用新版 POST API
      return await apiClient.postList<Document>(API_ENDPOINTS.DOCUMENTS.LIST, queryParams);
    } catch (error) {
      // 若新 API 失敗，嘗試舊版格式（相容性）
      if (error instanceof ApiException && error.statusCode === 404) {
        const response = await apiClient.get<{
          items: Document[];
          total: number;
          page: number;
          limit: number;
          total_pages: number;
        }>(API_ENDPOINTS.DOCUMENTS.INTEGRATED_SEARCH, {
          params: {
            skip: ((params?.page ?? 1) - 1) * (params?.limit ?? 20),
            limit: params?.limit ?? 100,
            keyword: keywordValue,
            doc_type: params?.doc_type || undefined,
            year: yearValue,
            status: params?.status || undefined,
            category: params?.category || undefined,
            contract_case: params?.contract_case || undefined,
            sender: params?.sender || undefined,
            receiver: params?.receiver || undefined,
            delivery_method: params?.delivery_method || undefined,
            doc_date_from: params?.doc_date_from || params?.date_from || undefined,
            doc_date_to: params?.doc_date_to || params?.date_to || undefined,
            sort_by: params?.sort_by ?? 'updated_at',
            sort_order: params?.sort_order ?? 'desc',
          }
        });
        // 轉換舊版格式
        return normalizePaginatedResponse(
          {
            items: response.items,
            total: response.total,
          } as LegacyListResponse<Document>,
          params?.page,
          params?.limit
        );
      }
      throw error;
    }
  },

  /**
   * 取得單一公文詳情（POST-only 資安機制）
   *
   * @param documentId 公文 ID
   * @returns 公文資料
   */
  async getDocument(documentId: number): Promise<Document> {
    return await apiClient.post<Document>(API_ENDPOINTS.DOCUMENTS.DETAIL(documentId));
  },

  /**
   * 建立新公文（POST-only 資安機制）
   *
   * @param data 公文資料
   * @returns 新建的公文
   */
  async createDocument(data: DocumentCreate): Promise<Document> {
    return await apiClient.post<Document>(API_ENDPOINTS.DOCUMENTS.CREATE, data);
  },

  /**
   * 更新公文（POST-only 資安機制）
   *
   * @param documentId 公文 ID
   * @param data 更新資料
   * @returns 更新後的公文
   */
  async updateDocument(documentId: number, data: DocumentUpdate): Promise<Document> {
    return await apiClient.post<Document>(API_ENDPOINTS.DOCUMENTS.UPDATE(documentId), data);
  },

  /**
   * 刪除公文（POST-only 資安機制）
   *
   * @param documentId 公文 ID
   * @returns 刪除結果
   */
  async deleteDocument(documentId: number): Promise<DeleteResponse> {
    return await apiClient.post<DeleteResponse>(API_ENDPOINTS.DOCUMENTS.DELETE(documentId));
  },

  /**
   * 取得公文統計資料
   *
   * @returns 統計資料
   */
  async getStatistics(): Promise<DocumentStatistics> {
    return await apiClient.post<DocumentStatistics>(API_ENDPOINTS.DOCUMENTS.STATISTICS);
  },

  /**
   * 取得下一個可用的發文字號
   *
   * 文號格式：{前綴}{民國年3位}{流水號7位}號
   * 範例：乾坤測字第1150000001號 (民國115年第1號)
   *
   * @param prefix 文號前綴 (可選，預設使用系統設定)
   * @param year 西元年 (可選，預設使用當前年度)
   * @returns 下一個可用的發文字號資訊
   */
  async getNextSendNumber(prefix?: string, year?: number): Promise<NextSendNumberResponse> {
    return await apiClient.post<NextSendNumberResponse>(
      API_ENDPOINTS.DOCUMENTS.NEXT_SEND_NUMBER,
      { prefix, year }
    );
  },

  /**
   * 取得篩選後的公文統計資料
   *
   * 根據當前篩選條件計算 total/send/receive 數量
   * 用於前端 Tab 標籤的動態數字顯示
   *
   * @param params 篩選參數（與 getDocuments 相同）
   * @returns 篩選後的統計資料
   */
  async getFilteredStatistics(params?: DocumentListParams): Promise<{
    success: boolean;
    total: number;
    send_count: number;
    receive_count: number;
    filters_applied: boolean;
  }> {
    // 合併 search 和 keyword，doc_number 獨立發送
    const keywordValue = params?.keyword || params?.search || undefined;
    const yearValue = params?.year ? Number(params.year) || undefined : undefined;

    const queryParams = {
      keyword: keywordValue,
      doc_number: params?.doc_number || undefined,  // 公文字號專用篩選
      doc_type: params?.doc_type || undefined,
      year: yearValue,
      sender: params?.sender || undefined,
      receiver: params?.receiver || undefined,
      delivery_method: params?.delivery_method || undefined,
      doc_date_from: params?.doc_date_from || params?.date_from || undefined,
      doc_date_to: params?.doc_date_to || params?.date_to || undefined,
      contract_case: params?.contract_case || undefined,
    };

    return await apiClient.post(API_ENDPOINTS.DOCUMENTS.FILTERED_STATISTICS, queryParams);
  },

  /**
   * 取得年度選項
   *
   * @returns 年度列表
   */
  async getYearOptions(): Promise<number[]> {
    const response = await apiClient.post<{ years: number[] }>(API_ENDPOINTS.DOCUMENTS.YEARS);
    return response.years || [];
  },

  /**
   * 取得承攬案件下拉選項
   *
   * @param search 搜尋關鍵字
   * @param limit 最大數量
   * @returns 選項列表
   */
  async getContractProjectOptions(search?: string, limit = 100): Promise<DropdownOption[]> {
    const response = await apiClient.post<{ options: DropdownOption[] }>(
      API_ENDPOINTS.DOCUMENTS.CONTRACT_PROJECTS_DROPDOWN,
      { search, limit }
    );
    return response.options || [];
  },

  /**
   * 取得機關下拉選項
   *
   * @param search 搜尋關鍵字
   * @param limit 最大數量
   * @returns 選項列表
   */
  async getAgencyOptions(search?: string, limit = 100): Promise<DropdownOption[]> {
    const response = await apiClient.post<{ options: DropdownOption[] }>(
      API_ENDPOINTS.DOCUMENTS.AGENCIES_DROPDOWN,
      { search, limit }
    );
    return response.options || [];
  },

  /**
   * 搜尋公文
   *
   * @param keyword 搜尋關鍵字
   * @param limit 最大數量
   * @returns 符合條件的公文列表
   */
  async searchDocuments(keyword: string, limit = 10): Promise<Document[]> {
    const response = await this.getDocuments({
      keyword,
      limit,
    });
    return response.items;
  },

  /**
   * 取得專案關聯公文（自動關聯機制）
   *
   * 根據 project_id 自動查詢該專案的所有關聯公文
   *
   * @param projectId 專案 ID
   * @param page 頁碼
   * @param limit 每頁筆數
   * @returns 分頁公文列表
   */
  async getDocumentsByProject(
    projectId: number,
    page = 1,
    limit = 50
  ): Promise<PaginatedResponse<Document>> {
    try {
      return await apiClient.postList<Document>(API_ENDPOINTS.DOCUMENTS.BY_PROJECT, {
        project_id: projectId,
        page,
        limit,
      });
    } catch (error) {
      logger.error('取得專案關聯公文失敗:', error);
      return {
        success: true,
        items: [],
        pagination: {
          total: 0,
          page: 1,
          limit,
          total_pages: 0,
          has_next: false,
          has_prev: false,
        },
      };
    }
  },

  /**
   * 匯出公文為 CSV 檔案
   *
   * @param documentIds 指定匯出的公文 ID 列表 (可選)
   * @param category 類別篩選 (可選)
   * @param year 年度篩選 (可選)
   */
  async exportDocuments(options?: {
    documentIds?: number[];
    category?: string;
    year?: number;
  }): Promise<void> {
    // 生成檔名
    const now = new Date();
    const dateStr = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`;
    const filename = `documents_export_${dateStr}.csv`;

    await apiClient.downloadPost(
      API_ENDPOINTS.DOCUMENTS.EXPORT,
      {
        document_ids: options?.documentIds || null,
        category: options?.category || null,
        year: options?.year || null,
        format: 'csv',
      },
      filename
    );
  },

  // ==========================================================================
  // 儀表板統計方法 (v13.0 新增)
  // ==========================================================================

  /**
   * 取得公文月度趨勢統計
   *
   * @returns 過去 12 個月每月收文/發文數量
   */
  async getDocumentTrends(): Promise<DocumentTrendsResponse> {
    try {
      return await apiClient.post<DocumentTrendsResponse>(API_ENDPOINTS.DOCUMENTS.TRENDS, {});
    } catch (error) {
      logger.error('取得公文趨勢失敗:', error);
      return { trends: [] };
    }
  },

  /**
   * 取得公文處理效率統計
   *
   * @returns 狀態分布、逾期率等統計資料
   */
  async getDocumentEfficiency(): Promise<DocumentEfficiencyResponse> {
    try {
      return await apiClient.post<DocumentEfficiencyResponse>(API_ENDPOINTS.DOCUMENTS.EFFICIENCY, {});
    } catch (error) {
      logger.error('取得公文效率統計失敗:', error);
      return { status_distribution: [], overdue_count: 0, overdue_rate: 0, total: 0 };
    }
  },

  // ==========================================================================
  // CSV 匯入方法
  // ==========================================================================

  /**
   * 匯入 CSV 檔案
   *
   * @param file CSV 檔案
   * @returns 匯入結果
   */
  async importCSV(file: File): Promise<{
    success: boolean;
    message: string;
    total_rows: number;
    success_count: number;
    error_count: number;
    errors: string[];
    processing_time: number;
  }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(
      `${API_BASE_URL}${API_ENDPOINTS.CSV_IMPORT.UPLOAD_AND_IMPORT}`,
      {
        method: 'POST',
        body: formData,
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `匯入失敗: HTTP ${response.status}`);
    }

    return await response.json();
  },

  // ==========================================================================
  // 檔案附件方法已移除 - 請直接使用 filesApi
  // filesApi.getDocumentAttachments, filesApi.downloadAttachment, etc.
  // ==========================================================================

  // ==========================================================================
  // 審計日誌方法
  // ==========================================================================

  /**
   * 取得審計日誌列表
   *
   * @param params 查詢參數
   * @returns 審計日誌分頁列表
   */
  async getAuditLogs(params?: {
    page?: number;
    limit?: number;
    action?: string;
    user_id?: number;
    resource_type?: string;
    date_from?: string;
    date_to?: string;
  }): Promise<{
    success: boolean;
    items: Array<{
      id: number;
      action: string;
      resource_type: string;
      resource_id: number;
      user_id: number;
      user_name: string;
      details: Record<string, unknown>;
      ip_address?: string;
      created_at: string;
    }>;
    total: number;
    page: number;
    limit: number;
  }> {
    return await apiClient.post(API_ENDPOINTS.DOCUMENTS.AUDIT_LOGS, params || {});
  },

  /**
   * 取得單一公文的審計歷史
   *
   * @param documentId 公文 ID
   * @returns 該公文的審計歷史記錄
   */
  async getDocumentAuditHistory(documentId: number): Promise<{
    success: boolean;
    document_id: number;
    history: Array<{
      id: number;
      action: string;
      user_name: string;
      details: Record<string, unknown>;
      created_at: string;
    }>;
  }> {
    return await apiClient.post(API_ENDPOINTS.DOCUMENTS.AUDIT_HISTORY(documentId));
  },
};

// 預設匯出
export default documentsApi;

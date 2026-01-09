/**
 * 公文管理 API 服務
 *
 * 使用統一的 API Client 和型別定義
 */

import { apiClient, ApiException } from './client';
import {
  PaginatedResponse,
  PaginationParams,
  SortParams,
  DeleteResponse,
  normalizePaginatedResponse,
  LegacyListResponse,
} from './types';
import { API_ENDPOINTS } from './endpoints';

// ============================================================================
// 型別定義
// ============================================================================

/** 公文基礎介面 - 與後端 DocumentResponse Schema 完整對應 */
export interface Document {
  id: number;
  doc_number: string;
  doc_type: string;
  subject: string;
  sender?: string;
  receiver?: string;
  doc_date?: string;
  receive_date?: string;
  send_date?: string;
  status?: string;
  category?: string;
  contract_case?: string;
  doc_word?: string;
  doc_class?: string;
  assignee?: string;
  user_confirm?: boolean;
  auto_serial?: string;  // 流水序號 (R0001=收文, S0001=發文)
  creator?: string;
  is_deleted?: boolean;
  notes?: string;
  priority_level?: string;
  content?: string;
  created_at: string;
  updated_at: string;

  // === 新增欄位 (與後端 DocumentResponse 對應) ===

  // 發文形式與附件欄位
  delivery_method?: string;      // 發文形式 (電子交換/紙本郵寄/電子+紙本)
  has_attachment?: boolean;      // 是否含附件

  // 承攬案件關聯資訊
  contract_project_id?: number;    // 承攬案件 ID
  contract_project_name?: string;  // 承攬案件名稱
  assigned_staff?: Array<{         // 負責業務同仁
    user_id: number;
    name: string;
    role: string;
  }>;

  // 附件統計
  attachment_count?: number;  // 附件數量

  // 公文字號拆分欄位
  doc_zi?: string;       // 公文「字」部分，如「桃工用」
  doc_wen_hao?: string;  // 公文「文號」部分，如「1140024090」
}

/** 公文建立請求 - 與後端 DocumentCreate Schema 對應 */
export interface DocumentCreate {
  doc_number: string;
  doc_type: string;
  subject: string;
  sender?: string;
  receiver?: string;
  doc_date?: string;
  receive_date?: string;
  send_date?: string;
  status?: string;
  category?: string;
  contract_case?: string;
  contract_project_id?: number;   // 承攬案件 ID
  sender_agency_id?: number;      // 發文機關 ID
  receiver_agency_id?: number;    // 受文機關 ID
  doc_word?: string;
  doc_class?: string;
  assignee?: string;              // 承辦人
  content?: string;               // 說明
  notes?: string;                 // 備註
  priority_level?: string;
  // 發文形式與附件欄位
  delivery_method?: string;       // 發文形式 (電子交換/紙本郵寄/電子+紙本)
  has_attachment?: boolean;       // 是否含附件
}

/** 公文更新請求 - 與後端 DocumentUpdate Schema 對應 */
export interface DocumentUpdate {
  doc_number?: string;
  doc_type?: string;
  subject?: string;
  sender?: string;
  receiver?: string;
  doc_date?: string;
  receive_date?: string;
  send_date?: string;
  status?: string;
  category?: string;
  contract_case?: string;
  contract_project_id?: number;   // 承攬案件 ID
  sender_agency_id?: number;      // 發文機關 ID
  receiver_agency_id?: number;    // 受文機關 ID
  doc_word?: string;
  doc_class?: string;
  assignee?: string;              // 承辦人
  content?: string;               // 說明
  notes?: string;                 // 備註
  priority_level?: string;
  // 發文形式與附件欄位
  delivery_method?: string;       // 發文形式 (電子交換/紙本郵寄/電子+紙本)
  has_attachment?: boolean;       // 是否含附件
}

/** 公文列表查詢參數 */
export interface DocumentListParams extends PaginationParams, SortParams {
  // 關鍵字搜尋（前端可用 search 或 keyword）
  search?: string;
  keyword?: string;
  doc_number?: string;       // 公文字號搜尋
  // 類型篩選
  doc_type?: string;
  year?: number | string;    // 支援數字或字串
  status?: string;
  category?: string;         // 收發文分類 (receive=收文, send=發文)
  // 進階篩選
  contract_case?: string;
  sender?: string;
  receiver?: string;
  delivery_method?: string;  // 發文形式 (電子交換/紙本郵寄)
  // 日期篩選（支援兩種命名格式）
  doc_date_from?: string;
  doc_date_to?: string;
  date_from?: string;        // 相容性別名
  date_to?: string;          // 相容性別名
}

/** 公文統計資料 */
export interface DocumentStatistics {
  total: number;
  total_documents: number;
  send: number;
  send_count: number;
  receive: number;
  receive_count: number;
  current_year_count: number;
  current_year_send_count: number;
  delivery_method_stats: {
    electronic: number;
    paper: number;
    both: number;
  };
}

/** 下拉選項 */
export interface DropdownOption {
  value: string;
  label: string;
  id?: number;
  year?: number;
  category?: string;
}

/** 文件附件 - 從 filesApi 匯入並重新匯出 */
import type { FileAttachment } from './filesApi';
export type { FileAttachment as DocumentAttachment };
type DocumentAttachment = FileAttachment;

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
    // 合併 search、keyword 和 doc_number，優先順序：keyword > search > doc_number
    // 如果有 doc_number 且沒有其他關鍵字，則使用 doc_number 作為搜尋詞
    const keywordValue = params?.keyword || params?.search || params?.doc_number || undefined;

    // 處理年度值（可能是字串或數字）
    const yearValue = params?.year ? Number(params.year) || undefined : undefined;

    const queryParams = {
      page: params?.page ?? 1,
      limit: params?.limit ?? 20,
      // 關鍵字搜尋
      keyword: keywordValue,
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
        }>('/documents-enhanced/integrated-search', {
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
    // 合併 search 和 keyword
    const keywordValue = params?.keyword || params?.search || params?.doc_number || undefined;
    const yearValue = params?.year ? Number(params.year) || undefined : undefined;

    const queryParams = {
      keyword: keywordValue,
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
      console.error('取得專案關聯公文失敗:', error);
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
      `${import.meta.env.VITE_API_BASE_URL || ''}/api/csv-import/upload-and-import`,
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
  // 檔案附件方法 - 委託給 filesApi（統一 API 呼叫）
  // ==========================================================================

  /**
   * 取得文件附件列表
   * @deprecated 請直接使用 filesApi.getDocumentAttachments
   */
  async getDocumentAttachments(documentId: number): Promise<DocumentAttachment[]> {
    const { filesApi } = await import('./filesApi');
    return filesApi.getDocumentAttachments(documentId);
  },

  /**
   * 下載附件
   * @deprecated 請直接使用 filesApi.downloadAttachment
   */
  async downloadAttachment(attachmentId: number, filename: string): Promise<void> {
    const { filesApi } = await import('./filesApi');
    return filesApi.downloadAttachment(attachmentId, filename);
  },

  /**
   * 取得附件 Blob（用於預覽）
   * @deprecated 請直接使用 filesApi.getAttachmentBlob
   */
  async getAttachmentBlob(attachmentId: number): Promise<Blob> {
    const { filesApi } = await import('./filesApi');
    return filesApi.getAttachmentBlob(attachmentId);
  },

  /**
   * 刪除附件
   * @deprecated 請直接使用 filesApi.deleteAttachment
   */
  async deleteAttachment(attachmentId: number): Promise<{ success: boolean; message: string }> {
    const { filesApi } = await import('./filesApi');
    return filesApi.deleteAttachment(attachmentId);
  },

  /**
   * 驗證附件完整性
   * @deprecated 請直接使用 filesApi.verifyAttachment
   */
  async verifyAttachment(attachmentId: number): Promise<{
    success: boolean;
    file_id: number;
    status: string;
    is_valid?: boolean;
    message: string;
  }> {
    const { filesApi } = await import('./filesApi');
    return filesApi.verifyAttachment(attachmentId);
  },

  /**
   * 取得儲存系統資訊
   * @deprecated 請直接使用 filesApi.getStorageInfo
   */
  async getStorageInfo(): Promise<{
    success: boolean;
    storage_path: string;
    storage_type: string;
    total_files: number;
    total_size_mb: number;
    allowed_extensions: string[];
    max_file_size_mb: number;
  }> {
    const { filesApi } = await import('./filesApi');
    return filesApi.getStorageInfo();
  },

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

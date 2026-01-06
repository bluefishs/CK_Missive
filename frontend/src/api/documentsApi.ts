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
  doc_word?: string;
  doc_class?: string;
  assignee?: string;
  notes?: string;
  priority_level?: string;
  content?: string;
  // 新增欄位
  delivery_method?: string;   // 發文形式 (電子交換/紙本郵寄/電子+紙本)
  has_attachment?: boolean;   // 是否含附件
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
  doc_word?: string;
  doc_class?: string;
  assignee?: string;
  notes?: string;
  priority_level?: string;
  content?: string;
  // 新增欄位
  delivery_method?: string;   // 發文形式 (電子交換/紙本郵寄/電子+紙本)
  has_attachment?: boolean;   // 是否含附件
}

/** 公文列表查詢參數 */
export interface DocumentListParams extends PaginationParams, SortParams {
  keyword?: string;
  doc_type?: string;
  year?: number;
  status?: string;
  category?: string;  // 收發文分類 (receive=收文, send=發文)
  contract_case?: string;
  sender?: string;
  receiver?: string;
  doc_date_from?: string;
  doc_date_to?: string;
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
    const queryParams = {
      page: params?.page ?? 1,
      limit: params?.limit ?? 20,
      keyword: params?.keyword,
      doc_type: params?.doc_type,
      year: params?.year,
      status: params?.status,
      category: params?.category,  // 收發文分類 (receive=收文, send=發文)
      contract_case: params?.contract_case,
      sender: params?.sender,
      receiver: params?.receiver,
      doc_date_from: params?.doc_date_from,
      doc_date_to: params?.doc_date_to,
      sort_by: params?.sort_by ?? 'updated_at',
      sort_order: params?.sort_order ?? 'desc',
    };

    try {
      // 使用新版 POST API
      return await apiClient.postList<Document>('/documents-enhanced/list', queryParams);
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
            keyword: params?.keyword,
            doc_type: params?.doc_type,
            year: params?.year,
            status: params?.status,
            category: params?.category,  // 收發文分類
            contract_case: params?.contract_case,
            sender: params?.sender,
            receiver: params?.receiver,
            doc_date_from: params?.doc_date_from,
            doc_date_to: params?.doc_date_to,
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
    return await apiClient.post<Document>(`/documents-enhanced/${documentId}/detail`);
  },

  /**
   * 建立新公文（POST-only 資安機制）
   *
   * @param data 公文資料
   * @returns 新建的公文
   */
  async createDocument(data: DocumentCreate): Promise<Document> {
    return await apiClient.post<Document>('/documents-enhanced', data);
  },

  /**
   * 更新公文（POST-only 資安機制）
   *
   * @param documentId 公文 ID
   * @param data 更新資料
   * @returns 更新後的公文
   */
  async updateDocument(documentId: number, data: DocumentUpdate): Promise<Document> {
    return await apiClient.post<Document>(`/documents-enhanced/${documentId}/update`, data);
  },

  /**
   * 刪除公文（POST-only 資安機制）
   *
   * @param documentId 公文 ID
   * @returns 刪除結果
   */
  async deleteDocument(documentId: number): Promise<DeleteResponse> {
    return await apiClient.post<DeleteResponse>(`/documents-enhanced/${documentId}/delete`);
  },

  /**
   * 取得公文統計資料
   *
   * @returns 統計資料
   */
  async getStatistics(): Promise<DocumentStatistics> {
    return await apiClient.post<DocumentStatistics>('/documents-enhanced/statistics');
  },

  /**
   * 取得年度選項
   *
   * @returns 年度列表
   */
  async getYearOptions(): Promise<number[]> {
    const response = await apiClient.post<{ years: number[] }>('/documents-enhanced/years');
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
      '/documents-enhanced/contract-projects-dropdown',
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
      '/documents-enhanced/agencies-dropdown',
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
      return await apiClient.postList<Document>('/documents-enhanced/by-project', {
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
      '/documents-enhanced/export',
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
};

// 預設匯出
export default documentsApi;

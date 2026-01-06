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

// ============================================================================
// 型別定義
// ============================================================================

/** 公文基礎介面 */
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
}

/** 公文建立請求 */
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
}

/** 公文更新請求 */
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

/** 文件附件 */
export interface DocumentAttachment {
  id: number;
  filename: string;
  original_filename?: string;
  file_size: number;
  content_type?: string;
  storage_type?: string;  // local/network/s3
  checksum?: string;      // SHA256 校驗碼
  uploaded_at?: string;
  uploaded_by?: number;
  created_at?: string;
}

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
    try {
      const response = await fetch(`${API_BASE_URL}/documents-enhanced/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_ids: options?.documentIds || null,
          category: options?.category || null,
          year: options?.year || null,
          format: 'csv',
        }),
      });

      if (!response.ok) {
        throw new Error('匯出失敗');
      }

      // 取得檔案名稱
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'documents_export.csv';
      if (contentDisposition) {
        const match = contentDisposition.match(/filename=(.+)/);
        if (match?.[1]) {
          filename = match[1].replace(/"/g, '');
        }
      }

      // 下載檔案
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('匯出公文失敗:', error);
      throw error;
    }
  },

  /**
   * 取得文件附件列表
   *
   * @param documentId 公文 ID
   * @returns 附件列表
   */
  async getDocumentAttachments(documentId: number): Promise<DocumentAttachment[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/files/document/${documentId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('取得附件失敗');
      }

      const data = await response.json();
      return data.attachments || [];
    } catch (error) {
      console.error('取得附件列表失敗:', error);
      return [];
    }
  },

  /**
   * 下載附件
   *
   * @param attachmentId 附件 ID
   * @param filename 檔案名稱
   */
  async downloadAttachment(attachmentId: number, filename: string): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/files/${attachmentId}/download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('下載失敗');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('下載附件失敗:', error);
      throw error;
    }
  },

  /**
   * 取得附件預覽 (POST-only 資安機制)
   *
   * 注意：由於採用 POST 方式，無法直接使用 URL 預覽
   * 需透過 downloadAttachment 方法取得 Blob 後顯示
   *
   * @param attachmentId 附件 ID
   * @returns 附件 Blob
   */
  async getAttachmentBlob(attachmentId: number): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/files/${attachmentId}/download`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) {
      throw new Error('取得附件失敗');
    }
    return await response.blob();
  },

  /**
   * 刪除附件 (POST-only 資安機制)
   *
   * @param attachmentId 附件 ID
   * @returns 刪除結果
   */
  async deleteAttachment(attachmentId: number): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE_URL}/files/${attachmentId}/delete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) {
      throw new Error('刪除附件失敗');
    }
    return await response.json();
  },

  /**
   * 驗證附件完整性 (POST-only 資安機制)
   *
   * @param attachmentId 附件 ID
   * @returns 驗證結果
   */
  async verifyAttachment(attachmentId: number): Promise<{
    success: boolean;
    file_id: number;
    status: string;
    is_valid?: boolean;
    message: string;
  }> {
    const response = await fetch(`${API_BASE_URL}/files/verify/${attachmentId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) {
      throw new Error('驗證附件失敗');
    }
    return await response.json();
  },

  /**
   * 取得儲存系統資訊
   *
   * @returns 儲存資訊
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
    const response = await fetch(`${API_BASE_URL}/files/storage-info`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) {
      throw new Error('取得儲存資訊失敗');
    }
    return await response.json();
  },
};

// 預設匯出
export default documentsApi;

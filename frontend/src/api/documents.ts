/**
 * @deprecated 此檔案已被 documentsApi.ts 取代
 * 請使用 import { documentsApi } from '@/api/documentsApi' 或 import { documentsApi } from '@/api'
 */
import { apiClient as axiosClient } from './client';

// 建立 axios 風格的 wrapper（因為此檔案使用 axios response 格式）
const apiClient = {
  async get<T>(url: string, config?: { params?: Record<string, unknown> }) {
    const response = await axiosClient.get<T>(url, config);
    return response;
  },
  async post<T>(url: string, data?: unknown) {
    const response = await axiosClient.post<T>(url, data);
    return response;
  },
};
import type { Document, DocumentListResponse } from '../types/document';

// Backend API response format (支援多種欄位名稱)
interface BackendDocumentListResponse {
  items?: Document[];      // documents-enhanced API 使用
  documents?: Document[];  // 舊版 API 使用
  total: number;
  page: number;
  limit?: number;          // documents-enhanced API 使用
  per_page?: number;       // 舊版 API 使用
  total_pages?: number;    // documents-enhanced API 使用
  pages?: number;          // 舊版 API 使用
}

/** @deprecated 請改用 documentsApi from './documentsApi' */
export const documentsApiLegacy = {
  // 獲取文件列表
  getDocuments: async (filters?: any): Promise<DocumentListResponse> => {
    try {
      console.log("=== 前端 API 調用：連接正式 PostgreSQL 資料庫 ===");

      // Convert page-based pagination to skip-based pagination
      const apiParams = { ...filters };
      if (apiParams.page && apiParams.limit) {
        apiParams.skip = (apiParams.page - 1) * apiParams.limit;
        delete apiParams.page; // Remove page parameter as backend uses skip
      }

      // 轉換排序參數名稱 (前端 camelCase -> 後端 snake_case)
      if (apiParams.sortBy) {
        apiParams.sort_by = apiParams.sortBy;
        delete apiParams.sortBy;
      }
      if (apiParams.sortOrder) {
        apiParams.sort_order = apiParams.sortOrder;
        delete apiParams.sortOrder;
      }

      console.log("=== 轉換後的 API 參數：", apiParams);

      // 使用documents-enhanced端點（已修復CORS問題）
      const backendResponse: BackendDocumentListResponse = await apiClient.get('/documents-enhanced/integrated-search', { params: apiParams });
      console.log("=== 正式資料庫 API 回應資料：", backendResponse);

      // Transform backend response format to frontend expected format
      // 後端 API 回傳: { items, total, page, limit, total_pages }
      const transformedResponse: DocumentListResponse = {
        items: backendResponse.items || backendResponse.documents || [],
        total: backendResponse.total || 0,
        page: backendResponse.page || 1,
        limit: backendResponse.limit || backendResponse.per_page || 10,
        total_pages: backendResponse.total_pages || backendResponse.pages || Math.ceil((backendResponse.total || 0) / (backendResponse.limit || 10))
      };

      console.log("=== 轉換後的回應資料：", transformedResponse);
      console.log("=== 文件數量：", transformedResponse.items.length);
      return transformedResponse;
    } catch (error) {
      console.error("API 調用失敗:", error);
      throw error;
    }
  },

  // 獲取單個文件
  getDocument: async (id: number): Promise<Document> => {
    const response = await apiClient.get(`/documents/${id}`);
    return response as unknown as Document;
  },

  // 創建文件
  createDocument: async (data: Partial<Document>): Promise<Document> => {
    const response = await apiClient.post('/documents', data);
    return response as unknown as Document;
  },

  // 更新文件
  updateDocument: async (id: number, data: Partial<Document>): Promise<Document> => {
    const response = await apiClient.put(`/documents/${id}`, data);
    return response as unknown as Document;
  },

  // 刪除文件
  deleteDocument: async (id: number): Promise<void> => {
    await apiClient.delete(`/documents/${id}`);
  },

  // 搜尋文件
  searchDocuments: async (query: string): Promise<Document[]> => {
    const response = await apiClient.get('/documents/search', { params: { q: query } });
    return response as unknown as Document[];
  },

  // 獲取統計數據（支援篩選條件）- 使用正確的 documents-enhanced API
  getStatistics: async (filters?: any): Promise<{ total: number; receive: number; send: number }> => {
    try {
      const params = filters || {};
      const response = await apiClient.get('/documents-enhanced/statistics', { params });
      // 統一回應格式
      return {
        total: (response as any).total || (response as any).total_documents || 0,
        receive: (response as any).receive || (response as any).receive_count || 0,
        send: (response as any).send || (response as any).send_count || 0,
      };
    } catch (error) {
      console.error('獲取統計數據失敗:', error);
      return { total: 0, receive: 0, send: 0 };
    }
  },
};

/** @deprecated 請改用 documentsApi from './documentsApi' */
export default documentsApiLegacy;

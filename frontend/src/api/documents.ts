import { apiClient } from './config';
import type { Document, DocumentListResponse } from '../types/document';

// Backend API response format (different from frontend expected format)
interface BackendDocumentListResponse {
  documents: Document[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export const documentsApi = {
  // 獲取文件列表
  getDocuments: async (filters?: any): Promise<DocumentListResponse> => {
    try {
      console.log("=== 前端 API 調用：連接正式 PostgreSQL 資料庫 (93筆記錄) ===");

      // Convert page-based pagination to skip-based pagination
      const apiParams = { ...filters };
      if (apiParams.page && apiParams.limit) {
        apiParams.skip = (apiParams.page - 1) * apiParams.limit;
        delete apiParams.page; // Remove page parameter as backend uses skip
      }
      console.log("=== 轉換後的 API 參數：", apiParams);

      // 使用documents-enhanced端點（已修復CORS問題）
      const backendResponse: BackendDocumentListResponse = await apiClient.get('/documents-enhanced/integrated-search', { params: apiParams });
      console.log("=== 正式資料庫 API 回應資料：", backendResponse);

      // Transform backend response format to frontend expected format
      const transformedResponse: DocumentListResponse = {
        items: backendResponse.items || backendResponse.documents || [], // Backend uses "items" in enhanced API
        total: backendResponse.total || 0,
        page: backendResponse.page || 1,
        limit: backendResponse.per_page || 10, // Backend uses "per_page", frontend expects "limit"
        total_pages: backendResponse.pages || 0 // Backend uses "pages", frontend expects "total_pages"
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

  // 獲取統計數據（支援篩選條件）
  getStatistics: async (filters?: any): Promise<{ total: number; receive: number; send: number }> => {
    const params = filters || {};
    const response = await apiClient.get('/dashboard/stats', { params });
    return response as { total: number; receive: number; send: number };
  },
};

export default documentsApi;

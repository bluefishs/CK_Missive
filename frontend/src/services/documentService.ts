import { documentsApi } from '../api';
import type { Document, DocumentFilter, DocumentListParams, DocumentListResponse } from '../types/document';

export const documentService = {
  // 獲取文件列表
  async getDocuments(params?: DocumentListParams): Promise<DocumentListResponse> {
    try {
      return await documentsApi.getDocuments(params);
    } catch (error) {
      console.error('Failed to fetch documents:', error);
      throw error;
    }
  },

  // 獲取單個文件
  async getDocument(id: number): Promise<Document> {
    try {
      return await documentsApi.getDocument(id);
    } catch (error) {
      console.error('Failed to fetch document:', error);
      throw error;
    }
  },

  // 創建文件
  async createDocument(data: Partial<Document>): Promise<Document> {
    try {
      return await documentsApi.createDocument(data);
    } catch (error) {
      console.error('Failed to create document:', error);
      throw error;
    }
  },

  // 更新文件
  async updateDocument(id: number, data: Partial<Document>): Promise<Document> {
    try {
      return await documentsApi.updateDocument(id, data);
    } catch (error) {
      console.error('Failed to update document:', error);
      throw error;
    }
  },

  // 刪除文件
  async deleteDocument(id: number): Promise<void> {
    try {
      await documentsApi.deleteDocument(id);
    } catch (error) {
      console.error('Failed to delete document:', error);
      throw error;
    }
  },

  // 搜尋文件
  async searchDocuments(query: string): Promise<Document[]> {
    try {
      return await documentsApi.searchDocuments(query);
    } catch (error) {
      console.error('Failed to search documents:', error);
      throw error;
    }
  },
};

export default documentService;

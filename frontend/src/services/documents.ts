/**
 * 文件 API 服務
 */

import httpClient from './httpClient';
import type { 
  Document, 
  DocumentListResponse,
  CreateDocumentRequest,
  UpdateDocumentRequest,
  QueryParams 
} from '../types/document';

class DocumentService {
  private readonly basePath = '/api/documents';

  /**
   * 獲取文件列表
   */
  async getDocuments(params?: QueryParams): Promise<DocumentListResponse> {
    const response = await httpClient.get<DocumentListResponse>(this.basePath, {
      params
    });
    return response;
  }

  /**
   * 獲取單個文件
   */
  async getDocument(id: string): Promise<Document> {
    const response = await httpClient.get<Document>(`${this.basePath}/${id}`);
    return response;
  }

  /**
   * 創建文件
   */
  async createDocument(data: CreateDocumentRequest): Promise<Document> {
    const response = await httpClient.post<Document>(this.basePath, data);
    return response;
  }

  /**
   * 更新文件
   */
  async updateDocument(id: string, data: UpdateDocumentRequest): Promise<Document> {
    const response = await httpClient.put<Document>(`${this.basePath}/${id}`, data);
    return response;
  }

  /**
   * 刪除文件
   */
  async deleteDocument(id: string): Promise<void> {
    await httpClient.delete(`${this.basePath}/${id}`);
  }
}

export const documentService = new DocumentService();
export { DocumentService };
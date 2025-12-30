/**
 * 文件相關類型定義
 */

import type {
  Document,
  DocumentStatus,
  DocumentType,
  DocumentPriority,
  DocumentFilter,
  DocumentAttachment,
  CreateDocumentRequest,
  UpdateDocumentRequest
} from './index';

export type {
  Document,
  DocumentStatus,
  DocumentType,
  DocumentPriority,
  DocumentFilter,
  DocumentAttachment,
  CreateDocumentRequest,
  UpdateDocumentRequest
};

// 文件列表參數類型
export interface DocumentListParams {
  readonly page?: number;
  readonly limit?: number;
  readonly search?: string;
  readonly status?: DocumentStatus;
  readonly type?: DocumentType;
  readonly priority?: DocumentPriority;
  readonly category?: string;
  readonly creator?: string;
  readonly assignee?: string;
  readonly dateFrom?: string;
  readonly dateTo?: string;
}

// 文件列表響應類型
export interface DocumentListResponse {
  readonly items: readonly Document[];
  readonly total: number;
  readonly page: number;
  readonly limit: number;
  readonly total_pages: number;
}

// 重新導出基礎類型
export type { ApiResponse, PaginationParams, QueryParams } from './index';
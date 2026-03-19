/**
 * 知識庫瀏覽器 API
 * @version 1.0.0
 */
import { apiClient } from './client';
import { API_ENDPOINTS } from './endpoints';
import type {
  FileInfo,
  SectionInfo,
  TreeResponse,
  FileContentResponse,
  AdrInfo,
  AdrListResponse,
  DiagramInfo,
  DiagramListResponse,
  KBSearchResult,
  KBSearchResponse,
} from '../types/api';

// Re-export types for backward compatibility
export type {
  FileInfo,
  SectionInfo,
  TreeResponse,
  FileContentResponse,
  AdrInfo,
  AdrListResponse,
  DiagramInfo,
  DiagramListResponse,
  KBSearchResult,
  KBSearchResponse,
};

// API functions
export const knowledgeBaseApi = {
  fetchTree: () =>
    apiClient.post<TreeResponse>(API_ENDPOINTS.KNOWLEDGE_BASE.TREE, {}),

  fetchFile: (path: string) =>
    apiClient.post<FileContentResponse>(API_ENDPOINTS.KNOWLEDGE_BASE.FILE, { path }),

  fetchAdrList: () =>
    apiClient.post<AdrListResponse>(API_ENDPOINTS.KNOWLEDGE_BASE.ADR_LIST, {}),

  fetchDiagramsList: () =>
    apiClient.post<DiagramListResponse>(API_ENDPOINTS.KNOWLEDGE_BASE.DIAGRAMS_LIST, {}),

  searchContent: (query: string, limit?: number) =>
    apiClient.post<KBSearchResponse>(API_ENDPOINTS.KNOWLEDGE_BASE.SEARCH, {
      query,
      ...(limit !== undefined && { limit }),
    }),
};

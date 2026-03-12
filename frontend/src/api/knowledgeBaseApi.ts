/**
 * 知識庫瀏覽器 API
 * @version 1.0.0
 */
import { apiClient } from './client';
import { API_ENDPOINTS } from './endpoints';

// Types
export interface FileInfo {
  name: string;
  path: string;
}

export interface SectionInfo {
  name: string;
  path: string;
  files: FileInfo[];
}

export interface TreeResponse {
  success: boolean;
  sections: SectionInfo[];
}

export interface FileContentResponse {
  success: boolean;
  content: string;
  filename: string;
}

export interface AdrInfo {
  number: string;
  title: string;
  status: string;
  date: string;
  path: string;
}

export interface AdrListResponse {
  success: boolean;
  items: AdrInfo[];
}

export interface DiagramInfo {
  name: string;
  path: string;
  title: string;
}

export interface DiagramListResponse {
  success: boolean;
  items: DiagramInfo[];
}

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
};

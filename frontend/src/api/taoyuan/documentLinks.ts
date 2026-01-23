/**
 * 桃園查估派工 - 公文關聯 API
 *
 * 包含:
 * - 公文-派工單關聯
 * - 公文-工程直接關聯
 *
 * @version 2.0.0
 * @date 2026-01-23
 */

import { apiClient } from '../client';
import { API_ENDPOINTS } from '../endpoints';
import type {
  DocumentDispatchLink,
  DocumentProjectLink,
} from '../../types/api';

/**
 * 公文-派工單關聯 API 服務
 */
export const documentLinksApi = {
  /**
   * 查詢公文關聯的派工單
   */
  async getDispatchLinks(documentId: number): Promise<{
    success: boolean;
    document_id: number;
    dispatch_orders: DocumentDispatchLink[];
    total: number;
  }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DOCUMENT_DISPATCH_LINKS(documentId),
      {}
    );
  },

  /**
   * 將公文關聯到派工單
   */
  async linkDispatch(
    documentId: number,
    dispatchOrderId: number,
    linkType: 'agency_incoming' | 'company_outgoing' = 'agency_incoming'
  ): Promise<{ success: boolean; message: string; link_id: number }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DOCUMENT_LINK_DISPATCH(documentId),
      {},
      {
        params: {
          dispatch_order_id: dispatchOrderId,
          link_type: linkType,
        },
      }
    );
  },

  /**
   * 移除公文與派工的關聯
   */
  async unlinkDispatch(documentId: number, linkId: number): Promise<{ success: boolean; message: string }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DOCUMENT_UNLINK_DISPATCH(documentId, linkId),
      {}
    );
  },

  /**
   * 批次查詢多筆公文的派工關聯
   */
  async getBatchDispatchLinks(documentIds: number[]): Promise<{
    success: boolean;
    links: Record<number, DocumentDispatchLink[]>;
  }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DOCUMENTS_BATCH_DISPATCH_LINKS,
      documentIds
    );
  },
};

/**
 * 公文-工程直接關聯 API 服務
 */
export const documentProjectLinksApi = {
  /**
   * 查詢公文關聯的工程
   */
  async getProjectLinks(documentId: number): Promise<{
    success: boolean;
    document_id: number;
    projects: DocumentProjectLink[];
    total: number;
  }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DOCUMENT_PROJECT_LINKS(documentId),
      {}
    );
  },

  /**
   * 將公文關聯到工程
   */
  async linkProject(
    documentId: number,
    projectId: number,
    linkType: 'agency_incoming' | 'company_outgoing' = 'agency_incoming',
    notes?: string
  ): Promise<{ success: boolean; message: string; link_id: number }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DOCUMENT_LINK_PROJECT(documentId),
      {},
      {
        params: {
          project_id: projectId,
          link_type: linkType,
          notes: notes,
        },
      }
    );
  },

  /**
   * 移除公文與工程的關聯
   */
  async unlinkProject(documentId: number, linkId: number): Promise<{ success: boolean; message: string }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DOCUMENT_UNLINK_PROJECT(documentId, linkId),
      {}
    );
  },

  /**
   * 批次查詢多筆公文的工程關聯
   */
  async getBatchProjectLinks(documentIds: number[]): Promise<{
    success: boolean;
    data: Record<number, DocumentProjectLink[]>;
    total: number;
  }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DOCUMENTS_BATCH_PROJECT_LINKS,
      documentIds
    );
  },
};

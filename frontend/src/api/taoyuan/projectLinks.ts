/**
 * 桃園查估派工 - 工程關聯 API
 *
 * @version 2.0.0
 * @date 2026-01-23
 */

import { apiClient } from '../client';
import { API_ENDPOINTS } from '../endpoints';
import type { ProjectDispatchLink } from '../../types/api';

/**
 * 工程關聯 API 服務
 */
export const projectLinksApi = {
  /**
   * 查詢工程關聯的派工單
   */
  async getDispatchLinks(projectId: number): Promise<{
    success: boolean;
    project_id: number;
    dispatch_orders: ProjectDispatchLink[];
    total: number;
  }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECT_DISPATCH_LINKS(projectId),
      {}
    );
  },

  /**
   * 將工程關聯到派工單
   * 自動同步：關聯成功後會自動將工程關聯到派工單關聯的所有公文
   */
  async linkDispatch(
    projectId: number,
    dispatchOrderId: number
  ): Promise<{
    success: boolean;
    message: string;
    link_id: number;
    auto_sync?: {
      document_count: number;
      auto_linked_count: number;
      message?: string;
    };
  }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECT_LINK_DISPATCH(projectId),
      {},
      {
        params: {
          dispatch_order_id: dispatchOrderId,
        },
      }
    );
  },

  /**
   * 移除工程與派工的關聯
   */
  async unlinkDispatch(projectId: number, linkId: number): Promise<{ success: boolean; message: string }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECT_UNLINK_DISPATCH(projectId, linkId),
      {}
    );
  },

  /**
   * 批次查詢多筆工程的派工關聯
   */
  async getBatchDispatchLinks(projectIds: number[]): Promise<{
    success: boolean;
    links: Record<number, ProjectDispatchLink[]>;
  }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS_BATCH_DISPATCH_LINKS,
      projectIds
    );
  },
};

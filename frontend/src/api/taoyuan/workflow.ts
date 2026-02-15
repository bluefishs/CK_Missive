/**
 * 桃園查估派工 - 作業歷程 API
 *
 * @version 1.0.0
 * @date 2026-02-13
 */

import { apiClient } from '../client';
import { API_ENDPOINTS } from '../endpoints';
import type {
  WorkRecord,
  WorkRecordCreate,
  WorkRecordUpdate,
  WorkRecordListResponse,
  ProjectWorkflowSummary,
} from '../../types/taoyuan';

/**
 * 作業歷程 API 服務
 */
export const workflowApi = {
  /**
   * 依派工單取得作業歷程列表
   */
  async listByDispatchOrder(
    dispatchOrderId: number,
    page = 1,
    pageSize = 50,
  ): Promise<WorkRecordListResponse> {
    return apiClient.post<WorkRecordListResponse>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.WORKFLOW_LIST,
      { dispatch_order_id: dispatchOrderId, page, page_size: pageSize },
    );
  },

  /**
   * 依工程取得作業歷程列表
   */
  async listByProject(
    projectId: number,
    page = 1,
    pageSize = 50,
  ): Promise<WorkRecordListResponse> {
    return apiClient.post<WorkRecordListResponse>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.WORKFLOW_BY_PROJECT,
      { project_id: projectId, page, page_size: pageSize },
    );
  },

  /**
   * 取得單筆作業紀錄
   */
  async getDetail(recordId: number): Promise<WorkRecord> {
    return apiClient.post<WorkRecord>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.WORKFLOW_DETAIL(recordId),
    );
  },

  /**
   * 建立作業紀錄
   */
  async create(data: WorkRecordCreate): Promise<WorkRecord> {
    return apiClient.post<WorkRecord>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.WORKFLOW_CREATE,
      data,
    );
  },

  /**
   * 更新作業紀錄
   */
  async update(recordId: number, data: WorkRecordUpdate): Promise<WorkRecord> {
    return apiClient.post<WorkRecord>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.WORKFLOW_UPDATE(recordId),
      data,
    );
  },

  /**
   * 刪除作業紀錄
   */
  async delete(recordId: number): Promise<{ success: boolean; message: string }> {
    return apiClient.post<{ success: boolean; message: string }>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.WORKFLOW_DELETE(recordId),
    );
  },

  /**
   * 批量更新批次歸屬
   */
  async batchUpdate(
    recordIds: number[],
    batchNo: number | null,
    batchLabel: string | null,
  ): Promise<{ updated_count: number }> {
    return apiClient.post<{ updated_count: number }>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.WORKFLOW_BATCH_UPDATE,
      { record_ids: recordIds, batch_no: batchNo, batch_label: batchLabel },
    );
  },

  /**
   * 取得工程歷程總覽
   */
  async getWorkflowSummary(projectId: number): Promise<ProjectWorkflowSummary> {
    return apiClient.post<ProjectWorkflowSummary>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.WORKFLOW_SUMMARY(projectId),
    );
  },
};

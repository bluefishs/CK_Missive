/**
 * 承辦同仁 API 服務
 *
 * 專案與承辦同仁關聯管理（POST-only 資安機制）
 */

import { apiClient } from './client';

// 從 types/api.ts 匯入統一的型別定義 (SSOT)
import type {
  ProjectStaff,
  ProjectStaffCreate,
  StaffOperationResponse,
  ProjectStaffListResponse,
  ProjectStaffRequest,
  ProjectStaffUpdate,
} from '../types/api';

// 重新匯出供外部使用
export type {
  ProjectStaff, ProjectStaffCreate,
  ProjectStaffListResponse, ProjectStaffRequest, ProjectStaffUpdate,
};

// ============================================================================
// API 方法
// ============================================================================

/**
 * 承辦同仁 API 服務
 */
export const projectStaffApi = {
  /**
   * 獲取專案的所有承辦同仁
   *
   * @param projectId 專案 ID
   * @returns 承辦同仁列表
   */
  async getProjectStaff(projectId: number): Promise<ProjectStaffListResponse> {
    return await apiClient.post<ProjectStaffListResponse>(
      `/project-staff/project/${projectId}/list`
    );
  },

  /**
   * 新增承辦同仁
   *
   * @param data 承辦同仁資料
   * @returns 操作結果
   */
  async addStaff(data: ProjectStaffRequest): Promise<StaffOperationResponse> {
    return await apiClient.post<StaffOperationResponse>('/project-staff', data);
  },

  /**
   * 更新承辦同仁
   *
   * @param projectId 專案 ID
   * @param userId 使用者 ID
   * @param data 更新資料
   * @returns 操作結果
   */
  async updateStaff(
    projectId: number,
    userId: number,
    data: ProjectStaffUpdate
  ): Promise<StaffOperationResponse> {
    return await apiClient.post<StaffOperationResponse>(
      `/project-staff/project/${projectId}/user/${userId}/update`,
      data
    );
  },

  /**
   * 刪除承辦同仁
   *
   * @param projectId 專案 ID
   * @param userId 使用者 ID
   * @returns 操作結果
   */
  async deleteStaff(projectId: number, userId: number): Promise<{ message: string }> {
    return await apiClient.post<{ message: string }>(
      `/project-staff/project/${projectId}/user/${userId}/delete`
    );
  },

  /**
   * 獲取所有承辦同仁關聯
   *
   * @param params 查詢參數
   * @returns 關聯列表
   */
  async getAllAssignments(params?: {
    skip?: number;
    limit?: number;
    project_id?: number;
    user_id?: number;
    status?: string;
  }): Promise<{ assignments: ProjectStaff[]; total: number; skip: number; limit: number }> {
    return await apiClient.post<{
      assignments: ProjectStaff[];
      total: number;
      skip: number;
      limit: number;
    }>('/project-staff/list', params || {});
  },
};

export default projectStaffApi;

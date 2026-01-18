/**
 * 承辦同仁 API 服務
 *
 * 專案與承辦同仁關聯管理（POST-only 資安機制）
 */

import { apiClient } from './client';

// 從 types/api.ts 匯入統一的型別定義
import { ProjectStaff as BaseProjectStaff, ProjectStaffCreate } from '../types/api';

// ============================================================================
// 型別定義 - API 專用擴展
// ============================================================================

/**
 * 承辦同仁資料 - 擴展基礎型別，包含 API 回應專用欄位
 * 基礎型別定義於 types/api.ts
 */
export interface ProjectStaff extends BaseProjectStaff {
  user_email?: string;
  department?: string;
  phone?: string;
}

// 重新匯出供外部使用
export type { ProjectStaffCreate };

/** 承辦同仁列表回應 */
export interface ProjectStaffListResponse {
  project_id: number;
  project_name: string;
  staff: ProjectStaff[];
  total: number;
}

/** 新增/更新承辦同仁請求 */
export interface ProjectStaffRequest {
  project_id: number;
  user_id: number;
  role?: string;
  is_primary?: boolean;
  start_date?: string;
  end_date?: string;
  status?: string;
  notes?: string;
}

/** 承辦同仁更新請求 */
export interface ProjectStaffUpdate {
  role?: string;
  is_primary?: boolean;
  start_date?: string;
  end_date?: string;
  status?: string;
  notes?: string;
}

/** 操作回應 */
interface StaffOperationResponse {
  message: string;
  project_id: number;
  user_id: number;
}

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

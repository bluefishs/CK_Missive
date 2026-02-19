/**
 * 協力廠商 API 服務
 *
 * 專案與協力廠商關聯管理（POST-only 資安機制）
 */

import { apiClient } from './client';

// 從 types/api.ts 匯入統一的型別定義
import { ProjectVendor as BaseProjectVendor, ProjectVendorCreate, VendorOperationResponse } from '../types/api';

// ============================================================================
// 型別定義 - API 專用擴展
// ============================================================================

/**
 * 協力廠商資料 - 擴展基礎型別，包含 API 回應專用欄位
 * 基礎型別定義於 types/api.ts
 */
export interface ProjectVendor extends BaseProjectVendor {
  vendor_contact_person?: string;
  vendor_phone?: string;
  vendor_business_type?: string;
}

// 重新匯出供外部使用
export type { ProjectVendorCreate };

/** 協力廠商列表回應 */
export interface ProjectVendorListResponse {
  project_id: number;
  project_name: string;
  associations: ProjectVendor[];
  total: number;
}

/** 新增協力廠商請求 */
export interface ProjectVendorRequest {
  project_id: number;
  vendor_id: number;
  role?: string;
  contract_amount?: number;
  start_date?: string;
  end_date?: string;
  status?: string;
}

/** 更新協力廠商請求 */
export interface ProjectVendorUpdate {
  role?: string;
  contract_amount?: number;
  start_date?: string;
  end_date?: string;
  status?: string;
}

// ============================================================================
// API 方法
// ============================================================================

/**
 * 協力廠商 API 服務
 */
export const projectVendorsApi = {
  /**
   * 獲取專案的所有協力廠商
   *
   * @param projectId 專案 ID
   * @returns 協力廠商列表
   */
  async getProjectVendors(projectId: number): Promise<ProjectVendorListResponse> {
    return await apiClient.post<ProjectVendorListResponse>(
      `/project-vendors/project/${projectId}/list`
    );
  },

  /**
   * 新增協力廠商
   *
   * @param data 協力廠商資料
   * @returns 操作結果
   */
  async addVendor(data: ProjectVendorRequest): Promise<VendorOperationResponse> {
    return await apiClient.post<VendorOperationResponse>('/project-vendors', data);
  },

  /**
   * 更新協力廠商
   *
   * @param projectId 專案 ID
   * @param vendorId 廠商 ID
   * @param data 更新資料
   * @returns 操作結果
   */
  async updateVendor(
    projectId: number,
    vendorId: number,
    data: ProjectVendorUpdate
  ): Promise<VendorOperationResponse> {
    return await apiClient.post<VendorOperationResponse>(
      `/project-vendors/project/${projectId}/vendor/${vendorId}/update`,
      data
    );
  },

  /**
   * 刪除協力廠商
   *
   * @param projectId 專案 ID
   * @param vendorId 廠商 ID
   * @returns 操作結果
   */
  async deleteVendor(projectId: number, vendorId: number): Promise<{ message: string }> {
    return await apiClient.post<{ message: string }>(
      `/project-vendors/project/${projectId}/vendor/${vendorId}/delete`
    );
  },

  /**
   * 獲取所有廠商關聯
   *
   * @param params 查詢參數
   * @returns 關聯列表
   */
  async getAllAssociations(params?: {
    skip?: number;
    limit?: number;
    project_id?: number;
    vendor_id?: number;
    status?: string;
  }): Promise<{ associations: ProjectVendor[]; total: number; skip: number; limit: number }> {
    return await apiClient.post<{
      associations: ProjectVendor[];
      total: number;
      skip: number;
      limit: number;
    }>('/project-vendors/list', params || {});
  },
};

export default projectVendorsApi;

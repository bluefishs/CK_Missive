/**
 * 協力廠商 API 服務
 *
 * 專案與協力廠商關聯管理（POST-only 資安機制）
 */

import { apiClient } from './client';
import { PROJECT_VENDORS_ENDPOINTS } from './endpoints';

// 從 types/api.ts 匯入統一的型別定義 (SSOT)
import type {
  ProjectVendor,
  ProjectVendorCreate,
  VendorOperationResponse,
  ProjectVendorListResponse,
  ProjectVendorRequest,
  ProjectVendorUpdate,
} from '../types/api';

// 重新匯出供外部使用
export type {
  ProjectVendor, ProjectVendorCreate,
  ProjectVendorListResponse, ProjectVendorRequest, ProjectVendorUpdate,
};

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
      PROJECT_VENDORS_ENDPOINTS.PROJECT_LIST(projectId)
    );
  },

  /**
   * 新增協力廠商
   *
   * @param data 協力廠商資料
   * @returns 操作結果
   */
  async addVendor(data: ProjectVendorRequest): Promise<VendorOperationResponse> {
    return await apiClient.post<VendorOperationResponse>(PROJECT_VENDORS_ENDPOINTS.CREATE, data);
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
      PROJECT_VENDORS_ENDPOINTS.UPDATE(projectId, vendorId),
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
      PROJECT_VENDORS_ENDPOINTS.DELETE(projectId, vendorId)
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
    }>(PROJECT_VENDORS_ENDPOINTS.LIST, params || {});
  },
};

export default projectVendorsApi;

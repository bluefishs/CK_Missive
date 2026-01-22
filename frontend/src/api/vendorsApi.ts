/**
 * 廠商管理 API 服務
 *
 * 使用統一的 API Client 和型別定義
 */

import { apiClient, ApiException } from './client';
import {
  PaginatedResponse,
  PaginationParams,
  SortParams,
  DeleteResponse,
  normalizePaginatedResponse,
  LegacyListResponse,
} from './types';
import {
  Vendor,
  VendorCreate,
  VendorUpdate,
  VendorOption,
} from '../types/api';
import { API_ENDPOINTS } from './endpoints';

// ============================================================================
// 查詢參數型別
// ============================================================================

/** 廠商列表查詢參數 */
export interface VendorListParams extends PaginationParams, SortParams {
  search?: string;
  business_type?: string;
}

/** 廠商統計資料 */
export interface VendorStatistics {
  total_vendors: number;
  business_types: Array<{
    business_type: string;
    count: number;
  }>;
  average_rating: number;
}

// ============================================================================
// API 方法
// ============================================================================

/**
 * 廠商 API 服務
 */
export const vendorsApi = {
  /**
   * 取得廠商列表
   *
   * @param params 查詢參數（分頁、搜尋、排序）
   * @returns 分頁廠商列表
   */
  async getVendors(
    params?: VendorListParams
  ): Promise<PaginatedResponse<Vendor>> {
    // 構建查詢參數，過濾 undefined 值避免 422 錯誤
    const queryParams: Record<string, unknown> = {
      page: params?.page ?? 1,
      limit: params?.limit ?? 20,
      sort_by: params?.sort_by ?? 'vendor_name',
      sort_order: params?.sort_order ?? 'asc',
    };

    // 只添加有值的可選參數
    if (params?.search) queryParams.search = params.search;
    if (params?.business_type) queryParams.business_type = params.business_type;

    try {
      // 嘗試使用新版 POST API
      return await apiClient.postList<Vendor>(API_ENDPOINTS.VENDORS.LIST, queryParams);
    } catch (error) {
      // 若新 API 失敗，嘗試舊版 GET API（相容性）
      if (error instanceof ApiException && error.statusCode === 404) {
        const response = await apiClient.get<LegacyListResponse<Vendor>>(
          API_ENDPOINTS.VENDORS.CREATE,
          {
            params: {
              skip: ((params?.page ?? 1) - 1) * (params?.limit ?? 20),
              limit: params?.limit ?? 100,
              search: params?.search,
            },
          }
        );
        return normalizePaginatedResponse(response, params?.page, params?.limit);
      }
      throw error;
    }
  },

  /**
   * 取得單一廠商詳情
   *
   * @param vendorId 廠商 ID
   * @returns 廠商資料
   */
  async getVendor(vendorId: number): Promise<Vendor> {
    return await apiClient.post<Vendor>(API_ENDPOINTS.VENDORS.DETAIL(vendorId));
  },

  /**
   * 建立新廠商
   *
   * @param data 廠商資料
   * @returns 新建的廠商
   */
  async createVendor(data: VendorCreate): Promise<Vendor> {
    return await apiClient.post<Vendor>(API_ENDPOINTS.VENDORS.CREATE, data);
  },

  /**
   * 更新廠商
   *
   * @param vendorId 廠商 ID
   * @param data 更新資料
   * @returns 更新後的廠商
   */
  async updateVendor(vendorId: number, data: VendorUpdate): Promise<Vendor> {
    return await apiClient.post<Vendor>(API_ENDPOINTS.VENDORS.UPDATE(vendorId), data);
  },

  /**
   * 刪除廠商
   *
   * @param vendorId 廠商 ID
   * @returns 刪除結果
   */
  async deleteVendor(vendorId: number): Promise<DeleteResponse> {
    return await apiClient.post<DeleteResponse>(API_ENDPOINTS.VENDORS.DELETE(vendorId));
  },

  /**
   * 取得廠商統計資料
   *
   * @returns 統計資料
   */
  async getStatistics(): Promise<VendorStatistics> {
    const response = await apiClient.post<{
      success: boolean;
      data: VendorStatistics;
    }>(API_ENDPOINTS.VENDORS.STATISTICS);
    return response.data;
  },

  /**
   * 取得廠商下拉選項
   *
   * 用於表單中的下拉選單
   *
   * @returns 廠商選項列表
   */
  async getVendorOptions(): Promise<VendorOption[]> {
    const response = await this.getVendors({ limit: 1000 });
    return response.items.map((vendor) => {
      const option: VendorOption = {
        id: vendor.id,
        vendor_name: vendor.vendor_name,
      };
      if (vendor.vendor_code) {
        option.vendor_code = vendor.vendor_code;
      }
      return option;
    });
  },

  /**
   * 搜尋廠商
   *
   * @param keyword 搜尋關鍵字
   * @param limit 最大數量
   * @returns 符合條件的廠商列表
   */
  async searchVendors(keyword: string, limit = 10): Promise<Vendor[]> {
    const response = await this.getVendors({
      search: keyword,
      limit,
    });
    return response.items;
  },

  /**
   * 批次刪除廠商
   *
   * @param vendorIds 要刪除的廠商 ID 列表
   * @returns 刪除結果（成功/失敗數量）
   */
  async batchDelete(
    vendorIds: number[]
  ): Promise<{
    success_count: number;
    failed_count: number;
    failed_ids: number[];
    errors: string[];
  }> {
    const results = await Promise.allSettled(
      vendorIds.map((id) => this.deleteVendor(id))
    );

    const successCount = results.filter((r) => r.status === 'fulfilled').length;
    const failedResults: { result: PromiseSettledResult<unknown>; id: number }[] = [];

    results.forEach((result, index) => {
      if (result.status === 'rejected') {
        failedResults.push({ result, id: vendorIds[index]! });
      }
    });

    return {
      success_count: successCount,
      failed_count: failedResults.length,
      failed_ids: failedResults.map((r) => r.id),
      errors: failedResults.map((r) =>
        r.result.status === 'rejected'
          ? (r.result.reason as Error).message
          : ''
      ),
    };
  },
};

// 預設匯出
export default vendorsApi;

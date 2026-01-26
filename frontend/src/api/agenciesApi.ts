/**
 * 機關單位管理 API 服務
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
import { API_ENDPOINTS } from './endpoints';

// 從 types/api.ts 匯入統一的機關型別
import {
  Agency,
  AgencyWithStats,
  AgencyCreate,
  AgencyUpdate,
  AgencyOption,
} from '../types/api';

// 重新匯出供外部使用
export type { Agency, AgencyWithStats, AgencyCreate, AgencyUpdate, AgencyOption };

/** 機關列表查詢參數 */
export interface AgencyListParams extends PaginationParams, SortParams {
  search?: string;
  agency_type?: string;
  include_stats?: boolean;
}

/** 分類統計 */
export interface CategoryStat {
  category: string;
  count: number;
  percentage: number;
}

/** 機關統計資料 */
export interface AgencyStatistics {
  total_agencies: number;
  categories: CategoryStat[];
}

// AgencyOption 已從 types/api.ts 匯入，不再重複定義

// ============================================================================
// API 方法
// ============================================================================

/**
 * 機關 API 服務
 */
export const agenciesApi = {
  /**
   * 取得機關列表
   *
   * @param params 查詢參數（分頁、搜尋、排序）
   * @returns 分頁機關列表
   */
  async getAgencies(
    params?: AgencyListParams
  ): Promise<PaginatedResponse<AgencyWithStats>> {
    // 構建查詢參數，過濾 undefined 值避免 422 錯誤
    const queryParams: Record<string, unknown> = {
      page: params?.page ?? 1,
      limit: params?.limit ?? 20,
      include_stats: params?.include_stats ?? true,
      sort_by: params?.sort_by ?? 'agency_name',
      sort_order: params?.sort_order ?? 'asc',
    };

    // 只添加有值的可選參數
    if (params?.search) queryParams.search = params.search;
    if (params?.agency_type) queryParams.agency_type = params.agency_type;

    try {
      // 使用新版 POST API
      return await apiClient.postList<AgencyWithStats>(API_ENDPOINTS.AGENCIES.LIST, queryParams);
    } catch (error) {
      // 若新 API 失敗，嘗試舊版格式（相容性）
      if (error instanceof ApiException && error.statusCode === 404) {
        const legacyParams: Record<string, unknown> = {
          skip: ((params?.page ?? 1) - 1) * (params?.limit ?? 20),
          limit: params?.limit ?? 100,
          include_stats: params?.include_stats ?? true,
        };
        if (params?.search) legacyParams.search = params.search;

        const response = await apiClient.get<{
          agencies: AgencyWithStats[];
          total: number;
          returned: number;
        }>(API_ENDPOINTS.AGENCIES.CREATE, {
          params: legacyParams,
        });
        // 轉換舊版格式
        return normalizePaginatedResponse(
          {
            items: response.agencies,
            total: response.total,
          } as LegacyListResponse<AgencyWithStats>,
          params?.page,
          params?.limit
        );
      }
      throw error;
    }
  },

  /**
   * 取得單一機關詳情
   *
   * @param agencyId 機關 ID
   * @returns 機關資料
   */
  async getAgency(agencyId: number): Promise<Agency> {
    return await apiClient.post<Agency>(API_ENDPOINTS.AGENCIES.DETAIL(agencyId));
  },

  /**
   * 建立新機關
   *
   * @param data 機關資料
   * @returns 新建的機關
   */
  async createAgency(data: AgencyCreate): Promise<Agency> {
    return await apiClient.post<Agency>(API_ENDPOINTS.AGENCIES.CREATE, data);
  },

  /**
   * 更新機關
   *
   * @param agencyId 機關 ID
   * @param data 更新資料
   * @returns 更新後的機關
   */
  async updateAgency(agencyId: number, data: AgencyUpdate): Promise<Agency> {
    return await apiClient.post<Agency>(API_ENDPOINTS.AGENCIES.UPDATE(agencyId), data);
  },

  /**
   * 刪除機關
   *
   * @param agencyId 機關 ID
   * @returns 刪除結果
   */
  async deleteAgency(agencyId: number): Promise<DeleteResponse> {
    return await apiClient.post<DeleteResponse>(API_ENDPOINTS.AGENCIES.DELETE(agencyId));
  },

  /**
   * 取得機關統計資料
   *
   * @returns 統計資料
   */
  async getStatistics(): Promise<AgencyStatistics> {
    return await apiClient.post<AgencyStatistics>(API_ENDPOINTS.AGENCIES.STATISTICS);
  },

  /**
   * 取得機關下拉選項
   *
   * 用於表單中的下拉選單
   *
   * @returns 機關選項列表
   */
  async getAgencyOptions(): Promise<AgencyOption[]> {
    const response = await this.getAgencies({ limit: 100, include_stats: false });
    return response.items.map((agency) => {
      const option: AgencyOption = {
        id: agency.id,
        agency_name: agency.agency_name,
      };
      if (agency.agency_code) {
        option.agency_code = agency.agency_code;
      }
      return option;
    });
  },

  /**
   * 搜尋機關
   *
   * @param keyword 搜尋關鍵字
   * @param limit 最大數量
   * @returns 符合條件的機關列表
   */
  async searchAgencies(keyword: string, limit = 10): Promise<AgencyWithStats[]> {
    const response = await this.getAgencies({
      search: keyword,
      limit,
    });
    return response.items;
  },
};

// 預設匯出
export default agenciesApi;

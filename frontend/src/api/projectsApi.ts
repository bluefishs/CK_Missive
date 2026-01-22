/**
 * 專案管理 API 服務
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
  SuccessResponse,
} from './types';
import {
  Project,
  ProjectCreate,
  ProjectUpdate,
  ProjectOption,
} from '../types/api';
import { API_ENDPOINTS } from './endpoints';

// ============================================================================
// 查詢參數型別
// ============================================================================

/** 專案列表查詢參數 */
export interface ProjectListParams extends PaginationParams, SortParams {
  search?: string;
  year?: number;
  category?: string;
  status?: string;
}

/** 專案統計資料 */
export interface ProjectStatistics {
  total_projects: number;
  status_breakdown: Array<{
    status: string;
    count: number;
  }>;
  year_breakdown: Array<{
    year: number;
    count: number;
  }>;
  average_contract_amount: number;
}

// ============================================================================
// API 方法
// ============================================================================

/**
 * 專案 API 服務
 */
export const projectsApi = {
  /**
   * 取得專案列表
   *
   * @param params 查詢參數（分頁、搜尋、排序）
   * @returns 分頁專案列表
   */
  async getProjects(
    params?: ProjectListParams
  ): Promise<PaginatedResponse<Project>> {
    // 構建查詢參數，過濾 undefined 值避免 422 錯誤
    const queryParams: Record<string, unknown> = {
      page: params?.page ?? 1,
      limit: params?.limit ?? 20,
      sort_by: params?.sort_by ?? 'year',  // 預設依年度排序
      sort_order: params?.sort_order ?? 'desc',  // 預設降冪排序
    };

    // 只添加有值的可選參數
    if (params?.search) queryParams.search = params.search;
    if (params?.year !== undefined) queryParams.year = params.year;
    if (params?.category) queryParams.category = params.category;
    if (params?.status) queryParams.status = params.status;

    try {
      // 使用新版 POST API
      return await apiClient.postList<Project>(API_ENDPOINTS.PROJECTS.LIST, queryParams);
    } catch (error) {
      // 若新 API 失敗，嘗試舊版格式（相容性）
      if (error instanceof ApiException && error.statusCode === 404) {
        const legacyParams: Record<string, unknown> = {
          skip: ((params?.page ?? 1) - 1) * (params?.limit ?? 20),
          limit: params?.limit ?? 100,
        };
        if (params?.search) legacyParams.search = params.search;
        if (params?.year !== undefined) legacyParams.year = params.year;
        if (params?.category) legacyParams.category = params.category;
        if (params?.status) legacyParams.status = params.status;

        const response = await apiClient.post<{
          projects: Project[];
          total: number;
          skip: number;
          limit: number;
        }>(API_ENDPOINTS.PROJECTS.LIST, legacyParams);
        // 轉換舊版格式
        return normalizePaginatedResponse(
          {
            items: response.projects,
            total: response.total,
          } as LegacyListResponse<Project>,
          params?.page,
          params?.limit
        );
      }
      throw error;
    }
  },

  /**
   * 取得單一專案詳情
   *
   * @param projectId 專案 ID
   * @returns 專案資料
   */
  async getProject(projectId: number): Promise<Project> {
    return await apiClient.post<Project>(API_ENDPOINTS.PROJECTS.DETAIL(projectId));
  },

  /**
   * 建立新專案
   *
   * @param data 專案資料
   * @returns 新建的專案
   */
  async createProject(data: ProjectCreate): Promise<Project> {
    return await apiClient.post<Project>(API_ENDPOINTS.PROJECTS.CREATE, data);
  },

  /**
   * 更新專案
   *
   * @param projectId 專案 ID
   * @param data 更新資料
   * @returns 更新後的專案
   */
  async updateProject(projectId: number, data: ProjectUpdate): Promise<Project> {
    return await apiClient.post<Project>(API_ENDPOINTS.PROJECTS.UPDATE(projectId), data);
  },

  /**
   * 刪除專案
   *
   * @param projectId 專案 ID
   * @returns 刪除結果
   */
  async deleteProject(projectId: number): Promise<DeleteResponse> {
    return await apiClient.post<DeleteResponse>(API_ENDPOINTS.PROJECTS.DELETE(projectId));
  },

  /**
   * 取得專案統計資料
   *
   * @returns 統計資料
   */
  async getStatistics(): Promise<ProjectStatistics> {
    const response = await apiClient.post<SuccessResponse<ProjectStatistics>>(
      API_ENDPOINTS.PROJECTS.STATISTICS
    );
    return response.data ?? {
      total_projects: 0,
      status_breakdown: [],
      year_breakdown: [],
      average_contract_amount: 0
    };
  },

  /**
   * 取得專案年度選項
   *
   * @returns 年度列表
   */
  async getYearOptions(): Promise<number[]> {
    const response = await apiClient.post<SuccessResponse<{ years: number[] }>>(
      API_ENDPOINTS.PROJECTS.YEARS
    );
    return response.data?.years ?? [];
  },

  /**
   * 取得專案類別選項
   *
   * @returns 類別列表
   */
  async getCategoryOptions(): Promise<string[]> {
    const response = await apiClient.post<SuccessResponse<{ categories: string[] }>>(
      API_ENDPOINTS.PROJECTS.CATEGORIES
    );
    return response.data?.categories ?? [];
  },

  /**
   * 取得專案狀態選項
   *
   * @returns 狀態列表
   */
  async getStatusOptions(): Promise<string[]> {
    const response = await apiClient.post<SuccessResponse<{ statuses: string[] }>>(
      API_ENDPOINTS.PROJECTS.STATUSES
    );
    return response.data?.statuses ?? [];
  },

  /**
   * 取得專案下拉選項
   *
   * 用於表單中的下拉選單
   *
   * @param year 可選的年度篩選
   * @returns 專案選項列表
   */
  async getProjectOptions(year?: number): Promise<ProjectOption[]> {
    const params: ProjectListParams = { limit: 1000 };
    if (year !== undefined) {
      params.year = year;
    }
    const response = await this.getProjects(params);
    return response.items.map((project) => {
      const option: ProjectOption = {
        id: project.id,
        project_name: project.project_name,
      };
      if (project.project_code) {
        option.project_code = project.project_code;
      }
      if (project.year) {
        option.year = project.year;
      }
      return option;
    });
  },

  /**
   * 搜尋專案
   *
   * @param keyword 搜尋關鍵字
   * @param limit 最大數量
   * @returns 符合條件的專案列表
   */
  async searchProjects(keyword: string, limit = 10): Promise<Project[]> {
    const response = await this.getProjects({
      search: keyword,
      limit,
    });
    return response.items;
  },
};

// 預設匯出
export default projectsApi;

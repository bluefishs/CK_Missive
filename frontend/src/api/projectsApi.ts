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
    const queryParams = {
      page: params?.page ?? 1,
      limit: params?.limit ?? 20,
      search: params?.search,
      year: params?.year,
      category: params?.category,
      status: params?.status,
      sort_by: params?.sort_by ?? 'year',  // 預設依年度排序
      sort_order: params?.sort_order ?? 'desc',  // 預設降冪排序
    };

    try {
      // 使用新版 POST API
      return await apiClient.postList<Project>('/projects/list', queryParams);
    } catch (error) {
      // 若新 API 失敗，嘗試舊版格式（相容性）
      if (error instanceof ApiException && error.statusCode === 404) {
        const response = await apiClient.post<{
          projects: Project[];
          total: number;
          skip: number;
          limit: number;
        }>('/projects/list', {
          skip: ((params?.page ?? 1) - 1) * (params?.limit ?? 20),
          limit: params?.limit ?? 100,
          search: params?.search,
          year: params?.year,
          category: params?.category,
          status: params?.status,
        });
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
    return await apiClient.post<Project>(`/projects/${projectId}/detail`);
  },

  /**
   * 建立新專案
   *
   * @param data 專案資料
   * @returns 新建的專案
   */
  async createProject(data: ProjectCreate): Promise<Project> {
    return await apiClient.post<Project>('/projects', data);
  },

  /**
   * 更新專案
   *
   * @param projectId 專案 ID
   * @param data 更新資料
   * @returns 更新後的專案
   */
  async updateProject(projectId: number, data: ProjectUpdate): Promise<Project> {
    return await apiClient.post<Project>(`/projects/${projectId}/update`, data);
  },

  /**
   * 刪除專案
   *
   * @param projectId 專案 ID
   * @returns 刪除結果
   */
  async deleteProject(projectId: number): Promise<DeleteResponse> {
    return await apiClient.post<DeleteResponse>(`/projects/${projectId}/delete`);
  },

  /**
   * 取得專案統計資料
   *
   * @returns 統計資料
   */
  async getStatistics(): Promise<ProjectStatistics> {
    const response = await apiClient.post<SuccessResponse<ProjectStatistics>>(
      '/projects/statistics'
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
      '/projects/years'
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
      '/projects/categories'
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
      '/projects/statuses'
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

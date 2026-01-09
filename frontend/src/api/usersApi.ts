/**
 * 使用者管理 API 服務
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

// ============================================================================
// 型別定義
// ============================================================================

/** 使用者基礎介面 */
export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  role?: string;
  is_active: boolean;
  last_login?: string;
  created_at?: string;
}

/** 使用者建立請求 */
export interface UserCreate {
  username: string;
  email: string;
  full_name?: string;
  role?: string;
  is_active?: boolean;
  password: string;
}

/** 使用者更新請求 */
export interface UserUpdate {
  email?: string;
  full_name?: string;
  role?: string;
  is_active?: boolean;
  password?: string;
}

/** 使用者狀態更新請求 */
export interface UserStatusUpdate {
  is_active: boolean;
}

/** 使用者選項（下拉選單用） */
export interface UserOption {
  id: number;
  username: string;
  full_name?: string;
}

/** 使用者列表查詢參數 */
export interface UserListParams extends PaginationParams, SortParams {
  search?: string;
  role?: string;
  is_active?: boolean;
}

// ============================================================================
// API 方法
// ============================================================================

/**
 * 使用者 API 服務
 */
export const usersApi = {
  /**
   * 取得使用者列表
   *
   * @param params 查詢參數（分頁、搜尋、排序）
   * @returns 分頁使用者列表
   */
  async getUsers(
    params?: UserListParams
  ): Promise<PaginatedResponse<User>> {
    const queryParams = {
      page: params?.page ?? 1,
      limit: params?.limit ?? 20,
      search: params?.search,
      role: params?.role,
      is_active: params?.is_active,
      sort_by: params?.sort_by ?? 'id',
      sort_order: params?.sort_order ?? 'asc',
    };

    try {
      // 使用新版 POST API
      return await apiClient.postList<User>(API_ENDPOINTS.USERS.LIST, queryParams);
    } catch (error) {
      // 若新 API 失敗，嘗試舊版格式（相容性）
      if (error instanceof ApiException && error.statusCode === 404) {
        const response = await apiClient.post<{
          items: User[];
          total: number;
          page: number;
          page_size: number;
          total_pages: number;
        }>(API_ENDPOINTS.USERS.LIST, {
          skip: ((params?.page ?? 1) - 1) * (params?.limit ?? 20),
          limit: params?.limit ?? 100,
          search: params?.search,
          role: params?.role,
          is_active: params?.is_active,
        });
        // 轉換舊版格式
        return normalizePaginatedResponse(
          {
            items: response.items,
            total: response.total,
          } as LegacyListResponse<User>,
          params?.page,
          params?.limit
        );
      }
      throw error;
    }
  },

  /**
   * 取得單一使用者詳情
   *
   * @param userId 使用者 ID
   * @returns 使用者資料
   */
  async getUser(userId: number): Promise<User> {
    return await apiClient.post<User>(API_ENDPOINTS.USERS.DETAIL(userId));
  },

  /**
   * 建立新使用者
   *
   * @param data 使用者資料
   * @returns 新建的使用者
   */
  async createUser(data: UserCreate): Promise<User> {
    return await apiClient.post<User>(API_ENDPOINTS.USERS.CREATE, data);
  },

  /**
   * 更新使用者
   *
   * @param userId 使用者 ID
   * @param data 更新資料
   * @returns 更新後的使用者
   */
  async updateUser(userId: number, data: UserUpdate): Promise<User> {
    return await apiClient.post<User>(API_ENDPOINTS.USERS.UPDATE(userId), data);
  },

  /**
   * 刪除使用者
   *
   * @param userId 使用者 ID
   * @returns 刪除結果
   */
  async deleteUser(userId: number): Promise<DeleteResponse> {
    return await apiClient.post<DeleteResponse>(API_ENDPOINTS.USERS.DELETE(userId));
  },

  /**
   * 更新使用者狀態
   *
   * @param userId 使用者 ID
   * @param isActive 是否啟用
   * @returns 更新後的使用者
   */
  async updateUserStatus(userId: number, isActive: boolean): Promise<User> {
    return await apiClient.post<User>(API_ENDPOINTS.USERS.STATUS(userId), {
      is_active: isActive,
    });
  },

  /**
   * 取得使用者下拉選項
   *
   * 用於表單中的下拉選單
   *
   * @param activeOnly 是否只取啟用的使用者
   * @returns 使用者選項列表
   */
  async getUserOptions(activeOnly = true): Promise<UserOption[]> {
    const params: UserListParams = { limit: 1000 };
    if (activeOnly) {
      params.is_active = true;
    }
    const response = await this.getUsers(params);
    return response.items.map((user) => {
      const option: UserOption = {
        id: user.id,
        username: user.username,
      };
      if (user.full_name) {
        option.full_name = user.full_name;
      }
      return option;
    });
  },

  /**
   * 搜尋使用者
   *
   * @param keyword 搜尋關鍵字
   * @param limit 最大數量
   * @returns 符合條件的使用者列表
   */
  async searchUsers(keyword: string, limit = 10): Promise<User[]> {
    const response = await this.getUsers({
      search: keyword,
      limit,
    });
    return response.items;
  },
};

// 預設匯出
export default usersApi;

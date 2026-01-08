/**
 * 管理員使用者管理 API
 *
 * 提供使用者帳號、角色與權限的管理功能
 * 使用 /admin/user-management 端點
 */

import { apiClient } from './client';
import type { PaginatedResponse } from './types';
import type { User, Permission, UserPermissions } from '../types/user';

// ============================================================================
// 型別定義
// ============================================================================

/** 使用者列表查詢參數 */
export interface AdminUserListParams {
  page?: number;
  per_page?: number;
  q?: string;
  role?: string;
  auth_provider?: string;
  status?: string;
}

/** 使用者建立/更新請求 */
export interface AdminUserUpdate {
  username?: string;
  email?: string;
  full_name?: string;
  role?: string;
  status?: string;
  is_active?: boolean;
  password?: string;
}

/** 使用者權限更新請求 */
export interface AdminPermissionUpdate {
  user_id: number;
  permissions: string[];
  role: string;
}

/** 使用者列表回應 */
export interface AdminUserListResponse {
  users: User[];
  total: number;
  page: number;
  per_page: number;
}

/** 可用權限回應 */
export interface AvailablePermissionsResponse {
  roles: Permission[];
  permissions?: string[];
}

// ============================================================================
// API 方法
// ============================================================================

export const adminUsersApi = {
  /**
   * 取得使用者列表
   */
  async getUsers(params?: AdminUserListParams): Promise<AdminUserListResponse> {
    const queryString = new URLSearchParams();
    if (params?.page) queryString.append('page', String(params.page));
    if (params?.per_page) queryString.append('per_page', String(params.per_page));
    if (params?.q) queryString.append('q', params.q);
    if (params?.role) queryString.append('role', params.role);
    if (params?.auth_provider) queryString.append('auth_provider', params.auth_provider);

    const url = `/admin/user-management/users${queryString.toString() ? '?' + queryString.toString() : ''}`;
    return await apiClient.get<AdminUserListResponse>(url);
  },

  /**
   * 取得可用權限列表
   */
  async getAvailablePermissions(): Promise<AvailablePermissionsResponse> {
    return await apiClient.get<AvailablePermissionsResponse>(
      '/admin/user-management/permissions/available'
    );
  },

  /**
   * 取得使用者權限
   */
  async getUserPermissions(userId: number): Promise<UserPermissions> {
    return await apiClient.get<UserPermissions>(
      `/admin/user-management/users/${userId}/permissions`
    );
  },

  /**
   * 建立使用者
   */
  async createUser(data: AdminUserUpdate): Promise<User> {
    return await apiClient.post<User>('/admin/user-management/users', data);
  },

  /**
   * 更新使用者
   */
  async updateUser(userId: number, data: AdminUserUpdate): Promise<User> {
    return await apiClient.put<User>(`/admin/user-management/users/${userId}`, data);
  },

  /**
   * 刪除使用者
   */
  async deleteUser(userId: number): Promise<void> {
    await apiClient.delete(`/admin/user-management/users/${userId}`);
  },

  /**
   * 更新使用者權限
   */
  async updateUserPermissions(
    userId: number,
    data: AdminPermissionUpdate
  ): Promise<UserPermissions> {
    return await apiClient.put<UserPermissions>(
      `/admin/user-management/users/${userId}/permissions`,
      data
    );
  },

  /**
   * 批量更新使用者狀態
   */
  async batchUpdateStatus(
    userIds: number[],
    status: string,
    isActive: boolean
  ): Promise<void> {
    await Promise.all(
      userIds.map((userId) =>
        apiClient.put(`/admin/user-management/users/${userId}`, {
          status,
          is_active: isActive,
        })
      )
    );
  },

  /**
   * 批量刪除使用者
   */
  async batchDelete(userIds: number[]): Promise<void> {
    await Promise.all(
      userIds.map((userId) =>
        apiClient.delete(`/admin/user-management/users/${userId}`)
      )
    );
  },

  /**
   * 批量驗證使用者角色
   */
  async batchUpdateRole(
    userIds: number[],
    role: string,
    permissions: string[]
  ): Promise<void> {
    await Promise.all(
      userIds.map(async (userId) => {
        await apiClient.put(`/admin/user-management/users/${userId}`, {
          role,
          status: 'active',
          is_active: true,
        });
        await apiClient.put(`/admin/user-management/users/${userId}/permissions`, {
          user_id: userId,
          permissions,
          role,
        });
      })
    );
  },
};

export default adminUsersApi;

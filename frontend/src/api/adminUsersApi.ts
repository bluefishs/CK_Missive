/**
 * 管理員使用者管理 API
 *
 * 提供使用者帳號、角色與權限的管理功能
 * 使用 /admin/user-management 端點
 *
 * @version 2.0.0 - POST-only 安全模式
 * @date 2026-01-11
 */

import { apiClient } from './client';
import { API_ENDPOINTS } from './endpoints';
import type {
  User,
  UserPermissions,
  UserSession,
  AdminUserListParams,
  AdminUserUpdate,
  AdminPermissionUpdate,
  AdminUserListResponse,
  AvailablePermissionsResponse,
} from '../types/api';

// 重新匯出型別供外部使用
export type {
  AdminUserListParams,
  AdminUserUpdate,
  AdminPermissionUpdate,
  AdminUserListResponse,
  AvailablePermissionsResponse,
  UserSession,
};

// ============================================================================
// API 方法 (POST-only 安全模式)
// ============================================================================

export const adminUsersApi = {
  /**
   * 取得使用者列表 (POST)
   */
  async getUsers(params?: AdminUserListParams): Promise<AdminUserListResponse> {
    const requestBody = {
      skip: params?.skip ?? ((params?.page ?? 1) - 1) * (params?.per_page ?? 20),
      limit: params?.limit ?? params?.per_page ?? 20,
      search: params?.search ?? params?.q,
      role: params?.role,
      auth_provider: params?.auth_provider,
      status: params?.status,
    };

    const response = await apiClient.post<AdminUserListResponse>(
      API_ENDPOINTS.ADMIN_USER_MANAGEMENT.USERS_LIST,
      requestBody
    );

    // 相容性處理：統一回傳格式
    return {
      users: response.users || response.items || [],
      items: response.items || response.users || [],
      total: response.total || 0,
      page: params?.page || 1,
      per_page: params?.per_page || 20,
      skip: response.skip,
      limit: response.limit,
    };
  },

  /**
   * 取得可用權限列表 (POST)
   */
  async getAvailablePermissions(): Promise<AvailablePermissionsResponse> {
    return await apiClient.post<AvailablePermissionsResponse>(
      API_ENDPOINTS.ADMIN_USER_MANAGEMENT.PERMISSIONS_AVAILABLE
    );
  },

  /**
   * 取得使用者權限 (POST)
   */
  async getUserPermissions(userId: number): Promise<UserPermissions> {
    return await apiClient.post<UserPermissions>(
      API_ENDPOINTS.ADMIN_USER_MANAGEMENT.USERS_PERMISSIONS_DETAIL(userId)
    );
  },

  /**
   * 取得使用者詳情 (POST)
   */
  async getUserDetail(userId: number): Promise<User> {
    return await apiClient.post<User>(
      API_ENDPOINTS.ADMIN_USER_MANAGEMENT.USERS_DETAIL(userId)
    );
  },

  /**
   * 建立使用者 (POST)
   */
  async createUser(data: AdminUserUpdate): Promise<User> {
    return await apiClient.post<User>(
      API_ENDPOINTS.ADMIN_USER_MANAGEMENT.USERS_CREATE,
      data
    );
  },

  /**
   * 更新使用者 (POST)
   */
  async updateUser(userId: number, data: AdminUserUpdate): Promise<User> {
    return await apiClient.post<User>(
      API_ENDPOINTS.ADMIN_USER_MANAGEMENT.USERS_UPDATE(userId),
      data
    );
  },

  /**
   * 刪除使用者 (POST)
   */
  async deleteUser(userId: number): Promise<void> {
    await apiClient.post(
      API_ENDPOINTS.ADMIN_USER_MANAGEMENT.USERS_DELETE(userId)
    );
  },

  /**
   * 更新使用者權限 (POST)
   */
  async updateUserPermissions(
    userId: number,
    data: AdminPermissionUpdate
  ): Promise<UserPermissions> {
    return await apiClient.post<UserPermissions>(
      API_ENDPOINTS.ADMIN_USER_MANAGEMENT.USERS_PERMISSIONS_UPDATE(userId),
      data
    );
  },

  /**
   * 取得使用者會話列表 (POST)
   */
  async getUserSessions(userId: number): Promise<UserSession[]> {
    const response = await apiClient.post<{ sessions: UserSession[] }>(
      API_ENDPOINTS.ADMIN_USER_MANAGEMENT.USERS_SESSIONS_LIST(userId)
    );
    return response.sessions || [];
  },

  /**
   * 撤銷會話 (POST)
   */
  async revokeSession(sessionId: number): Promise<void> {
    await apiClient.post(
      API_ENDPOINTS.ADMIN_USER_MANAGEMENT.SESSIONS_REVOKE(sessionId)
    );
  },

  /**
   * 批量更新使用者狀態 (POST)
   */
  async batchUpdateStatus(
    userIds: number[],
    status: string,
    isActive: boolean
  ): Promise<void> {
    await Promise.all(
      userIds.map((userId) =>
        apiClient.post(
          API_ENDPOINTS.ADMIN_USER_MANAGEMENT.USERS_UPDATE(userId),
          {
            status,
            is_active: isActive,
          }
        )
      )
    );
  },

  /**
   * 批量刪除使用者 (POST)
   */
  async batchDelete(userIds: number[]): Promise<void> {
    await Promise.all(
      userIds.map((userId) =>
        apiClient.post(
          API_ENDPOINTS.ADMIN_USER_MANAGEMENT.USERS_DELETE(userId)
        )
      )
    );
  },

  /**
   * 批量更新使用者角色 (POST)
   */
  async batchUpdateRole(
    userIds: number[],
    role: string,
    permissions: string[]
  ): Promise<void> {
    await Promise.all(
      userIds.map(async (userId) => {
        await apiClient.post(
          API_ENDPOINTS.ADMIN_USER_MANAGEMENT.USERS_UPDATE(userId),
          {
            role,
            status: 'active',
            is_active: true,
          }
        );
        await apiClient.post(
          API_ENDPOINTS.ADMIN_USER_MANAGEMENT.USERS_PERMISSIONS_UPDATE(userId),
          {
            user_id: userId,
            permissions,
            role,
          }
        );
      })
    );
  },
};

export default adminUsersApi;

/**
 * ADR-0034 動態 Role Permissions API client（POST-only）。
 *
 * 對應 PermissionManagementPage 動態編輯介面。
 */
import { apiClient } from './client';
import { ADMIN_USER_MANAGEMENT_ENDPOINTS } from './endpoints/users';
// 型別 SSOT（development-rules §3）：本檔不得宣告業務型別。
// 2026-08-29 由此處搬入 `types/navigation.ts`，這裡只 re-export 供既有呼叫端不動。
export type { RolePermissionDetail, RolePermissionsListResponse, RolePermissionsGetResponse, AvailablePermissionsResponse, UpdateRolePermissionsResponse, SyncUsersResponse, NavTreeNode, NavTreeResponse } from '../types/navigation';
import type { RolePermissionsListResponse, RolePermissionsGetResponse, AvailablePermissionsResponse, UpdateRolePermissionsResponse, SyncUsersResponse, NavTreeResponse } from '../types/navigation';

export const rolePermissionsApi = {
  /** 列所有 role 配置 */
  async list(): Promise<RolePermissionsListResponse> {
    return apiClient.post<RolePermissionsListResponse>(
      ADMIN_USER_MANAGEMENT_ENDPOINTS.ROLE_PERMISSIONS_LIST,
      {},
    );
  },

  /** 取單一 role 詳情 */
  async get(role: string): Promise<RolePermissionsGetResponse> {
    return apiClient.post<RolePermissionsGetResponse>(
      ADMIN_USER_MANAGEMENT_ENDPOINTS.ROLE_PERMISSIONS_GET,
      { role },
    );
  },

  /** 更新 role permissions（admin 限定） */
  async update(
    role: string,
    permissions: string[],
    note?: string,
  ): Promise<UpdateRolePermissionsResponse> {
    return apiClient.post<UpdateRolePermissionsResponse>(
      ADMIN_USER_MANAGEMENT_ENDPOINTS.ROLE_PERMISSIONS_UPDATE_DYNAMIC,
      { role, permissions, note },
    );
  },

  /** 取得系統可分派的 permission 全集（含 unassigned 紅點提示） */
  async getAvailable(): Promise<AvailablePermissionsResponse> {
    return apiClient.post<AvailablePermissionsResponse>(
      ADMIN_USER_MANAGEMENT_ENDPOINTS.ROLE_PERMISSIONS_AVAILABLE,
      {},
    );
  },

  /** 批次同步指定 role 的所有 user.permissions 為最新 role_permissions */
  async syncUsers(role: string, onlyOutdated = true): Promise<SyncUsersResponse> {
    return apiClient.post<SyncUsersResponse>(
      ADMIN_USER_MANAGEMENT_ENDPOINTS.ROLE_PERMISSIONS_SYNC_USERS,
      { role, only_outdated: onlyOutdated },
    );
  },

  /** 取 nav 階層樹 + perm 反查（給「依選單階層」編輯介面） */
  async getNavTree(role?: string): Promise<NavTreeResponse> {
    return apiClient.post<NavTreeResponse>(
      ADMIN_USER_MANAGEMENT_ENDPOINTS.ROLE_PERMISSIONS_NAV_TREE,
      role ? { role } : {},
    );
  },
};

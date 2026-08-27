/**
 * ADR-0034 動態 Role Permissions API client（POST-only）。
 *
 * 對應 PermissionManagementPage 動態編輯介面。
 */
import { apiClient } from './client';
import { ADMIN_USER_MANAGEMENT_ENDPOINTS } from './endpoints/users';

export interface RolePermissionDetail {
  role: string;
  permissions: string[];
  can_login: boolean;
  name_zh: string | null;
  description_zh: string | null;
  permission_count: number;
  is_wildcard: boolean;
  updated_at: string | null;
  updated_by: number | null;
  /**
   * 該 role 有幾位**在職**使用者的權限還沒對齊角色定義。
   *
   * 2026-08-27 新增。改角色權限**不會**動到既有使用者
   * （`role_permissions` 只在建立新帳號那一刻被讀一次），
   * 而儲存成功的訊息讀起來就是「做完了」——owner 因此以為設定生效了。
   * 這個數字讓「還沒生效」變成看得見的事實；已對齊時是 0，畫面就不出聲。
   *
   * 只在 `/get` 與 `/update` 回傳；`/list` 沒有（那一頁不需要，且要多 N 次查詢）。
   */
  pending_sync_users?: number;
}

export interface RolePermissionsListResponse {
  success: boolean;
  items: RolePermissionDetail[];
  total: number;
}

export interface RolePermissionsGetResponse {
  success: boolean;
  role: RolePermissionDetail;
}

export interface AvailablePermissionsResponse {
  success: boolean;
  all: string[];
  assigned: string[];
  unassigned: string[];
  from_navigation_items: string[];
  from_business_endpoints: string[];
  total_count: number;
  unassigned_count: number;
}

export interface UpdateRolePermissionsResponse {
  success: boolean;
  role: RolePermissionDetail;
  message: string;
}

export interface SyncUsersResponse {
  success: boolean;
  message: string;
  role: string;
  scanned: number;
  updated: number;
  skipped: number;
  updated_users: Array<{
    id: number;
    email: string;
    full_name: string;
    before_count: number;
    after_count: number;
  }>;
  skipped_users: Array<{ id: number; email: string; reason: string }>;
}

export interface NavTreeNode {
  id: number;
  parent_id: number | null;
  key: string;
  title: string;
  path: string | null;
  level: number;
  sort_order: number;
  is_enabled: boolean;
  is_visible: boolean;
  permission_required: string[];
  children: NavTreeNode[];
}

export interface NavTreeResponse {
  success: boolean;
  tree: NavTreeNode[];
  role: string | null;
  role_permissions: string[];
  perm_to_nav: Record<string, Array<{ id: number; key: string; title: string }>>;
  is_wildcard: boolean;
}

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

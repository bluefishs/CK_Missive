/** api-user — 使用者/權限/管理員型別 */

// ============================================================================
// 使用者 (User) 相關型別
// ============================================================================

/** 使用者角色 */
export type UserRole = 'unverified' | 'user' | 'staff' | 'admin' | 'superuser';

/** 使用者狀態 */
export type UserStatus = 'active' | 'inactive' | 'suspended' | 'pending';

/** 使用者基礎介面 - 單一真實來源 (Single Source of Truth) */
export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_admin: boolean;
  is_superuser?: boolean;
  role?: string;
  auth_provider?: string;
  avatar_url?: string;
  permissions?: string | string[];
  login_count?: number;
  last_login?: string;
  email_verified?: boolean;
  created_at: string;
  updated_at?: string;
  // 狀態相關欄位
  status?: UserStatus;
  verification_status?: string;
  suspended_reason?: string;
  can_login?: boolean;
  // 組織相關欄位
  department?: string;
  position?: string;
  // MFA 雙因素認證
  mfa_enabled?: boolean;
  // LINE Login 整合
  line_user_id?: string;
  line_display_name?: string;
  // 多 provider 追蹤
  google_id?: string;
  auth_providers?: string[];
}

/** 使用者選項（下拉選單用） */
export interface UserOption {
  id: number;
  username: string;
  full_name?: string;
  email?: string;
}

/** 權限定義 */
export interface Permission {
  name: string;
  display_name: string;
  default_permissions: string[];
}

/** 使用者權限 */
export interface UserPermissions {
  user_id: number;
  permissions: string[];
  role: string;
}

/** 使用者表單資料 */
export interface UserFormData {
  email: string;
  username: string;
  full_name?: string;
  password?: string;
  role: string;
  status: string;
  is_admin?: boolean;
  suspended_reason?: string;
}

/** 使用者分頁 */
export interface UserPagination {
  current: number;
  pageSize: number;
  total: number;
}

// ============================================================================
// 管理員使用者管理 (Admin User Management) 相關型別
// ============================================================================

/** 使用者列表查詢參數 */
export interface AdminUserListParams {
  page?: number;
  per_page?: number;
  limit?: number;
  skip?: number;
  q?: string;
  search?: string;
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
  items?: User[];
  total: number;
  page?: number;
  per_page?: number;
  skip?: number;
  limit?: number;
}

/** 可用權限回應 */
export interface AvailablePermissionsResponse {
  roles: Permission[];
  permissions?: string[];
}

// ============================================================================
// 使用者 CRUD 請求型別
// ============================================================================

/** 使用者建立請求 */
export interface UserCreate {
  username: string;
  email: string;
  full_name?: string;
  role?: string;
  is_active?: boolean;
  password: string;
  department?: string;
  position?: string;
}

/** 使用者更新請求 */
export interface UserUpdate {
  email?: string;
  full_name?: string;
  role?: string;
  is_active?: boolean;
  password?: string;
  department?: string;
  position?: string;
}

/** 使用者狀態更新請求 */
export interface UserStatusUpdate {
  is_active: boolean;
}

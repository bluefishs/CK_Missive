/**
 * 使用者管理相關型別定義
 * @description 從 UserManagementPage.tsx 提取
 */

export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string;
  is_active: boolean;
  is_admin: boolean;
  auth_provider: string;
  avatar_url?: string;
  role: string;
  status: string;
  created_at: string;
  last_login?: string;
  login_count: number;
  email_verified: boolean;
  verification_status?: string;
  suspended_reason?: string;
  can_login?: boolean;
}

export interface Permission {
  name: string;
  display_name: string;
  default_permissions: string[];
}

export interface UserPermissions {
  user_id: number;
  permissions: string[];
  role: string;
}

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

export interface UserPagination {
  current: number;
  pageSize: number;
  total: number;
}

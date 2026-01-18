/**
 * 使用者管理相關型別定義
 * @description 從 UserManagementPage.tsx 提取
 *
 * 注意: User 型別統一從 types/api.ts 匯入，此處只保留表單相關專用型別
 */

// 從 types/api.ts 匯入統一的 User 型別
export type { User, UserStatus } from './api';

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

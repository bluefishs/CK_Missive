/**
 * 表單型別集中管理 (SSOT)
 *
 * 所有頁面的 form interface 統一在此定義，避免重複。
 * 欄位名稱保持與 Ant Design Form.Item name 一致（即後端 API 欄位名）。
 *
 * @version 1.0.0
 * @date 2026-02-21
 */

// ============================================================================
// 認證相關 Forms
// ============================================================================

export interface LoginFormValues {
  username: string;
  password: string;
}

export interface RegisterFormValues {
  email: string;
  username: string;
  full_name: string;
  password: string;
  confirmPassword: string;
  agreement: boolean;
}

export interface ResetPasswordFormValues {
  new_password: string;
  confirm_password: string;
}

export interface ForgotPasswordFormValues {
  email: string;
}

// ============================================================================
// 公文相關 Forms
// ============================================================================

export interface DocumentFormValues {
  title?: string;
  type?: string;
  agency?: string;
  priority?: string;
  contract_case?: string[];
  content?: string;
  notes?: string;
  status?: string;
}

// ============================================================================
// 導覽管理 Forms
// ============================================================================

export interface NavigationFormValues {
  title: string;
  key: string;
  path?: string;
  icon: string;
  description?: string;
  parent_id: number | null;
  level: number;
  sort_order?: number;
  is_visible: boolean;
  is_enabled: boolean;
  permission_required?: string;
  target?: string;
}

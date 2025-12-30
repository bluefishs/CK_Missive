/**
 * 導覽列相關型別定義
 * @description 從 NavigationManagement.tsx 提取
 */

export interface NavigationItem {
  id: number;
  title: string;
  key: string;
  path?: string;
  icon?: string;
  parent_id?: number;
  sort_order: number;
  is_visible: boolean;
  is_enabled: boolean;
  level: number;
  description?: string;
  target: string;
  permission_required?: string;
  created_at?: string;
  updated_at?: string;
  children?: NavigationItem[];
}

export interface NavigationFormData {
  title: string;
  key: string;
  path?: string;
  icon?: string;
  parent_id?: number;
  sort_order: number;
  is_visible: boolean;
  is_enabled: boolean;
  level: number;
  description?: string;
  target: string;
  permission_required?: string;
}

export interface ParentOption {
  value: number;
  label: string;
}

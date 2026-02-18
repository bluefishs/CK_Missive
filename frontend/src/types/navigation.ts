/**
 * 導覽列相關型別定義
 * @description 整合共用模組 (site-management-module) 型別
 * @version 2.0.0 - 2026-01-09
 */

// ============ 核心資料型別 ============

export interface NavigationItem {
  id: number;
  title: string;
  key: string;
  path?: string;
  icon?: string;
  parent_id: number | null;
  sort_order: number;
  is_visible: boolean;
  is_enabled: boolean;
  level: number;
  description?: string;
  target?: string;
  permission_required?: string;
  created_at?: string;
  updated_at?: string;
  children?: NavigationItem[];
  // 擴展欄位 - 可添加自訂資料
  metadata?: Record<string, unknown>;
}

export interface NavigationFormData {
  title: string;
  key: string;
  path?: string;
  icon?: string;
  parent_id: number | null;
  sort_order: number;
  is_visible: boolean;
  is_enabled: boolean;
  level: number;
  description?: string;
  target?: string;
  permission_required?: string;
  metadata?: Record<string, unknown>;
}

export interface ParentOption {
  value: number;
  label: string;
}

// ============ 配置型別 ============

export interface IconOption {
  value: string;
  label: string;
  icon?: React.ReactNode;
}

export interface PermissionOption {
  value: string;
  label: string;
  description?: string;
}

export interface PermissionGroup {
  label: string;
  options: PermissionOption[];
}

// ============ API 服務介面 ============

export interface NavigationApiService {
  /** 取得所有導覽項目 */
  getItems: () => Promise<{ items: NavigationItem[] }>;
  /** 建立導覽項目 */
  createItem: (data: NavigationFormData) => Promise<NavigationItem>;
  /** 更新導覽項目 */
  updateItem: (data: Partial<NavigationFormData> & { id: number }) => Promise<NavigationItem>;
  /** 刪除導覽項目 */
  deleteItem: (id: number) => Promise<void>;
}

// ============ 組件配置 ============

export interface NavigationManagementConfig {
  // 外觀配置
  title?: string;
  showSearch?: boolean;
  showViewToggle?: boolean;
  defaultViewMode?: 'tree' | 'table';

  // 功能配置
  enableCreate?: boolean;
  enableEdit?: boolean;
  enableDelete?: boolean;
  enableStatusToggle?: boolean;
  enableDragSort?: boolean;

  // 欄位配置
  showPermissionColumn?: boolean;
  showDescriptionColumn?: boolean;

  // 國際化
  labels?: Partial<NavigationLabels>;
}

export interface NavigationLabels {
  addButton: string;
  editButton: string;
  deleteButton: string;
  treeView: string;
  tableView: string;
  searchPlaceholder: string;
  confirmDelete: string;
  confirmDeleteDescription: string;
  confirmOk: string;
  confirmCancel: string;
  createSuccess: string;
  updateSuccess: string;
  deleteSuccess: string;
  operationFailed: string;
}

// ============ 表單標籤 ============

export interface FormLabels {
  title: string;
  key: string;
  path: string;
  icon: string;
  parent: string;
  level: string;
  sortOrder: string;
  description: string;
  target: string;
  isVisible: string;
  isEnabled: string;
  permission: string;
  submit: string;
  update: string;
  cancel: string;
  addTitle: string;
  editTitle: string;
}

// ============ 預設值 ============

export const defaultLabels: NavigationLabels = {
  addButton: '新增導覽項目',
  editButton: '編輯',
  deleteButton: '刪除',
  treeView: '樹狀檢視',
  tableView: '表格檢視',
  searchPlaceholder: '搜尋導覽項目',
  confirmDelete: '確定要刪除這個項目嗎？',
  confirmDeleteDescription: '此操作無法復原',
  confirmOk: '確定',
  confirmCancel: '取消',
  createSuccess: '新增成功',
  updateSuccess: '更新成功',
  deleteSuccess: '刪除成功',
  operationFailed: '操作失敗',
};

export const defaultConfig: NavigationManagementConfig = {
  title: '導覽列管理',
  showSearch: true,
  showViewToggle: true,
  defaultViewMode: 'tree',
  enableCreate: true,
  enableEdit: true,
  enableDelete: true,
  enableStatusToggle: true,
  enableDragSort: false,
  showPermissionColumn: true,
  showDescriptionColumn: false,
  labels: defaultLabels,
};

export const defaultFormLabels: FormLabels = {
  title: '標題',
  key: '唯一鍵值',
  path: '路由路徑',
  icon: '圖示',
  parent: '父級項目',
  level: '層級',
  sortOrder: '排序順序',
  description: '描述',
  target: '開啟方式',
  isVisible: '是否可見',
  isEnabled: '是否啟用',
  permission: '所需權限',
  submit: '新增',
  update: '更新',
  cancel: '取消',
  addTitle: '新增導覽項目',
  editTitle: '編輯導覽項目',
};

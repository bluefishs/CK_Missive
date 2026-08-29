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


// ── 2026-08-29：型別 SSOT 收斂（development-rules §3）──────────────
// 原本宣告在 `src/api/rolePermissionsApi.ts` —— 規範明文禁止 api/*.ts 定義業務型別，
// 而**前端一直沒有機制在強制**（後端 2026-08-17 才補上 weekly 59，
// 當時累積出 18 個違規無人知曉；前端是同一個故事的另一半）。
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


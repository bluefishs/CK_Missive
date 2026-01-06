/**
 * 導覽列配置常數
 * @description 從 NavigationManagement.tsx 提取
 */

// 圖示選項
export const ICON_OPTIONS = [
  'dashboard', 'file-text', 'number', 'folder', 'project', 'team',
  'setting', 'user', 'global', 'database', 'bug', 'bar-chart', 'calendar'
];

// 模組名稱對照
export const MODULE_NAMES: Record<string, string> = {
  'documents': '公文',
  'projects': '案件',
  'agencies': '單位',
  'vendors': '廠商',
  'reports': '報表',
  'calendar': '行事曆'
};

// 操作名稱對照
export const ACTION_NAMES: Record<string, string> = {
  'read': '檢視',
  'create': '新增',
  'edit': '編輯',
  'delete': '刪除',
  'export': '匯出',
  'view': '檢視'
};

// 權限選項群組
export interface PermissionOption {
  value: string;
  label: string;
}

export interface PermissionGroup {
  label: string;
  options: PermissionOption[];
}

export const PERMISSION_GROUPS: PermissionGroup[] = [
  {
    label: '公文管理',
    options: [
      { value: 'documents:read', label: '公文：檢視' },
      { value: 'documents:create', label: '公文：新增' },
      { value: 'documents:edit', label: '公文：編輯' },
      { value: 'documents:delete', label: '公文：刪除' },
      { value: 'documents:export', label: '公文：匯出' },
    ]
  },
  {
    label: '承攬案件',
    options: [
      { value: 'projects:read', label: '案件：檢視' },
      { value: 'projects:create', label: '案件：新增' },
      { value: 'projects:edit', label: '案件：編輯' },
      { value: 'projects:delete', label: '案件：刪除' },
    ]
  },
  {
    label: '機關單位',
    options: [
      { value: 'agencies:read', label: '單位：檢視' },
      { value: 'agencies:create', label: '單位：新增' },
      { value: 'agencies:edit', label: '單位：編輯' },
      { value: 'agencies:delete', label: '單位：刪除' },
    ]
  },
  {
    label: '廠商管理',
    options: [
      { value: 'vendors:read', label: '廠商：檢視' },
      { value: 'vendors:create', label: '廠商：新增' },
      { value: 'vendors:edit', label: '廠商：編輯' },
      { value: 'vendors:delete', label: '廠商：刪除' },
    ]
  },
  {
    label: '統計報表',
    options: [
      { value: 'reports:view', label: '報表：檢視' },
      { value: 'reports:export', label: '報表：匯出' },
    ]
  },
  {
    label: '行事曆',
    options: [
      { value: 'calendar:read', label: '行事曆：檢視' },
      { value: 'calendar:edit', label: '行事曆：編輯' },
    ]
  },
  {
    label: '系統管理',
    options: [
      { value: 'admin:users', label: '使用者管理' },
      { value: 'admin:settings', label: '系統設定' },
      { value: 'admin:database', label: '資料庫管理' },
      { value: 'admin:site_management', label: '網站管理' },
    ]
  },
  {
    label: '角色限制',
    options: [
      { value: 'role:admin', label: '管理員以上' },
      { value: 'role:superuser', label: '超級管理員專用' },
    ]
  },
  {
    label: '其他功能',
    options: [
      { value: 'notifications:read', label: '通知：檢視' },
      { value: 'api:access', label: 'API 存取' },
    ]
  }
];

/**
 * 格式化權限標籤
 */
export const formatPermissionLabel = (permission: string | undefined): { label: string; color: string } => {
  if (!permission) {
    return { label: '無限制', color: 'green' };
  }

  if (permission.startsWith('admin:')) {
    return { label: permission.replace('admin:', '系統：'), color: 'red' };
  }

  if (permission.startsWith('role:')) {
    return { label: permission.replace('role:', '角色：'), color: 'purple' };
  }

  if (permission.includes(':')) {
    const parts = permission.split(':');
    const module = parts[0] ?? '';
    const action = parts[1] ?? '';
    const moduleName = MODULE_NAMES[module] || module;
    const actionName = ACTION_NAMES[action] || action;
    return { label: `${moduleName}：${actionName}`, color: 'cyan' };
  }

  return { label: permission, color: 'blue' };
};

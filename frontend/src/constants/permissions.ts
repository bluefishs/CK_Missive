/**
 * 權限管理中英對照配置
 */

export interface Permission {
  key: string;
  name_zh: string;
  name_en: string;
  category: string;
  description_zh?: string;
  description_en?: string;
}

export interface PermissionCategory {
  key: string;
  name_zh: string;
  name_en: string;
  permissions: Permission[];
}

// 權限類別定義
export const PERMISSION_CATEGORIES: Record<string, PermissionCategory> = {
  documents: {
    key: 'documents',
    name_zh: '公文管理',
    name_en: 'Document Management',
    permissions: [
      {
        key: 'documents:read',
        name_zh: '檢視公文',
        name_en: 'View Documents',
        category: 'documents',
        description_zh: '可以查看公文內容和清單',
        description_en: 'Can view document content and lists'
      },
      {
        key: 'documents:create',
        name_zh: '建立公文',
        name_en: 'Create Documents',
        category: 'documents',
        description_zh: '可以建立新的公文',
        description_en: 'Can create new documents'
      },
      {
        key: 'documents:edit',
        name_zh: '編輯公文',
        name_en: 'Edit Documents',
        category: 'documents',
        description_zh: '可以修改現有公文',
        description_en: 'Can modify existing documents'
      },
      {
        key: 'documents:delete',
        name_zh: '刪除公文',
        name_en: 'Delete Documents',
        category: 'documents',
        description_zh: '可以刪除公文',
        description_en: 'Can delete documents'
      }
    ]
  },
  projects: {
    key: 'projects',
    name_zh: '專案管理',
    name_en: 'Project Management',
    permissions: [
      {
        key: 'projects:read',
        name_zh: '檢視專案',
        name_en: 'View Projects',
        category: 'projects',
        description_zh: '可以查看專案資訊',
        description_en: 'Can view project information'
      },
      {
        key: 'projects:create',
        name_zh: '建立專案',
        name_en: 'Create Projects',
        category: 'projects',
        description_zh: '可以建立新專案',
        description_en: 'Can create new projects'
      },
      {
        key: 'projects:edit',
        name_zh: '編輯專案',
        name_en: 'Edit Projects',
        category: 'projects',
        description_zh: '可以修改專案資訊',
        description_en: 'Can modify project information'
      },
      {
        key: 'projects:delete',
        name_zh: '刪除專案',
        name_en: 'Delete Projects',
        category: 'projects',
        description_zh: '可以刪除專案',
        description_en: 'Can delete projects'
      }
    ]
  },
  agencies: {
    key: 'agencies',
    name_zh: '機關管理',
    name_en: 'Agency Management',
    permissions: [
      {
        key: 'agencies:read',
        name_zh: '檢視機關',
        name_en: 'View Agencies',
        category: 'agencies',
        description_zh: '可以查看機關資訊',
        description_en: 'Can view agency information'
      },
      {
        key: 'agencies:create',
        name_zh: '建立機關',
        name_en: 'Create Agencies',
        category: 'agencies',
        description_zh: '可以建立新機關',
        description_en: 'Can create new agencies'
      },
      {
        key: 'agencies:edit',
        name_zh: '編輯機關',
        name_en: 'Edit Agencies',
        category: 'agencies',
        description_zh: '可以修改機關資訊',
        description_en: 'Can modify agency information'
      },
      {
        key: 'agencies:delete',
        name_zh: '刪除機關',
        name_en: 'Delete Agencies',
        category: 'agencies',
        description_zh: '可以刪除機關',
        description_en: 'Can delete agencies'
      }
    ]
  },
  vendors: {
    key: 'vendors',
    name_zh: '廠商管理',
    name_en: 'Vendor Management',
    permissions: [
      {
        key: 'vendors:read',
        name_zh: '檢視廠商',
        name_en: 'View Vendors',
        category: 'vendors',
        description_zh: '可以查看廠商資訊',
        description_en: 'Can view vendor information'
      },
      {
        key: 'vendors:create',
        name_zh: '建立廠商',
        name_en: 'Create Vendors',
        category: 'vendors',
        description_zh: '可以建立新廠商',
        description_en: 'Can create new vendors'
      },
      {
        key: 'vendors:edit',
        name_zh: '編輯廠商',
        name_en: 'Edit Vendors',
        category: 'vendors',
        description_zh: '可以修改廠商資訊',
        description_en: 'Can modify vendor information'
      },
      {
        key: 'vendors:delete',
        name_zh: '刪除廠商',
        name_en: 'Delete Vendors',
        category: 'vendors',
        description_zh: '可以刪除廠商',
        description_en: 'Can delete vendors'
      }
    ]
  },
  calendar: {
    key: 'calendar',
    name_zh: '行事曆管理',
    name_en: 'Calendar Management',
    permissions: [
      {
        key: 'calendar:read',
        name_zh: '檢視行事曆',
        name_en: 'View Calendar',
        category: 'calendar',
        description_zh: '可以查看行事曆事件',
        description_en: 'Can view calendar events'
      },
      {
        key: 'calendar:edit',
        name_zh: '編輯行事曆',
        name_en: 'Edit Calendar',
        category: 'calendar',
        description_zh: '可以編輯行事曆事件',
        description_en: 'Can edit calendar events'
      }
    ]
  },
  reports: {
    key: 'reports',
    name_zh: '報表管理',
    name_en: 'Report Management',
    permissions: [
      {
        key: 'reports:view',
        name_zh: '檢視報表',
        name_en: 'View Reports',
        category: 'reports',
        description_zh: '可以查看系統報表',
        description_en: 'Can view system reports'
      },
      {
        key: 'reports:export',
        name_zh: '匯出報表',
        name_en: 'Export Reports',
        category: 'reports',
        description_zh: '可以匯出報表資料',
        description_en: 'Can export report data'
      }
    ]
  },
  system_docs: {
    key: 'system_docs',
    name_zh: '系統文件',
    name_en: 'System Documents',
    permissions: [
      {
        key: 'system_docs:read',
        name_zh: '檢視系統文件',
        name_en: 'View System Documents',
        category: 'system_docs',
        description_zh: '可以檢視系統文件和技術文檔',
        description_en: 'Can view system documents and technical documentation'
      },
      {
        key: 'system_docs:create',
        name_zh: '建立系統文件',
        name_en: 'Create System Documents',
        category: 'system_docs',
        description_zh: '可以建立新的系統文件',
        description_en: 'Can create new system documents'
      },
      {
        key: 'system_docs:edit',
        name_zh: '編輯系統文件',
        name_en: 'Edit System Documents',
        category: 'system_docs',
        description_zh: '可以修改現有系統文件',
        description_en: 'Can modify existing system documents'
      },
      {
        key: 'system_docs:delete',
        name_zh: '刪除系統文件',
        name_en: 'Delete System Documents',
        category: 'system_docs',
        description_zh: '可以刪除系統文件',
        description_en: 'Can delete system documents'
      }
    ]
  },
  admin: {
    key: 'admin',
    name_zh: '系統管理',
    name_en: 'System Administration',
    permissions: [
      {
        key: 'admin:users',
        name_zh: '使用者管理',
        name_en: 'User Management',
        category: 'admin',
        description_zh: '可以管理系統使用者',
        description_en: 'Can manage system users'
      },
      {
        key: 'admin:settings',
        name_zh: '系統設定',
        name_en: 'System Settings',
        category: 'admin',
        description_zh: '可以修改系統設定',
        description_en: 'Can modify system settings'
      },
      {
        key: 'admin:site_management',
        name_zh: '網站管理',
        name_en: 'Site Management',
        category: 'admin',
        description_zh: '可以管理網站內容',
        description_en: 'Can manage site content'
      }
    ]
  }
};

/**
 * 根據權限鍵值取得權限資訊
 */
export const getPermissionInfo = (permissionKey: string): Permission | undefined => {
  for (const category of Object.values(PERMISSION_CATEGORIES)) {
    const permission = category.permissions.find(p => p.key === permissionKey);
    if (permission) {
      return permission;
    }
  }
  return undefined;
};

/**
 * 取得權限的顯示名稱
 */
export const getPermissionDisplayName = (permissionKey: string, language: 'zh' | 'en' = 'zh'): string => {
  const permission = getPermissionInfo(permissionKey);
  if (!permission) {
    return permissionKey;
  }
  return language === 'zh' ? permission.name_zh : permission.name_en;
};

/**
 * 取得權限類別的顯示名稱
 */
export const getCategoryDisplayName = (categoryKey: string, language: 'zh' | 'en' = 'zh'): string => {
  const category = PERMISSION_CATEGORIES[categoryKey];
  if (!category) {
    return categoryKey;
  }
  return language === 'zh' ? category.name_zh : category.name_en;
};

/**
 * 根據權限清單分組
 */
export const groupPermissionsByCategory = (permissions: string[]): Record<string, Permission[]> => {
  const grouped: Record<string, Permission[]> = {};

  permissions.forEach(permKey => {
    const permission = getPermissionInfo(permKey);
    if (permission) {
      const category = permission.category;
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category]!.push(permission);
    }
  });

  return grouped;
};

// 使用者角色定義
export const USER_ROLES = {
  unverified: {
    key: 'unverified',
    name_zh: '未驗證者',
    name_en: 'Unverified User',
    description_zh: '新註冊使用者，需要管理者驗證後才能使用系統',
    description_en: 'New registered user, requires admin verification before using the system',
    default_permissions: [], // 無任何權限
    can_login: false // 不能登入系統
  },
  user: {
    key: 'user',
    name_zh: '一般使用者',
    name_en: 'Regular User',
    description_zh: '已驗證的一般使用者，具備基本檢視權限',
    description_en: 'Verified regular user with basic view permissions',
    default_permissions: [
      'documents:read',
      'projects:read',
      'agencies:read',
      'vendors:read',
      'calendar:read'
    ],
    can_login: true
  },
  admin: {
    key: 'admin',
    name_zh: '管理員',
    name_en: 'Administrator',
    description_zh: '系統管理員，具備大部分管理權限',
    description_en: 'System administrator with most management permissions',
    default_permissions: [
      'documents:read', 'documents:create', 'documents:edit',
      'projects:read', 'projects:create', 'projects:edit',
      'agencies:read', 'agencies:create', 'agencies:edit',
      'vendors:read', 'vendors:create', 'vendors:edit',
      'calendar:read', 'calendar:edit',
      'reports:view', 'reports:export',
      'admin:users'
    ],
    can_login: true
  },
  superuser: {
    key: 'superuser',
    name_zh: '超級管理員',
    name_en: 'Super Administrator',
    description_zh: '系統超級管理員，具備所有權限',
    description_en: 'System super administrator with all permissions',
    default_permissions: Object.values(PERMISSION_CATEGORIES)
      .flatMap(category => category.permissions.map(p => p.key)),
    can_login: true
  }
};

// 使用者狀態定義
export const USER_STATUSES = {
  active: {
    key: 'active',
    name_zh: '啟用',
    name_en: 'Active',
    description_zh: '使用者帳戶正常啟用',
    description_en: 'User account is active',
    can_login: true
  },
  inactive: {
    key: 'inactive', 
    name_zh: '停用',
    name_en: 'Inactive',
    description_zh: '使用者帳戶已停用，保留記錄但無法登入',
    description_en: 'User account is disabled, records preserved but cannot login',
    can_login: false
  },
  pending: {
    key: 'pending',
    name_zh: '待驗證',
    name_en: 'Pending Verification',
    description_zh: '新使用者等待管理者驗證',
    description_en: 'New user awaiting admin verification',
    can_login: false
  },
  suspended: {
    key: 'suspended',
    name_zh: '暫停',
    name_en: 'Suspended',
    description_zh: '使用者帳戶暫時暫停，可由管理者恢復',
    description_en: 'User account temporarily suspended, can be restored by admin',
    can_login: false
  }
};

/**
 * 獲取角色顯示名稱
 */
export const getRoleDisplayName = (roleKey: string, language: 'zh' | 'en' = 'zh'): string => {
  const role = USER_ROLES[roleKey as keyof typeof USER_ROLES];
  if (!role) return roleKey;
  return language === 'zh' ? role.name_zh : role.name_en;
};

/**
 * 獲取狀態顯示名稱
 */
export const getStatusDisplayName = (statusKey: string, language: 'zh' | 'en' = 'zh'): string => {
  const status = USER_STATUSES[statusKey as keyof typeof USER_STATUSES];
  if (!status) return statusKey;
  return language === 'zh' ? status.name_zh : status.name_en;
};

/**
 * 檢查角色是否可以登入
 */
export const canRoleLogin = (roleKey: string): boolean => {
  const role = USER_ROLES[roleKey as keyof typeof USER_ROLES];
  return role ? role.can_login : false;
};

/**
 * 檢查狀態是否可以登入
 */
export const canStatusLogin = (statusKey: string): boolean => {
  const status = USER_STATUSES[statusKey as keyof typeof USER_STATUSES];
  return status ? status.can_login : false;
};

/**
 * 獲取角色預設權限
 */
export const getRoleDefaultPermissions = (roleKey: string): string[] => {
  const role = USER_ROLES[roleKey as keyof typeof USER_ROLES];
  return role ? role.default_permissions : [];
};
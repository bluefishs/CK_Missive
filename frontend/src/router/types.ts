export interface RouteConfig {
  path: string;
  name: string;
  component: React.ComponentType<any>;
  exact?: boolean;
  children?: RouteConfig[];
  meta?: {
    title: string;
    description?: string;
    requireAuth?: boolean;
    roles?: string[];
    icon?: string;
    hideInMenu?: boolean;
    breadcrumb?: boolean;
  };
}

// 路由常量
export const ROUTES = {
  HOME: '/',
  DOCUMENTS: '/documents',
  DOCUMENT_DETAIL: '/documents/:id',
  DOCUMENT_CREATE: '/documents/create',
  DOCUMENT_EDIT: '/documents/:id/edit',
  DASHBOARD: '/dashboard',
  SETTINGS: '/settings',
  PROFILE: '/profile',
  DATABASE: '/admin/database',
  USER_MANAGEMENT: '/admin/user-management',
  CONTRACT_CASES: '/contract-cases',
  CONTRACT_CASE_DETAIL: '/contract-cases/:id',
  CONTRACT_CASE_CREATE: '/contract-cases/create',
  CONTRACT_CASE_EDIT: '/contract-cases/:id/edit',
  CASES: '/cases',
  CASE_DETAIL: '/cases/:id',
  CASE_CREATE: '/cases/create',
  CASE_EDIT: '/cases/:id/edit',
  DOCUMENT_NUMBERS: '/document-numbers',
  AGENCIES: '/agencies',
  VENDORS: '/vendors',
  STAFF: '/staff',
  PROJECTS: '/projects',
  CALENDAR: '/calendar',
  REPORTS: '/reports',
  SITE_MANAGEMENT: '/admin/site-management',
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
  NOT_FOUND: '/404',
  API_MAPPING: '/api-mapping', // 新增 API 對應頁面路由
  API_DOCS: '/api/docs', // API 文件頁面路由
  PERMISSION_MANAGEMENT: '/admin/permissions',
  SYSTEM: '/system',
  DOCUMENT_WORKFLOW: '/documents/workflow',
  DOCUMENT_IMPORT: '/documents/import',
  DOCUMENT_EXPORT: '/documents/export',
  UNIFIED_FORM_DEMO: '/unified-form-demo',
  PURE_CALENDAR: '/pure-calendar',
  GOOGLE_AUTH_DIAGNOSTIC: '/google-auth-diagnostic',
  ADMIN_DASHBOARD: '/admin/dashboard',
} as const;

// 路由元數據
export const ROUTE_META = {
  [ROUTES.HOME]: {
    title: '首頁',
    description: '系統首頁',
    icon: 'Home',
  },
  [ROUTES.API_MAPPING]: { // 新增 API 對應頁面元數據
    title: 'API 對應',
    description: '前端功能與後端 API 對應關係',
    icon: 'Api', // 使用一個通用的 API 圖標
  },
  [ROUTES.API_DOCS]: {
    title: 'API 文件',
    description: '系統 API 完整文件與測試介面',
    icon: 'FileTextOutlined',
  },
  [ROUTES.DOCUMENTS]: {
    title: '公文管理',
    description: '公文列表與管理',
    icon: 'Description',
  },
  [ROUTES.DOCUMENT_DETAIL]: {
    title: '公文詳情',
    description: '檢視公文詳細內容',
    breadcrumb: true,
  },
  [ROUTES.DOCUMENT_CREATE]: {
    title: '新增公文',
    description: '建立新的公文',
    breadcrumb: true,
  },
  [ROUTES.DOCUMENT_EDIT]: {
    title: '編輯公文',
    description: '編輯現有公文',
    breadcrumb: true,
  },
  [ROUTES.DASHBOARD]: {
    title: '儀表板',
    description: '系統總覽與統計',
    icon: 'Dashboard',
  },
  [ROUTES.SETTINGS]: {
    title: '系統設定',
    description: '系統配置與設定',
    icon: 'Settings',
    requireAuth: true,
  },
  [ROUTES.PROFILE]: {
    title: '個人資料',
    description: '使用者個人資料設定',
    icon: 'Person',
    requireAuth: true,
  },
  [ROUTES.DATABASE]: {
    title: '資料庫管理',
    description: '資料庫維護與管理',
    icon: 'Database',
    requireAuth: true,
  },
  [ROUTES.USER_MANAGEMENT]: {
    title: '帳號權限管理',
    description: '使用者帳號與權限管理',
    icon: 'UserOutlined',
    requireAuth: true,
    roles: ['admin', 'superuser'],
  },
  [ROUTES.CONTRACT_CASES]: {
    title: '承攬案件管理',
    description: '承攬案件維護與管理',
    icon: 'ProjectOutlined',
  },
  [ROUTES.CONTRACT_CASE_DETAIL]: {
    title: '承攬案件詳情',
    description: '檢視承攬案件詳細內容',
    breadcrumb: true,
  },
  [ROUTES.CONTRACT_CASE_CREATE]: {
    title: '新增承攬案件',
    description: '建立新的承攬案件',
    breadcrumb: true,
  },
  [ROUTES.CONTRACT_CASE_EDIT]: {
    title: '編輯承攬案件',
    description: '編輯現有承攬案件',
    breadcrumb: true,
  },
  [ROUTES.CASES]: {
    title: '承攬案件管理',
    description: '承攬案件維護與管理',
    icon: 'ProjectOutlined',
  },
  [ROUTES.CASE_DETAIL]: {
    title: '承攬案件詳情',
    description: '檢視承攬案件詳細內容',
    breadcrumb: true,
  },
  [ROUTES.CASE_CREATE]: {
    title: '新增承攬案件',
    description: '建立新的承攬案件',
    breadcrumb: true,
  },
  [ROUTES.CASE_EDIT]: {
    title: '編輯承攬案件',
    description: '編輯現有承攬案件',
    breadcrumb: true,
  },
  [ROUTES.DOCUMENT_NUMBERS]: {
    title: '發文字號管理',
    description: '發文字號清單與填報作業',
    icon: 'NumberOutlined',
  },
  [ROUTES.AGENCIES]: {
    title: '機關單位管理',
    description: '機關單位清單與統計資訊',
    icon: 'BankOutlined',
  },
  [ROUTES.VENDORS]: {
    title: '廠商管理',
    description: '協力廠商清單與管理',
    icon: 'ShopOutlined',
  },
  [ROUTES.STAFF]: {
    title: '承辦同仁',
    description: '承辦同仁清單與管理',
    icon: 'TeamOutlined',
  },
  [ROUTES.PROJECTS]: {
    title: '承攬案件',
    description: '承攬案件與廠商關聯管理',
    icon: 'ProjectOutlined',
  },
  [ROUTES.CALENDAR]: {
    title: '行事曆',
    description: '行事曆管理與排程',
    icon: 'CalendarOutlined',
  },
  [ROUTES.REPORTS]: {
    title: '統計報表',
    description: '各種統計分析報表',
    icon: 'BarChartOutlined',
  },
  [ROUTES.SITE_MANAGEMENT]: {
    title: '網站管理',
    description: '導覽列與網站配置管理',
    icon: 'GlobalOutlined',
    requireAuth: true,
  },
} as const;

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
  ENTRY: '/entry',  // 系統入口頁面
  DOCUMENTS: '/documents',
  DOCUMENT_DETAIL: '/documents/:id',
  DOCUMENT_CREATE: '/documents/create',
  DOCUMENT_EDIT: '/documents/:id/edit',
  DASHBOARD: '/dashboard',
  SETTINGS: '/settings',
  PROFILE: '/profile',
  DATABASE: '/admin/database',
  USER_MANAGEMENT: '/admin/user-management',
  USER_CREATE: '/admin/user-management/create',
  USER_EDIT: '/admin/user-management/:id/edit',
  CONTRACT_CASES: '/contract-cases',
  CONTRACT_CASE_DETAIL: '/contract-cases/:id',
  CONTRACT_CASE_CREATE: '/contract-cases/create',
  CONTRACT_CASE_EDIT: '/contract-cases/:id/edit',
  DOCUMENT_NUMBERS: '/document-numbers',
  SEND_DOCUMENT_CREATE: '/document-numbers/create',
  AGENCIES: '/agencies',
  AGENCY_CREATE: '/agencies/create',
  AGENCY_EDIT: '/agencies/:id/edit',
  VENDORS: '/vendors',
  VENDOR_CREATE: '/vendors/create',
  VENDOR_EDIT: '/vendors/:id/edit',
  STAFF: '/staff',
  STAFF_CREATE: '/staff/create',
  STAFF_DETAIL: '/staff/:id',
  // 證照管理（導航模式）
  CERTIFICATION_CREATE: '/staff/:userId/certifications/create',
  CERTIFICATION_EDIT: '/staff/:userId/certifications/:certId/edit',
  PROJECTS: '/projects',
  CALENDAR: '/calendar',
  CALENDAR_EVENT_CREATE: '/calendar/event/new',
  CALENDAR_EVENT_EDIT: '/calendar/event/:id/edit',
  PURE_CALENDAR: '/pure-calendar', // 重導向至 /calendar
  REPORTS: '/reports',
  SITE_MANAGEMENT: '/admin/site-management',
  LOGIN: '/login',
  MFA_VERIFY: '/mfa/verify',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: '/reset-password',
  VERIFY_EMAIL: '/verify-email',
  NOT_FOUND: '/404',
  API_MAPPING: '/api-mapping', // 新增 API 對應頁面路由
  API_DOCS: '/api/docs', // API 文件頁面路由
  PERMISSION_MANAGEMENT: '/admin/permissions',
  PERMISSION_ROLE_DETAIL: '/admin/permissions/:role',  // 角色權限詳情頁
  SYSTEM: '/system',
  UNIFIED_FORM_DEMO: '/unified-form-demo',
  GOOGLE_AUTH_DIAGNOSTIC: '/google-auth-diagnostic',
  ADMIN_DASHBOARD: '/admin/dashboard',
  BACKUP_MANAGEMENT: '/admin/backup',
  DEPLOYMENT_MANAGEMENT: '/admin/deployment',
  // AI 管理（同義詞與 Prompt 管理已整合至 AI 助理管理 Tab 分頁）
  AI_ASSISTANT_MANAGEMENT: '/admin/ai-assistant',
  // 桃園查估專區
  TAOYUAN_DISPATCH: '/taoyuan/dispatch',
  TAOYUAN_DISPATCH_CREATE: '/taoyuan/dispatch/create',
  TAOYUAN_DISPATCH_DETAIL: '/taoyuan/dispatch/:id',
  TAOYUAN_PROJECT_CREATE: '/taoyuan/project/create',
  TAOYUAN_PROJECT_DETAIL: '/taoyuan/project/:id',
  // 作業歷程（導航模式）
  TAOYUAN_WORKFLOW_CREATE: '/taoyuan/dispatch/:dispatchId/workflow/create',
  TAOYUAN_WORKFLOW_EDIT: '/taoyuan/dispatch/:dispatchId/workflow/:recordId/edit',
} as const;

// 路由元數據
export const ROUTE_META = {
  [ROUTES.HOME]: {
    title: '首頁',
    description: '系統首頁',
    icon: 'Home',
  },
  [ROUTES.ENTRY]: {
    title: '系統入口',
    description: '乾坤測繪公文系統入口',
    icon: 'LoginOutlined',
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
  [ROUTES.DOCUMENT_NUMBERS]: {
    title: '發文字號管理',
    description: '發文字號清單與填報作業',
    icon: 'NumberOutlined',
  },
  [ROUTES.SEND_DOCUMENT_CREATE]: {
    title: '新增發文',
    description: '建立新的發文公文',
    breadcrumb: true,
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
  [ROUTES.CERTIFICATION_CREATE]: {
    title: '新增證照',
    description: '新增承辦同仁證照',
    breadcrumb: true,
  },
  [ROUTES.CERTIFICATION_EDIT]: {
    title: '編輯證照',
    description: '編輯承辦同仁證照',
    breadcrumb: true,
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
  [ROUTES.CALENDAR_EVENT_CREATE]: {
    title: '新增日曆事件',
    description: '建立新的日曆事件',
    breadcrumb: true,
  },
  [ROUTES.CALENDAR_EVENT_EDIT]: {
    title: '編輯日曆事件',
    description: '編輯日曆事件詳情',
    breadcrumb: true,
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
  [ROUTES.BACKUP_MANAGEMENT]: {
    title: '備份管理',
    description: '系統備份、異地同步與排程管理',
    icon: 'CloudServerOutlined',
    requireAuth: true,
  },
  [ROUTES.DEPLOYMENT_MANAGEMENT]: {
    title: '部署管理',
    description: '系統部署狀態監控與操作',
    icon: 'RocketOutlined',
    requireAuth: true,
    roles: ['admin', 'superuser'],
  },
  [ROUTES.AI_ASSISTANT_MANAGEMENT]: {
    title: 'AI 助理管理',
    description: 'AI 助理統一管理儀表板',
    icon: 'DashboardOutlined',
    requireAuth: true,
    roles: ['admin', 'superuser'],
  },
  [ROUTES.TAOYUAN_DISPATCH]: {
    title: '派工管理',
    description: '桃園查估專區 - 派工管理',
    icon: 'ScheduleOutlined',
  },
  [ROUTES.TAOYUAN_DISPATCH_DETAIL]: {
    title: '派工詳情',
    description: '桃園查估專區 - 派工單詳細資訊',
    icon: 'SendOutlined',
    hideInMenu: true,
  },
  [ROUTES.TAOYUAN_PROJECT_DETAIL]: {
    title: '工程詳情',
    description: '桃園查估專區 - 轄管工程詳細資訊',
    icon: 'ProjectOutlined',
    hideInMenu: true,
  },
  [ROUTES.TAOYUAN_PROJECT_CREATE]: {
    title: '新增工程',
    description: '桃園查估專區 - 新增轄管工程',
    icon: 'PlusOutlined',
    hideInMenu: true,
  },
  [ROUTES.MFA_VERIFY]: {
    title: 'MFA 驗證',
    description: '雙因素認證驗證',
    icon: 'SafetyOutlined',
  },
  [ROUTES.RESET_PASSWORD]: {
    title: '重設密碼',
    description: '設定新密碼',
    icon: 'LockOutlined',
  },
  [ROUTES.VERIFY_EMAIL]: {
    title: 'Email 驗證',
    description: '驗證您的電子郵件',
    icon: 'MailOutlined',
  },
  [ROUTES.TAOYUAN_DISPATCH_CREATE]: {
    title: '新增派工單',
    description: '桃園查估專區 - 新增派工單',
    icon: 'PlusOutlined',
    hideInMenu: true,
  },
  [ROUTES.TAOYUAN_WORKFLOW_CREATE]: {
    title: '新增作業紀錄',
    description: '桃園查估專區 - 新增作業歷程紀錄',
    breadcrumb: true,
  },
  [ROUTES.TAOYUAN_WORKFLOW_EDIT]: {
    title: '編輯作業紀錄',
    description: '桃園查估專區 - 編輯作業歷程紀錄',
    breadcrumb: true,
  },
} as const;

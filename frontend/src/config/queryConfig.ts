/**
 * React Query 查詢鍵與快取配置
 *
 * 統一管理所有 API 查詢的 key 和快取策略
 */

// ============================================================================
// 查詢鍵定義
// ============================================================================

export const queryKeys = {
  // 公文相關
  documents: {
    all: ['documents'] as const,
    lists: () => [...queryKeys.documents.all, 'list'] as const,
    list: (filters: object) => [...queryKeys.documents.lists(), filters] as const,
    details: () => [...queryKeys.documents.all, 'detail'] as const,
    detail: (id: number) => [...queryKeys.documents.details(), id] as const,
    statistics: ['documents', 'statistics'] as const,
    years: ['documents', 'years'] as const,
  },

  // 專案相關
  projects: {
    all: ['projects'] as const,
    lists: () => [...queryKeys.projects.all, 'list'] as const,
    list: (filters: object) => [...queryKeys.projects.lists(), filters] as const,
    details: () => [...queryKeys.projects.all, 'detail'] as const,
    detail: (id: number) => [...queryKeys.projects.details(), id] as const,
    staff: (projectId: number) => ['projects', projectId, 'staff'] as const,
    vendors: (projectId: number) => ['projects', projectId, 'vendors'] as const,
    documents: (projectId: number) => ['projects', projectId, 'documents'] as const,
    statistics: ['projects', 'statistics'] as const,
  },

  // 廠商相關
  vendors: {
    all: ['vendors'] as const,
    lists: () => [...queryKeys.vendors.all, 'list'] as const,
    list: (filters: object) => [...queryKeys.vendors.lists(), filters] as const,
    details: () => [...queryKeys.vendors.all, 'detail'] as const,
    detail: (id: number) => [...queryKeys.vendors.details(), id] as const,
    dropdown: ['vendors', 'dropdown'] as const,
  },

  // 機關相關
  agencies: {
    all: ['agencies'] as const,
    lists: () => [...queryKeys.agencies.all, 'list'] as const,
    list: (filters: object) => [...queryKeys.agencies.lists(), filters] as const,
    details: () => [...queryKeys.agencies.all, 'detail'] as const,
    detail: (id: number) => [...queryKeys.agencies.details(), id] as const,
    dropdown: ['agencies', 'dropdown'] as const,
    statistics: ['agencies', 'statistics'] as const,
  },

  // 使用者相關
  users: {
    all: ['users'] as const,
    lists: () => [...queryKeys.users.all, 'list'] as const,
    list: (filters: object) => [...queryKeys.users.lists(), filters] as const,
    details: () => [...queryKeys.users.all, 'detail'] as const,
    detail: (id: number) => [...queryKeys.users.details(), id] as const,
    dropdown: ['users', 'dropdown'] as const,
    current: ['users', 'current'] as const,
  },

  // 行事曆相關
  calendar: {
    all: ['calendar'] as const,
    events: () => [...queryKeys.calendar.all, 'events'] as const,
    googleStatus: () => [...queryKeys.calendar.all, 'googleStatus'] as const,
  },

  // 儀表板行事曆
  dashboardCalendar: {
    all: ['dashboardCalendar'] as const,
    events: () => [...queryKeys.dashboardCalendar.all, 'events'] as const,
  },

  // 通知
  notifications: {
    all: ['notifications'] as const,
    unreadCount: ['notifications-unread-count'] as const,
    list: ['notifications-list'] as const,
  },

  // 桃園派工
  taoyuanDispatch: {
    all: ['taoyuan-dispatch-orders'] as const,
    orders: (params?: object) => ['taoyuan-dispatch-orders', ...(params ? [params] : [])] as const,
    order: (orderId: number | undefined) => ['taoyuan-dispatch-order', orderId] as const,
  },

  // 桃園專案
  taoyuanProjects: {
    all: ['taoyuan-projects'] as const,
    list: (params?: object) => ['taoyuan-projects', ...(params ? [params] : [])] as const,
    detail: (projectId: number | undefined) => ['taoyuan-project', projectId] as const,
  },

  // 桃園契金
  taoyuanPayments: {
    all: ['payment-control'] as const,
    byDispatch: (dispatchOrderId: number) => ['taoyuan-payments', dispatchOrderId] as const,
    paymentControl: (projectId: number) => ['payment-control', projectId] as const,
  },

  // 公文關聯搜尋
  documentRelations: {
    allDispatches: ['dispatch-orders-for-link'] as const,
    dispatchOrders: (keyword: string) => ['dispatch-orders-for-link', keyword] as const,
    allProjects: ['projects-for-link'] as const,
    projects: (keyword: string) => ['projects-for-link', keyword] as const,
  },

  // AI 同義詞管理
  aiSynonyms: {
    all: ['ai', 'synonyms'] as const,
    lists: () => [...queryKeys.aiSynonyms.all, 'list'] as const,
    list: (filters: object) => [...queryKeys.aiSynonyms.lists(), filters] as const,
  },

  // AI Prompt 版本管理
  aiPrompts: {
    all: ['ai', 'prompts'] as const,
    lists: () => [...queryKeys.aiPrompts.all, 'list'] as const,
    list: (feature?: string | null) => [...queryKeys.aiPrompts.lists(), feature] as const,
  },

  // AI 分析持久化
  aiAnalysis: {
    all: ['ai', 'analysis'] as const,
    detail: (documentId: number) => ['ai', 'analysis', documentId] as const,
    stats: ['ai', 'analysis', 'stats'] as const,
  },
} as const;

// ============================================================================
// 快取時間配置（毫秒）
// ============================================================================

export const staleTimeConfig = {
  // 下拉選單 - 較長快取（10 分鐘）
  dropdown: 10 * 60 * 1000,

  // 列表資料 - 中等快取（30 秒）
  list: 30 * 1000,

  // 詳情資料 - 中等快取（1 分鐘）
  detail: 60 * 1000,

  // 統計資料 - 較長快取（5 分鐘）
  statistics: 5 * 60 * 1000,

  // 年度選項 - 長快取（1 天）
  years: 24 * 60 * 60 * 1000,

  // 即時資料 - 無快取
  realtime: 0,
} as const;

// ============================================================================
// 查詢選項預設值
// ============================================================================

export const defaultQueryOptions = {
  /** 下拉選單查詢選項 */
  dropdown: {
    staleTime: staleTimeConfig.dropdown,
    gcTime: 30 * 60 * 1000, // 30 分鐘
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  },

  /** 列表查詢選項 */
  list: {
    staleTime: staleTimeConfig.list,
    gcTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  },

  /** 詳情查詢選項 */
  detail: {
    staleTime: staleTimeConfig.detail,
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  },

  /** 統計查詢選項 */
  statistics: {
    staleTime: staleTimeConfig.statistics,
    gcTime: 15 * 60 * 1000,
    refetchOnWindowFocus: false,
  },

  /** 即時資料選項 */
  realtime: {
    staleTime: 0,
    refetchInterval: 30 * 1000, // 每 30 秒刷新
  },
} as const;

// ============================================================================
// 工具函數
// ============================================================================

/**
 * 生成分頁查詢的快取鍵
 */
export function createPaginatedQueryKey(
  baseKey: readonly string[],
  page: number,
  limit: number,
  filters?: Record<string, unknown>
): readonly unknown[] {
  return [...baseKey, { page, limit, ...filters }];
}

/**
 * 使特定查詢失效
 */
export function invalidateQueries(
  queryClient: { invalidateQueries: (options: { queryKey: readonly unknown[] }) => void },
  keys: readonly unknown[]
): void {
  queryClient.invalidateQueries({ queryKey: keys });
}

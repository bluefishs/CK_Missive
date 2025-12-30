/**
 * 導覽服務 - 處理導覽項目載入和快取
 */
import axios from 'axios';
import { NavigationItem } from '../hooks/usePermissions';
import { cacheService, CACHE_KEYS, CACHE_TTL } from './cacheService';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';
const API_PREFIX = '/api';

class NavigationService {
  private static instance: NavigationService;
  private axios = axios.create({
    baseURL: API_BASE_URL + API_PREFIX,
    timeout: 10000,
  });

  constructor() {
    // 添加認證標頭
    this.axios.interceptors.request.use(config => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });
  }

  public static getInstance(): NavigationService {
    if (!NavigationService.instance) {
      NavigationService.instance = new NavigationService();
    }
    return NavigationService.instance;
  }

  /**
   * 從快取取得導覽項目
   */
  private getCachedNavigation(): NavigationItem[] | null {
    return cacheService.get<NavigationItem[]>(CACHE_KEYS.NAVIGATION_ITEMS, 'localStorage');
  }

  /**
   * 快取導覽項目
   */
  private setCachedNavigation(items: NavigationItem[]): void {
    cacheService.set(
      CACHE_KEYS.NAVIGATION_ITEMS,
      items,
      CACHE_TTL.MEDIUM,
      'localStorage'
    );
  }

  /**
   * 從 API 載入導覽項目
   */
  async loadNavigationFromAPI(): Promise<NavigationItem[]> {
    console.log('🌐 Forcing API call to load navigation...');

    try {
      console.log('🌐 Loading navigation from API...');
      const response = await this.axios.get('/site-management/navigation');
      console.log('📡 API Response:', response.data);
      const items = response.data.items || [];
      console.log('📋 Raw items received:', items.length);
      console.log('🔎 Sample items:', items.slice(0, 3).map(item => ({
        id: item.id,
        title: item.title,
        parent_id: item.parent_id,
        children: item.children?.length || 0
      })));

      // API 已經返回樹狀結構，直接使用
      console.log('🌲 Using API tree structure directly');
      console.log('🔍 Tree structure:', items.map(item => ({
        title: item.title,
        children: item.children?.length || 0
      })));

      // 轉換為標準格式
      const treeItems = this.convertApiItemsToNavigationItems(items);

      // 快取結果
      this.setCachedNavigation(treeItems);
      return treeItems;

    } catch (error) {
      console.error('❌ Failed to load navigation from API:', error);
      console.warn('🔄 Using default navigation items due to API failure');
      // 當 API 失敗時，直接回傳預設導航項目
      const defaultItems = this.getDefaultNavigationItems();
      this.setCachedNavigation(defaultItems);
      return defaultItems;
    }
  }

  /**
   * 解析權限字串
   */
  private parsePermissions(permissions: any): string[] {
    if (!permissions) return [];

    try {
      if (typeof permissions === 'string') {
        return JSON.parse(permissions);
      }
      if (Array.isArray(permissions)) {
        return permissions;
      }
    } catch (error) {
      console.warn('Failed to parse permissions:', permissions, error);
    }

    return [];
  }

  /**
   * 取得導覽項目（優先使用快取）
   */
  async getNavigationItems(useCache = true): Promise<NavigationItem[]> {
    // 檢查是否為開發模式 - 多種檢查方式
    const authDisabled = true || // 暫時強制開發模式
                        (import.meta.env?.VITE_AUTH_DISABLED === 'true') ||
                        (typeof window !== 'undefined' && window.localStorage?.getItem('VITE_AUTH_DISABLED') === 'true') ||
                        (import.meta.env?.MODE === 'development') ||
                        (!import.meta.env?.VITE_AUTH_DISABLED && import.meta.env?.DEV === true);

    console.log('🔧 NavigationService - Auth disabled mode:', authDisabled);
    console.log('🔧 NavigationService - Environment:', import.meta.env?.VITE_AUTH_DISABLED);

    if (authDisabled) {
      console.log('🛠️ Development mode: Using default navigation items without API call');
      // 開發模式：直接返回預設導覽項目，清除權限要求
      const defaultItems = this.getDefaultNavigationItems().map(item => ({
        ...item,
        permission_required: [], // 清除所有權限要求
        children: item.children?.map(child => ({
          ...child,
          permission_required: [] // 清除子項目權限要求
        }))
      }));
      return defaultItems;
    }

    // 正常模式：使用API載入導航項目
    console.log('🔄 Production mode: Loading navigation from API...');
    try {
      // 從 API 載入
      const apiItems = await this.loadNavigationFromAPI();
      console.log('✅ API navigation loaded successfully:', apiItems.length, 'items');
      return apiItems;
    } catch (error) {
      console.error('❌ API navigation failed, using default items:', error);
      // 如果API失敗，使用預設項目但清除權限要求
      const defaultItems = this.getDefaultNavigationItems().map(item => ({
        ...item,
        permission_required: [], // 清除所有權限要求
        children: item.children?.map(child => ({
          ...child,
          permission_required: [] // 清除子項目權限要求
        }))
      }));
      return defaultItems;
    }
  }

  /**
   * 清除導覽快取
   */
  clearNavigationCache(): void {
    cacheService.delete(CACHE_KEYS.NAVIGATION_ITEMS, 'localStorage');
  }

  /**
   * 轉換 API 項目為 NavigationItem（保持樹狀結構）
   */
  private convertApiItemsToNavigationItems(items: any[]): NavigationItem[] {
    return items.map(item => ({
      key: item.key || item.id?.toString() || '',
      title: item.title || '',
      path: item.path || '',
      icon: item.icon,
      permission_required: [], // 暫時清除所有權限要求，確保顯示所有項目
      is_visible: item.is_visible !== false,
      is_enabled: item.is_enabled !== false,
      sort_order: item.sort_order || 0,
      children: item.children ? this.convertApiItemsToNavigationItems(item.children) : []
    }));
  }

  /**
   * 建構樹狀結構導覽 (舊版本，用於扁平結構)
   */
  private buildNavigationTree(items: any[]): NavigationItem[] {
    if (!Array.isArray(items)) return [];

    // 將所有項目轉換為NavigationItem格式
    const navigationItems: NavigationItem[] = items.map(item => ({
      key: item.key || item.id?.toString() || '',
      title: item.title || '',
      path: item.path || '',
      icon: item.icon,
      permission_required: this.parsePermissions(item.permission_required),
      is_visible: item.is_visible !== false,
      is_enabled: item.is_enabled !== false,
      sort_order: item.sort_order || 0,
      children: []
    }));

    // 建立父子關係映射
    const itemMap = new Map<number, NavigationItem & { id: number, parent_id?: number }>();
    const rootItems: NavigationItem[] = [];

    items.forEach((item, index) => {
      const navItem = {
        ...navigationItems[index],
        id: item.id,
        parent_id: item.parent_id
      };
      itemMap.set(item.id, navItem);
    });

    // 建構樹狀結構
    itemMap.forEach(item => {
      if (item.parent_id && itemMap.has(item.parent_id)) {
        const parent = itemMap.get(item.parent_id)!;
        if (!parent.children) parent.children = [];
        parent.children.push(item);
      } else {
        rootItems.push(item);
      }
    });

    // 遞歸排序所有層級
    const sortItems = (items: NavigationItem[]): NavigationItem[] => {
      return items
        .sort((a, b) => a.sort_order - b.sort_order)
        .map(item => ({
          ...item,
          children: item.children ? sortItems(item.children) : []
        }));
    };

    return sortItems(rootItems);
  }

  /**
   * 取得預設導覽項目（如果 API 失敗時使用）
   * 根據既有頁面重新整理導覽結構
   */
  getDefaultNavigationItems(): NavigationItem[] {
    return [
      {
        key: 'dashboard',
        title: '儀表板',
        path: '/dashboard',
        icon: 'home',
        permission_required: [],
        is_visible: true,
        is_enabled: true,
        sort_order: 1
      },
      // 1. 公文管理
      {
        key: 'documents-menu',
        title: '公文管理',
        path: '',
        icon: 'file-text',
        permission_required: ['documents:read'],
        is_visible: true,
        is_enabled: true,
        sort_order: 2,
        children: [
          {
            key: 'document-list',
            title: '公文列表',
            path: '/documents',
            icon: 'file',
            permission_required: ['documents:read'],
            is_visible: true,
            is_enabled: true,
            sort_order: 1
          },
          {
            key: 'document-create',
            title: '新增公文',
            path: '/documents/create',
            icon: 'plus',
            permission_required: ['documents:create'],
            is_visible: true,
            is_enabled: true,
            sort_order: 2
          },
          {
            key: 'document-import',
            title: '文件匯入',
            path: '/documents/import',
            icon: 'upload',
            permission_required: ['documents:create'],
            is_visible: true,
            is_enabled: true,
            sort_order: 3
          },
          {
            key: 'document-export',
            title: '文件匯出',
            path: '/documents/export',
            icon: 'download',
            permission_required: ['documents:read'],
            is_visible: true,
            is_enabled: true,
            sort_order: 4
          },
          {
            key: 'document-workflow',
            title: '工作流程',
            path: '/documents/workflow',
            icon: 'workflow',
            permission_required: ['documents:edit'],
            is_visible: true,
            is_enabled: true,
            sort_order: 5
          },
          {
            key: 'document-numbers',
            title: '發文字號管理',
            path: '/document-numbers',
            icon: 'number',
            permission_required: ['documents:edit'],
            is_visible: true,
            is_enabled: true,
            sort_order: 6
          }
        ]
      },
      // 2. 專案管理 (統一為承攬案件)
      {
        key: 'contract-cases',
        title: '承攬案件',
        path: '/contract-cases',
        icon: 'project',
        permission_required: ['projects:read'],
        is_visible: true,
        is_enabled: true,
        sort_order: 3
      },
      // 3. 機關管理
      {
        key: 'agencies',
        title: '機關管理',
        path: '/agencies',
        icon: 'bank',
        permission_required: ['agencies:read'],
        is_visible: true,
        is_enabled: true,
        sort_order: 4
      },
      // 4. 廠商管理
      {
        key: 'vendors',
        title: '廠商管理',
        path: '/vendors',
        icon: 'shop',
        permission_required: ['vendors:read'],
        is_visible: true,
        is_enabled: true,
        sort_order: 5
      },
      // 5. 行事曆管理
      {
        key: 'calendar-menu',
        title: '行事曆管理',
        path: '',
        icon: 'calendar',
        permission_required: ['calendar:read'],
        is_visible: true,
        is_enabled: true,
        sort_order: 6,
        children: [
          {
            key: 'calendar',
            title: '行事曆',
            path: '/calendar',
            icon: 'calendar',
            permission_required: ['calendar:read'],
            is_visible: true,
            is_enabled: true,
            sort_order: 1
          },
          {
            key: 'pure-calendar',
            title: '純行事曆',
            path: '/pure-calendar',
            icon: 'calendar',
            permission_required: ['calendar:read'],
            is_visible: true,
            is_enabled: true,
            sort_order: 2
          }
        ]
      },
      // 6. 報表分析
      {
        key: 'reports',
        title: '報表分析',
        path: '/reports',
        icon: 'bar-chart',
        permission_required: ['reports:view'],
        is_visible: true,
        is_enabled: true,
        sort_order: 7
      },
      // 7. 系統文件
      {
        key: 'system-docs-menu',
        title: '系統文件',
        path: '',
        icon: 'file',
        permission_required: ['system_docs:read'],
        is_visible: true,
        is_enabled: true,
        sort_order: 8,
        children: [
          {
            key: 'api-docs',
            title: 'API 文件',
            path: '/api/docs',
            icon: 'api',
            permission_required: ['system_docs:read'],
            is_visible: true,
            is_enabled: true,
            sort_order: 1
          },
          {
            key: 'api-mapping',
            title: 'API 對應',
            path: '/api-mapping',
            icon: 'api',
            permission_required: ['system_docs:read'],
            is_visible: true,
            is_enabled: true,
            sort_order: 2
          },
          {
            key: 'google-auth-diagnostic',
            title: 'Google認證診斷',
            path: '/google-auth-diagnostic',
            icon: 'setting',
            permission_required: ['admin:settings'],
            is_visible: true,
            is_enabled: true,
            sort_order: 3
          },
          {
            key: 'unified-form-demo',
            title: '表單範例',
            path: '/unified-form-demo',
            icon: 'form',
            permission_required: ['system_docs:read'],
            is_visible: true,
            is_enabled: true,
            sort_order: 4
          }
        ]
      },
      // 8. 系統管理
      {
        key: 'system-admin-menu',
        title: '系統管理',
        path: '',
        icon: 'setting',
        permission_required: ['admin:users'],
        is_visible: true,
        is_enabled: true,
        sort_order: 9,
        children: [
          {
            key: 'admin-dashboard',
            title: '管理面板',
            path: '/admin/dashboard',
            icon: 'dashboard',
            permission_required: ['admin:users'],
            is_visible: true,
            is_enabled: true,
            sort_order: 1
          },
          {
            key: 'user-management',
            title: '使用者管理',
            path: '/admin/user-management',
            icon: 'user',
            permission_required: ['admin:users'],
            is_visible: true,
            is_enabled: true,
            sort_order: 2
          },
          {
            key: 'permission-management',
            title: '權限管理',
            path: '/admin/permissions',
            icon: 'key',
            permission_required: ['admin:users'],
            is_visible: true,
            is_enabled: true,
            sort_order: 3
          },
          {
            key: 'site-management',
            title: '網站管理',
            path: '/admin/site-management',
            icon: 'global',
            permission_required: ['admin:site_management'],
            is_visible: true,
            is_enabled: true,
            sort_order: 4
          },
          {
            key: 'database-management',
            title: '資料庫管理',
            path: '/admin/database',
            icon: 'database',
            permission_required: ['admin:settings'],
            is_visible: true,
            is_enabled: true,
            sort_order: 5
          },
          {
            key: 'system-settings',
            title: '系統設定',
            path: '/system',
            icon: 'setting',
            permission_required: ['admin:settings'],
            is_visible: true,
            is_enabled: true,
            sort_order: 6
          }
        ]
      }
    ];
  }

  /**
   * 取得帶有回退機制的導覽項目
   */
  async getNavigationItemsWithFallback(): Promise<NavigationItem[]> {
    // 檢查是否已有快取的導覽項目，避免重複載入
    const cached = this.getCachedNavigation();
    if (cached && cached.length > 0) {
      console.log('📋 Using cached navigation items');
      return cached;
    }

    // 在開發模式下直接使用預設導航，避免 API 調用問題
    console.log('🔄 Using default navigation items for stable development');
    const defaultItems = this.getDefaultNavigationItems();
    this.setCachedNavigation(defaultItems);
    return defaultItems;
  }
}

// 匯出單例實例
export const navigationService = NavigationService.getInstance();
export default navigationService;
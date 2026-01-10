/**
 * 導覽服務 - 處理導覽項目載入和快取
 *
 * 重構版本：使用 secureApiService 確保與網站管理頁面 API 一致
 *
 * @version 2.0.0
 * @date 2026-01-10
 */
import { NavigationItem } from '../hooks/usePermissions';
import { cacheService, CACHE_KEYS, CACHE_TTL } from './cacheService';
import { secureApiService } from './secureApiService';

// API 回應介面
interface NavigationApiResponse {
  items?: NavigationItemRaw[];
  total?: number;
}

interface NavigationItemRaw {
  id?: number;
  key?: string;
  title?: string;
  path?: string;
  icon?: string;
  parent_id?: number;
  sort_order?: number;
  is_visible?: boolean;
  is_enabled?: boolean;
  permission_required?: string | string[];
  children?: NavigationItemRaw[];
}

class NavigationService {
  private static instance: NavigationService;

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
   * 從 API 載入導覽項目（使用 secureApiService）
   */
  async loadNavigationFromAPI(): Promise<NavigationItem[]> {
    try {
      // 使用 secureApiService 確保與網站管理頁面一致
      const result = await secureApiService.getNavigationItems() as NavigationApiResponse;
      const items = result.items || [];

      // 轉換為標準格式
      const treeItems = this.convertApiItemsToNavigationItems(items);

      // 快取結果
      this.setCachedNavigation(treeItems);
      return treeItems;

    } catch (error) {
      console.error('Failed to load navigation from API:', error);
      // 當 API 失敗時，回傳預設導航項目
      const defaultItems = this.getDefaultNavigationItems();
      this.setCachedNavigation(defaultItems);
      return defaultItems;
    }
  }

  /**
   * 取得導覽項目（從 API 載入，支援快取）
   */
  async getNavigationItems(useCache = true): Promise<NavigationItem[]> {
    // 優先從快取取得（如果啟用快取）
    if (useCache) {
      const cached = this.getCachedNavigation();
      if (cached && cached.length > 0) {
        return cached;
      }
    }

    // 從 API 載入導航項目
    try {
      return await this.loadNavigationFromAPI();
    } catch (error) {
      console.error('API navigation failed, using default items:', error);
      // 如果 API 失敗，使用預設項目
      return this.getDefaultNavigationItems().map(item => ({
        ...item,
        permission_required: [],
        children: item.children?.map(child => ({
          ...child,
          permission_required: []
        }))
      }));
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
  private convertApiItemsToNavigationItems(items: NavigationItemRaw[]): NavigationItem[] {
    return items.map(item => ({
      key: item.key || item.id?.toString() || '',
      title: item.title || '',
      path: item.path || '',
      icon: item.icon,
      permission_required: this.parsePermissions(item.permission_required),
      is_visible: item.is_visible !== false,
      is_enabled: item.is_enabled !== false,
      sort_order: item.sort_order || 0,
      children: item.children ? this.convertApiItemsToNavigationItems(item.children) : []
    }));
  }

  /**
   * 解析權限字串
   */
  private parsePermissions(permissions: string | string[] | undefined): string[] {
    if (!permissions) return [];

    try {
      if (typeof permissions === 'string') {
        return JSON.parse(permissions);
      }
      if (Array.isArray(permissions)) {
        return permissions;
      }
    } catch {
      // 解析失敗時返回空陣列
    }

    return [];
  }

  /**
   * 取得預設導覽項目（如果 API 失敗時使用）
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
          }
        ]
      },
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
    // 檢查是否已有快取的導覽項目
    const cached = this.getCachedNavigation();
    if (cached && cached.length > 0) {
      return cached;
    }

    // 從 API 載入
    try {
      const apiItems = await this.loadNavigationFromAPI();
      if (apiItems && apiItems.length > 0) {
        return apiItems;
      }
    } catch (error) {
      console.warn('API failed, falling back to default items:', error);
    }

    // API 失敗時使用預設項目
    const defaultItems = this.getDefaultNavigationItems();
    this.setCachedNavigation(defaultItems);
    return defaultItems;
  }
}

// 匯出單例實例
export const navigationService = NavigationService.getInstance();
export default navigationService;

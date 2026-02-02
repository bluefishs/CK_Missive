/**
 * 導覽服務測試
 * Navigation Service Tests
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock dependencies
vi.mock('../../utils/logger', () => ({
  logger: {
    error: vi.fn(),
    warn: vi.fn(),
    log: vi.fn(),
    info: vi.fn(),
    debug: vi.fn(),
  },
}));

vi.mock('../cacheService', () => ({
  cacheService: {
    get: vi.fn(() => null),
    set: vi.fn(),
    delete: vi.fn(),
  },
  CACHE_KEYS: {
    NAVIGATION_ITEMS: 'navigation_items',
  },
  CACHE_TTL: {
    MEDIUM: 300000,
  },
}));

vi.mock('../secureApiService', () => ({
  secureApiService: {
    getNavigationItems: vi.fn(() => Promise.resolve({ items: [] })),
  },
}));

// Import after mocks
import { navigationService } from '../navigationService';
import { cacheService, CACHE_KEYS } from '../cacheService';
import { secureApiService } from '../secureApiService';

describe('navigationService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('單例模式', () => {
    it('應該返回同一個實例', () => {
      const instance1 = navigationService;
      const instance2 = navigationService;

      expect(instance1).toBe(instance2);
    });
  });

  describe('getDefaultNavigationItems', () => {
    it('應該返回預設導覽項目陣列', () => {
      const items = navigationService.getDefaultNavigationItems();

      expect(Array.isArray(items)).toBe(true);
      expect(items.length).toBeGreaterThan(0);
    });

    it('預設項目應該包含必要的欄位', () => {
      const items = navigationService.getDefaultNavigationItems();
      const firstItem = items[0];

      expect(firstItem).toHaveProperty('key');
      expect(firstItem).toHaveProperty('title');
      expect(firstItem).toHaveProperty('path');
      expect(firstItem).toHaveProperty('icon');
      expect(firstItem).toHaveProperty('permission_required');
      expect(firstItem).toHaveProperty('is_visible');
      expect(firstItem).toHaveProperty('is_enabled');
      expect(firstItem).toHaveProperty('sort_order');
    });

    it('應該包含儀表板項目', () => {
      const items = navigationService.getDefaultNavigationItems();
      const dashboard = items.find(item => item.key === 'dashboard');

      expect(dashboard).toBeDefined();
      expect(dashboard?.title).toBe('儀表板');
      expect(dashboard?.path).toBe('/dashboard');
    });

    it('應該包含公文管理項目及子項目', () => {
      const items = navigationService.getDefaultNavigationItems();
      const docMenu = items.find(item => item.key === 'documents-menu');

      expect(docMenu).toBeDefined();
      expect(docMenu?.children).toBeDefined();
      expect(docMenu?.children?.length).toBeGreaterThan(0);
    });

    it('子項目應該包含公文列表', () => {
      const items = navigationService.getDefaultNavigationItems();
      const docMenu = items.find(item => item.key === 'documents-menu');
      const docList = docMenu?.children?.find(child => child.key === 'document-list');

      expect(docList).toBeDefined();
      expect(docList?.path).toBe('/documents');
    });
  });

  describe('clearNavigationCache', () => {
    it('應該呼叫 cacheService.delete', () => {
      navigationService.clearNavigationCache();

      expect(cacheService.delete).toHaveBeenCalledWith(
        CACHE_KEYS.NAVIGATION_ITEMS,
        'localStorage'
      );
    });
  });

  describe('getNavigationItems', () => {
    it('當快取存在時應該返回快取資料', async () => {
      const cachedItems = [
        { key: 'cached', title: 'Cached Item', path: '/cached' },
      ];

      vi.mocked(cacheService.get).mockReturnValueOnce(cachedItems);

      const items = await navigationService.getNavigationItems(true);

      expect(items).toEqual(cachedItems);
      expect(secureApiService.getNavigationItems).not.toHaveBeenCalled();
    });

    it('當 useCache=false 時應該呼叫 API', async () => {
      const apiItems = {
        items: [{ key: 'api', title: 'API Item', path: '/api' }],
      };

      vi.mocked(secureApiService.getNavigationItems).mockResolvedValueOnce(apiItems);

      await navigationService.getNavigationItems(false);

      expect(secureApiService.getNavigationItems).toHaveBeenCalled();
    });

    it('當 API 失敗時應該返回預設項目', async () => {
      vi.mocked(cacheService.get).mockReturnValueOnce(null);
      vi.mocked(secureApiService.getNavigationItems).mockRejectedValueOnce(
        new Error('API Error')
      );

      const items = await navigationService.getNavigationItems();

      expect(items.length).toBeGreaterThan(0);
      expect(items[0]).toHaveProperty('key');
    });
  });

  describe('getNavigationItemsWithFallback', () => {
    it('當快取存在時應該返回快取', async () => {
      const cachedItems = [
        { key: 'cached', title: 'Cached', path: '/cached' },
      ];

      vi.mocked(cacheService.get).mockReturnValueOnce(cachedItems);

      const items = await navigationService.getNavigationItemsWithFallback();

      expect(items).toEqual(cachedItems);
    });

    it('當快取不存在且 API 成功時應該返回 API 結果', async () => {
      const apiResponse = {
        items: [{ key: 'api', title: 'API', path: '/api' }],
      };

      vi.mocked(cacheService.get).mockReturnValueOnce(null);
      vi.mocked(secureApiService.getNavigationItems).mockResolvedValueOnce(apiResponse);

      const items = await navigationService.getNavigationItemsWithFallback();

      expect(items.length).toBeGreaterThan(0);
    });

    it('當快取不存在且 API 失敗時應該返回預設項目', async () => {
      vi.mocked(cacheService.get).mockReturnValueOnce(null);
      vi.mocked(secureApiService.getNavigationItems).mockRejectedValueOnce(
        new Error('Network Error')
      );

      const items = await navigationService.getNavigationItemsWithFallback();

      expect(items.length).toBeGreaterThan(0);
      // 驗證是預設項目
      const dashboard = items.find(item => item.key === 'dashboard');
      expect(dashboard).toBeDefined();
    });
  });

  describe('loadNavigationFromAPI', () => {
    it('應該從 API 載入並快取結果', async () => {
      const apiResponse = {
        items: [
          {
            id: 1,
            key: 'test',
            title: 'Test Item',
            path: '/test',
            is_visible: true,
            is_enabled: true,
          },
        ],
      };

      vi.mocked(secureApiService.getNavigationItems).mockResolvedValueOnce(apiResponse);

      const items = await navigationService.loadNavigationFromAPI();

      expect(items.length).toBe(1);
      expect(items[0].key).toBe('test');
      expect(cacheService.set).toHaveBeenCalled();
    });

    it('當 API 失敗時應該返回預設項目', async () => {
      vi.mocked(secureApiService.getNavigationItems).mockRejectedValueOnce(
        new Error('API Error')
      );

      const items = await navigationService.loadNavigationFromAPI();

      expect(items.length).toBeGreaterThan(0);
      // 預設項目不會被快取
      expect(cacheService.set).not.toHaveBeenCalled();
    });
  });
});

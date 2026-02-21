/**
 * 快取服務測試
 * Cache Service Tests
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

// Mock sessionStorage
const sessionStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });
Object.defineProperty(window, 'sessionStorage', { value: sessionStorageMock });

// Import after mocking
import { cacheService, CACHE_KEYS, CACHE_TTL } from '../cacheService';

describe('cacheService', () => {
  beforeEach(() => {
    localStorageMock.clear();
    sessionStorageMock.clear();
    vi.clearAllMocks();
  });

  describe('記憶體快取', () => {
    it('應該能夠設定和取得記憶體快取', () => {
      const testData = { name: '測試資料', value: 123 };
      cacheService.set('test-key', testData, CACHE_TTL.SHORT, 'memory');

      const result = cacheService.get('test-key', 'memory');
      expect(result).toEqual(testData);
    });

    it('應該能夠刪除記憶體快取', () => {
      cacheService.set('delete-key', 'value', CACHE_TTL.SHORT, 'memory');
      cacheService.delete('delete-key', 'memory');

      const result = cacheService.get('delete-key', 'memory');
      expect(result).toBeNull();
    });
  });

  describe('localStorage 快取', () => {
    it('應該能夠設定 localStorage 快取', () => {
      const testData = { items: [1, 2, 3] };
      cacheService.set('local-key', testData, CACHE_TTL.MEDIUM, 'localStorage');

      expect(localStorageMock.setItem).toHaveBeenCalled();
    });

    it('應該能夠取得 localStorage 快取', () => {
      const testData = { test: 'value' };
      const cacheItem = {
        data: testData,
        timestamp: Date.now(),
        expiresAt: Date.now() + CACHE_TTL.MEDIUM,
      };
      localStorageMock.setItem('cache_local-get', JSON.stringify(cacheItem));

      const result = cacheService.get('local-get', 'localStorage');
      expect(result).toEqual(testData);
    });
  });

  describe('TTL (存活時間)', () => {
    it('應該返回 null 當快取已過期', () => {
      const expiredItem = {
        data: 'expired',
        timestamp: Date.now() - 10000,
        expiresAt: Date.now() - 5000, // 5秒前過期
      };
      localStorageMock.setItem('cache_expired-key', JSON.stringify(expiredItem));

      const result = cacheService.get('expired-key', 'localStorage');
      expect(result).toBeNull();
    });

    it('應該返回資料當快取未過期', () => {
      const validItem = {
        data: 'valid',
        timestamp: Date.now(),
        expiresAt: Date.now() + 60000, // 1分鐘後過期
      };
      localStorageMock.setItem('cache_valid-key', JSON.stringify(validItem));

      const result = cacheService.get('valid-key', 'localStorage');
      expect(result).toBe('valid');
    });
  });

  describe('CACHE_KEYS 常數', () => {
    it('應該包含 NAVIGATION_ITEMS 鍵', () => {
      expect(CACHE_KEYS.NAVIGATION_ITEMS).toBeDefined();
      expect(typeof CACHE_KEYS.NAVIGATION_ITEMS).toBe('string');
    });

    it('應該包含 USER_PERMISSIONS 鍵', () => {
      expect(CACHE_KEYS.USER_PERMISSIONS).toBeDefined();
    });
  });

  describe('CACHE_TTL 常數', () => {
    it('SHORT 應該小於 MEDIUM', () => {
      expect(CACHE_TTL.SHORT).toBeLessThan(CACHE_TTL.MEDIUM);
    });

    it('MEDIUM 應該小於 LONG', () => {
      expect(CACHE_TTL.MEDIUM).toBeLessThan(CACHE_TTL.LONG);
    });
  });
});

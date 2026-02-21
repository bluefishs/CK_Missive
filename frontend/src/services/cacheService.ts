/**
 * 快取服務 - 處理各種快取需求
 * 支援記憶體快取、localStorage和sessionStorage
 */

import { logger } from '../utils/logger';

interface CacheItem<T> {
  data: T;
  timestamp: number;
  expiresAt: number;
}

type CacheStorage = 'memory' | 'localStorage' | 'sessionStorage';

class CacheService {
  private static instance: CacheService;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private memoryCache = new Map<string, CacheItem<any>>();

  public static getInstance(): CacheService {
    if (!CacheService.instance) {
      CacheService.instance = new CacheService();
    }
    return CacheService.instance;
  }

  /**
   * 設定快取項目
   */
  set<T>(
    key: string,
    data: T,
    ttl: number = 5 * 60 * 1000, // 預設5分鐘
    storage: CacheStorage = 'memory'
  ): void {
    const cacheItem: CacheItem<T> = {
      data,
      timestamp: Date.now(),
      expiresAt: Date.now() + ttl
    };

    switch (storage) {
      case 'memory':
        this.memoryCache.set(key, cacheItem);
        break;
      case 'localStorage':
        try {
          localStorage.setItem(`cache_${key}`, JSON.stringify(cacheItem));
        } catch (error) {
          logger.warn('Failed to set localStorage cache:', error);
        }
        break;
      case 'sessionStorage':
        try {
          sessionStorage.setItem(`cache_${key}`, JSON.stringify(cacheItem));
        } catch (error) {
          logger.warn('Failed to set sessionStorage cache:', error);
        }
        break;
    }
  }

  /**
   * 取得快取項目
   */
  get<T>(key: string, storage: CacheStorage = 'memory'): T | null {
    let cacheItem: CacheItem<T> | null = null;

    try {
      switch (storage) {
        case 'memory':
          cacheItem = this.memoryCache.get(key) || null;
          break;
        case 'localStorage': {
          const localItem = localStorage.getItem(`cache_${key}`);
          cacheItem = localItem ? JSON.parse(localItem) : null;
          break;
        }
        case 'sessionStorage': {
          const sessionItem = sessionStorage.getItem(`cache_${key}`);
          cacheItem = sessionItem ? JSON.parse(sessionItem) : null;
          break;
        }
      }

      if (!cacheItem) return null;

      // 檢查是否過期
      if (Date.now() > cacheItem.expiresAt) {
        this.delete(key, storage);
        return null;
      }

      return cacheItem.data;
    } catch (error) {
      logger.warn('Failed to get cache:', error);
      return null;
    }
  }

  /**
   * 刪除快取項目
   */
  delete(key: string, storage: CacheStorage = 'memory'): void {
    switch (storage) {
      case 'memory':
        this.memoryCache.delete(key);
        break;
      case 'localStorage':
        localStorage.removeItem(`cache_${key}`);
        break;
      case 'sessionStorage':
        sessionStorage.removeItem(`cache_${key}`);
        break;
    }
  }

  /**
   * 清除所有快取
   */
  clear(storage: CacheStorage = 'memory'): void {
    switch (storage) {
      case 'memory':
        this.memoryCache.clear();
        break;
      case 'localStorage':
        Object.keys(localStorage).forEach(key => {
          if (key.startsWith('cache_')) {
            localStorage.removeItem(key);
          }
        });
        break;
      case 'sessionStorage':
        Object.keys(sessionStorage).forEach(key => {
          if (key.startsWith('cache_')) {
            sessionStorage.removeItem(key);
          }
        });
        break;
    }
  }

  /**
   * 檢查快取是否存在且未過期
   */
  has(key: string, storage: CacheStorage = 'memory'): boolean {
    return this.get(key, storage) !== null;
  }

  /**
   * 取得或設定快取（如果不存在則執行回調函數）
   */
  async getOrSet<T>(
    key: string,
    fetcher: () => Promise<T>,
    ttl: number = 5 * 60 * 1000,
    storage: CacheStorage = 'memory'
  ): Promise<T> {
    const cached = this.get<T>(key, storage);
    if (cached !== null) {
      return cached;
    }

    const data = await fetcher();
    this.set(key, data, ttl, storage);
    return data;
  }

  /**
   * 清理過期的記憶體快取
   */
  cleanupExpiredMemoryCache(): void {
    const now = Date.now();
    for (const [key, item] of this.memoryCache.entries()) {
      if (now > item.expiresAt) {
        this.memoryCache.delete(key);
      }
    }
  }

  /**
   * 取得快取統計資訊
   */
  getStats(): {
    memory: { size: number; keys: string[] };
    localStorage: { size: number; keys: string[] };
    sessionStorage: { size: number; keys: string[] };
  } {
    const getStorageKeys = (storage: Storage) => {
      return Object.keys(storage).filter(key => key.startsWith('cache_'));
    };

    return {
      memory: {
        size: this.memoryCache.size,
        keys: Array.from(this.memoryCache.keys())
      },
      localStorage: {
        size: getStorageKeys(localStorage).length,
        keys: getStorageKeys(localStorage)
      },
      sessionStorage: {
        size: getStorageKeys(sessionStorage).length,
        keys: getStorageKeys(sessionStorage)
      }
    };
  }
}

// 權限相關快取的特殊鍵值
export const CACHE_KEYS = {
  USER_PERMISSIONS: 'user_permissions',
  NAVIGATION_ITEMS: 'navigation_items',
  USER_INFO: 'user_info',
  ROLE_PERMISSIONS: 'role_permissions'
};

// 快取持續時間常數
export const CACHE_TTL = {
  SHORT: 2 * 60 * 1000,      // 2分鐘
  MEDIUM: 5 * 60 * 1000,     // 5分鐘
  LONG: 15 * 60 * 1000,      // 15分鐘
  VERY_LONG: 60 * 60 * 1000  // 1小時
};

// 定期清理過期的記憶體快取
setInterval(() => {
  CacheService.getInstance().cleanupExpiredMemoryCache();
}, 5 * 60 * 1000); // 每5分鐘清理一次

// 匯出單例實例
export const cacheService = CacheService.getInstance();
export default cacheService;
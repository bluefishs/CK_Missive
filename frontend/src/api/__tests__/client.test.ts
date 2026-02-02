/**
 * API Client 測試
 * API Client Tests
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock fetch
global.fetch = vi.fn();

// Mock env
vi.mock('../../config/env', () => ({
  isAuthDisabled: vi.fn(() => false),
  detectEnvironment: vi.fn(() => 'localhost'),
}));

// Mock logger
vi.mock('../../utils/logger', () => ({
  logger: {
    error: vi.fn(),
    warn: vi.fn(),
    log: vi.fn(),
    info: vi.fn(),
    debug: vi.fn(),
  },
}));

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

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
  });

  describe('API_BASE_URL', () => {
    it('應該有正確的 API 基礎 URL 格式', async () => {
      // 動態 import 以便取得模組
      const { API_BASE_URL } = await import('../client');

      expect(typeof API_BASE_URL).toBe('string');
      expect(API_BASE_URL).toMatch(/^https?:\/\//);
    });
  });

  describe('apiClient 結構', () => {
    it('應該匯出 apiClient', async () => {
      const { apiClient } = await import('../client');
      expect(apiClient).toBeDefined();
    });

    it('apiClient 應該有 post 方法', async () => {
      const { apiClient } = await import('../client');
      expect(typeof apiClient.post).toBe('function');
    });

    it('apiClient 應該有 get 方法', async () => {
      const { apiClient } = await import('../client');
      expect(typeof apiClient.get).toBe('function');
    });
  });

  describe('錯誤處理', () => {
    it('apiClient 應該有 post 方法', async () => {
      const { apiClient } = await import('../client');
      expect(typeof apiClient.post).toBe('function');
    });

    it('apiClient 應該是一個物件', async () => {
      const { apiClient } = await import('../client');
      expect(typeof apiClient).toBe('object');
    });
  });
});

describe('API Endpoints', () => {
  it('API_ENDPOINTS 應該包含 DOCUMENTS', async () => {
    const { API_ENDPOINTS } = await import('../endpoints');

    expect(API_ENDPOINTS.DOCUMENTS).toBeDefined();
    expect(API_ENDPOINTS.DOCUMENTS.LIST).toBeDefined();
  });

  it('API_ENDPOINTS 應該包含 AUTH', async () => {
    const { API_ENDPOINTS } = await import('../endpoints');

    expect(API_ENDPOINTS.AUTH).toBeDefined();
  });
});

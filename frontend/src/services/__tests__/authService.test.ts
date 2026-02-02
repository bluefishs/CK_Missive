/**
 * 認證服務測試
 * Auth Service Tests
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock dependencies before importing authService
vi.mock('../../config/env', () => ({
  isAuthDisabled: vi.fn(() => false),
  isInternalNetwork: vi.fn(() => false),
  detectEnvironment: vi.fn(() => 'localhost'),
}));

vi.mock('../../utils/logger', () => ({
  logger: {
    error: vi.fn(),
    warn: vi.fn(),
    log: vi.fn(),
    info: vi.fn(),
    debug: vi.fn(),
  },
}));

vi.mock('jwt-decode', () => ({
  jwtDecode: vi.fn(() => ({
    sub: 'test-user',
    email: 'test@example.com',
    exp: Math.floor(Date.now() / 1000) + 3600, // 1 hour from now
    iat: Math.floor(Date.now() / 1000),
    jti: 'test-jti',
  })),
}));

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
      post: vi.fn(),
      get: vi.fn(),
    })),
  },
}));

vi.mock('../../api/client', () => ({
  API_BASE_URL: 'http://localhost:8001',
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
    _getStore: () => store,
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Import after all mocks are set up
import authService from '../authService';

describe('authService', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  describe('getAccessToken', () => {
    it('應該返回儲存的 access token', () => {
      const testToken = 'test-access-token';
      localStorageMock.setItem('access_token', testToken);

      const result = authService.getAccessToken();
      expect(result).toBe(testToken);
    });

    it('當沒有 token 時應該返回 null', () => {
      const result = authService.getAccessToken();
      expect(result).toBeNull();
    });
  });

  describe('getToken', () => {
    it('應該返回 getAccessToken 的結果', () => {
      const testToken = 'test-token';
      localStorageMock.setItem('access_token', testToken);

      const result = authService.getToken();
      expect(result).toBe(testToken);
    });
  });

  describe('getRefreshToken', () => {
    it('應該返回儲存的 refresh token', () => {
      const testToken = 'test-refresh-token';
      localStorageMock.setItem('refresh_token', testToken);

      const result = authService.getRefreshToken();
      expect(result).toBe(testToken);
    });

    it('當沒有 refresh token 時應該返回 null', () => {
      const result = authService.getRefreshToken();
      expect(result).toBeNull();
    });
  });

  describe('getUserInfo', () => {
    it('應該返回儲存的使用者資訊', () => {
      const userInfo = {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        role: 'user',
        is_admin: false,
        login_count: 5,
        email_verified: true,
      };
      localStorageMock.setItem('user_info', JSON.stringify(userInfo));

      const result = authService.getUserInfo();
      expect(result).toEqual(userInfo);
    });

    it('當沒有使用者資訊時應該返回 null', () => {
      const result = authService.getUserInfo();
      expect(result).toBeNull();
    });

    it('當 JSON 解析失敗時應該返回 null', () => {
      localStorageMock.setItem('user_info', 'invalid-json');
      const result = authService.getUserInfo();
      expect(result).toBeNull();
    });
  });

  describe('setUserInfo', () => {
    it('應該儲存使用者資訊到 localStorage', () => {
      const userInfo = {
        id: 1,
        username: 'newuser',
        email: 'new@example.com',
        role: 'admin',
        is_admin: true,
        login_count: 10,
        email_verified: true,
      };

      authService.setUserInfo(userInfo as any);
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'user_info',
        JSON.stringify(userInfo)
      );
    });
  });

  describe('isAdmin', () => {
    it('當使用者 is_admin 為 true 時應該返回 true', () => {
      const adminUser = { is_admin: true, role: 'user' };
      localStorageMock.setItem('user_info', JSON.stringify(adminUser));

      const result = authService.isAdmin();
      expect(result).toBe(true);
    });

    it('當使用者 role 為 admin 時應該返回 true', () => {
      const adminUser = { is_admin: false, role: 'admin' };
      localStorageMock.setItem('user_info', JSON.stringify(adminUser));

      const result = authService.isAdmin();
      expect(result).toBe(true);
    });

    it('當使用者 role 為 superuser 時應該返回 true', () => {
      const superUser = { is_admin: false, role: 'superuser' };
      localStorageMock.setItem('user_info', JSON.stringify(superUser));

      const result = authService.isAdmin();
      expect(result).toBe(true);
    });

    it('當使用者不是管理員時應該返回 false', () => {
      const normalUser = { is_admin: false, role: 'user' };
      localStorageMock.setItem('user_info', JSON.stringify(normalUser));

      const result = authService.isAdmin();
      expect(result).toBe(false);
    });

    it('當沒有使用者資訊時應該返回 false', () => {
      const result = authService.isAdmin();
      expect(result).toBe(false);
    });
  });

  describe('hasRole', () => {
    it('應該在角色匹配時返回 true', () => {
      const user = { role: 'editor' };
      localStorageMock.setItem('user_info', JSON.stringify(user));

      const result = authService.hasRole('editor');
      expect(result).toBe(true);
    });

    it('應該在角色不匹配時返回 false', () => {
      const user = { role: 'viewer' };
      localStorageMock.setItem('user_info', JSON.stringify(user));

      const result = authService.hasRole('admin');
      expect(result).toBe(false);
    });
  });

  describe('getAuthHeader', () => {
    it('當有 token 時應該返回 Authorization header', () => {
      localStorageMock.setItem('access_token', 'my-token');

      const result = authService.getAuthHeader();
      expect(result).toEqual({ Authorization: 'Bearer my-token' });
    });

    it('當沒有 token 時應該返回空物件', () => {
      const result = authService.getAuthHeader();
      expect(result).toEqual({});
    });
  });

  describe('isAuthenticated', () => {
    it('當有有效 JWT token 時應該返回 true', () => {
      localStorageMock.setItem('access_token', 'valid-jwt-token');

      const result = authService.isAuthenticated();
      expect(result).toBe(true);
    });

    it('當沒有 token 且沒有 userInfo 時應該返回 false', () => {
      const result = authService.isAuthenticated();
      expect(result).toBe(false);
    });
  });

  describe('服務單例', () => {
    it('應該是同一個實例', () => {
      expect(authService).toBeDefined();
      expect(typeof authService.getAccessToken).toBe('function');
      expect(typeof authService.getUserInfo).toBe('function');
      expect(typeof authService.isAdmin).toBe('function');
    });

    it('應該有 axios 實例方法', () => {
      expect(typeof authService.getAxiosInstance).toBe('function');
    });
  });
});

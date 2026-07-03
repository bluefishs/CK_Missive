/**
 * authService 401 攔截器 regression（2026-07-03 SSO「停在登入頁」根治）
 *
 * 背景：authService 有**自己獨立的 axios 實例**（與 api/interceptors.ts 不同）。
 *   其 401 攔截器過去無條件 clearAuth() + window.location.href='/login'。
 *   唯一 401 來源＝bootstrap 期間 validateTokenOnStartup→checkAuthStatus，而 SSO 整頁
 *   重載後首個 /auth/check 會撞 cookie/csrf race → 瞬態 401 → 舊行為立即清 user_info +
 *   硬跳 /login → 600ms retry 永遠來不及 → 重載 bootstrap 見無 user_info → 停在登入頁。
 *   本 bug 曾多次「修在另一個 axios 實例」而漏掉這個 → 故鎖定：
 *     status='resolving' / 'authenticated' → 不清除、不跳轉（交 bootstrap 權威決定）；
 *     status='anonymous' → 才允許清除 + 跳 /login。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

// vi.mock 工廠會被提升至檔案頂端 → 內部引用的變數須用 vi.hoisted 宣告（避開 TDZ）
const h = vi.hoisted(() => ({
  capturedRejectHandler: null as null | ((error: unknown) => Promise<unknown>),
  mockStatus: 'anonymous' as 'resolving' | 'authenticated' | 'anonymous',
}));

vi.mock('../../config/env', () => ({
  isAuthDisabled: vi.fn(() => false),
  isInternalNetwork: vi.fn(() => false),
  detectEnvironment: vi.fn(() => 'public'),
}));

vi.mock('../../utils/logger', () => ({
  logger: { error: vi.fn(), warn: vi.fn(), log: vi.fn(), info: vi.fn(), debug: vi.fn() },
}));

vi.mock('jwt-decode', () => ({ jwtDecode: vi.fn(() => ({ exp: Math.floor(Date.now() / 1000) + 3600 })) }));

vi.mock('../../api/client', () => ({ API_BASE_URL: 'http://localhost:8001', getCookie: vi.fn(() => null) }));

// 受控的 sessionStore.getSessionStatus（authService 於 handler 內動態 import）
vi.mock('../../store/sessionStore', () => ({
  getSessionStatus: () => h.mockStatus,
}));

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      interceptors: {
        request: { use: vi.fn() },
        response: {
          use: vi.fn((_onFulfilled: unknown, onRejected: (e: unknown) => Promise<unknown>) => {
            h.capturedRejectHandler = onRejected;
          }),
        },
      },
      post: vi.fn(),
      get: vi.fn(),
    })),
  },
}));

// localStorage mock（觀察 clearAuth 是否清 user_info）
const store: Record<string, string> = {};
const localStorageMock = {
  getItem: vi.fn((k: string) => store[k] ?? null),
  setItem: vi.fn((k: string, v: string) => { store[k] = v; }),
  removeItem: vi.fn((k: string) => { delete store[k]; }),
  clear: vi.fn(() => { for (const k of Object.keys(store)) delete store[k]; }),
};
Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock, writable: true });

// window.location.href 觀察
const locationMock = { href: '', pathname: '/dashboard', replace: vi.fn() };
Object.defineProperty(globalThis, 'window', {
  value: { location: locationMock, addEventListener: vi.fn(), dispatchEvent: vi.fn() },
  writable: true,
});
Object.defineProperty(globalThis, 'document', { value: { cookie: '' }, writable: true });

// import 後 singleton 建構 → 攔截器被捕捉
import '../authService';

const make401 = () => ({ response: { status: 401 }, config: {} });

describe('authService 401 攔截器 — resolving/authenticated 不得破壞 session（SSO 停在登入頁 regression）', () => {
  beforeEach(() => {
    store['user_info'] = JSON.stringify({ id: 1, email: 'a@b.c' });
    store['access_token'] = 'tok';
    locationMock.href = '';
    locationMock.pathname = '/dashboard';
    vi.clearAllMocks();
  });

  it('攔截器已成功捕捉', () => {
    expect(h.capturedRejectHandler).toBeTypeOf('function');
  });

  it("status='resolving'：401 不清 user_info、不跳 /login", async () => {
    h.mockStatus = 'resolving';
    await expect(h.capturedRejectHandler!(make401())).rejects.toBeDefined();
    expect(store['user_info']).toBeDefined();
    expect(locationMock.href).not.toContain('/login');
  });

  it("status='authenticated'：401 不清 user_info、不跳 /login", async () => {
    h.mockStatus = 'authenticated';
    await expect(h.capturedRejectHandler!(make401())).rejects.toBeDefined();
    expect(store['user_info']).toBeDefined();
    expect(locationMock.href).not.toContain('/login');
  });

  it("status='anonymous'：401 才清除並跳 /login（維持登出安全）", async () => {
    h.mockStatus = 'anonymous';
    await expect(h.capturedRejectHandler!(make401())).rejects.toBeDefined();
    expect(store['user_info']).toBeUndefined();
    expect(locationMock.href).toContain('/login');
  });
});

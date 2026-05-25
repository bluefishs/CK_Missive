/**
 * P-58 regression test — shouldUseDevMockUser() 行為測試
 *
 * 修復 bug：先前內網 dev mode (VITE_AUTH_DISABLED=true) 強制把所有用戶視為
 * superuser → 一般使用者登入後仍看到全部 nav。
 *
 * 修法：當 localStorage 有真實 user_info 時，dev mock 不應介入。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('shouldUseDevMockUser (P-58)', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
  });

  it('VITE_AUTH_DISABLED=false → 永不使用 dev mock（公網模式）', async () => {
    vi.stubEnv('VITE_AUTH_DISABLED', 'false');
    const { shouldUseDevMockUser } = await import('../env');
    expect(shouldUseDevMockUser()).toBe(false);
  });

  it('VITE_AUTH_DISABLED=true 且 localStorage 無 user_info → 套 dev mock（首次進入內網）', async () => {
    vi.stubEnv('VITE_AUTH_DISABLED', 'true');
    const localStorageMock = {
      getItem: vi.fn().mockReturnValue(null),
    };
    vi.stubGlobal('window', {
      localStorage: localStorageMock,
      location: { origin: 'http://localhost:3000', hostname: 'localhost' },
    });
    const { shouldUseDevMockUser } = await import('../env');
    expect(shouldUseDevMockUser()).toBe(true);
  });

  it('VITE_AUTH_DISABLED=true 但已有真實 user_info → 不套 mock（尊重真用戶 role）', async () => {
    vi.stubEnv('VITE_AUTH_DISABLED', 'true');
    const localStorageMock = {
      getItem: vi.fn().mockReturnValue('{"id":42,"role":"user","full_name":"王駿穠"}'),
    };
    vi.stubGlobal('window', {
      localStorage: localStorageMock,
      location: { origin: 'http://localhost:3000', hostname: 'localhost' },
    });
    const { shouldUseDevMockUser } = await import('../env');
    expect(shouldUseDevMockUser()).toBe(false);
  });

  it('VITE_AUTH_DISABLED=true + localStorage throw → fallback 套 mock（保守行為）', async () => {
    vi.stubEnv('VITE_AUTH_DISABLED', 'true');
    const localStorageMock = {
      getItem: vi.fn().mockImplementation(() => {
        throw new Error('localStorage disabled');
      }),
    };
    vi.stubGlobal('window', {
      localStorage: localStorageMock,
      location: { origin: 'http://localhost:3000', hostname: 'localhost' },
    });
    const { shouldUseDevMockUser } = await import('../env');
    expect(shouldUseDevMockUser()).toBe(true);
  });
});

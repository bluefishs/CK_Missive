/**
 * sessionStore 單元測試 — 鎖定 SSO 治本（2026-06-15）的單一權威解析行為
 *
 * 鎖定不變式：
 * 1. markAuthenticated / markAnonymous 切換 status。
 * 2. 'user-logged-in' / 'user-logged-out' 事件即時同步 store。
 * 3. markAuthenticated(null) 退而從 authService.getUserInfo 取 user。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// vi.mock 工廠內不可引用外部變數 → 於工廠內定義 vi.fn()
vi.mock('../../services/authService', () => {
  const service = {
    getUserInfo: vi.fn(),
    validateTokenOnStartup: vi.fn().mockResolvedValue(true),
    isAdmin: vi.fn(() => false),
  };
  return { __esModule: true, default: service, authService: service };
});
vi.mock('../../config/env', () => ({
  isAuthDisabled: vi.fn(() => false),
  isInternalNetwork: vi.fn(() => false),
}));
vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), warn: vi.fn(), error: vi.fn(), info: vi.fn() },
}));

import { useSessionStore } from '../sessionStore';
import authService from '../../services/authService';

describe('sessionStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSessionStore.setState({ status: 'resolving', user: null });
  });

  it('markAuthenticated / markAnonymous 切換 status', () => {
    useSessionStore.getState().markAuthenticated({ id: 1, username: 'u' } as never);
    expect(useSessionStore.getState().status).toBe('authenticated');
    expect(useSessionStore.getState().user).toMatchObject({ id: 1 });

    useSessionStore.getState().markAnonymous();
    expect(useSessionStore.getState().status).toBe('anonymous');
    expect(useSessionStore.getState().user).toBeNull();
  });

  it("'user-logged-in' → authenticated；'user-logged-out' → anonymous", () => {
    vi.mocked(authService.getUserInfo).mockReturnValue({ id: 9, username: 'evt' } as never);
    window.dispatchEvent(new CustomEvent('user-logged-in'));
    expect(useSessionStore.getState().status).toBe('authenticated');
    expect(useSessionStore.getState().user).toMatchObject({ id: 9 });

    window.dispatchEvent(new CustomEvent('user-logged-out'));
    expect(useSessionStore.getState().status).toBe('anonymous');
    expect(useSessionStore.getState().user).toBeNull();
  });

  it('markAuthenticated(null) 退而從 authService.getUserInfo 取 user', () => {
    vi.mocked(authService.getUserInfo).mockReturnValue({ id: 7, username: 'fallback' } as never);
    useSessionStore.getState().markAuthenticated(null);
    expect(useSessionStore.getState().user).toMatchObject({ id: 7 });
  });
});

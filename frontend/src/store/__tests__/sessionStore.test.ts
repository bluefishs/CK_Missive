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
    clearAuthData: vi.fn(),
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

  // ── 競態防護 regression（2026-06-16 SSO 真根因：「第一次停在 entry、重刷才好」）──
  // 鎖定：bootstrap 對「殘留舊 token」的遲到驗證失敗，不得 clobber 掉、更不得 clearAuth 掉
  //   同時間 ssoBridge 已建立的全新 session（last-writer-wins 競態 + 破壞性副作用根因）。
  // 註：bootstrap 有 module 級 idempotent 旗標（每頁載入只跑一次），故本檔僅此一個 bootstrap 案例。
  it('競態防護：驗證遲到失敗時不得 clobber/clearAuth 掉 ssoBridge 已建立的 session', async () => {
    // 重開機後 localStorage 殘留舊 user_info（cached 不為 null → 走 validate 路徑）
    vi.mocked(authService.getUserInfo).mockReturnValue({ id: 1, username: 'cached' } as never);

    // validateTokenOnStartup 用可控 deferred：在 ssoBridge「贏」之後才遲到解析為 false（舊 token 失效）
    let resolveValidate: (v: boolean) => void = () => {};
    vi.mocked(authService.validateTokenOnStartup).mockReturnValue(
      new Promise<boolean>((res) => { resolveValidate = res; })
    );

    const p = useSessionStore.getState().bootstrap();

    // 競態：ssoBridge 用 ck_employee cookie 建立全新 session 並升級為已認證
    useSessionStore.getState().markAuthenticated({ id: 2, username: 'sso-fresh' } as never);
    expect(useSessionStore.getState().status).toBe('authenticated');

    // 舊 token 驗證此刻才遲到失敗
    resolveValidate(false);
    await p;

    // 不得降級回 anonymous，且不得清掉剛建立的 session
    expect(useSessionStore.getState().status).toBe('authenticated');
    expect(useSessionStore.getState().user).toMatchObject({ id: 2 });
    expect(authService.clearAuthData).not.toHaveBeenCalled();
  });
});

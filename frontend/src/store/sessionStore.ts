/**
 * sessionStore — 前端登入狀態的「單一權威解析器」（SSOT）
 *
 * 為何存在（2026-06-15 SSO 治本）：
 *   過去登入狀態散在 localStorage.user_info / access_token / csrf_token cookie /
 *   httpOnly cookie / /auth/check / /auth/me，且 EntryPage / useAuthGuard /
 *   ProtectedRoute / useNavigationData 各自推導「我登入了嗎」+ 各自 redirect。
 *   時機一錯就互相矛盾 → race（L41/L48/L66/L68/L69 + 6/15 stuck-at-entry 皆此族）。
 *
 * 本 store 的職責 = 唯一的「is-authenticated 真相」與「啟動解析」：
 *   - 啟動時只在一處 bootstrap（一次 /auth/me + retry），resolve 出 status。
 *   - status='resolving' 期間 SessionGate 顯示 loading、**禁止任何守衛 redirect** →
 *     從源頭消滅「瞬態未認證 → 跳轉 → 跳回」迴圈。
 *   - 其他元件（守衛）只讀 status，不再各自重新推導。
 *   - 監聽既有 'user-logged-in' / 'user-logged-out' 事件，現有登入派發點自動同步，
 *     無需逐一改寫。
 *
 * 邊界：user 物件的 IO 仍由 authService（localStorage）負責；本 store 不取代
 *   authService，只在其上加一層「已解析的權威狀態」。
 */
import { create } from 'zustand';
import authService, { UserInfo } from '../services/authService';
import { isAuthDisabled, isInternalNetwork } from '../config/env';
import { logger } from '../utils/logger';

export type SessionStatus = 'resolving' | 'authenticated' | 'anonymous';

interface SessionState {
  status: SessionStatus;
  user: UserInfo | null;
  /** 啟動解析（idempotent，只跑一次）。在 SessionGate mount 時呼叫。 */
  bootstrap: () => Promise<void>;
  /** 登入成功後標記（login/SSO/Google/LINE/MFA 經 'user-logged-in' 事件自動觸發）。 */
  markAuthenticated: (user: UserInfo | null) => void;
  /** 登出 / session 失效後標記。 */
  markAnonymous: () => void;
}

/** bypass：開發模式（AUTH_DISABLED）或內網 internal provider → 視為已認證。 */
const computeBypass = (): boolean => {
  if (isAuthDisabled()) return true;
  const u = authService.getUserInfo();
  return Boolean(isInternalNetwork() && u && u.auth_provider === 'internal');
};

let _bootstrapStarted = false;

export const useSessionStore = create<SessionState>((set) => ({
  status: 'resolving',
  user: null,

  bootstrap: async () => {
    if (_bootstrapStarted) return;
    _bootstrapStarted = true;

    // 1) bypass（dev / 內網）→ 直接 authenticated
    if (computeBypass()) {
      set({ status: 'authenticated', user: authService.getUserInfo() });
      return;
    }

    // 2) 無本地 user_info → 沒有可驗證的 session，視為匿名（公開頁可正常顯示）
    const cached = authService.getUserInfo();
    if (!cached) {
      set({ status: 'anonymous', user: null });
      return;
    }

    // 3) 有 user_info → 樂觀帶入，向後端確認一次（validateTokenOnStartup 內含 retry，
    //    防 SSO 整頁重載後 cookie/csrf 初始化 race）。確認失敗才降為匿名。
    set({ user: cached });
    try {
      const valid = await authService.validateTokenOnStartup();
      if (valid) {
        set({ status: 'authenticated', user: authService.getUserInfo() });
      } else {
        set({ status: 'anonymous', user: null });
      }
    } catch (err) {
      logger.warn('[session] bootstrap 驗證異常，視為匿名', err);
      set({ status: 'anonymous', user: null });
    }
  },

  markAuthenticated: (user) => set({ status: 'authenticated', user: user ?? authService.getUserInfo() }),
  markAnonymous: () => set({ status: 'anonymous', user: null }),
}));

// ── 與既有登入/登出事件接線（現有派發點自動同步 store，無需逐一改寫）──
if (typeof window !== 'undefined') {
  window.addEventListener('user-logged-in', () => {
    useSessionStore.getState().markAuthenticated(authService.getUserInfo());
  });
  window.addEventListener('user-logged-out', () => {
    useSessionStore.getState().markAnonymous();
  });
}

/** 非 React 環境（如 AppRouter 根判斷）即時取狀態用。 */
export const getSessionStatus = (): SessionStatus => useSessionStore.getState().status;

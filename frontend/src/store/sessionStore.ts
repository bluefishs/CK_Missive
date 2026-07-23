/**
 * sessionStore — 前端登入狀態的「單一權威解析器」（SSOT）
 *
 * 2026-07-23（L80 模組化）：tri-state 狀態機邏輯已收斂至 Tier 1 共享套件 @ck-shared/sso 的
 * createSessionStore（保真基準＝本檔原 Missive 版，含 L74/L78「markAuthenticated 明確成功事件
 * 優先於被動舊 token 檢查」競態防護）。本檔降為 config 注入的薄 wrapper。
 *
 * 職責不變：唯一的「is-authenticated 真相」與「啟動解析」；status='resolving' 期間 SessionGate
 * 顯示 loading、禁所有守衛 redirect（源頭消滅「瞬態未認證→跳轉→跳回」迴圈）。
 * 邊界：user 物件 IO 仍由 authService（localStorage）負責；本 store 只加一層已解析權威狀態。
 */
import authService, { UserInfo } from '../services/authService';
import { isAuthDisabled, isInternalNetwork } from '../config/env';
import { logger } from '../utils/logger';
import { createSessionStore, type SessionStatus } from '@ck-shared/sso';

export type { SessionStatus };

/** bypass：開發模式（AUTH_DISABLED）或內網 internal provider → 視為已認證。 */
const computeBypass = (): boolean => {
  if (isAuthDisabled()) return true;
  const u = authService.getUserInfo();
  return Boolean(isInternalNetwork() && u && u.auth_provider === 'internal');
};

export const { useSessionStore, getSessionStatus } = createSessionStore<UserInfo>({
  getUserInfo: () => authService.getUserInfo(),
  validateTokenOnStartup: () => authService.validateTokenOnStartup(),
  clearAuthData: () => authService.clearAuthData(),
  computeBypass,
  logger,
});

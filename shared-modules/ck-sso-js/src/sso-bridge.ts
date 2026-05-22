/**
 * ck-sso-js — framework-agnostic SSO Bridge for *.cksurvey.tw consumer frontends.
 *
 * 抽自 CK_Missive frontend `api/interceptors.ts attemptSSOBridge()` +
 * `services/authService.ts ssoBridge()`（2026-05-21 L41-sealed）。
 *
 * 用途：consumer React/Vue/vanilla 在 EntryPage / 任意「未登入入口」mount 時呼叫，
 * 嘗試用 www.cksurvey.tw 的 ck_employee cookie 自動建立 consumer session。
 *
 * 設計原則：
 *   - 純 fetch / sessionStorage，無框架依賴（axios 可選 transport）
 *   - 單層防禦：cooldown 30s（每 mount 內 30s 不重打 backend）
 *   - 不暴露 cookie 給 JS（HttpOnly cookie auto-send via credentials:'include'）
 *
 * v2.0 — 2026-05-22 — ADR-0004 L45 修法（B 案治本）
 *   移除「終態鎖」+「連續失敗計數鎖」設計。
 *
 *   原因（L45）：sessionStorage flag `ck_sso_bridge_attempted=1` 在 5/19~5/22 反覆 debug
 *   累積，造成 user 報「必須先在 missive 自己登入並保持頁面開啟才能進 missive」現象 —
 *   實際是 sessionStorage flag 鎖死讓 ssoBridge() 直接 return 'locked'，從未真嘗試。
 *
 *   反模式：「session-permanent lock」— 用 sessionStorage 設「永久終態」flag，把
 *   「暫時故障」（401/cookie drift）轉成「session 內永久不重試」。
 *   一旦 debug 期累積，正式環境也踩中。
 *
 *   B 案治本：完全移除 flag/failCount，只留 cooldown 30s。失敗 → 用戶看 login UI；
 *   用戶 reload / 重新點卡片 → 30s 後可重試。背景的 cooldown 保護 backend 不被狂打。
 *
 * v1.1 — 2026-05-22 — onSuccess 預設 replace('/dashboard') 取代 reload (L44 P2)
 * v1.0 — 2026-05-21
 */

// ─── 型別 ─────────────────────────────────────────────────────────

/** SSO bridge 嘗試結果 */
export interface SSOBridgeResult {
  /** 是否成功（200 + response.user_info）*/
  ok: boolean;
  /** HTTP status code（如有）*/
  status?: number;
  /** Response body parsed JSON */
  data?: unknown;
  /**
   * 中止原因：
   *   - 'cooldown': 距上次嘗試 < cooldownMs（本 tab 內 30s 防狂打 backend）
   *   - 'success': 200 OK
   *   - 'terminal': 403（員工帳號無權限）/ 404（KV 無此 email）
   *   - 'transient': 401（cookie 過期 / 沒帶 / JWT verify 失敗）/ 429 / 5xx
   *   - 'network': fetch 拋例外 / timeout
   *
   * v2.0 移除：'locked'（不再有 session-permanent lock — ADR-0004 L45）
   */
  reason: 'cooldown' | 'success' | 'terminal' | 'transient' | 'network';
}

/** 設定 */
export interface SSOBridgeConfig {
  /** consumer API base URL，例如 'https://lvrland.cksurvey.tw/api' */
  apiBaseURL: string;
  /** endpoint path，預設 '/auth/sso-bridge' */
  endpoint?: string;
  /** fetch timeout (ms)，預設 8000 */
  timeoutMs?: number;
  /** cooldown 期間（同 session 內不重打），預設 30000 */
  cooldownMs?: number;
  /** sessionStorage key 前綴，避免多 SSO 並存衝突，預設 'ck_sso_bridge' */
  storagePrefix?: string;
  /** logger，預設 console；傳 null 完全靜默 */
  logger?: Pick<Console, 'log' | 'warn'> | null;
  /** 成功後 callback；不傳則用 successRedirect 預設行為 */
  onSuccess?: (data: unknown) => void;
  /**
   * onSuccess 未指定時的預設跳轉路徑，預設 '/dashboard'。
   * v1.1：用 location.replace（非 reload / href）— L44 Part 2 修法：
   * 避免 protected route guard 在 zustand persist rehydrate 完成前攔截 → 假面失敗。
   */
  successRedirect?: string;
  /** 自訂 fetch（給測試或 axios adapter 用）*/
  fetchImpl?: typeof fetch;
}

// ─── 內部工具 ─────────────────────────────────────────────────────

interface StorageKeys {
  lastAttempt: string;
}

function buildKeys(prefix: string): StorageKeys {
  return {
    lastAttempt: `${prefix}_last_attempt`,
  };
}

function safeGet(key: string): string | null {
  try { return sessionStorage.getItem(key); } catch { return null; }
}
function safeSet(key: string, value: string): void {
  try { sessionStorage.setItem(key, value); } catch { /* ignore */ }
}
function safeRemove(key: string): void {
  try { sessionStorage.removeItem(key); } catch { /* ignore */ }
}

// ─── 核心 ─────────────────────────────────────────────────────────

/**
 * 嘗試 SSO bridge。
 *
 * @example
 * // React EntryPage useEffect
 * useEffect(() => {
 *   attemptSSOBridge({
 *     apiBaseURL: 'https://lvrland.cksurvey.tw/api',
 *     onSuccess: () => navigate('/dashboard'),
 *   }).then((r) => { if (!r.ok) setShowLoginUI(true); });
 * }, []);
 */
export async function attemptSSOBridge(
  config: SSOBridgeConfig,
): Promise<SSOBridgeResult> {
  const {
    apiBaseURL,
    endpoint = '/auth/sso-bridge',
    timeoutMs = 8000,
    cooldownMs = 30_000,
    storagePrefix = 'ck_sso_bridge',
    logger = console,
    onSuccess,
    successRedirect = '/dashboard',
    fetchImpl = fetch,
  } = config;

  const keys = buildKeys(storagePrefix);
  const log = logger ?? { log: () => {}, warn: () => {} };

  // Cooldown（v2.0：唯一保留的防禦層）
  const now = Date.now();
  const last = parseInt(safeGet(keys.lastAttempt) || '0', 10);
  if (last > 0 && now - last < cooldownMs) {
    return { ok: false, reason: 'cooldown' };
  }
  safeSet(keys.lastAttempt, String(now));

  const url = `${apiBaseURL.replace(/\/+$/, '')}${endpoint}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetchImpl(url, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
      signal: controller.signal,
    });
    clearTimeout(timer);

    let data: unknown;
    try { data = await res.json(); } catch { /* may be empty */ }

    if (res.status === 200) {
      log.log('[SSO-BRIDGE] success', { status: res.status });
      if (onSuccess) {
        try { onSuccess(data); } catch (e) { log.warn('[SSO-BRIDGE] onSuccess threw', e); }
      } else if (typeof window !== 'undefined') {
        // v1.1 (L44 Part 2): replace('/dashboard') 取代 reload()
        // 原因：reload 觸發 route guard 在 zustand persist rehydrate 完成前同步檢查 →
        // 看到 isAuthenticated=false → 立刻 Navigate /login → 假面失敗。
        // replace + 明確目標路徑 → full document load 同步初始化 localStorage 完成才 mount React。
        window.location.replace(successRedirect);
      }
      return { ok: true, status: 200, data, reason: 'success' };
    }

    if (res.status === 403 || res.status === 404) {
      log.log('[SSO-BRIDGE] terminal failure (no lock — v2.0)', { status: res.status });
      return { ok: false, status: res.status, data, reason: 'terminal' };
    }

    log.log('[SSO-BRIDGE] transient failure (no lock — v2.0)', { status: res.status });
    return { ok: false, status: res.status, data, reason: 'transient' };
  } catch (e) {
    clearTimeout(timer);
    log.log('[SSO-BRIDGE] network/timeout error', e);
    return { ok: false, reason: 'network' };
  }
}

/**
 * 重置 cooldown（v2.0：lock 已移除，只清 lastAttempt 立刻可重試）。
 * 用途：登出後、user 手動「重試 SSO」按鈕、debug。
 *
 * v2.0 breaking：不再清 flag / failCount（已移除）；只清 lastAttempt。
 * 舊版 caller 直接呼叫仍正常運作，但 sessionStorage 殘留的 *_attempted / *_fail_count
 * key 不會被自動清掉（無害，下次正常嘗試不受影響）。
 */
export function resetSSOBridgeState(storagePrefix = 'ck_sso_bridge'): void {
  const keys = buildKeys(storagePrefix);
  safeRemove(keys.lastAttempt);
  // v2.0：順便清掉舊版殘留（向前相容遷移）
  safeRemove(`${storagePrefix}_attempted`);
  safeRemove(`${storagePrefix}_fail_count`);
}

/**
 * 查詢目前的 cooldown 狀態（給 UI 顯示）。
 *
 * v2.0 breaking：移除 `locked` / `failCount` 欄位（已不存在概念）。
 */
export function getSSOBridgeState(storagePrefix = 'ck_sso_bridge'): {
  lastAttemptAt: number | null;
  cooldownRemainingMs: number;
} {
  const keys = buildKeys(storagePrefix);
  const last = parseInt(safeGet(keys.lastAttempt) || '0', 10) || null;
  const cooldownRemainingMs = last ? Math.max(0, 30_000 - (Date.now() - last)) : 0;
  return { lastAttemptAt: last, cooldownRemainingMs };
}

/**
 * ck-sso-js — framework-agnostic SSO Bridge for *.cksurvey.tw consumer frontends.
 *
 * 抽自 CK_Missive frontend `api/interceptors.ts attemptSSOBridge() v3.0` +
 * `services/authService.ts ssoBridge() v3.0`（2026-05-21 L41-sealed)。
 *
 * 用途：consumer React/Vue/vanilla 在 EntryPage / 任意「未登入入口」mount 時呼叫，
 * 嘗試用 www.cksurvey.tw 的 ck_employee cookie 自動建立 consumer session。
 *
 * 設計原則：
 *   - 純 fetch / sessionStorage，無框架依賴（axios 可選 transport）
 *   - 三層防禦：cooldown 30s × max-fail 3 × terminal lock
 *   - 不暴露 cookie 給 JS（HttpOnly cookie auto-send via credentials:'include'）
 *
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
   *   - 'locked':  sessionStorage 終態鎖 / 已達 max-fail
   *   - 'cooldown': 距上次嘗試 < cooldownMs
   *   - 'success': 200 OK
   *   - 'terminal': 403 / 404（權限或帳號終態問題）
   *   - 'transient': 401 / 429 / 503 / 5xx
   *   - 'network': fetch 拋例外
   */
  reason: 'locked' | 'cooldown' | 'success' | 'terminal' | 'transient' | 'network';
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
  /** 連續失敗 N 次永久鎖，預設 3 */
  maxFail?: number;
  /** sessionStorage key 前綴，避免多 SSO 並存衝突，預設 'ck_sso_bridge' */
  storagePrefix?: string;
  /** logger，預設 console；傳 null 完全靜默 */
  logger?: Pick<Console, 'log' | 'warn'> | null;
  /** 成功後 callback；預設 reload 頁面套用新 session */
  onSuccess?: (data: unknown) => void;
  /** 自訂 fetch（給測試或 axios adapter 用）*/
  fetchImpl?: typeof fetch;
}

// ─── 內部工具 ─────────────────────────────────────────────────────

interface StorageKeys {
  flag: string;
  lastAttempt: string;
  failCount: string;
}

function buildKeys(prefix: string): StorageKeys {
  return {
    flag: `${prefix}_attempted`,
    lastAttempt: `${prefix}_last_attempt`,
    failCount: `${prefix}_fail_count`,
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
    maxFail = 3,
    storagePrefix = 'ck_sso_bridge',
    logger = console,
    onSuccess,
    fetchImpl = fetch,
  } = config;

  const keys = buildKeys(storagePrefix);
  const log = logger ?? { log: () => {}, warn: () => {} };

  // (A) 終態鎖
  if (safeGet(keys.flag) === '1') {
    return { ok: false, reason: 'locked' };
  }

  // (B) Cooldown
  const now = Date.now();
  const last = parseInt(safeGet(keys.lastAttempt) || '0', 10);
  if (last > 0 && now - last < cooldownMs) {
    return { ok: false, reason: 'cooldown' };
  }
  safeSet(keys.lastAttempt, String(now));

  const lockTerminal = (): void => {
    safeSet(keys.flag, '1');
    safeRemove(keys.failCount);
  };
  const incrementFail = (): void => {
    const cur = parseInt(safeGet(keys.failCount) || '0', 10);
    const next = cur + 1;
    safeSet(keys.failCount, String(next));
    if (next >= maxFail) safeSet(keys.flag, '1');
  };

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
      lockTerminal();
      if (onSuccess) {
        try { onSuccess(data); } catch (e) { log.warn('[SSO-BRIDGE] onSuccess threw', e); }
      } else if (typeof window !== 'undefined') {
        window.location.reload();
      }
      return { ok: true, status: 200, data, reason: 'success' };
    }

    if (res.status === 403 || res.status === 404) {
      lockTerminal();
      log.log('[SSO-BRIDGE] terminal failure', { status: res.status });
      return { ok: false, status: res.status, data, reason: 'terminal' };
    }

    incrementFail();
    log.log('[SSO-BRIDGE] transient failure', { status: res.status });
    return { ok: false, status: res.status, data, reason: 'transient' };
  } catch (e) {
    clearTimeout(timer);
    incrementFail();
    log.log('[SSO-BRIDGE] network/timeout error', e);
    return { ok: false, reason: 'network' };
  }
}

/**
 * 重置所有 SSO bridge 鎖 / cooldown / 失敗計數。
 * 用途：登出後、user 手動「重試 SSO」按鈕、debug。
 */
export function resetSSOBridgeState(storagePrefix = 'ck_sso_bridge'): void {
  const keys = buildKeys(storagePrefix);
  safeRemove(keys.flag);
  safeRemove(keys.lastAttempt);
  safeRemove(keys.failCount);
}

/**
 * 查詢目前的 lock / 失敗狀態（給 UI 顯示）。
 */
export function getSSOBridgeState(storagePrefix = 'ck_sso_bridge'): {
  locked: boolean;
  lastAttemptAt: number | null;
  failCount: number;
} {
  const keys = buildKeys(storagePrefix);
  return {
    locked: safeGet(keys.flag) === '1',
    lastAttemptAt: parseInt(safeGet(keys.lastAttempt) || '0', 10) || null,
    failCount: parseInt(safeGet(keys.failCount) || '0', 10),
  };
}

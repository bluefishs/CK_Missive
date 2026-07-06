/**
 * Axios Interceptors & Instance
 *
 * Axios instance creation, request/response interceptors,
 * cookie helpers, and URL configuration.
 *
 * Extracted from client.ts (v3.0.0 split)
 */

import axios, {
  AxiosInstance,
  AxiosResponse,
  AxiosError,
  InternalAxiosRequestConfig,
} from 'axios';
import {
  ErrorCode,
  ErrorResponse,
} from './types';

// 從拆分模組匯入
import { ApiException, apiErrorBus } from './errors';
import { RequestThrottler, RETRY_CONFIG, isRetryableNetworkError } from './throttler';

// ============================================================================
// 配置常量
// ============================================================================

import { isInternalIPAddress } from '../config/env';
import { AUTH_ENDPOINTS } from './endpoints';
import { logger } from '../services/logger';

// ============================================================================
// Cookie 工具函數
// ============================================================================

/**
 * 從 document.cookie 中讀取指定名稱的 cookie 值
 *
 * @param name cookie 名稱
 * @returns cookie 值，或 null（若不存在）
 */
export function getCookie(name: string): string | null {
  const nameEq = `${name}=`;
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const trimmed = cookie.trim();
    if (trimmed.startsWith(nameEq)) {
      return decodeURIComponent(trimmed.substring(nameEq.length));
    }
  }
  return null;
}

/**
 * 動態 API URL 計算
 * 根據存取來源自動選擇正確的後端位址
 *
 * 內網 IP 判斷使用 config/env.ts 的共用常數 (SSOT)
 */
function getDynamicApiBaseUrl(): string {
  const hostname = window.location.hostname;
  const defaultPort = '8001';

  // 開發模式 → 一律使用相對路徑，透過 Vite proxy 轉發到後端
  // 避免 HTTPS 前端 → HTTP 後端的 mixed content / CORS 問題
  if (import.meta.env.DEV) {
    return '/api';
  }

  // === 以下為生產環境邏輯 ===

  // 1. localhost 或 127.0.0.1 → 使用 localhost 後端
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return `http://localhost:${defaultPort}/api`;
  }

  // 2. 內網 IP → 使用相同 IP 的後端（使用 config/env.ts 共用函數）
  if (isInternalIPAddress(hostname)) {
    return `http://${hostname}:${defaultPort}/api`;
  }

  // 3. ngrok 或其他公網域名 → 使用環境變數或相對路徑
  if (import.meta.env.VITE_API_BASE_URL) {
    return `${import.meta.env.VITE_API_BASE_URL}/api`;
  }

  // 4. 預設使用相對路徑（適用於同源部署）
  return '/api';
}

/** API 基礎 URL（動態計算，包含 /api） */
export const API_BASE_URL = getDynamicApiBaseUrl();

/** 伺服器基礎 URL（動態計算，不含 /api） */
export const SERVER_BASE_URL = API_BASE_URL.replace(/\/api$/, '');

// 開發模式下輸出 API URL 資訊
if (import.meta.env.DEV) {
  logger.log('Dynamic API URL:', API_BASE_URL);
  logger.log('Hostname:', window.location.hostname);
}

/** 預設請求超時時間（毫秒） */
const DEFAULT_TIMEOUT = 30000;

/** 認證是否禁用（開發模式） */
const AUTH_DISABLED = import.meta.env['VITE_AUTH_DISABLED'] === 'true';

const requestThrottler = new RequestThrottler();

// ============================================================================
// SSO Bridge — ADR-0001 / CK_Website#0001 / ADR-0004 L45 (B 案治本)
// 401 後嘗試用 www.cksurvey.tw 的 ck_employee cookie 建立 Missive session
// 成功 → replace('/dashboard') 套用新 session；失敗 → 走原本登入流程
//
// v4.0 (2026-05-22, ADR-0004 L45)：移除「session-permanent lock」反模式。
//   v3.0 sessionStorage flag (ck_sso_bridge_attempted=1) 在 5/19~5/22 反覆 debug
//   累積，造成 user 報「必須先在 missive 自己登入並保持頁面開啟」假象 — 實際是
//   ssoBridge 從未真嘗試，直接 return false。
//   v4.0 只留 cooldown 30s（防 React Strict Mode double mount + 死循環 429）。
//   失敗 → 用戶看 login UI → 用戶 reload / 重點卡 → 30s 後可重試。
// ============================================================================

const SSO_BRIDGE_LAST_ATTEMPT = 'ck_sso_bridge_last_attempt';

async function attemptSSOBridge(): Promise<boolean> {
  const COOLDOWN_MS = 30_000;

  try {
    const now = Date.now();
    const lastAttempt = parseInt(sessionStorage.getItem(SSO_BRIDGE_LAST_ATTEMPT) || '0', 10);
    if (lastAttempt > 0 && (now - lastAttempt) < COOLDOWN_MS) return false;
    sessionStorage.setItem(SSO_BRIDGE_LAST_ATTEMPT, String(now));
    // 順便清舊版殘留 key（向前相容遷移）
    sessionStorage.removeItem('ck_sso_bridge_attempted');
    sessionStorage.removeItem('ck_sso_bridge_fail_count');
  } catch {
    // sessionStorage 不可用就略過 guard
  }

  try {
    const res = await axios.post(
      `${API_BASE_URL}${AUTH_ENDPOINTS.SSO_BRIDGE}`,
      {},
      { withCredentials: true, timeout: 8000 },
    );
    if (res.status === 200 && res.data?.user_info) {
      // 2026-07-03 SSO「停在登入頁 / Header 訪客 / user_info=NULL」根治：
      //   本函式過去只 POST sso-bridge（後端設 httpOnly cookie）就 location.replace('/dashboard')，
      //   **從不把回傳的 user_info 寫進 localStorage** → 整頁重載後 sessionStore.bootstrap 讀
      //   getUserInfo()=NULL → 直接判 anonymous（連 /auth/check 都不驗）→ 導向 /entry、Header 顯訪客，
      //   即使後端 cookie 有效（故 /auth/me 仍 200，製造「登入成功卻回不去」假象）。
      //   authService.ssoBridge() 有 saveAuthData（寫 user_info）、本 raw 路徑漏了 → 補齊持久化。
      try {
        localStorage.setItem('user_info', JSON.stringify(res.data.user_info));
        if (res.data.access_token) localStorage.setItem('access_token', res.data.access_token);
        if (res.data.refresh_token) localStorage.setItem('refresh_token', res.data.refresh_token);
      } catch { /* localStorage 不可用（極罕見）→ 仍 reload，bootstrap 會再走一次 SSO */ }
      logger.log('[SSO-BRIDGE] succeeded (user_info 已持久化); navigating to /dashboard');
      // L44 P2 修法：location.replace 取代 reload — 避免 protected route guard
      // 在 zustand persist rehydrate 完成前同步檢查踢回 /login
      window.location.replace('/dashboard');
      return true;
    }
    return false;
  } catch (e: unknown) {
    logger.log('[SSO-BRIDGE] not available or failed; falling through to login', e);
    return false;
  }
}

// ============================================================================
// 建立 Axios 實例
// ============================================================================

/**
 * 建立並配置 Axios 實例
 */
function createAxiosInstance(): AxiosInstance {
  const instance = axios.create({
    baseURL: API_BASE_URL,
    timeout: DEFAULT_TIMEOUT,
    withCredentials: true,  // 啟用 cookie 跨域傳送（httpOnly cookie 認證）
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Token Key 常數（與 authService 統一）
  const ACCESS_TOKEN_KEY = 'access_token';
  const REFRESH_TOKEN_KEY = 'refresh_token';

  // 標記是否正在刷新 token
  let isRefreshing = false;
  let refreshSubscribers: Array<(token: string) => void> = [];

  const subscribeTokenRefresh = (cb: (token: string) => void) => {
    refreshSubscribers.push(cb);
  };

  const onTokenRefreshed = (token: string) => {
    refreshSubscribers.forEach((cb) => cb(token));
    refreshSubscribers = [];
  };

  // 請求節流攔截器（防止無限迴圈造成請求風暴）
  instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const result = requestThrottler.check(config.method, config.url);

      if (result.action === 'cache') {
        // 返回快取：透過自訂 adapter 直接返回上次結果
        const cachedData = result.data;
        config.adapter = () => Promise.resolve({
          data: cachedData,
          status: 200,
          statusText: 'OK (throttled cache)',
          headers: {},
          config,
        } as AxiosResponse);
      } else if (result.action === 'reject') {
        return Promise.reject(new ApiException(
          ErrorCode.TOO_MANY_REQUESTS,
          `請求被熔斷器攔截: ${result.reason}`,
          429
        ));
      }

      return config;
    }
  );

  // 請求攔截器（認證 Token - 向後相容過渡期）
  instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      // 向後相容：仍從 localStorage 讀取 token 附加到 header
      // 當完全遷移到 cookie 後，此段可移除
      const token = localStorage.getItem(ACCESS_TOKEN_KEY);
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // 請求攔截器（CSRF Token）
  instance.interceptors.request.use(
    async (config: InternalAxiosRequestConfig) => {
      const method = config.method?.toUpperCase() || '';
      // 非安全方法才需要附加 CSRF token
      if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
        let csrfToken = getCookie('csrf_token');
        // L68 (2026-06-10) CSRF 自癒：csrf_token cookie 固定 1h 過期 / iOS Safari 清除後，
        //   會出現「有 access_token cookie 但無 csrf cookie」→ 後端 CSRFMiddleware 403，
        //   被 GlobalApiErrorNotifier 誤標「權限不足」(OWASP CSRF 觀察點)。
        //   已登入(user_info)時主動補打已豁免的 csrf-token endpoint 重設 csrf cookie 再送。
        //   用裸 axios 避免遞迴觸發本攔截器；same-origin 才能補，跨站攻擊無法觸發→不削弱防護。
        if (!csrfToken && localStorage.getItem('user_info')) {
          try {
            await axios.post(
              `${API_BASE_URL}/secure-site-management/csrf-token`,
              {},
              { withCredentials: true }
            );
            csrfToken = getCookie('csrf_token');
          } catch {
            /* 補取失敗 → 後端會擋，走既有錯誤流，不阻斷請求 */
          }
        }
        if (csrfToken && config.headers) {
          config.headers['X-CSRF-Token'] = csrfToken;
        }
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // 回應攔截器（含 Token 自動刷新機制）
  instance.interceptors.response.use(
    (response: AxiosResponse) => {
      // 記錄成功回應供節流快取使用
      requestThrottler.recordResponse(
        response.config?.method,
        response.config?.url,
        response.data
      );
      return response;
    },
    async (error: AxiosError<ErrorResponse>) => {
      const originalRequest = error.config as InternalAxiosRequestConfig & {
        _retry?: boolean;
        _retryCount?: number;
      };

      // 網路錯誤自動重試（後端重啟期間的 ERR_CONNECTION_REFUSED）
      if (isRetryableNetworkError(error) && originalRequest) {
        const retryCount = originalRequest._retryCount || 0;
        if (retryCount < RETRY_CONFIG.MAX_RETRIES) {
          originalRequest._retryCount = retryCount + 1;
          const delay = Math.min(
            RETRY_CONFIG.BASE_DELAY_MS * Math.pow(RETRY_CONFIG.BACKOFF_MULTIPLIER, retryCount),
            RETRY_CONFIG.MAX_DELAY_MS
          );
          logger.warn(
            `[Retry] 網路錯誤，${delay}ms 後重試 (${retryCount + 1}/${RETRY_CONFIG.MAX_RETRIES}): ${originalRequest.url}`
          );
          await new Promise(resolve => setTimeout(resolve, delay));
          return instance(originalRequest);
        }
        // 重試耗盡，繼續走正常錯誤處理
        logger.error(`[Retry] 重試耗盡 (${RETRY_CONFIG.MAX_RETRIES}次)，後端可能未啟動: ${originalRequest.url}`);
      }

      // 處理 401 未授權
      if (error.response?.status === 401 && !AUTH_DISABLED) {
        // 檢查是否曾經登入過（user_info 才是真實認證證據）
        // F20 (5/04 修復)：原本用 csrf_token cookie 存在 ≠ 已登入。
        // 後端 commit 128392cb 讓 csrf-token endpoint 對任何訪客都設 cookie，
        // 導致無痕訪客誤判為「已登入」→ 觸發 refresh → 401 → 死循環。
        // 改用 user_info（僅 login 成功 setAuthData() 才會寫入 localStorage）。
        const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
        const hasUserInfo = !!localStorage.getItem('user_info');

        if ((refreshToken || hasUserInfo) && !originalRequest._retry) {
          if (isRefreshing) {
            // 如果正在刷新，等待刷新完成後重試
            return new Promise((resolve) => {
              subscribeTokenRefresh(() => {
                // cookie 認證模式下，重試時不需要手動設定 header
                resolve(instance(originalRequest));
              });
            });
          }

          originalRequest._retry = true;
          isRefreshing = true;

          try {
            // 嘗試刷新 token
            // 同時發送 body（向後相容）和依賴 cookie（新機制）
            const refreshPayload = refreshToken ? { refresh_token: refreshToken } : {};
            const response = await axios.post(
              `${API_BASE_URL}${AUTH_ENDPOINTS.REFRESH}`,
              refreshPayload,
              { withCredentials: true }
            );

            const { access_token, refresh_token: newRefreshToken } = response.data;

            // 向後相容：更新 localStorage（過渡期）
            if (access_token) {
              localStorage.setItem(ACCESS_TOKEN_KEY, access_token);
            }
            if (newRefreshToken) {
              localStorage.setItem(REFRESH_TOKEN_KEY, newRefreshToken);
            }

            // 通知所有等待的請求
            onTokenRefreshed(access_token || '');
            isRefreshing = false;

            // 重試原始請求（cookie 會自動附帶新的 access_token）
            if (access_token && originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${access_token}`;
            }
            return instance(originalRequest);
          } catch (refreshError) {
            // 刷新失敗
            isRefreshing = false;
            // 2026-07-02 SSO「閃一下又跳回登入」根治：sessionStore 已認證（剛 SSO/登入成功）時，
            //   單一端點 401（尤高頻輪詢 system-notifications/unread-count）+ refresh 失敗，
            //   不清 session、不跳 /login —— 僅讓該請求失敗。真失效於下次 reload bootstrap 驗證時降級。
            //   （原行為：任一 401+refresh 失敗即清 user_info + attemptSSOBridge cooldown → 硬跳 /login）
            const { useSessionStore } = await import('../store/sessionStore');
            // 2026-07-03：'authenticated' → '!== anonymous'（含 resolving），與 authService
            //   實例守衛一致 → bootstrap 進行中（resolving）的瞬態 401 也不觸發破壞性清除+導向。
            const believedAuthed = useSessionStore.getState().status !== 'anonymous';
            if (!believedAuthed) {
              localStorage.removeItem(ACCESS_TOKEN_KEY);
              localStorage.removeItem(REFRESH_TOKEN_KEY);
              localStorage.removeItem('user_info');
              document.cookie = 'csrf_token=; Path=/; Max-Age=0';
              if (!window.location.pathname.includes('/login')) {
                // ADR-0001：跳登入前先試 SSO bridge（成功會 reload，失敗才走 login）
                const ssoOk = await attemptSSOBridge();
                if (!ssoOk) {
                  window.location.href = '/login';
                }
                // 2026-07-06「第一次登入點選單閃錯誤訊息、自動刷新後正常」根治：
                //   走到這裡整頁跳轉已註定（bridge 成功 location.replace('/dashboard')；
                //   失敗/cooldown → href='/login'）。原本仍 throw → 元件在 reload 落地前
                //   收到 reject 而閃錯（token 過期復原窗口 ~2s 內的所有頁面請求）。
                //   頁面即將卸載 → 掛起原請求（never-resolve）安全且無感。
                return new Promise(() => { /* 整頁跳轉中，掛起原請求 */ });
              }
            }
            throw ApiException.fromAxiosError(error);
          }
        } else {
          // 2026-07-02 SSO「閃一下又跳回登入」根治（同上）：已認證時不清 session、不跳 /login
          const { useSessionStore } = await import('../store/sessionStore');
          // 2026-07-03：同上，resolving 也視為受保護（不清除、不導向）
          const believedAuthed = useSessionStore.getState().status !== 'anonymous';
          if (!believedAuthed) {
            // 沒有 refresh token，清除並嘗試 SSO bridge
            localStorage.removeItem(ACCESS_TOKEN_KEY);
            localStorage.removeItem(REFRESH_TOKEN_KEY);
            localStorage.removeItem('user_info');
            document.cookie = 'csrf_token=; Path=/; Max-Age=0';

            if (!window.location.pathname.includes('/login')) {
              // ADR-0001：跳登入前先試 SSO bridge
              const ssoOk = await attemptSSOBridge();
              if (!ssoOk) {
                window.location.href = '/login';
              }
              // 2026-07-06：同上分支——整頁跳轉已註定，掛起原請求防復原窗口閃錯
              return new Promise(() => { /* 整頁跳轉中，掛起原請求 */ });
            }
          }
        }
      }

      // 轉換為 ApiException 並發出全域錯誤事件
      const apiError = error instanceof ApiException
        ? error
        : ApiException.fromAxiosError(error);
      // 靜默判斷：_silent 標記 或 AI 端點路徑（AI API 內部 catch 處理，不需全域通知）
      const isSilent = !!(originalRequest as unknown as Record<string, unknown>)?._silent
        || originalRequest?.url?.startsWith('/api/ai/') === true;
      if (!isSilent && apiError.isGlobalError()) {
        apiErrorBus.emit(apiError);
      }
      throw apiError;
    }
  );

  return instance;
}

// 建立單例實例
export const axiosInstance = createAxiosInstance();

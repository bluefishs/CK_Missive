/**
 * interceptors.ts auth 生命週期 robustness regression（2026-07-25）
 *
 * 鎖定 AUTH_LIFECYCLE_ROBUSTNESS_DESIGN.md §5.1 兩項前端修法（2026-07-27 live 事證觸發）：
 *   FE-1（I2）：CSRF token 補打單飛 — 併發 mutation 只鑄一次 token，消 double-submit race。
 *   FE-2（I3）：CSRF-403 可恢復 — 單飛重取 csrf + 單次重試；非 csrf 的 403（真權限）不重試、
 *              仍 403 才彈全域錯誤。
 *
 * 手法：mock axios.create 捕捉 request/response 攔截器 handler，直接呼叫驗證行為
 *   （對齊 authService.interceptor401.regression.test.ts 既有範式）。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

const h = vi.hoisted(() => ({
  reqHandlers: [] as Array<(c: unknown) => unknown>,
  respReject: null as null | ((e: unknown) => Promise<unknown>),
  instanceCalls: [] as unknown[],
  csrfPostCount: 0,
  emitCount: 0,
  // 可控 csrf-token POST（用於單飛併發測）
  pendingResolvers: [] as Array<() => void>,
  postManual: false,
}));

vi.mock('axios', () => {
  const post = vi.fn(() => {
    h.csrfPostCount++;
    if (h.postManual) {
      return new Promise<{ data: unknown }>((resolve) => {
        h.pendingResolvers.push(() => resolve({ data: {} }));
      });
    }
    return Promise.resolve({ data: {} });
  });
  const create = vi.fn(() => {
    const inst = vi.fn((cfg: unknown) => {
      h.instanceCalls.push(cfg);
      return Promise.resolve({ data: 'retried', config: cfg });
    }) as unknown as {
      (cfg: unknown): unknown;
      interceptors: { request: { use: unknown }; response: { use: unknown } };
      post: unknown;
    };
    inst.interceptors = {
      request: { use: vi.fn((f: (c: unknown) => unknown) => { h.reqHandlers.push(f); }) },
      response: {
        use: vi.fn((_f: unknown, r: (e: unknown) => Promise<unknown>) => { h.respReject = r; }),
      },
    };
    inst.post = post;
    return inst;
  });
  return { default: { create, post, isAxiosError: () => false } };
});

vi.mock('../errors', () => ({
  ErrorCode: { TOO_MANY_REQUESTS: 'TOO_MANY_REQUESTS' },
  ApiException: class {
    isGlobalError() { return true; }
    static fromAxiosError() { return new (this as unknown as { new (): { isGlobalError(): boolean } })(); }
  },
  apiErrorBus: { emit: vi.fn(() => { h.emitCount++; }) },
}));

vi.mock('../throttler', () => ({
  RequestThrottler: class { check() { return { action: 'pass' }; } recordResponse() {} },
  RETRY_CONFIG: { MAX_RETRIES: 0, BASE_DELAY_MS: 1, BACKOFF_MULTIPLIER: 2, MAX_DELAY_MS: 1 },
  isRetryableNetworkError: () => false,
}));

vi.mock('../../config/env', () => ({ isInternalIPAddress: () => false }));
vi.mock('../endpoints', () => ({ AUTH_ENDPOINTS: { REFRESH: '/auth/refresh' } }));
vi.mock('../../services/logger', () => ({
  logger: { error: vi.fn(), warn: vi.fn(), log: vi.fn(), info: vi.fn(), debug: vi.fn() },
}));

// localStorage + document.cookie 控制
const store: Record<string, string> = {};
Object.defineProperty(globalThis, 'localStorage', {
  value: {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => { store[k] = v; },
    removeItem: (k: string) => { delete store[k]; },
  },
  writable: true,
});
let cookieStr = '';
Object.defineProperty(globalThis, 'document', {
  value: { get cookie() { return cookieStr; }, set cookie(v: string) { cookieStr = v; } },
  writable: true,
});
Object.defineProperty(globalThis, 'window', {
  value: { location: { href: '', pathname: '/taoyuan/dispatch', replace: vi.fn() } },
  writable: true,
});

// ⚠️ .env.development/.env.local 有 VITE_AUTH_DISABLED=true → 會使 AUTH_DISABLED=true 擋掉
//   FE-2 的 !AUTH_DISABLED 分支（且讓負向測試假通過）。必須在 import 前 stub 為 false，
//   且因 AUTH_DISABLED 於模組載入時計算 → 用動態 import 確保 stub 先生效。
import { beforeAll } from 'vitest';
beforeAll(async () => {
  vi.stubEnv('VITE_AUTH_DISABLED', 'false');
  await import('../interceptors'); // 建構 axiosInstance → 捕捉攔截器
});

const csrfRequestHandler = () => h.reqHandlers[h.reqHandlers.length - 1]; // 最後註冊＝CSRF

describe('interceptors FE-1：CSRF 補打單飛（I2）', () => {
  beforeEach(() => {
    store['user_info'] = JSON.stringify({ id: 1 });
    cookieStr = ''; // 無 csrf cookie → 觸發補打
    h.csrfPostCount = 0;
    h.pendingResolvers = [];
  });

  it('併發兩個 mutation（無 csrf cookie）只鑄一次 token', async () => {
    h.postManual = true;
    const handler = csrfRequestHandler();
    if (!handler) throw new Error('CSRF request handler 未捕捉');
    const cfg1 = { method: 'POST', headers: {} };
    const cfg2 = { method: 'POST', headers: {} };
    const p1 = handler(cfg1);
    const p2 = handler(cfg2);
    // 兩者都已進入單飛前置 → 只該有一個 in-flight POST
    expect(h.csrfPostCount).toBe(1);
    h.pendingResolvers.forEach((r) => r());
    await Promise.all([p1, p2]);
    expect(h.csrfPostCount).toBe(1);
    h.postManual = false;
  });
});

describe('interceptors FE-2：CSRF-403 可恢復重試（I3）', () => {
  beforeEach(() => {
    store['user_info'] = JSON.stringify({ id: 1 });
    cookieStr = 'csrf_token=fresh';
    h.instanceCalls = [];
    h.csrfPostCount = 0;
    h.emitCount = 0;
  });

  it('403 + csrf detail → 重取 csrf + 重試一次', async () => {
    const err = {
      response: { status: 403, data: { detail: 'CSRF 驗證失敗：token 不匹配' } },
      config: { headers: {}, url: '/api/taoyuan-dispatch/dispatch/list' },
      message: 'Request failed',
    };
    await h.respReject!(err);
    expect(h.csrfPostCount).toBe(1);        // 重取 csrf
    expect(h.instanceCalls.length).toBe(1); // 重試一次
    expect(h.emitCount).toBe(0);            // 未彈全域錯誤
  });

  it('403 但非 csrf（真權限）→ 不重試、彈全域錯誤', async () => {
    const err = {
      response: { status: 403, data: { detail: '您沒有權限執行此操作' } },
      config: { headers: {}, url: '/api/x' },
      message: 'Forbidden',
    };
    await expect(h.respReject!(err)).rejects.toBeDefined();
    expect(h.instanceCalls.length).toBe(0); // 不重試
    expect(h.emitCount).toBe(1);            // 彈全域錯誤
  });

  it('403 csrf 但已重試過（_csrfRetry）→ 不再重試、彈錯', async () => {
    const err = {
      response: { status: 403, data: { detail: 'CSRF 驗證失敗：token 不匹配' } },
      config: { headers: {}, url: '/api/x', _csrfRetry: true },
      message: 'Forbidden',
    };
    await expect(h.respReject!(err)).rejects.toBeDefined();
    expect(h.instanceCalls.length).toBe(0);
    expect(h.emitCount).toBe(1);
  });
});

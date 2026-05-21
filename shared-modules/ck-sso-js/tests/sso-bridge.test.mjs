/**
 * ck-sso-js unit tests (no test framework — plain assert + node test).
 *
 * Coverage：13 cases — sessionStorage 三層防禦、5 種 reason 路徑、
 * fetch impl 注入、storagePrefix 隔離、onSuccess callback。
 *
 * 跑法：node tests/sso-bridge.test.mjs
 */
import { strict as assert } from 'node:assert';
import { test } from 'node:test';

// 模擬 sessionStorage（Node 環境沒有）
class MemStorage {
  store = new Map();
  getItem(k) { return this.store.has(k) ? this.store.get(k) : null; }
  setItem(k, v) { this.store.set(k, String(v)); }
  removeItem(k) { this.store.delete(k); }
  clear() { this.store.clear(); }
}
globalThis.sessionStorage = new MemStorage();
globalThis.window = { location: { reload: () => { globalThis.__reloadCalled = true; } } };

// 動態 import 以確保 sessionStorage mock 先 set
const { attemptSSOBridge, resetSSOBridgeState, getSSOBridgeState } =
  await import('../src/sso-bridge.ts').catch(async () => {
    // fallback：直接 import .ts via tsx 或預先編 .mjs
    return await import('../dist/sso-bridge.js');
  });

function mockFetch(status, body = {}) {
  return async () => ({
    status,
    json: async () => body,
    ok: status >= 200 && status < 300,
  });
}

function mockFetchThrows(err = new Error('network down')) {
  return async () => { throw err; };
}

const SILENT = { log: () => {}, warn: () => {} };

function freshSession() {
  sessionStorage.clear();
  globalThis.__reloadCalled = false;
}

// ─── Tests ────────────────────────────────────────────────────────

test('200 success → ok + reason:success + lock + onSuccess called', async () => {
  freshSession();
  let onSuccessCalled = false;
  const r = await attemptSSOBridge({
    apiBaseURL: 'https://x.test',
    fetchImpl: mockFetch(200, { user_info: { email: 'a@b' } }),
    onSuccess: () => { onSuccessCalled = true; },
    logger: SILENT,
  });
  assert.equal(r.ok, true);
  assert.equal(r.reason, 'success');
  assert.equal(onSuccessCalled, true);
  assert.equal(getSSOBridgeState().locked, true);
});

test('401 → transient, fail count +1, NO lock yet', async () => {
  freshSession();
  const r = await attemptSSOBridge({
    apiBaseURL: 'https://x.test',
    fetchImpl: mockFetch(401),
    logger: SILENT,
  });
  assert.equal(r.ok, false);
  assert.equal(r.reason, 'transient');
  assert.equal(r.status, 401);
  assert.equal(getSSOBridgeState().locked, false);
  assert.equal(getSSOBridgeState().failCount, 1);
});

test('403 → terminal + lock', async () => {
  freshSession();
  const r = await attemptSSOBridge({
    apiBaseURL: 'https://x.test',
    fetchImpl: mockFetch(403),
    logger: SILENT,
  });
  assert.equal(r.reason, 'terminal');
  assert.equal(getSSOBridgeState().locked, true);
});

test('404 → terminal + lock', async () => {
  freshSession();
  const r = await attemptSSOBridge({
    apiBaseURL: 'https://x.test',
    fetchImpl: mockFetch(404),
    logger: SILENT,
  });
  assert.equal(r.reason, 'terminal');
  assert.equal(getSSOBridgeState().locked, true);
});

test('network error → network + fail count', async () => {
  freshSession();
  const r = await attemptSSOBridge({
    apiBaseURL: 'https://x.test',
    fetchImpl: mockFetchThrows(),
    logger: SILENT,
  });
  assert.equal(r.reason, 'network');
  assert.equal(getSSOBridgeState().failCount, 1);
});

test('locked → reason:locked, no fetch call', async () => {
  freshSession();
  sessionStorage.setItem('ck_sso_bridge_attempted', '1');
  let fetched = false;
  const r = await attemptSSOBridge({
    apiBaseURL: 'https://x.test',
    fetchImpl: async () => { fetched = true; return { status: 200, json: async () => ({}) }; },
    logger: SILENT,
  });
  assert.equal(r.reason, 'locked');
  assert.equal(fetched, false);
});

test('cooldown → reason:cooldown, no fetch call', async () => {
  freshSession();
  sessionStorage.setItem('ck_sso_bridge_last_attempt', String(Date.now()));
  let fetched = false;
  const r = await attemptSSOBridge({
    apiBaseURL: 'https://x.test',
    cooldownMs: 30_000,
    fetchImpl: async () => { fetched = true; return { status: 200, json: async () => ({}) }; },
    logger: SILENT,
  });
  assert.equal(r.reason, 'cooldown');
  assert.equal(fetched, false);
});

test('cooldown 過期 → 允許新 attempt', async () => {
  freshSession();
  sessionStorage.setItem('ck_sso_bridge_last_attempt', String(Date.now() - 60_000));
  const r = await attemptSSOBridge({
    apiBaseURL: 'https://x.test',
    cooldownMs: 30_000,
    fetchImpl: mockFetch(401),
    logger: SILENT,
  });
  assert.equal(r.reason, 'transient');
  assert.equal(r.status, 401);
});

test('maxFail 3: 連續 3 個 401 → 第 3 個觸發 lock', async () => {
  freshSession();
  for (let i = 0; i < 3; i++) {
    // 每次都把 lastAttempt 推回過去解 cooldown
    sessionStorage.setItem('ck_sso_bridge_last_attempt', '0');
    await attemptSSOBridge({
      apiBaseURL: 'https://x.test',
      fetchImpl: mockFetch(401),
      maxFail: 3,
      cooldownMs: 0,
      logger: SILENT,
    });
  }
  assert.equal(getSSOBridgeState().locked, true);
  assert.equal(getSSOBridgeState().failCount, 3);
});

test('resetSSOBridgeState 清乾淨', async () => {
  freshSession();
  sessionStorage.setItem('ck_sso_bridge_attempted', '1');
  sessionStorage.setItem('ck_sso_bridge_fail_count', '5');
  sessionStorage.setItem('ck_sso_bridge_last_attempt', '12345');
  resetSSOBridgeState();
  const s = getSSOBridgeState();
  assert.equal(s.locked, false);
  assert.equal(s.failCount, 0);
  assert.equal(s.lastAttemptAt, null);
});

test('storagePrefix 隔離 (多 SSO 並存)', async () => {
  freshSession();
  sessionStorage.setItem('ck_sso_bridge_attempted', '1');
  // 不同 prefix 不互相影響
  const r = await attemptSSOBridge({
    apiBaseURL: 'https://x.test',
    storagePrefix: 'other_sso',
    fetchImpl: mockFetch(401),
    logger: SILENT,
  });
  assert.equal(r.reason, 'transient');
});

test('timeoutMs 觸發 AbortController', async () => {
  freshSession();
  const slowFetch = async (_, opts) => {
    // 模擬慢回應；若 abort signal 觸發則 throw AbortError
    return await new Promise((resolve, reject) => {
      const t = setTimeout(() => resolve({ status: 200, json: async () => ({}) }), 500);
      opts?.signal?.addEventListener('abort', () => {
        clearTimeout(t);
        reject(new DOMException('aborted', 'AbortError'));
      });
    });
  };
  const r = await attemptSSOBridge({
    apiBaseURL: 'https://x.test',
    timeoutMs: 50,
    fetchImpl: slowFetch,
    logger: SILENT,
  });
  assert.equal(r.reason, 'network');
});

test('apiBaseURL trailing slash 正常 join', async () => {
  freshSession();
  let urlCalled = '';
  await attemptSSOBridge({
    apiBaseURL: 'https://x.test/api///',
    endpoint: '/auth/sso-bridge',
    fetchImpl: async (url) => { urlCalled = url; return { status: 401, json: async () => ({}) }; },
    logger: SILENT,
  });
  assert.equal(urlCalled, 'https://x.test/api/auth/sso-bridge');
});

console.log('All ck-sso-js tests passed.');

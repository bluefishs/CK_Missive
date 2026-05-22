/**
 * ck-sso-js v2.0 unit tests (no test framework — plain assert + node test).
 *
 * v2.0 (ADR-0004 L45) 修法：移除終態鎖 + 連續失敗計數鎖，只留 cooldown。
 *
 * 跑法：node tests/sso-bridge.test.mjs
 */
import { strict as assert } from 'node:assert';
import { test } from 'node:test';

class MemStorage {
  store = new Map();
  getItem(k) { return this.store.has(k) ? this.store.get(k) : null; }
  setItem(k, v) { this.store.set(k, String(v)); }
  removeItem(k) { this.store.delete(k); }
  clear() { this.store.clear(); }
}
globalThis.sessionStorage = new MemStorage();
globalThis.window = { location: { replace: () => { globalThis.__replaceCalled = true; } } };

const { attemptSSOBridge, resetSSOBridgeState, getSSOBridgeState } =
  await import('../src/sso-bridge.ts').catch(async () => {
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
  globalThis.__replaceCalled = false;
}

// ─── Tests v2.0 ──────────────────────────────────────────────────

test('200 success → ok + reason:success + onSuccess called (v2.0: 不再 lock)', async () => {
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
  // v2.0：成功後不再設 lock — 下次 mount 仍可嘗試（受 cooldown 保護）
  const s = getSSOBridgeState();
  assert.ok(s.lastAttemptAt > 0);
});

test('401 → transient, NO lock (v2.0: 無 failCount 累積)', async () => {
  freshSession();
  const r = await attemptSSOBridge({
    apiBaseURL: 'https://x.test',
    fetchImpl: mockFetch(401),
    logger: SILENT,
  });
  assert.equal(r.ok, false);
  assert.equal(r.reason, 'transient');
  assert.equal(r.status, 401);
  // v2.0：sessionStorage 不再有 fail_count / attempted key
  assert.equal(sessionStorage.getItem('ck_sso_bridge_fail_count'), null);
  assert.equal(sessionStorage.getItem('ck_sso_bridge_attempted'), null);
});

test('403 → terminal, NO lock (v2.0)', async () => {
  freshSession();
  const r = await attemptSSOBridge({
    apiBaseURL: 'https://x.test',
    fetchImpl: mockFetch(403),
    logger: SILENT,
  });
  assert.equal(r.reason, 'terminal');
  assert.equal(sessionStorage.getItem('ck_sso_bridge_attempted'), null);
});

test('404 → terminal, NO lock (v2.0)', async () => {
  freshSession();
  const r = await attemptSSOBridge({
    apiBaseURL: 'https://x.test',
    fetchImpl: mockFetch(404),
    logger: SILENT,
  });
  assert.equal(r.reason, 'terminal');
  assert.equal(sessionStorage.getItem('ck_sso_bridge_attempted'), null);
});

test('network error → network, NO fail count (v2.0)', async () => {
  freshSession();
  const r = await attemptSSOBridge({
    apiBaseURL: 'https://x.test',
    fetchImpl: mockFetchThrows(),
    logger: SILENT,
  });
  assert.equal(r.reason, 'network');
  assert.equal(sessionStorage.getItem('ck_sso_bridge_fail_count'), null);
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

test('v2.0 治本：連續 5 個 401 仍允許下次嘗試（無永久鎖）', async () => {
  freshSession();
  for (let i = 0; i < 5; i++) {
    sessionStorage.setItem('ck_sso_bridge_last_attempt', '0');  // 解 cooldown
    await attemptSSOBridge({
      apiBaseURL: 'https://x.test',
      fetchImpl: mockFetch(401),
      cooldownMs: 0,
      logger: SILENT,
    });
  }
  // 5 次 401 後仍可嘗試（cooldown=0 + 無 lock）
  sessionStorage.setItem('ck_sso_bridge_last_attempt', '0');
  const r = await attemptSSOBridge({
    apiBaseURL: 'https://x.test',
    fetchImpl: mockFetch(200, { user_info: { email: 'a@b' } }),
    cooldownMs: 0,
    logger: SILENT,
  });
  assert.equal(r.ok, true);
  assert.equal(r.reason, 'success');
});

test('resetSSOBridgeState 清 cooldown + 舊版殘留 key', async () => {
  freshSession();
  // 模擬 v1.x 殘留 key
  sessionStorage.setItem('ck_sso_bridge_attempted', '1');
  sessionStorage.setItem('ck_sso_bridge_fail_count', '5');
  sessionStorage.setItem('ck_sso_bridge_last_attempt', '12345');
  resetSSOBridgeState();
  assert.equal(sessionStorage.getItem('ck_sso_bridge_attempted'), null);
  assert.equal(sessionStorage.getItem('ck_sso_bridge_fail_count'), null);
  assert.equal(sessionStorage.getItem('ck_sso_bridge_last_attempt'), null);
  const s = getSSOBridgeState();
  assert.equal(s.lastAttemptAt, null);
  assert.equal(s.cooldownRemainingMs, 0);
});

test('storagePrefix 隔離 (多 SSO 並存)', async () => {
  freshSession();
  sessionStorage.setItem('ck_sso_bridge_last_attempt', String(Date.now()));  // default 在 cooldown
  // 不同 prefix 不互相影響
  const r = await attemptSSOBridge({
    apiBaseURL: 'https://x.test',
    storagePrefix: 'other_sso',
    fetchImpl: mockFetch(401),
    logger: SILENT,
  });
  assert.equal(r.reason, 'transient');  // 不被 default prefix cooldown 影響
});

test('timeoutMs 觸發 AbortController → network', async () => {
  freshSession();
  const slowFetch = async (_, opts) => {
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

test('onSuccess 未指定 → window.location.replace 觸發', async () => {
  freshSession();
  await attemptSSOBridge({
    apiBaseURL: 'https://x.test',
    fetchImpl: mockFetch(200, { user_info: { email: 'a@b' } }),
    successRedirect: '/dashboard',
    logger: SILENT,
  });
  assert.equal(globalThis.__replaceCalled, true);
});

console.log('All ck-sso-js v2.0 tests passed.');

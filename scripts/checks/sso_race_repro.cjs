// SSO bootstrap-race 真實瀏覽器重現（驗證 2026-06-16 b2b6ae26 修法）
//
// 在真實 Chromium 對「公網已部署的新 bundle」重現 owner 的精確競態：
//   (1) 預載 localStorage.user_info = 舊使用者（模擬重開機後磁碟殘留 → bootstrap 走 validate）
//   (2) 攔截 POST /api/auth/check → 永遠 401（模擬舊 token 失效；validateTokenOnStartup 兩次皆 401）
//   (3) 攔截 POST /api/auth/sso-bridge → 200 + 全新 user_info（模擬 ck_employee SSO 成功）
//   (4) 其餘 /api/** → 200 空物件（避免 interceptor 401 觸發無關 redirect，隔離本 race）
//
// 期望（修法後）：ssoBridge 成功 → status=authenticated → 宣告式 <Navigate> → 穩定落 /dashboard，
//   bootstrap 的遲到 validate 失敗**不得** clobber/clearAuth 把它踢回 /entry。
// PASS = 最終 pathname === '/dashboard'（且不再彈回 entry）。
const path = require('path');
const PW_DIR = 'C:/Users/User1/AppData/Roaming/npm/node_modules/@playwright/mcp/node_modules/playwright';
const fs = require('fs');
const { chromium } = require(PW_DIR);

const CACHE = 'C:/Users/User1/AppData/Local/ms-playwright';
const EXE = [
  CACHE + '/chromium_headless_shell-1217/chrome-headless-shell-win64/chrome-headless-shell.exe',
  CACHE + '/chromium_headless_shell-1223/chrome-headless-shell-win64/chrome-headless-shell.exe',
  CACHE + '/chromium_headless_shell-1208/chrome-headless-shell-win64/chrome-headless-shell.exe',
  CACHE + '/chromium-1161/chrome-win/chrome.exe',
].find((p) => fs.existsSync(p));

const ORIGIN = 'https://missive.cksurvey.tw';
const TARGET = ORIGIN + '/entry';
const SHOT = path.resolve('D:/CKProject/CK_Missive/scripts/checks/sso_race_repro.png');

const FRESH_USER = {
  id: 1, username: 'jujuiacc', full_name: 'SSO 新登入', email: 'jujuiacc@gmail.com',
  role: 'superuser', is_admin: true, is_active: true, permissions: '[]',
  auth_provider: 'ck_sso_bridge', created_at: '2026-06-16T00:00:00Z', login_count: 1, email_verified: true,
};
const STALE_USER = { ...FRESH_USER, full_name: '舊殘留(重開機前)', login_count: 0 };

(async () => {
  const out = { bundle: null, pathTransitions: [], ssoBridgeCalls: 0, checkCalls: 0,
    finalPath: null, sessionLogs: [], pass: false };
  const browser = await chromium.launch({ headless: true, executablePath: EXE });
  const context = await browser.newContext();

  // (1) 預載殘留 user_info（在頁面腳本前，模擬重開機後磁碟持久殘留），只種一次
  await context.addInitScript(({ stale }) => {
    try {
      if (!sessionStorage.getItem('__race_seeded')) {
        localStorage.setItem('user_info', JSON.stringify(stale));
        sessionStorage.setItem('__race_seeded', '1');
      }
    } catch (e) { void e; }
  }, { stale: STALE_USER });

  const page = await context.newPage();
  page.on('console', (m) => {
    const t = m.text();
    if (/\[session\]|\[SSO-BRIDGE\]|\[Auth\]|session\]|bootstrap/i.test(t)) out.sessionLogs.push(t.slice(0, 160));
  });

  // (2)(3)(4) 路由攔截 — 單一 handler 內分流（避免 Playwright 後註冊優先導致 catch-all 蓋掉專屬路由）
  out.apiSeen = [];
  await context.route('**/api/**', async (route) => {
    const u = route.request().url();
    out.apiSeen.push(u.replace(ORIGIN, ''));
    if (/\/auth\/check\b/.test(u)) {
      out.checkCalls++;
      return route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'stale token' }) });
    }
    if (/\/auth\/sso-bridge\b/.test(u)) {
      out.ssoBridgeCalls++;
      await new Promise((r) => setTimeout(r, 120)); // ssoBridge 快速回（早於 validate 600ms retry → 先贏）
      return route.fulfill({
        status: 200, contentType: 'application/json',
        headers: { 'set-cookie': 'csrf_token=racetest; Path=/; SameSite=Lax' },
        body: JSON.stringify({ access_token: 'fake-jwt', refresh_token: 'fake-refresh', token_type: 'bearer', user_info: FRESH_USER }),
      });
    }
    if (/\/auth\/me\b/.test(u)) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(FRESH_USER) });
    }
    // 其餘 API 一律 200 空物件，避免無關 401 觸發 interceptor redirect
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });

  // 追蹤 SPA 路徑變化
  let lastPath = null;
  const poll = setInterval(async () => {
    try {
      const p = await page.evaluate(() => location.pathname);
      if (p !== lastPath) { lastPath = p; out.pathTransitions.push({ t: Date.now(), path: p }); }
    } catch (e) { void e; }
  }, 150);

  try {
    await page.goto(TARGET, { waitUntil: 'domcontentloaded', timeout: 30000 });
  } catch (e) {
    clearInterval(poll);
    console.log(JSON.stringify({ ...out, gotoError: String(e) }, null, 2));
    await browser.close();
    process.exit(3);
  }

  out.bundle = await page.evaluate(() =>
    [...document.querySelectorAll('script[src]')].map((s) => s.src).find((s) => /\/main-/.test(s)) || null);

  // 等競態充分 settle（validate retry 600ms + ssoBridge 120ms + 導向/重載），觀察是否穩定
  await page.waitForTimeout(5000);
  out.finalPath = await page.evaluate(() => location.pathname);
  clearInterval(poll);
  try { await page.screenshot({ path: SHOT, fullPage: true }); out.screenshot = SHOT; } catch (e) { void e; }

  // PASS：最終落 dashboard（宣告式導向成功且未被 clobber 彈回 entry）
  out.pass = out.finalPath === '/dashboard' && out.ssoBridgeCalls >= 1;
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
  process.exit(out.pass ? 0 : 1);
})().catch((e) => { console.log('SCRIPT_FATAL', e); process.exit(2); });

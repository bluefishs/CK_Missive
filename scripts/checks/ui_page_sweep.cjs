/**
 * 全站頁面健康掃描（Page Sweep）— 2026-07-31
 *
 * owner：「無法針對前後端與頁面 UI 等管控與檢測」。
 *
 * 既有治理的盲區：
 *   - fitness / audit 只看**原始碼與資料**（路由是否註冊、型別是否 SSOT、cron 有無產出）
 *   - 端點探針只看 **API 回幾號**
 *   → 兩者都不會告訴你「這一頁打開來是壞的」。當日多起缺陷正是
 *     「API 200、程式碼看起來對，但畫面上沒有那個東西 / 一片空白 / 跳錯誤」。
 *
 * 本腳本補這一段：把 router/types.ts 的**靜態路由全部走一遍**，每頁檢查
 *   1. 有沒有被導回登入頁（權限/認證意外壞掉）
 *   2. 畫面是不是空的（root 幾乎沒有內容 → 白畫面）
 *   3. 有沒有出現錯誤字樣（載入失敗 / 發生錯誤 / Something went wrong…）
 *   4. 有沒有致命 console error（過濾已知雜訊）
 *   5. 有沒有跳 alert（前端多處用 alert 擋錯）
 *
 * 與 ui_flow_smoke.cjs 的分工：
 *   - ui_flow_smoke：**深度**——針對 owner 回報過的具體流程，驗特定元素與互動
 *   - ui_page_sweep：**廣度**——全站頁面是否還活著，抓大面積崩壞
 *
 * 用法：
 *   bash scripts/checks/run_ui_smoke.sh --sweep
 *   node scripts/checks/ui_page_sweep.cjs --limit=20     # 只掃前 20 頁（快速）
 *
 * 退出碼：0 全過 / 1 有頁面異常 / 2 未驗完
 */
const fs = require('fs');
const path = require('path');

const PW_DIR = 'C:/Users/User1/AppData/Roaming/npm/node_modules/@playwright/mcp/node_modules/playwright';
const { chromium } = require(PW_DIR);

const CACHE = 'C:/Users/User1/AppData/Local/ms-playwright';
const EXE = [
  CACHE + '/chromium_headless_shell-1223/chrome-headless-shell-win64/chrome-headless-shell.exe',
  CACHE + '/chromium_headless_shell-1217/chrome-headless-shell-win64/chrome-headless-shell.exe',
  CACHE + '/chromium_headless_shell-1208/chrome-headless-shell-win64/chrome-headless-shell.exe',
  CACHE + '/chromium-1161/chrome-win/chrome.exe',
].find((p) => fs.existsSync(p));

const ROOT = path.resolve(__dirname, '..', '..');
const BASE = process.env.SMOKE_BASE || 'https://missive.cksurvey.tw';
const SHOT_DIR = path.resolve(__dirname, 'ui_page_sweep_shots');
const LIMIT = Number((process.argv.find((a) => a.startsWith('--limit=')) || '').split('=')[1] || 0);

// 不掃：認證流程頁（需外部 OAuth）、開發/示範頁、錯誤頁本身
const EXCLUDE = new Set([
  '/', '/entry', '/login', '/register', '/forgot-password', '/reset-password',
  '/verify-email', '/mfa/verify', '/auth/line/callback', '/auth/line/bind-callback',
  '/404', '/api/docs', '/api-mapping', '/unified-form-demo', '/google-auth-diagnostic',
]);

const ERROR_TEXTS = ['載入失敗', '發生錯誤', '系統錯誤', 'Something went wrong', '無法載入'];
const NOISE_RE = [
  /favicon/i, /fedcm/i, /accounts\.google\.com/i, /gsi\/|identity\//i,
  /net::ERR_/i, /status of (401|403|404)/i, /ERR_BLOCKED_BY_CLIENT/i,
  /ResizeObserver/i, /Download the React DevTools/i,
];
const isNoise = (t) => NOISE_RE.some((re) => re.test(t));

function staticRoutes() {
  const src = fs.readFileSync(path.join(ROOT, 'frontend/src/router/types.ts'), 'utf-8');
  const out = [];
  const re = /^\s{2}([A-Z0-9_]+):\s*'(\/[^']*)'/gm;
  let m;
  while ((m = re.exec(src))) {
    const url = m[2];
    if (!url.includes(':') && !EXCLUDE.has(url)) out.push(url);
  }
  return [...new Set(out)];
}

async function main() {
  if (!EXE) { console.error('找不到 Chromium'); process.exit(2); }
  fs.mkdirSync(SHOT_DIR, { recursive: true });

  let routes = staticRoutes();
  if (LIMIT) routes = routes.slice(0, LIMIT);

  const cookieHeader = process.env.COOKIE || '';
  const userInfo = process.env.USER_INFO || '';
  const browser = await chromium.launch({ executablePath: EXE, headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });

  if (userInfo) {
    await context.addInitScript((ui) => {
      try { window.localStorage.setItem('user_info', ui); } catch { /* ignore */ }
    }, userInfo);
  }
  if (cookieHeader) {
    await context.addCookies(cookieHeader.split(';').map((kv) => {
      const i = kv.indexOf('=');
      return {
        name: kv.slice(0, i).trim(), value: kv.slice(i + 1).trim(),
        domain: new URL(BASE).hostname, path: '/',
      };
    }).filter((c) => c.name));
  }

  const bad = [];
  const skipped = [];
  const throttled = [];
  let okCount = 0;

  for (const route of routes) {
    const page = await context.newPage();
    const errors = [];
    const dialogs = [];
    page.on('dialog', async (d) => { dialogs.push(d.message()); await d.dismiss().catch(() => {}); });
    page.on('console', (m) => { if (m.type() === 'error' && !isNoise(m.text())) errors.push(m.text()); });
    page.on('pageerror', (e) => { if (!isNoise(String(e))) errors.push(String(e)); });

    const problems = [];
    try {
      await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(2200);

      if (/\/entry|\/login/.test(page.url())) {
        skipped.push(`${route} → 被導回登入頁`);
        await page.close();
        continue;
      }
      const textLen = (await page.locator('#root').innerText().catch(() => '')).trim().length;
      if (textLen < 40) problems.push(`畫面幾乎空白（內容 ${textLen} 字）`);

      for (const t of ERROR_TEXTS) {
        if (await page.getByText(t, { exact: false }).count()) {
          problems.push(`頁面出現「${t}」`);
          break;
        }
      }
      if (dialogs.length) problems.push(`跳出提示：${dialogs[0].slice(0, 60)}`);
      // 429 是掃描節奏造成的自我限流，不是頁面缺陷 —— 單獨記錄不列 FAIL
      //（初版沒分開 → 4 頁被誤報成壞掉，實際只是掃太快）
      const rateLimited = errors.filter((e) => /status of 429/.test(e));
      const realErrors = errors.filter((e) => !/status of 429/.test(e));
      if (rateLimited.length) throttled.push(route);
      if (realErrors.length) problems.push(`console error：${realErrors[0].slice(0, 90)}`);
    } catch (e) {
      problems.push(`例外：${String(e).slice(0, 90)}`);
    }

    if (problems.length) {
      bad.push({ route, problems });
      const safe = route.replace(/[^a-z0-9]/gi, '_');
      await page.screenshot({ path: path.join(SHOT_DIR, `${safe}.png`) }).catch(() => {});
    } else {
      okCount++;
    }
    await page.close();
    await new Promise((r) => setTimeout(r, 900));  // 節流：避免掃描自己觸發 429
  }

  await browser.close();

  console.log('='.repeat(70));
  console.log(`全站頁面健康掃描 — ${routes.length} 條靜態路由`);
  console.log('='.repeat(70));
  for (const { route, problems } of bad) {
    console.log(`❌ ${route}`);
    problems.forEach((p) => console.log(`      ${p}`));
  }
  if (skipped.length) {
    console.log(`\n⚪ 被導回登入頁 ${skipped.length} 條（未驗）：`);
    skipped.slice(0, 8).forEach((s) => console.log(`      ${s}`));
    if (skipped.length > 8) console.log(`      …另 ${skipped.length - 8} 條`);
  }
  if (throttled.length) {
    console.log(`
🟡 觸發 API 限流 ${throttled.length} 頁（掃描節奏所致，非頁面缺陷）`);
  }
  console.log('-'.repeat(70));
  console.log(`PASS ${okCount} / FAIL ${bad.length} / SKIP ${skipped.length} / 限流 ${throttled.length}`);
  if (bad.length) console.log(`截圖：${SHOT_DIR}`);
  // 契約規則 4：驗證型 job 也必須留下可驗產出 —— 沒有產出就無法區分
  // 「跑了全過」與「根本沒跑」。由既有 producer watchdog 以 file_fresh 監控此檔，
  // 停跑即由每日 cron_outcome_freshness 告警（不另建一套通知）。
  try {
    const RESULT_JSON = path.resolve(__dirname, '..', '..', 'wiki', 'memory',
      'integration-health', 'ui-sweep.json');
    fs.mkdirSync(path.dirname(RESULT_JSON), { recursive: true });
    fs.writeFileSync(RESULT_JSON, JSON.stringify({
      checked_at: new Date().toISOString(),
      base: BASE,
      pass: okCount, fail: bad.length, skip: skipped.length,
      throttled: throttled.length,
      failures: bad.map((b) => ({ route: b.route, problems: b.problems })),
    }, null, 1), 'utf-8');
  } catch (e) { console.error('寫入檢核結果失敗:', String(e)); }

  process.exit(bad.length ? 1 : skipped.length ? 2 : 0);
}

main().catch((e) => { console.error(e); process.exit(2); });

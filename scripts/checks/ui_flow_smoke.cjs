/**
 * UI 流程自我檢核（Browser Self-Audit）— 2026-07-31
 *
 * 立法背景：owner 連日反覆手動點同一批頁面才發現壞掉
 * （核銷點不進去、ezbid 無建案鈕、財務紀錄空、收據看不到、LINE 登入錯誤…）。
 * 「使用端當 QA」是最貴的偵測方式，而且只在 owner 剛好去點的時候才會發現。
 *
 * 本腳本把那些頁面變成可重跑的檢查：跑一次就知道哪一頁壞了。
 *
 * 設計原則：
 *   1. **看畫面上真的有什麼**，不是看 API 回什麼 —— 當日多起缺陷都是
 *      「API 正常但畫面沒有那個東西」（ezbid 無建案鈕、verified 紀錄整列不可點）。
 *   2. **捕捉 alert/confirm 而非被它卡住** —— 前端有數處用 alert 擋錯誤，
 *      未處理會讓自動化整個掛住。
 *   3. **收集 console error** 並分類（雜訊 vs 致命），比照既有 sso_entry_smoke。
 *   4. 認證走「自簽 admin session」（比照 admin_backup_smoke_test.py），
 *      不需要真人登入、也不碰 owner 的 session。
 *
 * 用法：
 *   node scripts/checks/ui_flow_smoke.cjs                # 全部檢查
 *   node scripts/checks/ui_flow_smoke.cjs --only=line    # 只跑某組
 *   node scripts/checks/ui_flow_smoke.cjs --headed       # 看得到瀏覽器（除錯用）
 *   COOKIE="access_token=..." node scripts/checks/ui_flow_smoke.cjs
 *
 * 退出碼：0 全過 / 1 有 FAIL（可掛 cron 或 fitness）
 */
const fs = require('fs');
const path = require('path');

const PW_DIR = 'C:/Users/User1/AppData/Roaming/npm/node_modules/@playwright/mcp/node_modules/playwright';
const { chromium } = require(PW_DIR);

const CACHE = 'C:/Users/User1/AppData/Local/ms-playwright';
const EXE_CANDIDATES = [
  CACHE + '/chromium_headless_shell-1223/chrome-headless-shell-win64/chrome-headless-shell.exe',
  CACHE + '/chromium_headless_shell-1217/chrome-headless-shell-win64/chrome-headless-shell.exe',
  CACHE + '/chromium_headless_shell-1208/chrome-headless-shell-win64/chrome-headless-shell.exe',
  CACHE + '/chromium-1161/chrome-win/chrome.exe',
];
const EXE = EXE_CANDIDATES.find((p) => fs.existsSync(p));

// Phase 1 引擎化（2026-08-01）：零硬編碼，per-repo 差異全在 selfaudit.config.json。
// 跨專案移植時只改設定、不改引擎（引擎漂移由 sync-vendored drift gate 擋）。
const CONFIG_PATH = process.env.SELFAUDIT_CONFIG
  || path.resolve(__dirname, '..', '..', 'selfaudit.config.json');
if (!fs.existsSync(CONFIG_PATH)) {
  console.error(`找不到設定檔：${CONFIG_PATH}
（跨專案移植需先建立 selfaudit.config.json）`);
  process.exit(2);
}
const CONFIG = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
const BASE = process.env.SMOKE_BASE || CONFIG.base_url;
const SHOT_DIR = path.resolve(__dirname, 'ui_flow_smoke_shots');
const HEADED = process.argv.includes('--headed');
const ONLY = (process.argv.find((a) => a.startsWith('--only=')) || '').split('=')[1];

// console error 雜訊過濾（比照 sso_entry_smoke）
const NOISE_RE = [
  /favicon/i, /fedcm/i, /accounts\.google\.com/i, /gsi\/|identity\//i,
  /net::ERR_/i, /status of (401|403|404)/i, /ERR_BLOCKED_BY_CLIENT/i,
];
const isNoise = (t) => NOISE_RE.some((re) => re.test(t));

// ---------------------------------------------------------------------------
// 檢查定義 —— 每一條都對應 owner 曾經手動回報過的問題
// ---------------------------------------------------------------------------
/**
 * Step 直譯器 —— 把 config 的宣告式步驟翻成 playwright 操作。
 *
 * 為何用宣告式而非直接寫 JS：移植到別的 repo 時，該 repo 的檢查清單應該是
 * **資料**而非程式碼，否則每個 repo 都要改引擎 → 回到 copy-式漂移的老路。
 * 支援的 action 刻意保持少而穩（新增前先問是否真的需要）。
 */
async function runSteps(page, ctx, steps) {
  for (const st of steps) {
    switch (st.action) {
      case 'wait':
        await page.waitForTimeout(st.ms || 1000);
        break;
      case 'waitFor':
        await page.locator(st.selector).first()
          .waitFor({ state: 'visible', timeout: st.timeout || 10000 }).catch(() => {});
        break;
      case 'click':
        await page.locator(st.selector).first()
          .click({ timeout: st.timeout || 8000 }).catch(() => {});
        break;
      case 'clickText':
        await page.getByText(st.text, { exact: false }).first()
          .click({ timeout: st.timeout || 8000 }).catch(() => {});
        break;
      case 'assertCount': {
        const n = await page.locator(st.selector).count();
        if (n < (st.min ?? 1)) return { fail: `${st.failMsg}（找到 ${n}）` };
        break;
      }
      case 'assertTextAbsent':
        if (await page.getByText(st.text, { exact: false }).count()) return { fail: st.failMsg };
        break;
      case 'assertTextsPresent': {
        const missing = [];
        for (const t of st.texts) {
          if (!(await page.getByText(t, { exact: false }).count())) missing.push(t);
        }
        if (missing.length) return { fail: `${st.failMsg}：${missing.join('、')}` };
        break;
      }
      case 'assertNoDialog':
        if (ctx.dialogs.length) return { fail: `${st.failMsg}：「${ctx.dialogs.join(' / ')}」` };
        break;
      case 'assertUrlMatches': {
        const u = page.url();
        if (new RegExp(st.pattern, 'i').test(u)) return { ok: st.okMsg || `導向 ${u}` };
        return { fail: `${st.failMsg}：${u}` };
      }
      default:
        return { fail: `未知的 step action：${st.action}` };
    }
  }
  return { ok: 'ok' };
}

const CHECKS = (CONFIG.flows || []).map((f) => ({
  id: f.id,
  name: f.name,
  auth: !!f.auth,
  url: f.url,
  viewport: f.viewport,
  run: (page, ctx) => runSteps(page, ctx, f.steps || []),
}));

// ---------------------------------------------------------------------------
async function main() {
  if (!EXE) {
    console.error('找不到可用的 Chromium 執行檔，請確認 ms-playwright 快取');
    process.exit(2);
  }
  fs.mkdirSync(SHOT_DIR, { recursive: true });

  const cookieHeader = process.env.COOKIE || '';
  const browser = await chromium.launch({ executablePath: EXE, headless: !HEADED });
  const results = [];

  for (const check of CHECKS) {
    if (ONLY && check.id !== ONLY) continue;
    const context = await browser.newContext({
      viewport: check.viewport || { width: 1440, height: 900 },
    });

    if (check.auth && process.env.USER_INFO) {
      // SPA 通常先讀 localStorage 判斷登入狀態，只塞 cookie 會被判 anonymous 而導回入口頁。
      // **但各 repo 的 key 與形狀不同**（2026-08-01 移植 lvrland 時發現）：
      //   CK_Missive        → key 'user_info'，值就是 user 物件
      //   CK_lvrland_Webmap → key 'auth-storage'（zustand persist），
      //                        形狀為 {state:{user,isAuthenticated},version:0}
      // 故也 config 化，引擎不需要知道任何 repo 的儲存慣例。
      const st = CONFIG.auth?.session_storage || { key: 'user_info', shape: 'raw' };
      await context.addInitScript(({ ui, storage }) => {
        try {
          const value = storage.shape === 'zustand-persist'
            ? JSON.stringify({ state: { user: JSON.parse(ui), isAuthenticated: true }, version: 0 })
            : ui;
          window.localStorage.setItem(storage.key, value);
        } catch { /* ignore */ }
      }, { ui: process.env.USER_INFO, storage: st });
    }
    if (check.auth && cookieHeader) {
      const cookies = cookieHeader.split(';').map((kv) => {
        const i = kv.indexOf('=');
        return {
          name: kv.slice(0, i).trim(),
          value: kv.slice(i + 1).trim(),
          domain: new URL(BASE).hostname,
          path: '/',
        };
      }).filter((c) => c.name);
      await context.addCookies(cookies);
    }

    const page = await context.newPage();
    const ctx = { dialogs: [], errors: [] };
    // alert/confirm 必須攔下，否則自動化會整個卡住（前端多處用 alert 擋錯誤）
    page.on('dialog', async (d) => { ctx.dialogs.push(d.message()); await d.dismiss().catch(() => {}); });
    page.on('console', (m) => { if (m.type() === 'error' && !isNoise(m.text())) ctx.errors.push(m.text()); });
    page.on('pageerror', (e) => ctx.errors.push(String(e)));

    let outcome;
    try {
      await page.goto(BASE + check.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(2500);
      // SPA bootstrap 有已知競態（L74 家族）：第一次進來偶爾會被導回入口頁，
      // 重新整理即恢復。自動化重試一次，避免把競態誤報成「頁面壞了」。
      if (check.auth && /\/entry|\/login/.test(page.url())) {
        await page.goto(BASE + check.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(3000);
      }
      if (check.auth && /\/entry|\/login/.test(page.url())) {
        outcome = { skip: cookieHeader ? '重試後仍被導回入口頁（認證未生效）' : '未提供 COOKIE' };
      } else {
        outcome = await check.run(page, ctx);
      }
    } catch (e) {
      outcome = { fail: `例外：${String(e).slice(0, 160)}` };
    }

    if (outcome.fail) {
      await page.screenshot({ path: path.join(SHOT_DIR, `${check.id}.png`), fullPage: false }).catch(() => {});
    }
    results.push({ check, outcome, errors: ctx.errors.slice(0, 3) });
    await context.close();
  }

  await browser.close();

  console.log('='.repeat(66));
  console.log('UI 流程自我檢核 — 對應 owner 曾手動回報的頁面');
  console.log('='.repeat(66));
  let failed = 0;
  for (const { check, outcome, errors } of results) {
    const tag = outcome.fail ? '❌ FAIL' : outcome.skip ? '⚪ SKIP' : '✅ PASS';
    if (outcome.fail) failed++;
    console.log(`${tag}  ${check.name}`);
    console.log(`        ${check.url} — ${outcome.fail || outcome.skip || outcome.ok}`);
    if (errors.length) console.log(`        console error: ${errors.join(' | ').slice(0, 160)}`);
  }
  console.log('-'.repeat(66));
  // SKIP 不得算 GREEN —— 初版就是因為 5 項 SKIP 仍印「GREEN 全部通過」
  // 而差點自我欺騙（本檢核器自己犯了它要抓的那種假綠）。
  const skipped = results.filter((r) => r.outcome.skip).length;
  const passed = results.filter((r) => r.outcome.ok).length;
  if (failed) {
    console.log(`FAIL ${failed} 項 / PASS ${passed} / SKIP ${skipped}（截圖於 ${SHOT_DIR}）`);
  } else if (skipped) {
    console.log(`INCOMPLETE — PASS ${passed} / SKIP ${skipped}（未驗完，勿視為通過）`);
  } else {
    console.log(`GREEN — 全部 ${passed} 項通過`);
  }
  // 有 FAIL → 1；只有 SKIP → 2（未驗完，與通過區分）
  // 契約規則 4：驗證型 job 也必須留下可驗產出 —— 沒有產出就無法區分
  // 「跑了全過」與「根本沒跑」。由既有 producer watchdog 以 file_fresh 監控此檔，
  // 停跑即由每日 cron_outcome_freshness 告警（不另建一套通知）。
  try {
    const RESULT_JSON = path.resolve(__dirname, '..', '..', CONFIG.output.flow_result);
    fs.mkdirSync(path.dirname(RESULT_JSON), { recursive: true });
    fs.writeFileSync(RESULT_JSON, JSON.stringify({
      checked_at: new Date().toISOString(),
      base: BASE,
      pass: passed, fail: failed, skip: skipped,
      failures: results.filter((r) => r.outcome.fail).map((r) => ({ id: r.check.id, name: r.check.name, reason: r.outcome.fail })),
    }, null, 1), 'utf-8');
  } catch (e) { console.error('寫入檢核結果失敗:', String(e)); }

  process.exit(failed ? 1 : skipped ? 2 : 0);
}

main().catch((e) => { console.error(e); process.exit(2); });

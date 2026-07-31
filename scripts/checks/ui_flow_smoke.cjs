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

const BASE = process.env.SMOKE_BASE || 'https://missive.cksurvey.tw';
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
const CHECKS = [
  {
    id: 'line',
    name: 'LINE 登入（owner 回報：一選就出現登入錯誤）',
    auth: false,
    url: '/entry',
    async run(page, ctx) {
      const btn = page.locator('button:has-text("LINE"), [class*="line"]:has-text("LINE")').first();
      // 等按鈕真的出現再判定 —— 初版沒等，SPA 慢一點就誤報「找不到按鈕」
      await btn.waitFor({ state: 'visible', timeout: 15000 }).catch(() => {});
      if (!(await btn.count())) return { fail: '入口頁找不到 LINE 登入按鈕' };
      await btn.click({ timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(2500);
      if (ctx.dialogs.length) {
        return { fail: `前端擋下並跳出提示：「${ctx.dialogs.join(' / ')}」` };
      }
      const url = page.url();
      if (/access\.line\.me|line\.me\/oauth/i.test(url)) return { ok: '已正確導向 LINE 授權頁' };
      if (url.includes('/entry')) return { fail: `點擊後仍停在入口頁（未導向 LINE）：${url}` };
      return { ok: `導向 ${url}` };
    },
  },
  {
    id: 'quotation-expense',
    name: '報價「費用核銷」列可點入（owner 回報兩次）',
    auth: true,
    url: '/erp/quotations/167',
    async run(page) {
      await page.getByText('費用核銷', { exact: false }).first().click({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(2000);
      const view = page.locator('button:has-text("檢視")');
      if (!(await view.count())) return { fail: '費用核銷分頁沒有任何「檢視」按鈕（已核准紀錄將無法點入）' };
      return { ok: `找到 ${await view.count()} 個「檢視」入口` };
    },
  },
  {
    id: 'ezbid-create-case',
    name: 'ezbid 標案有「一鍵建案」（owner 回報：無法建案）',
    auth: true,
    url: '/tender/ezbid/2227632',
    async run(page) {
      await page.waitForTimeout(2500);
      const btn = page.locator('button:has-text("一鍵建案")');
      if (!(await btn.count())) return { fail: 'ezbid 標案頁沒有「一鍵建案」按鈕' };
      const fav = page.locator('button:has-text("收藏")');
      if (!(await fav.count())) return { fail: '有建案鈕但缺收藏（與 PCC 頁設計不一致）' };
      return { ok: '建案 + 收藏 皆在（兩來源設計一致）' };
    },
  },
  {
    id: 'contract-finance',
    name: '承攬案件財務紀錄有資料（owner 回報：無法填報）',
    auth: true,
    url: '/contract-cases/187',
    async run(page) {
      await page.getByText('財務紀錄', { exact: false }).first().click({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(2000);
      const empty = await page.getByText('尚無 ERP 報價紀錄').count();
      if (empty) return { fail: '財務紀錄仍是空的（case_code / 報價未接通）' };
      return { ok: '財務紀錄顯示報價摘要' };
    },
  },
  {
    id: 'receipt-image',
    name: '核銷收據影像載得出來（owner 回報：看不到）',
    auth: true,
    url: '/erp/expenses/6',
    async run(page) {
      await page.waitForTimeout(2500);
      // 影像位於「收據影像」分頁，不切分頁就看不到
      //（初版沒切 → 誤判成「頁面壞了」，實際 API 回 200/178KB）
      await page.getByText('收據影像', { exact: false }).first()
        .click({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(2500);
      const noImg = await page.getByText('無收據影像').count();
      if (noImg) return { fail: '詳情頁顯示「無收據影像」' };
      const img = page.locator('img[src^="blob:"], img[alt*="收據"]');
      if (!(await img.count())) return { fail: '找不到收據影像元素' };
      return { ok: '收據影像已載入' };
    },
  },
  {
    id: 'kunge',
    name: '坤哥意識體服務鏈（對話/心智/進化/圖譜/運維五主軸）',
    auth: true,
    url: '/kunge',
    async run(page) {
      await page.waitForTimeout(3000);
      // ADR-0031：坤哥為唯一意識體入口，5 核心主軸缺一即代表服務鏈斷了一段
      const TABS = ['對話', '心智', '進化', '圖譜', '運維'];
      const missing = [];
      for (const t of TABS) {
        if (!(await page.getByText(t, { exact: false }).count())) missing.push(t);
      }
      if (missing.length) return { fail: `缺少主軸：${missing.join('、')}` };
      // 進化分頁 = 學習閉環（pattern→proposal→crystal）的可見出口
      await page.getByText('進化', { exact: false }).first().click({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(2500);
      const dead = await page.getByText('載入失敗', { exact: false }).count();
      if (dead) return { fail: '進化分頁載入失敗（學習閉環資料鏈斷）' };
      return { ok: '五主軸皆在、進化分頁可載入' };
    },
  },
  {
    id: 'mobile-create',
    name: '行動版核銷建立頁（重點摘要 + 批次連續）',
    auth: true,
    url: '/erp/expenses/create?case_code=CK2026_FN_01_001',
    viewport: { width: 390, height: 844 },
    async run(page) {
      await page.waitForTimeout(2500);
      // 手機版是兩步流程（輸入方式 → 填寫送出），表單在第 2 步；
      // 選「手動」可直接進表單（初版沒進第 2 步 → 誤報找不到按鈕）
      await page.getByText('手動', { exact: false }).first().click({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(1200);
      await page.locator('button:has-text("開始填寫")').first().click({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(2000);
      const cont = page.locator('button:has-text("建立並繼續")');
      if (!(await cont.count())) return { fail: '沒有「建立並繼續掃下一張」（手機批次會被中斷）' };
      return { ok: '批次連續入口存在' };
    },
  },
];

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
      // SPA 的 sessionStore bootstrap 會先讀 localStorage.user_info 才決定要不要
      // 打 /auth/check —— 只塞 cookie 會被判為 anonymous 而導回入口頁。
      await context.addInitScript((ui) => {
        try { window.localStorage.setItem('user_info', ui); } catch { /* ignore */ }
      }, process.env.USER_INFO);
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
    const RESULT_JSON = path.resolve(__dirname, '..', '..', 'wiki', 'memory',
      'integration-health', 'ui-flow.json');
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

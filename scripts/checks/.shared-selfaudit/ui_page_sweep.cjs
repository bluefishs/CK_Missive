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

const boot = require('./_bootstrap.cjs');

// 設定載入 + 結構驗證（缺欄位一律 exit 2「未驗完」，絕不印綠燈）。
// ROOT 以設定檔位置為準，不可由 __dirname 上推 —— vendored 安裝時引擎位於
// <repo>/scripts/checks/.shared-selfaudit/ 比原生位置多一層（2026-08-01 移植 lvrland 時踩到）。
const { CONFIG, ROOT } = boot.loadConfig('sweep', __dirname);
const PW = boot.resolvePlaywright(ROOT);
const chromium = PW && PW.chromium;
const EXE = PW && PW.exe;
const SWEEP = CONFIG.page_sweep || {};
const BASE = process.env.SMOKE_BASE || CONFIG.base_url;
// 截圖寫進 repo 的 docs/health 而非引擎目錄 —— 寫在 vendored 目錄內會讓
// sync-vendored --check 永遠 DRIFT（2026-08-01 pilot 實際踩到）
const SHOT_DIR = path.resolve(ROOT, 'docs', 'health', 'ui_page_sweep_shots');
const LIMIT = Number((process.argv.find((a) => a.startsWith('--limit=')) || '').split('=')[1] || 0);

// 不掃：認證流程頁（需外部 OAuth）、開發/示範頁、錯誤頁本身
const EXCLUDE = new Set(SWEEP.exclude || []);

const ERROR_TEXTS = SWEEP.error_texts || [];

// 已知環境限制：**不是程式缺陷**，但也不能整頁豁免（否則該頁真的壞掉會被蓋掉）。
// 作法：只有當該頁的問題**完全符合**登記的訊號時才降級為「已知限制」；
// 出現任何其他問題仍照常 FAIL。
const KNOWN_LIMITATIONS = (SWEEP.known_limitations || [])
  .map((k) => ({ ...k, match: new RegExp(k.match) }));
const NOISE_RE = [
  /favicon/i, /fedcm/i, /accounts\.google\.com/i, /gsi\/|identity\//i,
  /net::ERR_/i, /status of (401|403|404)/i, /ERR_BLOCKED_BY_CLIENT/i,
  /ResizeObserver/i, /Download the React DevTools/i,
];
const isNoise = (t) => NOISE_RE.some((re) => re.test(t));

function staticRoutes() {
  const src = fs.readFileSync(path.join(ROOT, SWEEP.routes_source), 'utf-8');
  const out = [];
  const re = new RegExp(SWEEP.routes_pattern, 'gm');
  let m;
  while ((m = re.exec(src))) {
    // 路徑可能落在第 1 或第 2 個捕獲群組 —— 各 repo 的 pattern 形狀不同
    // （CK_Missive 的 ROUTES 常數需先捕獲 KEY 再捕獲路徑＝2 群組；
    //   lvrland 的 <Route path="..."> 只有 1 群組）。取第一個以 / 開頭者。
    const url = [m[1], m[2]].find((g) => typeof g === 'string' && g.startsWith('/'));
    if (!url) continue;
    if (!url.includes(':') && !EXCLUDE.has(url)) out.push(url);
  }
  return [...new Set(out)];
}

async function main() {
  if (!EXE) boot.fail(boot.playwrightMissingMessage());
  fs.mkdirSync(SHOT_DIR, { recursive: true });

  let routes = staticRoutes();
  if (routes.length === 0) {
    // 掃到 0 條路由必定是設定錯（routes_source / routes_pattern），不是「全都好」。
    // 2026-08-01 移植 lvrland 時實際發生：pattern 群組位置不同 → 0 條卻印 PASS 0 = 假綠。
    console.error(
      `✗ 從 ${SWEEP.routes_source} 以 pattern ${SWEEP.routes_pattern} 取得 0 條路由 —— ` +
      '請檢查 selfaudit.config.json 的 page_sweep 設定（0 條不等於全部健康）',
    );
    process.exit(2);
  }
  if (LIMIT) routes = routes.slice(0, LIMIT);

  const browser = await chromium.launch({ executablePath: EXE, headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  // 登入態注入走共用函式（初版此處寫死 'user_info'、與深度引擎的 config 化不一致）
  await boot.applyAuth(context, CONFIG, BASE);

  const bad = [];
  const skipped = [];
  const throttled = [];
  const limitations = [];
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
      // 429 有兩種來源訊息：瀏覽器原生 'status of 429'，與 app 自己記的
      // （如 '[ApiClient] API Error: 429'）。初版只認前者 → lvrland 的
      // /admin/user-management 被誤報成頁面壞掉，實際只是掃描把自己限流了。
      const RATE_LIMITED_RE = /status of 429|Error:\s*429|\b429\b/;
      const rateLimited = errors.filter((e) => RATE_LIMITED_RE.test(e));
      const realErrors = errors.filter((e) => !RATE_LIMITED_RE.test(e));
      if (rateLimited.length) throttled.push(route);
      if (realErrors.length) problems.push(`console error：${realErrors[0].slice(0, 90)}`);
    } catch (e) {
      problems.push(`例外：${String(e).slice(0, 90)}`);
    }

    // 已知環境限制降級（每一個問題都被登記的訊號涵蓋，才算已知）
    const known = KNOWN_LIMITATIONS.find((k) => k.route === route);
    if (problems.length && known && problems.every((p) => known.match.test(p))) {
      limitations.push({ route, reason: known.reason });
      okCount++;
      await page.close();
      await new Promise((r) => setTimeout(r, SWEEP.throttle_ms || 900));
      continue;
    }

    if (problems.length) {
      bad.push({ route, problems });
      const safe = route.replace(/[^a-z0-9]/gi, '_');
      await page.screenshot({ path: path.join(SHOT_DIR, `${safe}.png`) }).catch(() => {});
    } else {
      okCount++;
    }
    await page.close();
    await new Promise((r) => setTimeout(r, SWEEP.throttle_ms || 900));  // 節流：避免掃描自己觸發 429
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
  if (limitations.length) {
    console.log(`
🟡 已知環境限制 ${limitations.length} 頁（非程式缺陷）：`);
    limitations.forEach((l) => console.log(`      ${l.route} — ${l.reason}`));
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
    const RESULT_JSON = path.resolve(ROOT, CONFIG.output.sweep_result);
    fs.mkdirSync(path.dirname(RESULT_JSON), { recursive: true });
    fs.writeFileSync(RESULT_JSON, JSON.stringify({
      checked_at: new Date().toISOString(),
      base: BASE,
      pass: okCount, fail: bad.length, skip: skipped.length,
      throttled: throttled.length,
      known_limitations: limitations.map((l) => ({ route: l.route, reason: l.reason })),
      failures: bad.map((b) => ({ route: b.route, problems: b.problems })),
    }, null, 1), 'utf-8');
  } catch (e) { console.error('寫入檢核結果失敗:', String(e)); }

  process.exit(bad.length ? 1 : skipped.length ? 2 : 0);
}

main().catch((e) => { console.error(e); process.exit(2); });

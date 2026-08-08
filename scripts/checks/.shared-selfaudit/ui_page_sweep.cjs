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
// 截圖落點：預設寫進該 repo 的 docs/health；**型態 A（零足跡）必須能外置**，
// 否則「目標專案 0 個檔案」不成立（2026-08-02 查證發現此破口）。
// 以 output.shots_dir 覆寫；絕對路徑時 path.resolve 會忽略 ROOT。
const SHOT_DIR = CONFIG.output && CONFIG.output.shots_dir
  ? path.resolve(ROOT, CONFIG.output.shots_dir)
  : path.resolve(ROOT, 'docs', 'health', 'ui_page_sweep_shots');
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
  // 2026-08-05：支援明確路由清單。
  // 原本一律從程式碼解析（SPA 的 ROUTES 常數 / <Route path>），但**非 SPA 的專案
  // 沒有那種檔案**（如 CK_Website 是靜態 HTML + Cloudflare Pages），
  // 於是引擎在那些 repo 根本用不了。導入其他專案時這是第一道門檻。
  // 明確清單也適合「只想走查關鍵頁」的情境。
  if (Array.isArray(SWEEP.routes) && SWEEP.routes.length) {
    return [...new Set(SWEEP.routes.filter((u) => !EXCLUDE.has(u)))];
  }
  if (!SWEEP.routes_source) {
    console.error('✗ page_sweep 未提供 routes 也未提供 routes_source —— 無法取得要走查的頁面。');
    process.exit(2);
  }
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
  // 有沒有登入態決定「空白頁」該判缺陷還是判未驗（見下方 textLen 判斷）
  const hasAuth = Boolean(process.env.COOKIE || process.env.USER_INFO);

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
      // 等網路靜下來再往下判定（2026-08-04）。
      // 少了這一步，仍在飛的請求會在 `page.close()` 時被中止，閘道記為
      // `Incoming request ended abruptly: context canceled`、瀏覽器 console 則看到 502
      // → **掃描自己製造 FAIL**（實測 /pm/cases/create 被判失敗，同一路由直打連 3 次皆 200；
      // 來源是 QueryProvider 的全域 prefetch 還沒回來就換頁）。
      // 這層現在更要緊：fail>0 已接上 producer 告警，假 FAIL 會變成假告警。
      // 逾時就算了（catch）——網路一直不靜是頁面自己的事，交給下面的檢查判。
      await page.waitForLoadState('networkidle', { timeout: 4000 }).catch(() => {});

      // 2026-08-08：判「被導回登入頁」前**先給它時間把認證解析完**。
      //
      // 前端的登入態解析是非同步的（bootstrap → 驗 cookie → 還原 store），
      // 期間 URL 會短暫停在 /login，networkidle 剛好落在那個窗口就會誤判。
      // 實測 pile：臨時憑證打 /api/auth/check 本機與公網皆 200、截圖也顯示
      // 頁面完整渲染且已登入，卻仍被記成「被導回登入頁」—— 判定太早，不是真的沒登入。
      // 同 v6.44「判 FAIL 前重跑一次」：不穩定的檢核＝每次紅不同條＝假告警。
      if (/\/entry|\/login/.test(page.url())) {
        await page.waitForTimeout(2000);
        await page.waitForLoadState('networkidle', { timeout: 4000 }).catch(() => {});
      }
      // 2026-08-08：判定改為「**離開了目標路由**且落在登入/入口頁」，並把實際 URL 講出來。
      //
      // 原本只測 URL 是否含 /entry|/login —— 於是 `/admin/login-history` 這種
      // **路由名稱本身含 login** 的頁面必然命中，永遠被記成「被導回登入頁」。
      // 而訊息又不說它到底去了哪，於是無從發現這是假陽性。
      // 檢核要說出它看到什麼，否則錯的結論會被當成事實沿用。
      const nowUrl = page.url();
      const nowPath = (() => { try { return new URL(nowUrl).pathname; } catch { return nowUrl; } })();
      const leftRoute = nowPath !== route && !nowPath.startsWith(route);
      if (leftRoute && /^\/(entry|login)(\/|$)/.test(nowPath)) {
        // 一併回報「登入態有沒有真的被種進去」。
        // 沒有這一項時，「被導回登入頁」有兩種完全不同的成因無法區分：
        //   (a) 走查根本沒帶登入態（檢核自己的問題）
        //   (b) 帶了但應用端拒絕（真的權限/認證缺陷）
        // 兩者的處置相反，卻長得一模一樣。
        const seeded = await page.evaluate((keys) => {
          try {
            return keys.filter((k) => window.localStorage.getItem(k)).join(',') || 'none';
          } catch { return 'unreadable'; }
        }, ((Array.isArray(CONFIG.auth && CONFIG.auth.session_storage)
              ? CONFIG.auth.session_storage
              : [CONFIG.auth && CONFIG.auth.session_storage]).filter(Boolean).map((x) => x.key)));
        // console 錯誤從導航前就在收，跳過時卻沒被用到 —— 而「應用端為什麼拒絕」
        // 的答案往往就在那裡（401/403/某支 API 掛掉觸發登出）。一併帶出來。
        // 連 cookie 也一起報：登入態有三個載體（localStorage / cookie / 後端 session），
        // 少報一個就會像這次一樣，卡在「後端說有效、瀏覽器說沒有」而無從判斷。
        const ck = await context.cookies().then(
          (cs) => cs.map((c) => c.name).join(',') || 'none',
        ).catch(() => 'unreadable');
        const why = errors.length ? `｜console: ${errors.slice(0, 2).join(' / ').slice(0, 160)}` : '｜console 無錯誤';
        skipped.push(`${route} → 被導回 ${nowPath}（登入態: ${seeded}｜cookie: ${ck}${why}）`);
        await page.close();
        continue;
      }
      // 內容容器可設定（2026-08-05）。原本寫死 `#root` —— 那是 React SPA 的慣例，
      // **靜態站根本沒有這個元素**，於是每一頁都量到 0 字元、全部judged「空白」。
      // 導入 CK_Website 時首跑 8 頁全 SKIP，就是這個原因。
      // （引擎當時報的是 SKIP 未驗完而不是 FAIL，行為是對的 —— 見下方免登入判斷。）
      const textLen = (await page.locator(SWEEP.content_selector || '#root')
        .innerText().catch(() => '')).trim().length;
      if (textLen < 40) {
        // **未提供登入態時的空白頁不可判為缺陷**：有些 SPA 對未登入的受保護路由
        // 不導向登入頁，而是渲染空殼 → 每一頁都「空白」。
        // 2026-08-02 實測：對 CK_PileMgmt 跑免登入掃描，41 條路由產生
        // **35 個「整頁空白」全數為假陽性**（實際只是沒登入）。
        // 這種輸出比沒有工具更糟——它讓人以為量過了（標準 §3）。
        if (!hasAuth) {
          skipped.push(`${route} → 空白（未提供登入態，無法判定）`);
          await page.close();
          await new Promise((r) => setTimeout(r, SWEEP.throttle_ms || 900));
          continue;
        }
        problems.push(`畫面幾乎空白（內容 ${textLen} 字）`);
      }

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

    // 未提供登入態時，401/403 造成的問題一律判「未驗」而非缺陷。
    // 2026-08-02 實測：對 CK_PileMgmt 免登入掃描，10 個 FAIL 中有 8 個是
    // `/admin/*` 因 403 顯示「載入失敗」——未登入看不到管理頁本來就是對的。
    // 不濾掉的話，型態 A 對「全站需登入」的應用只會產出噪音。
    // **但 404 / 5xx 不在此列**——那不是權限問題（pile 另兩筆正是這類，屬真線索）。
    if (!hasAuth && problems.length) {
      const authSignal = /\b(401|403)\b/;
      const nonAuth = errors.filter((e) => !authSignal.test(e) && !isNoise(e));
      const onlyAuthProblems = problems.every(
        (p) => ERROR_TEXTS.some((t) => p.includes(t)) || authSignal.test(p),
      );
      if (onlyAuthProblems && nonAuth.length === 0 && errors.some((e) => authSignal.test(e))) {
        skipped.push(`${route} → 需登入（401/403），未驗`);
        await page.close();
        await new Promise((r) => setTimeout(r, SWEEP.throttle_ms || 900));
        continue;
      }
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

  // ---- 行動裝置版面觀測（RWD）--------------------------------------------
  // 為何是「觀測」而不是 FAIL：資料密集表格設 scroll={{x}} 橫向捲動是**刻意設計**，
  // 一律判缺陷會產出整片噪音（同 pile 型態 A 的教訓：清單不穩就不該交付）。
  // 這裡只交付一個**經對照驗證過有鑑別力**的量：同一頁在手機寬與桌面寬的表格外溢差。
  //   2026-08-02 驗證：/erp/quotations 手機 708px vs 桌面 0px、/documents 158 vs 0
  //   → 手機獨有，非恆為真。另量過「小於 32px 的觸控目標數」＝手機 157 / 桌面 156
  //   **無鑑別力（按鈕大小不隨視窗變）故不採用**，不放進交付。
  // 不影響 exit code：這是決策輸入，不是告警。
  const MP = SWEEP.mobile_probe || {};
  const mobileRows = [];
  // 2026-08-04：加上 detail_routes。
  // 廣度掃描只吃**靜態**路由（帶 `:id` 的一律排除），行動觀測沿用同一份清單，
  // 於是**所有詳情頁從來沒有在手機寬度下被量過** —— 而詳情頁正是行動裝置最常
  // 用來檢視的地方。實測補上後立刻揭露 /contract-cases/:id 的每個分頁表格
  // 外溢 434~534px（390px 螢幕看不到一半，每列都要左右拉）。
  // 這類路由需要真實 id，無法從 routes 常數推導，故由設定明列。
  const mobileTargets = [...(MP.routes || []), ...(MP.detail_routes || [])];
  if (MP.enabled && mobileTargets.length) {
    const vp = MP.viewport || { width: 390, height: 844 };
    // 刻意不設 isMobile —— Playwright 的行動模擬會 shrink-to-fit：頁面內容較寬時
    // 它把 layout viewport 放大到內容寬度（實測設 390 卻回報 477），
    // 於是「溢出」永遠算成 0＝假綠。用純 viewport 才有可控基準。
    // 2026-08-02 對照：同一頁 isMobile=true → innerWidth 477 / doc 477（看似沒事）；
    //                  純 viewport → innerWidth 390 / doc 476（真的溢出 86px）。
    const mctx = await browser.newContext({ viewport: vp, hasTouch: true });
    await boot.applyAuth(mctx, CONFIG, BASE);
    for (const route of mobileTargets) {
      const page = await mctx.newPage();
      try {
        await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(2200);
        if (/\/entry|\/login/.test(page.url())) { await page.close(); continue; }
        // 註（2026-08-02）：這裡量到的是「進頁約 2.2 秒時」的狀態，**刻意不等到完全穩定**。
        // 實測 /taoyuan/dispatch：2.2 秒時仍渲染桌面版表格（外溢 632px），
        // 到 3 秒才切成手機版清單（表格 0）。兩個數字都對，但意義不同——
        // 使用者在手機上開這頁，前幾秒確實會先看到會橫向溢出的桌面版表格再跳版。
        // 調高等待會讓這個「佈局跳動」從報告裡消失，那是把問題藏起來而不是解決。
        const m = await page.evaluate((vw) => {
          const tables = [...document.querySelectorAll('.ant-table-content, .ant-table-body')]
            .map((t) => t.scrollWidth - t.clientWidth).filter((x) => x > 4);
          return {
            // 用**設定的**視窗寬做基準，不能用 window.innerWidth：
            // 當頁面被寬元素撐開時，行動瀏覽器會放大 layout viewport（實測 /taoyuan/dispatch
            // 設 390 卻回報 985），此時 scrollWidth - innerWidth 會是 0 ＝ 假綠。
            pageOverflow: document.documentElement.scrollWidth - vw,
            // innerWidth 本身就是訊號：它 > 設定值代表整頁被撐開（破版），與表格無關
            layoutViewport: window.innerWidth,
            tableOverflow: tables.length ? Math.max(...tables) : 0,
          };
        }, vp.width);
        mobileRows.push({ route, ...m });
      } catch (e) { mobileRows.push({ route, error: String(e).slice(0, 80) }); }
      await page.close();
      await new Promise((r) => setTimeout(r, SWEEP.throttle_ms || 900));
    }
    await mctx.close();
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
  if (mobileRows.length) {
    const warn = MP.overflow_warn_px || 400;
    const ranked = mobileRows.filter((r) => !r.error)
      .sort((a, b) => b.tableOverflow - a.tableOverflow);
    console.log(`\n📱 行動版面觀測（${(MP.viewport || {}).width || 390}px 寬，觀測不告警）：`);
    const over = ranked.filter((r) => r.tableOverflow >= warn);
    if (over.length) {
      console.log(`   表格橫向外溢 ≥${warn}px 共 ${over.length} 頁（手機需左右滑動才看得完整列）：`);
      over.slice(0, 8).forEach((r) => console.log(`      ${r.route} — 外溢 ${r.tableOverflow}px`));
      if (over.length > 8) console.log(`      …另 ${over.length - 8} 頁`);
    } else if (ranked.length === 0) {
      // 0 頁不是「全部通過」——是根本沒量到。實際發生過一次（登入態失效時
      // 每一頁都被導回登入頁而跳過），當時卻印「皆低於門檻」＝假綠。
      console.log(`   ⚠ 未量到任何頁面（設定了 ${mobileTargets.length} 條）`
        + ' —— 可能登入態失效或全被導回登入頁，**不可視為通過**');
    } else {
      console.log(`   已測 ${ranked.length} 頁，皆低於 ${warn}px 門檻`);
    }
    const vw = (MP.viewport || {}).width || 390;
    const blown = ranked.filter((r) => (r.layoutViewport || vw) > vw + 8);
    if (blown.length) {
      console.log(`   ⚠ 整頁被撐開（layout viewport > ${vw}px，屬版面破格，與表格無關）${blown.length} 頁：`);
      blown.slice(0, 5).forEach((r) => console.log(`      ${r.route} — 撐到 ${r.layoutViewport}px`));
    }
    const pageOver = ranked.filter((r) => r.pageOverflow > 8 && !blown.includes(r));
    if (pageOver.length) {
      console.log(`   ⚠ 整頁橫向溢出（版面破格，非表格內捲）${pageOver.length} 頁：`);
      pageOver.slice(0, 5).forEach((r) => console.log(`      ${r.route} — ${r.pageOverflow}px`));
    }
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
      // 2026-08-04：原本只記數量。實測某次掃描出現 skip=1，退出碼因此固定為 2，
      // 但**查不到是哪一條**——只能重跑一次才知道。跳過屬「未驗完」，
      // 未驗完的清單本身就是要留下來給人看的資訊。
      skipped_routes: skipped,
      throttled: throttled.length,
      known_limitations: limitations.map((l) => ({ route: l.route, reason: l.reason })),
      failures: bad.map((b) => ({ route: b.route, problems: b.problems })),
      // 觀測資料（不影響 pass/fail 判定）
      mobile_probe: mobileRows.length
        ? { viewport: MP.viewport || { width: 390, height: 844 }, rows: mobileRows }
        : null,
    }, null, 1), 'utf-8');
  } catch (e) { console.error('寫入檢核結果失敗:', String(e)); }

  process.exit(bad.length ? 1 : skipped.length ? 2 : 0);
}

main().catch((e) => { console.error(e); process.exit(2); });

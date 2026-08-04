/**
 * 引擎共用啟動邏輯（2026-08-01 抽出）
 *
 * 抽出理由：兩支引擎各自複製了一份「找 playwright／讀 config／算 ROOT」的
 * 開頭三十行 —— 這正是本專案一直在治的「異質同工」，而且已經咬過一次：
 * 廣度引擎修好了「0 條 = 假綠」，深度引擎沒修，因為那段是分開的。
 * 修一處要能同時生效，就不能有兩份。
 *
 * 對外提供：resolvePlaywright() / loadConfig() / assertNonEmpty()
 */
const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------------------------
// Playwright 定位
// ---------------------------------------------------------------------------
/**
 * 找 playwright 模組與 Chromium 執行檔。
 *
 * 為何不寫死路徑：初版寫死 `C:/Users/User1/...`，換一台機器、換一個 Windows
 * 使用者、或跑在 CI 上就 `MODULE_NOT_FOUND` 崩在 require 那一行 —— 使用者看到
 * 的是 node 堆疊，不是「你缺 playwright」。**崩潰不等於清楚**。
 *
 * 順序：環境變數 → 各 repo node_modules → 全域 npm → 已知快取。
 * 全部找不到時回傳 null，由呼叫端印可操作的訊息並 exit 2（不得當成通過）。
 */
function resolvePlaywright(root) {
  const candidates = [];
  if (process.env.SELFAUDIT_PLAYWRIGHT) candidates.push(process.env.SELFAUDIT_PLAYWRIGHT);
  if (root) {
    candidates.push(path.join(root, 'node_modules', 'playwright'));
    candidates.push(path.join(root, 'frontend', 'node_modules', 'playwright'));
  }
  const appData = process.env.APPDATA;
  if (appData) {
    candidates.push(path.join(appData, 'npm/node_modules/@playwright/mcp/node_modules/playwright'));
    candidates.push(path.join(appData, 'npm/node_modules/playwright'));
  }
  if (process.env.HOME) {
    candidates.push(path.join(process.env.HOME, '.npm-global/lib/node_modules/playwright'));
  }

  let mod = null;
  for (const c of candidates) {
    try { mod = require(c); break; } catch { /* 換下一個 */ }
  }
  if (!mod) { try { mod = require('playwright'); } catch { /* 沒有就是沒有 */ } }
  if (!mod) return null;

  // 執行檔：先信任 playwright 自己的解析，失敗才掃已知快取目錄
  const cacheRoots = [
    process.env.PLAYWRIGHT_BROWSERS_PATH,
    process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, 'ms-playwright'),
    process.env.HOME && path.join(process.env.HOME, '.cache/ms-playwright'),
  ].filter(Boolean);

  let exe = null;
  try {
    const p = mod.chromium.executablePath();
    if (p && fs.existsSync(p)) exe = p;
  } catch { /* 未 install 時會拋 */ }

  if (!exe) {
    const leafs = [
      'chrome-headless-shell-win64/chrome-headless-shell.exe',
      'chrome-win/chrome.exe',
      'chrome-linux/chrome',
      'chrome-mac/Chromium.app/Contents/MacOS/Chromium',
    ];
    outer:
    for (const cr of cacheRoots) {
      if (!fs.existsSync(cr)) continue;
      // 版本目錄名會隨 playwright 版本變（chromium_headless_shell-1223…）→ 掃目錄不寫死
      for (const dir of fs.readdirSync(cr).sort().reverse()) {
        for (const leaf of leafs) {
          const cand = path.join(cr, dir, leaf);
          if (fs.existsSync(cand)) { exe = cand; break outer; }
        }
      }
    }
  }
  return exe ? { chromium: mod.chromium, exe } : null;
}

function playwrightMissingMessage() {
  return `找不到 playwright 或 Chromium 執行檔。

頁面層檢核需要 headless 瀏覽器。三種解法擇一：
  1. 該 repo 安裝：npm i -D playwright && npx playwright install chromium
  2. 指定既有安裝：SELFAUDIT_PLAYWRIGHT=/path/to/playwright bash <入口腳本>
  3. 指定瀏覽器快取：PLAYWRIGHT_BROWSERS_PATH=/path/to/ms-playwright

（不會假裝通過 —— 退出碼 2 表示「未驗完」，不是「沒問題」）`;
}

// ---------------------------------------------------------------------------
// 設定載入 + 結構驗證
// ---------------------------------------------------------------------------
/**
 * 讀取並**驗證** selfaudit.config.json。
 *
 * 為何要驗：漏寫或打錯一個欄位，引擎會用預設值繼續跑然後印綠燈
 * —— 移植到新 repo 最可能發生的失敗，就是設定沒寫完卻看到 GREEN。
 * 設定錯必須是「未驗完（exit 2）」，永遠不能是「通過」。
 *
 * @param {'flow'|'sweep'} mode 只驗該模式真正會用到的欄位
 */
function loadConfig(mode, dirnameFallback) {
  // 未指定時往上找 —— 不可寫死上推層數：引擎可能位於
  // <repo>/scripts/checks/（原生）或 <repo>/scripts/checks/.shared-selfaudit/（vendored），
  // 深度不同。2026-08-01 把 CK_Missive 也改成 vendored 消費時，寫死的 '..','..' 立刻指錯。
  const configPath = process.env.SELFAUDIT_CONFIG || findUpward(dirnameFallback);
  if (!fs.existsSync(configPath)) {
    fail(`找不到設定檔：${configPath}
（跨專案移植需先在 repo 根目錄建立 selfaudit.config.json，範本見 shared-modules/selfaudit/README.md）`);
  }

  let cfg;
  try {
    cfg = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
  } catch (e) {
    fail(`設定檔不是合法 JSON：${configPath}\n${e.message}`);
  }

  // ROOT 預設為設定檔所在位置（不可由 __dirname 上推，vendored 安裝多一層目錄）。
  // 但可用 repo_root 覆寫 —— 這讓設定檔**放在目標專案外面**也能跑，
  // 亦即「集中執行、目標專案零足跡」模式（見 README §使用型態）。
  const root = cfg.repo_root
    ? path.resolve(path.dirname(configPath), cfg.repo_root)
    : path.dirname(configPath);
  const problems = [];

  if (!cfg.base_url) problems.push('缺 base_url');
  if (!cfg.output || !cfg.output[mode === 'sweep' ? 'sweep_result' : 'flow_result']) {
    problems.push(`缺 output.${mode === 'sweep' ? 'sweep_result' : 'flow_result'}`);
  }

  if (mode === 'sweep') {
    const sw = cfg.page_sweep;
    if (!sw) problems.push('缺 page_sweep');
    else {
      // 2026-08-05：兩種取得路由的方式擇一即可 —— 明確清單（非 SPA 專案用）
      // 或從程式碼解析（SPA 用）。原本硬性要求後者，導致靜態站根本無法導入。
      const hasExplicit = Array.isArray(sw.routes) && sw.routes.length > 0;
      if (!hasExplicit && !sw.routes_source) {
        problems.push('page_sweep 需提供 routes（明確清單）或 routes_source（從程式碼解析）其一');
      }
      if (sw.routes_source && !fs.existsSync(path.join(root, sw.routes_source))) {
        problems.push(`page_sweep.routes_source 指向不存在的檔案：${sw.routes_source}`);
      }
      if (!hasExplicit && !sw.routes_pattern) problems.push('缺 page_sweep.routes_pattern（路由擷取 regex）');
      else if (sw.routes_pattern) {
        try { new RegExp(sw.routes_pattern); } catch (e) {
          problems.push(`page_sweep.routes_pattern 不是合法 regex：${e.message}`);
        }
      }
    }
  } else if (!Array.isArray(cfg.flows) || cfg.flows.length === 0) {
    // 這一條是實測踩到的假綠：漏寫 flows → 印「GREEN 全部 0 項通過」
    problems.push('缺 flows 或為空陣列（沒有檢查項目不等於健康）');
  }

  if (problems.length) {
    fail(`設定檔不完整：${configPath}\n  - ${problems.join('\n  - ')}\n\n`
      + '（設定不完整一律視為「未驗完」，不會印綠燈）');
  }
  return { CONFIG: cfg, CONFIG_PATH: configPath, ROOT: root };
}

/** 由引擎所在位置往上找 selfaudit.config.json（最多 6 層，避免無限上溯） */
function findUpward(from) {
  let dir = from;
  for (let i = 0; i < 6; i += 1) {
    const cand = path.join(dir, 'selfaudit.config.json');
    if (fs.existsSync(cand)) return cand;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return path.join(from, 'selfaudit.config.json');   // 找不到 → 交由呼叫端報「找不到設定檔」
}

/** 統一的「未驗完」出口：印訊息並 exit 2（0 保留給真正通過） */
function fail(msg) {
  console.error(msg);
  process.exit(2);
}

/**
 * 執行後守衛：檢查項目數為 0 時不得回報通過。
 * 「掃到 0 條路由」「0 個 flow」看起來像全綠，實際是設定或擷取壞了。
 */
function assertNonEmpty(n, what, hint) {
  if (n > 0) return;
  fail(`✗ ${what} 取得 0 項 —— ${hint}\n（0 項不等於全部健康）`);
}

// ---------------------------------------------------------------------------
// 登入態注入
// ---------------------------------------------------------------------------
/**
 * 把 cookie 與前端 session 一起塞進 browser context。
 *
 * SPA 通常先讀 localStorage 判斷登入狀態，只塞 cookie 會被判 anonymous 而導回入口頁。
 * **各 repo 的 key 與形狀不同**（2026-08-01 移植 lvrland 時發現）：
 *   CK_Missive        → key 'user_info'，值就是 user 物件
 *   CK_lvrland_Webmap → key 'auth-storage'（zustand persist），
 *                       形狀 {state:{user,isAuthenticated},version:0}
 * 故 config 化。**兩支引擎共用此函式** —— 初版只有深度引擎讀 config、
 * 廣度引擎寫死 'user_info'，是同一件事做兩遍的典型（異質同工）。
 */
async function applyAuth(context, cfg, base) {
  const cookieHeader = process.env.COOKIE || '';
  const userInfo = process.env.USER_INFO || '';

  if (userInfo) {
    const st = (cfg.auth && cfg.auth.session_storage) || { key: 'user_info', shape: 'raw' };
    await context.addInitScript(({ ui, storage }) => {
      try {
        const value = storage.shape === 'zustand-persist'
          ? JSON.stringify({ state: { user: JSON.parse(ui), isAuthenticated: true }, version: 0 })
          : ui;
        window.localStorage.setItem(storage.key, value);
      } catch { /* ignore */ }
    }, { ui: userInfo, storage: st });
  }

  if (cookieHeader) {
    const cookies = cookieHeader.split(';').map((kv) => {
      const i = kv.indexOf('=');
      return {
        name: kv.slice(0, i).trim(),
        value: kv.slice(i + 1).trim(),
        domain: new URL(base).hostname,
        path: '/',
      };
    }).filter((c) => c.name);
    if (cookies.length) await context.addCookies(cookies);
  }
}

module.exports = {
  resolvePlaywright, playwrightMissingMessage, loadConfig, assertNonEmpty, fail, applyAuth,
};

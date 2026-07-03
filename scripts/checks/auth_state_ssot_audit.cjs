#!/usr/bin/env node
/**
 * auth_state_ssot_audit.cjs — 前端「登入狀態 SSOT」結構性護欄（fitness step 64）
 *
 * 為何存在（2026-06-16，SSO 第 N 次修後立法）：
 *   SSO「停在 entry / 閃訪客跳回」反覆復發的根因＝**前端無單一權威登入狀態**：
 *   is-authenticated 散在 localStorage.user_info / authService.isAuthenticated() / cookie，
 *   且多個元件各自推導「我登入了嗎」+ 各自 redirect → 時機一錯即 race（L41/L48/L66/L68/L69
 *   + 6/15 stuck-at-entry + 6/16 bootstrap 競態 clearAuth）。每次只補一處故持續開新洞。
 *   2026-06-15 SSO 治本已集中到 sessionStore（唯一 is-authenticated 真相）+ SessionGate +
 *   useAuthGuard。本 audit 防「新元件又自行推導 auth + 自行 redirect」破壞該 SSOT。
 *
 * 偵測反模式（同一非基礎設施檔同時出現）：
 *   (A) 推導登入：authService.isAuthenticated() 或直接讀 localStorage user_info 做 gate
 *   (B) 自行導向認證頁：location.replace(...) 或 navigate(ROUTES.LOGIN/ENTRY/DASHBOARD)
 *                      或 <Navigate to={ROUTES.LOGIN/ENTRY/DASHBOARD ...}/>
 *   → 元件應改讀 useSessionStore / useAuthGuard，由其權威狀態決定，勿自行推導+導向。
 *
 * 合法（allowlist）＝ auth 基礎設施本身：sessionStore / SessionGate / useAuthGuard /
 *   useIdleTimeout / EntryPage / authService / api interceptors / router 守衛 / config.env。
 *
 * baseline（2026-06-16 修後）：0 violation。新增任一 → RED（--strict exit 1）。
 *
 * 對齊 lesson「防護腳本存在 ≠ 生效」：本檔須掛 run_fitness.sh（step 64）才算啟用。
 */
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const SRC = path.join(ROOT, 'frontend', 'src');
const STRICT = process.argv.includes('--strict');

// auth 基礎設施 — 唯一被允許「推導登入 + 導向認證頁」之處（相對 frontend/src，POSIX 斜線）
const ALLOWLIST = [
  'store/sessionStore.ts',
  'components/common/SessionGate.tsx',
  'hooks/utility/useAuthGuard.ts',
  'hooks/utility/useIdleTimeout.ts',
  'pages/EntryPage.tsx',
  'services/authService.ts',
  'api/interceptors.ts',
  'config/env.ts',
];
// router 目錄整體為守衛基礎設施（ProtectedRoute / AppRouter / hooks）
const ALLOW_DIR_PREFIX = ['router/'];

const AUTH_DERIVE = [
  /authService\.isAuthenticated\s*\(/,
  /\.isAuthenticated\s*\(\)/,
  /localStorage\.getItem\(\s*['"]user_info['"]\s*\)/,
];
const REDIRECT_TO_AUTH = [
  /location\.replace\s*\(/,
  /navigate\(\s*ROUTES\.(LOGIN|ENTRY|DASHBOARD)\b/,
  /<Navigate\b[^>]*\bto=\{?\s*ROUTES\.(LOGIN|ENTRY|DASHBOARD)\b/,
];

// ── Rule C/D（2026-07-03 擴充，SSO 反覆回歸元覆盤）──
//   step 64 原本 allowlist 完全信任 auth 基礎設施（interceptors/authService），但 07-03 兩個
//   反覆回歸 bug 正好都在這些檔內部（2 個 axios 實例的 401 handler + 2 條 sso-bridge 路徑）。
//   → 不再無條件信任基礎設施內部，直掃兩類破口。
//   詳見 docs/architecture/SSO_RECURRING_REGRESSION_RETROSPECTIVE.md（不變式 I2/I3）。

// Rule C（I2）：401 情境下的破壞性動作
const HAS_401 = /(status\s*===?\s*401|\.status\s*===\s*401|response\?\.status\s*===\s*401)/;
const DESTRUCTIVE_401 = [
  /clearAuth\s*\(/,
  /removeItem\(\s*['"]user_info['"]/,
  /location\.href\s*=\s*['"]\/login/,
  /location\.replace\s*\(\s*['"]\/login/,
];
// 破壞性動作合法前提：同檔引用「權威 session 狀態守衛」
const SESSION_GUARD_REF = [
  /getSessionStatus/,
  /useSessionStore/,
  /(status)\s*(===|!==)\s*['"](anonymous|authenticated|resolving)['"]/,
];

// Rule D（I3）：SSO bridge「POST 後整頁 reload」的路徑必須持久化 user_info
//   只鎖真正危險樣態＝post bridge + location.replace/reload/href（會整頁重載）但沒寫 user_info
//   （＝修法前 attemptSSOBridge 破口）。純端點常數定義檔（無 post/無 reload）不觸發。
const REFS_SSO_BRIDGE = /(SSO_BRIDGE|auth\/sso-bridge|ssoBridge\s*\()/;
const POSTS = /\.post\s*\(/;
const FULL_RELOAD = /(location\.(replace|reload)\s*\(|location\.href\s*=)/;
const PERSISTS_USER_INFO = [
  /setItem\(\s*['"]user_info['"]/,
  /saveAuthData\s*\(/,
  /setUserInfo\s*\(/,
];

function anyMatch(lines, patterns) {
  return lines.some((ln) => patterns.some((p) => p.test(ln)));
}

function walk(dir, out) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) {
      if (ent.name === 'node_modules' || ent.name === '__tests__') continue;
      walk(full, out);
    } else if (/\.(ts|tsx)$/.test(ent.name) && !/\.(test|spec)\.(ts|tsx)$/.test(ent.name)) {
      out.push(full);
    }
  }
  return out;
}

function rel(full) {
  return path.relative(SRC, full).split(path.sep).join('/');
}

function isAllowed(r) {
  return ALLOWLIST.includes(r) || ALLOW_DIR_PREFIX.some((p) => r.startsWith(p));
}

function firstMatchLine(lines, patterns) {
  for (let i = 0; i < lines.length; i++) {
    for (const p of patterns) {
      if (p.test(lines[i])) return { n: i + 1, text: lines[i].trim().slice(0, 100) };
    }
  }
  return null;
}

function main() {
  if (!fs.existsSync(SRC)) {
    console.log('[auth-ssot] frontend/src 不存在，跳過');
    process.exit(0);
  }
  const files = walk(SRC, []);
  const violations = [];       // Rule A+B（元件自行推導+導向）
  const infraViolations = [];  // Rule C+D（基礎設施內部破口）

  for (const full of files) {
    const r = rel(full);
    const lines = fs.readFileSync(full, 'utf8').split(/\r?\n/);

    // Rule A+B：僅對非基礎設施元件
    if (!isAllowed(r)) {
      const derive = firstMatchLine(lines, AUTH_DERIVE);
      const redirect = firstMatchLine(lines, REDIRECT_TO_AUTH);
      if (derive && redirect) violations.push({ file: r, derive, redirect });
    }

    // Rule C（I2）：任何檔在 401 情境做破壞性清除/導向，同檔必須引用 session 狀態守衛
    if (HAS_401.test(lines.join('\n'))) {
      const destructive = firstMatchLine(lines, DESTRUCTIVE_401);
      if (destructive && !anyMatch(lines, SESSION_GUARD_REF)) {
        infraViolations.push({
          file: r, rule: 'C', line: destructive,
          why: '401 破壞性清除/導向但無權威狀態守衛（I2）— 瞬態 race 會清掉剛建立的 session',
          fix: '破壞性動作前加 getSessionStatus()===\'anonymous\' 守衛；resolving/authenticated 只 reject。',
        });
      }
    }

    // Rule D（I3）：SSO bridge「POST 後整頁 reload」但未持久化 user_info
    {
      const body = lines.join('\n');
      const isBridgeReloadPath = REFS_SSO_BRIDGE.test(body) && POSTS.test(body) && FULL_RELOAD.test(body);
      if (isBridgeReloadPath && !anyMatch(lines, PERSISTS_USER_INFO)) {
        const ln = firstMatchLine(lines, [FULL_RELOAD]);
        infraViolations.push({
          file: r, rule: 'D', line: ln || { n: 0, text: '(sso-bridge reload)' },
          why: 'SSO bridge POST 後整頁 reload 卻未持久化 user_info（I3）— reload 後 bootstrap 讀 user_info=NULL → anonymous → 停登入頁',
          fix: '200 後 setItem(\'user_info\', res.data.user_info)（+token）再 reload；或呼叫 saveAuthData/setUserInfo。',
        });
      }
    }
  }

  console.log(`[auth-ssot] 掃描 ${files.length} 檔，allowlist ${ALLOWLIST.length + ALLOW_DIR_PREFIX.length} 項`);
  const total = violations.length + infraViolations.length;
  if (total === 0) {
    console.log('[auth-ssot] GREEN — 無元件自行推導+導向（A/B），基礎設施 401 守衛與 user_info 持久化完整（C/D）');
    process.exit(0);
  }

  if (violations.length) {
    console.log(`[auth-ssot] RED(A/B) — ${violations.length} 檔同時「推導登入」+「自行導向認證頁」，違反 sessionStore SSOT：`);
    for (const v of violations) {
      console.log(`  • ${v.file}`);
      console.log(`      推導登入  L${v.derive.n}: ${v.derive.text}`);
      console.log(`      自行導向  L${v.redirect.n}: ${v.redirect.text}`);
    }
    console.log('  修法：改讀 useSessionStore(s=>s.status) 或 useAuthGuard，勿自行 isAuthenticated()+redirect。');
  }
  if (infraViolations.length) {
    console.log(`[auth-ssot] RED(C/D) — ${infraViolations.length} 處 auth 基礎設施內部破口（SSO 反覆回歸元覆盤）：`);
    for (const v of infraViolations) {
      console.log(`  • [Rule ${v.rule}] ${v.file} L${v.line.n}: ${v.line.text}`);
      console.log(`      ${v.why}`);
      console.log(`      修法：${v.fix}`);
    }
    console.log('  參見 docs/architecture/SSO_RECURRING_REGRESSION_RETROSPECTIVE.md（不變式 I2/I3）。');
  }
  process.exit(STRICT ? 1 : 0);
}

main();

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
  const violations = [];

  for (const full of files) {
    const r = rel(full);
    if (isAllowed(r)) continue;
    const lines = fs.readFileSync(full, 'utf8').split(/\r?\n/);
    const derive = firstMatchLine(lines, AUTH_DERIVE);
    const redirect = firstMatchLine(lines, REDIRECT_TO_AUTH);
    if (derive && redirect) {
      violations.push({ file: r, derive, redirect });
    }
  }

  console.log(`[auth-ssot] 掃描 ${files.length} 檔，allowlist ${ALLOWLIST.length + ALLOW_DIR_PREFIX.length} 項`);
  if (violations.length === 0) {
    console.log('[auth-ssot] GREEN — 無元件自行推導登入 + 自行導向認證頁（SSOT 完整）');
    process.exit(0);
  }

  console.log(`[auth-ssot] RED — ${violations.length} 檔同時「推導登入」+「自行導向認證頁」，違反 sessionStore SSOT：`);
  for (const v of violations) {
    console.log(`  • ${v.file}`);
    console.log(`      推導登入  L${v.derive.n}: ${v.derive.text}`);
    console.log(`      自行導向  L${v.redirect.n}: ${v.redirect.text}`);
  }
  console.log('  修法：改讀 useSessionStore(s=>s.status) 或 useAuthGuard，勿自行 isAuthenticated()+redirect。');
  process.exit(STRICT ? 1 : 0);
}

main();

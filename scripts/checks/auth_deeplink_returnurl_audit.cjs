#!/usr/bin/env node
/**
 * auth_deeplink_returnurl_audit.cjs — 「登入後回跳」深連結護欄（fitness step 75）
 *
 * 為何存在（2026-07-29 立法）：
 *   owner 用手機掃案件核銷 QR（`/erp/expenses/create?case_code=CK2026_PM_01_005`）
 *   無法進入該案核銷。核銷鏈路本身完整（QR 產生、頁面讀參數、相機直拍皆在），
 *   斷點是 **EntryPage 登入/SSO 成功後 5 處寫死 `navigate(ROUTES.DASHBOARD)`**
 *   → `?returnUrl=` 被丟棄 → 所有「深連結 + 需登入」情境（QR / Email / LINE 分享）
 *   在公網一律失效。
 *
 *   屬 L30 家族「產生端正確、消費端丟棄」的半接通：ProtectedRoute / useAuthGuard /
 *   withAuth 三處都正確存了 returnUrl，卻沒有人消費。
 *
 * 偵測反模式：**認證入口頁**（登入/入口/回呼）內出現「寫死的登入後導向常數」
 *   —— 即 navigate(ROUTES.DASHBOARD) / <Navigate to={ROUTES.DASHBOARD}>
 *   而該檔又未使用 resolveReturnUrl / returnUrl。
 *   → 應改用 `resolveReturnUrl(searchParams, ROUTES.DASHBOARD)`（utils/returnUrl.ts SSOT）。
 *
 * baseline（2026-07-29 修後）：0 violation。新增任一 → RED（--strict exit 1）。
 *
 * 對齊 lesson「防護腳本存在 ≠ 生效」：本檔須掛 run_fitness.sh（step 75）才算啟用。
 */
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const SRC = path.join(ROOT, 'frontend', 'src');
const STRICT = process.argv.includes('--strict');

/**
 * 認證入口頁 = 使用者「登入完成後會離開」的那些頁面。
 * 只有這些頁面決定「登入後去哪裡」，因此只需守這一小組（避免 L58 範本污染式全域掃描）。
 */
const ENTRY_FILES = [
  'pages/EntryPage.tsx',
  'pages/LoginPage.tsx',
  'pages/LineCallbackPage.tsx',
  'pages/MFAVerifyPage.tsx',
];

// 寫死的「登入後目的地」常數（這些是 returnUrl 該覆寫的預設值，不該直接 navigate）
const HARDCODED_TARGET = /(?:navigate\(\s*ROUTES\.DASHBOARD|<Navigate\s+to=\{\s*ROUTES\.DASHBOARD)/;
// 有正確消費 returnUrl 的訊號
const HONORS_RETURN_URL = /resolveReturnUrl|returnUrl/;

function main() {
  const violations = [];
  const checked = [];

  for (const rel of ENTRY_FILES) {
    const abs = path.join(SRC, rel);
    if (!fs.existsSync(abs)) continue; // 檔案改名/移除不視為違規（graceful）
    const text = fs.readFileSync(abs, 'utf8');
    checked.push(rel);

    if (HARDCODED_TARGET.test(text) && !HONORS_RETURN_URL.test(text)) {
      const lines = text.split('\n');
      const hits = lines
        .map((l, i) => (HARDCODED_TARGET.test(l) ? i + 1 : 0))
        .filter(Boolean);
      violations.push({ file: rel, lines: hits });
    }
  }

  console.log('=== 登入後回跳（returnUrl）深連結護欄 ===');
  console.log(`檢查認證入口頁: ${checked.length} 個 (${checked.join(', ')})`);

  if (violations.length === 0) {
    console.log('✅ GREEN — 所有認證入口頁都尊重 returnUrl（深連結可用）');
    return 0;
  }

  console.log(`🔴 RED — ${violations.length} 個入口頁寫死登入後導向、未消費 returnUrl:`);
  for (const v of violations) {
    console.log(`  - ${v.file} (行 ${v.lines.join(', ')})`);
  }
  console.log('');
  console.log('修法：改用 utils/returnUrl.ts 的 resolveReturnUrl(searchParams, ROUTES.DASHBOARD)，');
  console.log('      勿直接 navigate(ROUTES.DASHBOARD)（會丟棄 QR/Email/LINE 深連結目的地）。');
  return STRICT ? 1 : 0;
}

process.exit(main());

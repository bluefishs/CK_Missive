#!/usr/bin/env node
/**
 * 文檔同步檢查 — 偵測 CLAUDE.md / CHANGELOG / skills-inventory / skills 目錄落差
 *
 * 檢查項目：
 *   (a) CLAUDE.md 宣告版本 == .claude/CHANGELOG.md 最新版本
 *   (b) ls .claude/skills/*.md ⊆ skills-inventory.md 表格條目
 *   (c) CHANGELOG 最新版本日期距今 ≤ 14 天（超過警告）
 *   (d) CLAUDE.md 「最後更新」日期距今 ≤ 14 天
 *
 * Exit code:
 *   0 = 通過（可有 warning）
 *   1 = 有 error（文檔落差）
 *
 * 使用方式：
 *   node scripts/checks/doc-sync-check.cjs
 *   node scripts/checks/doc-sync-check.cjs --warn-only  # 降級為警告
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '../..');
const CLAUDE_MD = path.join(ROOT, 'CLAUDE.md');
const CHANGELOG = path.join(ROOT, '.claude/CHANGELOG.md');
const SKILLS_DIR = path.join(ROOT, '.claude/skills');
const INVENTORY = path.join(ROOT, '.claude/rules/skills-inventory.md');

const WARN_ONLY = process.argv.includes('--warn-only');
const STALE_DAYS = 14;

const errors = [];
const warnings = [];
const ok = [];

function read(p) {
  try { return fs.readFileSync(p, 'utf8'); } catch { return null; }
}

function daysBetween(dateStr) {
  const d = new Date(dateStr);
  if (isNaN(d)) return null;
  return Math.floor((Date.now() - d.getTime()) / 86400000);
}

// (a) CLAUDE.md 版本
const claudeMd = read(CLAUDE_MD) || '';
const claudeVer = (claudeMd.match(/\*\*版本\*\*:\s*v?(\d+\.\d+\.\d+)/) || [])[1];
const claudeDate = (claudeMd.match(/\*\*最後更新\*\*:\s*(\d{4}-\d{2}-\d{2})/) || [])[1];

const changelog = read(CHANGELOG) || '';
const clVer = (changelog.match(/^##\s*\[(\d+\.\d+\.\d+)\]/m) || [])[1];
const clDateMatch = changelog.match(/^##\s*\[\d+\.\d+\.\d+\][^\n]*?(\d{4}-\d{2}-\d{2})[^\n]*$/m);
const clDate = clDateMatch ? clDateMatch[1] : null;

if (!claudeVer) errors.push('CLAUDE.md 無法解析 **版本** 欄位');
else if (!clVer) errors.push('.claude/CHANGELOG.md 無法解析最新版本');
else if (claudeVer !== clVer) {
  errors.push(`版本不一致：CLAUDE.md=v${claudeVer} ≠ CHANGELOG=v${clVer}`);
} else {
  ok.push(`版本一致：v${claudeVer}`);
}

// (d) CLAUDE.md 最後更新
if (claudeDate) {
  const age = daysBetween(claudeDate);
  if (age !== null && age > STALE_DAYS) {
    warnings.push(`CLAUDE.md 最後更新 ${claudeDate}（${age} 天前，超過 ${STALE_DAYS} 天）`);
  } else ok.push(`CLAUDE.md 最後更新 ${claudeDate}（${age} 天前）`);
}

// (c) CHANGELOG 最新版本日期
if (clDate) {
  const age = daysBetween(clDate);
  if (age !== null && age > STALE_DAYS) {
    warnings.push(`CHANGELOG 最新版本日期 ${clDate}（${age} 天前）— 是否漏更新？`);
  }
}

// (b) skills 目錄 ⊆ inventory 表格
const inventory = read(INVENTORY) || '';
const skillFiles = fs.existsSync(SKILLS_DIR)
  ? fs.readdirSync(SKILLS_DIR).filter(f => f.endsWith('.md') && !f.startsWith('_') && f !== 'README.md' && f !== 'SKILLS_INVENTORY.md')
  : [];

const missing = skillFiles.filter(f => !inventory.includes('`' + f + '`'));
if (missing.length) {
  errors.push(`skills-inventory.md 未列出 ${missing.length} 個 skill：\n  - ` + missing.join('\n  - '));
} else {
  ok.push(`skills-inventory 涵蓋全部 ${skillFiles.length} 個 skill`);
}

// (e) architecture.md 提到的後端檔案存在性抽樣
const ARCH = path.join(ROOT, '.claude/rules/architecture.md');
const archContent = read(ARCH) || '';
const archPaths = Array.from(archContent.matchAll(/`(backend\/app\/[^`\s]+\.py)`/g)).map(m => m[1]);
const uniqArch = [...new Set(archPaths)];
const missingArch = uniqArch.filter(rel => !fs.existsSync(path.join(ROOT, rel)));
if (missingArch.length) {
  warnings.push(`architecture.md 提及 ${missingArch.length} 個不存在的後端檔案（抽樣前 5）：\n  - ` + missingArch.slice(0, 5).join('\n  - '));
} else if (uniqArch.length) {
  ok.push(`architecture.md 引用的 ${uniqArch.length} 個後端檔案皆存在`);
}

// 報告
const RED = '\x1b[31m', YEL = '\x1b[33m', GRN = '\x1b[32m', RST = '\x1b[0m';
console.log('=== 文檔同步檢查 ===');
ok.forEach(m => console.log(`${GRN}✓${RST} ${m}`));
warnings.forEach(m => console.log(`${YEL}⚠${RST} ${m}`));
errors.forEach(m => console.log(`${RED}✗${RST} ${m}`));
console.log(`\n總計：${ok.length} ok, ${warnings.length} warning, ${errors.length} error`);

if (errors.length && !WARN_ONLY) process.exit(1);
process.exit(0);

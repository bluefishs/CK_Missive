#!/usr/bin/env node
/**
 * Wiki Orphan 分類器
 *
 * 目的：把 Phase 4 lint 產出的 orphan 頁面按「處置策略」分類，
 * 讓人工批次處理，而不是逐一決定。
 *
 * 分類規則：
 *   A. auto-archive  — 明顯過時（檔名含舊日期或 deprecated）
 *   B. auto-link     — 能從 KG 找到對應實體 → 可由 compiler 自動補反向連結
 *   C. auto-merge    — 存在同名/近似名 wiki page（可能拼寫不同）
 *   D. manual-review — 剩餘，需人工判斷
 *
 * 使用：
 *   node scripts/checks/wiki-orphan-classify.cjs [--wiki wiki] [--json]
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '../..');
const WIKI_DIR = path.join(ROOT, process.argv.includes('--wiki') ? process.argv[process.argv.indexOf('--wiki') + 1] : 'wiki');
const AS_JSON = process.argv.includes('--json');

function walk(dir) {
  const out = [];
  if (!fs.existsSync(dir)) return out;
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    const stat = fs.statSync(full);
    if (stat.isDirectory()) out.push(...walk(full));
    else if (name.endsWith('.md')) out.push(full);
  }
  return out;
}

function extractFrontmatter(content) {
  const m = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!m) return {};
  const fm = {};
  m[1].split(/\r?\n/).forEach(line => {
    const [k, ...rest] = line.split(':');
    if (k) fm[k.trim()] = rest.join(':').trim();
  });
  return fm;
}

function normalizeTitle(s) {
  return String(s || '').replace(/\s+/g, '').toLowerCase();
}

// 讀取全部 wiki pages
const pages = walk(WIKI_DIR).filter(p => !p.includes(path.sep + 'archive' + path.sep));
const index = new Map();
const refs = new Map(); // slug → [referencing files]

for (const p of pages) {
  const content = fs.readFileSync(p, 'utf8');
  const fm = extractFrontmatter(content);
  const slug = path.basename(p, '.md');
  const title = fm.title || fm.name || slug;
  index.set(slug, { path: p, title, fm, hasKgId: !!fm.kg_entity_id, normalized: normalizeTitle(title) });

  // 掃描 markdown 連結 [text](slug.md) 或 [[slug]]
  const linkPattern = /\[[^\]]*\]\(([^)]+\.md)\)|\[\[([^\]]+)\]\]/g;
  let m;
  while ((m = linkPattern.exec(content))) {
    const target = (m[1] || m[2] || '').replace(/\.md$/, '').split('/').pop();
    if (!target) continue;
    if (!refs.has(target)) refs.set(target, []);
    refs.get(target).push(p);
  }
}

// 偵測 orphans（非 index、非 README、無任何反向連結）
const SKIP_NAMES = new Set(['index', 'README', 'log', 'SCHEMA']);
const orphans = [];
for (const [slug, info] of index) {
  if (SKIP_NAMES.has(slug)) continue;
  if ((refs.get(slug) || []).length === 0) {
    orphans.push({ slug, ...info });
  }
}

// 分類
const buckets = { archive: [], link: [], merge: [], review: [] };
const DEPRECATED_RE = /deprecated|obsolete|舊|過時|2024|2023/i;

for (const o of orphans) {
  if (DEPRECATED_RE.test(o.slug) || DEPRECATED_RE.test(o.title)) {
    buckets.archive.push(o);
    continue;
  }
  if (o.hasKgId) {
    buckets.link.push(o);
    continue;
  }
  // 查是否有同 normalized title 的其他 page（用 path 比對避免 spread 造成的 self-match）
  const dup = [...index.values()].find(p => p.path !== o.path && p.normalized === o.normalized);
  if (dup) {
    buckets.merge.push({ ...o, duplicate_of: path.basename(dup.path) });
    continue;
  }
  buckets.review.push(o);
}

if (AS_JSON) {
  console.log(JSON.stringify({ total_pages: pages.length, orphans: orphans.length, buckets }, null, 2));
  process.exit(0);
}

console.log(`=== Wiki Orphan 分類 ===`);
console.log(`總頁數: ${pages.length}  |  Orphan: ${orphans.length}\n`);

const RED = '\x1b[31m', YEL = '\x1b[33m', GRN = '\x1b[32m', CYN = '\x1b[36m', RST = '\x1b[0m';
const print = (color, label, list, hint) => {
  console.log(`${color}● ${label}${RST} (${list.length}) — ${hint}`);
  list.slice(0, 10).forEach(o => {
    const extra = o.duplicate_of ? ` → ${o.duplicate_of}` : (o.hasKgId ? ` [KG:${o.fm.kg_entity_id}]` : '');
    console.log(`  - ${o.slug}${extra}`);
  });
  if (list.length > 10) console.log(`  ... ${list.length - 10} more`);
  console.log();
};

print(CYN, 'A. auto-archive', buckets.archive, '含 deprecated/舊日期，可直接搬去 wiki/archive/');
print(GRN, 'B. auto-link',  buckets.link,    '有 kg_entity_id，可由 compiler 自動補反向連結');
print(YEL, 'C. auto-merge', buckets.merge,   '疑似重複，需決定保留哪份後合併');
print(RED, 'D. manual-review', buckets.review, '需人工判斷（新頁？移除？改連結？）');

console.log(`建議處置順序: A → B → C → D\n`);
process.exit(0);

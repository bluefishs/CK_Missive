#!/usr/bin/env node
/**
 * 健康快照 → wiki/log.md append
 *
 * 目的：每日固定寫入一行健康指標到 wiki/log.md，
 * 形成可追溯的時序（之後能做趨勢圖）。
 *
 * 指標來源：
 *   1. /health/summary (後端)
 *   2. git log 最近 24h commits 數
 *   3. wiki 頁數 + orphan 數（本機 lint）
 *
 * 使用：
 *   node scripts/health/log-health-snapshot.cjs
 *   node scripts/health/log-health-snapshot.cjs --dry-run
 *
 * 建議排程：每日 06:05（在 wiki_lint 05:30 之後）
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT = path.resolve(__dirname, '../..');
const LOG = path.join(ROOT, 'wiki/log.md');
const DRY = process.argv.includes('--dry-run');
const API = process.env.HEALTH_URL || 'http://localhost:8001/health/summary';

function sh(cmd) {
  try { return execSync(cmd, { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim(); }
  catch { return ''; }
}

async function fetchHealth() {
  try {
    const res = await fetch(API, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) return null;
    return await res.json();
  } catch { return null; }
}

function countWiki() {
  const dir = path.join(ROOT, 'wiki');
  if (!fs.existsSync(dir)) return 0;
  const walk = d => fs.readdirSync(d).reduce((acc, n) => {
    const p = path.join(d, n);
    return acc + (fs.statSync(p).isDirectory() ? walk(p) : (n.endsWith('.md') ? 1 : 0));
  }, 0);
  return walk(dir);
}

async function main() {
  const today = new Date().toISOString().slice(0, 10);
  const commits24h = sh('git log --since="24 hours ago" --oneline').split('\n').filter(Boolean).length;
  const wikiPages = countWiki();
  const health = await fetchHealth();

  const parts = [
    `commits_24h=${commits24h}`,
    `wiki_pages=${wikiPages}`,
  ];
  if (health) {
    if (health.scheduler?.total_jobs) parts.push(`scheduler_jobs=${health.scheduler.total_jobs}`);
    if (health.db?.status) parts.push(`db=${health.db.status}`);
    if (health.redis?.status) parts.push(`redis=${health.redis.status}`);
    if (typeof health.agent_learnings === 'number') parts.push(`learnings=${health.agent_learnings}`);
  } else {
    parts.push('health=unreachable');
  }

  const line = `## [${today}] health-snapshot | ${parts.join(' | ')}\n\n`;

  if (DRY) {
    console.log('[dry-run] 將寫入:\n' + line);
    return;
  }

  fs.appendFileSync(LOG, line);
  console.log(`✓ 已寫入 wiki/log.md：${line.trim()}`);
}

main().catch(e => { console.error(e); process.exit(1); });

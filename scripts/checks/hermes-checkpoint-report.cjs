#!/usr/bin/env node
/**
 * Hermes Migration Checkpoint Report (ADR-0014)
 *
 * 讀取 docs/HERMES_MIGRATION_PLAN.md 解析 Phase 0~4 checkbox 狀態，
 * 結合 git log 的 hermes/acp/tunnel 相關 commit 活動，
 * 輸出每個 phase 的進度 + rollback 窗口狀態。
 *
 * 供 /retro skill 消費（可 --json 讓其他腳本 parse）。
 *
 * 用法:
 *   node scripts/checks/hermes-checkpoint-report.cjs
 *   node scripts/checks/hermes-checkpoint-report.cjs --json
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT = path.resolve(__dirname, '../..');
const PLAN = path.join(ROOT, 'docs/HERMES_MIGRATION_PLAN.md');
const START_DATE = '2026-04-14'; // ADR-0014 啟動日
const AS_JSON = process.argv.includes('--json');

function die(msg) {
  console.error(msg);
  process.exit(1);
}

if (!fs.existsSync(PLAN)) {
  die(`HERMES_MIGRATION_PLAN.md not found at ${PLAN}`);
}

// ---------------------------------------------------------------------------
// 1. 解析 plan.md → phases
// ---------------------------------------------------------------------------
const text = fs.readFileSync(PLAN, 'utf-8');
const lines = text.split(/\r?\n/);

const phases = [];
let current = null;
const PHASE_RE = /^## Phase (\d+)\s+—\s+(.+?)（Day\s+(\d+)[–-](\d+)）/;

for (const line of lines) {
  const m = line.match(PHASE_RE);
  if (m) {
    current = {
      phase: parseInt(m[1], 10),
      title: m[2].trim(),
      dayStart: parseInt(m[3], 10),
      dayEnd: parseInt(m[4], 10),
      checklist: [],
    };
    phases.push(current);
    continue;
  }
  if (!current) continue;
  const cb = line.match(/^- \[([ xX])\]\s+(.+)$/);
  if (cb) {
    current.checklist.push({
      done: cb[1].toLowerCase() === 'x',
      text: cb[2].trim(),
    });
  }
}

// ---------------------------------------------------------------------------
// 2. 日期推算 (Day 0 = 2026-04-14)
// ---------------------------------------------------------------------------
const startMs = new Date(START_DATE + 'T00:00:00').getTime();
const today = new Date();
const currentDay = Math.floor((today.getTime() - startMs) / 86400000);

function addDays(d) {
  const t = new Date(startMs + d * 86400000);
  return t.toISOString().slice(0, 10);
}

// ---------------------------------------------------------------------------
// 3. git activity (hermes/acp/tunnel/manifest keywords)
// ---------------------------------------------------------------------------
let commits = [];
try {
  const out = execSync(
    `git log --since=${START_DATE} --pretty=format:"%h|%ad|%s" --date=short`,
    { cwd: ROOT, encoding: 'utf-8' }
  );
  const keywords = /hermes|acp|tunnel|cloudflare|manifest|shadow|adr-001[456]/i;
  commits = out
    .split(/\r?\n/)
    .filter(Boolean)
    .map((l) => {
      const [hash, date, ...msg] = l.split('|');
      return { hash, date, msg: msg.join('|') };
    })
    .filter((c) => keywords.test(c.msg));
} catch (e) {
  commits = [];
}

// ---------------------------------------------------------------------------
// 4. Phase state 判定
// ---------------------------------------------------------------------------
function phaseState(p) {
  const done = p.checklist.filter((c) => c.done).length;
  const total = p.checklist.length;
  const ratio = total ? done / total : null;
  let status;
  if (currentDay < p.dayStart) status = 'upcoming';
  else if (currentDay > p.dayEnd) status = ratio === 1 ? 'completed' : 'overdue';
  else status = 'active';
  return { done, total, ratio, status };
}

const report = {
  plan_start: START_DATE,
  today: today.toISOString().slice(0, 10),
  current_day: currentDay,
  phases: phases.map((p) => {
    const s = phaseState(p);
    return {
      phase: p.phase,
      title: p.title,
      day_range: `Day ${p.dayStart}–${p.dayEnd} (${addDays(p.dayStart)} → ${addDays(p.dayEnd)})`,
      status: s.status,
      checklist_progress: `${s.done}/${s.total}` + (s.ratio !== null ? ` (${Math.round(s.ratio * 100)}%)` : ''),
      pending: p.checklist.filter((c) => !c.done).map((c) => c.text),
    };
  }),
  commits_since_start: commits.length,
  recent_commits: commits.slice(0, 10),
};

// ---------------------------------------------------------------------------
// 5. Output
// ---------------------------------------------------------------------------
if (AS_JSON) {
  console.log(JSON.stringify(report, null, 2));
  process.exit(0);
}

console.log(`\n=== Hermes Migration Checkpoint (ADR-0014) ===`);
console.log(`Start: ${report.plan_start}  |  Today: ${report.today}  |  Day ${currentDay}`);
console.log('');
for (const p of report.phases) {
  const icon =
    p.status === 'completed' ? '✓'
    : p.status === 'active' ? '▶'
    : p.status === 'overdue' ? '⚠️'
    : '·';
  console.log(`${icon} Phase ${p.phase} — ${p.title}`);
  console.log(`  ${p.day_range}`);
  console.log(`  Status: ${p.status}  Progress: ${p.checklist_progress}`);
  if (p.pending.length && (p.status === 'active' || p.status === 'overdue')) {
    for (const t of p.pending.slice(0, 5)) {
      console.log(`    [ ] ${t}`);
    }
    if (p.pending.length > 5) console.log(`    ... (+${p.pending.length - 5} more)`);
  }
  console.log('');
}
console.log(`Commits (hermes/acp/tunnel/manifest/shadow): ${commits.length}`);
for (const c of report.recent_commits) {
  console.log(`  ${c.hash} ${c.date}  ${c.msg}`);
}
console.log('');

// exit 1 if any phase is overdue (便於 CI / scheduler 偵測)
const hasOverdue = report.phases.some((p) => p.status === 'overdue');
process.exit(hasOverdue ? 1 : 0);

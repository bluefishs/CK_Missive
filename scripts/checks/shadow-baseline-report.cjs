#!/usr/bin/env node
/**
 * Shadow Baseline Report — 讀 backend/logs/shadow_trace.db 產出 Haiku→Missive 鏈路基線。
 *
 * 用途：作為 OpenClaw Haiku → Gemma 4 切換決策的基準資料。
 *
 * 指標：
 *   - 總呼叫數 / 成功率
 *   - 依 channel 分組（line/telegram/openclaw/mcp/web/discord）
 *   - 延遲分佈（p50/p90/p95/max）
 *   - 工具使用前 N
 *   - 錯誤碼分佈
 *   - 每日趨勢
 *
 * 使用：
 *   node scripts/checks/shadow-baseline-report.cjs
 *   node scripts/checks/shadow-baseline-report.cjs --since 2026-04-14
 *   node scripts/checks/shadow-baseline-report.cjs --json
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '../..');
const DB = path.join(ROOT, 'backend/logs/shadow_trace.db');
const AS_JSON = process.argv.includes('--json');
const SINCE = (() => {
  const i = process.argv.indexOf('--since');
  return i >= 0 ? process.argv[i + 1] : null;
})();

if (!fs.existsSync(DB)) {
  console.error(`shadow_trace.db not found at ${DB}`);
  console.error('請先啟用 SHADOW_ENABLED=1 讓後端開始記錄 trace。');
  process.exit(1);
}

// 用 better-sqlite3 若可用，否則 fallback node sqlite3 package
let rows;
try {
  const Database = require('better-sqlite3');
  const db = new Database(DB, { readonly: true });
  const where = SINCE ? `WHERE ts >= '${SINCE}'` : '';
  rows = db.prepare(`SELECT * FROM query_trace ${where} ORDER BY ts`).all();
  db.close();
} catch {
  // fallback: spawn python for sqlite3
  const { execSync } = require('child_process');
  const where = SINCE ? `WHERE ts >= '${SINCE}'` : '';
  const out = execSync(
    `python -c "import sqlite3, json; c=sqlite3.connect(r'${DB}'); c.row_factory=sqlite3.Row; ` +
      `rows=[dict(r) for r in c.execute(\\"SELECT * FROM query_trace ${where} ORDER BY ts\\")]; ` +
      `print(json.dumps(rows, ensure_ascii=True))"`,
    { encoding: 'utf8', maxBuffer: 50 * 1024 * 1024, env: { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' } }
  );
  rows = JSON.parse(out);
}

if (rows.length === 0) {
  console.log('尚無資料。請確認 SHADOW_ENABLED=1 且有流量進入 /ai/agent/query_sync。');
  process.exit(0);
}

function pctl(arr, p) {
  if (!arr.length) return null;
  const s = [...arr].sort((a, b) => a - b);
  const idx = Math.min(s.length - 1, Math.floor((s.length - 1) * p));
  return s[idx];
}
function count(arr) { const m = new Map(); arr.forEach(x => m.set(x, (m.get(x) || 0) + 1)); return m; }

const total = rows.length;
const ok = rows.filter(r => r.success === 1).length;
const latencies = rows.map(r => r.latency_ms || 0).filter(x => x > 0);
const byChannel = new Map();
for (const r of rows) {
  const k = r.channel || 'unknown';
  if (!byChannel.has(k)) byChannel.set(k, []);
  byChannel.get(k).push(r);
}

const allTools = [];
for (const r of rows) {
  try {
    const arr = JSON.parse(r.tools_used || '[]');
    allTools.push(...arr);
  } catch {}
}

const errors = rows.filter(r => r.error_code).map(r => r.error_code);

// 依 provider 分組（A/B 比對）
const byProvider = new Map();
for (const r of rows) {
  const k = r.provider || 'unknown';
  if (!byProvider.has(k)) byProvider.set(k, []);
  byProvider.get(k).push(r);
}

// 每日分佈
const byDate = new Map();
for (const r of rows) {
  const d = (r.ts || '').slice(0, 10);
  if (!byDate.has(d)) byDate.set(d, []);
  byDate.get(d).push(r);
}

const report = {
  span: { from: rows[0].ts, to: rows[rows.length - 1].ts, days: byDate.size },
  total_calls: total,
  success_rate: +(ok / total * 100).toFixed(2),
  latency_ms: {
    p50: pctl(latencies, 0.5),
    p90: pctl(latencies, 0.9),
    p95: pctl(latencies, 0.95),
    max: Math.max(...latencies, 0),
    mean: Math.round(latencies.reduce((a, b) => a + b, 0) / (latencies.length || 1)),
  },
  by_channel: Object.fromEntries(
    [...byChannel.entries()].map(([k, v]) => {
      const lat = v.map(r => r.latency_ms || 0).filter(x => x > 0);
      return [k, {
        count: v.length,
        success_rate: +(v.filter(r => r.success === 1).length / v.length * 100).toFixed(2),
        p50: pctl(lat, 0.5),
        p95: pctl(lat, 0.95),
      }];
    })
  ),
  by_provider: Object.fromEntries(
    [...byProvider.entries()].map(([k, v]) => {
      const lat = v.map(r => r.latency_ms || 0).filter(x => x > 0);
      return [k, {
        count: v.length,
        success_rate: +(v.filter(r => r.success === 1).length / v.length * 100).toFixed(2),
        p50: pctl(lat, 0.5),
        p95: pctl(lat, 0.95),
      }];
    })
  ),
  top_tools: [...count(allTools).entries()].sort((a, b) => b[1] - a[1]).slice(0, 10),
  errors: Object.fromEntries(count(errors)),
  by_date: Object.fromEntries(
    [...byDate.entries()].sort().map(([d, v]) => [d, v.length])
  ),
};

if (AS_JSON) {
  console.log(JSON.stringify(report, null, 2));
  process.exit(0);
}

const { span, latency_ms: L } = report;
console.log(`\n=== Shadow Baseline Report ===`);
console.log(`期間: ${span.from} → ${span.to} (${span.days} 天)`);
console.log(`總呼叫: ${report.total_calls}  |  成功率: ${report.success_rate}%\n`);
console.log(`延遲 (ms): p50=${L.p50}  p90=${L.p90}  p95=${L.p95}  max=${L.max}  mean=${L.mean}\n`);
console.log(`各頻道:`);
for (const [ch, s] of Object.entries(report.by_channel)) {
  console.log(`  ${ch.padEnd(10)} count=${String(s.count).padStart(4)}  ok=${s.success_rate}%  p50=${s.p50}ms  p95=${s.p95}ms`);
}
console.log(`\n依 provider (A/B 比對):`);
for (const [p, s] of Object.entries(report.by_provider)) {
  console.log(`  ${p.padEnd(20)} count=${String(s.count).padStart(4)}  ok=${s.success_rate}%  p50=${s.p50}ms  p95=${s.p95}ms`);
}
console.log(`\n熱門工具 Top 10:`);
report.top_tools.forEach(([t, n], i) => console.log(`  ${i + 1}. ${t.padEnd(30)} ${n}`));
if (Object.keys(report.errors).length) {
  console.log(`\n錯誤碼:`);
  for (const [e, n] of Object.entries(report.errors)) console.log(`  ${e}: ${n}`);
}
console.log(`\n每日分佈:`);
for (const [d, n] of Object.entries(report.by_date)) console.log(`  ${d}: ${n}`);
console.log();

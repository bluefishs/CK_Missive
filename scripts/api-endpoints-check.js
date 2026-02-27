#!/usr/bin/env node
/**
 * API 端點一致性檢測工具 (API Endpoints Check)
 *
 * 比對前端 endpoints.ts 與後端 OpenAPI 的端點定義：
 *   - frontend/src/api/endpoints.ts  — 前端 API 端點常數
 *   - openapi_temp.json (或即時 OpenAPI)  — 後端 API 路徑
 *
 * 使用方式：
 *   node scripts/api-endpoints-check.js              — 使用快照檢查
 *   node scripts/api-endpoints-check.js --live        — 從即時 API 取得 OpenAPI
 *   node scripts/api-endpoints-check.js --strict      — CI 模式，有問題 exit 1
 *   node scripts/api-endpoints-check.js --verbose     — 顯示完整比對矩陣
 *   node scripts/api-endpoints-check.js --update-snapshot — 更新 openapi_temp.json
 *
 * @version 1.0.0
 * @date 2026-02-28
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.join(__dirname, '..');

// ============================================================
// 檔案路徑
// ============================================================
const FILES = {
  endpointsTs: path.join(ROOT, 'frontend/src/api/endpoints.ts'),
  openApiSnapshot: path.join(ROOT, 'openapi_temp.json'),
};

const LIVE_OPENAPI_URL = 'http://localhost:8001/openapi.json';

// ============================================================
// 後端獨有路徑排除規則
// ============================================================
const BACKEND_ONLY_PREFIXES = [
  '/api/debug/',
  '/api/statistics/',
  '/api/secure-site-management/',
  '/api/site-management/',
];

const BACKEND_ONLY_EXACT = new Set([
  '/',
  '/health',
  '/health/detailed',
  '/api/auth/register',
  '/api/auth/google',
  '/api/auth/check',
  '/api/health',
  '/api/health/detailed',
  '/api/health/liveness',
  '/api/health/readiness',
  '/api/health/pool',
  '/api/health/tasks',
  '/api/health/audit',
  '/api/health/metrics',
]);

function isBackendOnly(apiPath) {
  if (BACKEND_ONLY_EXACT.has(apiPath)) return true;
  for (const prefix of BACKEND_ONLY_PREFIXES) {
    if (apiPath.startsWith(prefix)) return true;
  }
  return false;
}

// ============================================================
// 路徑正規化：統一參數名 + 去除查詢字串 + 去除尾部斜線
// ============================================================
function normalizePath(p) {
  let norm = p.split('?')[0];          // 去除查詢字串
  norm = norm.replace(/\/+$/, '');      // 去除尾部斜線
  norm = norm.replace(/\{[^}]+\}/g, '{_}'); // 統一參數名
  return norm || '/';                   // 空字串 fallback 為 /
}

// ============================================================
// 1. 解析 endpoints.ts
// ============================================================
function parseEndpointsTs(content) {
  const entries = [];
  const lines = content.split('\n');

  let currentGroup = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // 偵測 export const XXX_ENDPOINTS = {
    const groupMatch = line.match(/^export\s+const\s+(\w+_ENDPOINTS)\s*=\s*\{/);
    if (groupMatch) {
      currentGroup = groupMatch[1];
      continue;
    }

    // 偵測群組結束 } as const;
    if (currentGroup && /^\}\s*as\s+const/.test(line)) {
      currentGroup = null;
      continue;
    }

    if (!currentGroup) continue;

    // 靜態路徑: KEY: '/path',
    const staticMatch = line.match(/^\s+(\w+):\s*'(\/[^']*)'/);
    if (staticMatch) {
      entries.push({
        group: currentGroup,
        key: staticMatch[1],
        path: staticMatch[2],
        type: 'static',
      });
      continue;
    }

    // Template 函數 (單行): KEY: (params) => `/path/${param}/...`,
    const templateMatch = line.match(/^\s+(\w+):\s*\([^)]*\)\s*=>\s*`(\/[^`]*)`/);
    if (templateMatch) {
      const rawPath = templateMatch[2].replace(/\$\{([^}]+)\}/g, '{$1}');
      entries.push({
        group: currentGroup,
        key: templateMatch[1],
        path: rawPath,
        type: 'template',
      });
      continue;
    }

    // Template 函數 (多行開始): KEY: (params) =>
    const multiLineStart = line.match(/^\s+(\w+):\s*\([^)]*\)\s*=>\s*$/);
    if (multiLineStart) {
      // 下一行應該有 template literal
      const nextLine = lines[i + 1] || '';
      const pathMatch = nextLine.match(/^\s+`(\/[^`]*)`/);
      if (pathMatch) {
        const rawPath = pathMatch[1].replace(/\$\{([^}]+)\}/g, '{$1}');
        entries.push({
          group: multiLineStart[1],
          key: multiLineStart[1],
          path: rawPath,
          type: 'template',
        });
        i++; // skip next line
      }
      continue;
    }
  }

  return entries;
}

// ============================================================
// 2. 解析 OpenAPI JSON
// ============================================================
function parseOpenAPI(data) {
  const paths = Object.keys(data.paths || {});
  return new Set(paths);
}

// ============================================================
// 3. 比對引擎
// ============================================================
function compareEndpoints(feEntries, bePaths) {
  const results = {
    matched: [],
    feOnly: [],
    beOnlyExcluded: [],
    beOnlyUnmapped: [],
  };

  // 建立 BE 正規化路徑 → 原始路徑的映射
  const beNormalized = new Map();
  for (const p of bePaths) {
    beNormalized.set(normalizePath(p), p);
  }

  // 追蹤已匹配的 BE 路徑
  const matchedBePaths = new Set();

  for (const entry of feEntries) {
    const feApiPath = '/api' + entry.path;
    const feNorm = normalizePath(feApiPath);

    if (beNormalized.has(feNorm)) {
      results.matched.push({
        ...entry,
        apiPath: feApiPath,
        bePath: beNormalized.get(feNorm),
      });
      matchedBePaths.add(beNormalized.get(feNorm));
    } else {
      results.feOnly.push({
        ...entry,
        apiPath: feApiPath,
      });
    }
  }

  // 反向：找出 BE 獨有路徑
  for (const bePath of bePaths) {
    if (matchedBePaths.has(bePath)) continue;

    if (isBackendOnly(bePath)) {
      results.beOnlyExcluded.push(bePath);
    } else {
      results.beOnlyUnmapped.push(bePath);
    }
  }

  return results;
}

// ============================================================
// 4. 報告輸出
// ============================================================
function formatReport(results, counts, options) {
  const lines = [];
  const timestamp = new Date().toISOString().slice(0, 19).replace('T', ' ');

  lines.push('='.repeat(65));
  lines.push(` API Endpoints Sync Report             ${timestamp}`);
  lines.push('='.repeat(65));
  lines.push(`  Frontend: ${counts.fe} endpoints (${counts.feStatic} static + ${counts.feTemplate} template)`);
  const sourceLabel = counts.isLive ? 'live' : `snapshot ${counts.snapshotDate || '?'}`;
  lines.push(`  Backend:  ${counts.be} paths (OpenAPI v${counts.apiVersion}, ${sourceLabel})`);
  lines.push(`  Matched:  ${results.matched.length} (after normalization)`);
  lines.push('');

  // FE-only (warnings)
  if (results.feOnly.length > 0) {
    lines.push(`  [WARN] Frontend-only — no backend match (${results.feOnly.length}):`);
    for (const e of results.feOnly) {
      const label = `${e.group}.${e.key}`.replace('_ENDPOINTS', '');
      lines.push(`    - ${label.padEnd(45)} ${e.apiPath}`);
    }
    lines.push('');
  }

  // BE unmapped (info)
  if (results.beOnlyUnmapped.length > 0) {
    lines.push(`  [INFO] Backend-only — no frontend mapping (${results.beOnlyUnmapped.length}):`);
    for (const p of results.beOnlyUnmapped.sort()) {
      lines.push(`    - ${p}`);
    }
    lines.push('');
  }

  // BE excluded
  if (results.beOnlyExcluded.length > 0) {
    // Group by prefix for compact display
    const groups = {};
    for (const p of results.beOnlyExcluded) {
      const segments = p.split('/').filter(Boolean);
      const prefix = segments.length === 0
        ? '/'
        : '/' + segments.slice(0, Math.min(2, segments.length)).join('/') + '/*';
      groups[prefix] = (groups[prefix] || 0) + 1;
    }
    lines.push(`  [SKIP] Backend-internal excluded (${results.beOnlyExcluded.length}):`);
    for (const [prefix, count] of Object.entries(groups).sort()) {
      lines.push(`    - ${prefix.padEnd(45)} (${count} paths)`);
    }
    lines.push('');
  }

  // Verbose: full matrix
  if (options.verbose) {
    lines.push('  Full Match Matrix:');
    lines.push('  ' + '-'.repeat(95));
    lines.push('  ' + 'Frontend Key'.padEnd(45) + 'API Path'.padEnd(48) + 'BE');
    lines.push('  ' + '-'.repeat(95));
    for (const m of results.matched) {
      const label = `${m.group}.${m.key}`.replace('_ENDPOINTS', '');
      lines.push('  ' + label.padEnd(45) + m.apiPath.padEnd(48) + 'Y');
    }
    for (const e of results.feOnly) {
      const label = `${e.group}.${e.key}`.replace('_ENDPOINTS', '');
      lines.push('  ' + label.padEnd(45) + e.apiPath.padEnd(48) + 'N');
    }
    lines.push('  ' + '-'.repeat(95));
    lines.push('');
  }

  // Summary
  lines.push('='.repeat(65));
  lines.push(' Summary');
  lines.push('='.repeat(65));
  lines.push(`  Matched:      ${results.matched.length} endpoints`);
  if (results.feOnly.length > 0) {
    lines.push(`  FE-only:      ${results.feOnly.length} (may be stale or not yet implemented)`);
  }
  lines.push(`  BE-excluded:  ${results.beOnlyExcluded.length} (backend-internal)`);
  if (results.beOnlyUnmapped.length > 0) {
    lines.push(`  BE-unmapped:  ${results.beOnlyUnmapped.length} (backend paths without frontend mapping)`);
  }
  lines.push('='.repeat(65));

  return lines.join('\n');
}

// ============================================================
// 5. 主程式
// ============================================================
async function main() {
  const args = process.argv.slice(2);
  const isStrict = args.includes('--strict');
  const verbose = args.includes('--verbose');
  const useLive = args.includes('--live');
  const updateSnapshot = args.includes('--update-snapshot');

  // --- 讀取前端 endpoints.ts ---
  if (!fs.existsSync(FILES.endpointsTs)) {
    console.error(`File not found: ${FILES.endpointsTs}`);
    process.exit(1);
  }
  const endpointsContent = fs.readFileSync(FILES.endpointsTs, 'utf-8');
  const feEntries = parseEndpointsTs(endpointsContent);

  // --- 取得 OpenAPI 資料 ---
  let openApiData;

  if (useLive || updateSnapshot) {
    try {
      const response = await fetch(LIVE_OPENAPI_URL);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      openApiData = await response.json();

      if (updateSnapshot) {
        fs.writeFileSync(FILES.openApiSnapshot, JSON.stringify(openApiData, null, 2), 'utf-8');
        console.log(`Updated snapshot: ${FILES.openApiSnapshot}`);
      }
    } catch (err) {
      if (useLive) {
        console.error(`Cannot fetch live OpenAPI from ${LIVE_OPENAPI_URL}: ${err.message}`);
        console.error('Hint: Ensure backend is running, or use snapshot mode (without --live)');
        process.exit(1);
      }
      // updateSnapshot 失敗時 fallback 到快照
      console.warn(`Live fetch failed (${err.message}), falling back to snapshot`);
    }
  }

  if (!openApiData) {
    if (!fs.existsSync(FILES.openApiSnapshot)) {
      console.error(`OpenAPI snapshot not found: ${FILES.openApiSnapshot}`);
      console.error('Hint: Run with --update-snapshot while backend is running');
      process.exit(1);
    }
    openApiData = JSON.parse(fs.readFileSync(FILES.openApiSnapshot, 'utf-8'));
  }

  const bePaths = parseOpenAPI(openApiData);

  // --- 統計 ---
  const feStatic = feEntries.filter(e => e.type === 'static').length;
  const feTemplate = feEntries.filter(e => e.type === 'template').length;
  const apiVersion = openApiData.info?.version || 'unknown';
  const snapshotStat = !useLive && fs.existsSync(FILES.openApiSnapshot)
    ? fs.statSync(FILES.openApiSnapshot).mtime.toISOString().slice(0, 10)
    : null;
  const counts = {
    fe: feEntries.length,
    feStatic,
    feTemplate,
    be: bePaths.size,
    apiVersion,
    snapshotDate: snapshotStat,
    isLive: !!useLive,
  };

  // --- 比對 ---
  const results = compareEndpoints(feEntries, bePaths);

  // --- 報告 ---
  const report = formatReport(results, counts, { verbose });
  console.log(report);

  // --- Exit code ---
  if (isStrict && results.feOnly.length > 0) {
    process.exit(1);
  }
}

main();

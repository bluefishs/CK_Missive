#!/usr/bin/env node
/**
 * 路由同步檢測工具 (Route Sync Check)
 *
 * 比對 4 處路由定義的一致性，偵測路由漂移：
 *   1. frontend/src/router/types.ts      — ROUTES 常數
 *   2. frontend/src/router/AppRouter.tsx  — Route 元素
 *   3. backend/app/scripts/init_navigation_data.py — 導覽項目
 *   4. backend/app/core/navigation_validator.py    — 路徑白名單
 *
 * 使用方式：
 *   node scripts/route-sync-check.js            — 快速檢查
 *   node scripts/route-sync-check.js --strict    — CI 模式，有問題 exit 1
 *   node scripts/route-sync-check.js --verbose   — 顯示完整矩陣
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
  typesTs: path.join(ROOT, 'frontend/src/router/types.ts'),
  appRouter: path.join(ROOT, 'frontend/src/router/AppRouter.tsx'),
  initNav: path.join(ROOT, 'backend/app/scripts/init_navigation_data.py'),
  validator: path.join(ROOT, 'backend/app/core/navigation_validator.py'),
};

// ============================================================
// 排除規則：這些路徑不需要在 init_nav / validator 中
// ============================================================
const PARAM_ROUTE_PATTERN = /:/;
const CREATE_ROUTE_PATTERN = /\/(create|new)$/;

const AUTH_ROUTES = new Set([
  '/login', '/register', '/reset-password', '/verify-email',
  '/mfa/verify', '/forgot-password',
]);

const SYSTEM_ONLY_ROUTES = new Set([
  '/', '/entry', '/404',
]);

function isExcludedFromNav(routePath) {
  if (PARAM_ROUTE_PATTERN.test(routePath)) return 'parameterized';
  if (CREATE_ROUTE_PATTERN.test(routePath)) return 'create-page';
  if (AUTH_ROUTES.has(routePath)) return 'auth';
  if (SYSTEM_ONLY_ROUTES.has(routePath)) return 'system';
  return null;
}

// ============================================================
// 1. 解析 types.ts — ROUTES 常數
// ============================================================
function parseTypesTs(content) {
  const routes = {};
  const lines = content.split('\n');

  for (const line of lines) {
    // 匹配: KEY: '/path' 或 KEY: '/path/:param'
    const match = line.match(/^\s+(\w+):\s*'(\/[^']*)'/);
    if (match) {
      routes[match[1]] = match[2];
    }
  }
  return routes;
}

// ============================================================
// 2. 解析 AppRouter.tsx — Route 元素
// ============================================================
function parseAppRouter(content) {
  const paths = new Set();

  // 匹配 path={ROUTES.KEY} — 間接引用
  const routeRefMatches = content.matchAll(/path=\{ROUTES\.(\w+)\}/g);
  for (const m of routeRefMatches) {
    paths.add(m[1]); // 儲存 ROUTES key
  }

  // 匹配 path="/xxx" — 直接字串
  const directMatches = content.matchAll(/path="(\/[^"]*)"/g);
  for (const m of directMatches) {
    paths.add(m[1]); // 儲存路徑本身
  }

  return paths;
}

// ============================================================
// 3. 解析 init_navigation_data.py
// ============================================================
function parseInitNav(content) {
  const paths = new Set();
  const lines = content.split('\n');

  for (const line of lines) {
    // 匹配: "path": "/xxx" 或 'path': '/xxx'
    const match = line.match(/["']path["']\s*:\s*["'](\/[^"']*)["']/);
    if (match) {
      paths.add(match[1]);
    }
  }
  return paths;
}

// ============================================================
// 4. 解析 navigation_validator.py
// ============================================================
function parseValidator(content) {
  const paths = new Set();
  const lines = content.split('\n');
  let inSet = false;

  for (const line of lines) {
    if (line.includes('VALID_NAVIGATION_PATHS')) inSet = true;
    if (inSet && line.includes('}')) { inSet = false; continue; }

    if (inSet) {
      const match = line.match(/^\s+"(\/[^"]*)"/);
      if (match) {
        paths.add(match[1]);
      }
    }
  }
  return paths;
}

// ============================================================
// 5. 比對引擎
// ============================================================
function compareRoutes(routes, appRouterKeys, initNavPaths, validatorPaths) {
  const results = {
    synced: [],
    bugs: [],
    warnings: [],
    info: [],
  };

  const allPaths = Object.values(routes);

  for (const [key, routePath] of Object.entries(routes)) {
    const exclusion = isExcludedFromNav(routePath);

    // 檢查 AppRouter 是否有此 route
    const inAppRouter = appRouterKeys.has(key) || appRouterKeys.has(routePath);

    // 檢查 init_nav 和 validator
    const inInitNav = initNavPaths.has(routePath);
    const inValidator = validatorPaths.has(routePath);

    if (exclusion) {
      // 參數化/認證/系統路徑只需在 types.ts + AppRouter
      if (!inAppRouter) {
        results.warnings.push({
          path: routePath,
          key,
          message: `ROUTES.${key} 在 AppRouter 中無對應 Route`,
        });
      } else {
        results.info.push({
          path: routePath,
          key,
          reason: exclusion,
        });
      }
      continue;
    }

    // 導覽路徑：應在全部 4 處
    if (!inAppRouter) {
      results.bugs.push({
        path: routePath,
        key,
        message: `ROUTES.${key} 在 AppRouter 中無對應 Route`,
        present: { typesTs: true, appRouter: false, initNav: inInitNav, validator: inValidator },
      });
    } else if (!inValidator && inInitNav) {
      // 在 init_nav 中有但 validator 沒有 — 真正的 bug
      results.bugs.push({
        path: routePath,
        key,
        message: `在 init_nav 中存在但 validator 缺失`,
        present: { typesTs: true, appRouter: true, initNav: true, validator: false },
      });
    } else if (!inValidator) {
      // 不在 validator 也不在 init_nav — 可能是尚未加入導覽的頁面
      results.warnings.push({
        path: routePath,
        key,
        message: `不在 validator 白名單中（可能尚未加入導覽）`,
      });
    } else {
      results.synced.push({ path: routePath, key });
    }
  }

  // 反向檢查：validator 中有但 types.ts 沒有的
  for (const vPath of validatorPaths) {
    if (!allPaths.includes(vPath)) {
      results.warnings.push({
        path: vPath,
        key: null,
        message: `在 validator 中但不在 types.ts ROUTES 中`,
      });
    }
  }

  // 反向檢查：init_nav 中有但 types.ts 沒有的
  for (const nPath of initNavPaths) {
    if (!allPaths.includes(nPath)) {
      results.warnings.push({
        path: nPath,
        key: null,
        message: `在 init_nav 中但不在 types.ts ROUTES 中`,
      });
    }
  }

  return results;
}

// ============================================================
// 6. 報告輸出
// ============================================================
function formatReport(results, counts, options) {
  const lines = [];

  lines.push('='.repeat(65));
  lines.push(` Route Sync Report                   ${new Date().toISOString().slice(0, 19).replace('T', ' ')}`);
  lines.push('='.repeat(65));
  lines.push(`  Sources: types.ts(${counts.types}) | AppRouter(${counts.router}) | init_nav(${counts.initNav}) | validator(${counts.validator})`);
  lines.push('');

  // Bugs
  if (results.bugs.length > 0) {
    lines.push(`  [BUG] ${results.bugs.length} issue(s):`);
    for (const b of results.bugs) {
      const present = b.present
        ? ` [types:Y router:${b.present.appRouter ? 'Y' : 'N'} nav:${b.present.initNav ? 'Y' : 'N'} valid:${b.present.validator ? 'Y' : 'N'}]`
        : '';
      lines.push(`    - ${b.path}: ${b.message}${present}`);
    }
    lines.push('');
  }

  // Warnings
  if (results.warnings.length > 0) {
    lines.push(`  [WARN] ${results.warnings.length} warning(s):`);
    for (const w of results.warnings) {
      lines.push(`    - ${w.path}: ${w.message}`);
    }
    lines.push('');
  }

  // Verbose mode: full matrix
  if (options.verbose) {
    lines.push('  Full Route Matrix:');
    lines.push('  ' + '-'.repeat(61));
    lines.push('  ' + 'Path'.padEnd(45) + 'T  R  N  V');
    lines.push('  ' + '-'.repeat(61));
    for (const s of results.synced) {
      lines.push('  ' + s.path.padEnd(45) + 'Y  Y  ?  Y');
    }
    for (const i of results.info) {
      const tag = `(${i.reason})`;
      lines.push('  ' + (i.path + ' ' + tag).padEnd(45) + 'Y  Y  -  -');
    }
    lines.push('  ' + '-'.repeat(61));
    lines.push('');
  }

  // Summary
  lines.push('='.repeat(65));
  lines.push(' Summary');
  lines.push('='.repeat(65));
  lines.push(`  Synced:       ${results.synced.length} navigable paths`);
  lines.push(`  Excluded:     ${results.info.length} (parameterized/auth/system)`);
  if (results.bugs.length > 0) {
    lines.push(`  Bugs:         ${results.bugs.length} (sync required)`);
  }
  if (results.warnings.length > 0) {
    lines.push(`  Warnings:     ${results.warnings.length}`);
  }
  lines.push('='.repeat(65));

  return lines.join('\n');
}

// ============================================================
// 7. 主程式
// ============================================================
function main() {
  const args = process.argv.slice(2);
  const isStrict = args.includes('--strict');
  const verbose = args.includes('--verbose');

  // 讀取 4 個檔案
  for (const [name, filePath] of Object.entries(FILES)) {
    if (!fs.existsSync(filePath)) {
      console.error(`File not found: ${filePath} (${name})`);
      process.exit(1);
    }
  }

  const typesContent = fs.readFileSync(FILES.typesTs, 'utf-8');
  const routerContent = fs.readFileSync(FILES.appRouter, 'utf-8');
  const initNavContent = fs.readFileSync(FILES.initNav, 'utf-8');
  const validatorContent = fs.readFileSync(FILES.validator, 'utf-8');

  // 解析
  const routes = parseTypesTs(typesContent);
  const appRouterKeys = parseAppRouter(routerContent);
  const initNavPaths = parseInitNav(initNavContent);
  const validatorPaths = parseValidator(validatorContent);

  const counts = {
    types: Object.keys(routes).length,
    router: appRouterKeys.size,
    initNav: initNavPaths.size,
    validator: validatorPaths.size,
  };

  // 比對
  const results = compareRoutes(routes, appRouterKeys, initNavPaths, validatorPaths);

  // 報告
  const report = formatReport(results, counts, { verbose });
  console.log(report);

  // Exit code
  if (isStrict && results.bugs.length > 0) {
    process.exit(1);
  }
}

main();

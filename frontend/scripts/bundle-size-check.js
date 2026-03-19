/**
 * Bundle Size Check — 建置產物大小驗證
 *
 * 用途：CI 中驗證 bundle 大小不超過閾值
 * 執行：node scripts/bundle-size-check.js [--build]
 *
 * @version 1.0.0
 */

import { readdirSync, statSync } from 'fs';
import { join, extname } from 'path';
import { execSync } from 'child_process';

const DIST_DIR = join(import.meta.dirname, '..', 'dist');
const ASSETS_DIR = join(DIST_DIR, 'assets');

// 閾值定義 (bytes) — 基準線 2026-03-14 + 15% headroom
const LIMITS = {
  totalRaw: 10.5 * 1024 * 1024,    // 10.5 MB total raw (baseline 8.87 MB)
  totalGzip: 3.5 * 1024 * 1024,    // 3.5 MB total gzip (baseline 2.63 MB)
  singleFileRaw: 1.5 * 1024 * 1024,// 1.5 MB per file (antd-core ~1.3 MB)
  mainJsRaw: 1.5 * 1024 * 1024,    // 1.5 MB main entry JS (baseline 1.2 MB)
};

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function getGzipSize(filePath) {
  try {
    const result = execSync(`gzip -c "${filePath}" | wc -c`, { encoding: 'utf8' });
    return parseInt(result.trim(), 10);
  } catch {
    // Fallback: estimate ~40% compression
    return Math.round(statSync(filePath).size * 0.4);
  }
}

function scanAssets(dir) {
  const files = [];
  try {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const fullPath = join(dir, entry.name);
      if (entry.isDirectory()) {
        files.push(...scanAssets(fullPath));
      } else {
        const ext = extname(entry.name).toLowerCase();
        if (['.js', '.css', '.html'].includes(ext)) {
          const raw = statSync(fullPath).size;
          const gzip = getGzipSize(fullPath);
          files.push({ name: entry.name, path: fullPath, raw, gzip, ext });
        }
      }
    }
  } catch {
    // dir doesn't exist
  }
  return files;
}

function main() {
  const shouldBuild = process.argv.includes('--build');

  if (shouldBuild) {
    console.log('Building...');
    execSync('npm run build', { cwd: join(import.meta.dirname, '..'), stdio: 'inherit' });
  }

  const assets = scanAssets(ASSETS_DIR);

  if (assets.length === 0) {
    console.error('No assets found. Run with --build or build first.');
    process.exit(1);
  }

  const totalRaw = assets.reduce((s, f) => s + f.raw, 0);
  const totalGzip = assets.reduce((s, f) => s + f.gzip, 0);
  const jsFiles = assets.filter(f => f.ext === '.js').sort((a, b) => b.raw - a.raw);
  const cssFiles = assets.filter(f => f.ext === '.css').sort((a, b) => b.raw - a.raw);

  console.log('\n=== Bundle Size Report ===\n');

  console.log('Top JS files:');
  jsFiles.slice(0, 10).forEach(f => {
    const flag = f.raw > LIMITS.singleFileRaw ? ' ⚠️ OVER LIMIT' : '';
    console.log(`  ${f.name.padEnd(45)} ${formatSize(f.raw).padStart(10)} (gzip: ${formatSize(f.gzip).padStart(10)})${flag}`);
  });

  console.log('\nCSS files:');
  cssFiles.forEach(f => {
    console.log(`  ${f.name.padEnd(45)} ${formatSize(f.raw).padStart(10)} (gzip: ${formatSize(f.gzip).padStart(10)})`);
  });

  console.log(`\nTotal: ${formatSize(totalRaw)} raw / ${formatSize(totalGzip)} gzip`);
  console.log(`Files: ${jsFiles.length} JS + ${cssFiles.length} CSS\n`);

  // Check limits
  const failures = [];

  if (totalRaw > LIMITS.totalRaw) {
    failures.push(`Total raw size ${formatSize(totalRaw)} exceeds limit ${formatSize(LIMITS.totalRaw)}`);
  }
  if (totalGzip > LIMITS.totalGzip) {
    failures.push(`Total gzip size ${formatSize(totalGzip)} exceeds limit ${formatSize(LIMITS.totalGzip)}`);
  }

  const mainJs = jsFiles.find(f => f.name.startsWith('index-') || f.name.startsWith('main-'));
  if (mainJs && mainJs.raw > LIMITS.mainJsRaw) {
    failures.push(`Main JS ${mainJs.name} (${formatSize(mainJs.raw)}) exceeds limit ${formatSize(LIMITS.mainJsRaw)}`);
  }

  const oversized = jsFiles.filter(f => f.raw > LIMITS.singleFileRaw);
  oversized.forEach(f => {
    failures.push(`${f.name} (${formatSize(f.raw)}) exceeds single-file limit ${formatSize(LIMITS.singleFileRaw)}`);
  });

  if (failures.length > 0) {
    console.log('FAILURES:');
    failures.forEach(f => console.log(`  - ${f}`));
    process.exit(1);
  }

  console.log('All bundle size checks passed.');
}

main();

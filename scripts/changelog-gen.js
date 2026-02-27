#!/usr/bin/env node
/**
 * Changelog 骨架產生器 (Changelog Generator)
 *
 * 從 conventional commits 自動產生 CHANGELOG 骨架：
 *   - 解析 git log 的 conventional commit 格式
 *   - 依 type 分組 (feat/fix/refactor/docs/test/perf/chore)
 *   - 產生繁中 Markdown 骨架供人工審閱/微調
 *
 * 使用方式：
 *   node scripts/changelog-gen.js                    — 從上次 tag 到 HEAD
 *   node scripts/changelog-gen.js --since 2026-02-27 — 指定起始日期
 *   node scripts/changelog-gen.js --from abc1234     — 指定起始 commit
 *   node scripts/changelog-gen.js --version 1.74.0   — 指定版本號
 *   node scripts/changelog-gen.js --output changelog-draft.md — 輸出到檔案
 *
 * @version 1.0.0
 * @date 2026-02-28
 */

import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.join(__dirname, '..');

// ============================================================
// Commit type 分類 (conventional commits)
// ============================================================
const TYPE_CONFIG = {
  feat:     { label: '新功能 (Features)',      emoji: '✨', order: 1 },
  fix:      { label: '修正 (Bug Fixes)',       emoji: '🐛', order: 2 },
  perf:     { label: '效能優化 (Performance)', emoji: '⚡', order: 3 },
  refactor: { label: '重構 (Refactoring)',     emoji: '♻️', order: 4 },
  test:     { label: '測試 (Tests)',           emoji: '🧪', order: 5 },
  docs:     { label: '文件 (Documentation)',   emoji: '📝', order: 6 },
  chore:    { label: '維護 (Chores)',          emoji: '🔧', order: 7 },
  ci:       { label: 'CI/CD',                 emoji: '🔄', order: 8 },
};

// ============================================================
// 1. 取得 git log (用 %x00 分隔 commits，||| 分隔欄位)
// ============================================================
const FIELD_SEP = '|||';
const RECORD_SEP = '%x00';
const LOG_FORMAT = `%H${FIELD_SEP}%s${FIELD_SEP}%b${FIELD_SEP}%ai${RECORD_SEP}`;

function getGitLog(fromRef, extraArgs) {
  const rangeArg = fromRef ? `${fromRef}..HEAD` : '';
  const extra = extraArgs || '';

  try {
    const cmd = `git log ${rangeArg} ${extra} --format="${LOG_FORMAT}" --no-merges`;
    const output = execSync(cmd, {
      cwd: ROOT,
      encoding: 'utf-8',
      maxBuffer: 10 * 1024 * 1024,
    });
    return output.trim();
  } catch (err) {
    console.error(`Git log failed: ${err.message}`);
    process.exit(1);
  }
}

// ============================================================
// 2. 解析 conventional commit (用 \0 分隔 records)
// ============================================================
function parseCommits(rawLog) {
  if (!rawLog) return [];

  const commits = [];
  // 用 null byte 分隔 commits
  const records = rawLog.split('\0').filter(r => r.trim());

  for (const record of records) {
    const parts = record.split(FIELD_SEP);
    if (parts.length < 4) continue;

    const hash = parts[0].trim();
    const subject = parts[1].trim();
    const body = parts[2].trim();
    const date = parts[3].trim().slice(0, 10); // YYYY-MM-DD

    // 解析 conventional commit subject: type(scope): description
    const match = subject.match(/^(\w+)(?:\(([^)]*)\))?:\s*(.+)$/);

    if (match) {
      commits.push({
        hash: hash.slice(0, 7),
        type: match[1].toLowerCase(),
        scope: match[2] || null,
        description: match[3],
        body,
        date,
      });
    } else {
      // 非 conventional commit
      commits.push({
        hash: hash.slice(0, 7),
        type: 'other',
        scope: null,
        description: subject,
        body,
        date,
      });
    }
  }

  return commits;
}

// ============================================================
// 3. 取得最新 tag
// ============================================================
function getLatestTag() {
  try {
    return execSync('git describe --tags --abbrev=0', {
      cwd: ROOT,
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
    }).trim();
  } catch {
    return null; // 沒有 tag
  }
}

// ============================================================
// 4. 猜測版本號
// ============================================================
function guessNextVersion(commits, currentVersion) {
  if (currentVersion) return currentVersion;

  const tag = getLatestTag();
  if (!tag) return '0.1.0';

  const match = tag.replace(/^v/, '').match(/^(\d+)\.(\d+)\.(\d+)/);
  if (!match) return '0.1.0';

  let [, major, minor, patch] = match.map(Number);

  // 根據 commit types 決定版本升級
  const hasBreaking = commits.some(c => c.body && c.body.includes('BREAKING CHANGE'));
  const hasFeat = commits.some(c => c.type === 'feat');

  if (hasBreaking) {
    major++;
    minor = 0;
    patch = 0;
  } else if (hasFeat) {
    minor++;
    patch = 0;
  } else {
    patch++;
  }

  return `${major}.${minor}.${patch}`;
}

// ============================================================
// 5. 產生 Markdown
// ============================================================
function generateMarkdown(commits, version) {
  const lines = [];
  const today = new Date().toISOString().slice(0, 10);

  lines.push(`## [${version}] - ${today}`);
  lines.push('');

  // 依 type 分組
  const groups = {};
  for (const commit of commits) {
    const type = TYPE_CONFIG[commit.type] ? commit.type : 'other';
    if (!groups[type]) groups[type] = [];
    groups[type].push(commit);
  }

  // 排序輸出
  const sortedTypes = Object.keys(groups).sort((a, b) => {
    const orderA = TYPE_CONFIG[a]?.order || 99;
    const orderB = TYPE_CONFIG[b]?.order || 99;
    return orderA - orderB;
  });

  for (const type of sortedTypes) {
    const config = TYPE_CONFIG[type] || { label: '其他 (Other)', emoji: '📌', order: 99 };
    lines.push(`### ${config.emoji} ${config.label}`);
    lines.push('');

    for (const commit of groups[type]) {
      const scope = commit.scope ? `**${commit.scope}**: ` : '';
      lines.push(`- ${scope}${commit.description} (\`${commit.hash}\`)`);

      // 如果有 body，取前 3 行作為子項
      if (commit.body) {
        const bodyLines = commit.body.split('\n').filter(l => l.trim()).slice(0, 3);
        for (const bl of bodyLines) {
          lines.push(`  - ${bl.trim()}`);
        }
      }
    }

    lines.push('');
  }

  // 統計
  lines.push('---');
  lines.push('');
  lines.push(`**統計**: ${commits.length} commits`);
  for (const type of sortedTypes) {
    const config = TYPE_CONFIG[type] || { label: '其他', emoji: '📌' };
    lines.push(`- ${config.emoji} ${type}: ${groups[type].length}`);
  }
  lines.push('');

  return lines.join('\n');
}

// ============================================================
// 6. 主程式
// ============================================================
function main() {
  const args = process.argv.slice(2);

  // 解析參數
  let fromRef = null;
  let sinceDate = null;
  let version = null;
  let outputFile = null;

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--from':
        fromRef = args[++i];
        break;
      case '--since':
        sinceDate = args[++i];
        break;
      case '--version':
        version = args[++i];
        break;
      case '--output':
        outputFile = args[++i];
        break;
      case '--help':
        console.log(`Usage: node scripts/changelog-gen.js [options]

Options:
  --since DATE     從指定日期開始 (YYYY-MM-DD)
  --from COMMIT    從指定 commit/tag 開始
  --version VER    指定版本號 (預設自動猜測)
  --output FILE    輸出到檔案 (預設 stdout)
  --help           顯示說明`);
        process.exit(0);
    }
  }

  // 決定起始點
  if (sinceDate) {
    const rawLog = getGitLog(null, `--since="${sinceDate}"`);
    const commits = parseCommits(rawLog);

    if (commits.length === 0) {
      console.log(`No commits found since ${sinceDate}`);
      process.exit(0);
    }

    const ver = guessNextVersion(commits, version);
    const md = generateMarkdown(commits, ver);

    if (outputFile) {
      const outPath = path.resolve(outputFile);
      fs.writeFileSync(outPath, md, 'utf-8');
      console.log(`Written to ${outPath} (${commits.length} commits)`);
    } else {
      console.log(md);
    }
    return;
  }

  // 從 tag 或 commit 開始
  if (!fromRef) {
    fromRef = getLatestTag();
    if (fromRef) {
      console.error(`Using latest tag: ${fromRef}`);
    } else {
      console.error('No tags found, using full history');
    }
  }

  const rawLog = getGitLog(fromRef);
  const commits = parseCommits(rawLog);

  if (commits.length === 0) {
    console.log('No new commits found');
    process.exit(0);
  }

  const ver = guessNextVersion(commits, version);
  const md = generateMarkdown(commits, ver);

  if (outputFile) {
    const outPath = path.resolve(outputFile);
    fs.writeFileSync(outPath, md, 'utf-8');
    console.log(`Written to ${outPath} (${commits.length} commits)`);
  } else {
    console.log(md);
  }
}

main();

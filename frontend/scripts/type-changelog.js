#!/usr/bin/env node
/**
 * 型別變更日誌生成器
 * Type Changelog Generator
 *
 * 用途：
 * 1. 比較 OpenAPI 生成前後的型別差異
 * 2. 自動生成變更日誌
 * 3. 追蹤型別演進歷史
 *
 * 使用方式：
 * - npm run api:generate:changelog
 *
 * @version 1.0.0
 * @date 2026-01-18
 */

import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

// ESM 需要手動定義 __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 路徑配置
const GENERATED_FILE = path.join(__dirname, '../src/types/generated/api.d.ts');
const BACKUP_FILE = path.join(__dirname, '../src/types/generated/api.d.ts.backup');
const CHANGELOG_FILE = path.join(__dirname, '../src/types/generated/CHANGELOG.md');

/**
 * 從型別定義檔案中提取 schema 名稱
 */
function extractSchemaNames(content) {
  const schemaRegex = /^\s+([A-Z][a-zA-Z]+):/gm;
  const schemas = new Set();
  let match;

  while ((match = schemaRegex.exec(content)) !== null) {
    schemas.add(match[1]);
  }

  return schemas;
}

/**
 * 比較兩個 schema 集合的差異
 */
function compareSchemas(oldSchemas, newSchemas) {
  const added = [...newSchemas].filter(s => !oldSchemas.has(s));
  const removed = [...oldSchemas].filter(s => !newSchemas.has(s));
  const unchanged = [...newSchemas].filter(s => oldSchemas.has(s));

  return { added, removed, unchanged };
}

/**
 * 生成 Markdown 格式的變更日誌條目
 */
function generateChangelogEntry(diff, timestamp) {
  const lines = [];
  const date = new Date(timestamp).toISOString().split('T')[0];
  const time = new Date(timestamp).toISOString().split('T')[1].split('.')[0];

  lines.push(`## ${date} ${time}`);
  lines.push('');

  if (diff.added.length > 0) {
    lines.push('### ✅ 新增 (Added)');
    diff.added.forEach(s => lines.push(`- \`${s}\``));
    lines.push('');
  }

  if (diff.removed.length > 0) {
    lines.push('### ❌ 移除 (Removed)');
    diff.removed.forEach(s => lines.push(`- \`${s}\``));
    lines.push('');
  }

  if (diff.added.length === 0 && diff.removed.length === 0) {
    lines.push('### 📝 無結構變更');
    lines.push('- 型別定義欄位可能有更新，但 schema 結構未變');
    lines.push('');
  }

  lines.push(`**統計**: ${diff.unchanged.length} 個 schema 保持不變`);
  lines.push('');
  lines.push('---');
  lines.push('');

  return lines.join('\n');
}

/**
 * 主程序
 */
async function main() {
  const args = process.argv.slice(2);
  const command = args[0] || 'generate';

  console.log('🔄 型別變更日誌生成器');
  console.log('');

  switch (command) {
    case 'backup':
      // 備份當前型別定義
      if (fs.existsSync(GENERATED_FILE)) {
        fs.copyFileSync(GENERATED_FILE, BACKUP_FILE);
        console.log('✅ 已備份當前型別定義');
      } else {
        console.log('⚠️  找不到型別定義檔案');
      }
      break;

    case 'compare':
      // 比較並生成日誌
      if (!fs.existsSync(BACKUP_FILE)) {
        console.log('⚠️  找不到備份檔案，跳過比較');
        return;
      }

      if (!fs.existsSync(GENERATED_FILE)) {
        console.log('❌ 找不到生成的型別定義檔案');
        return;
      }

      const oldContentCompare = fs.readFileSync(BACKUP_FILE, 'utf-8');
      const newContentCompare = fs.readFileSync(GENERATED_FILE, 'utf-8');

      const oldSchemasCompare = extractSchemaNames(oldContentCompare);
      const newSchemasCompare = extractSchemaNames(newContentCompare);

      const diffCompare = compareSchemas(oldSchemasCompare, newSchemasCompare);
      const entryCompare = generateChangelogEntry(diffCompare, Date.now());

      // 更新 CHANGELOG
      let existingChangelogCompare = '';
      if (fs.existsSync(CHANGELOG_FILE)) {
        existingChangelogCompare = fs.readFileSync(CHANGELOG_FILE, 'utf-8');
        // 移除標題行
        existingChangelogCompare = existingChangelogCompare.replace(/^# 型別變更日誌.*\n\n/m, '');
      }

      const newChangelogCompare = [
        '# 型別變更日誌 (Type Changelog)',
        '',
        '此檔案自動生成，記錄 OpenAPI 型別定義的變更歷史。',
        '',
        entryCompare,
        existingChangelogCompare
      ].join('\n');

      fs.writeFileSync(CHANGELOG_FILE, newChangelogCompare);

      // 清理備份
      fs.unlinkSync(BACKUP_FILE);

      console.log('📝 變更日誌已更新');
      console.log(`   新增: ${diffCompare.added.length}`);
      console.log(`   移除: ${diffCompare.removed.length}`);
      console.log(`   不變: ${diffCompare.unchanged.length}`);
      break;

    case 'generate':
    default:
      // 完整流程：備份 -> 生成 -> 比較
      console.log('步驟 1/3: 備份當前型別定義...');
      if (fs.existsSync(GENERATED_FILE)) {
        fs.copyFileSync(GENERATED_FILE, BACKUP_FILE);
        console.log('  ✅ 備份完成');
      } else {
        console.log('  ⚠️  首次生成，無需備份');
      }

      console.log('');
      console.log('步驟 2/3: 從 OpenAPI 生成型別...');
      try {
        execSync('npm run api:generate', {
          stdio: 'inherit',
          cwd: path.join(__dirname, '..')
        });
        console.log('  ✅ 型別生成完成');
      } catch (error) {
        console.log('  ❌ 型別生成失敗');
        process.exit(1);
      }

      console.log('');
      console.log('步驟 3/3: 比較並更新變更日誌...');
      if (fs.existsSync(BACKUP_FILE)) {
        const oldContent = fs.readFileSync(BACKUP_FILE, 'utf-8');
        const newContent = fs.readFileSync(GENERATED_FILE, 'utf-8');

        const oldSchemas = extractSchemaNames(oldContent);
        const newSchemas = extractSchemaNames(newContent);

        const diff = compareSchemas(oldSchemas, newSchemas);
        const entry = generateChangelogEntry(diff, Date.now());

        let existingChangelog = '';
        if (fs.existsSync(CHANGELOG_FILE)) {
          existingChangelog = fs.readFileSync(CHANGELOG_FILE, 'utf-8');
          existingChangelog = existingChangelog.replace(/^# 型別變更日誌.*\n\n此檔案自動生成.*\n\n/m, '');
        }

        const newChangelog = [
          '# 型別變更日誌 (Type Changelog)',
          '',
          '此檔案自動生成，記錄 OpenAPI 型別定義的變更歷史。',
          '',
          entry,
          existingChangelog
        ].join('\n');

        fs.writeFileSync(CHANGELOG_FILE, newChangelog);
        fs.unlinkSync(BACKUP_FILE);

        console.log('  ✅ 變更日誌已更新');

        if (diff.added.length > 0 || diff.removed.length > 0) {
          console.log('');
          console.log('📊 變更摘要:');
          if (diff.added.length > 0) {
            console.log(`   ➕ 新增: ${diff.added.join(', ')}`);
          }
          if (diff.removed.length > 0) {
            console.log(`   ➖ 移除: ${diff.removed.join(', ')}`);
          }
        }
      } else {
        console.log('  ⚠️  首次生成，已建立初始日誌');

        const newContent = fs.readFileSync(GENERATED_FILE, 'utf-8');
        const newSchemas = extractSchemaNames(newContent);

        const initialEntry = [
          '# 型別變更日誌 (Type Changelog)',
          '',
          '此檔案自動生成，記錄 OpenAPI 型別定義的變更歷史。',
          '',
          `## ${new Date().toISOString().split('T')[0]} (初始化)`,
          '',
          '### 📝 初始型別定義',
          '',
          `共 ${newSchemas.size} 個 schema`,
          '',
          '---',
          ''
        ].join('\n');

        fs.writeFileSync(CHANGELOG_FILE, initialEntry);
      }
      break;
  }

  console.log('');
  console.log('✨ 完成');
}

main().catch(console.error);

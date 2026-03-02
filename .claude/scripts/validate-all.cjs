#!/usr/bin/env node

/**
 * Skills, Agents & Commands 統一格式驗證腳本
 *
 * 用途：檢查所有 Skill, Agent, Command 檔案是否符合標準格式
 * 執行：node .claude/scripts/validate-all.cjs
 * 選項：--quiet 僅輸出錯誤摘要
 *       --strict-shared 對 _shared/ 目錄也執行完整驗證
 *       --validate-extended 驗證 maturity/related/depends_on 欄位
 *       --validate-commands 同時驗證 Commands
 *
 * 支援三種 Frontmatter 格式：
 * 1. 標準 YAML 格式 (推薦)
 * 2. YAML 變體 (trigger_keywords/date，向後相容)
 * 3. 引用區塊格式 (舊格式，向後相容)
 */

const fs = require('fs');
const path = require('path');

// 命令列選項
const QUIET_MODE = process.argv.includes('--quiet');
const STRICT_SHARED = process.argv.includes('--strict-shared');
const VALIDATE_EXTENDED = process.argv.includes('--validate-extended');
const VALIDATE_COMMANDS = process.argv.includes('--validate-commands');

// 配置
const CLAUDE_DIR = path.join(__dirname, '..');
const SKILLS_DIR = path.join(CLAUDE_DIR, 'skills');
const AGENTS_DIR = path.join(CLAUDE_DIR, 'agents');
const COMMANDS_DIR = path.join(CLAUDE_DIR, 'commands');

// 標準 YAML Frontmatter 欄位
const YAML_SKILL_FIELDS = ['name', 'version', 'category', 'triggers', 'updated'];
const YAML_AGENT_FIELDS = ['name', 'version', 'category', 'triggers', 'updated'];
const YAML_COMMAND_FIELDS = ['name', 'description'];

// 舊格式欄位 (中文，向後相容)
const LEGACY_SKILL_FIELDS = ['技能名稱', '觸發', '版本', '分類', '更新日期'];
const LEGACY_AGENT_FIELDS = ['用途', '觸發', '版本', '分類', '更新日期'];

const VALID_CATEGORIES = ['shared', 'react', 'project', 'backend', 'ai'];
const VALID_MATURITY = ['draft', 'beta', 'stable', 'frozen'];

const SHARED_DIR_NAME = '_shared';

// 結果統計
const results = {
  skills: { total: 0, passed: 0, failed: 0, warnings: 0, errors: [] },
  agents: { total: 0, passed: 0, failed: 0, warnings: 0, errors: [] },
  commands: { total: 0, passed: 0, failed: 0, warnings: 0, errors: [] },
};

/**
 * 解析標準 YAML Frontmatter (含 CK_Missive 變體正規化)
 */
function parseYamlFrontmatter(content) {
  const normalizedContent = content.replace(/\r\n/g, '\n');
  const yamlMatch = normalizedContent.match(/^---\n([\s\S]*?)\n---/);
  if (!yamlMatch) return null;

  const yamlContent = yamlMatch[1];
  const fields = {};
  const lines = yamlContent.split('\n');
  let currentKey = null;
  let inArray = false;

  for (const line of lines) {
    if (line.match(/^\s*-\s+(.+)/)) {
      if (currentKey && inArray) {
        const value = line.match(/^\s*-\s+(.+)/)[1].trim().replace(/^['"]|['"]$/g, '');
        if (!Array.isArray(fields[currentKey])) fields[currentKey] = [];
        fields[currentKey].push(value);
      }
      continue;
    }

    const kvMatch = line.match(/^(\w+):\s*(.*)$/);
    if (kvMatch) {
      currentKey = kvMatch[1];
      const value = kvMatch[2].trim();
      if (value === '' || value === '|' || value === '>') {
        inArray = true;
        fields[currentKey] = [];
      } else {
        inArray = false;
        fields[currentKey] = value.replace(/^['"]|['"]$/g, '');
      }
    }
  }

  // 正規化欄位名稱
  if (fields.trigger_keywords && !fields.triggers) {
    fields.triggers = fields.trigger_keywords;
  }
  if (fields.keywords && !fields.triggers) {
    fields.triggers = fields.keywords;
  }
  if (fields.date && !fields.updated) {
    fields.updated = fields.date;
  }

  return fields;
}

/**
 * 解析舊格式 Frontmatter (引用區塊)
 */
function parseLegacyFrontmatter(content) {
  const frontmatterRegex = /> \*\*(.+?)\*\*[：:]\s*(.+)/g;
  const fields = {};

  let match;
  while ((match = frontmatterRegex.exec(content)) !== null) {
    const key = match[1];
    const value = match[2];
    if (key === '觸發' || key === '觸發關鍵字') {
      fields['觸發'] = value;
    } else {
      fields[key] = value;
    }
  }

  return Object.keys(fields).length > 0 ? fields : null;
}

/**
 * 驗證 Frontmatter 欄位
 */
function validateFrontmatter(content, yamlFields, legacyFields) {
  const errors = [];
  const warnings = [];
  let format = 'unknown';

  // 嘗試解析 YAML 格式
  const yamlParsed = parseYamlFrontmatter(content);
  if (yamlParsed) {
    format = 'yaml';

    // 檢查是否為變體格式
    const rawContent = content.replace(/\r\n/g, '\n');
    if (rawContent.includes('trigger_keywords:') || rawContent.includes('date:')) {
      warnings.push('使用 YAML 變體格式，建議遷移 trigger_keywords→triggers, date→updated');
    }

    // 檢查必要欄位
    for (const field of yamlFields) {
      if (!yamlParsed[field]) {
        errors.push(`缺少必要欄位: ${field}`);
      }
    }

    // 檢查分類值
    if (yamlParsed.category && !VALID_CATEGORIES.includes(yamlParsed.category)) {
      errors.push(`無效的分類值: ${yamlParsed.category} (應為 ${VALID_CATEGORIES.join(' | ')})`);
    }

    // 檢查觸發關鍵字格式
    const triggers = yamlParsed.triggers;
    if (triggers && Array.isArray(triggers)) {
      const hasCommand = triggers.some(t => t.startsWith('/'));
      if (!hasCommand) {
        warnings.push('建議至少包含一個 /command 格式的觸發關鍵字');
      }
    }

    // 擴充驗證
    if (VALIDATE_EXTENDED) {
      if (yamlParsed.maturity && !VALID_MATURITY.includes(yamlParsed.maturity)) {
        errors.push(`無效的 maturity 值: ${yamlParsed.maturity} (應為 ${VALID_MATURITY.join(' | ')})`);
      }
      if (yamlParsed.related && Array.isArray(yamlParsed.related)) {
        for (const ref of yamlParsed.related) {
          if (ref.includes('.md') || ref.includes('/')) {
            warnings.push(`related "${ref}" 應為 kebab-case ID，不含 .md 或路徑`);
          }
        }
      }
      if (yamlParsed.depends_on && Array.isArray(yamlParsed.depends_on)) {
        for (const dep of yamlParsed.depends_on) {
          if (dep.includes('.md') || dep.includes('/')) {
            warnings.push(`depends_on "${dep}" 應為 kebab-case ID，不含 .md 或路徑`);
          }
        }
      }
    }

    return { format, errors, warnings };
  }

  // 嘗試解析舊格式
  const legacyParsed = parseLegacyFrontmatter(content);
  if (legacyParsed) {
    format = 'legacy';
    warnings.push('使用舊格式 Frontmatter，建議遷移至標準 YAML 格式');

    for (const field of legacyFields) {
      if (!legacyParsed[field]) {
        errors.push(`缺少必要欄位: ${field}`);
      }
    }

    if (legacyParsed['分類'] && !VALID_CATEGORIES.includes(legacyParsed['分類'])) {
      errors.push(`無效的分類值: ${legacyParsed['分類']} (應為 ${VALID_CATEGORIES.join(' | ')})`);
    }

    return { format, errors, warnings };
  }

  // 兩種格式都沒有
  errors.push('缺少有效的 Frontmatter (YAML 或引用區塊格式)');
  return { format, errors, warnings };
}

/**
 * 寬鬆驗證 Commands
 */
function validateCommand(content) {
  const errors = [];
  const warnings = [];

  const hasYaml = content.match(/^---[\s\S]*?---/m);
  const hasTitle = content.match(/^# .+/m);

  if (!hasTitle) {
    errors.push('缺少 # 標題');
  }

  if (!hasYaml) {
    warnings.push('建議添加 YAML frontmatter');
  }

  return { errors, warnings };
}

function isSharedFile(relativePath) {
  return relativePath.includes(SHARED_DIR_NAME);
}

function parseSharedFrontmatter(content) {
  const errors = [];
  const warnings = [];

  const hasYaml = content.match(/^---[\s\S]*?---/m);
  const hasTitle = content.match(/^# .+/m);
  const hasLegacy = content.match(/> \*\*.+\*\*[：:]/);

  if (!hasYaml && !hasTitle && !hasLegacy) {
    warnings.push('建議添加 Frontmatter 或標題');
  }

  return { errors, warnings };
}

/**
 * 遞迴掃描目錄
 */
function scanDirectory(dir, type, yamlFields, legacyFields, relativePath = '') {
  if (!fs.existsSync(dir)) {
    if (!QUIET_MODE) console.log(`   ⚠️  目錄不存在: ${dir}`);
    return;
  }

  const items = fs.readdirSync(dir);
  const resultObj = results[type];

  for (const item of items) {
    const fullPath = path.join(dir, item);
    const relPath = path.join(relativePath, item);
    const stat = fs.statSync(fullPath);

    if (stat.isDirectory()) {
      scanDirectory(fullPath, type, yamlFields, legacyFields, relPath);
    } else if (item.endsWith('.md') && !item.includes('TEMPLATE')) {
      resultObj.total++;

      const content = fs.readFileSync(fullPath, 'utf-8');
      const isShared = isSharedFile(relPath);

      let validationResult;
      if (type === 'commands') {
        validationResult = validateCommand(content);
      } else if (isShared && !STRICT_SHARED) {
        validationResult = parseSharedFrontmatter(content);
      } else {
        validationResult = validateFrontmatter(content, yamlFields, legacyFields);
      }

      const { errors, warnings } = validationResult;

      if (errors.length === 0) {
        resultObj.passed++;
        if (!QUIET_MODE) {
          const suffix = isShared ? ' (同步檔案)' : '';
          console.log(`   ✅ ${relPath}${suffix}`);
          if (warnings.length > 0) {
            resultObj.warnings += warnings.length;
            warnings.forEach(w => console.log(`      ⚠️  ${w}`));
          }
        }
      } else {
        resultObj.failed++;
        if (!QUIET_MODE) {
          console.log(`   ❌ ${relPath}`);
          errors.forEach(e => console.log(`      ❌ ${e}`));
          warnings.forEach(w => console.log(`      ⚠️  ${w}`));
        }
        resultObj.errors.push({ file: relPath, errors, warnings });
      }
    }
  }
}

// ===== 主程式 =====
if (!QUIET_MODE) {
  console.log('🔍 Claude Skills, Agents & Commands 格式驗證\n');
  console.log('═══════════════════════════════════════════\n');
}

// 驗證 Skills
if (!QUIET_MODE) {
  console.log('📚 Skills 驗證:');
  console.log('-------------------------------------------');
}
scanDirectory(SKILLS_DIR, 'skills', YAML_SKILL_FIELDS, LEGACY_SKILL_FIELDS);

if (!QUIET_MODE) console.log('\n');

// 驗證 Agents
if (!QUIET_MODE) {
  console.log('🤖 Agents 驗證:');
  console.log('-------------------------------------------');
}
scanDirectory(AGENTS_DIR, 'agents', YAML_AGENT_FIELDS, LEGACY_AGENT_FIELDS);

// 驗證 Commands
if (VALIDATE_COMMANDS) {
  if (!QUIET_MODE) {
    console.log('\n');
    console.log('⚡ Commands 驗證:');
    console.log('-------------------------------------------');
  }
  scanDirectory(COMMANDS_DIR, 'commands', YAML_COMMAND_FIELDS, []);
}

// 輸出統計
if (!QUIET_MODE) {
  console.log('\n═══════════════════════════════════════════');
  console.log('\n📊 驗證結果統計:\n');

  console.log('Skills:');
  console.log(`   總計: ${results.skills.total}`);
  console.log(`   ✅ 通過: ${results.skills.passed}`);
  console.log(`   ❌ 失敗: ${results.skills.failed}`);
  console.log(`   ⚠️  警告: ${results.skills.warnings}`);

  console.log('\nAgents:');
  console.log(`   總計: ${results.agents.total}`);
  console.log(`   ✅ 通過: ${results.agents.passed}`);
  console.log(`   ❌ 失敗: ${results.agents.failed}`);
  console.log(`   ⚠️  警告: ${results.agents.warnings}`);

  if (VALIDATE_COMMANDS) {
    console.log('\nCommands:');
    console.log(`   總計: ${results.commands.total}`);
    console.log(`   ✅ 通過: ${results.commands.passed}`);
    console.log(`   ❌ 失敗: ${results.commands.failed}`);
    console.log(`   ⚠️  警告: ${results.commands.warnings}`);
  }
}

const totalFailed = results.skills.failed + results.agents.failed + results.commands.failed;
if (totalFailed > 0) {
  if (QUIET_MODE) {
    console.log(`❌ 驗證失敗: Skills ${results.skills.failed}/${results.skills.total}, Agents ${results.agents.failed}/${results.agents.total}`);
  } else {
    console.log('\n❌ 驗證失敗，請修復上述錯誤');
  }
  process.exit(1);
} else {
  if (QUIET_MODE) {
    console.log(`✅ 驗證通過: Skills ${results.skills.total}, Agents ${results.agents.total}`);
  } else {
    console.log('\n✅ 所有格式驗證通過');
  }
  process.exit(0);
}

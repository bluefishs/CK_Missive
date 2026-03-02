#!/usr/bin/env node

/**
 * Learned Pattern Promotion Script
 *
 * 掃描 .claude/learned/ 中的學習模式，將符合升級條件的模式
 * 自動生成 Skill 模板至 .claude/skills/
 *
 * 升級條件（來自 .claude/learned/config.json）：
 * - confidence >= 0.8
 * - use_count >= 5
 *
 * 用法：
 *   node .claude/scripts/promote-learned-patterns.cjs          # 乾跑（預設）
 *   node .claude/scripts/promote-learned-patterns.cjs --apply  # 實際生成
 */

const fs = require('fs');
const path = require('path');

const LEARNED_DIR = path.join(__dirname, '..', 'learned');
const SKILLS_DIR = path.join(__dirname, '..', 'skills');
const CONFIG_PATH = path.join(LEARNED_DIR, 'config.json');

const DRY_RUN = !process.argv.includes('--apply');

// 讀取升級規則配置
function loadConfig() {
  if (!fs.existsSync(CONFIG_PATH)) {
    console.log('⚠️  未找到 config.json，使用預設升級規則');
    return { min_confidence: 0.8, min_use_count: 5, target_path: '.claude/skills/' };
  }
  const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
  return config.promotion_rules || { min_confidence: 0.8, min_use_count: 5, target_path: '.claude/skills/' };
}

// 解析 YAML frontmatter
function parseYamlFrontmatter(content) {
  const normalizedContent = content.replace(/\r\n/g, '\n');
  const yamlMatch = normalizedContent.match(/^---\n([\s\S]*?)\n---/);
  if (!yamlMatch) return null;

  const fields = {};
  const lines = yamlMatch[1].split('\n');
  let currentKey = null;
  let inArray = false;

  for (const line of lines) {
    const arrayItemMatch = line.match(/^\s*-\s+(.+)/);
    if (arrayItemMatch) {
      if (currentKey && inArray) {
        if (!Array.isArray(fields[currentKey])) fields[currentKey] = [];
        fields[currentKey].push(arrayItemMatch[1].trim().replace(/^['"]|['"]$/g, ''));
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
  return fields;
}

// 提取內文（frontmatter 以外的部分）
function extractBody(content) {
  const normalizedContent = content.replace(/\r\n/g, '\n');
  const endMatch = normalizedContent.match(/^---\n[\s\S]*?\n---\n/);
  if (endMatch) {
    return normalizedContent.substring(endMatch[0].length).trim();
  }
  return normalizedContent.trim();
}

// 掃描符合升級條件的模式
function scanLearnedPatterns(rules) {
  const patterns = [];

  if (!fs.existsSync(LEARNED_DIR)) {
    return patterns;
  }

  for (const file of fs.readdirSync(LEARNED_DIR)) {
    if (!file.endsWith('.md')) continue;

    const filePath = path.join(LEARNED_DIR, file);
    const content = fs.readFileSync(filePath, 'utf-8');
    const frontmatter = parseYamlFrontmatter(content);

    if (!frontmatter) continue;

    const confidence = parseFloat(frontmatter.confidence || '0');
    const useCount = parseInt(frontmatter.use_count || '0', 10);

    if (confidence >= rules.min_confidence && useCount >= rules.min_use_count) {
      patterns.push({
        file,
        name: frontmatter.name || file.replace('.md', ''),
        type: frontmatter.type || 'project_specific',
        confidence,
        useCount,
        content,
      });
    }
  }

  return patterns;
}

// 生成 Skill 模板
function generateSkillTemplate(pattern) {
  const today = new Date().toISOString().slice(0, 10);
  const skillId = pattern.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
  const body = extractBody(pattern.content);

  return {
    filename: `${skillId}.md`,
    content: `---
name: ${pattern.name}
description: 從學習模式升級 - ${pattern.type}
version: 0.1.0
category: project
triggers:
  - /${skillId}
updated: ${today}
maturity: beta
related: []
depends_on: []
---

# ${pattern.name}

> 本 Skill 由學習模式自動升級生成
> 信心度: ${pattern.confidence} | 使用次數: ${pattern.useCount} | 類型: ${pattern.type}

${body}
`,
  };
}

// 主程式
console.log('🔍 Learned Pattern Promotion Scanner\n');
console.log('═══════════════════════════════════════════\n');

const rules = loadConfig();
console.log(`📋 升級規則: confidence >= ${rules.min_confidence}, use_count >= ${rules.min_use_count}`);
console.log(`📁 掃描目錄: ${LEARNED_DIR}`);
console.log(`📤 目標目錄: ${SKILLS_DIR}`);
console.log(`🔧 模式: ${DRY_RUN ? '乾跑 (加 --apply 實際生成)' : '實際生成'}\n`);

const patterns = scanLearnedPatterns(rules);

if (patterns.length === 0) {
  console.log('📭 No patterns eligible for promotion.');
  console.log('\n提示：使用 /learn 指令在對話中記錄可重用模式。');
  console.log('模式檔案格式參考 .claude/skills/continuous-learning.md');
  process.exit(0);
}

console.log(`\n🎯 找到 ${patterns.length} 個符合升級條件的模式：\n`);

let promoted = 0;
for (const pattern of patterns) {
  const template = generateSkillTemplate(pattern);
  const targetPath = path.join(SKILLS_DIR, template.filename);

  if (fs.existsSync(targetPath)) {
    console.log(`   ⚠️  ${pattern.file} → ${template.filename} (已存在，跳過)`);
    continue;
  }

  if (DRY_RUN) {
    console.log(`   📝 ${pattern.file} → ${template.filename} (乾跑，不生成)`);
    console.log(`      名稱: ${pattern.name} | 信心度: ${pattern.confidence} | 使用: ${pattern.useCount}`);
  } else {
    fs.writeFileSync(targetPath, template.content, 'utf-8');
    console.log(`   ✅ ${pattern.file} → ${template.filename} (已生成)`);
  }
  promoted++;
}

console.log(`\n═══════════════════════════════════════════`);
console.log(`\n📊 結果: ${promoted} 個模式${DRY_RUN ? '可升級' : '已升級'}，${patterns.length - promoted} 個跳過`);

if (DRY_RUN && promoted > 0) {
  console.log('\n💡 執行 `node .claude/scripts/promote-learned-patterns.cjs --apply` 實際生成');
}

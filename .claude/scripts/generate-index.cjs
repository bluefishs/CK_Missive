#!/usr/bin/env node

/**
 * Skills, Agents & Commands 索引生成腳本
 *
 * 用途：生成 skills-index.json, agents-index.json, commands-index.json 供知識地圖使用
 * 執行：node .claude/scripts/generate-index.cjs
 */

const fs = require('fs');
const path = require('path');

// 配置
const CLAUDE_DIR = path.join(__dirname, '..');
const SKILLS_DIR = path.join(CLAUDE_DIR, 'skills');
const AGENTS_DIR = path.join(CLAUDE_DIR, 'agents');
const COMMANDS_DIR = path.join(CLAUDE_DIR, 'commands');
const OUTPUT_DIR = path.join(CLAUDE_DIR, 'generated');

// 確保輸出目錄存在
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

/**
 * 解析標準 YAML Frontmatter
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
    // 陣列項目
    const arrayItemMatch = line.match(/^\s*-\s+(.+)/);
    if (arrayItemMatch) {
      if (currentKey && inArray) {
        const value = arrayItemMatch[1].trim().replace(/^['"]|['"]$/g, '');
        if (!Array.isArray(fields[currentKey])) fields[currentKey] = [];
        fields[currentKey].push(value);
      }
      continue;
    }

    // 鍵值對
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

  // 正規化欄位名稱（CK_Missive 變體支援）
  if (fields.trigger_keywords && !fields.triggers) {
    fields.triggers = fields.trigger_keywords;
    delete fields.trigger_keywords;
  }
  if (fields.keywords && !fields.triggers) {
    fields.triggers = fields.keywords;
    delete fields.keywords;
  }
  if (fields.date && !fields.updated) {
    fields.updated = fields.date;
    delete fields.date;
  }

  return fields;
}

/**
 * 解析 Markdown 檔案的 frontmatter
 * 優先解析 YAML 格式，fallback 舊格式
 */
function parseFrontmatter(content) {
  const fields = {};

  // 1. 嘗試 YAML frontmatter
  const yamlFields = parseYamlFrontmatter(content);
  if (yamlFields) {
    if (yamlFields.name) fields.title = yamlFields.name;
    if (yamlFields.description) fields.description = yamlFields.description;
    if (yamlFields.version) fields.version = yamlFields.version;
    if (yamlFields.category) fields.category = yamlFields.category;
    if (yamlFields.updated) fields.updated = yamlFields.updated;
    if (yamlFields.maturity) fields.maturity = yamlFields.maturity;
    if (yamlFields.triggers) {
      fields.triggers = Array.isArray(yamlFields.triggers) ? yamlFields.triggers : [yamlFields.triggers];
    }
    if (yamlFields.related) {
      fields.related = Array.isArray(yamlFields.related) ? yamlFields.related : [yamlFields.related];
    }
    if (yamlFields.depends_on) {
      fields.depends_on = Array.isArray(yamlFields.depends_on) ? yamlFields.depends_on : [yamlFields.depends_on];
    }
    return fields;
  }

  // 2. Fallback: 舊格式解析 (> **欄位**: 值)
  const headerContent = content.substring(0, 800);

  const titleMatch = headerContent.match(/^# (.+)/m);
  if (titleMatch) fields.title = titleMatch[1];

  // 中文鍵值對
  const frontmatterRegex = /> \*\*(.+?)\*\*[：:]\s*(.+)/g;
  let match;
  while ((match = frontmatterRegex.exec(headerContent)) !== null) {
    const key = match[1];
    const value = match[2];
    if (key === '觸發' || key === '觸發關鍵字') {
      fields.triggers = value.split(/[,、]/).map(t => t.trim().replace(/`/g, ''));
    } else if (key === '版本') {
      fields.version = value;
    } else if (key === '分類') {
      fields.category = value;
    } else if (key === '更新日期' || key === '建立日期') {
      fields.updated = value;
    } else if (key === '適用範圍') {
      fields.description = value;
    } else {
      fields[key] = value;
    }
  }

  return fields;
}

/**
 * 遞迴掃描目錄
 */
function scanDirectory(dir, basePath = '') {
  const items = [];

  if (!fs.existsSync(dir)) {
    return items;
  }

  const files = fs.readdirSync(dir);

  for (const file of files) {
    const fullPath = path.join(dir, file);
    const relativePath = path.join(basePath, file);
    const stat = fs.statSync(fullPath);

    if (stat.isDirectory()) {
      items.push(...scanDirectory(fullPath, relativePath));
    } else if (file.endsWith('.md') && !file.includes('TEMPLATE')) {
      const content = fs.readFileSync(fullPath, 'utf-8');
      const metadata = parseFrontmatter(content);

      items.push({
        id: relativePath.replace(/\\/g, '/').replace('.md', '').replace(/\//g, '-'),
        path: relativePath.replace(/\\/g, '/'),
        ...metadata,
        lastModified: stat.mtime.toISOString(),
      });
    }
  }

  return items;
}

// ===== 生成 Skills 索引 =====
console.log('📚 生成 Skills 索引...');
const skills = scanDirectory(SKILLS_DIR);
const skillsIndex = {
  generated: new Date().toISOString(),
  total: skills.length,
  categories: [...new Set(skills.map(s => s.category).filter(Boolean))],
  items: skills,
};

fs.writeFileSync(
  path.join(OUTPUT_DIR, 'skills-index.json'),
  JSON.stringify(skillsIndex, null, 2),
  'utf-8'
);
console.log(`   ✅ 已生成 skills-index.json (${skills.length} 個 Skills)`);

// ===== 生成 Agents 索引 =====
console.log('🤖 生成 Agents 索引...');
const agents = scanDirectory(AGENTS_DIR);
const agentsIndex = {
  generated: new Date().toISOString(),
  total: agents.length,
  categories: [...new Set(agents.map(a => a.category).filter(Boolean))],
  items: agents,
};

fs.writeFileSync(
  path.join(OUTPUT_DIR, 'agents-index.json'),
  JSON.stringify(agentsIndex, null, 2),
  'utf-8'
);
console.log(`   ✅ 已生成 agents-index.json (${agents.length} 個 Agents)`);

// ===== 生成 Commands 索引 (CK_Missive 特有) =====
console.log('⚡ 生成 Commands 索引...');
const commands = scanDirectory(COMMANDS_DIR);
const commandsIndex = {
  generated: new Date().toISOString(),
  total: commands.length,
  items: commands,
};

fs.writeFileSync(
  path.join(OUTPUT_DIR, 'commands-index.json'),
  JSON.stringify(commandsIndex, null, 2),
  'utf-8'
);
console.log(`   ✅ 已生成 commands-index.json (${commands.length} 個 Commands)`);

// ===== 生成觸發關鍵字索引 =====
console.log('🔑 生成觸發關鍵字索引...');
const triggerIndex = {
  generated: new Date().toISOString(),
  skills: {},
  agents: {},
  commands: {},
};

for (const skill of skills) {
  if (skill.triggers) {
    for (const trigger of skill.triggers) {
      triggerIndex.skills[trigger] = {
        id: skill.id,
        name: skill.title,
        path: skill.path,
      };
    }
  }
}

for (const agent of agents) {
  if (agent.triggers) {
    for (const trigger of agent.triggers) {
      triggerIndex.agents[trigger] = {
        id: agent.id,
        name: agent.title,
        path: agent.path,
      };
    }
  }
}

for (const cmd of commands) {
  if (cmd.triggers) {
    for (const trigger of cmd.triggers) {
      triggerIndex.commands[trigger] = {
        id: cmd.id,
        name: cmd.title,
        path: cmd.path,
      };
    }
  }
}

fs.writeFileSync(
  path.join(OUTPUT_DIR, 'trigger-index.json'),
  JSON.stringify(triggerIndex, null, 2),
  'utf-8'
);

const totalTriggers = Object.keys(triggerIndex.skills).length +
  Object.keys(triggerIndex.agents).length +
  Object.keys(triggerIndex.commands).length;
console.log(`   ✅ 已生成 trigger-index.json (${totalTriggers} 個觸發關鍵字)`);

console.log('\n✅ 索引生成完成！');
console.log(`   輸出目錄: ${OUTPUT_DIR}`);

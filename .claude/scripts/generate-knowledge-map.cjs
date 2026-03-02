#!/usr/bin/env node

/**
 * CK_Missive Heptabase Knowledge Map Generator
 *
 * 讀取所有知識源（Skills, Agents, Commands, Rules, Hooks, Docs, ADR, Diagrams, Wiki, Checklists, Core），
 * 生成 Obsidian 相容的 Markdown 卡片結構，供匯入 Heptabase。
 *
 * 用法：node .claude/scripts/generate-knowledge-map.cjs [--clean] [--if-stale] [--diff]
 * 選項：--clean     清除舊卡片後重建
 *       --if-stale  僅在源檔案比知識地圖更新時才重建
 *       --diff      比較新舊卡片差異，輸出變更報告（不覆寫舊卡片）
 * 輸出：docs/knowledge-map/
 */

const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = path.join(__dirname, '..', '..');
const CLAUDE_DIR = path.join(PROJECT_ROOT, '.claude');
const OUTPUT_DIR = path.join(PROJECT_ROOT, 'docs', 'knowledge-map');
const TIMESTAMP_FILE = path.join(OUTPUT_DIR, '.last-generated');
const CLEAN = process.argv.includes('--clean');
const IF_STALE = process.argv.includes('--if-stale');
const DIFF_MODE = process.argv.includes('--diff');
const DIFF_REPORT = path.join(OUTPUT_DIR, '_Diff-Report.md');

// ═══════════════════════════════════════════
// Staleness Check
// ═══════════════════════════════════════════
function checkStaleness() {
  if (!fs.existsSync(TIMESTAMP_FILE)) return true; // 從未生成過
  const lastGen = fs.statSync(TIMESTAMP_FILE).mtimeMs;

  // 掃描所有知識源目錄，找最新修改時間
  const sourceDirs = [
    path.join(CLAUDE_DIR, 'skills'),
    path.join(CLAUDE_DIR, 'agents'),
    path.join(CLAUDE_DIR, 'commands'),
    path.join(CLAUDE_DIR, 'rules'),
    path.join(CLAUDE_DIR, 'hooks'),
    path.join(PROJECT_ROOT, 'docs'),
    path.join(PROJECT_ROOT, 'CLAUDE.md'),
  ];

  function getNewestMtime(dir) {
    if (!fs.existsSync(dir)) return 0;
    const stat = fs.statSync(dir);
    if (!stat.isDirectory()) return stat.mtimeMs;

    let newest = 0;
    try {
      for (const item of fs.readdirSync(dir)) {
        const full = path.join(dir, item);
        const s = fs.statSync(full);
        if (s.isDirectory()) {
          newest = Math.max(newest, getNewestMtime(full));
        } else if (item.endsWith('.md') || item.endsWith('.ps1') || item.endsWith('.sh')) {
          newest = Math.max(newest, s.mtimeMs);
        }
      }
    } catch { /* ignore permission errors */ }
    return newest;
  }

  let newestSource = 0;
  for (const dir of sourceDirs) {
    newestSource = Math.max(newestSource, getNewestMtime(dir));
  }

  return newestSource > lastGen;
}

function writeTimestamp() {
  fs.mkdirSync(path.dirname(TIMESTAMP_FILE), { recursive: true });
  fs.writeFileSync(TIMESTAMP_FILE, new Date().toISOString(), 'utf-8');
}

// ═══════════════════════════════════════════
// Diff：新舊卡片差異比較
// ═══════════════════════════════════════════
function loadExistingCards() {
  const existing = {};
  if (!fs.existsSync(OUTPUT_DIR)) return existing;

  function scan(dir) {
    if (!fs.existsSync(dir)) return;
    for (const item of fs.readdirSync(dir)) {
      if (item.startsWith('_')) continue; // skip _Index.md, _Relationship-Map.md, _Diff-Report.md
      const full = path.join(dir, item);
      const stat = fs.statSync(full);
      if (stat.isDirectory()) {
        scan(full);
      } else if (item.endsWith('.md')) {
        const content = fs.readFileSync(full, 'utf-8');
        const relPath = path.relative(OUTPUT_DIR, full).replace(/\\/g, '/');
        // Extract card id from aliases
        const aliasMatch = content.match(/aliases:\n\s*-\s+(.+)/);
        const id = aliasMatch ? aliasMatch[1].trim() : path.basename(item, '.md');
        existing[id] = { path: relPath, content, title: path.basename(item, '.md') };
      }
    }
  }
  scan(OUTPUT_DIR);
  return existing;
}

function generateDiffReport(newCards, existingCards) {
  const added = [];
  const modified = [];
  const deleted = [];

  // Build new card map: id → { content, section, title }
  const newCardMap = {};
  for (const card of newCards) {
    const content = generateCardContent(card);
    newCardMap[card.id] = { content, section: card.section, title: card.title };
  }

  // Find added and modified
  for (const [id, info] of Object.entries(newCardMap)) {
    if (!existingCards[id]) {
      added.push({ id, title: info.title, section: info.section });
    } else {
      // Compare content (normalize whitespace)
      const oldNorm = existingCards[id].content.replace(/\r\n/g, '\n').trim();
      const newNorm = info.content.replace(/\r\n/g, '\n').trim();
      if (oldNorm !== newNorm) {
        modified.push({ id, title: info.title, section: info.section, oldPath: existingCards[id].path });
      }
    }
  }

  // Find deleted
  for (const [id, info] of Object.entries(existingCards)) {
    if (!newCardMap[id]) {
      deleted.push({ id, title: info.title, path: info.path });
    }
  }

  // Generate report
  const now = new Date().toISOString().split('T')[0];
  let report = `# Knowledge Map Diff Report\n\n`;
  report += `**Generated**: ${now} | **Mode**: diff\n\n`;
  report += `| 類型 | 數量 |\n|------|------|\n`;
  report += `| 新增 | ${added.length} |\n`;
  report += `| 修改 | ${modified.length} |\n`;
  report += `| 刪除 | ${deleted.length} |\n`;
  report += `| 未變 | ${newCards.length - added.length - modified.length} |\n\n`;

  if (added.length === 0 && modified.length === 0 && deleted.length === 0) {
    report += `> ✅ 知識地圖與源檔案完全同步，無需更新 Heptabase。\n`;
    return { report, added, modified, deleted };
  }

  if (added.length > 0) {
    report += `## 新增卡片 (${added.length})\n\n`;
    report += `> 以下卡片在 Heptabase 中不存在，需要匯入。\n\n`;
    for (const a of added) {
      report += `- **${a.title}** → \`${a.section}/\`\n`;
    }
    report += '\n';
  }

  if (modified.length > 0) {
    report += `## 修改卡片 (${modified.length})\n\n`;
    report += `> 以下卡片內容已變更，建議在 Heptabase 中手動更新。\n\n`;
    for (const m of modified) {
      report += `- **${m.title}** (${m.section})\n`;
    }
    report += '\n';
  }

  if (deleted.length > 0) {
    report += `## 刪除卡片 (${deleted.length})\n\n`;
    report += `> 以下卡片已不再由源檔案生成，可在 Heptabase 中封存。\n\n`;
    for (const d of deleted) {
      report += `- ~~${d.title}~~ (原路徑: ${d.path})\n`;
    }
    report += '\n';
  }

  report += `---\n\n## Heptabase 維護建議\n\n`;
  report += `1. **新增卡片**：將 \`docs/knowledge-map/\` 中標記為「新增」的卡片單獨匯入\n`;
  report += `2. **修改卡片**：開啟對應檔案，複製更新內容到 Heptabase 卡片\n`;
  report += `3. **刪除卡片**：在 Heptabase 中加上 \`archived\` tag 或移至封存白板\n`;
  report += `4. **Wikilink**：新增卡片的 \`[[連結]]\` 會自動指向已存在的同名卡片\n`;

  return { report, added, modified, deleted };
}

// ═══════════════════════════════════════════
// Section 配置 (9 個 CK_Missive 專屬 Section)
// ═══════════════════════════════════════════
const SECTIONS = {
  '00-Overview': {
    label: 'Project Overview',
    desc: '專案總覽、技術棧、服務端口',
  },
  '01-Architecture': {
    label: 'Architecture',
    desc: 'ADR (11)、Diagrams (6)、架構文件',
    keywords: ['architecture', 'adr', '架構', 'data-flow', 'database-er', 'deployment', 'system-overview'],
  },
  '02-Backend': {
    label: 'Backend',
    desc: 'FastAPI、Schema、Service、Repository、Alembic、Database',
    categories: ['backend'],
    keywords: ['schema', 'service', 'repository', 'pydantic', 'fastapi', 'api', 'database', 'alembic', 'migration', 'serialization', 'csv'],
  },
  '03-Frontend': {
    label: 'Frontend',
    desc: 'React、TypeScript、Ant Design、Components、RWD',
    categories: ['react'],
    keywords: ['react', 'hook', 'eslint', 'vite', 'frontend', 'component', 'typescript', 'antd', 'rwd', 'ui'],
  },
  '04-AI': {
    label: 'AI',
    desc: 'Groq/Ollama、Agent、RAG、pgvector、NER、Embedding',
    categories: ['ai'],
    keywords: ['ai-development', 'ai-pipeline', 'groq', 'ollama', 'embedding', 'rag', 'pgvector', 'ner', 'llm', 'qwen', 'chitchat', '語意', '摘要'],
  },
  '05-DevOps': {
    label: 'DevOps',
    desc: 'Docker、PM2、CI/CD、Git、部署、環境配置',
    categories: ['devops'],
    keywords: ['git', 'docker', 'ci-cd', 'cicd', 'deploy', 'pipeline', 'devops', 'config', 'pm2', 'nas', 'runner', 'env', 'gitops', '部署', 'github-runner', 'worktree'],
  },
  '06-Security': {
    label: 'Security',
    desc: 'httpOnly Cookie、CSRF、Auth、安全審計、安全強化',
    categories: ['security'],
    keywords: ['security', 'auth', 'csrf', 'cookie', 'token', 'httponly', 'audit', 'vulnerability', 'xss', 'injection', '安全', '防護', 'owasp', 'access-control', 'supply-chain'],
  },
  '07-Quality': {
    label: 'Quality',
    desc: 'Checklists、Testing、Performance、Optimization',
    categories: ['quality'],
    keywords: ['test', 'coverage', 'optimization', 'checklist', 'tdd', 'performance', 'quality', 'maintenance', '測試', '效能'],
  },
  '08-Governance': {
    label: 'Governance',
    desc: 'Commands (19)、Hooks (12)、Agents、Skills、Wiki、Knowledge',
    keywords: ['skill', 'agent', 'hook', 'governance', 'command', 'wiki', 'knowledge', 'codewiki', 'inventory'],
  },
};

// ═══════════════════════════════════════════
// YAML Frontmatter 解析器
// ═══════════════════════════════════════════
function parseYamlFrontmatter(content) {
  const normalized = content.replace(/\r\n/g, '\n');
  const match = normalized.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return null;

  const fields = {};
  const lines = match[1].split('\n');
  let currentKey = null;
  let inArray = false;

  for (const line of lines) {
    const arrMatch = line.match(/^\s*-\s+(.+)/);
    if (arrMatch) {
      if (currentKey && inArray) {
        if (!Array.isArray(fields[currentKey])) fields[currentKey] = [];
        fields[currentKey].push(arrMatch[1].trim().replace(/^['"]|['"]$/g, ''));
      }
      continue;
    }
    const kvMatch = line.match(/^([\w_]+):\s*(.*)$/);
    if (kvMatch) {
      currentKey = kvMatch[1];
      const value = kvMatch[2].trim();
      if (value === '' || value === '|' || value === '>') {
        inArray = true;
        fields[currentKey] = [];
      } else if (value.startsWith('[') && value.endsWith(']')) {
        fields[currentKey] = value.slice(1, -1).split(',').map(v => v.trim().replace(/^['"]|['"]$/g, ''));
        inArray = false;
      } else {
        inArray = false;
        fields[currentKey] = value.replace(/^['"]|['"]$/g, '');
      }
    }
  }
  return fields;
}

// 提取摘要
function extractSummary(content, maxLen = 200) {
  const normalized = content.replace(/\r\n/g, '\n');
  const endMatch = normalized.match(/^---\n[\s\S]*?\n---\n/);
  const body = endMatch ? normalized.substring(endMatch[0].length) : normalized;

  const lines = body.split('\n');
  const paragraphs = [];
  let current = [];

  for (const line of lines) {
    if (line.trim() === '' || line.startsWith('#') || line.startsWith('---') || line.startsWith('>') || line.startsWith('|')) {
      if (current.length > 0) {
        paragraphs.push(current.join(' '));
        current = [];
      }
      continue;
    }
    if (line.startsWith('**') && line.endsWith('**')) continue;
    if (line.startsWith('- ') || line.startsWith('* ')) continue;
    if (line.startsWith('```')) continue;
    current.push(line.trim());
  }
  if (current.length > 0) paragraphs.push(current.join(' '));

  const summary = paragraphs[0] || '';
  return summary.length > maxLen ? summary.substring(0, maxLen) + '...' : summary;
}

// 從 Markdown 提取標題
function extractTitle(content, fallback) {
  const match = content.match(/^# (.+)/m);
  return match ? match[1].trim() : fallback;
}

// ═══════════════════════════════════════════
// Source Readers (10 個)
// ═══════════════════════════════════════════
const allCards = [];
const cardRegistry = {};

// 1. readSkills — 從 skills-index.json 讀取
function readSkills() {
  const indexPath = path.join(CLAUDE_DIR, 'generated', 'skills-index.json');
  if (!fs.existsSync(indexPath)) {
    console.log('⚠️  skills-index.json 不存在，請先執行 generate-index.cjs');
    return;
  }
  const index = JSON.parse(fs.readFileSync(indexPath, 'utf-8'));

  for (const skill of index.items) {
    if (skill.path === 'README.md' || skill.path === 'SKILLS_INVENTORY.md') continue;
    const fullPath = path.join(CLAUDE_DIR, 'skills', skill.path);
    if (!fs.existsSync(fullPath)) continue;

    const content = fs.readFileSync(fullPath, 'utf-8');

    allCards.push({
      id: skill.id,
      title: skill.title || skill.id,
      type: 'skill',
      category: skill.category || 'shared',
      maturity: skill.maturity || 'stable',
      related: skill.related || [],
      depends_on: skill.depends_on || [],
      source: `.claude/skills/${skill.path}`,
      summary: skill.description || extractSummary(content),
      triggers: skill.triggers || [],
    });
  }
}

// 2. readRules — 從 .claude/rules/ 讀取 (CK_Missive 為 flat 結構)
function readRules() {
  const rulesDir = path.join(CLAUDE_DIR, 'rules');
  if (!fs.existsSync(rulesDir)) return;

  for (const item of fs.readdirSync(rulesDir)) {
    const full = path.join(rulesDir, item);
    if (!item.endsWith('.md') || item.includes('template')) continue;
    if (fs.statSync(full).isDirectory()) continue;

    const content = fs.readFileSync(full, 'utf-8');
    const title = extractTitle(content, item.replace('.md', ''));

    allCards.push({
      id: `rule-${item.replace('.md', '')}`,
      title,
      type: 'rule',
      category: inferCategoryFromContent(item, content),
      maturity: 'stable',
      related: [],
      depends_on: [],
      source: `.claude/rules/${item}`,
      summary: extractSummary(content),
    });
  }
}

// 3. readAgents — 從 agents-index.json 讀取
function readAgents() {
  const indexPath = path.join(CLAUDE_DIR, 'generated', 'agents-index.json');
  if (!fs.existsSync(indexPath)) return;
  const index = JSON.parse(fs.readFileSync(indexPath, 'utf-8'));

  for (const agent of index.items) {
    allCards.push({
      id: `agent-${agent.id}`,
      title: agent.title || agent.id,
      type: 'agent',
      category: agent.category || 'shared',
      maturity: 'stable',
      related: [],
      depends_on: [],
      source: `.claude/agents/${agent.path}`,
      summary: agent.description || '',
    });
  }
}

// 4. readDocs — ADR + Specs + Key docs
function readDocs() {
  // ADR (11 files)
  const adrDir = path.join(PROJECT_ROOT, 'docs', 'adr');
  if (fs.existsSync(adrDir)) {
    for (const file of fs.readdirSync(adrDir)) {
      if (!file.endsWith('.md') || file === 'README.md' || file === 'TEMPLATE.md') continue;
      const content = fs.readFileSync(path.join(adrDir, file), 'utf-8');
      const title = extractTitle(content, file.replace('.md', ''));

      allCards.push({
        id: `adr-${file.replace('.md', '')}`,
        title: `ADR: ${title}`,
        type: 'adr',
        category: inferCategoryFromContent(file, content),
        maturity: 'frozen',
        related: [],
        depends_on: [],
        source: `docs/adr/${file}`,
        summary: extractSummary(content),
      });
    }
  }

  // Specifications (13 files in docs/specifications/)
  const specsDir = path.join(PROJECT_ROOT, 'docs', 'specifications');
  if (fs.existsSync(specsDir)) {
    for (const file of fs.readdirSync(specsDir)) {
      if (!file.endsWith('.md')) continue;
      const content = fs.readFileSync(path.join(specsDir, file), 'utf-8');
      const title = extractTitle(content, file.replace('.md', ''));

      allCards.push({
        id: `spec-${file.replace('.md', '').toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
        title,
        type: 'spec',
        category: inferCategoryFromContent(file, content),
        maturity: 'stable',
        related: [],
        depends_on: [],
        source: `docs/specifications/${file}`,
        summary: extractSummary(content),
      });
    }
  }

  // Key docs (selected important docs from docs/ root)
  const keyDocs = [
    'ARCHITECTURE.md',
    'DATABASE_SCHEMA.md',
    'DEVELOPMENT_GUIDE.md',
    'DEVELOPMENT_STANDARDS.md',
    'DEPLOYMENT_GUIDE.md',
    'PRODUCTION_DEPLOYMENT_GUIDE.md',
    'NAS_DEPLOYMENT_GUIDE.md',
    'ERROR_HANDLING_GUIDE.md',
    'FRONTEND_API_MAPPING.md',
    'CALENDAR_ARCHITECTURE.md',
    'CSV_IMPORT_MAINTENANCE.md',
    'OLLAMA_SETUP_GUIDE.md',
    'SECURITY_AUDIT_REPORT.md',
    'STRUCTURE.md',
    'CONTRIBUTING.md',
    'GITHUB_RUNNER_SETUP.md',
    'ENV_MANAGEMENT_GUIDE.md',
  ];

  for (const file of keyDocs) {
    const filePath = path.join(PROJECT_ROOT, 'docs', file);
    if (!fs.existsSync(filePath)) continue;
    const content = fs.readFileSync(filePath, 'utf-8');
    const title = extractTitle(content, file.replace('.md', ''));

    allCards.push({
      id: `doc-${file.replace('.md', '').toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
      title,
      type: 'doc',
      category: inferCategoryFromContent(file, content),
      maturity: 'stable',
      related: [],
      depends_on: [],
      source: `docs/${file}`,
      summary: extractSummary(content),
    });
  }
}

// 5. readCoreFiles — CLAUDE.md, @AGENT.md
function readCoreFiles() {
  // CLAUDE.md
  const claudePath = path.join(PROJECT_ROOT, 'CLAUDE.md');
  if (fs.existsSync(claudePath)) {
    allCards.push({
      id: 'core-claude',
      title: 'CK_Missive 公文管理系統',
      type: 'core',
      category: 'project',
      maturity: 'stable',
      related: [],
      depends_on: [],
      source: 'CLAUDE.md',
      summary: '乾坤測繪公文管理系統 — FastAPI + PostgreSQL + React + TypeScript + Ant Design + Docker',
    });
  }

  // Service Ports (from CLAUDE.md)
  allCards.push({
    id: 'core-ports',
    title: 'Service Ports',
    type: 'core',
    category: 'project',
    maturity: 'stable',
    related: [],
    depends_on: [],
    source: 'CLAUDE.md',
    summary: 'PostgreSQL:5432, Backend:8000, Frontend:3000, Redis:6379',
    extra: `| 服務 | 端口 |\n|------|------|\n| PostgreSQL | **5432** |\n| Backend (FastAPI) | **8000** |\n| Frontend (Dev) | **3000** |\n| Redis | 6379 |`,
  });

  // @AGENT.md
  const agentPath = path.join(PROJECT_ROOT, '@AGENT.md');
  if (fs.existsSync(agentPath)) {
    const content = fs.readFileSync(agentPath, 'utf-8');
    allCards.push({
      id: 'core-agent',
      title: 'Agent 人格設定',
      type: 'core',
      category: 'project',
      maturity: 'stable',
      related: [],
      depends_on: [],
      source: '@AGENT.md',
      summary: extractSummary(content),
    });
  }
}

// 6. readHooks — .claude/hooks/ (PowerShell + Shell)
function readHooks() {
  const hooksDir = path.join(CLAUDE_DIR, 'hooks');
  if (!fs.existsSync(hooksDir)) return;

  const hookDescriptions = {
    'api-serialization-check.ps1': { event: 'PostToolUse', desc: 'API 序列化格式檢查' },
    'auto-approve.ps1': { event: 'PermissionRequest', desc: '自動同意唯讀操作' },
    'link-id-check.ps1': { event: 'PostToolUse', desc: 'Link ID 欄位檢查' },
    'link-id-validation.ps1': { event: 'PreToolUse', desc: 'Link ID 驗證' },
    'performance-check.ps1': { event: 'PostToolUse', desc: '效能指標檢查' },
    'post-write-lint.sh': { event: 'PostToolUse(Edit)', desc: '寫入後自動 lint 修復' },
    'python-lint.ps1': { event: 'PostToolUse', desc: 'Python 程式碼 lint 檢查' },
    'route-sync-check.ps1': { event: 'PostToolUse', desc: '路由同步檢查' },
    'session-init.sh': { event: 'SessionStart', desc: '對話初始化載入上下文' },
    'session-start.ps1': { event: 'SessionStart', desc: '載入分支/提交/動態指標' },
    'typescript-check.ps1': { event: 'PostToolUse', desc: 'TypeScript 類型檢查' },
    'validate-file-location.ps1': { event: 'PreToolUse(Write)', desc: '驗證檔案放置位置' },
  };

  for (const file of fs.readdirSync(hooksDir)) {
    if (file === 'README.md') continue;
    if (!file.endsWith('.ps1') && !file.endsWith('.sh') && !file.endsWith('.js')) continue;

    const info = hookDescriptions[file] || { event: 'Unknown', desc: file };
    const ext = path.extname(file).replace('.', '');

    allCards.push({
      id: `hook-${file.replace(/\.(ps1|sh|js)$/, '')}`,
      title: `Hook: ${info.event} — ${file}`,
      type: 'hook',
      category: 'governance',
      maturity: 'stable',
      related: [],
      depends_on: [],
      source: `.claude/hooks/${file}`,
      summary: `${info.desc} (${ext.toUpperCase()})`,
    });
  }
}

// 7. readCommands — 從 commands-index.json 讀取 (CK_Missive 獨有)
function readCommands() {
  const indexPath = path.join(CLAUDE_DIR, 'generated', 'commands-index.json');
  if (!fs.existsSync(indexPath)) return;
  const index = JSON.parse(fs.readFileSync(indexPath, 'utf-8'));

  for (const cmd of index.items) {
    const fullPath = path.join(CLAUDE_DIR, 'commands', cmd.path);
    if (!fs.existsSync(fullPath)) continue;
    const content = fs.readFileSync(fullPath, 'utf-8');

    allCards.push({
      id: `command-${cmd.id}`,
      title: `Command: /${cmd.path.replace('.md', '').replace(/\\/g, '/')}`,
      type: 'command',
      category: 'governance',
      maturity: 'stable',
      related: [],
      depends_on: [],
      source: `.claude/commands/${cmd.path}`,
      summary: cmd.description || extractSummary(content),
      triggers: cmd.triggers || [],
    });
  }
}

// 8. readDiagrams — docs/diagrams/ (CK_Missive 獨有)
function readDiagrams() {
  const diagramDir = path.join(PROJECT_ROOT, 'docs', 'diagrams');
  if (!fs.existsSync(diagramDir)) return;

  for (const file of fs.readdirSync(diagramDir)) {
    if (!file.endsWith('.md') || file === 'README.md') continue;
    const content = fs.readFileSync(path.join(diagramDir, file), 'utf-8');
    const title = extractTitle(content, file.replace('.md', ''));

    // 檢測 Mermaid 圖表類型
    const mermaidMatch = content.match(/```mermaid\n(\w+)/);
    const diagramType = mermaidMatch ? mermaidMatch[1] : 'unknown';

    allCards.push({
      id: `diagram-${file.replace('.md', '')}`,
      title: `Diagram: ${title}`,
      type: 'diagram',
      category: inferCategoryFromContent(file, content),
      maturity: 'stable',
      related: [],
      depends_on: [],
      source: `docs/diagrams/${file}`,
      summary: `${diagramType} 圖表 — ${extractSummary(content)}`,
    });
  }
}

// 9. readChecklists — MANDATORY_CHECKLIST.md + docs/ checklists (CK_Missive 獨有)
function readChecklists() {
  // Main mandatory checklist — 拆分各節
  const mandatoryPath = path.join(CLAUDE_DIR, 'MANDATORY_CHECKLIST.md');
  if (fs.existsSync(mandatoryPath)) {
    const content = fs.readFileSync(mandatoryPath, 'utf-8');

    // 找到所有 ## 節
    const sections = content.split(/\n(?=## )/);
    let checklistCount = 0;

    for (const section of sections) {
      const titleMatch = section.match(/^## (.+)/);
      if (!titleMatch) continue;
      const sectionTitle = titleMatch[1].trim();

      // 計算檢查項數量
      const checkItems = (section.match(/- \[[ x]\]/g) || []).length;
      if (checkItems === 0) continue;

      checklistCount++;
      const sectionId = sectionTitle.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

      allCards.push({
        id: `checklist-mandatory-${sectionId}`,
        title: `Checklist: ${sectionTitle}`,
        type: 'checklist',
        category: 'quality',
        maturity: 'stable',
        related: [],
        depends_on: [],
        source: '.claude/MANDATORY_CHECKLIST.md',
        summary: `${checkItems} 項檢查項目`,
      });
    }

    // 如果沒有找到子節，就整體當一張卡片
    if (checklistCount === 0) {
      allCards.push({
        id: 'checklist-mandatory',
        title: 'MANDATORY_CHECKLIST',
        type: 'checklist',
        category: 'quality',
        maturity: 'stable',
        related: [],
        depends_on: [],
        source: '.claude/MANDATORY_CHECKLIST.md',
        summary: extractSummary(content),
      });
    }
  }

  // Additional checklists in docs/
  const additionalChecklists = [
    'DEPLOYMENT_CHECKLIST.md',
    'PRODUCTION_SECURITY_CHECKLIST.md',
    'SYSTEM_CONFIG_CHECKLIST.md',
  ];

  for (const file of additionalChecklists) {
    const filePath = path.join(PROJECT_ROOT, 'docs', file);
    if (!fs.existsSync(filePath)) continue;
    const content = fs.readFileSync(filePath, 'utf-8');
    const title = extractTitle(content, file.replace('.md', ''));
    const checkItems = (content.match(/- \[[ x]\]/g) || []).length;

    allCards.push({
      id: `checklist-${file.replace('.md', '').toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
      title: `Checklist: ${title}`,
      type: 'checklist',
      category: file.includes('SECURITY') ? 'security' : 'quality',
      maturity: 'stable',
      related: [],
      depends_on: [],
      source: `docs/${file}`,
      summary: `${checkItems} 項檢查項目 — ${extractSummary(content)}`,
    });
  }
}

// 10. readWiki — docs/wiki/ (CK_Missive 獨有)
function readWiki() {
  const wikiDir = path.join(PROJECT_ROOT, 'docs', 'wiki');
  if (!fs.existsSync(wikiDir)) return;

  for (const file of fs.readdirSync(wikiDir)) {
    if (!file.endsWith('.md') || file === '_Sidebar.md') continue;
    const content = fs.readFileSync(path.join(wikiDir, file), 'utf-8');
    const title = extractTitle(content, file.replace('.md', '').replace(/-/g, ' '));

    allCards.push({
      id: `wiki-${file.replace('.md', '').toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
      title: `Wiki: ${title}`,
      type: 'wiki',
      category: inferCategoryFromContent(file, content),
      maturity: 'stable',
      related: [],
      depends_on: [],
      source: `docs/wiki/${file}`,
      summary: extractSummary(content),
    });
  }
}

// ═══════════════════════════════════════════
// Category / Section 推斷
// ═══════════════════════════════════════════
function inferCategoryFromContent(filename, content) {
  const lower = (filename + ' ' + (content || '').substring(0, 500)).toLowerCase();

  // AI keywords (CK_Missive 特有)
  if (lower.includes('groq') || lower.includes('ollama') || lower.includes('embedding') ||
      lower.includes('rag') || lower.includes('pgvector') || lower.includes('ner') ||
      lower.includes('qwen') || lower.includes('ai-pipeline') || lower.includes('four-layer-ai')) return 'ai';

  // Security keywords (CK_Missive 特有)
  if (lower.includes('security') || lower.includes('auth') || lower.includes('csrf') ||
      lower.includes('cookie') || lower.includes('httponly') || lower.includes('vulnerability') ||
      lower.includes('audit') || lower.includes('xss') || lower.includes('injection')) return 'security';

  // Backend
  if (lower.includes('api') || lower.includes('schema') || lower.includes('database') ||
      lower.includes('alembic') || lower.includes('repository') || lower.includes('fastapi') ||
      lower.includes('pydantic') || lower.includes('serialization') || lower.includes('csv')) return 'backend';

  // Frontend
  if (lower.includes('react') || lower.includes('frontend') || lower.includes('component') ||
      lower.includes('typescript') || lower.includes('antd') || lower.includes('rwd') ||
      lower.includes('vite') || lower.includes('eslint')) return 'react';

  // DevOps
  if (lower.includes('deploy') || lower.includes('docker') || lower.includes('ci') ||
      lower.includes('git') || lower.includes('runner') || lower.includes('nas') ||
      lower.includes('env') || lower.includes('config')) return 'devops';

  // Quality
  if (lower.includes('test') || lower.includes('checklist') || lower.includes('optimization') ||
      lower.includes('performance')) return 'quality';

  return 'shared';
}

function assignSection(card) {
  // Core files → 00-Overview
  if (card.type === 'core') return '00-Overview';

  // ADR + Diagrams → 01-Architecture
  if (card.type === 'adr') return '01-Architecture';
  if (card.type === 'diagram') return '01-Architecture';

  // Hooks + Commands → 08-Governance
  if (card.type === 'hook') return '08-Governance';
  if (card.type === 'command') return '08-Governance';

  // Wiki → 依內容分配
  if (card.type === 'wiki') {
    if (card.category === 'react') return '03-Frontend';
    if (card.category === 'backend') return '02-Backend';
    if (card.category === 'ai') return '04-AI';
    return '08-Governance';
  }

  // Checklists → 07-Quality (except security ones)
  if (card.type === 'checklist') {
    if (card.category === 'security') return '06-Security';
    return '07-Quality';
  }

  // DevOps 優先判定（防止 DevOps 卡片被 AI/Backend 搶走）
  if (card.type === 'doc' || card.type === 'spec') {
    const devopsText = `${card.id} ${card.title} ${card.summary}`.toLowerCase();
    const devopsSignals = ['ci/cd', 'cicd', 'ci-cd', '部署', 'deploy', 'docker', 'pm2', 'nas', 'runner', 'github-runner', 'worktree', '自動部署', 'production'];
    const devopsScore = devopsSignals.filter(kw => devopsText.includes(kw)).length;
    if (devopsScore >= 2) return '05-DevOps';
  }

  // Skills/Agents/Rules/Docs → by category
  for (const [sectionId, config] of Object.entries(SECTIONS)) {
    if (config.categories && config.categories.includes(card.category)) return sectionId;
  }

  // Keyword-based fallback
  const searchText = `${card.id} ${card.title} ${card.summary}`.toLowerCase();
  for (const [sectionId, config] of Object.entries(SECTIONS)) {
    if (config.keywords && config.keywords.some(kw => searchText.includes(kw))) return sectionId;
  }

  // Default
  if (card.category === 'project' || card.category === 'governance') return '08-Governance';
  if (card.category === 'quality') return '07-Quality';
  if (card.category === 'devops') return '05-DevOps';
  return '07-Quality';
}

// ═══════════════════════════════════════════
// Relationship Inference Engine
// ═══════════════════════════════════════════

/**
 * 建立 source path → card id 的反向索引
 * 例如 '.claude/skills/ai-development.md' → 'ai-development'
 */
function buildSourceIndex() {
  const sourceToId = {};
  for (const card of allCards) {
    if (!card.source) continue;
    // 完整路徑
    sourceToId[card.source] = card.id;
    // 不含前綴的路徑變體
    const variants = [
      card.source,
      card.source.replace(/^\.claude\//, ''),
      card.source.replace(/^\.\//, ''),
      card.source.replace(/\\/g, '/'),
    ];
    for (const v of variants) {
      sourceToId[v] = card.id;
    }
  }
  return sourceToId;
}

/**
 * 從檔案內容中掃描所有檔案路徑引用
 * 匹配模式：
 *   - `.claude/skills/xxx.md`
 *   - `docs/xxx.md`
 *   - `docs/specifications/xxx.md`
 *   - `docs/adr/xxx.md`
 *   - `docs/wiki/xxx.md`
 *   - `docs/diagrams/xxx.md`
 *   - `.claude/commands/xxx.md`
 *   - `.claude/agents/xxx.md`
 *   - `.claude/hooks/xxx.ps1`
 *   - `.claude/rules/xxx.md`
 *   - `.claude/MANDATORY_CHECKLIST.md`
 */
function extractFileReferences(content) {
  const refs = new Set();
  // 匹配 backtick 或裸路徑中的檔案引用
  const patterns = [
    /`(\.claude\/(?:skills|agents|commands|hooks|rules)\/[^\s`]+\.(?:md|ps1|sh|js))`/g,
    /`(\.claude\/[A-Z][A-Z_]+\.md)`/g,
    /`(docs\/(?:adr|wiki|diagrams|specifications)\/[^\s`]+\.md)`/g,
    /`(docs\/[A-Z][A-Z_]+\.md)`/g,
    // 不在 backtick 內的路徑 (表格、列表中)
    /(?:^|\s|：|:|\|)(\.claude\/(?:skills|agents|commands|hooks|rules)\/[^\s|,)]+\.(?:md|ps1|sh|js))/gm,
    /(?:^|\s|：|:|\|)(\.claude\/[A-Z][A-Z_]+\.md)/gm,
    /(?:^|\s|：|:|\|)(docs\/(?:adr|wiki|diagrams|specifications)\/[^\s|,)]+\.md)/gm,
    /(?:^|\s|：|:|\|)(docs\/[A-Z][A-Z_]+\.md)/gm,
    // Markdown 連結 [text](path)
    /\]\((\.\.\/[^\s)]+\.md)\)/g,
    /\]\((\.\/([\w-]+)\.md)\)/g,
  ];

  for (const pattern of patterns) {
    let match;
    while ((match = pattern.exec(content)) !== null) {
      let ref = match[1].trim();
      // 正規化路徑
      ref = ref.replace(/\\/g, '/');
      refs.add(ref);
    }
  }

  // ADR 交叉引用 (ADR-0001 → docs/adr/0001-*.md)
  const adrRefs = content.matchAll(/ADR-(\d{4})/g);
  for (const m of adrRefs) {
    const num = m[1];
    // 找到對應的 adr card
    for (const card of allCards) {
      if (card.type === 'adr' && card.source && card.source.includes(num)) {
        refs.add(card.source);
      }
    }
  }

  // Command → Skill 引用 (Invoke the xxx skill)
  const invokeMatch = content.match(/Invoke the ([\w:-]+) skill/);
  if (invokeMatch) {
    const skillRef = invokeMatch[1].replace(/:/g, '/');
    // 嘗試匹配 _shared 路徑
    for (const card of allCards) {
      if (card.type === 'skill' && card.source && card.source.includes(skillRef)) {
        refs.add(card.source);
      }
    }
  }

  return [...refs];
}

/**
 * 為所有卡片推斷關聯
 */
function buildRelationships() {
  const sourceIndex = buildSourceIndex();
  let totalLinks = 0;

  for (const card of allCards) {
    if (!card.source) continue;

    // 讀取源檔案
    const fullPath = path.join(PROJECT_ROOT, card.source);
    if (!fs.existsSync(fullPath)) continue;

    const content = fs.readFileSync(fullPath, 'utf-8');
    const refs = extractFileReferences(content);

    for (const ref of refs) {
      // 嘗試多種路徑變體解析目標 card
      const targetId = sourceIndex[ref]
        || sourceIndex[ref.replace(/^\.\//, '')]
        || sourceIndex[ref.replace(/^\.\.\//, 'docs/')];

      if (!targetId || targetId === card.id) continue;

      // 避免重複
      if (!card.related.includes(targetId)) {
        card.related.push(targetId);
        totalLinks++;
      }
    }
  }

  return totalLinks;
}

/**
 * Checklist 主題分群 — 為同域 Checklist 建立互連
 * 28 張 Checklist 按前端/後端/安全/DevOps/通用分群，組內互相建立 related
 */
// Checklist 分群：按首字母匹配 (ID 格式: checklist-mandatory-X...)
const CHECKLIST_GROUPS = {
  frontend: ['a', 'c', 'i', 'l', 'n', 'o', 't', 'x'],
  backend:  ['b', 'e', 'f', 'j', 'k', 'p', 'q'],
  security: ['d', 's', 'v'],
  devops:   ['r', 'w'],
  quality:  ['g', 'h', 'm', 'u'],
};

function getChecklistLetter(cardId) {
  // checklist-mandatory-a → 'a', checklist-mandatory-b-api → 'b'
  const match = cardId.match(/^checklist-mandatory-([a-z])/);
  return match ? match[1] : null;
}

function buildChecklistGroupLinks() {
  let links = 0;
  const checklistCards = allCards.filter(c => c.type === 'checklist' && c.id.startsWith('checklist-mandatory-'));

  for (const [, letters] of Object.entries(CHECKLIST_GROUPS)) {
    // 找出屬於此 group 的卡片
    const groupCards = checklistCards.filter(c => {
      const letter = getChecklistLetter(c.id);
      return letter && letters.includes(letter);
    });

    // 組內互相連結
    for (let i = 0; i < groupCards.length; i++) {
      for (let j = i + 1; j < groupCards.length; j++) {
        if (!groupCards[i].related.includes(groupCards[j].id)) {
          groupCards[i].related.push(groupCards[j].id);
          links++;
        }
        if (!groupCards[j].related.includes(groupCards[i].id)) {
          groupCards[j].related.push(groupCards[i].id);
          links++;
        }
      }
    }
  }
  return links;
}

/**
 * 語義關聯推斷 — 同 section + 同 category 的卡片若有共同關鍵字則建立 "See Also"
 * 從標題和 summary 提取有意義的中文/英文關鍵字，計算 Jaccard 相似度
 */
function extractKeywords(text) {
  if (!text) return new Set();
  const lower = text.toLowerCase();
  // 英文：提取 3+ 字元的單字（排除常見停用詞）
  const stopWords = new Set(['the', 'and', 'for', 'that', 'this', 'with', 'from', 'are', 'not', 'but', 'has', 'was', 'will', 'can', 'use', 'used', 'using', 'type', 'all']);
  const enWords = lower.match(/[a-z][a-z0-9_-]{2,}/g) || [];
  const meaningful = enWords.filter(w => !stopWords.has(w));
  // 中文：提取 2-4 字的詞組
  const cnWords = text.match(/[\u4e00-\u9fa5]{2,4}/g) || [];
  return new Set([...meaningful, ...cnWords]);
}

function buildSemanticRelationships() {
  let links = 0;
  const MAX_SEMANTIC_LINKS = 5; // 每張卡片最多加 5 條語義連結

  // 按 section 分組
  const bySection = {};
  for (const card of allCards) {
    if (!card.section) continue;
    if (!bySection[card.section]) bySection[card.section] = [];
    bySection[card.section].push(card);
  }

  // 預先提取每張卡片的關鍵字
  const cardKeywords = new Map();
  for (const card of allCards) {
    cardKeywords.set(card.id, extractKeywords(`${card.title} ${card.summary}`));
  }

  for (const [, sectionCards] of Object.entries(bySection)) {
    for (let i = 0; i < sectionCards.length; i++) {
      const cardA = sectionCards[i];
      const kwA = cardKeywords.get(cardA.id);
      if (kwA.size < 2) continue;

      // 計算此卡片可新增的語義連結數量
      let added = 0;
      const candidates = [];

      for (let j = 0; j < sectionCards.length; j++) {
        if (i === j) continue;
        const cardB = sectionCards[j];
        if (cardA.related.includes(cardB.id)) continue; // 已有直接連結

        const kwB = cardKeywords.get(cardB.id);
        if (kwB.size < 2) continue;

        // Jaccard 相似度
        const intersection = new Set([...kwA].filter(k => kwB.has(k)));
        const union = new Set([...kwA, ...kwB]);
        const similarity = intersection.size / union.size;

        // 同 category 降低閾值（0.15），跨 category 需更高（0.25）
        const threshold = cardA.category === cardB.category ? 0.15 : 0.25;
        if (similarity >= threshold && intersection.size >= 2) {
          candidates.push({ card: cardB, similarity });
        }
      }

      // 按相似度排序，取 top-N
      candidates.sort((a, b) => b.similarity - a.similarity);
      for (const { card: cardB } of candidates.slice(0, MAX_SEMANTIC_LINKS)) {
        if (!cardA.related.includes(cardB.id)) {
          cardA.related.push(cardB.id);
          links++;
          added++;
        }
        if (!cardB.related.includes(cardA.id)) {
          cardB.related.push(cardA.id);
          links++;
        }
      }
    }
  }

  return links;
}

// ═══════════════════════════════════════════
// Card Generation
// ═══════════════════════════════════════════
function sanitizeFilename(title) {
  return title
    .replace(/[<>:"/\\|?*]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .substring(0, 80);
}

function generateCardContent(card) {
  const tags = [
    'project/CK_Missive',
    `section/${card.section}`,
    `category/${card.category}`,
    `maturity/${card.maturity}`,
    `type/${card.type}`,
  ];

  // 共用 Skill/Agent → 跨專案標籤
  if (card.source && card.source.includes('_shared/')) {
    tags.push('cross-project/shared');
  }

  const relatedLinks = (card.related || [])
    .map(relId => {
      const target = cardRegistry[relId];
      return target ? `- [[${target}]]` : `- ${relId}`;
    })
    .join('\n');

  const dependsLinks = (card.depends_on || [])
    .map(depId => {
      const target = cardRegistry[depId];
      return target ? `- [[${target}]] (prerequisite)` : `- ${depId} (prerequisite)`;
    })
    .join('\n');

  let content = `---
tags:
${tags.map(t => `  - ${t}`).join('\n')}
aliases:
  - ${card.id}
---

# ${card.title}

**Type**: ${card.type} | **Category**: ${card.category} | **Maturity**: ${card.maturity}
**Source**: \`${card.source}\`

## Summary

${card.summary}
`;

  if (card.extra) {
    content += `\n${card.extra}\n`;
  }

  if (card.triggers && card.triggers.length > 0) {
    content += `\n## Triggers\n\n${card.triggers.map(t => `\`${t}\``).join(' ')}\n`;
  }

  if (relatedLinks || dependsLinks) {
    content += '\n## Related\n\n';
    if (dependsLinks) content += dependsLinks + '\n';
    if (relatedLinks) content += relatedLinks + '\n';
  }

  return content;
}

// ═══════════════════════════════════════════
// Index & Relationship Map
// ═══════════════════════════════════════════
function generateIndex(cardsBySection) {
  let content = `---
tags:
  - type/index
---

# CK_Missive Knowledge Map

**Generated**: ${new Date().toISOString().slice(0, 10)}
**Total Cards**: ${allCards.length}
**Sections**: ${Object.keys(cardsBySection).length}

---

`;

  for (const [sectionId, config] of Object.entries(SECTIONS)) {
    const cards = cardsBySection[sectionId] || [];
    content += `## [[${config.label}]] (${sectionId})\n\n`;
    content += `${config.desc}\n\n`;
    for (const card of cards) {
      content += `- [[${card.title}]] *(${card.type})*\n`;
    }
    content += '\n';
  }

  return content;
}

function generateRelationshipMap() {
  let content = `---
tags:
  - type/relationship-map
---

# Relationship Map

**Generated**: ${new Date().toISOString().slice(0, 10)}

## Adjacency List

`;

  for (const card of allCards) {
    const links = [...(card.related || []), ...(card.depends_on || [])];
    if (links.length === 0) continue;

    const resolvedLinks = links
      .map(id => {
        const target = cardRegistry[id];
        return target ? `[[${target}]]` : id;
      })
      .join(', ');

    content += `- **[[${card.title}]]** → ${resolvedLinks}\n`;
  }

  // Inbound link tracking (雙向連結)
  const inboundLinks = {};
  for (const card of allCards) {
    for (const relId of (card.related || [])) {
      if (!inboundLinks[relId]) inboundLinks[relId] = [];
      inboundLinks[relId].push(card.id);
    }
  }

  // Type statistics
  const typeCounts = {};
  for (const card of allCards) {
    typeCounts[card.type] = (typeCounts[card.type] || 0) + 1;
  }

  const cardsWithRels = allCards.filter(c => (c.related?.length || 0) + (c.depends_on?.length || 0) > 0).length;
  const orphanCards = allCards.filter(c =>
    (c.related?.length || 0) === 0 && (c.depends_on?.length || 0) === 0 && !(inboundLinks[c.id]?.length)
  );

  content += `\n## Statistics\n\n`;
  content += `- Total cards: ${allCards.length}\n`;
  for (const [type, count] of Object.entries(typeCounts).sort((a, b) => b[1] - a[1])) {
    content += `- ${type}: ${count}\n`;
  }
  content += `- Cards with outbound links: ${cardsWithRels}\n`;
  content += `- Cards with inbound links: ${Object.keys(inboundLinks).length}\n`;
  content += `- True orphans (no links at all): ${orphanCards.length}\n`;
  content += `- Relationship density: ${Math.round(cardsWithRels / allCards.length * 100)}%\n`;

  // Top-15 Hub Cards
  content += `\n## Top-15 Hub Cards (most connections)\n\n`;
  const hubScores = allCards.map(c => ({
    id: c.id,
    title: c.title,
    outbound: (c.related?.length || 0) + (c.depends_on?.length || 0),
    inbound: (inboundLinks[c.id] || []).length,
    total: (c.related?.length || 0) + (c.depends_on?.length || 0) + (inboundLinks[c.id] || []).length,
  })).sort((a, b) => b.total - a.total);

  content += `| Rank | Card | Outbound | Inbound | Total |\n`;
  content += `|------|------|----------|---------|-------|\n`;
  for (let i = 0; i < Math.min(15, hubScores.length); i++) {
    const h = hubScores[i];
    content += `| ${i + 1} | [[${h.title}]] | ${h.outbound} | ${h.inbound} | ${h.total} |\n`;
  }

  // Orphan list (for maintenance)
  if (orphanCards.length > 0) {
    content += `\n## Orphan Cards (${orphanCards.length})\n\n`;
    content += `> 以下卡片無任何連結，建議檢視是否需要補充關聯。\n\n`;
    for (const card of orphanCards) {
      content += `- ${card.title} (${card.section}/${card.type})\n`;
    }
  }

  return content;
}

// ═══════════════════════════════════════════
// Main
// ═══════════════════════════════════════════
console.log('🗺️  CK_Missive Heptabase Knowledge Map Generator\n');
console.log('═══════════════════════════════════════════\n');

// Staleness check (early exit)
if (IF_STALE && !checkStaleness()) {
  console.log('✅ 知識地圖已是最新，無需重建。');
  process.exit(0);
}

// Load existing cards for diff (before clean)
const existingCards = DIFF_MODE ? loadExistingCards() : {};
if (DIFF_MODE) {
  console.log(`📊 已載入 ${Object.keys(existingCards).length} 張舊卡片用於比較\n`);
}

// Clean output directory
if (fs.existsSync(OUTPUT_DIR)) {
  if (CLEAN) {
    fs.rmSync(OUTPUT_DIR, { recursive: true });
    console.log('🧹 已清除舊的知識地圖\n');
  }
}

// Read all 10 sources
console.log('📖 讀取知識源...');

readSkills();
const skillCount = allCards.length;
console.log(`   Skills: ${skillCount}`);

readRules();
const ruleCount = allCards.length - skillCount;
console.log(`   Rules: ${ruleCount}`);

readAgents();
const agentCount = allCards.length - skillCount - ruleCount;
console.log(`   Agents: ${agentCount}`);

readDocs();
const docCount = allCards.length - skillCount - ruleCount - agentCount;
console.log(`   Docs (ADR+Specs+Key): ${docCount}`);

readCoreFiles();
const coreCount = allCards.length - skillCount - ruleCount - agentCount - docCount;
console.log(`   Core: ${coreCount}`);

readHooks();
const hookCount = allCards.length - skillCount - ruleCount - agentCount - docCount - coreCount;
console.log(`   Hooks: ${hookCount}`);

readCommands();
const cmdCount = allCards.length - skillCount - ruleCount - agentCount - docCount - coreCount - hookCount;
console.log(`   Commands: ${cmdCount}`);

readDiagrams();
const diagCount = allCards.length - skillCount - ruleCount - agentCount - docCount - coreCount - hookCount - cmdCount;
console.log(`   Diagrams: ${diagCount}`);

readChecklists();
const checkCount = allCards.length - skillCount - ruleCount - agentCount - docCount - coreCount - hookCount - cmdCount - diagCount;
console.log(`   Checklists: ${checkCount}`);

readWiki();
const wikiCount = allCards.length - skillCount - ruleCount - agentCount - docCount - coreCount - hookCount - cmdCount - diagCount - checkCount;
console.log(`   Wiki: ${wikiCount}`);

console.log(`\n📊 總計: ${allCards.length} 張卡片\n`);

// Build card registry
for (const card of allCards) {
  cardRegistry[card.id] = card.title;
  if (card.type === 'skill' || card.type === 'agent') {
    const shortId = card.id
      .replace(/^_shared-shared-/, '')
      .replace(/^_shared-ai-/, '')
      .replace(/^_shared-backend-/, '')
      .replace(/^_shared-react-/, '')
      .replace(/^_shared-/, '')
      .replace(/^shared-/, '')
      .replace(/^agent-/, '')
      .replace(/^agent-_shared-/, '');
    if (!cardRegistry[shortId]) cardRegistry[shortId] = card.title;
    const superShort = shortId.replace(/^superpowers-/, '');
    if (!cardRegistry[superShort]) cardRegistry[superShort] = card.title;
  }
}

// Assign sections
for (const card of allCards) {
  card.section = assignSection(card);
}

// Build relationships (三層關聯推斷)
console.log('🔗 推斷卡片關聯...');
const fileLinks = buildRelationships();
console.log(`   檔案引用: ${fileLinks} 條`);
const checklistLinks = buildChecklistGroupLinks();
console.log(`   Checklist 分群: ${checklistLinks} 條`);
const semanticLinks = buildSemanticRelationships();
console.log(`   語義相似: ${semanticLinks} 條`);
const totalLinks = fileLinks + checklistLinks + semanticLinks;
const cardsWithLinks = allCards.filter(c => c.related.length > 0).length;
const orphanCount = allCards.length - cardsWithLinks;
console.log(`   📊 總計 ${totalLinks} 條關聯 (涵蓋 ${cardsWithLinks}/${allCards.length} 張卡片, 孤島 ${orphanCount})\n`);

// Group by section
const cardsBySection = {};
for (const card of allCards) {
  if (!cardsBySection[card.section]) cardsBySection[card.section] = [];
  cardsBySection[card.section].push(card);
}

// Create output directories
console.log('📁 生成目錄結構...');
fs.mkdirSync(OUTPUT_DIR, { recursive: true });
for (const sectionId of Object.keys(SECTIONS)) {
  fs.mkdirSync(path.join(OUTPUT_DIR, sectionId), { recursive: true });
}

// Write cards
console.log('📝 生成卡片...\n');
let totalWritten = 0;
for (const [sectionId, cards] of Object.entries(cardsBySection)) {
  const sectionLabel = SECTIONS[sectionId]?.label || sectionId;
  console.log(`   ${sectionId} (${sectionLabel}): ${cards.length} 張`);

  for (const card of cards) {
    const filename = sanitizeFilename(card.title) + '.md';
    const filePath = path.join(OUTPUT_DIR, sectionId, filename);
    fs.writeFileSync(filePath, generateCardContent(card), 'utf-8');
    totalWritten++;
  }
}

// Write section guide cards (導覽卡)
console.log('\n📋 生成 Section 導覽卡...');
for (const [sectionId, config] of Object.entries(SECTIONS)) {
  const sectionCards = cardsBySection[sectionId] || [];
  if (sectionCards.length === 0) continue;

  // 依 type 分類
  const byType = {};
  for (const c of sectionCards) {
    if (!byType[c.type]) byType[c.type] = [];
    byType[c.type].push(c);
  }

  let guideContent = `---\ntags:\n  - project/CK_Missive\n  - section/${sectionId}\n  - type/guide\naliases:\n  - guide-${sectionId}\n---\n\n`;
  guideContent += `# ${config.label} Guide\n\n`;
  guideContent += `**Section**: ${sectionId} | **Cards**: ${sectionCards.length}\n\n`;
  guideContent += `${config.desc}\n\n`;

  for (const [type, cards] of Object.entries(byType).sort((a, b) => b[1].length - a[1].length)) {
    guideContent += `## ${type.charAt(0).toUpperCase() + type.slice(1)} (${cards.length})\n\n`;
    for (const c of cards.sort((a, b) => a.title.localeCompare(b.title))) {
      guideContent += `- [[${c.title}]]`;
      if (c.maturity !== 'stable') guideContent += ` _(${c.maturity})_`;
      guideContent += '\n';
    }
    guideContent += '\n';
  }

  const guidePath = path.join(OUTPUT_DIR, sectionId, `_${config.label} Guide.md`);
  fs.writeFileSync(guidePath, guideContent, 'utf-8');
  totalWritten++;
}

// Write index
const indexContent = generateIndex(cardsBySection);
fs.writeFileSync(path.join(OUTPUT_DIR, '_Index.md'), indexContent, 'utf-8');

// Write relationship map
const relMapContent = generateRelationshipMap();
fs.writeFileSync(path.join(OUTPUT_DIR, '_Relationship-Map.md'), relMapContent, 'utf-8');

// Write Mermaid dependency graph
console.log('🔀 生成 Mermaid 依賴圖...');
let mermaidContent = `---\ntags:\n  - type/dependency-graph\n---\n\n# Dependency Graph\n\n`;
mermaidContent += `**Generated**: ${new Date().toISOString().slice(0, 10)}\n\n`;
mermaidContent += `## Skill → Command → Hook 依賴鏈\n\n\`\`\`mermaid\ngraph LR\n`;

// 收集 Command→Skill 和 Hook→Skill 關聯
const commandCards = allCards.filter(c => c.type === 'command');
const hookCards = allCards.filter(c => c.type === 'hook');
const skillCards = allCards.filter(c => c.type === 'skill' && !c.source?.includes('_shared/'));
const mermaidNodes = new Set();
const mermaidEdges = new Set();

// 簡化節點 ID（Mermaid 不支持中文 node id）
function mNode(id) { return id.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 30); }
function mLabel(title) { return title.substring(0, 25).replace(/"/g, "'"); }

for (const cmd of commandCards) {
  const cmdNode = mNode(cmd.id);
  mermaidNodes.add(`  ${cmdNode}["📋 ${mLabel(cmd.title)}"]`);
  for (const relId of (cmd.related || [])) {
    const target = allCards.find(c => c.id === relId);
    if (target && target.type === 'skill') {
      const targetNode = mNode(target.id);
      mermaidNodes.add(`  ${targetNode}["⚡ ${mLabel(target.title)}"]`);
      mermaidEdges.add(`  ${cmdNode} --> ${targetNode}`);
    }
  }
}

for (const hook of hookCards) {
  const hookNode = mNode(hook.id);
  mermaidNodes.add(`  ${hookNode}["🪝 ${mLabel(hook.title)}"]`);
  for (const relId of (hook.related || [])) {
    const target = allCards.find(c => c.id === relId);
    if (target && target.type === 'skill') {
      const targetNode = mNode(target.id);
      mermaidNodes.add(`  ${targetNode}["⚡ ${mLabel(target.title)}"]`);
      mermaidEdges.add(`  ${hookNode} -.-> ${targetNode}`);
    } else if (target && target.type === 'command') {
      const targetNode = mNode(target.id);
      mermaidEdges.add(`  ${hookNode} -.-> ${targetNode}`);
    }
  }
}

for (const node of mermaidNodes) mermaidContent += node + '\n';
for (const edge of mermaidEdges) mermaidContent += edge + '\n';
mermaidContent += `\`\`\`\n\n`;

// Section 概覽圖
mermaidContent += `## Section 概覽\n\n\`\`\`mermaid\ngraph TD\n`;
for (const [sectionId, config] of Object.entries(SECTIONS)) {
  const count = (cardsBySection[sectionId] || []).length;
  mermaidContent += `  ${sectionId.replace(/-/g, '_')}["${config.label}<br/>${count} cards"]\n`;
}
// Overview connects to all
const overviewId = '00_Overview';
for (const sectionId of Object.keys(SECTIONS)) {
  if (sectionId !== '00-Overview') {
    mermaidContent += `  ${overviewId} --> ${sectionId.replace(/-/g, '_')}\n`;
  }
}
mermaidContent += `\`\`\`\n`;

fs.writeFileSync(path.join(OUTPUT_DIR, '_Dependency-Graph.md'), mermaidContent, 'utf-8');

// Diff report
if (DIFF_MODE) {
  const { report, added, modified, deleted } = generateDiffReport(allCards, existingCards);
  fs.writeFileSync(DIFF_REPORT, report, 'utf-8');
  console.log(`\n📊 差異報告:`);
  console.log(`   新增: ${added.length} | 修改: ${modified.length} | 刪除: ${deleted.length} | 未變: ${allCards.length - added.length - modified.length}`);
  console.log(`   報告: ${DIFF_REPORT}`);
}

// Write generation timestamp
writeTimestamp();

console.log(`\n═══════════════════════════════════════════`);
console.log(`\n✅ 知識地圖生成完成！`);
console.log(`   📁 輸出: ${OUTPUT_DIR}`);
console.log(`   📝 卡片: ${totalWritten}`);
console.log(`   📋 索引: _Index.md`);
console.log(`   🔗 關係圖: _Relationship-Map.md`);
if (DIFF_MODE) {
  console.log(`   📊 差異報告: _Diff-Report.md`);
  console.log(`\n💡 Heptabase 增量更新:`);
  console.log(`   1. 檢視 _Diff-Report.md 了解變更`);
  console.log(`   2. 新增卡片：匯入對應 .md 檔案`);
  console.log(`   3. 修改卡片：手動更新 Heptabase 卡片內容`);
} else {
  console.log(`\n💡 首次匯入 Heptabase:`);
  console.log(`   1. 壓縮 docs/knowledge-map/ → .zip`);
  console.log(`   2. Heptabase → Import → Obsidian → 選擇 .zip`);
  console.log(`\n💡 後續更新請使用 --diff 模式:`);
  console.log(`   node .claude/scripts/generate-knowledge-map.cjs --diff`);
}

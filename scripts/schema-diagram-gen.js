#!/usr/bin/env node
/**
 * Schema 圖表產生器 (Schema Diagram Generator)
 *
 * 靜態分析 ORM 模型檔案，產生 Mermaid ER 圖。
 * 不需要啟動後端或匯入 Python 模組。
 *
 * 使用方式：
 *   node scripts/schema-diagram-gen.js                — 輸出 Mermaid 到 stdout
 *   node scripts/schema-diagram-gen.js --output FILE  — 輸出到檔案
 *   node scripts/schema-diagram-gen.js --module core   — 只產生指定模組
 *   node scripts/schema-diagram-gen.js --compact       — 精簡模式（省略欄位）
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

const MODELS_DIR = path.join(ROOT, 'backend/app/extended/models');

// ============================================================
// SQLAlchemy 型別 → Mermaid 型別對照
// ============================================================
const TYPE_MAP = {
  'Integer': 'int',
  'String': 'string',
  'Text': 'text',
  'Float': 'float',
  'Boolean': 'boolean',
  'Date': 'date',
  'DateTime': 'datetime',
  'JSON': 'json',
  'JSONB': 'jsonb',
  'Vector': 'vector',
};

// ============================================================
// 模組描述
// ============================================================
const MODULE_LABELS = {
  'associations': '關聯表',
  'core': '基礎實體',
  'document': '公文模組',
  'calendar': '行事曆模組',
  'system': '系統 + AI',
  'staff': '專案人員',
  'taoyuan': '桃園派工',
  'entity': 'AI 實體提取',
  'knowledge_graph': '知識圖譜',
};

// ============================================================
// 1. 解析 Python ORM Class
// ============================================================
function parseModelFile(content, filename) {
  const models = [];
  const lines = content.split('\n');

  let currentModel = null;
  let inTable = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // --- Class 模型 ---
    const classMatch = line.match(/^class\s+(\w+)\(Base\):/);
    if (classMatch) {
      if (currentModel) models.push(currentModel);
      currentModel = {
        name: classMatch[1],
        tableName: null,
        columns: [],
        foreignKeys: [],
        relationships: [],
        module: filename.replace('.py', ''),
      };
      inTable = null;
      continue;
    }

    // --- Table 定義 (關聯表) ---
    const tableMatch = line.match(/^(\w+)\s*=\s*Table\(/);
    if (tableMatch) {
      if (currentModel) models.push(currentModel);
      currentModel = null;
      inTable = {
        varName: tableMatch[1],
        tableName: null,
        columns: [],
        foreignKeys: [],
        relationships: [],
        module: filename.replace('.py', ''),
        isAssociation: true,
      };
      continue;
    }

    // Table name (字串)
    if (inTable && !inTable.tableName) {
      const tableNameMatch = line.match(/^\s+'([^']+)'/);
      if (tableNameMatch) {
        inTable.tableName = tableNameMatch[1];
        inTable.name = inTable.varName;
      }
    }

    // __tablename__
    if (currentModel) {
      const tableNameMatch = line.match(/__tablename__\s*=\s*["']([^"']+)["']/);
      if (tableNameMatch) {
        currentModel.tableName = tableNameMatch[1];
      }
    }

    // 活動上下文
    const ctx = currentModel || inTable;
    if (!ctx) continue;

    // Column 定義
    const colMatch = line.match(/^\s+(?:(\w+)\s*=\s*)?Column\((\w+)(?:\(([^)]*)\))?/);
    if (colMatch) {
      const colName = colMatch[1] || null;
      const colType = colMatch[2];
      const isPK = line.includes('primary_key=True');
      const isFK = line.includes('ForeignKey');
      const isUnique = line.includes('unique=True');
      const isNullable = line.includes('nullable=True') || (!line.includes('nullable=False') && !isPK);

      // 提取 comment
      const commentMatch = line.match(/comment="([^"]*)"/);
      const comment = commentMatch ? commentMatch[1] : null;

      if (colName) {
        ctx.columns.push({
          name: colName,
          type: TYPE_MAP[colType] || colType.toLowerCase(),
          isPK,
          isFK,
          isUnique,
          comment,
        });
      }

      // ForeignKey 提取
      if (isFK) {
        const fkMatch = line.match(/ForeignKey\(['"]([^'"]+)['"]\)/);
        if (fkMatch) {
          const [fkTable, fkCol] = fkMatch[1].split('.');
          ctx.foreignKeys.push({
            column: colName,
            refTable: fkTable,
            refColumn: fkCol,
          });
        }
      }
      continue;
    }

    // Table() 裡面的 Column（關聯表格式）
    if (inTable) {
      const tableColMatch = line.match(/^\s+Column\('(\w+)',\s*(\w+)/);
      if (tableColMatch) {
        const colName = tableColMatch[1];
        const colType = tableColMatch[2];
        const isPK = line.includes('primary_key=True');

        inTable.columns.push({
          name: colName,
          type: TYPE_MAP[colType] || colType.toLowerCase(),
          isPK,
          isFK: line.includes('ForeignKey'),
          isUnique: false,
          comment: null,
        });

        // FK
        const fkMatch = line.match(/ForeignKey\(['"]([^'"]+)['"]\)/);
        if (fkMatch) {
          const [fkTable, fkCol] = fkMatch[1].split('.');
          inTable.foreignKeys.push({
            column: colName,
            refTable: fkTable,
            refColumn: fkCol,
          });
        }
      }
    }

    // relationship 定義
    if (currentModel) {
      const relMatch = line.match(/(\w+)\s*=\s*relationship\(["'](\w+)["']/);
      if (relMatch) {
        currentModel.relationships.push({
          name: relMatch[1],
          target: relMatch[2],
        });
      }
    }

    // Table 結束
    if (inTable && /^\)/.test(line)) {
      models.push(inTable);
      inTable = null;
    }
  }

  if (currentModel) models.push(currentModel);
  if (inTable) models.push(inTable);

  return models;
}

// ============================================================
// 2. 產生 Mermaid ER 圖
// ============================================================
function generateMermaid(allModels, options) {
  const lines = [];
  lines.push('erDiagram');

  // 建立 tableName → model 映射
  const tableMap = new Map();
  for (const m of allModels) {
    if (m.tableName) {
      tableMap.set(m.tableName, m);
    }
  }

  // 收集所有關聯
  const relationships = new Set();

  for (const model of allModels) {
    for (const fk of model.foreignKeys) {
      const fromTable = model.tableName || model.name;
      const toTable = fk.refTable;
      // 判斷關聯類型
      const isAssoc = model.isAssociation;
      const rel = isAssoc
        ? `    ${toTable} }o--o{ ${fromTable} : ""`
        : `    ${toTable} ||--o{ ${fromTable} : ""`;
      relationships.add(rel);
    }
  }

  // 輸出關聯
  for (const rel of relationships) {
    lines.push(rel);
  }

  lines.push('');

  // 按模組分組輸出 entities
  const modules = {};
  for (const m of allModels) {
    const mod = m.module || 'other';
    if (!modules[mod]) modules[mod] = [];
    modules[mod].push(m);
  }

  for (const [mod, models] of Object.entries(modules)) {
    const label = MODULE_LABELS[mod] || mod;
    lines.push(`    %% ── ${label} ──`);

    for (const model of models) {
      const tName = model.tableName || model.name;
      lines.push(`    ${tName} {`);

      if (!options.compact) {
        for (const col of model.columns) {
          const markers = [];
          if (col.isPK) markers.push('PK');
          if (col.isFK) markers.push('FK');
          if (col.isUnique && !col.isPK) markers.push('UK');
          const markerStr = markers.length > 0 ? ' ' + markers.join(',') : '';
          const commentStr = col.comment ? ` "${col.comment}"` : '';
          lines.push(`        ${col.type} ${col.name}${markerStr}${commentStr}`);
        }
      }

      lines.push('    }');
    }

    lines.push('');
  }

  return lines.join('\n');
}

// ============================================================
// 3. 統計摘要
// ============================================================
function generateSummary(allModels) {
  const lines = [];
  const totalCols = allModels.reduce((s, m) => s + m.columns.length, 0);
  const totalFKs = allModels.reduce((s, m) => s + m.foreignKeys.length, 0);
  const associations = allModels.filter(m => m.isAssociation).length;
  const entities = allModels.length - associations;

  lines.push('');
  lines.push('<!--');
  lines.push(`  Schema Diagram — generated ${new Date().toISOString().slice(0, 19)}`);
  lines.push(`  Models: ${entities} entities + ${associations} association tables`);
  lines.push(`  Columns: ${totalCols}`);
  lines.push(`  Foreign Keys: ${totalFKs}`);
  lines.push('');

  const modules = {};
  for (const m of allModels) {
    const mod = m.module || 'other';
    if (!modules[mod]) modules[mod] = [];
    modules[mod].push(m);
  }

  lines.push('  Modules:');
  for (const [mod, models] of Object.entries(modules)) {
    const label = MODULE_LABELS[mod] || mod;
    const names = models.map(m => m.tableName || m.name).join(', ');
    lines.push(`    ${label}: ${names}`);
  }

  lines.push('-->');
  return lines.join('\n');
}

// ============================================================
// 4. 主程式
// ============================================================
function main() {
  const args = process.argv.slice(2);

  let outputFile = null;
  let filterModule = null;
  let compact = false;

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--output':
        outputFile = args[++i];
        break;
      case '--module':
        filterModule = args[++i];
        break;
      case '--compact':
        compact = true;
        break;
      case '--help':
        console.log(`Usage: node scripts/schema-diagram-gen.js [options]

Options:
  --output FILE    輸出到檔案 (預設 stdout)
  --module NAME    只產生指定模組 (core/document/calendar/system/staff/taoyuan/entity/knowledge_graph)
  --compact        精簡模式（只顯示關聯，省略欄位）
  --help           顯示說明`);
        process.exit(0);
    }
  }

  // 讀取模型檔案
  if (!fs.existsSync(MODELS_DIR)) {
    console.error(`Models directory not found: ${MODELS_DIR}`);
    process.exit(1);
  }

  const pyFiles = fs.readdirSync(MODELS_DIR)
    .filter(f => f.endsWith('.py') && !f.startsWith('_'));

  let allModels = [];

  for (const file of pyFiles) {
    if (filterModule && file !== `${filterModule}.py`) continue;

    const content = fs.readFileSync(path.join(MODELS_DIR, file), 'utf-8');
    const models = parseModelFile(content, file);
    allModels = allModels.concat(models);
  }

  if (allModels.length === 0) {
    console.error('No models found');
    process.exit(1);
  }

  // 產生 Mermaid
  const mermaid = generateMermaid(allModels, { compact });
  const summary = generateSummary(allModels);

  const header = `# CK_Missive Database ER Diagram\n\n\`\`\`mermaid\n`;
  const footer = `\n\`\`\`\n${summary}\n`;

  const output = header + mermaid + footer;

  if (outputFile) {
    const outPath = path.resolve(outputFile);
    fs.writeFileSync(outPath, output, 'utf-8');
    console.log(`Written to ${outPath} (${allModels.length} models, ${allModels.reduce((s, m) => s + m.columns.length, 0)} columns)`);
  } else {
    console.log(output);
  }
}

main();

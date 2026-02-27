#!/usr/bin/env node
/**
 * 型別同步檢查工具 (Type Sync Check)
 *
 * 比對 OpenAPI 自動生成型別與手寫 SSOT 型別的欄位級差異，
 * 偵測前後端型別漂移（drift）。
 *
 * 使用方式：
 * - npm run type:sync           — 快速比對（使用現有 generated/api.d.ts）
 * - npm run type:sync:full      — 重新生成 + 比對（需後端運行中）
 * - node scripts/type-sync-check.js --strict        — CI 模式，有漂移 exit 1
 * - node scripts/type-sync-check.js --list-unmapped  — 列出未映射 schema
 *
 * @version 1.0.0
 * @date 2026-02-27
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ============================================================
// 路徑配置
// ============================================================
const GENERATED_FILE = path.join(__dirname, '../src/types/generated/api.d.ts');
const TYPES_DIR = path.join(__dirname, '../src/types');
const MAPPING_FILE = path.join(__dirname, 'type-mapping.json');

// ============================================================
// 1. Generated .d.ts 解析器
// ============================================================

/**
 * 從 openapi-typescript 生成的 .d.ts 中提取所有 schema 定義及其欄位
 *
 * 結構模式：
 *   (8 spaces)SchemaName: {
 *     (12 spaces)field_name?: type;
 *   };
 */
function parseGeneratedSchemas(content) {
  const schemas = {};
  const lines = content.split('\n');

  let currentSchema = null;
  let braceDepth = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (!currentSchema) {
      // 匹配 schema 起始：8 空格 + 大寫名稱 + : {
      const match = line.match(/^        ([A-Z]\w+): \{$/);
      if (match) {
        currentSchema = match[1];
        schemas[currentSchema] = {};
        braceDepth = 1;
      }
      continue;
    }

    // 追蹤大括號
    const opens = (line.match(/\{/g) || []).length;
    const closes = (line.match(/\}/g) || []).length;
    braceDepth += opens - closes;

    if (braceDepth <= 0) {
      currentSchema = null;
      braceDepth = 0;
      continue;
    }

    // 只解析第一層欄位（braceDepth === 1, 12 空格縮排）
    if (braceDepth === 1) {
      const fieldMatch = line.match(/^            (\w+)(\?)?: (.+);$/);
      if (fieldMatch) {
        const [, name, optional, typeStr] = fieldMatch;
        schemas[currentSchema][name] = {
          type: normalizeGeneratedType(typeStr),
          optional: !!optional,
          raw: typeStr,
        };
      }
    }
  }

  return schemas;
}

/**
 * 正規化 generated 型別字串
 */
function normalizeGeneratedType(typeStr) {
  return typeStr
    // components["schemas"]["Foo"] → Foo
    .replace(/components\["schemas"\]\["(\w+)"\]/g, '$1')
    // components["schemas"]["Foo"][] → Foo[]
    .replace(/components\["schemas"\]\["(\w+)"\]\[\]/g, '$1[]')
    .trim();
}

// ============================================================
// 2. 手寫 TypeScript 解析器
// ============================================================

/**
 * 從手寫 .ts 檔案中提取所有 export interface 定義及其欄位
 */
function parseHandwrittenFile(content) {
  const interfaces = {};
  const lines = content.split('\n');

  let currentInterface = null;
  let braceDepth = 0;
  let extendsClause = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (!currentInterface) {
      // export interface Foo { 或 export interface Bar extends Baz {
      const match = line.match(/^export interface (\w+)(?:\s+extends\s+(.+?))?\s*\{/);
      if (match) {
        currentInterface = match[1];
        extendsClause = match[2] || null;
        interfaces[currentInterface] = {
          fields: {},
          extends: extendsClause,
        };
        braceDepth = 1;
        continue;
      }
      continue;
    }

    const opens = (line.match(/\{/g) || []).length;
    const closes = (line.match(/\}/g) || []).length;
    braceDepth += opens - closes;

    if (braceDepth <= 0) {
      currentInterface = null;
      braceDepth = 0;
      continue;
    }

    // 只解析第一層欄位
    if (braceDepth === 1) {
      // 跳過註解行和空行
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('//') || trimmed.startsWith('/*') || trimmed.startsWith('*')) {
        continue;
      }

      // 欄位匹配：name?: type; 或 name: type;
      const fieldMatch = line.match(/^\s+(?:readonly\s+)?(\w+)(\?)?\s*:\s*(.+)/);
      if (fieldMatch) {
        const [, name, optional, rawType] = fieldMatch;
        // 去除行尾分號和註解
        const typeStr = rawType
          .replace(/\/\/.*$/, '')  // 去除行尾註解
          .replace(/;[\s]*$/, '') // 去除行尾分號
          .trim();
        if (typeStr) {
          interfaces[currentInterface].fields[name] = {
            type: typeStr,
            optional: !!optional,
          };
        }
      }
    }
  }

  return interfaces;
}

// ============================================================
// 2.5 繼承解析
// ============================================================

/**
 * 解析 interface 的 extends 繼承，合併父類別欄位
 * 支援 extends Foo、extends Partial<Foo>
 */
function resolveFields(interfaces, targetName) {
  const iface = interfaces[targetName];
  if (!iface) return null;

  const resolved = { ...iface.fields };

  if (iface.extends) {
    // 解析 extends 子句：可能是 "Foo" 或 "Partial<Foo>" 或 "Foo, Bar"
    const parts = iface.extends.split(',').map(s => s.trim());
    for (const part of parts) {
      const partialMatch = part.match(/^Partial<(\w+)>$/);
      const parentName = partialMatch ? partialMatch[1] : part;
      const parentIface = interfaces[parentName];

      if (parentIface) {
        // 遞迴解析父類別
        const parentFields = resolveFields(interfaces, parentName) || parentIface.fields;
        for (const [name, field] of Object.entries(parentFields)) {
          if (!resolved[name]) {
            resolved[name] = partialMatch
              ? { ...field, optional: true }
              : { ...field };
          }
        }
      }
    }
  }

  return resolved;
}

// ============================================================
// 3. 型別比對引擎
// ============================================================

/**
 * 比較兩個型別字串是否相容
 */
function typesCompatible(genType, hwType) {
  // 完全相同
  if (genType === hwType) return true;

  // 正規化：移除 | null, | undefined
  const normalize = (t) =>
    t.replace(/\s*\|\s*null/g, '').replace(/\s*\|\s*undefined/g, '').trim();

  const gen = normalize(genType);
  const hw = normalize(hwType);

  if (gen === hw) return true;

  // string <-> 自定義 string union/enum (DocType, DocStatus, UserStatus 等)
  if (gen === 'string' && !['number', 'boolean', 'object'].includes(hw)) return true;

  // number <-> number
  if (gen === 'number' && hw === 'number') return true;

  // boolean <-> boolean
  if (gen === 'boolean' && hw === 'boolean') return true;

  // 陣列型別寬鬆比對
  if (gen.endsWith('[]') && (hw.startsWith('Array<') || hw.endsWith('[]'))) return true;

  // AuthProvider enum vs string
  if (gen === 'AuthProvider' && hw === 'string') return true;

  return false;
}

/**
 * 對一組映射執行欄位級比對
 */
function compareMapping(mapping, genFields, hwFields) {
  const virtualFields = new Set(mapping.virtualFields || []);
  const ignoredHW = new Set((mapping.ignoredFields?.handwritten) || []);
  const ignoredGen = new Set((mapping.ignoredFields?.generated) || []);

  const result = {
    matched: [],
    missing: [],
    extra: [],
    typeMismatch: [],
  };

  // generated → handwritten（找遺漏欄位）
  for (const [name, genField] of Object.entries(genFields)) {
    if (ignoredGen.has(name)) continue;

    if (!hwFields[name]) {
      // 虛擬欄位不算遺漏
      if (!virtualFields.has(name)) {
        result.missing.push({
          field: name,
          generatedType: genField.type,
        });
      }
    } else {
      if (typesCompatible(genField.type, hwFields[name].type)) {
        result.matched.push({ field: name });
      } else {
        result.typeMismatch.push({
          field: name,
          generatedType: genField.type,
          handwrittenType: hwFields[name].type,
        });
      }
    }
  }

  // handwritten → generated（找多餘欄位）
  for (const [name] of Object.entries(hwFields)) {
    if (ignoredHW.has(name)) continue;
    if (!genFields[name] && !virtualFields.has(name)) {
      result.extra.push({
        field: name,
        handwrittenType: hwFields[name].type,
      });
    }
  }

  return result;
}

// ============================================================
// 4. 報告輸出
// ============================================================

function formatReport(results, stats, unmapped, options) {
  const lines = [];

  lines.push('='.repeat(65));
  lines.push(` Type Sync Report                    ${new Date().toISOString().slice(0, 19).replace('T', ' ')}`);
  lines.push('='.repeat(65));
  lines.push('');

  let perfectCount = 0;
  let issueCount = 0;
  let totalMissing = 0;
  let totalMismatch = 0;

  for (let i = 0; i < results.length; i++) {
    const r = results[i];
    const m = r.mapping;
    const idx = `[${i + 1}/${results.length}]`;

    if (r.error) {
      lines.push(`${idx} ${m.generated} -> ${m.handwritten} (${m.file})`);
      lines.push(`  !! ${r.error}`);
      lines.push('');
      issueCount++;
      continue;
    }

    const c = r.comparison;
    const hasIssues = c.missing.length > 0 || c.typeMismatch.length > 0;

    if (hasIssues) issueCount++;
    else perfectCount++;

    totalMissing += c.missing.length;
    totalMismatch += c.typeMismatch.length;

    lines.push(`${idx} ${m.generated} -> ${m.handwritten} (${m.file})`);
    lines.push(`  OK ${c.matched.length} fields matched`);

    if (c.typeMismatch.length > 0) {
      lines.push(`  !! Type mismatch: ${c.typeMismatch.length}`);
      for (const tm of c.typeMismatch) {
        lines.push(`    - ${tm.field}: generated=${tm.generatedType}, handwritten=${tm.handwrittenType}`);
      }
    }

    if (c.missing.length > 0) {
      lines.push(`  ?? Missing in handwritten: ${c.missing.length}`);
      for (const ms of c.missing) {
        lines.push(`    - ${ms.field}: ${ms.generatedType}`);
      }
    }

    if (c.extra.length > 0) {
      lines.push(`  .. Extra in handwritten: ${c.extra.length}`);
      for (const ex of c.extra) {
        lines.push(`    - ${ex.field}: ${ex.handwrittenType}`);
      }
    }

    lines.push('');
  }

  lines.push('='.repeat(65));
  lines.push(' Summary');
  lines.push('='.repeat(65));
  lines.push(`  Schemas checked:   ${results.length} / ${stats.totalSchemas}`);
  lines.push(`  Perfect match:     ${perfectCount}`);
  lines.push(`  With issues:       ${issueCount}`);
  if (totalMismatch > 0) {
    lines.push(`  - Type mismatches: ${totalMismatch} fields`);
  }
  if (totalMissing > 0) {
    lines.push(`  - Missing fields:  ${totalMissing} fields`);
  }
  lines.push(`  Unmapped schemas:  ${unmapped.length}`);
  lines.push('='.repeat(65));

  if (options.listUnmapped && unmapped.length > 0) {
    lines.push('');
    lines.push('Unmapped schemas:');
    for (const s of unmapped.sort()) {
      lines.push(`  - ${s}`);
    }
  }

  return lines.join('\n');
}

// ============================================================
// 5. 主程式
// ============================================================

async function main() {
  const args = process.argv.slice(2);
  const isStrict = args.includes('--strict');
  const listUnmapped = args.includes('--list-unmapped');

  // 讀取映射配置
  if (!fs.existsSync(MAPPING_FILE)) {
    console.error(`Mapping file not found: ${MAPPING_FILE}`);
    process.exit(1);
  }
  const mapping = JSON.parse(fs.readFileSync(MAPPING_FILE, 'utf-8'));

  // 讀取 generated 型別
  if (!fs.existsSync(GENERATED_FILE)) {
    console.error(`Generated file not found: ${GENERATED_FILE}`);
    console.error('Run "npm run api:generate" first.');
    process.exit(1);
  }
  const generatedContent = fs.readFileSync(GENERATED_FILE, 'utf-8');
  const genSchemas = parseGeneratedSchemas(generatedContent);

  // 快取手寫檔案解析結果
  const hwCache = {};

  function getHandwrittenInterfaces(file) {
    if (!hwCache[file]) {
      const filePath = path.join(TYPES_DIR, file);
      if (!fs.existsSync(filePath)) {
        hwCache[file] = null;
        return null;
      }
      hwCache[file] = parseHandwrittenFile(fs.readFileSync(filePath, 'utf-8'));
    }
    return hwCache[file];
  }

  // 逐映射比對
  const results = [];
  for (const m of mapping.mappings) {
    if (!genSchemas[m.generated]) {
      results.push({ mapping: m, error: `Generated schema "${m.generated}" not found in api.d.ts` });
      continue;
    }

    const hwInterfaces = getHandwrittenInterfaces(m.file);
    if (!hwInterfaces) {
      results.push({ mapping: m, error: `File not found: ${m.file}` });
      continue;
    }

    if (!hwInterfaces[m.handwritten]) {
      results.push({ mapping: m, error: `Interface "${m.handwritten}" not found in ${m.file}` });
      continue;
    }

    // 解析繼承，合併父類別欄位
    const resolvedHWFields = resolveFields(hwInterfaces, m.handwritten) || hwInterfaces[m.handwritten].fields;

    const comparison = compareMapping(
      m,
      genSchemas[m.generated],
      resolvedHWFields,
    );
    results.push({ mapping: m, comparison });
  }

  // 統計未映射 schema
  const mappedSchemas = new Set(mapping.mappings.map(m => m.generated));
  const unmapped = Object.keys(genSchemas).filter(s => !mappedSchemas.has(s));

  // 輸出報告
  const stats = { totalSchemas: Object.keys(genSchemas).length };
  const report = formatReport(results, stats, unmapped, { listUnmapped });
  console.log(report);

  // Exit code
  const hasRealIssues = results.some(r =>
    r.error ||
    r.comparison?.missing?.length > 0 ||
    r.comparison?.typeMismatch?.length > 0,
  );

  if (isStrict && hasRealIssues) {
    process.exit(1);
  }
}

main().catch((err) => {
  console.error('Type sync check failed:', err.message);
  process.exit(1);
});

#!/usr/bin/env node
/**
 * 把 .ts/.tsx 原始碼裡的「非程式碼文字」抹掉，只留程式碼 —— 供靜態判準比對用。
 *
 * ## 為什麼需要這一支（2026-08-29）
 *
 * 同一天有五個靜態判準被**自己的散文**騙過：
 *   · weekly 81 的負向對照回綠 —— 因為註解裡寫著「isTablet」
 *   · weekly 56 放過一個 16 欄表格 —— 因為註解寫著「刻意不改用 EnhancedTable」
 *   · weekly 82 的負向對照回綠 —— 因為 `console.warn('...totals...')` 是字串
 *
 * 我先用手寫正則剝註解與引號字串，**而它看起來已經處理好了**。
 * 實測 7 種形態後仍有三個洞：**樣板字串／JSX 文字／多行樣板** ——
 * 在 React 專案裡 JSX 文字到處都是。
 *
 * CK_AaaP 同日獨立踩到同一形狀（正則抓 `add_middleware(...)`，把註解掉的
 * 與字串裡的都算進去，5 個 vs 實際 3 個），結論一致：
 * **不要自己寫剝除邏輯，用語言自己的解析器。**
 * 他們用 `ast.parse`；TypeScript 這邊對應的是 `ts.createScanner`。
 *
 * ## 保證
 *
 * 抹掉的區段以**等長空白**取代（換行保留）⇒ **位元組位移與行號完全不變**，
 * 呼叫端報出來的行號仍然指向原檔的正確位置。
 *
 * ## 抹掉什麼
 *
 * 註解（行/區塊/JSDoc）、字串字面值、樣板字串（含 `${}` 外的所有片段）、
 * JSX 文字節點、regex 字面值。
 *
 * ⚠️ **抹不掉的**：條件式執行。`if (flag) { doThing(); }` 裡的 `doThing()`
 * 是真實呼叫點，但「這次有沒有走到」靜態看不出來 —— 那是判準本身的邊界，
 * 不是本工具的缺陷，呼叫端要自己知道。
 *
 * ## 用法
 *
 *   node ts_code_only.cjs <file...>        → 逐檔輸出 JSON {path, code}
 *   node ts_code_only.cjs --stdin          → 從 stdin 讀 JSON 路徑陣列
 *
 * 找不到 typescript 套件時**以退出碼 3 明確失敗**，不靜默退回較弱的判準 ——
 * 「判準變弱了」與「沒有違規」在輸出上長得一樣（ADR-0028）。
 */
'use strict';

const fs = require('fs');
const path = require('path');

function loadTS() {
  const candidates = [
    path.resolve(__dirname, '../../../frontend/node_modules/typescript'),
    path.resolve(__dirname, '../../../node_modules/typescript'),
    'typescript',
  ];
  for (const c of candidates) {
    try {
      return require(c);
    } catch (_) { /* try next */ }
  }
  return null;
}

const ts = loadTS();
if (!ts) {
  process.stderr.write(
    '找不到 typescript 套件（試過 frontend/node_modules、專案根、全域）。\n' +
    '不退回手寫正則 —— 那會讓判準悄悄變弱，而變弱與「沒有違規」在輸出上一樣。\n'
  );
  process.exit(3);
}

/** 抹掉區段，以等長空白取代（保留換行 ⇒ 行號不變） */
function blank(text, start, end) {
  let out = '';
  for (let i = start; i < end; i++) out += text[i] === '\n' ? '\n' : ' ';
  return text.slice(0, start) + out + text.slice(end);
}

const KILL = new Set();
for (const k of [
  'StringLiteral', 'NoSubstitutionTemplateLiteral',
  'TemplateHead', 'TemplateMiddle', 'TemplateTail',
  'JsxText', 'RegularExpressionLiteral',
  'SingleLineCommentTrivia', 'MultiLineCommentTrivia',
]) {
  if (ts.SyntaxKind[k] !== undefined) KILL.add(ts.SyntaxKind[k]);
}

/**
 * ⚠️ 用 **parser（createSourceFile）** 而不是 scanner。
 *
 * 首版用 `ts.createScanner` 走 token —— 合成案例 8/8 全過，**真實檔案卻漏了**：
 * `ERPVendorAccountsPage.tsx` 裡一個樣板字串沒被抹掉。原因是純 token 掃描
 * 沒有語法上下文：遇到 JSX 之後它分不出 `/` 是除法還是 regex 起頭、
 * `>` 屬於哪一層標籤，**一旦失步後面的 token 全部認錯**。
 *
 * 這正是「正向控制通過、真實案例失敗」——合成案例太乾淨，證明不了什麼。
 * parser 有完整上下文，沒有這個問題。
 */
function codeOnly(text, fileName) {
  const kind = /\.tsx$/i.test(fileName) ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
  const sf = ts.createSourceFile(fileName, text, ts.ScriptTarget.Latest, true, kind);
  const ranges = [];

  const walk = (node) => {
    // ① 字面值：字串／樣板（含 head/middle/tail）／JSX 文字／regex
    if (KILL.has(node.kind)) {
      ranges.push([node.getStart(sf), node.getEnd()]);
    }
    // ② 註解：每一則註解都是某個 token 的前置 trivia
    const full = node.getFullStart();
    const start = node.getStart(sf);
    if (full < start) {
      const cs = ts.getLeadingCommentRanges(text, full) || [];
      for (const c of cs) ranges.push([c.pos, c.end]);
    }
    node.forEachChild(walk);
  };
  sf.forEachChild(walk);

  // 檔尾的註解掛在 EndOfFileToken 上，會被上面的 forEachChild 漏掉
  const eof = sf.endOfFileToken;
  if (eof) {
    const cs = ts.getLeadingCommentRanges(text, eof.getFullStart()) || [];
    for (const c of cs) ranges.push([c.pos, c.end]);
  }

  let out = text;
  ranges.sort((a, b) => b[0] - a[0]);
  for (const [s, e] of ranges) out = blank(out, s, e);
  return out;
}

function main() {
  let files = process.argv.slice(2);
  if (files[0] === '--stdin') {
    files = JSON.parse(fs.readFileSync(0, 'utf8'));
  }
  const result = {};
  for (const f of files) {
    try {
      result[f] = codeOnly(fs.readFileSync(f, 'utf8'), f);
    } catch (e) {
      process.stderr.write(`讀取/解析失敗 ${f}: ${String(e).slice(0, 120)}\n`);
      process.exit(4);
    }
  }
  process.stdout.write(JSON.stringify(result));
}

main();

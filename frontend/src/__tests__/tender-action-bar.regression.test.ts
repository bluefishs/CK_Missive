/**
 * Regression — 標案詳情操作按鈕列一致性（2026-07-31）
 *
 * 事故：owner 以兩張截圖指出 PCC 與 ezbid 兩頁「設計不一致」——
 *   主要按鈕相反（一邊是外部連結、一邊是建案）、順序相反、ezbid 完全沒有收藏。
 * 根因是同一功能在兩個 render 分支各寫一套（與當日「改錯檔／漏改一邊」同型）。
 *
 * 治法是只留一套（TenderActionBar）。本測試守住「不准再各寫一套」。
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';

const PAGE = join(__dirname, '..', 'pages', 'TenderDetailPage.tsx');
const BAR = join(__dirname, '..', 'pages', 'tenderDetail', 'TenderActionBar.tsx');

/** 去除註解，避免比對命中說明文字（同日已被此陷阱咬過兩次） */
function stripComments(src: string): string {
  return src
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '');
}

describe('標案詳情操作按鈕列', () => {
  it('PCC 與 ezbid 兩個分支都使用共用元件', () => {
    const src = stripComments(readFileSync(PAGE, 'utf-8'));
    const uses = src.match(/<TenderActionBar/g) ?? [];
    expect(uses.length, '兩個來源分支都必須渲染 TenderActionBar').toBe(2);
  });

  it('頁面不得自行實作建案／收藏按鈕（必須經共用元件）', () => {
    const src = stripComments(readFileSync(PAGE, 'utf-8'));
    expect(src.includes('一鍵建案'), '頁面內出現「一鍵建案」字面 → 又各寫了一套').toBe(false);
    expect(src.includes('收藏此標案'), '頁面內出現「收藏此標案」字面 → 又各寫了一套').toBe(false);
  });

  it('共用元件內建案為主要動作、外部連結為次要', () => {
    const src = stripComments(readFileSync(BAR, 'utf-8'));
    const createIdx = src.indexOf('一鍵建案');
    const externalIdx = src.indexOf('externalLabel}');
    expect(createIdx).toBeGreaterThan(0);
    expect(externalIdx).toBeGreaterThan(0);
    // 建案必須排在外部連結之前（視覺順序）
    expect(createIdx < externalIdx, '建案應排在外部連結之前').toBe(true);
    // 建案是唯一的 type="primary"
    const primaries = src.match(/type="primary"/g) ?? [];
    expect(primaries.length, '按鈕列只應有一個主要動作').toBe(1);
  });

  it('共用元件提供收藏能力（ezbid 過去完全沒有）', () => {
    const src = stripComments(readFileSync(BAR, 'utf-8'));
    expect(src.includes('收藏此標案')).toBe(true);
    expect(src.includes('onCreateBookmark')).toBe(true);
  });
});

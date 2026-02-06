/**
 * 機關名稱處理工具函數測試
 *
 * 測試 utils/agencyUtils.ts 中所有匯出函數
 */
import { describe, it, expect } from 'vitest';
import {
  normalizeName,
  extractAgencyName,
  formatAgencyDisplay,
  extractAgencyList,
} from '../agencyUtils';

// ============================================================================
// normalizeName - 標準化名稱
// ============================================================================

describe('normalizeName', () => {
  it('應該去除前後空白', () => {
    expect(normalizeName('  桃園市政府  ')).toBe('桃園市政府');
  });

  it('應該移除中間空白', () => {
    expect(normalizeName('桃園 市政府')).toBe('桃園市政府');
  });

  it('應該移除全形空白', () => {
    expect(normalizeName('桃園\u3000市政府')).toBe('桃園市政府');
  });

  it('應該將全形括號轉為半形括號', () => {
    expect(normalizeName('（桃園市政府）')).toBe('(桃園市政府)');
  });

  it('混合全形半形括號應該統一為半形', () => {
    expect(normalizeName('（桃園）(市政府)')).toBe('(桃園)(市政府)');
  });

  it('null 輸入應該回傳空字串', () => {
    expect(normalizeName(null)).toBe('');
  });

  it('undefined 輸入應該回傳空字串', () => {
    expect(normalizeName(undefined)).toBe('');
  });

  it('空字串應該回傳空字串', () => {
    expect(normalizeName('')).toBe('');
  });

  it('已標準化的名稱不應改變', () => {
    expect(normalizeName('內政部國土管理署')).toBe('內政部國土管理署');
  });
});

// ============================================================================
// extractAgencyName - 提取機關名稱
// ============================================================================

describe('extractAgencyName', () => {
  it('應該從括號格式中提取名稱', () => {
    expect(extractAgencyName('376480000A (南投縣政府)')).toBe('南投縣政府');
  });

  it('應該提取第一組括號內的名稱', () => {
    expect(extractAgencyName('A01020100G (內政部國土管理署城鄉發展分署)')).toBe(
      '內政部國土管理署城鄉發展分署'
    );
  });

  it('沒有括號時應該回傳去除空白後的原始字串', () => {
    expect(extractAgencyName('內政部國土管理署')).toBe('內政部國土管理署');
  });

  it('空字串應該回傳空字串', () => {
    expect(extractAgencyName('')).toBe('');
  });

  it('前後有空白時應該去除', () => {
    expect(extractAgencyName('  376480000A (南投縣政府)  ')).toBe('南投縣政府');
  });

  it('只有代碼沒有括號時應該回傳代碼', () => {
    expect(extractAgencyName('376480000A')).toBe('376480000A');
  });
});

// ============================================================================
// formatAgencyDisplay - 格式化顯示
// ============================================================================

describe('formatAgencyDisplay', () => {
  it('單一機關應該提取名稱顯示', () => {
    expect(formatAgencyDisplay('376480000A (南投縣政府)')).toBe('南投縣政府');
  });

  it('多機關應該用頓號分隔顯示', () => {
    const input = '376480000A (南投縣政府) | A01020100G (內政部國土管理署城鄉發展分署)';
    expect(formatAgencyDisplay(input)).toBe(
      '南投縣政府、內政部國土管理署城鄉發展分署'
    );
  });

  it('沒有括號的機關應該原樣顯示', () => {
    expect(formatAgencyDisplay('桃園市政府')).toBe('桃園市政府');
  });

  it('null 輸入應該回傳 "-"', () => {
    expect(formatAgencyDisplay(null)).toBe('-');
  });

  it('undefined 輸入應該回傳 "-"', () => {
    expect(formatAgencyDisplay(undefined)).toBe('-');
  });

  it('空字串應該回傳 "-"', () => {
    expect(formatAgencyDisplay('')).toBe('-');
  });

  it('三個機關應該正確顯示', () => {
    const input = 'A (台北市政府) | B (新北市政府) | C (桃園市政府)';
    expect(formatAgencyDisplay(input)).toBe('台北市政府、新北市政府、桃園市政府');
  });
});

// ============================================================================
// extractAgencyList - 提取機關列表
// ============================================================================

describe('extractAgencyList', () => {
  it('應該提取多個機關名稱為陣列', () => {
    const input = '376480000A (南投縣政府) | A01020100G (內政部)';
    const result = extractAgencyList(input);
    expect(result).toEqual(['南投縣政府', '內政部']);
  });

  it('單一機關應該回傳單元素陣列', () => {
    const result = extractAgencyList('376480000A (桃園市政府)');
    expect(result).toEqual(['桃園市政府']);
  });

  it('應該過濾掉「未指定」', () => {
    const input = '376480000A (南投縣政府) | X (未指定)';
    const result = extractAgencyList(input);
    expect(result).toEqual(['南投縣政府']);
  });

  it('null 輸入應該回傳空陣列', () => {
    expect(extractAgencyList(null)).toEqual([]);
  });

  it('undefined 輸入應該回傳空陣列', () => {
    expect(extractAgencyList(undefined)).toEqual([]);
  });

  it('空字串應該回傳空陣列', () => {
    expect(extractAgencyList('')).toEqual([]);
  });

  it('提取結果應該經過 normalizeName 處理', () => {
    // normalizeName 會移除空白，所以名稱中的空格會被去除
    const input = 'A (南投 縣政府)';
    const result = extractAgencyList(input);
    expect(result).toEqual(['南投縣政府']);
  });

  it('多個分隔符號之間的空白不影響結果', () => {
    const input = 'A (台北市政府)  |  B (新北市政府)';
    const result = extractAgencyList(input);
    expect(result).toEqual(['台北市政府', '新北市政府']);
  });
});

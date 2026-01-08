/**
 * 格式化工具函數測試
 * Formatter Utility Tests
 */
import { describe, it, expect } from 'vitest';

// 日期格式化函數 (範例)
function formatDate(date: string | Date | null): string {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('zh-TW');
}

// 金額格式化函數 (範例)
function formatCurrency(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return '-';
  return new Intl.NumberFormat('zh-TW', {
    style: 'currency',
    currency: 'TWD',
    minimumFractionDigits: 0,
  }).format(amount);
}

describe('formatDate', () => {
  it('應該正確格式化日期字串', () => {
    const result = formatDate('2026-01-08');
    expect(result).toContain('2026');
  });

  it('應該處理 null 值', () => {
    expect(formatDate(null)).toBe('-');
  });

  it('應該處理 Date 物件', () => {
    const date = new Date('2026-01-08');
    const result = formatDate(date);
    expect(result).toContain('2026');
  });
});

describe('formatCurrency', () => {
  it('應該正確格式化金額', () => {
    const result = formatCurrency(1000000);
    expect(result).toContain('1,000,000');
  });

  it('應該處理 null 值', () => {
    expect(formatCurrency(null)).toBe('-');
  });

  it('應該處理 undefined 值', () => {
    expect(formatCurrency(undefined)).toBe('-');
  });

  it('應該處理零值', () => {
    const result = formatCurrency(0);
    expect(result).toContain('0');
  });
});

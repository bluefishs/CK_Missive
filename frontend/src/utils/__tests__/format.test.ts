/**
 * format.ts 工具函數測試
 *
 * @version 1.0.0
 * @created 2026-03-15
 */
import { describe, it, expect } from 'vitest';
import {
  formatDate,
  formatFileSize,
  getStatusColor,
  getPriorityColor,
  getStatusLabel,
  getPriorityLabel,
  parseCurrencyInput,
} from '../format';

describe('formatDate', () => {
  it('格式化日期字串', () => {
    expect(formatDate('2026-03-15')).toBe('2026-03-15');
  });

  it('格式化 Date 物件', () => {
    const d = new Date(2026, 2, 15);
    expect(formatDate(d)).toBe('2026-03-15');
  });

  it('格式化含時間的日期', () => {
    const d = new Date(2026, 2, 15, 14, 30, 45);
    expect(formatDate(d, 'yyyy-MM-dd HH:mm:ss')).toBe('2026-03-15 14:30:45');
  });

  it('空值返回空字串', () => {
    expect(formatDate('')).toBe('');
  });

  it('無效日期返回「無效日期」', () => {
    expect(formatDate('invalid')).toBe('無效日期');
  });

  it('未知格式仍返回日期部分', () => {
    const d = new Date(2026, 2, 15);
    expect(formatDate(d, 'unknown')).toBe('2026-03-15');
  });
});

describe('formatFileSize', () => {
  it('0 bytes', () => {
    expect(formatFileSize(0)).toBe('0 B');
  });

  it('bytes', () => {
    expect(formatFileSize(512)).toBe('512 B');
  });

  it('KB', () => {
    expect(formatFileSize(1024)).toBe('1 KB');
  });

  it('MB', () => {
    expect(formatFileSize(1048576)).toBe('1 MB');
  });

  it('GB', () => {
    expect(formatFileSize(1073741824)).toBe('1 GB');
  });

  it('非整數顯示小數', () => {
    expect(formatFileSize(1500)).toBe('1.46 KB');
  });
});

describe('getStatusColor', () => {
  it('draft → default', () => expect(getStatusColor('draft')).toBe('default'));
  it('review → warning', () => expect(getStatusColor('review')).toBe('warning'));
  it('published → success', () => expect(getStatusColor('published')).toBe('success'));
  it('archived → info', () => expect(getStatusColor('archived')).toBe('info'));
  it('unknown → default', () => expect(getStatusColor('xyz')).toBe('default'));
});

describe('getPriorityColor', () => {
  it('low → info', () => expect(getPriorityColor('low')).toBe('info'));
  it('normal → default', () => expect(getPriorityColor('normal')).toBe('default'));
  it('high → warning', () => expect(getPriorityColor('high')).toBe('warning'));
  it('urgent → error', () => expect(getPriorityColor('urgent')).toBe('error'));
  it('unknown → default', () => expect(getPriorityColor('xyz')).toBe('default'));
});

describe('getStatusLabel', () => {
  it('draft → 草稿', () => expect(getStatusLabel('draft')).toBe('草稿'));
  it('review → 審核中', () => expect(getStatusLabel('review')).toBe('審核中'));
  it('published → 已發布', () => expect(getStatusLabel('published')).toBe('已發布'));
  it('archived → 已歸檔', () => expect(getStatusLabel('archived')).toBe('已歸檔'));
  it('unknown → 原值', () => expect(getStatusLabel('custom')).toBe('custom'));
});

describe('getPriorityLabel', () => {
  it('low → 低', () => expect(getPriorityLabel('low')).toBe('低'));
  it('normal → 一般', () => expect(getPriorityLabel('normal')).toBe('一般'));
  it('high → 高', () => expect(getPriorityLabel('high')).toBe('高'));
  it('urgent → 緊急', () => expect(getPriorityLabel('urgent')).toBe('緊急'));
  it('unknown → 原值', () => expect(getPriorityLabel('custom')).toBe('custom'));
});

describe('parseCurrencyInput', () => {
  it('數字字串', () => expect(parseCurrencyInput('1234')).toBe(1234));
  it('含千分位逗號', () => expect(parseCurrencyInput('1,234,567')).toBe(1234567));
  it('含貨幣符號', () => expect(parseCurrencyInput('$1,234')).toBe(1234));
  it('含空格', () => expect(parseCurrencyInput('$ 1,234')).toBe(1234));
  it('undefined 返回 0', () => expect(parseCurrencyInput(undefined)).toBe(0));
  it('空字串返回 0', () => expect(parseCurrencyInput('')).toBe(0));
  it('非數字返回 0', () => expect(parseCurrencyInput('abc')).toBe(0));
  it('小數', () => expect(parseCurrencyInput('1234.56')).toBe(1234.56));
});

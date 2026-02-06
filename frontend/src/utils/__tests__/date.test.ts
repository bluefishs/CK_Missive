/**
 * 日期工具函數測試
 *
 * 測試 utils/date.ts 中所有匯出函數
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  formatDate,
  formatDateTime,
  formatRelativeTime,
  isToday,
  getDateRange,
} from '../date';

describe('formatDate', () => {
  it('應該使用預設格式 yyyy-MM-dd 格式化日期', () => {
    const result = formatDate(new Date(2026, 0, 15)); // 2026-01-15
    expect(result).toBe('2026-01-15');
  });

  it('應該正確格式化日期字串', () => {
    const result = formatDate('2026-03-08T10:30:00');
    expect(result).toBe('2026-03-08');
  });

  it('應該支援 yyyy-MM-dd HH:mm:ss 格式', () => {
    const result = formatDate(new Date(2026, 5, 20, 14, 30, 45), 'yyyy-MM-dd HH:mm:ss');
    expect(result).toBe('2026-06-20 14:30:45');
  });

  it('當月份和日期為個位數時應該補零', () => {
    const result = formatDate(new Date(2026, 0, 5)); // January 5
    expect(result).toBe('2026-01-05');
  });

  it('當傳入無效日期字串時應該回傳「無效日期」', () => {
    const result = formatDate('not-a-date');
    expect(result).toBe('無效日期');
  });

  it('當傳入空字串時應該回傳空字串', () => {
    const result = formatDate('');
    expect(result).toBe('');
  });

  it('當傳入不支援的格式字串時應該回退為 yyyy-MM-dd', () => {
    const result = formatDate(new Date(2026, 0, 15), 'dd/MM/yyyy');
    expect(result).toBe('2026-01-15');
  });
});

describe('formatDateTime', () => {
  it('應該格式化為 yyyy-MM-dd HH:mm:ss 格式', () => {
    const result = formatDateTime(new Date(2026, 11, 25, 8, 5, 3));
    expect(result).toBe('2026-12-25 08:05:03');
  });

  it('應該接受日期字串', () => {
    const result = formatDateTime('2026-07-04T16:45:30');
    expect(result).toMatch(/^2026-07-04 \d{2}:\d{2}:\d{2}$/);
  });

  it('當傳入空值時應該回傳空字串', () => {
    const result = formatDateTime('');
    expect(result).toBe('');
  });

  it('當傳入無效日期時應該回傳「無效日期」', () => {
    const result = formatDateTime('invalid');
    expect(result).toBe('無效日期');
  });
});

describe('formatRelativeTime', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 1, 6, 12, 0, 0)); // 2026-02-06 12:00:00
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('30 秒以內應該回傳「剛剛」', () => {
    const thirtySecondsAgo = new Date(2026, 1, 6, 11, 59, 35);
    expect(formatRelativeTime(thirtySecondsAgo)).toBe('剛剛');
  });

  it('5 分鐘前應該回傳「5 分鐘前」', () => {
    const fiveMinutesAgo = new Date(2026, 1, 6, 11, 55, 0);
    expect(formatRelativeTime(fiveMinutesAgo)).toBe('5 分鐘前');
  });

  it('3 小時前應該回傳「3 小時前」', () => {
    const threeHoursAgo = new Date(2026, 1, 6, 9, 0, 0);
    expect(formatRelativeTime(threeHoursAgo)).toBe('3 小時前');
  });

  it('2 天前應該回傳「2 天前」', () => {
    const twoDaysAgo = new Date(2026, 1, 4, 12, 0, 0);
    expect(formatRelativeTime(twoDaysAgo)).toBe('2 天前');
  });

  it('當傳入空字串時應該回傳空字串', () => {
    expect(formatRelativeTime('')).toBe('');
  });

  it('當傳入無效日期時應該回傳「無效日期」', () => {
    expect(formatRelativeTime('not-valid')).toBe('無效日期');
  });
});

describe('isToday', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 1, 6, 15, 0, 0)); // 2026-02-06 15:00
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('今天的日期應該回傳 true', () => {
    const today = new Date(2026, 1, 6, 8, 30, 0);
    expect(isToday(today)).toBe(true);
  });

  it('今天的日期字串應該回傳 true', () => {
    expect(isToday('2026-02-06T03:00:00')).toBe(true);
  });

  it('昨天的日期應該回傳 false', () => {
    const yesterday = new Date(2026, 1, 5, 15, 0, 0);
    expect(isToday(yesterday)).toBe(false);
  });

  it('當傳入空字串時應該回傳 false', () => {
    expect(isToday('')).toBe(false);
  });
});

describe('getDateRange', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 1, 6, 12, 0, 0)); // 2026-02-06 12:00
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('應該回傳正確的開始和結束日期', () => {
    const { start, end } = getDateRange(7);

    expect(end.getFullYear()).toBe(2026);
    expect(end.getMonth()).toBe(1); // February (0-indexed)
    expect(end.getDate()).toBe(6);

    expect(start.getFullYear()).toBe(2026);
    expect(start.getMonth()).toBe(0); // January
    expect(start.getDate()).toBe(30);
  });

  it('傳入 0 天時 start 和 end 應該是同一天', () => {
    const { start, end } = getDateRange(0);
    expect(start.toDateString()).toBe(end.toDateString());
  });

  it('傳入 30 天應該往回推 30 天', () => {
    const { start } = getDateRange(30);
    expect(start.getMonth()).toBe(0); // January
    expect(start.getDate()).toBe(7);
  });
});

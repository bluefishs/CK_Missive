/**
 * format.ts 單元測試
 *
 * 測試格式化工具函數：日期格式化、檔案大小、狀態/優先級標籤與顏色
 *
 * @version 1.0.0
 * @date 2026-02-06
 */
import { describe, it, expect } from 'vitest';
import {
  formatDate,
  formatFileSize,
  getStatusColor,
  getPriorityColor,
  getStatusLabel,
  getPriorityLabel,
} from '../../utils/format';

// =============================================================================
// formatDate
// =============================================================================

describe('formatDate', () => {
  it('Date 物件應格式化為 yyyy-MM-dd', () => {
    const date = new Date(2026, 1, 6); // 2026-02-06
    expect(formatDate(date)).toBe('2026-02-06');
  });

  it('字串日期應正確解析並格式化', () => {
    expect(formatDate('2026-01-15')).toBe('2026-01-15');
  });

  it('空值應返回空字串', () => {
    expect(formatDate('')).toBe('');
  });

  it('無效日期應返回「無效日期」', () => {
    expect(formatDate('not-a-date')).toBe('無效日期');
  });

  it('yyyy-MM-dd HH:mm:ss 格式應包含時間', () => {
    const date = new Date(2026, 1, 6, 14, 30, 45);
    expect(formatDate(date, 'yyyy-MM-dd HH:mm:ss')).toBe('2026-02-06 14:30:45');
  });

  it('月份和日期應補零', () => {
    const date = new Date(2026, 0, 5); // 2026-01-05
    expect(formatDate(date)).toBe('2026-01-05');
  });

  it('未知格式應 fallback 為 yyyy-MM-dd', () => {
    const date = new Date(2026, 1, 6);
    expect(formatDate(date, 'unknown-format')).toBe('2026-02-06');
  });
});

// =============================================================================
// formatFileSize
// =============================================================================

describe('formatFileSize', () => {
  it('0 bytes 應返回 "0 B"', () => {
    expect(formatFileSize(0)).toBe('0 B');
  });

  it('小於 1KB 應顯示 B', () => {
    expect(formatFileSize(500)).toBe('500 B');
  });

  it('1024 bytes 應顯示 1 KB', () => {
    expect(formatFileSize(1024)).toBe('1 KB');
  });

  it('1.5 KB 應正確顯示', () => {
    expect(formatFileSize(1536)).toBe('1.5 KB');
  });

  it('1 MB 應正確顯示', () => {
    expect(formatFileSize(1024 * 1024)).toBe('1 MB');
  });

  it('2.5 GB 應正確顯示', () => {
    expect(formatFileSize(2.5 * 1024 * 1024 * 1024)).toBe('2.5 GB');
  });
});

// =============================================================================
// getStatusColor
// =============================================================================

describe('getStatusColor', () => {
  it('draft 應返回 default', () => {
    expect(getStatusColor('draft')).toBe('default');
  });

  it('review 應返回 warning', () => {
    expect(getStatusColor('review')).toBe('warning');
  });

  it('published 應返回 success', () => {
    expect(getStatusColor('published')).toBe('success');
  });

  it('archived 應返回 info', () => {
    expect(getStatusColor('archived')).toBe('info');
  });

  it('未知狀態應返回 default', () => {
    expect(getStatusColor('unknown')).toBe('default');
  });
});

// =============================================================================
// getPriorityColor
// =============================================================================

describe('getPriorityColor', () => {
  it('low 應返回 info', () => {
    expect(getPriorityColor('low')).toBe('info');
  });

  it('normal 應返回 default', () => {
    expect(getPriorityColor('normal')).toBe('default');
  });

  it('high 應返回 warning', () => {
    expect(getPriorityColor('high')).toBe('warning');
  });

  it('urgent 應返回 error', () => {
    expect(getPriorityColor('urgent')).toBe('error');
  });

  it('未知優先級應返回 default', () => {
    expect(getPriorityColor('unknown')).toBe('default');
  });
});

// =============================================================================
// getStatusLabel
// =============================================================================

describe('getStatusLabel', () => {
  it('draft 應返回「草稿」', () => {
    expect(getStatusLabel('draft')).toBe('草稿');
  });

  it('review 應返回「審核中」', () => {
    expect(getStatusLabel('review')).toBe('審核中');
  });

  it('published 應返回「已發布」', () => {
    expect(getStatusLabel('published')).toBe('已發布');
  });

  it('archived 應返回「已歸檔」', () => {
    expect(getStatusLabel('archived')).toBe('已歸檔');
  });

  it('未知狀態應返回原始值', () => {
    expect(getStatusLabel('custom_status')).toBe('custom_status');
  });
});

// =============================================================================
// getPriorityLabel
// =============================================================================

describe('getPriorityLabel', () => {
  it('low 應返回「低」', () => {
    expect(getPriorityLabel('low')).toBe('低');
  });

  it('normal 應返回「一般」', () => {
    expect(getPriorityLabel('normal')).toBe('一般');
  });

  it('high 應返回「高」', () => {
    expect(getPriorityLabel('high')).toBe('高');
  });

  it('urgent 應返回「緊急」', () => {
    expect(getPriorityLabel('urgent')).toBe('緊急');
  });

  it('未知優先級應返回原始值', () => {
    expect(getPriorityLabel('custom')).toBe('custom');
  });
});

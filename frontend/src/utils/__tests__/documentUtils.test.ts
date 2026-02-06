/**
 * 公文工具函數測試
 *
 * 測試 utils/documentUtils.ts 中所有匯出函數
 */
import { describe, it, expect } from 'vitest';
import {
  formatDate,
  getStatusColor,
  getStatusLabel,
  getPriorityColor,
  getPriorityLabel,
  formatFileSize,
  truncateText,
} from '../documentUtils';

// ============================================================================
// 日期格式化 (Intl.DateTimeFormat 版本)
// ============================================================================

describe('formatDate (documentUtils)', () => {
  it('應該格式化日期字串為中文區域格式', () => {
    const result = formatDate('2026-01-15T10:30:00');
    // Intl.DateTimeFormat 的 zh-TW 格式包含年月日和時間
    expect(result).toContain('2026');
    expect(result).toContain('1');
    expect(result).toContain('15');
  });

  it('應該包含時間部分', () => {
    const result = formatDate('2026-06-20T14:30:00');
    // zh-TW locale 使用 12 小時制 (下午02:30) 而非 24 小時制
    expect(result).toContain('02');
    expect(result).toContain('30');
  });
});

// ============================================================================
// 狀態顏色映射
// ============================================================================

describe('getStatusColor (documentUtils)', () => {
  it('draft 應該回傳 default', () => {
    expect(getStatusColor('draft')).toBe('default');
  });

  it('pending 應該回傳 warning', () => {
    expect(getStatusColor('pending')).toBe('warning');
  });

  it('approved 應該回傳 success', () => {
    expect(getStatusColor('approved')).toBe('success');
  });

  it('rejected 應該回傳 error', () => {
    expect(getStatusColor('rejected')).toBe('error');
  });

  it('未知狀態應該回傳 default', () => {
    expect(getStatusColor('unknown_status')).toBe('default');
  });
});

// ============================================================================
// 狀態標籤映射
// ============================================================================

describe('getStatusLabel (documentUtils)', () => {
  it('draft 應該回傳「草稿」', () => {
    expect(getStatusLabel('draft')).toBe('草稿');
  });

  it('pending 應該回傳「待審核」', () => {
    expect(getStatusLabel('pending')).toBe('待審核');
  });

  it('approved 應該回傳「已核准」', () => {
    expect(getStatusLabel('approved')).toBe('已核准');
  });

  it('rejected 應該回傳「已拒絕」', () => {
    expect(getStatusLabel('rejected')).toBe('已拒絕');
  });

  it('未知狀態應該回傳「未知」', () => {
    expect(getStatusLabel('something_else')).toBe('未知');
  });
});

// ============================================================================
// 優先級顏色映射
// ============================================================================

describe('getPriorityColor (documentUtils)', () => {
  it('urgent 應該回傳 error', () => {
    expect(getPriorityColor('urgent')).toBe('error');
  });

  it('high 應該回傳 warning', () => {
    expect(getPriorityColor('high')).toBe('warning');
  });

  it('medium 應該回傳 info', () => {
    expect(getPriorityColor('medium')).toBe('info');
  });

  it('low 應該回傳 default', () => {
    expect(getPriorityColor('low')).toBe('default');
  });

  it('未知優先級應該回傳 default', () => {
    expect(getPriorityColor('critical')).toBe('default');
  });
});

// ============================================================================
// 優先級標籤映射
// ============================================================================

describe('getPriorityLabel (documentUtils)', () => {
  it('urgent 應該回傳「緊急」', () => {
    expect(getPriorityLabel('urgent')).toBe('緊急');
  });

  it('high 應該回傳「高」', () => {
    expect(getPriorityLabel('high')).toBe('高');
  });

  it('medium 應該回傳「中」', () => {
    expect(getPriorityLabel('medium')).toBe('中');
  });

  it('low 應該回傳「低」', () => {
    expect(getPriorityLabel('low')).toBe('低');
  });

  it('未知優先級應該回傳「一般」', () => {
    expect(getPriorityLabel('unknown')).toBe('一般');
  });
});

// ============================================================================
// 檔案大小格式化
// ============================================================================

describe('formatFileSize (documentUtils)', () => {
  it('0 bytes 應該回傳 "0 Bytes"', () => {
    expect(formatFileSize(0)).toBe('0 Bytes');
  });

  it('應該正確格式化 Bytes', () => {
    expect(formatFileSize(512)).toBe('512 Bytes');
  });

  it('應該正確格式化 KB', () => {
    expect(formatFileSize(1024)).toBe('1 KB');
  });

  it('應該正確格式化 MB', () => {
    expect(formatFileSize(1048576)).toBe('1 MB');
  });

  it('應該正確格式化 GB', () => {
    expect(formatFileSize(1073741824)).toBe('1 GB');
  });

  it('應該保留兩位小數', () => {
    expect(formatFileSize(1536)).toBe('1.5 KB');
  });
});

// ============================================================================
// 文字截斷
// ============================================================================

describe('truncateText', () => {
  it('短於上限的文字應該原樣回傳', () => {
    expect(truncateText('Hello', 10)).toBe('Hello');
  });

  it('剛好等於上限的文字應該原樣回傳', () => {
    expect(truncateText('12345', 5)).toBe('12345');
  });

  it('超過上限的文字應該截斷並加上省略號', () => {
    expect(truncateText('Hello World', 5)).toBe('Hello...');
  });

  it('中文文字也應該正確截斷', () => {
    expect(truncateText('桃園市政府公文', 3)).toBe('桃園市...');
  });

  it('空字串應該回傳空字串', () => {
    expect(truncateText('', 10)).toBe('');
  });
});

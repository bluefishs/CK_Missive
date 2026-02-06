/**
 * 通用工具函數測試
 *
 * 測試 utils/common.ts 中所有匯出函數
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  delay,
  debounce,
  throttle,
  deepClone,
  generateId,
  formatFileSize,
  formatNumber,
  isValidEmail,
  isValidUrl,
  capitalize,
  toKebabCase,
  toCamelCase,
  getStatusColor,
  getStatusLabel,
  getPriorityColor,
  getPriorityLabel,
} from '../common';

// ============================================================================
// 計時器相關函數
// ============================================================================

describe('delay', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('應該在指定毫秒後 resolve', async () => {
    const promise = delay(1000);
    vi.advanceTimersByTime(1000);
    await expect(promise).resolves.toBeUndefined();
  });

  it('在時間未到時不應該 resolve', () => {
    let resolved = false;
    delay(500).then(() => { resolved = true; });
    vi.advanceTimersByTime(300);
    expect(resolved).toBe(false);
  });
});

describe('debounce', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('在等待時間內連續呼叫只應該執行最後一次', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 200);

    debounced('a');
    debounced('b');
    debounced('c');

    vi.advanceTimersByTime(200);
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith('c');
  });

  it('等待時間過後應該可以再次觸發', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);

    debounced('first');
    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledTimes(1);

    debounced('second');
    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it('在等待時間內未再次呼叫應該正常觸發', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 300);

    debounced('only');
    vi.advanceTimersByTime(300);
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith('only');
  });
});

describe('throttle', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('第一次呼叫應該立即執行', () => {
    const fn = vi.fn();
    const throttled = throttle(fn, 200);

    throttled('first');
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith('first');
  });

  it('在節流期間內的呼叫應該被忽略', () => {
    const fn = vi.fn();
    const throttled = throttle(fn, 200);

    throttled('a');
    throttled('b');
    throttled('c');

    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith('a');
  });

  it('節流期間過後應該可以再次觸發', () => {
    const fn = vi.fn();
    const throttled = throttle(fn, 100);

    throttled('first');
    expect(fn).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(100);

    throttled('second');
    expect(fn).toHaveBeenCalledTimes(2);
    expect(fn).toHaveBeenCalledWith('second');
  });
});

// ============================================================================
// 資料處理函數
// ============================================================================

describe('deepClone', () => {
  it('應該複製基本型別', () => {
    expect(deepClone(42)).toBe(42);
    expect(deepClone('hello')).toBe('hello');
    expect(deepClone(true)).toBe(true);
    expect(deepClone(null)).toBe(null);
  });

  it('應該正確複製 Date 物件', () => {
    const date = new Date(2026, 0, 15);
    const cloned = deepClone(date);

    expect(cloned).toEqual(date);
    expect(cloned).not.toBe(date); // 不同參照
    expect(cloned.getTime()).toBe(date.getTime());
  });

  it('應該深度複製陣列', () => {
    const arr = [1, [2, 3], { a: 4 }];
    const cloned = deepClone(arr);

    expect(cloned).toEqual(arr);
    expect(cloned).not.toBe(arr);
    expect(cloned[1]).not.toBe(arr[1]);
    expect(cloned[2]).not.toBe(arr[2]);
  });

  it('應該深度複製巢狀物件', () => {
    const obj = {
      name: 'test',
      nested: {
        value: 123,
        deep: { flag: true },
      },
    };
    const cloned = deepClone(obj);

    expect(cloned).toEqual(obj);
    expect(cloned).not.toBe(obj);
    expect(cloned.nested).not.toBe(obj.nested);
    expect(cloned.nested.deep).not.toBe(obj.nested.deep);
  });

  it('修改複製品不應該影響原始物件', () => {
    const original = { a: 1, b: { c: 2 } };
    const cloned = deepClone(original);

    cloned.a = 99;
    cloned.b.c = 99;

    expect(original.a).toBe(1);
    expect(original.b.c).toBe(2);
  });
});

describe('generateId', () => {
  it('應該產生非空字串', () => {
    const id = generateId();
    expect(id).toBeTruthy();
    expect(typeof id).toBe('string');
  });

  it('連續呼叫應該產生不同的 ID', () => {
    const ids = new Set([generateId(), generateId(), generateId()]);
    expect(ids.size).toBe(3);
  });

  it('應該支援自訂前綴', () => {
    const id = generateId('doc_');
    expect(id.startsWith('doc_')).toBe(true);
  });

  it('不帶前綴時不應該有固定前綴', () => {
    const id = generateId();
    // 只驗證是英數字組合 (base36)
    expect(id).toMatch(/^[a-z0-9]+$/);
  });
});

// ============================================================================
// 格式化函數
// ============================================================================

describe('formatFileSize', () => {
  it('0 bytes 應該回傳 "0 Bytes"', () => {
    expect(formatFileSize(0)).toBe('0 Bytes');
  });

  it('應該正確格式化 Bytes 範圍', () => {
    expect(formatFileSize(500)).toBe('500 Bytes');
  });

  it('應該正確格式化 KB 範圍', () => {
    expect(formatFileSize(1024)).toBe('1 KB');
    expect(formatFileSize(1536)).toBe('1.5 KB');
  });

  it('應該正確格式化 MB 範圍', () => {
    expect(formatFileSize(1048576)).toBe('1 MB');
    expect(formatFileSize(5242880)).toBe('5 MB');
  });

  it('應該正確格式化 GB 範圍', () => {
    expect(formatFileSize(1073741824)).toBe('1 GB');
  });
});

describe('formatNumber', () => {
  it('應該加上千分位分隔符號', () => {
    expect(formatNumber(1000000)).toBe('1,000,000');
  });

  it('小於 1000 的數字不需要分隔符號', () => {
    expect(formatNumber(999)).toBe('999');
  });

  it('應該處理 0', () => {
    expect(formatNumber(0)).toBe('0');
  });

  it('應該處理負數', () => {
    const result = formatNumber(-12345);
    expect(result).toContain('12,345');
  });
});

// ============================================================================
// 驗證函數
// ============================================================================

describe('isValidEmail', () => {
  it('合法 Email 應該回傳 true', () => {
    expect(isValidEmail('user@example.com')).toBe(true);
    expect(isValidEmail('test.name@domain.co.tw')).toBe(true);
  });

  it('缺少 @ 符號應該回傳 false', () => {
    expect(isValidEmail('userexample.com')).toBe(false);
  });

  it('缺少域名應該回傳 false', () => {
    expect(isValidEmail('user@')).toBe(false);
  });

  it('空字串應該回傳 false', () => {
    expect(isValidEmail('')).toBe(false);
  });

  it('包含空白應該回傳 false', () => {
    expect(isValidEmail('user @example.com')).toBe(false);
  });
});

describe('isValidUrl', () => {
  it('合法 URL 應該回傳 true', () => {
    expect(isValidUrl('https://example.com')).toBe(true);
    expect(isValidUrl('http://localhost:3000')).toBe(true);
    expect(isValidUrl('ftp://files.example.com/doc.pdf')).toBe(true);
  });

  it('缺少協議的字串應該回傳 false', () => {
    expect(isValidUrl('example.com')).toBe(false);
  });

  it('空字串應該回傳 false', () => {
    expect(isValidUrl('')).toBe(false);
  });

  it('隨意文字應該回傳 false', () => {
    expect(isValidUrl('not a url')).toBe(false);
  });
});

// ============================================================================
// 字串轉換函數
// ============================================================================

describe('capitalize', () => {
  it('應該將首字母轉為大寫', () => {
    expect(capitalize('hello')).toBe('Hello');
  });

  it('已經大寫的首字母不應改變', () => {
    expect(capitalize('Hello')).toBe('Hello');
  });

  it('單一字元應該轉為大寫', () => {
    expect(capitalize('a')).toBe('A');
  });

  it('空字串應該回傳空字串', () => {
    expect(capitalize('')).toBe('');
  });
});

describe('toKebabCase', () => {
  it('應該將 camelCase 轉為 kebab-case', () => {
    expect(toKebabCase('helloWorld')).toBe('hello-world');
  });

  it('應該將空格轉為連字號', () => {
    expect(toKebabCase('hello world')).toBe('hello-world');
  });

  it('應該將底線轉為連字號', () => {
    expect(toKebabCase('hello_world')).toBe('hello-world');
  });

  it('應該將 PascalCase 轉為 kebab-case', () => {
    expect(toKebabCase('HelloWorld')).toBe('hello-world');
  });

  it('應該全部轉為小寫', () => {
    expect(toKebabCase('HELLO')).toBe('hello');
  });
});

describe('toCamelCase', () => {
  it('應該將 kebab-case 轉為 camelCase', () => {
    expect(toCamelCase('hello-world')).toBe('helloWorld');
  });

  it('應該將 snake_case 轉為 camelCase', () => {
    expect(toCamelCase('hello_world')).toBe('helloWorld');
  });

  it('應該將空格分隔轉為 camelCase', () => {
    expect(toCamelCase('hello world')).toBe('helloWorld');
  });

  it('首字母應該是小寫', () => {
    expect(toCamelCase('Hello-world')).toBe('helloWorld');
  });
});

// ============================================================================
// 狀態/優先級映射函數
// ============================================================================

describe('getStatusColor', () => {
  it('pending 應該回傳 warning', () => {
    expect(getStatusColor('pending')).toBe('warning');
  });

  it('in_progress 應該回傳 info', () => {
    expect(getStatusColor('in_progress')).toBe('info');
  });

  it('completed 應該回傳 success', () => {
    expect(getStatusColor('completed')).toBe('success');
  });

  it('cancelled 應該回傳 error', () => {
    expect(getStatusColor('cancelled')).toBe('error');
  });

  it('未知狀態應該回傳 default', () => {
    expect(getStatusColor('unknown')).toBe('default');
  });
});

describe('getStatusLabel', () => {
  it('pending 應該回傳「待處理」', () => {
    expect(getStatusLabel('pending')).toBe('待處理');
  });

  it('in_progress 應該回傳「處理中」', () => {
    expect(getStatusLabel('in_progress')).toBe('處理中');
  });

  it('completed 應該回傳「已完成」', () => {
    expect(getStatusLabel('completed')).toBe('已完成');
  });

  it('cancelled 應該回傳「已取消」', () => {
    expect(getStatusLabel('cancelled')).toBe('已取消');
  });

  it('未知狀態應該原樣回傳', () => {
    expect(getStatusLabel('custom_status')).toBe('custom_status');
  });
});

describe('getPriorityColor', () => {
  it('high 應該回傳 error', () => {
    expect(getPriorityColor('high')).toBe('error');
  });

  it('medium 應該回傳 warning', () => {
    expect(getPriorityColor('medium')).toBe('warning');
  });

  it('low 應該回傳 info', () => {
    expect(getPriorityColor('low')).toBe('info');
  });

  it('未知優先級應該回傳 default', () => {
    expect(getPriorityColor('critical')).toBe('default');
  });
});

describe('getPriorityLabel', () => {
  it('high 應該回傳「高」', () => {
    expect(getPriorityLabel('high')).toBe('高');
  });

  it('medium 應該回傳「中」', () => {
    expect(getPriorityLabel('medium')).toBe('中');
  });

  it('low 應該回傳「低」', () => {
    expect(getPriorityLabel('low')).toBe('低');
  });

  it('未知優先級應該原樣回傳', () => {
    expect(getPriorityLabel('critical')).toBe('critical');
  });
});

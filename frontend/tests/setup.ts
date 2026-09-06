/**
 * Vitest 測試環境設定
 * Test Environment Setup
 *
 * 此檔案在每個測試檔案執行前自動載入
 */
import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeAll, afterAll, vi } from 'vitest';

// 每個測試後自動清理
afterEach(() => {
  cleanup();
});

// Mock matchMedia (Ant Design 需要)
beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation(query => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });

  // Mock ResizeObserver
  global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));

  // jsdom 的 getComputedStyle 不支援 pseudo-element（AntD 會傳 '::after'）⇒ 'Not implemented' 錯誤 153 次。
  // ⚠️ 兩支回歸測試跑在 node environment（沒有 window）—— 這裡不守就是整支 suite 在 setup 階段 TypeError。
  // 註：node environment 下 window 可能存在（其他 setup 造的殼）但沒有 getComputedStyle ⇒ 判函式本身，不判 window
  if (typeof window !== 'undefined' && typeof window.getComputedStyle === 'function') {
    const _gcs = window.getComputedStyle.bind(window);
    window.getComputedStyle = ((el: Element, _pseudo?: string | null) => _gcs(el)) as typeof window.getComputedStyle;
    window.scrollTo = vi.fn();
  } else if (typeof window !== 'undefined') {
    window.scrollTo = vi.fn();
  }
});

// Mock import.meta.env
vi.stubGlobal('import', {
  meta: {
    env: {
      VITE_API_BASE_URL: 'http://localhost:8001',
      VITE_AUTH_DISABLED: 'true',
      MODE: 'test',
    },
  },
});

// Console 錯誤處理 (可選: 在測試中隱藏特定警告)
const originalError = console.error;
beforeAll(() => {
  console.error = (...args) => {
    // 過濾 React 18 的特定警告
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Warning: ReactDOM.render') ||
       args[0].includes('act(...)'))
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

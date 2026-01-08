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

  // Mock scrollTo
  window.scrollTo = vi.fn();
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

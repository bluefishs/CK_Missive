/**
 * ErrorBoundary 元件測試
 * ErrorBoundary Component Tests
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

// Mock logger
vi.mock('../../utils/logger', () => ({
  logger: {
    error: vi.fn(),
    warn: vi.fn(),
    log: vi.fn(),
    info: vi.fn(),
    debug: vi.fn(),
  },
}));

import { ErrorBoundary } from '../../components/common/ErrorBoundary';

// 會拋出錯誤的測試元件
const ThrowingComponent: React.FC<{ shouldThrow?: boolean }> = ({ shouldThrow = true }) => {
  if (shouldThrow) {
    throw new Error('測試錯誤');
  }
  return <div>正常渲染</div>;
};

// 正常的測試元件
const NormalComponent: React.FC = () => <div data-testid="normal">正常元件</div>;

describe('ErrorBoundary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // 抑制 React 錯誤邊界的 console.error
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  describe('正常渲染', () => {
    it('應該正常渲染子元件', () => {
      render(
        <ErrorBoundary>
          <NormalComponent />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('normal')).toBeInTheDocument();
    });

    it('應該渲染多個子元件', () => {
      render(
        <ErrorBoundary>
          <div data-testid="child-1">子元件 1</div>
          <div data-testid="child-2">子元件 2</div>
        </ErrorBoundary>
      );

      expect(screen.getByTestId('child-1')).toBeInTheDocument();
      expect(screen.getByTestId('child-2')).toBeInTheDocument();
    });
  });

  describe('錯誤捕獲', () => {
    it('應該捕獲子元件錯誤並顯示錯誤 UI', () => {
      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      );

      // 應該顯示錯誤相關的 UI
      expect(screen.queryByTestId('normal')).not.toBeInTheDocument();
    });

    it('應該顯示自定義 fallback', () => {
      const CustomFallback = <div data-testid="custom-fallback">自定義錯誤畫面</div>;

      render(
        <ErrorBoundary fallback={CustomFallback}>
          <ThrowingComponent />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
    });
  });

  describe('錯誤回調', () => {
    it('應該呼叫 onError 回調函數', () => {
      const onError = vi.fn();

      render(
        <ErrorBoundary onError={onError}>
          <ThrowingComponent />
        </ErrorBoundary>
      );

      expect(onError).toHaveBeenCalled();
    });

    it('onError 應該接收錯誤資訊', () => {
      const onError = vi.fn();

      render(
        <ErrorBoundary onError={onError}>
          <ThrowingComponent />
        </ErrorBoundary>
      );

      const [error, errorInfo] = onError.mock.calls[0];
      expect(error).toBeInstanceOf(Error);
      expect(error.message).toBe('測試錯誤');
      expect(errorInfo).toBeDefined();
    });
  });
});

// Note: withErrorBoundary HOC 未在此元件中匯出，跳過相關測試

/**
 * useIdleTimeout Hook 單元測試
 * useIdleTimeout Hook Unit Tests
 *
 * 測試閒置超時偵測功能
 *
 * 執行方式:
 *   cd frontend && npm run test -- useIdleTimeout
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// ============================================================================
// Mock 設定 (vi.mock 工廠內不可引用外部變數)
// ============================================================================

const mockNavigate = vi.fn();

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

// Mock authService - 在工廠內部定義
vi.mock('../../services/authService', () => {
  const service = {
    isAuthenticated: vi.fn().mockReturnValue(true),
    logout: vi.fn().mockResolvedValue(undefined),
  };
  return {
    default: service,
    authService: service,
  };
});

// Mock env config
vi.mock('../../config/env', () => ({
  isAuthDisabled: vi.fn().mockReturnValue(false),
}));

// Mock ROUTES
vi.mock('../../router/types', () => ({
  ROUTES: {
    LOGIN: '/login',
  },
}));

// Mock logger
vi.mock('../../utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

// 引入被測試的 hook 與 mock 模組 (放在 vi.mock 之後)
import { useIdleTimeout } from '../../hooks/utility/useIdleTimeout';
import authService from '../../services/authService';
import { isAuthDisabled } from '../../config/env';

// ============================================================================
// useIdleTimeout Hook 測試
// ============================================================================

describe('useIdleTimeout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    // 預設：認證已啟用、使用者已認證
    vi.mocked(isAuthDisabled).mockReturnValue(false);
    vi.mocked(authService.isAuthenticated).mockReturnValue(true);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // --------------------------------------------------------------------------
  // 基本行為
  // --------------------------------------------------------------------------

  it('應該在已認證時設定超時計時器', () => {
    renderHook(() => useIdleTimeout({ timeoutMs: 5000 }));

    // 計時器應該被設定
    expect(vi.getTimerCount()).toBe(1);
  });

  it('AUTH_DISABLED 模式下不應啟動計時器', () => {
    vi.mocked(isAuthDisabled).mockReturnValue(true);

    renderHook(() => useIdleTimeout({ timeoutMs: 5000 }));

    expect(vi.getTimerCount()).toBe(0);
  });

  it('未認證時不應啟動計時器', () => {
    vi.mocked(authService.isAuthenticated).mockReturnValue(false);

    renderHook(() => useIdleTimeout({ timeoutMs: 5000 }));

    expect(vi.getTimerCount()).toBe(0);
  });

  it('enabled=false 時不應啟動計時器', () => {
    renderHook(() => useIdleTimeout({ timeoutMs: 5000, enabled: false }));

    expect(vi.getTimerCount()).toBe(0);
  });

  // --------------------------------------------------------------------------
  // 超時觸發登出
  // --------------------------------------------------------------------------

  it('超時後應該呼叫 logout', () => {
    const timeoutMs = 5000;
    renderHook(() => useIdleTimeout({ timeoutMs }));

    // 快轉超過超時時間
    act(() => {
      vi.advanceTimersByTime(timeoutMs + 100);
    });

    expect(authService.logout).toHaveBeenCalled();
  });

  // --------------------------------------------------------------------------
  // 卸載時清理
  // --------------------------------------------------------------------------

  it('元件卸載時應該清理計時器', () => {
    const { unmount } = renderHook(() => useIdleTimeout({ timeoutMs: 5000 }));

    // 確認計時器存在
    expect(vi.getTimerCount()).toBe(1);

    // 卸載
    unmount();

    // 計時器應被清除
    expect(vi.getTimerCount()).toBe(0);
  });

  // --------------------------------------------------------------------------
  // 活動事件
  // --------------------------------------------------------------------------

  it('啟用時應該監聽使用者活動事件', () => {
    const addEventListenerSpy = vi.spyOn(window, 'addEventListener');

    renderHook(() => useIdleTimeout({ timeoutMs: 5000 }));

    // 應該監聽至少 mousemove, keydown 事件
    const registeredEvents = addEventListenerSpy.mock.calls.map(call => call[0]);
    expect(registeredEvents).toContain('mousemove');
    expect(registeredEvents).toContain('keydown');
    expect(registeredEvents).toContain('mousedown');
    expect(registeredEvents).toContain('touchstart');
    expect(registeredEvents).toContain('scroll');

    addEventListenerSpy.mockRestore();
  });
});

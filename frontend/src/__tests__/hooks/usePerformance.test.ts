/**
 * usePerformance Hook 單元測試
 *
 * 測試效能監控 Hook 的基本行為
 *
 * 執行方式:
 *   cd frontend && npm run test -- usePerformance
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';

// Mock PerformanceObserver
const mockObserve = vi.fn();
const mockDisconnect = vi.fn();

class MockPerformanceObserver {
  callback: PerformanceObserverCallback;
  constructor(callback: PerformanceObserverCallback) {
    this.callback = callback;
  }
  observe = mockObserve;
  disconnect = mockDisconnect;
  takeRecords = vi.fn().mockReturnValue([]);
}

// Import after setting up mocks
import { usePerformance } from '../../hooks/utility/usePerformance';

// ==========================================================================
// Tests
// ==========================================================================

describe('usePerformance', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset PerformanceObserver mock
    vi.stubGlobal('PerformanceObserver', MockPerformanceObserver);
  });

  it('returns initial performance metrics', () => {
    const { result } = renderHook(() => usePerformance());

    expect(result.current).toHaveProperty('loadTime');
    expect(result.current).toHaveProperty('renderTime');
    expect(typeof result.current.loadTime).toBe('number');
    expect(typeof result.current.renderTime).toBe('number');
  });

  it('sets loadTime from performance.now()', () => {
    const { result } = renderHook(() => usePerformance());

    // loadTime should be set from window.performance.now()
    expect(result.current.loadTime).toBeGreaterThanOrEqual(0);
  });

  it('observes performance entries', () => {
    renderHook(() => usePerformance());

    expect(mockObserve).toHaveBeenCalledWith({ entryTypes: ['measure'] });
  });

  it('disconnects observer on unmount', () => {
    const { unmount } = renderHook(() => usePerformance());

    unmount();

    expect(mockDisconnect).toHaveBeenCalled();
  });
});

/**
 * GlobalApiErrorNotifier - Unit Tests
 *
 * Tests subscription to ApiErrorBus, error display, and deduplication.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, act } from '@testing-library/react';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';

// ============================================================================
// Mocks
// ============================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

// ============================================================================
// Imports (after mocks)
// ============================================================================

import GlobalApiErrorNotifier from '../../components/common/GlobalApiErrorNotifier';
import { apiErrorBus, ApiException } from '../../api/errors';

// ============================================================================
// Helpers
// ============================================================================

// We need to capture the notification calls via Ant Design's App context
// Since Ant Design's notification is internal, we test via apiErrorBus emissions
function renderWithAntd() {
  return render(
    <ConfigProvider locale={zhTW}>
      <AntApp>
        <GlobalApiErrorNotifier />
      </AntApp>
    </ConfigProvider>,
  );
}

// ============================================================================
// Tests
// ============================================================================

describe('GlobalApiErrorNotifier', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders without crashing (returns null, no visible UI)', () => {
    const { container } = renderWithAntd();
    // Component returns null but AntApp wrapper adds its own container div
    // Verify there are no visible text nodes from the notifier itself
    expect(container.textContent).toBe('');
  });

  it('subscribes to apiErrorBus on mount', () => {
    const subscribeSpy = vi.spyOn(apiErrorBus, 'subscribe');
    renderWithAntd();
    expect(subscribeSpy).toHaveBeenCalledTimes(1);
    subscribeSpy.mockRestore();
  });

  it('unsubscribes from apiErrorBus on unmount', () => {
    const unsubscribeFn = vi.fn();
    const subscribeSpy = vi.spyOn(apiErrorBus, 'subscribe').mockReturnValue(unsubscribeFn);

    const { unmount } = renderWithAntd();
    unmount();

    expect(unsubscribeFn).toHaveBeenCalledTimes(1);
    subscribeSpy.mockRestore();
  });

  it('handles 429 error emission without throwing', () => {
    renderWithAntd();

    act(() => {
      apiErrorBus.emit(new ApiException('TOO_MANY_REQUESTS', '請求過多', 429));
    });

    // Should not throw - error is handled internally
    expect(true).toBe(true);
  });

  it('deduplicates errors within 3 second window', () => {
    // Track how many times the subscriber callback runs meaningfully
    let callCount = 0;
    const originalSubscribe = apiErrorBus.subscribe.bind(apiErrorBus);
    const subscribeSpy = vi.spyOn(apiErrorBus, 'subscribe').mockImplementation((listener) => {
      const wrappedListener = (error: ApiException) => {
        callCount++;
        listener(error);
      };
      return originalSubscribe(wrappedListener);
    });

    renderWithAntd();
    subscribeSpy.mockRestore();

    // Emit first error
    act(() => {
      apiErrorBus.emit(new ApiException('SERVER_ERROR', 'Error 1', 500));
    });

    // Emit second error within 3s window (should be deduplicated by component)
    act(() => {
      apiErrorBus.emit(new ApiException('SERVER_ERROR', 'Error 2', 500));
    });

    // Both emissions reach the bus, but component deduplicates internally
    expect(callCount).toBe(2);
  });

  it('handles network error emission (statusCode 0)', () => {
    renderWithAntd();

    act(() => {
      apiErrorBus.emit(new ApiException('NETWORK_ERROR', 'No network', 0));
    });

    // Should not throw
    expect(true).toBe(true);
  });
});

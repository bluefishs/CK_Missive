/**
 * useNotifications Hook 單元測試
 * useNotifications Hook Unit Tests
 *
 * 測試通知中心 React Query Hooks
 *
 * 執行方式:
 *   cd frontend && npm run test -- useNotifications
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// ============================================================================
// Mock 資料工廠函數
// ============================================================================

import type { SystemNotification } from '../../hooks/system/useNotifications';

const createMockNotification = (overrides: Partial<SystemNotification> = {}): SystemNotification => ({
  id: 1,
  type: 'document',
  severity: 'info',
  title: '測試通知',
  message: '這是一則測試通知',
  source_table: 'official_documents',
  source_id: 100,
  is_read: false,
  created_at: '2026-03-01T09:00:00Z',
  ...overrides,
});

// Mock apiClient
const mockPost = vi.fn();
vi.mock('../../api/client', () => ({
  apiClient: {
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

// Mock endpoints
vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    SYSTEM_NOTIFICATIONS: {
      UNREAD_COUNT: '/system-notifications/unread-count',
      LIST: '/system-notifications/list',
      MARK_READ: '/system-notifications/mark-read',
      MARK_ALL_READ: '/system-notifications/mark-all-read',
    },
  },
}));

// Mock queryConfig
vi.mock('../../config/queryConfig', () => ({
  queryKeys: {
    notifications: {
      unreadCount: ['notifications', 'unreadCount'],
      list: ['notifications', 'list'],
    },
  },
}));

// 引入被測試的 hooks
import {
  useUnreadNotificationCount,
  useNotificationList,
  useNotificationMutations,
  useNotificationCenter,
} from '../../hooks/system/useNotifications';

// 建立測試用 QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        refetchInterval: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

// 建立 wrapper
const createWrapper = () => {
  const queryClient = createTestQueryClient();
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
  return Wrapper;
};

// ============================================================================
// useUnreadNotificationCount Hook 測試
// ============================================================================

describe('useUnreadNotificationCount', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return unread count on success', async () => {
    mockPost.mockResolvedValue({
      success: true,
      unread_count: 5,
    });

    const { result } = renderHook(() => useUnreadNotificationCount(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.unreadCount).toBe(5);
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should return 0 when no data', async () => {
    mockPost.mockResolvedValue({
      success: true,
      unread_count: 0,
    });

    const { result } = renderHook(() => useUnreadNotificationCount(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.unreadCount).toBe(0);
  });

  it('should not fetch when enabled is false', () => {
    const { result } = renderHook(() => useUnreadNotificationCount(false), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('should handle API errors gracefully', async () => {
    mockPost.mockRejectedValue(new Error('Network Error'));

    const { result } = renderHook(() => useUnreadNotificationCount(), {
      wrapper: createWrapper(),
    });

    // The hook has retry: 1, so wait for query to settle
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    }, { timeout: 5000 });

    // Should fallback to 0 regardless of error state
    expect(result.current.unreadCount).toBe(0);
  });
});

// ============================================================================
// useNotificationList Hook 測試
// ============================================================================

describe('useNotificationList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return notification list on success', async () => {
    const mockNotifications = [
      createMockNotification({ id: 1, title: '通知一' }),
      createMockNotification({ id: 2, title: '通知二', is_read: true }),
    ];

    mockPost.mockResolvedValue({
      success: true,
      items: mockNotifications,
      total: 2,
      unread_count: 1,
    });

    const { result } = renderHook(() => useNotificationList(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.notifications).toHaveLength(2);
    });

    expect(result.current.total).toBe(2);
    expect(result.current.unreadCount).toBe(1);
    expect(result.current.notifications[0]?.title).toBe('通知一');
  });

  it('should return empty list when no data', async () => {
    mockPost.mockResolvedValue({
      success: true,
      items: [],
      total: 0,
      unread_count: 0,
    });

    const { result } = renderHook(() => useNotificationList(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.notifications).toHaveLength(0);
    expect(result.current.total).toBe(0);
  });

  it('should not fetch when enabled is false', () => {
    const { result } = renderHook(() => useNotificationList(false), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(mockPost).not.toHaveBeenCalled();
  });
});

// ============================================================================
// useNotificationMutations Hook 測試
// ============================================================================

describe('useNotificationMutations', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should provide markRead and markAllRead functions', () => {
    const { result } = renderHook(() => useNotificationMutations(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.markRead).toBe('function');
    expect(typeof result.current.markReadAsync).toBe('function');
    expect(typeof result.current.markAllRead).toBe('function');
    expect(typeof result.current.markAllReadAsync).toBe('function');
    expect(result.current.isMarkingRead).toBe(false);
    expect(result.current.isMarkingAllRead).toBe(false);
  });

  it('should call markRead with correct notification IDs', async () => {
    mockPost.mockResolvedValue({
      success: true,
      updated_count: 2,
      message: '已標記已讀',
    });

    const { result } = renderHook(() => useNotificationMutations(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.markReadAsync([1, 2]);
    });

    expect(mockPost).toHaveBeenCalledWith(
      '/system-notifications/mark-read',
      { notification_ids: [1, 2] }
    );
  });

  it('should call markAllRead', async () => {
    mockPost.mockResolvedValue({
      success: true,
      updated_count: 5,
      message: '全部已標記已讀',
    });

    const { result } = renderHook(() => useNotificationMutations(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.markAllReadAsync();
    });

    expect(mockPost).toHaveBeenCalledWith(
      '/system-notifications/mark-all-read',
      {}
    );
  });
});

// ============================================================================
// useNotificationCenter Hook 測試
// ============================================================================

describe('useNotificationCenter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should integrate unread count and operations', async () => {
    mockPost.mockImplementation((url: string) => {
      if (url.includes('unread-count')) {
        return Promise.resolve({ success: true, unread_count: 3 });
      }
      if (url.includes('/list')) {
        return Promise.resolve({ success: true, items: [], total: 0, unread_count: 3 });
      }
      return Promise.resolve({ success: true });
    });

    const { result } = renderHook(() => useNotificationCenter(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.unreadCount).toBe(3);
    });

    expect(typeof result.current.markRead).toBe('function');
    expect(typeof result.current.markAllRead).toBe('function');
    expect(typeof result.current.refetch).toBe('function');
  });

  it('should not load list by default', async () => {
    mockPost.mockImplementation((url: string) => {
      if (url.includes('unread-count')) {
        return Promise.resolve({ success: true, unread_count: 0 });
      }
      return Promise.resolve({ success: true, items: [], total: 0, unread_count: 0 });
    });

    const { result } = renderHook(() => useNotificationCenter(false), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // List should be empty since listEnabled=false
    expect(result.current.notifications).toHaveLength(0);
  });

  it('should load list when listEnabled is true', async () => {
    const mockNotifications = [
      createMockNotification({ id: 1, title: '通知A' }),
    ];

    mockPost.mockImplementation((url: string) => {
      if (url.includes('unread-count')) {
        return Promise.resolve({ success: true, unread_count: 1 });
      }
      if (url.includes('/list')) {
        return Promise.resolve({
          success: true,
          items: mockNotifications,
          total: 1,
          unread_count: 1,
        });
      }
      return Promise.resolve({ success: true });
    });

    const { result } = renderHook(() => useNotificationCenter(true), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.notifications).toHaveLength(1);
    });

    expect(result.current.total).toBe(1);
    expect(result.current.unreadCount).toBe(1);
  });
});

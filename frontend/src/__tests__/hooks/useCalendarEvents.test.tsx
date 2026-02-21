/**
 * useCalendar Hook 單元測試
 * useCalendar Hook Unit Tests
 *
 * 測試行事曆 React Query Hooks
 *
 * 執行方式:
 *   cd frontend && npm run test -- useCalendarEvents
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import dayjs from 'dayjs';
import isoWeek from 'dayjs/plugin/isoWeek';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
import type { CalendarEventUI, GoogleCalendarStatus } from '../../types/api';

// 載入 dayjs 插件 (useCalendar.ts 內部使用)
dayjs.extend(isoWeek);
dayjs.extend(isSameOrAfter);
dayjs.extend(isSameOrBefore);

// ============================================================================
// Mock 資料工廠函數
// ============================================================================

/** 建立完整的行事曆事件 Mock 資料 */
const createMockCalendarEvent = (overrides: Partial<CalendarEventUI> = {}): CalendarEventUI => ({
  id: 1,
  title: '測試事件',
  description: '測試描述',
  start_datetime: '2026-02-21T09:00:00Z',
  end_datetime: '2026-02-21T10:00:00Z',
  all_day: false,
  document_id: 100,
  doc_number: 'DOC-001',
  event_type: 'reminder',
  priority: 'medium',
  status: 'pending',
  location: '辦公室',
  google_event_id: undefined,
  google_sync_status: 'pending',
  ...overrides,
});

/** 建立 Google Calendar 狀態 Mock 資料 */
const createMockGoogleStatus = (overrides: Partial<GoogleCalendarStatus> = {}): GoogleCalendarStatus => ({
  google_calendar_available: true,
  connection_status: {
    status: 'connected',
    message: '已連線',
    calendars: [{ id: 'primary', summary: 'Primary Calendar', primary: true }],
  },
  service_type: '行事曆管理系統',
  supported_event_types: [
    { type: 'reminder', name: '提醒', color: '#faad14' },
    { type: 'deadline', name: '截止日期', color: '#f5222d' },
  ],
  features: ['本地行事曆', '事件提醒'],
  ...overrides,
});

// Mock calendarApi
vi.mock('../../api/calendarApi', () => ({
  calendarApi: {
    getEvents: vi.fn(),
    getGoogleStatus: vi.fn(),
    updateEvent: vi.fn(),
    deleteEvent: vi.fn(),
    bulkSync: vi.fn(),
  },
  DEFAULT_CATEGORIES: [
    { value: 'reminder', label: '提醒', color: '#faad14' },
    { value: 'deadline', label: '截止日期', color: '#f5222d' },
    { value: 'meeting', label: '會議', color: '#722ed1' },
    { value: 'review', label: '審查', color: '#1890ff' },
  ],
}));

// Mock queryConfig
vi.mock('../../config/queryConfig', () => ({
  queryKeys: {
    calendar: {
      all: ['calendar'],
      events: () => ['calendar', 'events'],
      googleStatus: () => ['calendar', 'googleStatus'],
    },
    dashboardCalendar: {
      all: ['dashboardCalendar'],
      events: () => ['dashboardCalendar', 'events'],
    },
  },
  defaultQueryOptions: {
    list: { staleTime: 5000 },
    detail: { staleTime: 10000 },
    dropdown: { staleTime: 60000 },
  },
}));

// 引入被測試的 hooks
import {
  useCalendarEvents,
  useGoogleCalendarStatus,
  useUpdateCalendarEvent,
  useDeleteCalendarEvent,
  useBulkSync,
  useCalendarPage,
} from '../../hooks/system/useCalendar';

import { calendarApi } from '../../api/calendarApi';

// 建立測試用 QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

// 建立 wrapper
const createWrapper = () => {
  const queryClient = createTestQueryClient();
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return Wrapper;
};

// ============================================================================
// useCalendarEvents Hook 測試
// ============================================================================

describe('useCalendarEvents', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得行事曆事件列表', async () => {
    const mockEvents = [
      createMockCalendarEvent({ id: 1, title: '事件A' }),
      createMockCalendarEvent({ id: 2, title: '事件B' }),
    ];

    vi.mocked(calendarApi.getEvents).mockResolvedValue(mockEvents);

    const { result } = renderHook(() => useCalendarEvents(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toHaveLength(2);
    expect(result.current.data?.[0]?.title).toBe('事件A');
  });

  it('應該處理空列表', async () => {
    vi.mocked(calendarApi.getEvents).mockResolvedValue([]);

    const { result } = renderHook(() => useCalendarEvents(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toHaveLength(0);
  });

  it('應該處理 API 錯誤', async () => {
    const error = new Error('API Error');
    vi.mocked(calendarApi.getEvents).mockRejectedValue(error);

    const { result } = renderHook(() => useCalendarEvents(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});

// ============================================================================
// useGoogleCalendarStatus Hook 測試
// ============================================================================

describe('useGoogleCalendarStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得 Google Calendar 狀態', async () => {
    const mockStatus = createMockGoogleStatus();

    vi.mocked(calendarApi.getGoogleStatus).mockResolvedValue(mockStatus);

    const { result } = renderHook(() => useGoogleCalendarStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.google_calendar_available).toBe(true);
    expect(result.current.data?.connection_status.status).toBe('connected');
  });
});

// ============================================================================
// Mutation Hooks 測試
// ============================================================================

describe('useUpdateCalendarEvent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功更新事件', async () => {
    vi.mocked(calendarApi.updateEvent).mockResolvedValue(undefined);

    const { result } = renderHook(() => useUpdateCalendarEvent(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync({
      eventId: 1,
      updates: { title: '更新後標題' },
    });

    expect(calendarApi.updateEvent).toHaveBeenCalledWith(1, {
      title: '更新後標題',
    });
  });
});

describe('useDeleteCalendarEvent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功刪除事件', async () => {
    vi.mocked(calendarApi.deleteEvent).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteCalendarEvent(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync(1);

    expect(calendarApi.deleteEvent).toHaveBeenCalledWith(1);
  });
});

describe('useBulkSync', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功批量同步', async () => {
    const mockSyncResult = {
      success: true,
      message: '同步完成',
      synced_count: 5,
      failed_count: 0,
    };

    vi.mocked(calendarApi.bulkSync).mockResolvedValue(mockSyncResult);

    const { result } = renderHook(() => useBulkSync(), {
      wrapper: createWrapper(),
    });

    const syncResult = await result.current.mutateAsync();

    expect(calendarApi.bulkSync).toHaveBeenCalled();
    expect(syncResult.synced_count).toBe(5);
  });
});

// ============================================================================
// useCalendarPage Hook 測試
// ============================================================================

describe('useCalendarPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(calendarApi.getEvents).mockResolvedValue([
      createMockCalendarEvent({ id: 1, title: '事件A' }),
      createMockCalendarEvent({ id: 2, title: '事件B' }),
    ]);

    vi.mocked(calendarApi.getGoogleStatus).mockResolvedValue(
      createMockGoogleStatus()
    );
  });

  it('應該整合事件列表與 Google 狀態', async () => {
    const { result } = renderHook(() => useCalendarPage(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.events).toHaveLength(2);
    expect(result.current.googleStatus?.google_calendar_available).toBe(true);
  });

  it('應該計算統計資料', async () => {
    const { result } = renderHook(() => useCalendarPage(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.stats).toBeDefined();
    expect(result.current.stats.total_events).toBe(2);
  });

  it('應該提供操作方法', async () => {
    const { result } = renderHook(() => useCalendarPage(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(typeof result.current.updateEvent).toBe('function');
    expect(typeof result.current.deleteEvent).toBe('function');
    expect(typeof result.current.bulkSync).toBe('function');
    expect(typeof result.current.refetch).toBe('function');
  });

  it('應該提供預設分類', async () => {
    const { result } = renderHook(() => useCalendarPage(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.categories).toBeDefined();
    expect(result.current.categories.length).toBeGreaterThan(0);
  });

  it('事件列表為空時統計應為零', async () => {
    vi.mocked(calendarApi.getEvents).mockResolvedValue([]);

    const { result } = renderHook(() => useCalendarPage(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.events).toHaveLength(0);
    expect(result.current.stats.total_events).toBe(0);
    expect(result.current.stats.today_events).toBe(0);
    expect(result.current.stats.this_week_events).toBe(0);
    expect(result.current.stats.this_month_events).toBe(0);
  });
});

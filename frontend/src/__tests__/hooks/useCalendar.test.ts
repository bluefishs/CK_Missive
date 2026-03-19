/**
 * useCalendar hooks 單元測試
 *
 * 測試行事曆 React Query Hooks (useCalendarEvents, useCalendarPage 等)
 *
 * 執行方式:
 *   cd frontend && npm run test -- useCalendar.test
 *
 * @version 1.0.0
 * @created 2026-03-16
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import dayjs from 'dayjs';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
import isoWeek from 'dayjs/plugin/isoWeek';
import { createWrapper } from '../../test/testUtils';

// Extend dayjs with required plugins (normally loaded at app entry)
dayjs.extend(isSameOrAfter);
dayjs.extend(isSameOrBefore);
dayjs.extend(isoWeek);

// ============================================================================
// Mocks
// ============================================================================

const mockGetEvents = vi.fn();
const mockGetGoogleStatus = vi.fn();
const mockUpdateEvent = vi.fn();
const mockDeleteEvent = vi.fn();
const mockBulkSync = vi.fn();

vi.mock('../../api/calendarApi', () => ({
  calendarApi: {
    getEvents: (...args: unknown[]) => mockGetEvents(...args),
    getGoogleStatus: (...args: unknown[]) => mockGetGoogleStatus(...args),
    updateEvent: (...args: unknown[]) => mockUpdateEvent(...args),
    deleteEvent: (...args: unknown[]) => mockDeleteEvent(...args),
    bulkSync: (...args: unknown[]) => mockBulkSync(...args),
  },
  DEFAULT_CATEGORIES: ['meeting', 'deadline', 'reminder'],
}));

vi.mock('../../config/queryConfig', () => ({
  queryKeys: {
    calendar: {
      all: ['calendar'],
      events: () => ['calendar', 'events'],
      googleStatus: () => ['calendar', 'googleStatus'],
    },
    dashboardCalendar: {
      all: ['dashboardCalendar'],
    },
  },
  defaultQueryOptions: {
    list: { staleTime: 30000 },
    dropdown: { staleTime: 300000 },
  },
}));

// Import after mocks
import {
  useCalendarEvents,
  useCalendarPage,
  useUpdateCalendarEvent,
  useDeleteCalendarEvent,
} from '../../hooks/system/useCalendar';

describe('useCalendar hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetEvents.mockResolvedValue([]);
    mockGetGoogleStatus.mockResolvedValue({ connected: false });
  });

  // ==========================================================================
  // useCalendarEvents
  // ==========================================================================

  describe('useCalendarEvents', () => {
    it('returns empty array initially while loading', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCalendarEvents(), { wrapper });

      expect(result.current.isLoading).toBe(true);
    });

    it('fetches events via calendarApi.getEvents', async () => {
      const mockEvents = [
        { id: 1, title: '會議', start_datetime: '2026-03-16T09:00:00Z' },
      ];
      mockGetEvents.mockResolvedValue(mockEvents);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useCalendarEvents(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockEvents);
      expect(mockGetEvents).toHaveBeenCalledTimes(1);
    });
  });

  // ==========================================================================
  // useUpdateCalendarEvent
  // ==========================================================================

  describe('useUpdateCalendarEvent', () => {
    it('exposes mutateAsync function', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useUpdateCalendarEvent(), { wrapper });

      expect(typeof result.current.mutateAsync).toBe('function');
      expect(result.current.isPending).toBe(false);
    });
  });

  // ==========================================================================
  // useDeleteCalendarEvent
  // ==========================================================================

  describe('useDeleteCalendarEvent', () => {
    it('exposes mutateAsync function', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useDeleteCalendarEvent(), { wrapper });

      expect(typeof result.current.mutateAsync).toBe('function');
      expect(result.current.isPending).toBe(false);
    });
  });

  // ==========================================================================
  // useCalendarPage
  // ==========================================================================

  describe('useCalendarPage', () => {
    it('returns default state with empty events', async () => {
      mockGetEvents.mockResolvedValue([]);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useCalendarPage(), { wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.events).toEqual([]);
      expect(result.current.stats.total_events).toBe(0);
      expect(result.current.categories).toEqual(['meeting', 'deadline', 'reminder']);
    });

    it('computes total_events from events array', async () => {
      // Use far-future dates to avoid isSameOrAfter/isSameOrBefore edge cases
      mockGetEvents.mockResolvedValue([
        { id: 1, title: 'A', start_datetime: '2099-01-01T09:00:00Z' },
        { id: 2, title: 'B', start_datetime: '2099-06-15T09:00:00Z' },
      ]);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useCalendarPage(), { wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.stats.total_events).toBe(2);
    });

    it('exposes mutation functions', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCalendarPage(), { wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(typeof result.current.updateEvent).toBe('function');
      expect(typeof result.current.deleteEvent).toBe('function');
      expect(typeof result.current.bulkSync).toBe('function');
      expect(result.current.isUpdating).toBe(false);
      expect(result.current.isDeleting).toBe(false);
      expect(result.current.isSyncing).toBe(false);
    });
  });
});

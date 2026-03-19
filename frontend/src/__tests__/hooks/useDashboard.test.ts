/**
 * useDashboard hooks 單元測試
 *
 * 測試儀表板 React Query Hooks (useDashboardData, useDashboardPage)
 *
 * 執行方式:
 *   cd frontend && npm run test -- useDashboard.test
 *
 * @version 1.0.0
 * @created 2026-03-16
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { createWrapper } from '../../test/testUtils';

// ============================================================================
// Mocks
// ============================================================================

const mockGetDashboardData = vi.fn();
const mockFormatRecentDocuments = vi.fn();

vi.mock('../../api/dashboardApi', () => ({
  dashboardApi: {
    getDashboardData: (...args: unknown[]) => mockGetDashboardData(...args),
    formatRecentDocuments: (...args: unknown[]) => mockFormatRecentDocuments(...args),
  },
}));

vi.mock('../../config/queryConfig', () => ({
  defaultQueryOptions: {
    detail: { staleTime: 60000 },
  },
}));

// Import after mocks
import { useDashboardData, useDashboardPage } from '../../hooks/system/useDashboard';

describe('useDashboard hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetDashboardData.mockResolvedValue({
      stats: { total: 0, approved: 0, pending: 0, rejected: 0 },
      recent_documents: [],
    });
    mockFormatRecentDocuments.mockReturnValue([]);
  });

  // ==========================================================================
  // useDashboardData
  // ==========================================================================

  describe('useDashboardData', () => {
    it('starts in loading state', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useDashboardData(), { wrapper });

      expect(result.current.isLoading).toBe(true);
    });

    it('fetches dashboard data successfully', async () => {
      const mockData = {
        stats: { total: 100, approved: 50, pending: 30, rejected: 20 },
        recent_documents: [{ id: 1, subject: '測試公文' }],
      };
      mockGetDashboardData.mockResolvedValue(mockData);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useDashboardData(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockData);
    });
  });

  // ==========================================================================
  // useDashboardPage
  // ==========================================================================

  describe('useDashboardPage', () => {
    it('returns default stats when data has no stats', async () => {
      mockGetDashboardData.mockResolvedValue({});

      const wrapper = createWrapper();
      const { result } = renderHook(() => useDashboardPage(), { wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.stats).toEqual({
        total: 0,
        approved: 0,
        pending: 0,
        rejected: 0,
      });
      expect(result.current.recentDocuments).toEqual([]);
    });

    it('formats recent documents when data is available', async () => {
      const rawDocs = [{ id: 1, subject: '公文A' }];
      const formattedDocs = [{ id: 1, subject: '公文A', formatted: true }];

      mockGetDashboardData.mockResolvedValue({
        stats: { total: 10, approved: 5, pending: 3, rejected: 2 },
        recent_documents: rawDocs,
      });
      mockFormatRecentDocuments.mockReturnValue(formattedDocs);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useDashboardPage(), { wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.stats.total).toBe(10);
      expect(result.current.recentDocuments).toEqual(formattedDocs);
      expect(mockFormatRecentDocuments).toHaveBeenCalledWith(rawDocs);
    });

    it('exposes refetch function', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useDashboardPage(), { wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(typeof result.current.refetch).toBe('function');
    });
  });
});

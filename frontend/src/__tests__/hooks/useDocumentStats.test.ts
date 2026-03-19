/**
 * useDocumentStats hook 單元測試
 *
 * 測試公文統計 React Query Hook
 *
 * 執行方式:
 *   cd frontend && npm run test -- useDocumentStats.test
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

const mockPost = vi.fn();

vi.mock('../../api/client', () => ({
  apiClient: {
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    DOCUMENTS: {
      STATISTICS: '/documents-enhanced/statistics',
    },
  },
}));

vi.mock('../../config/queryConfig', () => ({
  queryKeys: {
    documents: {
      statistics: ['documents', 'statistics'],
    },
  },
}));

// Import after mocks
import { useDocumentStats } from '../../hooks/system/useDocumentStats';

describe('useDocumentStats', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPost.mockResolvedValue({
      total: 0,
      pending: 0,
      approved: 0,
      rejected: 0,
      draft: 0,
    });
  });

  it('starts in loading state', () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDocumentStats(), { wrapper });

    expect(result.current.isLoading).toBe(true);
  });

  it('fetches document statistics successfully', async () => {
    const mockStats = {
      total: 150,
      pending: 30,
      approved: 100,
      rejected: 10,
      draft: 10,
    };
    mockPost.mockResolvedValue(mockStats);

    const wrapper = createWrapper();
    const { result } = renderHook(() => useDocumentStats(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockStats);
    expect(mockPost).toHaveBeenCalledWith('/documents-enhanced/statistics');
  });

  it('handles API error gracefully', async () => {
    mockPost.mockRejectedValue(new Error('Server error'));

    const wrapper = createWrapper();
    const { result } = renderHook(() => useDocumentStats(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeTruthy();
  });
});

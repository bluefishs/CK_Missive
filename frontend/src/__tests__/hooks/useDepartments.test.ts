/**
 * useDepartments hook 單元測試
 *
 * 測試部門選項 React Query Hook
 *
 * 執行方式:
 *   cd frontend && npm run test -- useDepartments.test
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

const mockGetDepartments = vi.fn();

vi.mock('../../api/usersApi', () => ({
  usersApi: {
    getDepartments: (...args: unknown[]) => mockGetDepartments(...args),
  },
}));

// Import after mocks
import { useDepartments } from '../../hooks/system/useDepartments';

describe('useDepartments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetDepartments.mockResolvedValue([]);
  });

  it('starts in loading state', () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDepartments(), { wrapper });

    expect(result.current.isLoading).toBe(true);
  });

  it('fetches departments list successfully', async () => {
    const mockData = [
      { value: 'engineering', label: '工程部' },
      { value: 'admin', label: '行政部' },
      { value: 'finance', label: '財務部' },
    ];
    mockGetDepartments.mockResolvedValue(mockData);

    const wrapper = createWrapper();
    const { result } = renderHook(() => useDepartments(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockData);
    expect(mockGetDepartments).toHaveBeenCalledTimes(1);
  });

  it('handles API error gracefully', async () => {
    mockGetDepartments.mockRejectedValue(new Error('Network error'));

    const wrapper = createWrapper();
    const { result } = renderHook(() => useDepartments(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeTruthy();
    expect(result.current.data).toBeUndefined();
  });
});

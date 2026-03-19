/**
 * useVendorsWithStore Hook 單元測試
 *
 * 測試廠商管理整合 Hook (React Query + Zustand) 基本結構
 *
 * 執行方式:
 *   cd frontend && npm run test -- useVendorsWithStore
 */
import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { createWrapper, createMockPaginatedResponse } from '../../test/testUtils';

// ==========================================================================
// Mocks
// ==========================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

const mockPost = vi.fn();
vi.mock('../../api/client', () => ({
  apiClient: {
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

vi.mock('../../api/endpoints', () => ({
  VENDORS_ENDPOINTS: {
    LIST: '/vendors/list',
    DETAIL: (id: number) => `/vendors/${id}`,
    CREATE: '/vendors/create',
    UPDATE: (id: number) => `/vendors/${id}/update`,
    DELETE: (id: number) => `/vendors/${id}/delete`,
  },
}));

// Import after mocks
import { useVendorsWithStore } from '../../hooks/business/useVendorsWithStore';

// ==========================================================================
// Tests
// ==========================================================================

describe('useVendorsWithStore', () => {
  it('returns expected shape with all properties', () => {
    mockPost.mockResolvedValue(createMockPaginatedResponse([]));

    const { result } = renderHook(() => useVendorsWithStore(), {
      wrapper: createWrapper(),
    });

    expect(Array.isArray(result.current.vendors)).toBe(true);
    expect(result.current.selectedVendor).toBeNull();
    expect(result.current.filters).toBeDefined();
    expect(result.current.pagination).toBeDefined();
    expect(typeof result.current.isLoading).toBe('boolean');
    expect(typeof result.current.isError).toBe('boolean');
    expect(typeof result.current.loading).toBe('boolean');
  });

  it('exposes CRUD mutation flags as false initially', () => {
    mockPost.mockResolvedValue(createMockPaginatedResponse([]));

    const { result } = renderHook(() => useVendorsWithStore(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isCreating).toBe(false);
    expect(result.current.isUpdating).toBe(false);
    expect(result.current.isDeleting).toBe(false);
  });

  it('exposes all required action functions', () => {
    mockPost.mockResolvedValue(createMockPaginatedResponse([]));

    const { result } = renderHook(() => useVendorsWithStore(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.createVendor).toBe('function');
    expect(typeof result.current.updateVendor).toBe('function');
    expect(typeof result.current.deleteVendor).toBe('function');
    expect(typeof result.current.setPage).toBe('function');
    expect(typeof result.current.setFilters).toBe('function');
    expect(typeof result.current.resetFilters).toBe('function');
    expect(typeof result.current.refetch).toBe('function');
    expect(typeof result.current.selectVendor).toBe('function');
  });
});

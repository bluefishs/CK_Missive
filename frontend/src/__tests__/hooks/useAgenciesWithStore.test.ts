/**
 * useAgenciesWithStore Hook 單元測試
 *
 * 測試機關管理整合 Hook (React Query + Zustand) 基本結構
 *
 * 執行方式:
 *   cd frontend && npm run test -- useAgenciesWithStore
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
  AGENCIES_ENDPOINTS: {
    LIST: '/agencies/list',
    DETAIL: (id: number) => `/agencies/${id}`,
    CREATE: '/agencies/create',
    UPDATE: (id: number) => `/agencies/${id}/update`,
    DELETE: (id: number) => `/agencies/${id}/delete`,
  },
}));

// Import after mocks
import { useAgenciesWithStore } from '../../hooks/business/useAgenciesWithStore';

// ==========================================================================
// Tests
// ==========================================================================

describe('useAgenciesWithStore', () => {
  it('returns expected shape with all properties', () => {
    mockPost.mockResolvedValue(createMockPaginatedResponse([]));

    const { result } = renderHook(() => useAgenciesWithStore(), {
      wrapper: createWrapper(),
    });

    expect(Array.isArray(result.current.agencies)).toBe(true);
    expect(result.current.selectedAgency).toBeNull();
    expect(result.current.filters).toBeDefined();
    expect(result.current.pagination).toBeDefined();
    expect(typeof result.current.isLoading).toBe('boolean');
    expect(typeof result.current.isError).toBe('boolean');
    expect(typeof result.current.loading).toBe('boolean');
  });

  it('exposes CRUD mutation flags as false initially', () => {
    mockPost.mockResolvedValue(createMockPaginatedResponse([]));

    const { result } = renderHook(() => useAgenciesWithStore(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isCreating).toBe(false);
    expect(result.current.isUpdating).toBe(false);
    expect(result.current.isDeleting).toBe(false);
  });

  it('exposes all required action functions', () => {
    mockPost.mockResolvedValue(createMockPaginatedResponse([]));

    const { result } = renderHook(() => useAgenciesWithStore(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.createAgency).toBe('function');
    expect(typeof result.current.updateAgency).toBe('function');
    expect(typeof result.current.deleteAgency).toBe('function');
    expect(typeof result.current.setPage).toBe('function');
    expect(typeof result.current.setFilters).toBe('function');
    expect(typeof result.current.resetFilters).toBe('function');
    expect(typeof result.current.refetch).toBe('function');
    expect(typeof result.current.selectAgency).toBe('function');
  });
});

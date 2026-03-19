/**
 * useProjectsWithStore Hook 單元測試
 *
 * 測試專案管理整合 Hook (React Query + Zustand) 基本結構
 *
 * 執行方式:
 *   cd frontend && npm run test -- useProjectsWithStore
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
  PROJECTS_ENDPOINTS: {
    LIST: '/projects/list',
    DETAIL: (id: number) => `/projects/${id}`,
    CREATE: '/projects/create',
    UPDATE: (id: number) => `/projects/${id}/update`,
    DELETE: (id: number) => `/projects/${id}/delete`,
    STATISTICS: '/projects/statistics',
    YEAR_OPTIONS: '/projects/year-options',
    CATEGORY_OPTIONS: '/projects/category-options',
    STATUS_OPTIONS: '/projects/status-options',
  },
}));

// Import after mocks
import { useProjectsWithStore } from '../../hooks/business/useProjectsWithStore';

// ==========================================================================
// Tests
// ==========================================================================

describe('useProjectsWithStore', () => {
  it('returns expected shape with all properties', () => {
    mockPost.mockResolvedValue(createMockPaginatedResponse([]));

    const { result } = renderHook(() => useProjectsWithStore(), {
      wrapper: createWrapper(),
    });

    expect(Array.isArray(result.current.projects)).toBe(true);
    expect(result.current.selectedProject).toBeNull();
    expect(result.current.filters).toBeDefined();
    expect(result.current.pagination).toBeDefined();
    expect(typeof result.current.isLoading).toBe('boolean');
    expect(typeof result.current.isError).toBe('boolean');
    expect(typeof result.current.loading).toBe('boolean');
  });

  it('exposes CRUD mutation flags as false initially', () => {
    mockPost.mockResolvedValue(createMockPaginatedResponse([]));

    const { result } = renderHook(() => useProjectsWithStore(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isCreating).toBe(false);
    expect(result.current.isUpdating).toBe(false);
    expect(result.current.isDeleting).toBe(false);
  });

  it('exposes all required action functions', () => {
    mockPost.mockResolvedValue(createMockPaginatedResponse([]));

    const { result } = renderHook(() => useProjectsWithStore(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.createProject).toBe('function');
    expect(typeof result.current.updateProject).toBe('function');
    expect(typeof result.current.deleteProject).toBe('function');
    expect(typeof result.current.setPage).toBe('function');
    expect(typeof result.current.setFilters).toBe('function');
    expect(typeof result.current.resetFilters).toBe('function');
    expect(typeof result.current.refetch).toBe('function');
    expect(typeof result.current.selectProject).toBe('function');
  });
});

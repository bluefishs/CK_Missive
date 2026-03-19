/**
 * useDocumentsWithStore Hook 單元測試
 *
 * 測試公文管理整合 Hook (React Query + Zustand) 基本結構
 *
 * 執行方式:
 *   cd frontend && npm run test -- useDocumentsWithStore
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
  DOCUMENTS_ENDPOINTS: {
    LIST: '/documents-enhanced/list',
    DETAIL: (id: number) => `/documents-enhanced/${id}`,
    CREATE: '/documents-enhanced/create',
    UPDATE: (id: number) => `/documents-enhanced/${id}/update`,
    DELETE: (id: number) => `/documents-enhanced/${id}/delete`,
    STATISTICS: '/documents-enhanced/statistics',
    YEAR_OPTIONS: '/documents-enhanced/year-options',
    CONTRACT_PROJECT_OPTIONS: '/documents-enhanced/contract-project-options',
  },
}));

// Import after mocks
import { useDocumentsWithStore } from '../../hooks/business/useDocumentsWithStore';

// ==========================================================================
// Tests
// ==========================================================================

describe('useDocumentsWithStore', () => {
  it('returns expected shape with all properties', () => {
    mockPost.mockResolvedValue(createMockPaginatedResponse([]));

    const { result } = renderHook(() => useDocumentsWithStore(), {
      wrapper: createWrapper(),
    });

    // Verify the hook returns expected structure
    expect(Array.isArray(result.current.documents)).toBe(true);
    expect(result.current.selectedDocument).toBeNull();
    expect(result.current.filters).toBeDefined();
    expect(result.current.pagination).toBeDefined();
    expect(typeof result.current.isLoading).toBe('boolean');
    expect(typeof result.current.isError).toBe('boolean');
  });

  it('exposes CRUD mutation flags as false initially', () => {
    mockPost.mockResolvedValue(createMockPaginatedResponse([]));

    const { result } = renderHook(() => useDocumentsWithStore(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isCreating).toBe(false);
    expect(result.current.isUpdating).toBe(false);
    expect(result.current.isDeleting).toBe(false);
  });

  it('exposes all required action functions', () => {
    mockPost.mockResolvedValue(createMockPaginatedResponse([]));

    const { result } = renderHook(() => useDocumentsWithStore(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.createDocument).toBe('function');
    expect(typeof result.current.updateDocument).toBe('function');
    expect(typeof result.current.deleteDocument).toBe('function');
    expect(typeof result.current.setPage).toBe('function');
    expect(typeof result.current.setFilters).toBe('function');
    expect(typeof result.current.resetFilters).toBe('function');
    expect(typeof result.current.refetch).toBe('function');
    expect(typeof result.current.selectDocument).toBe('function');
  });
});

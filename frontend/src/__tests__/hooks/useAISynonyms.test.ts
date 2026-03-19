/**
 * useAISynonyms hooks 單元測試
 *
 * 測試 AI 同義詞管理 React Query Hooks
 *
 * 執行方式:
 *   cd frontend && npm run test -- useAISynonyms.test
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

const mockListSynonyms = vi.fn();
const mockCreateSynonym = vi.fn();
const mockUpdateSynonym = vi.fn();
const mockDeleteSynonym = vi.fn();
const mockReloadSynonyms = vi.fn();

vi.mock('../../api/aiApi', () => ({
  aiApi: {
    listSynonyms: (...args: unknown[]) => mockListSynonyms(...args),
    createSynonym: (...args: unknown[]) => mockCreateSynonym(...args),
    updateSynonym: (...args: unknown[]) => mockUpdateSynonym(...args),
    deleteSynonym: (...args: unknown[]) => mockDeleteSynonym(...args),
    reloadSynonyms: (...args: unknown[]) => mockReloadSynonyms(...args),
  },
}));

vi.mock('../../config/queryConfig', () => ({
  queryKeys: {
    aiSynonyms: {
      all: ['aiSynonyms'],
      list: (params: object) => ['aiSynonyms', 'list', params],
    },
  },
  defaultQueryOptions: {
    list: { staleTime: 30000 },
  },
}));

// Import after mocks
import {
  useAISynonyms,
  useCreateSynonym,
  useUpdateSynonym,
  useDeleteSynonym,
  useReloadSynonyms,
} from '../../hooks/system/useAISynonyms';

describe('useAISynonyms hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListSynonyms.mockResolvedValue([]);
  });

  // ==========================================================================
  // useAISynonyms
  // ==========================================================================

  describe('useAISynonyms', () => {
    it('starts in loading state', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAISynonyms(), { wrapper });

      expect(result.current.isLoading).toBe(true);
    });

    it('fetches synonym list successfully', async () => {
      const mockData = [
        { id: 1, canonical: '公文', synonyms: ['公函', '函文'], category: 'document' },
        { id: 2, canonical: '機關', synonyms: ['單位', '部門'], category: 'agency' },
      ];
      mockListSynonyms.mockResolvedValue(mockData);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useAISynonyms(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockData);
    });

    it('passes filter params to API', async () => {
      const params = { category: 'document' };
      const wrapper = createWrapper();
      renderHook(() => useAISynonyms(params), { wrapper });

      await waitFor(() => expect(mockListSynonyms).toHaveBeenCalledWith(params));
    });
  });

  // ==========================================================================
  // useCreateSynonym
  // ==========================================================================

  describe('useCreateSynonym', () => {
    it('exposes mutateAsync function', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCreateSynonym(), { wrapper });

      expect(typeof result.current.mutateAsync).toBe('function');
      expect(result.current.isPending).toBe(false);
    });
  });

  // ==========================================================================
  // useUpdateSynonym
  // ==========================================================================

  describe('useUpdateSynonym', () => {
    it('exposes mutateAsync function', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useUpdateSynonym(), { wrapper });

      expect(typeof result.current.mutateAsync).toBe('function');
      expect(result.current.isPending).toBe(false);
    });
  });

  // ==========================================================================
  // useDeleteSynonym
  // ==========================================================================

  describe('useDeleteSynonym', () => {
    it('exposes mutateAsync function', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useDeleteSynonym(), { wrapper });

      expect(typeof result.current.mutateAsync).toBe('function');
      expect(result.current.isPending).toBe(false);
    });
  });

  // ==========================================================================
  // useReloadSynonyms
  // ==========================================================================

  describe('useReloadSynonyms', () => {
    it('exposes mutateAsync function', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useReloadSynonyms(), { wrapper });

      expect(typeof result.current.mutateAsync).toBe('function');
      expect(result.current.isPending).toBe(false);
    });
  });
});

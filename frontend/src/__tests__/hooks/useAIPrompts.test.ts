/**
 * useAIPrompts hooks 單元測試
 *
 * 測試 AI Prompt 版本管理 React Query Hooks
 *
 * 執行方式:
 *   cd frontend && npm run test -- useAIPrompts.test
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

const mockListPrompts = vi.fn();
const mockCreatePrompt = vi.fn();
const mockActivatePrompt = vi.fn();
const mockComparePrompts = vi.fn();

vi.mock('../../api/aiApi', () => ({
  aiApi: {
    listPrompts: (...args: unknown[]) => mockListPrompts(...args),
    createPrompt: (...args: unknown[]) => mockCreatePrompt(...args),
    activatePrompt: (...args: unknown[]) => mockActivatePrompt(...args),
    comparePrompts: (...args: unknown[]) => mockComparePrompts(...args),
  },
}));

vi.mock('../../config/queryConfig', () => ({
  queryKeys: {
    aiPrompts: {
      all: ['aiPrompts'],
      list: (feature?: string | null) => ['aiPrompts', 'list', feature],
    },
  },
  defaultQueryOptions: {
    list: { staleTime: 30000 },
  },
}));

// Import after mocks
import {
  useAIPrompts,
  useCreatePrompt,
  useActivatePrompt,
  useComparePrompts,
} from '../../hooks/system/useAIPrompts';

describe('useAIPrompts hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListPrompts.mockResolvedValue([]);
  });

  // ==========================================================================
  // useAIPrompts
  // ==========================================================================

  describe('useAIPrompts', () => {
    it('starts in loading state', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAIPrompts(), { wrapper });

      expect(result.current.isLoading).toBe(true);
    });

    it('fetches prompt list successfully', async () => {
      const mockData = [
        { id: 1, feature: 'summary', version: 1, content: '摘要提示', is_active: true },
        { id: 2, feature: 'summary', version: 2, content: '摘要提示v2', is_active: false },
      ];
      mockListPrompts.mockResolvedValue(mockData);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useAIPrompts(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockData);
      expect(mockListPrompts).toHaveBeenCalledWith(undefined);
    });

    it('passes feature filter to API', async () => {
      const wrapper = createWrapper();
      renderHook(() => useAIPrompts('classification'), { wrapper });

      await waitFor(() => expect(mockListPrompts).toHaveBeenCalledWith('classification'));
    });
  });

  // ==========================================================================
  // useCreatePrompt
  // ==========================================================================

  describe('useCreatePrompt', () => {
    it('exposes mutateAsync function', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCreatePrompt(), { wrapper });

      expect(typeof result.current.mutateAsync).toBe('function');
      expect(result.current.isPending).toBe(false);
    });
  });

  // ==========================================================================
  // useActivatePrompt
  // ==========================================================================

  describe('useActivatePrompt', () => {
    it('exposes mutateAsync function', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useActivatePrompt(), { wrapper });

      expect(typeof result.current.mutateAsync).toBe('function');
      expect(result.current.isPending).toBe(false);
    });
  });

  // ==========================================================================
  // useComparePrompts
  // ==========================================================================

  describe('useComparePrompts', () => {
    it('exposes mutateAsync function', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useComparePrompts(), { wrapper });

      expect(typeof result.current.mutateAsync).toBe('function');
      expect(result.current.isPending).toBe(false);
    });
  });
});

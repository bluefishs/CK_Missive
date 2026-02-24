/**
 * AI Prompt 版本管理 React Query Hooks
 *
 * 整合 queryConfig 統一快取策略
 *
 * @version 1.0.0
 * @date 2026-02-24
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { aiApi } from '../../api/aiApi';
import type { PromptCreateRequest } from '../../types/ai';
import { queryKeys, defaultQueryOptions } from '../../config/queryConfig';

// ============================================================================
// 查詢 Hooks
// ============================================================================

/**
 * 取得 Prompt 版本列表
 */
export const useAIPrompts = (feature?: string | null) => {
  return useQuery({
    queryKey: queryKeys.aiPrompts.list(feature),
    queryFn: () => aiApi.listPrompts(feature || undefined),
    ...defaultQueryOptions.list,
  });
};

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * 新增 Prompt 版本
 */
export const useCreatePrompt = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: PromptCreateRequest) => aiApi.createPrompt(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.aiPrompts.all });
    },
  });
};

/**
 * 啟用 Prompt 版本
 */
export const useActivatePrompt = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => aiApi.activatePrompt(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.aiPrompts.all });
    },
  });
};

/**
 * 比較 Prompt 版本
 */
export const useComparePrompts = () => {
  return useMutation({
    mutationFn: ({ idA, idB }: { idA: number; idB: number }) =>
      aiApi.comparePrompts(idA, idB),
  });
};

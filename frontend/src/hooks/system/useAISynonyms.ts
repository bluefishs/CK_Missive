/**
 * AI 同義詞管理 React Query Hooks
 *
 * 整合 queryConfig 統一快取策略
 *
 * @version 1.0.0
 * @date 2026-02-24
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { aiApi } from '../../api/aiApi';
import type {
  AISynonymListRequest,
  AISynonymCreateRequest,
  AISynonymUpdateRequest,
} from '../../types/ai';
import { queryKeys, defaultQueryOptions } from '../../config/queryConfig';

// ============================================================================
// 查詢 Hooks
// ============================================================================

/**
 * 取得同義詞列表
 */
export const useAISynonyms = (params?: AISynonymListRequest) => {
  return useQuery({
    queryKey: queryKeys.aiSynonyms.list(params || {}),
    queryFn: () => aiApi.listSynonyms(params),
    ...defaultQueryOptions.list,
  });
};

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * 新增同義詞群組
 */
export const useCreateSynonym = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AISynonymCreateRequest) => aiApi.createSynonym(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.aiSynonyms.all });
    },
  });
};

/**
 * 更新同義詞群組
 */
export const useUpdateSynonym = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AISynonymUpdateRequest) => aiApi.updateSynonym(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.aiSynonyms.all });
    },
  });
};

/**
 * 刪除同義詞群組
 */
export const useDeleteSynonym = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => aiApi.deleteSynonym(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.aiSynonyms.all });
    },
  });
};

/**
 * 重新載入同義詞（同步到後端記憶體）
 */
export const useReloadSynonyms = () => {
  return useMutation({
    mutationFn: () => aiApi.reloadSynonyms(),
  });
};

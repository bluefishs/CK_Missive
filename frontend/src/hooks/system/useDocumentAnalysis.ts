/**
 * 公文 AI 分析 React Query Hooks
 *
 * 提供分析結果查詢與觸發分析的 hooks。
 *
 * @version 1.0.0
 * @date 2026-02-28
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { aiApi } from '../../api/aiApi';
import { queryKeys, defaultQueryOptions } from '../../config/queryConfig';

/**
 * 取得公文 AI 分析結果
 *
 * 自動查詢指定公文的持久化分析結果。
 * 若尚未分析則回傳 null（API 回 404 時靜默處理）。
 */
export const useDocumentAnalysis = (documentId: number | undefined) => {
  return useQuery({
    queryKey: queryKeys.aiAnalysis.detail(documentId!),
    queryFn: () => aiApi.getDocumentAnalysis(documentId!),
    enabled: !!documentId,
    ...defaultQueryOptions.detail,
  });
};

/**
 * 觸發公文 AI 分析 Mutation
 *
 * 成功後自動 invalidate 該公文的分析快取。
 */
export const useTriggerAnalysis = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ documentId, force = false }: { documentId: number; force?: boolean }) =>
      aiApi.triggerDocumentAnalysis(documentId, force),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.aiAnalysis.detail(variables.documentId),
      });
    },
  });
};

/**
 * AI 分析覆蓋率統計
 */
export const useAnalysisStats = () => {
  return useQuery({
    queryKey: queryKeys.aiAnalysis.stats,
    queryFn: () => aiApi.getAnalysisStats(),
    ...defaultQueryOptions.statistics,
  });
};

/**
 * useDeleteWorkRecord - 作業紀錄刪除共用 Hook
 *
 * 從 DispatchWorkflowTab 和 ProjectWorkOverviewTab 提取的共用刪除 mutation。
 *
 * @version 1.0.0
 * @date 2026-03-04
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { workflowApi } from '../../../api/taoyuan';
import { logger } from '../../../services/logger';

interface UseDeleteWorkRecordOptions {
  /** 需要 invalidate 的 query keys */
  invalidateKeys: readonly (readonly (string | number)[])[];
  /** logger 前綴 */
  logPrefix?: string;
}

export function useDeleteWorkRecord({
  invalidateKeys,
  logPrefix = 'WorkRecord',
}: UseDeleteWorkRecordOptions) {
  const queryClient = useQueryClient();
  const { message } = App.useApp();

  return useMutation({
    mutationFn: (id: number) => workflowApi.delete(id),
    onSuccess: () => {
      message.success('作業紀錄已刪除');
      for (const key of invalidateKeys) {
        queryClient.invalidateQueries({ queryKey: key });
      }
    },
    onError: (error: Error) => {
      logger.error(`[${logPrefix}] 刪除失敗:`, error);
      message.error('刪除失敗，請稍後再試');
    },
  });
}

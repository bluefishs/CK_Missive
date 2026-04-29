/**
 * useDispatchCacheInvalidator
 *
 * 派工 write-side 與 read-side 之間的 cache 契約集中化。
 *
 * 領域問題：
 *   派工總覽 (`/taoyuan/dispatch?tab=0`) 的 `dispatch-morning-status` query
 *   是「下游讀視圖」。任何「上游寫操作」(派工 / 作業紀錄 / 看板狀態 / 訂閱)
 *   都必須 invalidate 它，否則前端顯示與後端真實狀態漂移。
 *
 * 過去做法：每個 mutation 自己 `queryClient.invalidateQueries(...)`，9 處散落，
 *   新增 mutation 容易遺漏（v5.10.x 曾發生）。
 *
 * 領域驅動解：把 cache 契約封裝成 aggregate-root method。新 mutation 從這
 *   幾個方法擇一，無從遺漏。
 *
 * 使用：
 *   const cache = useDispatchCacheInvalidator();
 *   ...
 *   onSuccess: () => {
 *     cache.invalidateDispatchAggregate(); // 派工本體更新
 *     // 或
 *     cache.invalidateWorkRecord();        // 作業紀錄變動
 *     // 或
 *     cache.invalidateProjectLinks();      // 工程關聯變動
 *     // 或
 *     cache.invalidateMorningStatusOnly(); // 僅 morning-status (極少數場景)
 *   }
 */

import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../config/queryConfig';

const MORNING_STATUS_KEY = ['dispatch-morning-status'] as const;

export function useDispatchCacheInvalidator() {
  const queryClient = useQueryClient();

  /**
   * 派工本體寫操作後 — 派工 list/detail 全鏈 + 晨報視圖
   * 適用：派工單 CRUD / display_status 更新
   */
  const invalidateDispatchAggregate = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
    queryClient.invalidateQueries({ queryKey: MORNING_STATUS_KEY });
  };

  /**
   * 作業紀錄變動 — 影響 work_progress 計算 → 派工總覽 morning-status
   * 適用：work_record CRUD / 內聯建立
   */
  const invalidateWorkRecord = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
    queryClient.invalidateQueries({ queryKey: MORNING_STATUS_KEY });
  };

  /**
   * 工程關聯變動 — dispatch + projects + 文件關聯 + 晨報視圖
   * 適用：linkProject / unlinkProject / createProject (隱含 link)
   */
  const invalidateProjectLinks = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
    queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanProjects.all });
    queryClient.invalidateQueries({ queryKey: ['document-project-links'] });
    queryClient.invalidateQueries({ queryKey: MORNING_STATUS_KEY });
  };

  /**
   * 看板狀態切換 — kanban-workflow 自身 + 晨報視圖
   * 適用：KanbanBoardTab statusMutation
   */
  const invalidateKanbanStatus = (projectId?: number) => {
    if (projectId !== undefined) {
      queryClient.invalidateQueries({ queryKey: ['kanban-workflow', projectId] });
    }
    queryClient.invalidateQueries({ queryKey: MORNING_STATUS_KEY });
  };

  /**
   * 僅 morning-status — 極少數場景（如交付期限直接更新）
   */
  const invalidateMorningStatusOnly = () => {
    queryClient.invalidateQueries({ queryKey: MORNING_STATUS_KEY });
  };

  return {
    invalidateDispatchAggregate,
    invalidateWorkRecord,
    invalidateProjectLinks,
    invalidateKanbanStatus,
    invalidateMorningStatusOnly,
  };
}

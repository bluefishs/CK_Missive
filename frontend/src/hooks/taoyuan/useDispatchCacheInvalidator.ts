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
const KANBAN_DISPATCHES_KEY = ['kanban-dispatches'] as const;
// 2026-05-20 chronic fix — queryKey drift L39（dispatch=158 第二次發作根因）：
// 真實 useTaoyuanDispatchOrders 用 queryKeys.taoyuanDispatch.orders() = ['taoyuan-dispatch-orders', params]，
// 過去 invalidate 寫 ['dispatch-orders'] 不重疊 → 永遠不生效（同 L29 dict-key drift 反模式）。
// 同時保留舊 key 防其他散戶 query 使用。
const DISPATCH_ORDERS_KEY = ['taoyuan-dispatch-orders'] as const;
const DISPATCH_ORDERS_LEGACY_KEY = ['dispatch-orders'] as const;
const DISPATCH_ORDER_DETAIL_LEGACY_KEY = ['dispatch-order-detail'] as const;
// 2026-05-21 chronic fix — L39 第 14 處（dispatch=146 batch_no 修改後詳情/列表不一致）：
// 真實 useTaoyuanDispatchOrder 用 queryKeys.taoyuanDispatch.order(id) = ['taoyuan-dispatch-order', id]，
// 上方 ['dispatch-order-detail'] 與 ['taoyuan-dispatch-order'] prefix 完全不重疊 → 詳情族永不被 invalidate。
const DISPATCH_ORDER_DETAIL_KEY = ['taoyuan-dispatch-order'] as const;

/**
 * 派工列表/看板/詳情 — 跨頁面共用「列表族」key（不在 queryKeys.taoyuanDispatch.all 樹下）
 *
 * 2026-05-18 fix（dispatch=158 案例 v1）：DB 已 unlink 公文但前端列表仍顯示舊文號的根因是
 *   `useDispatchDocLinking` 只 invalidate 詳情 ['dispatch-order-detail']，但列表 query
 *   ['dispatch-morning-status'] + ['kanban-dispatches'] + ['dispatch-orders'] 從未被清。
 *
 * 2026-05-20 fix（dispatch=158 案例 v2 / chronic 根因）：上述 5/18 修法的 ['dispatch-orders']
 *   key 與真實 query key ['taoyuan-dispatch-orders'] **完全不重疊**！invalidate 永遠 silent
 *   不生效（L39 同 L29 dict-key drift 反模式）。本檔已改用 ['taoyuan-dispatch-orders']。
 *
 * 統一在此一處，所有 mutation 必要時呼叫 invalidateAllDispatchLists() 避免遺漏。
 */
const DISPATCH_LIST_FAMILY_KEYS = [
  MORNING_STATUS_KEY,
  KANBAN_DISPATCHES_KEY,
  DISPATCH_ORDERS_KEY,                // 真實 list query key (5/20 修)
  DISPATCH_ORDERS_LEGACY_KEY,         // 舊 key（防其他散戶 query 還用著）
  DISPATCH_ORDER_DETAIL_KEY,          // 真實 detail query key (5/21 L39 第 14 處修)
  DISPATCH_ORDER_DETAIL_LEGACY_KEY,   // 舊 detail key (防 historical 散戶)
  ['dispatch-orders-for-link'] as const,
  ['kanban-workflow'] as const,
] as const;

export function useDispatchCacheInvalidator() {
  const queryClient = useQueryClient();

  // 內部 helper — 全列表族一次清
  const _invalidateAllListFamily = () => {
    for (const key of DISPATCH_LIST_FAMILY_KEYS) {
      queryClient.invalidateQueries({ queryKey: key });
    }
  };

  /**
   * 派工本體寫操作後 — 派工 list/detail 全鏈 + 晨報視圖 + 列表族
   * 適用：派工單 CRUD / display_status 更新 / 自動匹配公文 / link/unlink 公文
   *
   * v5.18 擴充：加入 KANBAN_DISPATCHES + DISPATCH_ORDERS + DETAIL（解 158 案例）
   */
  const invalidateDispatchAggregate = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
    queryClient.invalidateQueries({ queryKey: DISPATCH_ORDER_DETAIL_KEY });          // 真實 detail family (5/21 修)
    queryClient.invalidateQueries({ queryKey: DISPATCH_ORDER_DETAIL_LEGACY_KEY });   // 舊 key 保險
    _invalidateAllListFamily();
  };

  /**
   * 作業紀錄變動 — 影響 work_progress 計算 → 派工總覽 morning-status
   * 適用：work_record CRUD / 內聯建立
   */
  const invalidateWorkRecord = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
    _invalidateAllListFamily();
  };

  /**
   * 工程關聯變動 — dispatch + projects + 文件關聯 + 晨報視圖 + 列表族
   * 適用：linkProject / unlinkProject / createProject (隱含 link)
   */
  const invalidateProjectLinks = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
    queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanProjects.all });
    queryClient.invalidateQueries({ queryKey: ['document-project-links'] });
    _invalidateAllListFamily();
  };

  /**
   * 公文關聯變動 — dispatch detail + 公文列表 + 派工列表族
   * 適用：link/unlink/auto-match 公文（含後端 cascade — 刪公文時前端應呼叫此方法）
   *
   * 2026-05-18 新增：解 dispatch=158「DB 已 unlink 但前端仍顯示」根因
   */
  const invalidateDocumentLinks = (dispatchId?: number) => {
    queryClient.invalidateQueries({ queryKey: DISPATCH_ORDER_DETAIL_KEY });
    if (dispatchId !== undefined) {
      queryClient.invalidateQueries({ queryKey: ['dispatch-documents', dispatchId] });
    } else {
      queryClient.invalidateQueries({ queryKey: ['dispatch-documents'] });
    }
    queryClient.invalidateQueries({ queryKey: ['document-dispatch-links'] });
    _invalidateAllListFamily();
  };

  /**
   * 看板狀態切換 — kanban-workflow + 列表族
   * 適用：KanbanBoardTab statusMutation
   */
  const invalidateKanbanStatus = (projectId?: number) => {
    if (projectId !== undefined) {
      queryClient.invalidateQueries({ queryKey: ['kanban-workflow', projectId] });
    }
    _invalidateAllListFamily();
  };

  /**
   * 僅 morning-status — 極少數場景（如交付期限直接更新）
   */
  const invalidateMorningStatusOnly = () => {
    queryClient.invalidateQueries({ queryKey: MORNING_STATUS_KEY });
  };

  /**
   * 全列表族 — 給跨 module mutation（如刪公文後 cascade 影響派工）
   * 2026-05-18 新增
   */
  const invalidateAllDispatchLists = _invalidateAllListFamily;

  return {
    invalidateDispatchAggregate,
    invalidateWorkRecord,
    invalidateProjectLinks,
    invalidateDocumentLinks,
    invalidateKanbanStatus,
    invalidateMorningStatusOnly,
    invalidateAllDispatchLists,
  };
}

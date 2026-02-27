/**
 * 派工紀錄匯出邏輯 Hook
 *
 * 從 DispatchOrdersTab 提取的匯出功能，包含：
 * - 同步匯出（小量資料 <= 200 筆）
 * - 非同步匯出 + 進度輪詢（大量資料）
 * - 輪詢失敗自動停止（最多 10 次失敗）
 * - 元件卸載時自動清理 polling interval
 *
 * @version 1.0.0
 * @date 2026-02-27
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { dispatchOrdersApi } from '../../../api/taoyuanDispatchApi';

export interface ExportProgress {
  progress: number;
  message: string;
}

export interface UseDispatchOrderExportParams {
  /** Contract project ID for export filtering */
  contractProjectId: number;
  /** Search text for export filtering */
  searchText: string;
  /** Total number of orders (determines sync vs async export) */
  orderCount: number;
  /** Ant Design message API instance */
  message: {
    success: (content: string) => void;
    error: (content: string) => void;
  };
}

export interface UseDispatchOrderExportReturn {
  /** Whether an export operation is in progress */
  exporting: boolean;
  /** Current export progress (null when not actively tracking async progress) */
  exportProgress: ExportProgress | null;
  /** Trigger the master Excel export */
  handleExportMasterExcel: () => Promise<void>;
}

const ASYNC_THRESHOLD = 200;
const MAX_POLL_FAILURES = 10;
const POLL_INTERVAL_MS = 2000;

/**
 * Custom hook that encapsulates dispatch order export logic,
 * including synchronous export for small datasets and asynchronous
 * export with progress polling for larger datasets.
 */
export function useDispatchOrderExport({
  contractProjectId,
  searchText,
  orderCount,
  message,
}: UseDispatchOrderExportParams): UseDispatchOrderExportReturn {
  const [exporting, setExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState<ExportProgress | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollFailCountRef = useRef(0);

  // Clean up polling interval on unmount
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, []);

  const handleExportMasterExcel = useCallback(async () => {
    // Small dataset: synchronous export
    if (orderCount <= ASYNC_THRESHOLD) {
      setExporting(true);
      try {
        await dispatchOrdersApi.exportMasterExcel({
          contract_project_id: contractProjectId,
          search: searchText || undefined,
        });
        message.success('匯出成功');
      } catch {
        message.error('匯出失敗');
      } finally {
        setExporting(false);
      }
      return;
    }

    // Large dataset: async export with progress polling
    setExporting(true);
    setExportProgress({ progress: 0, message: '提交匯出任務...' });

    try {
      const { task_id } = await dispatchOrdersApi.submitAsyncExport({
        contract_project_id: contractProjectId,
        search: searchText || undefined,
      });

      // Start polling for progress
      pollFailCountRef.current = 0;
      pollTimerRef.current = setInterval(async () => {
        try {
          const status = await dispatchOrdersApi.getExportProgress(task_id);
          pollFailCountRef.current = 0; // Reset on success

          setExportProgress({ progress: status.progress, message: status.message });

          if (status.status === 'completed') {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
            setExportProgress(null);
            setExporting(false);

            // Auto-download
            await dispatchOrdersApi.downloadAsyncExport(task_id, status.filename);
            message.success('匯出完成');
          } else if (status.status === 'failed') {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
            setExportProgress(null);
            setExporting(false);
            message.error(status.message || '匯出失敗');
          }
        } catch {
          pollFailCountRef.current += 1;
          if (pollFailCountRef.current >= MAX_POLL_FAILURES) {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
            setExportProgress(null);
            setExporting(false);
            message.error('匯出進度查詢失敗，請稍後重試');
          }
        }
      }, POLL_INTERVAL_MS);
    } catch {
      setExportProgress(null);
      setExporting(false);
      message.error('提交匯出任務失敗');
    }
  }, [contractProjectId, searchText, message, orderCount]);

  return {
    exporting,
    exportProgress,
    handleExportMasterExcel,
  };
}

export default useDispatchOrderExport;

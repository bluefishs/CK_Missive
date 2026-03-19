/**
 * useGraphDataLoader - 圖譜資料載入 Hook
 *
 * 負責：
 * - 外部資料注入模式 (externalGraphData)
 * - 內部 API 載入模式 (dataProvider)
 * - loading / error 狀態管理
 *
 * @version 1.0.0
 * @created 2026-03-18
 */

import { useState, useEffect, useCallback } from 'react';
import type { GraphNode, GraphEdge } from '../../../types/ai';
import type { ExternalGraphData, GraphDataProvider } from '../KnowledgeGraph';

interface UseGraphDataLoaderParams {
  documentIds: number[];
  externalGraphData?: ExternalGraphData | null;
  onExternalRefresh?: () => void;
  dataProvider: GraphDataProvider;
}

interface UseGraphDataLoaderReturn {
  rawNodes: GraphNode[];
  rawEdges: GraphEdge[];
  loading: boolean;
  error: string | null;
  setRawNodes: React.Dispatch<React.SetStateAction<GraphNode[]>>;
  setRawEdges: React.Dispatch<React.SetStateAction<GraphEdge[]>>;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
  /** Reset state and reload data */
  reload: () => void;
}

export function useGraphDataLoader({
  documentIds,
  externalGraphData,
  onExternalRefresh,
  dataProvider,
}: UseGraphDataLoaderParams): UseGraphDataLoaderReturn {
  const [rawNodes, setRawNodes] = useState<GraphNode[]>([]);
  const [rawEdges, setRawEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  // 外部資料注入模式
  useEffect(() => {
    if (!externalGraphData) return;
    setRawNodes(externalGraphData.nodes);
    setRawEdges(externalGraphData.edges);
    setLoading(false);
    setError(null);
  }, [externalGraphData]);

  // 內部 API 載入模式
  useEffect(() => {
    if (externalGraphData) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    dataProvider
      .loadGraph({ document_ids: documentIds })
      .then((result) => {
        if (cancelled) return;
        if (result) {
          setRawNodes(result.nodes);
          setRawEdges(result.edges);
        } else {
          setRawNodes([]);
          setRawEdges([]);
        }
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : '載入關聯圖譜失敗');
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // reloadKey triggers re-fetch
  }, [documentIds, externalGraphData, dataProvider, reloadKey]);

  const reload = useCallback(() => {
    setError(null);

    if (externalGraphData && onExternalRefresh) {
      onExternalRefresh();
      return;
    }

    setRawNodes([]);
    setRawEdges([]);
    setReloadKey((k) => k + 1);
  }, [externalGraphData, onExternalRefresh]);

  return {
    rawNodes,
    rawEdges,
    loading,
    error,
    setRawNodes,
    setRawEdges,
    setError,
    reload,
  };
}

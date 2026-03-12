/**
 * KnowledgeGraph - 公文關聯網絡互動式視覺化元件 v3.2
 *
 * 使用 react-force-graph-2d 實現力導向佈局：
 * - 物理模擬自動排列節點
 * - 縮放/平移/拖曳節點
 * - 點擊節點高亮鄰居 + 右側詳情面板
 * - 搜尋過濾、類型過濾
 * - 方向箭頭 + 邊標籤
 * - Phase 2 正規化實體詳情側邊欄
 *
 * 節點按類型分色：公文=藍, 專案=綠, 機關=橙, 派工=紫
 * 實體節點大小 ∝ mention_count，邊粗細 ∝ weight
 *
 * v3.2: Extracted types, constants, force-graph render callbacks
 *
 * @version 3.2.0
 * @created 2026-02-24
 * @updated 2026-02-27 — 拆分 types / render callbacks / toolbar / search hook
 */

import React, { useState, useMemo, useCallback, useEffect, useRef, lazy, Suspense } from 'react';
import { Spin, Empty } from 'antd';
import ForceGraph2D, { type ForceGraphMethods } from 'react-force-graph-2d';
import { aiApi } from '../../api/aiApi';
import type { GraphNode, GraphEdge } from '../../types/ai';
import {
  CANONICAL_ENTITY_TYPES,
  GRAPH_NODE_CONFIG,
  getNodeConfig,
  getAllMergedConfigs,
} from '../../config/graphNodeConfig';
import type { GraphNodeTypeConfig } from '../../config/graphNodeConfig';
import { EntityDetailSidebar } from './EntityDetailSidebar';
import { GraphNodeSettings } from './GraphNodeSettings';
import { GraphToolbar } from './knowledgeGraph/GraphToolbar';
import { SelectedNodeInfoCard } from './knowledgeGraph/SelectedNodeInfoCard';
import { useGraphSearch } from './knowledgeGraph/useGraphSearch';
import { useForceGraphCallbacks } from './knowledgeGraph/useForceGraphCallbacks';
import { useForceGraph3DCallbacks } from './knowledgeGraph/useForceGraph3DCallbacks';
import { useGraphAgentBridgeOptional } from './knowledgeGraph/GraphAgentBridge';
import type { NavigateEvent, SummaryResultEvent, DrawResultEvent } from './knowledgeGraph/GraphAgentBridge';
import type { ForceNode, GraphData } from './knowledgeGraph/types';

// Lazy load 3D graph（three.js 較大，按需載入）
const ForceGraph3D = lazy(() => import('react-force-graph-3d'));

// ============================================================================
// Props
// ============================================================================

export interface ExternalGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

/**
 * 圖譜資料提供者介面 — 用於解耦 API 呼叫，實現模組化移植。
 * 不提供時使用內建的 aiApi.getRelationGraph。
 */
export interface GraphDataProvider {
  /** 載入圖譜資料 */
  loadGraph: (params: { document_ids: number[] }) => Promise<ExternalGraphData | null>;
}

export interface KnowledgeGraphProps {
  documentIds: number[];
  height?: number;
  /** 外部注入的圖譜資料（Code Wiki 等），提供時跳過內部 API 請求 */
  externalGraphData?: ExternalGraphData | null;
  /** 外部重新載入回調（搭配 externalGraphData 使用） */
  onExternalRefresh?: () => void;
  /** 預設維度（2D 或 3D） */
  defaultDimension?: '2d' | '3d';
  /** 節點點擊外部回調（供父元件處理交叉導航等） */
  onNodeClickExternal?: (node: { id: string; label: string; type: string }) => void;
  /** 自訂資料提供者（移植時替換 API 來源） */
  dataProvider?: GraphDataProvider;
  /** 自訂節點類型配置（移植時覆蓋預設的 GRAPH_NODE_CONFIG） */
  nodeConfig?: Record<string, GraphNodeTypeConfig>;
}

// ============================================================================
// 主元件
// ============================================================================

/** 預設 dataProvider：使用內建 aiApi */
const defaultProvider: GraphDataProvider = {
  loadGraph: async (params) => {
    const result = await aiApi.getRelationGraph({ document_ids: params.document_ids });
    return result ? { nodes: result.nodes, edges: result.edges } : null;
  },
};

export const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({
  documentIds,
  height = 700,
  externalGraphData,
  onExternalRefresh,
  defaultDimension = '2d',
  onNodeClickExternal,
  dataProvider = defaultProvider,
  nodeConfig,
}) => {
  // 衍生配置函數（支援自訂 nodeConfig 覆蓋）
  const effectiveConfig = nodeConfig ?? GRAPH_NODE_CONFIG;
  const effectiveGetNode = useCallback(
    (type: string) => getNodeConfig(type),
    // getNodeConfig uses GRAPH_NODE_CONFIG internally — if nodeConfig is provided, override
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );
  const effectiveGetNodeConfig = nodeConfig
    ? (type: string) => effectiveConfig[type] ?? { color: '#999999', radius: 5, label: '未知', detailable: false, description: '未知類型的節點' }
    : effectiveGetNode;
  const effectiveDetailable = useMemo(
    () =>
      nodeConfig
        ? new Set(Object.entries(nodeConfig).filter(([, c]) => c.detailable).map(([t]) => t))
        : CANONICAL_ENTITY_TYPES,
    [nodeConfig],
  );

  const fgRef = useRef<ForceGraphMethods | undefined>();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fg3dRef = useRef<any>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(800);
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [dimension, setDimension] = useState<'2d' | '3d'>(defaultDimension);

  // GraphAgentBridge（可選 — 在 Provider 外使用時為 null）
  const bridge = useGraphAgentBridgeOptional();

  // API 狀態
  const [rawNodes, setRawNodes] = useState<GraphNode[]>([]);
  const [rawEdges, setRawEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 互動狀態
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [visibleTypes, setVisibleTypes] = useState<Set<string>>(() => {
    const configs = getAllMergedConfigs();
    return new Set(
      Object.entries(configs)
        .filter(([, cfg]) => cfg.visible)
        .map(([type]) => type)
    );
  });

  // 節點設定面板
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [configVersion, setConfigVersion] = useState(0);

  // 當前圖譜中實際出現的節點類型（供 GraphNodeSettings 過濾用）
  const activeNodeTypes = useMemo(() => new Set(rawNodes.map((n) => n.type)), [rawNodes]);

  // 設定面板儲存後，同步工具列勾選狀態
  useEffect(() => {
    if (configVersion === 0) return;
    const configs = getAllMergedConfigs();
    setVisibleTypes(new Set(
      Object.entries(configs)
        .filter(([, cfg]) => cfg.visible)
        .map(([type]) => type)
    ));
  }, [configVersion]);

  // Entity Detail Sidebar 狀態
  const [sidebarVisible, setSidebarVisible] = useState(false);
  const [sidebarEntityName, setSidebarEntityName] = useState('');
  const [sidebarEntityType, setSidebarEntityType] = useState('');

  // Search hook
  const {
    searchText,
    setSearchText,
    setApiSearchMatchIds,
    apiSearching,
    handleSearchSubmit,
    searchMatchIds,
    aliasHint,
  } = useGraphSearch({ rawNodes });

  // 容器寬度偵測
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // 側邊欄開啟時，圖譜 canvas 有效寬度需扣除 Drawer 寬度
  const SIDEBAR_WIDTH = 380;
  const effectiveWidth = Math.max(
    (containerWidth - (sidebarVisible ? SIDEBAR_WIDTH : 0)) - 2,
    300,
  );

  // 容器寬度或側邊欄狀態變化時重新適配
  const prevWidthRef = useRef(containerWidth);
  const prevSidebarRef = useRef(sidebarVisible);
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const widthChanged = Math.abs(containerWidth - prevWidthRef.current) > 10;
    const sidebarChanged = sidebarVisible !== prevSidebarRef.current;
    if ((widthChanged || sidebarChanged) && rawNodes.length > 0) {
      timer = setTimeout(() => {
        fgRef.current?.zoomToFit(400, 60);
        if (dimension === '3d') fg3dRef.current?.zoomToFit(400, 60);
      }, 300);
    }
    prevWidthRef.current = containerWidth;
    prevSidebarRef.current = sidebarVisible;
    return () => { if (timer) clearTimeout(timer); };
  }, [containerWidth, rawNodes.length, sidebarVisible, dimension]);

  // 外部資料注入模式
  useEffect(() => {
    if (!externalGraphData) return;
    setRawNodes(externalGraphData.nodes);
    setRawEdges(externalGraphData.edges);
    setLoading(false);
    setError(null);
    setSelectedNodeId(null);
  }, [externalGraphData]);

  // 內部 API 載入模式（無外部資料時）
  // 注意：documentIds 為空時後端會自動載入預設公文（_load_default_doc_ids）
  useEffect(() => {
    if (externalGraphData) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setSelectedNodeId(null);

    dataProvider.loadGraph({ document_ids: documentIds }).then((result) => {
      if (cancelled) return;
      if (result) {
        setRawNodes(result.nodes);
        setRawEdges(result.edges);
      } else {
        setRawNodes([]);
        setRawEdges([]);
      }
      setLoading(false);
    }).catch((err) => {
      if (cancelled) return;
      setError(err instanceof Error ? err.message : '載入關聯圖譜失敗');
      setLoading(false);
    });

    return () => { cancelled = true; };
  }, [documentIds, externalGraphData, dataProvider]);

  // 鄰居 lookup
  const neighborMap = useMemo(() => {
    const map = new Map<string, Set<string>>();
    for (const edge of rawEdges) {
      if (!map.has(edge.source)) map.set(edge.source, new Set());
      if (!map.has(edge.target)) map.set(edge.target, new Set());
      map.get(edge.source)!.add(edge.target);
      map.get(edge.target)!.add(edge.source);
    }
    return map;
  }, [rawEdges]);

  // 使用者合併配置快取（隨 configVersion 更新）
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const mergedConfigs = useMemo(() => getAllMergedConfigs(effectiveConfig), [configVersion, effectiveConfig]);

  // 轉換為 force-graph 格式（過濾孤立節點避免飄散）
  const graphData = useMemo((): GraphData => {
    const filteredNodes = rawNodes.filter((n) => {
      if (!visibleTypes.has(n.type)) return false;
      const cfg = mergedConfigs[n.type];
      if (cfg && !cfg.visible) return false;
      return true;
    });
    const nodeIdSet = new Set(filteredNodes.map((n) => n.id));

    const links = rawEdges
      .filter((e) => nodeIdSet.has(e.source) && nodeIdSet.has(e.target))
      .map((e) => ({
        source: e.source,
        target: e.target,
        label: e.label,
        type: e.type,
        weight: e.weight ?? undefined,
      }));

    // 收集有邊連接的節點 ID，過濾孤立節點（無邊的節點會飄散）
    const connectedIds = new Set<string>();
    for (const link of links) {
      connectedIds.add(link.source);
      connectedIds.add(link.target);
    }

    const nodes: ForceNode[] = filteredNodes
      .filter((n) => connectedIds.has(n.id))
      .map((n) => ({
        id: n.id,
        label: n.label,
        type: n.type,
        color: mergedConfigs[n.type]?.color ?? effectiveGetNodeConfig(n.type).color,
        category: n.category,
        doc_number: n.doc_number,
        status: n.status,
        mention_count: n.mention_count ?? undefined,
      }));

    return { nodes, links };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rawNodes, rawEdges, visibleTypes, mergedConfigs]);

  // D3: O(1) 節點查找索引（避免 500+ 節點時 O(n) find）
  const nodeByLabel = useMemo(() => {
    const map = new Map<string, ForceNode>();
    for (const n of graphData.nodes) {
      map.set(n.label, n);
    }
    return map;
  }, [graphData.nodes]);

  // Force-graph 渲染回調 (2D)
  const {
    paintNode,
    nodePointerAreaPaint,
    linkColor,
    linkWidth,
    linkDirectionalArrowColor,
    linkCanvasObject,
  } = useForceGraphCallbacks({
    mergedConfigs,
    selectedNodeId,
    hoveredNodeId,
    searchMatchIds,
    neighborMap,
  });

  // Force-graph 渲染回調 (3D)
  const graph3dCallbacks = useForceGraph3DCallbacks({
    mergedConfigs,
    selectedNodeId,
    hoveredNodeId,
    searchMatchIds,
    neighborMap,
  });

  // 點擊節點（2D/3D 共用）
  const handleNodeClick = useCallback((node: ForceNode) => {
    const newSelected = selectedNodeId === node.id ? null : node.id;
    setSelectedNodeId(newSelected);

    if (newSelected && effectiveDetailable.has(node.type)) {
      setSidebarEntityName(node.label);
      setSidebarEntityType(node.type);
      setSidebarVisible(true);

      // 三位一體：通知 Agent 生成摘要（如果 Bridge 存在）
      const entityIdNum = parseInt(node.id.replace(/^entity_/, ''), 10);
      if (bridge && !isNaN(entityIdNum)) {
        bridge.requestSummary(entityIdNum, node.label, node.type);
      }
    } else {
      setSidebarVisible(false);
    }

    // B6: 外部節點點擊回調（交叉導航）
    if (newSelected && onNodeClickExternal) {
      onNodeClickExternal({ id: node.id, label: node.label, type: node.type });
    }

    // 3D fly-to 動畫：鏡頭飛向被選取的節點
    if (newSelected && dimension === '3d' && fg3dRef.current && node.x != null && node.y != null) {
      const distance = 120;
      const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z ?? 0);
      fg3dRef.current.cameraPosition(
        { x: node.x * distRatio, y: node.y * distRatio, z: (node.z ?? 0) * distRatio },
        { x: node.x, y: node.y, z: node.z ?? 0 },
        1000,
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedNodeId, dimension, bridge, onNodeClickExternal]);

  // Hover 節點
  const handleNodeHover = useCallback((node: ForceNode | null) => {
    if (hoverTimerRef.current) {
      clearTimeout(hoverTimerRef.current);
      hoverTimerRef.current = null;
    }
    if (node) {
      setHoveredNodeId(node.id);
    } else {
      hoverTimerRef.current = setTimeout(() => {
        setHoveredNodeId(null);
      }, 150);
    }
    if (containerRef.current) {
      containerRef.current.style.cursor = node ? 'pointer' : 'default';
    }
  }, []);

  // 配置 d3 力導向參數：加強向心力、調整排斥力
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    // 向心力：將節點拉向中心，避免分散（強度 0.05）
    fg.d3Force('center')?.strength?.(0.05);
    // 連結距離：根據節點數量動態調整
    const nodeCount = graphData.nodes.length;
    const linkDist = nodeCount > 200 ? 30 : nodeCount > 50 ? 50 : 80;
    fg.d3Force('link')?.distance?.(linkDist);
    // 排斥力：節點數量多時降低排斥強度避免過度擴散
    const chargeStrength = nodeCount > 200 ? -30 : nodeCount > 50 ? -60 : -100;
    fg.d3Force('charge')?.strength?.(chargeStrength);
  }, [graphData]);

  // Zoom to Fit
  const handleZoomToFit = useCallback(() => {
    fgRef.current?.zoomToFit(400, 40);
  }, []);

  // 重新載入
  const handleRefresh = useCallback(() => {
    setSelectedNodeId(null);
    setSearchText('');
    setApiSearchMatchIds(null);
    setSidebarVisible(false);
    setError(null);

    // 外部資料模式：委託父層重新載入
    if (externalGraphData && onExternalRefresh) {
      onExternalRefresh();
      return;
    }

    setRawNodes([]);
    setRawEdges([]);
    setLoading(true);
    dataProvider.loadGraph({ document_ids: documentIds }).then((result) => {
      if (result) {
        setRawNodes(result.nodes);
        setRawEdges(result.edges);
      }
      setLoading(false);
      setTimeout(() => fgRef.current?.zoomToFit(400, 60), 500);
    }).catch((err) => {
      setError(err instanceof Error ? err.message : '重新載入失敗');
      setLoading(false);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentIds, externalGraphData, onExternalRefresh]);

  // 搜尋後聚焦（2D/3D）
  useEffect(() => {
    if (!searchMatchIds || searchMatchIds.size === 0) return;
    const firstId = Array.from(searchMatchIds)[0];
    const node = graphData.nodes.find((n) => n.id === firstId);
    if (!node || node.x == null || node.y == null) return;

    if (dimension === '3d' && fg3dRef.current) {
      const distance = 150;
      const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z ?? 0);
      fg3dRef.current.cameraPosition(
        { x: node.x * distRatio, y: node.y * distRatio, z: (node.z ?? 0) * distRatio },
        { x: node.x, y: node.y, z: node.z ?? 0 },
        800,
      );
    } else if (fgRef.current) {
      fgRef.current.centerAt(node.x, node.y, 300);
      fgRef.current.zoom(2, 300);
    }
  }, [searchMatchIds, graphData.nodes, dimension]);

  // Initial zoom
  useEffect(() => {
    if (!loading && rawNodes.length > 0) {
      setTimeout(() => fgRef.current?.zoomToFit(600, 60), 500);
    }
  }, [loading, rawNodes.length]);

  // 三位一體：監聽 Agent navigate 事件 → 圖譜 fly-to + 高亮
  useEffect(() => {
    if (!bridge) return;
    const unsub = bridge.bus.on<NavigateEvent>('navigate', (event) => {
      // 設定高亮 IDs
      const ids = new Set(event.highlightIds.map((id) => `entity_${id}`));
      setApiSearchMatchIds(ids);

      // fly-to 中心實體 (D3: 使用 nodeByLabel 索引)
      if (event.centerEntityName) {
        const targetNode = nodeByLabel.get(event.centerEntityName)
          ?? graphData.nodes.find((n) => ids.has(n.id));
        if (targetNode?.x != null && targetNode?.y != null) {
          if (dimension === '3d' && fg3dRef.current) {
            const d = 120;
            const r = 1 + d / Math.hypot(targetNode.x, targetNode.y, targetNode.z ?? 0);
            fg3dRef.current.cameraPosition(
              { x: targetNode.x * r, y: targetNode.y * r, z: (targetNode.z ?? 0) * r },
              { x: targetNode.x, y: targetNode.y, z: targetNode.z ?? 0 },
              1000,
            );
          } else if (fgRef.current) {
            fgRef.current.centerAt(targetNode.x, targetNode.y, 500);
            fgRef.current.zoom(2, 500);
          }
        }
      }
    });
    return unsub;
  }, [bridge, graphData.nodes, nodeByLabel, dimension, setApiSearchMatchIds]);

  // 三位一體：監聽 Agent summary_result 事件 → 高亮上下游 + fly-to
  useEffect(() => {
    if (!bridge) return;
    const unsub = bridge.bus.on<SummaryResultEvent>('summary_result', (event) => {
      // D3: 使用 nodeByLabel 索引
      const targetNode = nodeByLabel.get(event.entityName);

      // 收集高亮 IDs：主實體 + 上游 + 下游
      const highlightIds = new Set<string>();
      if (targetNode) {
        highlightIds.add(targetNode.id);
      }

      const upstreamNames = event.upstreamNames ?? [];
      const downstreamNames = event.downstreamNames ?? [];
      const relatedNames = [...upstreamNames, ...downstreamNames];

      for (const name of relatedNames) {
        const relNode = nodeByLabel.get(name);
        if (relNode) {
          highlightIds.add(relNode.id);
        }
      }

      // 設定高亮
      if (highlightIds.size > 0) {
        setApiSearchMatchIds(highlightIds);
      }

      // 選取主實體節點
      if (targetNode) {
        setSelectedNodeId(targetNode.id);

        // fly-to 主實體
        if (targetNode.x != null && targetNode.y != null) {
          if (dimension === '3d' && fg3dRef.current) {
            const d = 120;
            const r = 1 + d / Math.hypot(targetNode.x, targetNode.y, targetNode.z ?? 0);
            fg3dRef.current.cameraPosition(
              { x: targetNode.x * r, y: targetNode.y * r, z: (targetNode.z ?? 0) * r },
              { x: targetNode.x, y: targetNode.y, z: targetNode.z ?? 0 },
              1000,
            );
          } else if (fgRef.current) {
            fgRef.current.centerAt(targetNode.x, targetNode.y, 500);
            fgRef.current.zoom(2, 500);
          }
        }
      }
    });
    return unsub;
  }, [bridge, nodeByLabel, dimension, setApiSearchMatchIds]);

  // B8: 監聽 Agent draw_result 事件 → 高亮圖中涉及的實體
  useEffect(() => {
    if (!bridge) return;
    const unsub = bridge.bus.on<DrawResultEvent>('draw_result', (event) => {
      if (!event.relatedEntities?.length) return;
      const highlightIds = new Set<string>();
      for (const name of event.relatedEntities) {
        const node = nodeByLabel.get(name);
        if (node) highlightIds.add(node.id);
      }
      if (highlightIds.size > 0) {
        setApiSearchMatchIds(highlightIds);
      }
    });
    return unsub;
  }, [bridge, nodeByLabel, setApiSearchMatchIds]);

  // 類型過濾切換
  const handleTypeToggle = useCallback((type: string, checked: boolean) => {
    setVisibleTypes((prev) => {
      const next = new Set(prev);
      if (checked) next.add(type);
      else next.delete(type);
      return next;
    });
  }, []);

  // 搜尋 onChange handler（清除 API 結果以回到本地搜尋）
  const handleSearchChange = useCallback((value: string) => {
    setSearchText(value);
    setApiSearchMatchIds(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ============================================================================
  // Render
  // ============================================================================

  if (loading) {
    return (
      <div style={{ height, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
        <Spin size="large" />
        <div style={{ marginTop: 12, color: '#888' }}>載入關聯圖譜...</div>
      </div>
    );
  }

  if (error) {
    return <Empty description={`載入失敗：${error}`} style={{ padding: 20 }} />;
  }

  if (rawNodes.length === 0) {
    return <Empty description="無關聯資料" style={{ padding: 20 }} />;
  }

  // Selected node data for info card
  const selectedNode = selectedNodeId
    ? graphData.nodes.find((n) => n.id === selectedNodeId)
    : null;
  const selectedNodeConfig = selectedNode
    ? (mergedConfigs[selectedNode.type] ?? { ...effectiveGetNodeConfig(selectedNode.type), visible: true as const })
    : null;
  const selectedNeighborCount = selectedNodeId
    ? (neighborMap.get(selectedNodeId)?.size || 0)
    : 0;

  return (
    <div ref={containerRef} style={{ position: 'relative', overflow: 'hidden', width: '100%' }}>
      {/* 工具列 */}
      <GraphToolbar
        searchText={searchText}
        onSearchChange={handleSearchChange}
        onSearchSubmit={handleSearchSubmit}
        apiSearching={apiSearching}
        visibleTypes={visibleTypes}
        onTypeToggle={handleTypeToggle}
        onSettingsOpen={() => setSettingsOpen(true)}
        onZoomToFit={handleZoomToFit}
        onRefresh={handleRefresh}
        rawNodes={rawNodes}
        mergedConfigs={mergedConfigs}
      />

      {/* 別名命中提示 */}
      {aliasHint && (
        <div style={{ fontSize: 11, color: '#1890ff', marginBottom: 2 }}>
          {aliasHint}
        </div>
      )}

      {/* 統計資訊 */}
      <div style={{ fontSize: 11, color: '#999', marginBottom: 4 }}>
        {graphData.nodes.length} 個節點 · {graphData.links.length} 條關聯
        {selectedNodeId && (
          <span style={{ marginLeft: 8, color: '#1890ff' }}>
            已選取：{graphData.nodes.find((n) => n.id === selectedNodeId)?.label || selectedNodeId}
            （{neighborMap.get(selectedNodeId)?.size || 0} 個關聯節點）
          </span>
        )}
      </div>

      {/* 力導向圖 + 側邊欄 inline flex 佈局（避免 Drawer overlay 遮蔽） */}
      <div style={{ display: 'flex', gap: 0 }}>
        {/* 圖譜區域 */}
        <div style={{
          flex: 1, minWidth: 0, position: 'relative',
          border: '1px solid #f0f0f0', borderRadius: sidebarVisible ? '8px 0 0 8px' : 8,
          overflow: 'hidden', background: dimension === '3d' ? '#1a1a2e' : '#fafafa',
        }}>
          {dimension === '2d' ? (
            <ForceGraph2D
              ref={fgRef}
              graphData={graphData}
              width={effectiveWidth}
              height={height}
              d3AlphaDecay={0.04}
              d3VelocityDecay={0.3}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              nodeCanvasObject={paintNode as any}
              nodePointerAreaPaint={nodePointerAreaPaint}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              onNodeClick={handleNodeClick as any}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              onNodeHover={handleNodeHover as any}
              linkColor={linkColor}
              linkWidth={linkWidth}
              linkDirectionalArrowLength={4}
              linkDirectionalArrowRelPos={0.85}
              linkDirectionalArrowColor={linkDirectionalArrowColor}
              linkCanvasObjectMode={() => 'after'}
              linkCanvasObject={linkCanvasObject}
              onBackgroundClick={() => {
                setSelectedNodeId(null);
                setSidebarVisible(false);
              }}
              onEngineStop={() => {
                fgRef.current?.zoomToFit(400, 60);
              }}
              warmupTicks={30}
              cooldownTicks={200}
            />
          ) : (
            <Suspense fallback={<div style={{ height, display: 'flex', justifyContent: 'center', alignItems: 'center' }}><Spin tip="載入 3D 引擎..."><div /></Spin></div>}>
              <ForceGraph3D
                ref={fg3dRef}
                graphData={graphData}
                width={effectiveWidth}
                height={height}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                nodeThreeObject={graph3dCallbacks.nodeThreeObject as any}
                nodeThreeObjectExtend={false}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                onNodeClick={handleNodeClick as any}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                onNodeHover={handleNodeHover as any}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                linkColor={graph3dCallbacks.linkColor as any}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                linkWidth={graph3dCallbacks.linkWidth as any}
                linkDirectionalArrowLength={4}
                linkDirectionalArrowRelPos={0.85}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                linkDirectionalArrowColor={graph3dCallbacks.linkDirectionalArrowColor as any}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                linkThreeObject={graph3dCallbacks.linkThreeObject as any}
                linkThreeObjectExtend={false}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                linkPositionUpdate={graph3dCallbacks.linkPositionUpdate as any}
                onBackgroundClick={() => {
                  setSelectedNodeId(null);
                  setSidebarVisible(false);
                }}
                onEngineStop={() => {
                  fg3dRef.current?.zoomToFit(400, 60);
                }}
                warmupTicks={30}
                cooldownTicks={200}
                backgroundColor="#1a1a2e"
              />
            </Suspense>
          )}

          {/* 2D/3D 切換按鈕 — 浮動右下角 */}
          <div style={{
            position: 'absolute', right: 12, bottom: 12, zIndex: 20,
            display: 'inline-flex', borderRadius: 6, overflow: 'hidden',
            border: '1px solid rgba(0,0,0,0.15)', fontSize: 12,
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          }}>
            <button
              onClick={() => setDimension('2d')}
              style={{
                padding: '6px 14px', border: 'none', cursor: 'pointer',
                background: dimension === '2d' ? '#1890ff' : '#fff',
                color: dimension === '2d' ? '#fff' : '#333',
                fontWeight: dimension === '2d' ? 600 : 400,
              }}
            >
              2D
            </button>
            <button
              onClick={() => setDimension('3d')}
              style={{
                padding: '6px 14px', border: 'none', cursor: 'pointer',
                borderLeft: '1px solid #d9d9d9',
                background: dimension === '3d' ? '#1890ff' : '#fff',
                color: dimension === '3d' ? '#fff' : '#333',
                fontWeight: dimension === '3d' ? 600 : 400,
              }}
            >
              3D
            </button>
          </div>

          {/* 選取節點資訊面板（浮動在圖譜內） */}
          {selectedNode && selectedNodeConfig && !sidebarVisible && (
            <SelectedNodeInfoCard
              node={selectedNode}
              nodeConfig={selectedNodeConfig}
              neighborCount={selectedNeighborCount}
              onClose={() => setSelectedNodeId(null)}
              onViewDetail={(label, type) => {
                setSidebarEntityName(label);
                setSidebarEntityType(type);
                setSidebarVisible(true);
              }}
            />
          )}
        </div>

        {/* Entity Detail Sidebar — inline 面板，非 Drawer overlay */}
        {sidebarVisible && (
          <div style={{
            width: SIDEBAR_WIDTH,
            minWidth: SIDEBAR_WIDTH,
            height: height + 2,
            borderTop: '1px solid #f0f0f0',
            borderRight: '1px solid #f0f0f0',
            borderBottom: '1px solid #f0f0f0',
            borderRadius: '0 8px 8px 0',
            overflow: 'hidden',
          }}>
            <EntityDetailSidebar
              visible={sidebarVisible}
              entityName={sidebarEntityName}
              entityType={sidebarEntityType}
              onClose={() => setSidebarVisible(false)}
              inline
            />
          </div>
        )}
      </div>

      {/* 節點設定面板 — 僅顯示當前圖譜中實際出現的節點類型 */}
      <GraphNodeSettings
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={() => setConfigVersion((v) => v + 1)}
        activeTypes={activeNodeTypes}
      />
    </div>
  );
};

export default KnowledgeGraph;

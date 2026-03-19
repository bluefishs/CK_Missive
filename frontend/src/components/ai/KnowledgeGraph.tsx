/**
 * KnowledgeGraph - 公文關聯網絡互動式視覺化元件 v3.4
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
 * v3.4: Extracted useGraphDataLoader, useGraphTransform, useContainerWidth
 *
 * @version 3.4.0
 * @created 2026-02-24
 * @updated 2026-03-18 — 拆分 data loader / transform / container width
 */

import React, { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { Spin, Empty } from 'antd';
import type { ForceGraphMethods } from 'react-force-graph-2d';
import { aiApi } from '../../api/aiApi';
import type { GraphNode, GraphEdge } from '../../types/ai';
import {
  CANONICAL_ENTITY_TYPES,
  GRAPH_NODE_CONFIG,
  getNodeConfig,
  getAllMergedConfigs,
} from '../../config/graphNodeConfig';
import type { GraphNodeTypeConfig } from '../../config/graphNodeConfig';
import { GraphNodeSettings } from './GraphNodeSettings';
import { GraphToolbar } from './knowledgeGraph/GraphToolbar';
import type { GraphViewMode } from './knowledgeGraph/GraphToolbar';
import { useGraphSearch } from './knowledgeGraph/useGraphSearch';
import { useForceGraphCallbacks } from './knowledgeGraph/useForceGraphCallbacks';
import { useForceGraph3DCallbacks } from './knowledgeGraph/useForceGraph3DCallbacks';
import { useGraphAgentEvents } from './knowledgeGraph/useGraphAgentEvents';
import { useGraphForceConfig } from './knowledgeGraph/useGraphForceConfig';
import { useGraphDataLoader } from './knowledgeGraph/useGraphDataLoader';
import { useGraphTransform } from './knowledgeGraph/useGraphTransform';
import { useContainerWidth } from './knowledgeGraph/useContainerWidth';
import { GraphCanvas } from './knowledgeGraph/GraphCanvas';
import { GraphStatsBar } from './knowledgeGraph/GraphStatsBar';
import type { ForceNode } from './knowledgeGraph/types';

// ============================================================================
// Props
// ============================================================================

export interface ExternalGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphDataProvider {
  loadGraph: (params: { document_ids: number[] }) => Promise<ExternalGraphData | null>;
}

export interface KnowledgeGraphProps {
  documentIds: number[];
  height?: number;
  width?: number;
  externalGraphData?: ExternalGraphData | null;
  onExternalRefresh?: () => void;
  defaultDimension?: '2d' | '3d';
  onNodeClickExternal?: (node: { id: string; label: string; type: string }) => void;
  dataProvider?: GraphDataProvider;
  nodeConfig?: Record<string, GraphNodeTypeConfig>;
}

// ============================================================================
// 主元件
// ============================================================================

const defaultProvider: GraphDataProvider = {
  loadGraph: async (params) => {
    const result = await aiApi.getRelationGraph({ document_ids: params.document_ids });
    return result ? { nodes: result.nodes, edges: result.edges } : null;
  },
};

export const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({
  documentIds,
  height = 700,
  width: externalWidth,
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
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [dimension, setDimension] = useState<'2d' | '3d'>(defaultDimension);

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

  const [viewMode, setViewMode] = useState<GraphViewMode>('entity');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [configVersion, setConfigVersion] = useState(0);

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

  // Data loading
  const {
    rawNodes, rawEdges, loading, error,
    setError, reload,
  } = useGraphDataLoader({
    documentIds,
    externalGraphData,
    onExternalRefresh,
    dataProvider,
  });

  const activeNodeTypes = useMemo(() => new Set(rawNodes.map((n) => n.type)), [rawNodes]);

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

  // Container width management
  const { containerRef, effectiveWidth } = useContainerWidth({
    externalWidth,
    sidebarVisible,
    fgRef,
    fg3dRef,
    dimension,
    rawNodesLength: rawNodes.length,
  });

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const mergedConfigs = useMemo(() => getAllMergedConfigs(effectiveConfig), [configVersion, effectiveConfig]);

  // Data transformation
  const { graphData, neighborMap, nodeByLabel } = useGraphTransform({
    rawNodes,
    rawEdges,
    visibleTypes,
    mergedConfigs,
    viewMode,
    effectiveGetNodeConfig,
  });

  // Force-graph 渲染回調 (2D)
  const callbacks2d = useForceGraphCallbacks({
    mergedConfigs,
    selectedNodeId,
    hoveredNodeId,
    searchMatchIds,
    neighborMap,
    entityMode: viewMode === 'entity',
  });

  // Force-graph 渲染回調 (3D)
  const graph3dCallbacks = useForceGraph3DCallbacks({
    mergedConfigs,
    selectedNodeId,
    hoveredNodeId,
    searchMatchIds,
    neighborMap,
    enabled: dimension === '3d',
  });

  // D3 force configuration
  useGraphForceConfig({ fgRef, graphData, viewMode, mergedConfigs });

  // Agent bridge events
  const bridge = useGraphAgentEvents({
    graphNodes: graphData.nodes,
    nodeByLabel,
    dimension,
    setApiSearchMatchIds,
    setSelectedNodeId,
    fgRef,
    fg3dRef,
  });

  // 點擊節點
  const handleNodeClick = useCallback((node: ForceNode) => {
    const newSelected = selectedNodeId === node.id ? null : node.id;
    setSelectedNodeId(newSelected);

    const isDetailable = effectiveDetailable.has(node.type) || node.id.startsWith('ce_');
    if (newSelected && isDetailable) {
      setSidebarEntityName(node.label);
      setSidebarEntityType(node.type);
      setSidebarVisible(true);

      const entityIdNum = parseInt(node.id.replace(/^entity_/, ''), 10);
      if (bridge && !isNaN(entityIdNum)) {
        bridge.requestSummary(entityIdNum, node.label, node.type);
      }
    } else {
      setSidebarVisible(false);
    }

    if (newSelected && onNodeClickExternal) {
      onNodeClickExternal({ id: node.id, label: node.label, type: node.type });
    }

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
  }, [containerRef]);

  const handleZoomToFit = useCallback(() => {
    fgRef.current?.zoomToFit(400, 40);
  }, []);

  const handleRefresh = useCallback(() => {
    setSelectedNodeId(null);
    setSearchText('');
    setApiSearchMatchIds(null);
    setSidebarVisible(false);
    setError(null);
    reload();
    setTimeout(() => fgRef.current?.zoomToFit(400, 60), 500);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reload]);

  // 搜尋後聚焦
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

  const handleTypeToggle = useCallback((type: string, checked: boolean) => {
    setVisibleTypes((prev) => {
      const next = new Set(prev);
      if (checked) next.add(type);
      else next.delete(type);
      return next;
    });
  }, []);

  const handleSearchChange = useCallback((value: string) => {
    setSearchText(value);
    setApiSearchMatchIds(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleBackgroundClick = useCallback(() => {
    setSelectedNodeId(null);
    setSidebarVisible(false);
  }, []);

  // ============================================================================
  // Render
  // ============================================================================

  if (loading) {
    return (
      <div style={{ height: '100%', minHeight: 200, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
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

  const selectedNode = selectedNodeId
    ? graphData.nodes.find((n) => n.id === selectedNodeId)
    : null;
  const selectedNodeConfig = selectedNode
    ? (mergedConfigs[selectedNode.type] ?? { ...effectiveGetNodeConfig(selectedNode.type), visible: true })
    : null;
  const selectedNeighborCount = selectedNodeId
    ? (neighborMap.get(selectedNodeId)?.size || 0)
    : 0;

  return (
    <div ref={containerRef} style={{ position: 'relative', overflow: 'hidden', width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
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
        rawEdges={rawEdges}
        mergedConfigs={mergedConfigs}
        dimension={dimension}
        onDimensionChange={setDimension}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />

      {aliasHint && (
        <div style={{ fontSize: 11, color: '#1890ff', marginBottom: 2 }}>
          {aliasHint}
        </div>
      )}

      <GraphStatsBar
        graphData={graphData}
        selectedNodeId={selectedNodeId}
        neighborMap={neighborMap}
        mergedConfigs={mergedConfigs}
        effectiveGetNodeConfig={effectiveGetNodeConfig}
      />

      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
      <GraphCanvas
        dimension={dimension}
        graphData={graphData}
        effectiveWidth={effectiveWidth}
        height={height}
        fgRef={fgRef}
        fg3dRef={fg3dRef}
        paintNode={callbacks2d.paintNode}
        nodePointerAreaPaint={callbacks2d.nodePointerAreaPaint}
        linkColor={callbacks2d.linkColor}
        linkWidth={callbacks2d.linkWidth}
        linkDirectionalArrowColor={callbacks2d.linkDirectionalArrowColor}
        linkCanvasObject={callbacks2d.linkCanvasObject}
        graph3dCallbacks={graph3dCallbacks}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        onBackgroundClick={handleBackgroundClick}
        selectedNode={selectedNode ?? null}
        selectedNodeConfig={selectedNodeConfig}
        selectedNeighborCount={selectedNeighborCount}
        onSelectedNodeClose={() => setSelectedNodeId(null)}
        onViewDetail={(label, type) => {
          setSidebarEntityName(label);
          setSidebarEntityType(type);
          setSidebarVisible(true);
        }}
        sidebarVisible={sidebarVisible}
        sidebarEntityName={sidebarEntityName}
        sidebarEntityType={sidebarEntityType}
        onSidebarClose={() => setSidebarVisible(false)}
      />
      </div>

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

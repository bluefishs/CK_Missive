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

import React, { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { Spin, Empty } from 'antd';
import ForceGraph2D, { type ForceGraphMethods } from 'react-force-graph-2d';
import { aiApi } from '../../api/aiApi';
import type { GraphNode, GraphEdge } from '../../types/ai';
import {
  CANONICAL_ENTITY_TYPES,
  getNodeConfig,
  getAllMergedConfigs,
} from '../../config/graphNodeConfig';
import { EntityDetailSidebar } from './EntityDetailSidebar';
import { GraphNodeSettings } from './GraphNodeSettings';
import { GraphToolbar } from './knowledgeGraph/GraphToolbar';
import { SelectedNodeInfoCard } from './knowledgeGraph/SelectedNodeInfoCard';
import { useGraphSearch } from './knowledgeGraph/useGraphSearch';
import { useForceGraphCallbacks } from './knowledgeGraph/useForceGraphCallbacks';
import type { ForceNode, GraphData } from './knowledgeGraph/types';

// ============================================================================
// Props
// ============================================================================

export interface KnowledgeGraphProps {
  documentIds: number[];
  height?: number;
}

// ============================================================================
// 主元件
// ============================================================================

export const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({
  documentIds,
  height = 700,
}) => {
  const fgRef = useRef<ForceGraphMethods | undefined>();
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(800);
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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

  // 載入圖譜資料
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setSelectedNodeId(null);

    aiApi.getRelationGraph({ document_ids: documentIds }).then((result) => {
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
  }, [documentIds]);

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
  const mergedConfigs = useMemo(() => getAllMergedConfigs(), [configVersion]);

  // 轉換為 force-graph 格式
  const graphData = useMemo((): GraphData => {
    const filteredNodes = rawNodes.filter((n) => {
      if (!visibleTypes.has(n.type)) return false;
      const cfg = mergedConfigs[n.type];
      if (cfg && !cfg.visible) return false;
      return true;
    });
    const nodeIdSet = new Set(filteredNodes.map((n) => n.id));

    const nodes: ForceNode[] = filteredNodes.map((n) => ({
      id: n.id,
      label: n.label,
      type: n.type,
      color: mergedConfigs[n.type]?.color ?? getNodeConfig(n.type).color,
      category: n.category,
      doc_number: n.doc_number,
      status: n.status,
      mention_count: n.mention_count ?? undefined,
    }));

    const links = rawEdges
      .filter((e) => nodeIdSet.has(e.source) && nodeIdSet.has(e.target))
      .map((e) => ({
        source: e.source,
        target: e.target,
        label: e.label,
        type: e.type,
        weight: e.weight ?? undefined,
      }));

    return { nodes, links };
  }, [rawNodes, rawEdges, visibleTypes, mergedConfigs]);

  // Force-graph 渲染回調
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

  // 點擊節點
  const handleNodeClick = useCallback((node: ForceNode) => {
    const newSelected = selectedNodeId === node.id ? null : node.id;
    setSelectedNodeId(newSelected);

    if (newSelected && CANONICAL_ENTITY_TYPES.has(node.type)) {
      setSidebarEntityName(node.label);
      setSidebarEntityType(node.type);
      setSidebarVisible(true);
    } else {
      setSidebarVisible(false);
    }
  }, [selectedNodeId]);

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
    setRawNodes([]);
    setRawEdges([]);
    setLoading(true);
    let cancelled = false;
    aiApi.getRelationGraph({ document_ids: documentIds }).then((result) => {
      if (cancelled) return;
      if (result) {
        setRawNodes(result.nodes);
        setRawEdges(result.edges);
      }
      setLoading(false);
      setTimeout(() => fgRef.current?.zoomToFit(400, 60), 500);
    }).catch((err) => {
      if (cancelled) return;
      setError(err instanceof Error ? err.message : '重新載入失敗');
      setLoading(false);
    });
  }, [documentIds, setSearchText, setApiSearchMatchIds]);

  // 搜尋後聚焦
  useEffect(() => {
    if (searchMatchIds && searchMatchIds.size > 0 && fgRef.current) {
      const firstId = Array.from(searchMatchIds)[0];
      const node = graphData.nodes.find((n) => n.id === firstId);
      if (node?.x != null && node?.y != null) {
        fgRef.current.centerAt(node.x, node.y, 300);
        fgRef.current.zoom(2, 300);
      }
    }
  }, [searchMatchIds, graphData.nodes]);

  // Initial zoom
  useEffect(() => {
    if (!loading && rawNodes.length > 0) {
      setTimeout(() => fgRef.current?.zoomToFit(600, 60), 500);
    }
  }, [loading, rawNodes.length]);

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
  }, [setSearchText, setApiSearchMatchIds]);

  // ============================================================================
  // Render
  // ============================================================================

  if (loading) {
    return (
      <Spin tip="載入關聯圖譜...">
        <div style={{ height, display: 'flex', justifyContent: 'center', alignItems: 'center' }} />
      </Spin>
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
    ? (mergedConfigs[selectedNode.type] ?? { ...getNodeConfig(selectedNode.type), visible: true as const })
    : null;
  const selectedNeighborCount = selectedNodeId
    ? (neighborMap.get(selectedNodeId)?.size || 0)
    : 0;

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
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

      {/* 力導向圖 */}
      <div style={{
        border: '1px solid #f0f0f0', borderRadius: 8,
        overflow: 'hidden', background: '#fafafa',
      }}>
        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          width={containerWidth}
          height={height}
          d3AlphaDecay={0.05}
          d3VelocityDecay={0.4}
          nodeCanvasObject={paintNode as any}
          nodePointerAreaPaint={nodePointerAreaPaint}
          onNodeClick={handleNodeClick as any}
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
      </div>

      {/* 選取節點資訊面板 */}
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

      {/* Entity Detail Sidebar */}
      <EntityDetailSidebar
        visible={sidebarVisible}
        entityName={sidebarEntityName}
        entityType={sidebarEntityType}
        onClose={() => setSidebarVisible(false)}
      />

      {/* 節點設定面板 */}
      <GraphNodeSettings
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={() => setConfigVersion((v) => v + 1)}
      />
    </div>
  );
};

export default KnowledgeGraph;

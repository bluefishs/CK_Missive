/**
 * KnowledgeGraph - 公文關聯網絡互動式視覺化元件 v3.0
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
 * @version 3.0.0
 * @created 2026-02-24
 * @updated 2026-02-24 — 新增 EntityDetailSidebar + 正規化實體查詢
 */

import React, { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import {
  Spin, Empty, Input, Checkbox, Button, Space,
  Tooltip as AntTooltip, Typography, App,
} from 'antd';
import {
  AimOutlined,
  ReloadOutlined,
  SearchOutlined,
  SettingOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import ForceGraph2D, { type ForceGraphMethods } from 'react-force-graph-2d';
import { aiApi } from '../../api/aiApi';
import type { GraphNode, GraphEdge } from '../../types/ai';
import {
  GRAPH_NODE_CONFIG,
  CANONICAL_ENTITY_TYPES,
  getNodeConfig,
  getAllMergedConfigs,
} from '../../config/graphNodeConfig';
import { EntityDetailSidebar } from './EntityDetailSidebar';
import { GraphNodeSettings } from './GraphNodeSettings';

const { Text } = Typography;

// ============================================================================
// 內部型別
// ============================================================================

interface ForceNode {
  id: string;
  label: string;
  type: string;
  color: string;
  category?: string | null;
  doc_number?: string | null;
  status?: string | null;
  mention_count?: number;
  x?: number;
  y?: number;
}

interface ForceLink {
  source: string | ForceNode;
  target: string | ForceNode;
  label: string;
  type: string;
  weight?: number;
}

interface GraphData {
  nodes: ForceNode[];
  links: ForceLink[];
}

// ============================================================================
// Props
// ============================================================================

export interface KnowledgeGraphProps {
  documentIds: number[];
  height?: number;
}

// ============================================================================
// 工具函數
// ============================================================================

function truncate(str: string, max: number): string {
  return str.length > max ? str.slice(0, max) + '...' : str;
}

function getNodeId(node: string | ForceNode): string {
  return typeof node === 'string' ? node : node.id;
}

// ============================================================================
// 主元件
// ============================================================================

export const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({
  documentIds,
  height = 700,
}) => {
  const { message } = App.useApp();
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
  const [searchText, setSearchText] = useState('');
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

  // 本地搜尋匹配（打字即時回應）
  const localSearchMatchIds = useMemo(() => {
    if (!searchText.trim()) return null;
    const lower = searchText.toLowerCase();
    const ids = new Set<string>();
    for (const node of rawNodes) {
      if (
        node.label.toLowerCase().includes(lower) ||
        (node.doc_number && node.doc_number.toLowerCase().includes(lower))
      ) {
        ids.add(node.id);
      }
    }
    return ids;
  }, [searchText, rawNodes]);

  // API 搜尋結果（Enter 觸發，含同義詞擴展）
  const [apiSearchMatchIds, setApiSearchMatchIds] = useState<Set<string> | null>(null);
  const [apiSearching, setApiSearching] = useState(false);

  const handleSearchSubmit = useCallback(async () => {
    const q = searchText.trim();
    if (!q) {
      setApiSearchMatchIds(null);
      return;
    }
    setApiSearching(true);
    try {
      const result = await aiApi.searchGraphEntities({ query: q, limit: 30 });
      if (result?.results?.length > 0) {
        // 將 API 搜尋到的實體名稱映射到圖譜中已有的節點
        const matchedNames = new Set(result.results.map((r: { canonical_name: string }) => r.canonical_name.toLowerCase()));
        const ids = new Set<string>();
        for (const node of rawNodes) {
          if (matchedNames.has(node.label.toLowerCase())) {
            ids.add(node.id);
          }
        }
        setApiSearchMatchIds(ids.size > 0 ? ids : null);
        if (ids.size === 0) {
          message.info(`找到 ${result.results.length} 個正規化實體，但不在目前圖譜中`);
        }
      } else {
        setApiSearchMatchIds(null);
        message.info('未找到匹配的正規化實體');
      }
    } catch {
      // API 搜尋失敗時靜默降級到本地搜尋
      setApiSearchMatchIds(null);
    } finally {
      setApiSearching(false);
    }
  }, [searchText, rawNodes]);

  // 合併搜尋結果：API 結果優先，無 API 結果時用本地
  const searchMatchIds = apiSearchMatchIds ?? localSearchMatchIds;

  // 使用者合併配置快取（隨 configVersion 更新）
  const mergedConfigs = useMemo(() => getAllMergedConfigs(), [configVersion]);

  // 轉換為 force-graph 格式
  const graphData = useMemo((): GraphData => {
    const filteredNodes = rawNodes.filter((n) => {
      // 同時考慮使用者手動的 visibleTypes 和設定面板的 visible
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

    const links: ForceLink[] = rawEdges
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

  // 高亮判斷
  const isHighlighted = useCallback((nodeId: string): boolean => {
    if (searchMatchIds) return searchMatchIds.has(nodeId);
    if (selectedNodeId) {
      return nodeId === selectedNodeId || (neighborMap.get(selectedNodeId)?.has(nodeId) ?? false);
    }
    if (hoveredNodeId) {
      return nodeId === hoveredNodeId || (neighborMap.get(hoveredNodeId)?.has(nodeId) ?? false);
    }
    return true;
  }, [searchMatchIds, selectedNodeId, hoveredNodeId, neighborMap]);

  const isLinkHighlighted = useCallback((link: ForceLink): boolean => {
    const srcId = getNodeId(link.source);
    const tgtId = getNodeId(link.target);
    if (searchMatchIds) return searchMatchIds.has(srcId) || searchMatchIds.has(tgtId);
    if (selectedNodeId) return srcId === selectedNodeId || tgtId === selectedNodeId;
    if (hoveredNodeId) return srcId === hoveredNodeId || tgtId === hoveredNodeId;
    return true;
  }, [searchMatchIds, selectedNodeId, hoveredNodeId]);

  // Canvas 繪製節點
  const paintNode = useCallback((node: ForceNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const x = node.x ?? 0;
    const y = node.y ?? 0;
    const cfg = mergedConfigs[node.type] ?? getNodeConfig(node.type);
    const baseR = cfg.radius;
    // 實體節點大小可隨 mention_count 調整
    const mentionBonus = node.mention_count ? Math.min(Math.log2(node.mention_count + 1) * 1.5, 6) : 0;
    const r = baseR + mentionBonus;
    const highlighted = isHighlighted(node.id);
    const isSelected = selectedNodeId === node.id;
    const isSearchMatch = searchMatchIds?.has(node.id);

    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.fillStyle = highlighted ? node.color : 'rgba(200,200,200,0.3)';
    ctx.fill();

    if (isSelected) {
      ctx.strokeStyle = '#333';
      ctx.lineWidth = 2.5 / globalScale;
    } else if (isSearchMatch) {
      ctx.strokeStyle = '#ff4d4f';
      ctx.lineWidth = 2 / globalScale;
    } else {
      ctx.strokeStyle = highlighted ? 'rgba(255,255,255,0.9)' : 'rgba(200,200,200,0.2)';
      ctx.lineWidth = 1 / globalScale;
    }
    ctx.stroke();

    // 標籤
    if (globalScale > 1.0 || isSelected || isSearchMatch) {
      const fontSize = Math.max(10 / globalScale, 2);
      ctx.font = `${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = highlighted ? '#333' : 'rgba(180,180,180,0.5)';
      ctx.fillText(truncate(node.label, 14), x, y + r + 2 / globalScale);
    }
  }, [isHighlighted, selectedNodeId, searchMatchIds, mergedConfigs]);

  // 點擊節點
  const handleNodeClick = useCallback((node: ForceNode) => {
    const newSelected = selectedNodeId === node.id ? null : node.id;
    setSelectedNodeId(newSelected);

    // 如果是 canonical entity 類型，打開詳情側邊欄
    if (newSelected && CANONICAL_ENTITY_TYPES.has(node.type)) {
      setSidebarEntityName(node.label);
      setSidebarEntityType(node.type);
      setSidebarVisible(true);
    } else {
      setSidebarVisible(false);
    }
  }, [selectedNodeId]);

  // Hover 節點（僅用於高亮 + 游標樣式，不顯示互動面板）
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
  }, [documentIds]);

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

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      {/* 工具列 */}
      <div style={{
        display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8,
        marginBottom: 8, padding: '6px 0',
      }}>
        <Input
          prefix={<SearchOutlined />}
          suffix={apiSearching ? <Spin size="small" /> : undefined}
          placeholder="搜尋節點（Enter 擴展搜尋）"
          value={searchText}
          onChange={(e) => { setSearchText(e.target.value); setApiSearchMatchIds(null); }}
          onPressEnter={handleSearchSubmit}
          allowClear
          size="small"
          style={{ width: 220 }}
        />

        <Space size={4}>
          {Object.entries(GRAPH_NODE_CONFIG)
            .filter(([type]) => rawNodes.some((n) => n.type === type))
            .map(([type]) => {
              const merged = mergedConfigs[type] ?? getNodeConfig(type);
              return (
                <AntTooltip key={type} title={merged.description} mouseEnterDelay={0.4}>
                  <Checkbox
                    checked={visibleTypes.has(type)}
                    onChange={(e) => handleTypeToggle(type, e.target.checked)}
                    style={{ fontSize: 12 }}
                  >
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                      <span style={{
                        width: 8, height: 8, borderRadius: '50%',
                        background: merged.color, display: 'inline-block',
                      }} />
                      {merged.label}
                    </span>
                  </Checkbox>
                </AntTooltip>
              );
            })}
        </Space>

        <Space size={4} style={{ marginLeft: 'auto' }}>
          <AntTooltip title="節點設定">
            <Button size="small" icon={<SettingOutlined />} onClick={() => setSettingsOpen(true)} />
          </AntTooltip>
          <AntTooltip title="自動適配畫面">
            <Button size="small" icon={<AimOutlined />} onClick={handleZoomToFit} />
          </AntTooltip>
          <AntTooltip title="重新載入">
            <Button size="small" icon={<ReloadOutlined />} onClick={handleRefresh} />
          </AntTooltip>
        </Space>
      </div>

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
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
          nodeCanvasObject={paintNode as any}
          nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
            const baseR = mergedConfigs[node.type]?.radius ?? getNodeConfig(node.type).radius;
            // 確保點擊區域至少 12px，方便滑鼠操作
            const r = Math.max(baseR + 4, 12);
            ctx.beginPath();
            ctx.arc(node.x ?? 0, node.y ?? 0, r, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          }}
          onNodeClick={handleNodeClick as any}
          onNodeHover={handleNodeHover as any}
          linkColor={(link: any) => isLinkHighlighted(link) ? 'rgba(150,150,150,0.6)' : 'rgba(220,220,220,0.2)'}
          linkWidth={(link: any) => {
            const base = isLinkHighlighted(link) ? 1.5 : 0.5;
            const w = link.weight ?? 1;
            return base * Math.min(w, 5);
          }}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={0.85}
          linkDirectionalArrowColor={(link: any) => isLinkHighlighted(link) ? 'rgba(120,120,120,0.5)' : 'rgba(220,220,220,0.2)'}
          linkCanvasObjectMode={() => 'after'}
          linkCanvasObject={(link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
            if (globalScale < 1.5 || !isLinkHighlighted(link)) return;
            const src = link.source;
            const tgt = link.target;
            if (!src?.x || !tgt?.x) return;
            const midX = (src.x + tgt.x) / 2;
            const midY = (src.y + tgt.y) / 2;
            const fontSize = Math.max(8 / globalScale, 1.5);
            ctx.font = `${fontSize}px sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = 'rgba(100,100,100,0.7)';
            ctx.fillText(link.label || '', midX, midY - 3 / globalScale);
          }}
          onBackgroundClick={() => {
            setSelectedNodeId(null);
            setSidebarVisible(false);
          }}
          onEngineStop={() => {
            // 力模擬結束後自動適配，確保所有節點在可視範圍內
            fgRef.current?.zoomToFit(400, 60);
          }}
          warmupTicks={50}
          cooldownTicks={100}
        />
      </div>

      {/* 選取節點資訊面板（點擊節點後顯示，不會消失） */}
      {selectedNodeId && !sidebarVisible && (() => {
        const node = graphData.nodes.find((n) => n.id === selectedNodeId);
        if (!node) return null;
        const nodeCfg = mergedConfigs[node.type] ?? getNodeConfig(node.type);
        const neighborCount = neighborMap.get(selectedNodeId)?.size || 0;
        return (
          <div
            style={{
              position: 'absolute', top: 45, right: 8,
              background: 'white', border: '1px solid #d9d9d9', borderRadius: 6,
              padding: '10px 14px', fontSize: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
              minWidth: 200, maxWidth: 280, zIndex: 10,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <div style={{ fontWeight: 'bold', color: node.color, fontSize: 13 }}>
                <span style={{
                  width: 10, height: 10, borderRadius: '50%',
                  background: node.color, display: 'inline-block', marginRight: 6,
                }} />
                {nodeCfg.label}
              </div>
              <span
                style={{ color: '#999', cursor: 'pointer', fontSize: 14 }}
                onClick={() => { setSelectedNodeId(null); }}
              >
                ✕
              </span>
            </div>
            <div style={{ fontWeight: 500, marginBottom: 4 }}>{node.label}</div>
            {nodeCfg.description && (
              <div style={{ color: '#999', fontSize: 11, marginBottom: 4 }}>{nodeCfg.description}</div>
            )}
            {node.doc_number && <div style={{ color: '#666' }}>文號：{node.doc_number}</div>}
            {node.category && <div style={{ color: '#666' }}>分類：{node.category}</div>}
            {node.status && <div style={{ color: '#666' }}>狀態：{node.status}</div>}
            <div style={{ color: '#666', marginTop: 2 }}>關聯節點：{neighborCount} 個</div>
            {nodeCfg.detailable && (
              <div
                style={{
                  color: '#1890ff', marginTop: 8, fontSize: 12, cursor: 'pointer',
                  padding: '4px 8px', background: '#f0f5ff', borderRadius: 4,
                  textAlign: 'center', border: '1px solid #d6e4ff',
                }}
                onClick={() => {
                  setSidebarEntityName(node.label);
                  setSidebarEntityType(node.type);
                  setSidebarVisible(true);
                }}
              >
                <LinkOutlined /> 檢視正規化實體詳情
              </div>
            )}
          </div>
        );
      })()}

      {/* Entity Detail Sidebar (Phase 2) */}
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

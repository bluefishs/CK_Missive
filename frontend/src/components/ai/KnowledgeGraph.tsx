/**
 * KnowledgeGraph - 公文關聯網絡互動式視覺化元件
 *
 * 使用 react-force-graph-2d 實現力導向佈局：
 * - 物理模擬自動排列節點
 * - 縮放/平移/拖曳節點
 * - 點擊節點高亮鄰居
 * - 搜尋過濾、類型過濾
 * - 方向箭頭 + 邊標籤
 *
 * 節點按類型分色：公文=藍, 專案=綠, 機關=橙, 派工=紫
 *
 * @version 2.0.0
 * @created 2026-02-24
 * @updated 2026-02-24 — 從靜態 SVG 遷移至 react-force-graph-2d
 */

import React, { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { Spin, Empty, Input, Checkbox, Button, Space, Tooltip as AntTooltip } from 'antd';
import {
  AimOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import ForceGraph2D, { type ForceGraphMethods } from 'react-force-graph-2d';
import { aiApi, type GraphNode, type GraphEdge } from '../../api/aiApi';

// ============================================================================
// 常數
// ============================================================================

const NODE_COLORS: Record<string, string> = {
  document: '#1890ff',
  project: '#52c41a',
  agency: '#fa8c16',
  dispatch: '#722ed1',
  // NER 提取實體類型
  org: '#fa8c16',      // 與 agency 同色系（機關/組織）
  person: '#f5222d',   // 紅
  location: '#faad14', // 黃
  date: '#13c2c2',     // 青
  topic: '#eb2f96',    // 粉紅
};

const NODE_RADIUS: Record<string, number> = {
  document: 6,
  project: 9,
  agency: 5,
  dispatch: 7,
  org: 5,
  person: 5,
  location: 4,
  date: 4,
  topic: 5,
};

const TYPE_LABELS: Record<string, string> = {
  document: '公文',
  project: '專案',
  agency: '機關',
  dispatch: '派工',
  org: '組織',
  person: '人物',
  location: '地點',
  date: '日期',
  topic: '主題',
};

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
  x?: number;
  y?: number;
}

interface ForceLink {
  source: string | ForceNode;
  target: string | ForceNode;
  label: string;
  type: string;
}

interface GraphData {
  nodes: ForceNode[];
  links: ForceLink[];
}

// ============================================================================
// Props
// ============================================================================

export interface KnowledgeGraphProps {
  /** 要顯示關聯的公文 ID 列表（空=自動載入最近公文） */
  documentIds: number[];
  /** 容器高度 */
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
// 元件
// ============================================================================

export const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({
  documentIds,
  height = 500,
}) => {
  const fgRef = useRef<ForceGraphMethods | undefined>();
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(800);

  // API 狀態
  const [rawNodes, setRawNodes] = useState<GraphNode[]>([]);
  const [rawEdges, setRawEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 互動狀態
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [visibleTypes, setVisibleTypes] = useState<Set<string>>(
    new Set(['document', 'project', 'agency', 'dispatch', 'org', 'person', 'location', 'date', 'topic'])
  );

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

  // 鄰居 lookup（用於點擊高亮）
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

  // 搜尋匹配的節點 ID
  const searchMatchIds = useMemo(() => {
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

  // 轉換為 force-graph 格式（含過濾）
  const graphData = useMemo((): GraphData => {
    const filteredNodes = rawNodes.filter((n) => visibleTypes.has(n.type));
    const nodeIdSet = new Set(filteredNodes.map((n) => n.id));

    const nodes: ForceNode[] = filteredNodes.map((n) => ({
      id: n.id,
      label: n.label,
      type: n.type,
      color: NODE_COLORS[n.type] || '#999',
      category: n.category,
      doc_number: n.doc_number,
      status: n.status,
    }));

    const links: ForceLink[] = rawEdges
      .filter((e) => nodeIdSet.has(e.source) && nodeIdSet.has(e.target))
      .map((e) => ({
        source: e.source,
        target: e.target,
        label: e.label,
        type: e.type,
      }));

    return { nodes, links };
  }, [rawNodes, rawEdges, visibleTypes]);

  // 判斷節點是否應高亮
  const isHighlighted = useCallback((nodeId: string): boolean => {
    // 搜尋模式
    if (searchMatchIds) return searchMatchIds.has(nodeId);
    // 點擊高亮模式
    if (selectedNodeId) {
      return nodeId === selectedNodeId || (neighborMap.get(selectedNodeId)?.has(nodeId) ?? false);
    }
    // Hover 高亮
    if (hoveredNodeId) {
      return nodeId === hoveredNodeId || (neighborMap.get(hoveredNodeId)?.has(nodeId) ?? false);
    }
    return true;
  }, [searchMatchIds, selectedNodeId, hoveredNodeId, neighborMap]);

  // 判斷邊是否應高亮
  const isLinkHighlighted = useCallback((link: ForceLink): boolean => {
    const srcId = getNodeId(link.source);
    const tgtId = getNodeId(link.target);
    if (searchMatchIds) return searchMatchIds.has(srcId) || searchMatchIds.has(tgtId);
    if (selectedNodeId) return srcId === selectedNodeId || tgtId === selectedNodeId;
    if (hoveredNodeId) return srcId === hoveredNodeId || tgtId === hoveredNodeId;
    return true;
  }, [searchMatchIds, selectedNodeId, hoveredNodeId]);

  // Canvas 自訂繪製節點
  const paintNode = useCallback((node: ForceNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const x = node.x ?? 0;
    const y = node.y ?? 0;
    const r = NODE_RADIUS[node.type] || 6;
    const highlighted = isHighlighted(node.id);
    const isSelected = selectedNodeId === node.id;
    const isSearchMatch = searchMatchIds?.has(node.id);

    // 圓形節點
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.fillStyle = highlighted ? node.color : 'rgba(200,200,200,0.3)';
    ctx.fill();

    // 邊框
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

    // 標籤（全域縮放 > 1.0 或被選中時顯示）
    if (globalScale > 1.0 || isSelected || isSearchMatch) {
      const fontSize = Math.max(10 / globalScale, 2);
      ctx.font = `${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = highlighted ? '#333' : 'rgba(180,180,180,0.5)';
      ctx.fillText(truncate(node.label, 14), x, y + r + 2 / globalScale);
    }
  }, [isHighlighted, selectedNodeId, searchMatchIds]);

  // 點擊節點
  const handleNodeClick = useCallback((node: ForceNode) => {
    setSelectedNodeId((prev) => (prev === node.id ? null : node.id));
  }, []);

  // Hover 節點
  const handleNodeHover = useCallback((node: ForceNode | null) => {
    setHoveredNodeId(node?.id ?? null);
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
    // 觸發 useEffect 重新載入
    setRawNodes([]);
    setRawEdges([]);
    setLoading(true);
    aiApi.getRelationGraph({ document_ids: documentIds }).then((result) => {
      if (result) {
        setRawNodes(result.nodes);
        setRawEdges(result.edges);
      }
      setLoading(false);
      setTimeout(() => fgRef.current?.zoomToFit(400, 40), 500);
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

  // Zoom to fit on initial load
  useEffect(() => {
    if (!loading && rawNodes.length > 0) {
      setTimeout(() => fgRef.current?.zoomToFit(600, 50), 300);
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
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height }}>
        <Spin tip="載入關聯圖譜..." />
      </div>
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
        {/* 搜尋 */}
        <Input
          prefix={<SearchOutlined />}
          placeholder="搜尋節點..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          allowClear
          size="small"
          style={{ width: 180 }}
        />

        {/* 類型過濾（只顯示圖譜中實際存在的類型） */}
        <Space size={4}>
          {Object.entries(TYPE_LABELS).filter(([type]) => rawNodes.some((n) => n.type === type)).map(([type, label]) => (
            <Checkbox
              key={type}
              checked={visibleTypes.has(type)}
              onChange={(e) => handleTypeToggle(type, e.target.checked)}
              style={{ fontSize: 12 }}
            >
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                <span style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: NODE_COLORS[type], display: 'inline-block',
                }} />
                {label}
              </span>
            </Checkbox>
          ))}
        </Space>

        {/* 按鈕 */}
        <Space size={4} style={{ marginLeft: 'auto' }}>
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
            （{neighborMap.get(selectedNodeId)?.size || 0} 個鄰居）
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
          // 力學參數
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
          // 節點
          nodeCanvasObject={paintNode as any}
          nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
            const r = NODE_RADIUS[node.type] || 6;
            ctx.beginPath();
            ctx.arc(node.x ?? 0, node.y ?? 0, r + 2, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          }}
          onNodeClick={handleNodeClick as any}
          onNodeHover={handleNodeHover as any}
          // 邊
          linkColor={(link: any) => isLinkHighlighted(link) ? 'rgba(150,150,150,0.6)' : 'rgba(220,220,220,0.2)'}
          linkWidth={(link: any) => isLinkHighlighted(link) ? 1.5 : 0.5}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={0.85}
          linkDirectionalArrowColor={(link: any) => isLinkHighlighted(link) ? 'rgba(120,120,120,0.5)' : 'rgba(220,220,220,0.2)'}
          linkCanvasObjectMode={() => 'after'}
          linkCanvasObject={(link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
            // 邊標籤（只在縮放 > 1.5 且高亮時顯示）
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
          // 背景
          onBackgroundClick={() => setSelectedNodeId(null)}
          // 效能
          warmupTicks={50}
          cooldownTicks={100}
        />
      </div>

      {/* Hover 節點詳情浮動面板 */}
      {hoveredNodeId && (() => {
        const node = graphData.nodes.find((n) => n.id === hoveredNodeId);
        if (!node) return null;
        return (
          <div style={{
            position: 'absolute', top: 45, right: 8,
            background: 'white', border: '1px solid #d9d9d9', borderRadius: 6,
            padding: '8px 12px', fontSize: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            minWidth: 160, zIndex: 10, pointerEvents: 'none',
          }}>
            <div style={{ fontWeight: 'bold', marginBottom: 4, color: node.color }}>
              {TYPE_LABELS[node.type] || node.type}
            </div>
            <div>{node.label}</div>
            {node.doc_number && <div style={{ color: '#666' }}>文號：{node.doc_number}</div>}
            {node.category && <div style={{ color: '#666' }}>分類：{node.category}</div>}
            {node.status && <div style={{ color: '#666' }}>狀態：{node.status}</div>}
          </div>
        );
      })()}
    </div>
  );
};

export default KnowledgeGraph;

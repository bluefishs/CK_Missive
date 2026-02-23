/**
 * KnowledgeGraph - 公文關聯網絡視覺化元件
 *
 * 純 SVG 放射狀佈局，零額外依賴。
 * 節點按類型分色：公文=藍, 專案=綠, 機關=橙, 派工=紫
 *
 * @version 1.0.0
 * @created 2026-02-24
 */

import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { Spin, Empty, Tooltip } from 'antd';
import { aiApi, type GraphNode, type GraphEdge } from '../../api/aiApi';

// ============================================================================
// 常數
// ============================================================================

const NODE_COLORS: Record<string, string> = {
  document: '#1890ff',
  project: '#52c41a',
  agency: '#fa8c16',
  dispatch: '#722ed1',
};

const NODE_RADIUS: Record<string, number> = {
  document: 20,
  project: 26,
  agency: 18,
  dispatch: 22,
};

const TYPE_LABELS: Record<string, string> = {
  document: '公文',
  project: '專案',
  agency: '機關',
  dispatch: '派工',
};

// ============================================================================
// 佈局演算法
// ============================================================================

interface LayoutNode extends GraphNode {
  x: number;
  y: number;
  r: number;
}

function computeLayout(
  nodes: GraphNode[],
  edges: GraphEdge[],
  width: number,
  height: number,
): LayoutNode[] {
  if (nodes.length === 0) return [];

  const cx = width / 2;
  const cy = height / 2;

  // 按類型分組
  const groups: Record<string, GraphNode[]> = {};
  for (const node of nodes) {
    if (!groups[node.type]) groups[node.type] = [];
    groups[node.type]!.push(node);
  }

  const layoutNodes: LayoutNode[] = [];
  const typeOrder = ['project', 'dispatch', 'document', 'agency'];
  const ringRadii = [0, 80, 160, 230];

  let ringIndex = 0;
  for (const type of typeOrder) {
    const group = groups[type];
    if (!group || group.length === 0) continue;

    const radius = ringRadii[Math.min(ringIndex, ringRadii.length - 1)] || 230;
    const angleStep = (2 * Math.PI) / Math.max(group.length, 1);
    const startAngle = ringIndex * 0.3; // 錯開角度

    group.forEach((node, i) => {
      const angle = startAngle + i * angleStep;
      layoutNodes.push({
        ...node,
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
        r: NODE_RADIUS[node.type] || 18,
      });
    });

    ringIndex++;
  }

  return layoutNodes;
}

// ============================================================================
// Props
// ============================================================================

export interface KnowledgeGraphProps {
  /** 要顯示關聯的公文 ID 列表 */
  documentIds: number[];
  /** SVG 寬度 */
  width?: number;
  /** SVG 高度 */
  height?: number;
}

// ============================================================================
// 元件
// ============================================================================

export const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({
  documentIds,
  width = 560,
  height = 400,
}) => {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState(false);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  // 載入圖譜資料
  useEffect(() => {
    if (documentIds.length === 0) return;

    let cancelled = false;
    setLoading(true);

    aiApi.getRelationGraph({ document_ids: documentIds }).then((result) => {
      if (cancelled) return;
      if (result) {
        setNodes(result.nodes);
        setEdges(result.edges);
      }
      setLoading(false);
    });

    return () => { cancelled = true; };
  }, [documentIds]);

  // 計算佈局
  const layoutNodes = useMemo(
    () => computeLayout(nodes, edges, width, height),
    [nodes, edges, width, height],
  );

  // 節點位置 lookup
  const nodeMap = useMemo(() => {
    const map = new Map<string, LayoutNode>();
    for (const n of layoutNodes) map.set(n.id, n);
    return map;
  }, [layoutNodes]);

  // 高亮連接邊
  const highlightedEdges = useMemo(() => {
    if (!hoveredNode) return new Set<string>();
    const set = new Set<string>();
    for (const e of edges) {
      if (e.source === hoveredNode || e.target === hoveredNode) {
        set.add(`${e.source}->${e.target}`);
      }
    }
    return set;
  }, [hoveredNode, edges]);

  const handleNodeHover = useCallback((id: string | null) => {
    setHoveredNode(id);
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height }}>
        <Spin tip="載入關聯圖譜..." />
      </div>
    );
  }

  if (nodes.length === 0) {
    return <Empty description="無關聯資料" style={{ padding: 20 }} />;
  }

  return (
    <div style={{ position: 'relative' }}>
      {/* 圖例 */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 6, fontSize: 11, color: '#666' }}>
        {Object.entries(TYPE_LABELS).map(([type, label]) => (
          <span key={type} style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{
              width: 10, height: 10, borderRadius: '50%',
              background: NODE_COLORS[type], display: 'inline-block',
            }} />
            {label}
          </span>
        ))}
      </div>

      <svg
        width={width}
        height={height}
        style={{ background: '#fafafa', borderRadius: 8, border: '1px solid #f0f0f0' }}
      >
        {/* 邊 */}
        {edges.map((edge) => {
          const src = nodeMap.get(edge.source);
          const tgt = nodeMap.get(edge.target);
          if (!src || !tgt) return null;
          const edgeKey = `${edge.source}->${edge.target}`;
          const isHighlighted = hoveredNode
            ? highlightedEdges.has(edgeKey)
            : true;

          return (
            <g key={edgeKey}>
              <line
                x1={src.x} y1={src.y}
                x2={tgt.x} y2={tgt.y}
                stroke={isHighlighted ? '#999' : '#e8e8e8'}
                strokeWidth={isHighlighted && hoveredNode ? 2 : 1}
                opacity={isHighlighted ? 0.8 : 0.3}
              />
              {isHighlighted && edge.label && (
                <text
                  x={(src.x + tgt.x) / 2}
                  y={(src.y + tgt.y) / 2 - 4}
                  textAnchor="middle"
                  fontSize={9}
                  fill="#999"
                >
                  {edge.label}
                </text>
              )}
            </g>
          );
        })}

        {/* 節點 */}
        {layoutNodes.map((node) => {
          const isHovered = hoveredNode === node.id;
          const isConnected = hoveredNode
            ? highlightedEdges.has(`${hoveredNode}->${node.id}`) ||
              highlightedEdges.has(`${node.id}->${hoveredNode}`) ||
              isHovered
            : true;

          return (
            <Tooltip
              key={node.id}
              title={
                <div style={{ fontSize: 12 }}>
                  <div><strong>{node.label}</strong></div>
                  {node.doc_number && <div>文號: {node.doc_number}</div>}
                  {node.category && <div>分類: {node.category}</div>}
                  {node.status && <div>狀態: {node.status}</div>}
                  <div style={{ color: '#aaa' }}>{TYPE_LABELS[node.type] || node.type}</div>
                </div>
              }
            >
              <g
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => handleNodeHover(node.id)}
                onMouseLeave={() => handleNodeHover(null)}
                opacity={isConnected ? 1 : 0.3}
              >
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={isHovered ? node.r + 3 : node.r}
                  fill={NODE_COLORS[node.type] || '#999'}
                  opacity={0.85}
                  stroke={isHovered ? '#333' : 'white'}
                  strokeWidth={isHovered ? 2 : 1.5}
                />
                <text
                  x={node.x}
                  y={node.y + node.r + 12}
                  textAnchor="middle"
                  fontSize={10}
                  fill="#333"
                >
                  {node.label.length > 8 ? node.label.slice(0, 8) + '...' : node.label}
                </text>
              </g>
            </Tooltip>
          );
        })}
      </svg>
    </div>
  );
};

export default KnowledgeGraph;

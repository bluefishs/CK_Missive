import React from 'react';
import type { MergedNodeConfig } from '../../../config/graphNodeConfig';
import type { ForceNode, GraphData } from './types';

interface GraphStatsBarProps {
  graphData: GraphData;
  selectedNodeId: string | null;
  neighborMap: Map<string, Set<string>>;
  mergedConfigs: Record<string, MergedNodeConfig>;
  effectiveGetNodeConfig: (type: string) => { label?: string; color: string };
}

export const GraphStatsBar: React.FC<GraphStatsBarProps> = ({
  graphData,
  selectedNodeId,
  neighborMap,
  mergedConfigs,
  effectiveGetNodeConfig,
}) => {
  return (
    <div style={{ fontSize: 11, color: '#999', marginBottom: 4 }}>
      {graphData.nodes.length} 個節點 · {graphData.links.length} 條關聯
      {selectedNodeId && (() => {
        const sel = graphData.nodes.find((n: ForceNode) => n.id === selectedNodeId);
        if (!sel) return null;
        const neighborIds = neighborMap.get(selectedNodeId);
        const neighborNodes = neighborIds
          ? graphData.nodes.filter((n: ForceNode) => neighborIds.has(n.id))
          : [];
        // 按類型分組鄰居摘要
        const typeSummary: Record<string, string[]> = {};
        for (const nb of neighborNodes) {
          const merged = mergedConfigs[nb.type] ?? effectiveGetNodeConfig(nb.type);
          const typeLabel = merged.label || nb.type;
          if (!typeSummary[typeLabel]) typeSummary[typeLabel] = [];
          if (typeSummary[typeLabel].length < 3) typeSummary[typeLabel].push(nb.label);
        }
        const summaryParts = Object.entries(typeSummary)
          .sort((a, b) => b[1].length - a[1].length)
          .slice(0, 4)
          .map(([type, labels]) => {
            const extra = neighborNodes.filter((n: ForceNode) => {
              const m = mergedConfigs[n.type] ?? effectiveGetNodeConfig(n.type);
              return (m.label || n.type) === type;
            }).length;
            return `${type}(${extra}): ${labels.slice(0, 2).join('、')}${extra > 2 ? '…' : ''}`;
          });
        return (
          <span style={{ marginLeft: 8, color: '#1890ff' }}>
            已選取：{sel.label}（{neighborIds?.size || 0} 個關聯）
            {summaryParts.length > 0 && (
              <span style={{ color: '#666', marginLeft: 4 }}>
                — {summaryParts.join(' | ')}
              </span>
            )}
          </span>
        );
      })()}
    </div>
  );
};

/**
 * Legend Panel - Bottom-left legend with category colors
 *
 * @version 1.0.0
 */

import React from 'react';
import { Flex, Typography } from 'antd';
import type { CategoryInfo, SkillNode } from './types';

const { Text } = Typography;

interface LegendPanelProps {
  categories: Record<string, CategoryInfo>;
  nodes: SkillNode[];
}

export const LegendPanel: React.FC<LegendPanelProps> = ({ categories, nodes }) => {
  // Count nodes per category
  const counts = new Map<string, number>();
  for (const n of nodes) {
    counts.set(n.category, (counts.get(n.category) || 0) + 1);
  }

  return (
    <div style={{
      position: 'absolute',
      bottom: 16,
      left: 16,
      background: 'rgba(18, 18, 42, 0.92)',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 8,
      padding: '12px 16px',
      minWidth: 160,
      backdropFilter: 'blur(8px)',
    }}>
      <Text strong style={{ color: '#ccc', fontSize: 12, display: 'block', marginBottom: 8 }}>
        圖例
      </Text>
      <Flex vertical gap={4}>
        {Object.entries(categories).map(([key, info]) => {
          const count = counts.get(key) || 0;
          if (count === 0) return null;
          return (
            <Flex key={key} align="center" gap={6}>
              <span style={{
                display: 'inline-block', width: 10, height: 10,
                borderRadius: '50%', background: info.color, flexShrink: 0,
              }} />
              <Text style={{ color: '#aaa', fontSize: 11, flex: 1 }}>{info.label}</Text>
              <Text style={{ color: '#666', fontSize: 10 }}>{count}</Text>
            </Flex>
          );
        })}
      </Flex>

      {/* Edge type legend */}
      <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', marginTop: 8, paddingTop: 8 }}>
        <Flex vertical gap={3}>
          <Flex align="center" gap={6}>
            <svg width={20} height={8}><line x1={0} y1={4} x2={20} y2={4} stroke="#50c878" strokeWidth={2} /></svg>
            <Text style={{ color: '#aaa', fontSize: 10 }}>演化</Text>
          </Flex>
          <Flex align="center" gap={6}>
            <svg width={20} height={8}><line x1={0} y1={4} x2={20} y2={4} stroke="#ff5050" strokeWidth={1.5} strokeDasharray="4 3" /></svg>
            <Text style={{ color: '#aaa', fontSize: 10 }}>融合</Text>
          </Flex>
          <Flex align="center" gap={6}>
            <svg width={20} height={8}><line x1={0} y1={4} x2={20} y2={4} stroke="#999" strokeWidth={1} strokeDasharray="3 4" /></svg>
            <Text style={{ color: '#aaa', fontSize: 10 }}>規劃中</Text>
          </Flex>
        </Flex>
      </div>
    </div>
  );
};

/**
 * Stats Panel - Bottom-right statistics display
 *
 * @version 1.0.0
 */

import React from 'react';
import { Flex, Typography } from 'antd';
import {
  ThunderboltOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  MergeCellsOutlined,
  BranchesOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons';
import type { SkillEvolutionStats } from './types';

const { Text } = Typography;

interface StatsPanelProps {
  stats: SkillEvolutionStats;
}

interface StatItemProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}

const StatItem: React.FC<StatItemProps> = ({ icon, label, value, color }) => (
  <Flex align="center" gap={6}>
    <span style={{ color, fontSize: 14 }}>{icon}</span>
    <Text style={{ color: '#aaa', fontSize: 11 }}>{label}</Text>
    <Text strong style={{ color: '#e0e0e0', fontSize: 13, marginLeft: 'auto' }}>{value}</Text>
  </Flex>
);

export const StatsPanel: React.FC<StatsPanelProps> = ({ stats }) => {
  return (
    <div style={{
      position: 'absolute',
      bottom: 16,
      right: 16,
      background: 'rgba(18, 18, 42, 0.92)',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 8,
      padding: '12px 16px',
      minWidth: 180,
      backdropFilter: 'blur(8px)',
    }}>
      <Text strong style={{ color: '#ccc', fontSize: 12, display: 'block', marginBottom: 8 }}>
        統計
      </Text>
      <Flex vertical gap={6}>
        <StatItem icon={<ThunderboltOutlined />} label="技能總數" value={stats.total} color="#50c878" />
        <StatItem icon={<CheckCircleOutlined />} label="啟用" value={stats.active} color="#52c41a" />
        <StatItem icon={<ClockCircleOutlined />} label="規劃中" value={stats.planned} color="#888" />
        <StatItem icon={<MergeCellsOutlined />} label="已融合" value={stats.merged} color="#f5c842" />
        <StatItem icon={<BranchesOutlined />} label="演化次數" value={stats.evolution_count} color="#50c878" />
        <StatItem icon={<NodeIndexOutlined />} label="融合次數" value={stats.merge_count} color="#ff5050" />
      </Flex>
    </div>
  );
};

/**
 * MemoryStatsRow — Memory Wiki 6 張統計卡片（ADR-0031 Phase 3）
 *
 * 提取自 kunge/MemoryTab + MemoryDashboardPage 的重複實作。
 *
 * 呈現 6 個核心指標：
 *   日記天數 · 成功模式 · 失敗教訓 · 待批提案 · 已套用結晶 · 週自傳
 *
 * @version 1.0.0 — 2026-04-22
 */

import React from 'react';
import { Card, Col, Row, Statistic } from 'antd';
import {
  BookOutlined,
  BranchesOutlined,
  BulbOutlined,
  CrownOutlined,
  HistoryOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons';
import type { MemoryStats } from '../../types/memory';

export interface MemoryStatsRowProps {
  stats: MemoryStats | undefined;
  loading?: boolean;
  /** 卡片 span 配置，預設為 xs=12 md=8 lg=4（6 欄） */
  colSpans?: { xs?: number; md?: number; lg?: number };
}

/**
 * Memory Wiki 統計 6-卡片 Row。
 *
 * @example
 * ```tsx
 * const { data: stats, isLoading } = useMemoryStats();
 * <MemoryStatsRow stats={stats} loading={isLoading} />
 * ```
 */
export const MemoryStatsRow: React.FC<MemoryStatsRowProps> = ({
  stats,
  loading = false,
  colSpans = { xs: 12, md: 8, lg: 4 },
}) => (
  <Row gutter={[12, 12]}>
    <Col {...colSpans}>
      <Card size="small" loading={loading}>
        <Statistic
          title="日記天數"
          value={stats?.diary_days ?? 0}
          prefix={<BookOutlined />}
        />
      </Card>
    </Col>
    <Col {...colSpans}>
      <Card size="small" loading={loading}>
        <Statistic
          title="成功模式"
          value={stats?.patterns ?? 0}
          prefix={<BranchesOutlined />}
          valueStyle={{ color: '#52c41a' }}
        />
      </Card>
    </Col>
    <Col {...colSpans}>
      <Card size="small" loading={loading}>
        <Statistic
          title="失敗教訓"
          value={stats?.failures ?? 0}
          prefix={<BulbOutlined />}
          valueStyle={{
            color: (stats?.failures ?? 0) > 0 ? '#fa541c' : undefined,
          }}
        />
      </Card>
    </Col>
    <Col {...colSpans}>
      <Card size="small" loading={loading}>
        <Statistic
          title="待批提案"
          value={stats?.proposals_pending ?? 0}
          suffix={
            <span style={{ fontSize: 12, color: '#888' }}>
              / {stats?.proposals_total ?? 0}
            </span>
          }
          prefix={<CrownOutlined />}
          valueStyle={{
            color: (stats?.proposals_pending ?? 0) > 0 ? '#fa8c16' : undefined,
          }}
        />
      </Card>
    </Col>
    <Col {...colSpans}>
      <Card size="small" loading={loading}>
        <Statistic
          title="已套用結晶"
          value={stats?.crystals ?? 0}
          prefix={<NodeIndexOutlined />}
        />
      </Card>
    </Col>
    <Col {...colSpans}>
      <Card size="small" loading={loading}>
        <Statistic
          title="週自傳"
          value={stats?.evolutions ?? 0}
          prefix={<HistoryOutlined />}
        />
      </Card>
    </Col>
  </Row>
);

export default MemoryStatsRow;

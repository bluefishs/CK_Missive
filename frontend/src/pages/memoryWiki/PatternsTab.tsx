/**
 * PatternsTab — 成功模式與失敗教訓
 *
 * Phase 5 Slice 3 — 兩個子區塊。
 */
import React from 'react';
import { Alert, Card, Col, Empty, Row, Spin, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { useFailuresList, usePatternsList } from '../../hooks/useMemoryData';
import type { FailureSummary, PatternSummary } from '../../types/memory';

const patternColumns: ColumnsType<PatternSummary> = [
  { title: '檔名', dataIndex: 'filename', key: 'filename', ellipsis: true, width: 220 },
  {
    title: 'hit / success',
    key: 'hit',
    render: (_, r) => (
      <span>
        <Tag color="blue">{r.meta?.hit_count ?? '-'}</Tag>
        <Tag color="green">{r.meta?.success_count ?? '-'}</Tag>
      </span>
    ),
  },
  {
    title: 'success_rate',
    key: 'rate',
    render: (_, r) => {
      const rate = r.meta?.success_rate;
      if (typeof rate !== 'number') return '-';
      return <Tag color={rate >= 0.9 ? 'green' : rate >= 0.7 ? 'orange' : 'red'}>{(rate * 100).toFixed(1)}%</Tag>;
    },
  },
  {
    title: '結晶候選',
    key: 'crystal',
    render: (_, r) => (
      r.meta?.crystallized
        ? <Tag color="gold">已結晶</Tag>
        : r.meta?.crystallization_candidate
          ? <Tag color="cyan">候選</Tag>
          : <Tag>-</Tag>
    ),
  },
  { title: '最後見', dataIndex: ['meta', 'last_seen'], key: 'last_seen', width: 180 },
];

const failureColumns: ColumnsType<FailureSummary> = [
  { title: '檔名', dataIndex: 'filename', key: 'filename', ellipsis: true, width: 220 },
  {
    title: 'hit / failure_rate',
    key: 'fail',
    render: (_, r) => (
      <span>
        <Tag color="blue">{r.meta?.hit_count ?? '-'}</Tag>
        <Tag color="red">
          {typeof r.meta?.failure_rate === 'number' ? `${(r.meta.failure_rate * 100).toFixed(1)}%` : '-'}
        </Tag>
      </span>
    ),
  },
  {
    title: '啟用',
    dataIndex: ['meta', 'active'],
    key: 'active',
    render: (v: unknown) => (v ? <Tag color="green">active</Tag> : <Tag>停用</Tag>),
  },
  {
    title: '防禦規則',
    dataIndex: ['meta', 'defense_rule'],
    key: 'defense_rule',
    ellipsis: true,
  },
];

const PatternsTab: React.FC = () => {
  const { data: patterns = [], isLoading: loadingP } = usePatternsList({ limit: 100 });
  const { data: failures = [], isLoading: loadingF } = useFailuresList({ limit: 100 });

  return (
    <Row gutter={[16, 16]} style={{ marginTop: 12 }}>
      <Col xs={24}>
        <Card
          size="small"
          title={<span>成功模式 <Tag color="green">{patterns.length}</Tag></span>}
        >
          {loadingP ? (
            <Spin />
          ) : patterns.length === 0 ? (
            <Empty description="尚無成功模式（Pattern Extractor 04:00 自動產生）" />
          ) : (
            <Table
              size="small"
              rowKey="filename"
              columns={patternColumns}
              dataSource={patterns}
              pagination={{ pageSize: 20 }}
              scroll={{ x: 'max-content' }}
            />
          )}
        </Card>
      </Col>
      <Col xs={24}>
        <Card
          size="small"
          title={<span>失敗教訓 <Tag color="red">{failures.length}</Tag></span>}
        >
          <Alert
            type="info"
            message="active=true 的失敗規則會被 agent_planner 自動注入為防禦規則"
            style={{ marginBottom: 12 }}
            showIcon
          />
          {loadingF ? (
            <Spin />
          ) : failures.length === 0 ? (
            <Typography.Text type="secondary">尚無失敗教訓</Typography.Text>
          ) : (
            <Table
              size="small"
              rowKey="filename"
              columns={failureColumns}
              dataSource={failures}
              pagination={{ pageSize: 20 }}
              scroll={{ x: 'max-content' }}
            />
          )}
        </Card>
      </Col>
    </Row>
  );
};

export default PatternsTab;

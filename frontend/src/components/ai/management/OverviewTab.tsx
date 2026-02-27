/**
 * OverviewTab - 搜尋統計總覽
 *
 * 條件渲染：無搜尋紀錄時顯示簡潔空狀態，
 * 分佈統計區塊僅在有資料時顯示。
 *
 * @version 2.1.0
 * @updated 2026-02-27 — 條件渲染優化，避免顯示大量「無數據」空殼
 */
import React, { useMemo } from 'react';
import {
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Row,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloudServerOutlined,
  DashboardOutlined,
  ReloadOutlined,
  SearchOutlined,
  TagsOutlined,
  ThunderboltOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import type { ColumnsType } from 'antd/es/table';

import { aiApi } from '../../../api/aiApi';
import type { DailyTrend, TopQuery } from '../../../types/ai';

export const OverviewTab: React.FC = () => {
  const {
    data: stats = null,
    isLoading: loading,
    refetch: loadStats,
  } = useQuery({
    queryKey: ['ai-management', 'search-stats'],
    queryFn: () => aiApi.getSearchStats(),
    staleTime: 5 * 60 * 1000,
  });

  const topQueryColumns: ColumnsType<TopQuery> = useMemo(() => [
    { title: '查詢內容', dataIndex: 'query', key: 'query', ellipsis: true },
    { title: '次數', dataIndex: 'count', key: 'count', width: 80, sorter: (a, b) => a.count - b.count },
    {
      title: '平均結果',
      dataIndex: 'avg_results',
      key: 'avg_results',
      width: 100,
      render: (v: number | null) => v != null ? v.toFixed(1) : '-',
    },
  ], []);

  const trendColumns: ColumnsType<DailyTrend> = useMemo(() => [
    { title: '日期', dataIndex: 'date', key: 'date', width: 120 },
    { title: '搜尋次數', dataIndex: 'count', key: 'count', width: 100 },
  ], []);

  if (loading) {
    return (
      <Spin tip="載入統計中...">
        <div style={{ height: 200 }} />
      </Spin>
    );
  }

  if (!stats) {
    return <Empty description="無法載入統計資料" />;
  }

  // 無任何搜尋紀錄 → 簡潔空狀態
  if (stats.total_searches === 0) {
    return (
      <Empty
        description="尚無搜尋紀錄，使用 AI 搜尋後將自動產生統計資料"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      >
        <Button size="small" icon={<ReloadOutlined />} onClick={() => loadStats()}>
          重新整理
        </Button>
      </Empty>
    );
  }

  // 判斷分佈區塊是否有資料
  const hasDistributions =
    Object.keys(stats.strategy_distribution).length > 0 ||
    Object.keys(stats.source_distribution).length > 0 ||
    Object.keys(stats.entity_distribution).length > 0;

  return (
    <div>
      {/* 統計卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="總搜尋次數"
              value={stats.total_searches}
              prefix={<SearchOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="今日搜尋"
              value={stats.today_searches}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="規則引擎命中率"
              value={stats.rule_engine_hit_rate * 100}
              suffix="%"
              precision={1}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: stats.rule_engine_hit_rate > 0.5 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="平均回應時間"
              value={stats.avg_latency_ms}
              suffix="ms"
              precision={0}
              prefix={<DashboardOutlined />}
              valueStyle={{ color: stats.avg_latency_ms < 500 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
      </Row>

      {/* AI 信心度與搜尋品質 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="平均信心度"
              value={(stats.avg_confidence ?? 0) * 100}
              suffix="%"
              precision={1}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: (stats.avg_confidence ?? 0) >= 0.6 ? '#3f8600' : '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="錯誤源比例"
              value={
                stats.source_distribution?.error
                  ? ((stats.source_distribution.error / Math.max(stats.total_searches, 1)) * 100)
                  : 0
              }
              suffix="%"
              precision={1}
              prefix={<WarningOutlined />}
              valueStyle={{
                color: (stats.source_distribution?.error ?? 0) > 0 ? '#cf1322' : '#3f8600',
              }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="同義詞擴展使用"
              value={
                stats.strategy_distribution?.hybrid
                  ? stats.strategy_distribution.hybrid
                  : 0
              }
              suffix="次"
              prefix={<TagsOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="派工搜尋次數"
              value={stats.entity_distribution?.dispatch_order ?? 0}
              suffix="次"
              prefix={<CloudServerOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 分佈統計（僅在有資料時顯示） */}
      {hasDistributions && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          {Object.keys(stats.strategy_distribution).length > 0 && (
            <Col xs={24} sm={8}>
              <Card title="搜尋策略分佈" size="small">
                <Descriptions column={1} size="small">
                  {Object.entries(stats.strategy_distribution).map(([key, val]) => (
                    <Descriptions.Item key={key} label={
                      <Tag color={key === 'hybrid' ? 'purple' : key === 'similarity' ? 'blue' : 'default'}>{key}</Tag>
                    }>
                      {val} 次
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              </Card>
            </Col>
          )}
          {Object.keys(stats.source_distribution).length > 0 && (
            <Col xs={24} sm={8}>
              <Card title="解析來源分佈" size="small">
                <Descriptions column={1} size="small">
                  {Object.entries(stats.source_distribution).map(([key, val]) => (
                    <Descriptions.Item key={key} label={
                      <Tag color={key === 'rule_engine' ? 'green' : key === 'vector' ? 'cyan' : key === 'ai' ? 'blue' : key === 'merged' ? 'purple' : 'default'}>{key}</Tag>
                    }>
                      {val} 次
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              </Card>
            </Col>
          )}
          {Object.keys(stats.entity_distribution).length > 0 && (
            <Col xs={24} sm={8}>
              <Card title="實體類型分佈" size="small">
                <Descriptions column={1} size="small">
                  {Object.entries(stats.entity_distribution).map(([key, val]) => (
                    <Descriptions.Item key={key} label={
                      <Tag color="volcano">{key === 'dispatch_order' ? '派工單' : key === 'project' ? '專案' : key}</Tag>
                    }>
                      {val} 次
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              </Card>
            </Col>
          )}
        </Row>
      )}

      {/* 熱門查詢與趨勢 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={14}>
          <Card title="熱門查詢 Top 10" size="small">
            <Table
              dataSource={stats.top_queries}
              columns={topQueryColumns}
              rowKey="query"
              size="small"
              pagination={false}
              locale={{ emptyText: '尚無搜尋紀錄' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={10}>
          <Card
            title="近 30 天搜尋趨勢"
            size="small"
            extra={<Button size="small" icon={<ReloadOutlined />} onClick={() => loadStats()}>重新整理</Button>}
          >
            <Table
              dataSource={stats.daily_trend}
              columns={trendColumns}
              rowKey="date"
              size="small"
              pagination={false}
              scroll={{ y: 300 }}
              locale={{ emptyText: '尚無趨勢資料' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

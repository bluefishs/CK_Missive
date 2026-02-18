/**
 * AI 助理管理頁面
 *
 * Version: 1.0.0
 * Created: 2026-02-09
 *
 * 統一管理入口，整合搜尋統計、搜尋歷史、同義詞管理、Prompt 管理。
 */
import React, { useMemo, useState } from 'react';
import {
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Empty,
  Input,
  message,
  Popconfirm,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import {
  BarChartOutlined,
  ClockCircleOutlined,
  DashboardOutlined,
  DeleteOutlined,
  ExperimentOutlined,
  HistoryOutlined,
  ReloadOutlined,
  RobotOutlined,
  SearchOutlined,
  TagsOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import type { ColumnsType } from 'antd/es/table';

import { aiApi } from '../api/aiApi';
import type {
  SearchHistoryItem,
  SearchHistoryListRequest,
  SearchStatsResponse,
  DailyTrend,
  TopQuery,
} from '../api/aiApi';
import { SynonymManagementContent } from './AISynonymManagementPage';
import { PromptManagementContent } from './AIPromptManagementPage';

const { Title, Text } = Typography;

// ============================================================================
// Tab 1: 搜尋總覽
// ============================================================================
const OverviewTab: React.FC = () => {
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

      {/* 分佈統計 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card title="搜尋策略分佈" size="small">
            {Object.entries(stats.strategy_distribution).length > 0 ? (
              <Descriptions column={1} size="small">
                {Object.entries(stats.strategy_distribution).map(([key, val]) => (
                  <Descriptions.Item key={key} label={
                    <Tag color={key === 'hybrid' ? 'purple' : key === 'similarity' ? 'blue' : 'default'}>{key}</Tag>
                  }>
                    {val} 次
                  </Descriptions.Item>
                ))}
              </Descriptions>
            ) : <Empty description="無數據" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card title="解析來源分佈" size="small">
            {Object.entries(stats.source_distribution).length > 0 ? (
              <Descriptions column={1} size="small">
                {Object.entries(stats.source_distribution).map(([key, val]) => (
                  <Descriptions.Item key={key} label={
                    <Tag color={key === 'rule_engine' ? 'green' : key === 'vector' ? 'cyan' : key === 'ai' ? 'blue' : key === 'merged' ? 'purple' : 'default'}>{key}</Tag>
                  }>
                    {val} 次
                  </Descriptions.Item>
                ))}
              </Descriptions>
            ) : <Empty description="無數據" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card title="實體類型分佈" size="small">
            {Object.entries(stats.entity_distribution).length > 0 ? (
              <Descriptions column={1} size="small">
                {Object.entries(stats.entity_distribution).map(([key, val]) => (
                  <Descriptions.Item key={key} label={
                    <Tag color="volcano">{key === 'dispatch_order' ? '派工單' : key === 'project' ? '專案' : key}</Tag>
                  }>
                    {val} 次
                  </Descriptions.Item>
                ))}
              </Descriptions>
            ) : <Empty description="無數據" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
          </Card>
        </Col>
      </Row>

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
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

// ============================================================================
// Tab 2: 搜尋歷史
// ============================================================================
const HistoryTab: React.FC = () => {
  const queryClient = useQueryClient();
  const [params, setParams] = useState<SearchHistoryListRequest>({
    page: 1,
    page_size: 20,
  });

  const {
    data: historyData,
    isLoading: loading,
  } = useQuery({
    queryKey: ['ai-management', 'search-history', params],
    queryFn: () => aiApi.listSearchHistory(params),
    staleTime: 2 * 60 * 1000,
  });

  const items = historyData?.items || [];
  const total = historyData?.total || 0;

  const clearMutation = useMutation({
    mutationFn: () => aiApi.clearSearchHistory(),
    onSuccess: (ok) => {
      if (ok) {
        message.success('搜尋歷史已清除');
        setParams(prev => ({ ...prev, page: 1 }));
        queryClient.invalidateQueries({ queryKey: ['ai-management', 'search-history'] });
        queryClient.invalidateQueries({ queryKey: ['ai-management', 'search-stats'] });
      } else {
        message.error('清除搜尋歷史失敗');
      }
    },
    onError: () => {
      message.error('清除搜尋歷史失敗');
    },
  });

  const handleClear = () => clearMutation.mutate();

  const columns: ColumnsType<SearchHistoryItem> = useMemo(() => [
    {
      title: '時間',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (v: string | null) => v ? dayjs(v).format('MM-DD HH:mm:ss') : '-',
    },
    {
      title: '使用者',
      dataIndex: 'user_name',
      key: 'user_name',
      width: 100,
      render: (v: string | null) => v || <Text type="secondary">匿名</Text>,
    },
    {
      title: '查詢內容',
      dataIndex: 'query',
      key: 'query',
      ellipsis: true,
    },
    {
      title: '結果數',
      dataIndex: 'results_count',
      key: 'results_count',
      width: 80,
      sorter: (a, b) => a.results_count - b.results_count,
    },
    {
      title: '來源',
      dataIndex: 'source',
      key: 'source',
      width: 100,
      render: (v: string | null) => {
        const colorMap: Record<string, string> = {
          rule_engine: 'green',
          vector: 'cyan',
          ai: 'blue',
          merged: 'purple',
          fallback: 'default',
        };
        return <Tag color={colorMap[v || ''] || 'default'}>{v || '-'}</Tag>;
      },
    },
    {
      title: '信心度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 80,
      render: (v: number | null) => v !== null && v !== undefined ? `${(v * 100).toFixed(0)}%` : '-',
    },
    {
      title: '延遲',
      dataIndex: 'latency_ms',
      key: 'latency_ms',
      width: 80,
      render: (v: number | null) => v !== null && v !== undefined ? `${v}ms` : '-',
      sorter: (a, b) => (a.latency_ms || 0) - (b.latency_ms || 0),
    },
  ], []);

  return (
    <div>
      {/* 篩選列 */}
      <Space wrap style={{ marginBottom: 16 }}>
        <Input.Search
          placeholder="搜尋查詢內容"
          allowClear
          style={{ width: 200 }}
          onSearch={(v) => setParams(prev => ({ ...prev, keyword: v || undefined, page: 1 }))}
        />
        <DatePicker.RangePicker
          placeholder={['開始日期', '結束日期']}
          onChange={(dates) => {
            setParams(prev => ({
              ...prev,
              date_from: dates?.[0] ? dates[0].format('YYYY-MM-DD') : undefined,
              date_to: dates?.[1] ? dates[1].format('YYYY-MM-DD') : undefined,
              page: 1,
            }));
          }}
          style={{ width: 240 }}
        />
        <Select
          placeholder="來源"
          allowClear
          style={{ width: 140 }}
          onChange={(v) => setParams(prev => ({ ...prev, source: v || undefined, page: 1 }))}
          options={[
            { value: 'rule_engine', label: '規則引擎' },
            { value: 'vector', label: '向量匹配' },
            { value: 'ai', label: 'AI 解析' },
            { value: 'merged', label: '混合' },
            { value: 'fallback', label: '降級' },
          ]}
        />
        <Select
          placeholder="策略"
          allowClear
          style={{ width: 140 }}
          onChange={(v) => setParams(prev => ({ ...prev, search_strategy: v || undefined, page: 1 }))}
          options={[
            { value: 'keyword', label: 'keyword' },
            { value: 'similarity', label: 'similarity' },
            { value: 'hybrid', label: 'hybrid' },
          ]}
        />
        <Popconfirm title="確定要清除所有搜尋歷史？" onConfirm={handleClear}>
          <Button danger icon={<DeleteOutlined />}>清除歷史</Button>
        </Popconfirm>
      </Space>

      <Table
        dataSource={items}
        columns={columns}
        rowKey="id"
        size="small"
        loading={loading}
        pagination={{
          current: params.page,
          pageSize: params.page_size,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 筆`,
          onChange: (page, pageSize) => setParams(prev => ({ ...prev, page, page_size: pageSize })),
        }}
        expandable={{
          expandedRowRender: (record) => (
            <Descriptions size="small" column={2} bordered>
              <Descriptions.Item label="原始查詢" span={2}>{record.query}</Descriptions.Item>
              <Descriptions.Item label="搜尋策略">{record.search_strategy || '-'}</Descriptions.Item>
              <Descriptions.Item label="同義詞擴展">{record.synonym_expanded ? '是' : '否'}</Descriptions.Item>
              <Descriptions.Item label="關聯實體">
                {record.related_entity
                  ? <Tag color="volcano">{record.related_entity === 'dispatch_order' ? '派工單' : record.related_entity === 'project' ? '專案' : record.related_entity}</Tag>
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="結果數量">{record.results_count}</Descriptions.Item>
              {record.parsed_intent && (
                <Descriptions.Item label="解析意圖" span={2}>
                  <pre style={{ fontSize: 12, margin: 0, maxHeight: 200, overflow: 'auto' }}>
                    {JSON.stringify(record.parsed_intent, null, 2)}
                  </pre>
                </Descriptions.Item>
              )}
            </Descriptions>
          ),
        }}
      />
    </div>
  );
};

// ============================================================================
// 主頁面
// ============================================================================
const AIAssistantManagementPage: React.FC = () => {
  const tabItems = useMemo(() => [
    {
      key: 'overview',
      label: (
        <span><BarChartOutlined /> 搜尋總覽</span>
      ),
      children: <OverviewTab />,
    },
    {
      key: 'history',
      label: (
        <span><HistoryOutlined /> 搜尋歷史</span>
      ),
      children: <HistoryTab />,
    },
    {
      key: 'synonyms',
      label: (
        <span><TagsOutlined /> 同義詞管理</span>
      ),
      children: <SynonymManagementContent />,
    },
    {
      key: 'prompts',
      label: (
        <span><RobotOutlined /> Prompt 管理</span>
      ),
      children: <PromptManagementContent />,
    },
  ], []);

  return (
    <div style={{ padding: '0 0 24px' }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <ExperimentOutlined /> AI 助理管理
        </Title>
        <Text type="secondary">搜尋統計分析、歷史記錄查詢、同義詞與 Prompt 版本管理</Text>
      </div>
      <Tabs defaultActiveKey="overview" items={tabItems} />
    </div>
  );
};

export default AIAssistantManagementPage;

/**
 * AI 助理管理頁面
 *
 * Version: 2.0.0
 * Created: 2026-02-09
 * Updated: 2026-02-24 — 新增 Embedding 管理、知識圖譜、AI 服務監控 Tab
 *
 * 統一管理入口，整合搜尋統計、搜尋歷史、同義詞管理、Prompt 管理、
 * Embedding 管線、知識圖譜、AI 服務監控。
 */
import React, { useCallback, useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Empty,
  Input,
  InputNumber,
  message,
  Popconfirm,
  Progress,
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
  ApartmentOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  CloudServerOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  ExperimentOutlined,
  HeartOutlined,
  HistoryOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  RobotOutlined,
  SearchOutlined,
  TagsOutlined,
  ThunderboltOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import type { ColumnsType } from 'antd/es/table';

import { aiApi } from '../api/aiApi';
import type {
  SearchHistoryItem,
  SearchHistoryListRequest,
  DailyTrend,
  TopQuery,
  AIHealthStatus,
  EmbeddingStatsResponse,
  EmbeddingBatchResponse,
} from '../api/aiApi';
import { SynonymManagementContent } from './AISynonymManagementPage';
import { PromptManagementContent } from './AIPromptManagementPage';
import { KnowledgeGraph } from '../components/ai/KnowledgeGraph';

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
// Tab 3+4: SynonymManagementContent / PromptManagementContent (外部匯入)
// ============================================================================

// ============================================================================
// Tab 5: Embedding 管理
// ============================================================================
const EmbeddingTab: React.FC = () => {
  const queryClient = useQueryClient();
  const [batchLimit, setBatchLimit] = useState<number>(100);

  const {
    data: embStats = null,
    isLoading: statsLoading,
    refetch: refetchStats,
  } = useQuery({
    queryKey: ['ai-management', 'embedding-stats'],
    queryFn: () => aiApi.getEmbeddingStats(),
    staleTime: 60 * 1000,
  });

  const batchMutation = useMutation({
    mutationFn: () => aiApi.runEmbeddingBatch({ limit: batchLimit }),
    onSuccess: (result: EmbeddingBatchResponse | null) => {
      if (result?.success) {
        message.success(
          `批次完成：成功 ${result.success_count} 筆、跳過 ${result.skip_count} 筆、` +
          `失敗 ${result.error_count} 筆（耗時 ${result.elapsed_seconds.toFixed(1)}s）`
        );
        refetchStats();
        queryClient.invalidateQueries({ queryKey: ['ai-management', 'embedding-stats'] });
      } else {
        message.error(result?.message || 'Embedding 批次執行失敗');
      }
    },
    onError: () => {
      message.error('Embedding 批次執行失敗');
    },
  });

  if (statsLoading) {
    return (
      <Spin tip="載入 Embedding 統計...">
        <div style={{ height: 200 }} />
      </Spin>
    );
  }

  const pgvectorEnabled = embStats?.pgvector_enabled ?? false;

  return (
    <div>
      {!pgvectorEnabled && (
        <Alert
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          message="pgvector 未啟用"
          description="Embedding 功能需要啟用 pgvector 擴展 (PGVECTOR_ENABLED=true) 及 Ollama 服務。"
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 覆蓋率統計 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="公文總數"
              value={embStats?.total_documents ?? 0}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="已生成 Embedding"
              value={embStats?.with_embedding ?? 0}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="未生成 Embedding"
              value={embStats?.without_embedding ?? 0}
              valueStyle={{ color: embStats?.without_embedding ? '#cf1322' : '#3f8600' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="覆蓋率"
              value={embStats?.coverage_percent ?? 0}
              suffix="%"
              precision={1}
              prefix={<DashboardOutlined />}
              valueStyle={{
                color: (embStats?.coverage_percent ?? 0) >= 80 ? '#3f8600'
                  : (embStats?.coverage_percent ?? 0) >= 50 ? '#d48806' : '#cf1322',
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* 覆蓋率進度條 */}
      <Card size="small" style={{ marginBottom: 24 }}>
        <div style={{ marginBottom: 8 }}>
          <Typography.Text strong>Embedding 覆蓋率</Typography.Text>
        </div>
        <Progress
          percent={embStats?.coverage_percent ?? 0}
          status={
            (embStats?.coverage_percent ?? 0) >= 80 ? 'success'
              : (embStats?.coverage_percent ?? 0) >= 50 ? 'normal' : 'exception'
          }
          format={(p) => `${(p ?? 0).toFixed(1)}%`}
        />
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          {embStats?.with_embedding ?? 0} / {embStats?.total_documents ?? 0} 筆公文已生成向量
        </Typography.Text>
      </Card>

      {/* 批次處理 */}
      <Card
        title="手動批次生成 Embedding"
        size="small"
        extra={
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => refetchStats()}
          >
            重新整理
          </Button>
        }
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Typography.Text>每批處理筆數：</Typography.Text>
            <InputNumber
              min={10}
              max={500}
              step={10}
              value={batchLimit}
              onChange={(v) => setBatchLimit(v || 100)}
              style={{ marginLeft: 8, width: 120 }}
              disabled={!pgvectorEnabled}
            />
          </div>
          <Popconfirm
            title={`確定要執行 Embedding 批次處理？將處理最多 ${batchLimit} 筆公文。`}
            onConfirm={() => batchMutation.mutate()}
            disabled={!pgvectorEnabled}
          >
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              loading={batchMutation.isPending}
              disabled={!pgvectorEnabled || (embStats?.without_embedding ?? 0) === 0}
            >
              {batchMutation.isPending ? '執行中...' : '開始批次處理'}
            </Button>
          </Popconfirm>
          {(embStats?.without_embedding ?? 0) === 0 && pgvectorEnabled && (
            <Alert type="success" message="所有公文皆已生成 Embedding" showIcon />
          )}
        </Space>
      </Card>
    </div>
  );
};

// ============================================================================
// Tab 6: 知識圖譜
// ============================================================================
const KnowledgeGraphTab: React.FC = () => {
  const [inputIds, setInputIds] = useState<string>('');
  const [documentIds, setDocumentIds] = useState<number[]>([]);
  const [autoMode, setAutoMode] = useState(true);
  const [batchLoading, setBatchLoading] = useState(false);

  // 實體提取覆蓋統計
  const {
    data: entityStats = null,
    refetch: refetchEntityStats,
  } = useQuery({
    queryKey: ['ai-management', 'entity-stats'],
    queryFn: () => aiApi.getEntityStats(),
    staleTime: 60 * 1000,
  });

  const handleLoadGraph = useCallback(() => {
    const ids = inputIds
      .split(/[,，\s]+/)
      .map((s) => parseInt(s.trim(), 10))
      .filter((n) => !isNaN(n) && n > 0);

    if (ids.length === 0) {
      message.warning('請輸入至少一個有效的公文 ID');
      return;
    }
    setDocumentIds(ids);
    setAutoMode(false);
  }, [inputIds]);

  const handleLoadRecent = useCallback(() => {
    setDocumentIds([]);
    setInputIds('');
    setAutoMode(true);
  }, []);

  const handleEntityBatch = useCallback(async () => {
    setBatchLoading(true);
    try {
      const result = await aiApi.runEntityBatch({ limit: 50 });
      if (result?.success) {
        message.success(result.message);
      } else {
        message.error(result?.message || '批次提取失敗');
      }
    } catch {
      message.error('批次提取請求失敗');
    } finally {
      setBatchLoading(false);
      refetchEntityStats();
    }
  }, [refetchEntityStats]);

  return (
    <div>
      {/* 實體提取統計 */}
      {entityStats && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={4}>
              <Statistic
                title="實體覆蓋率"
                value={entityStats.coverage_percent}
                suffix="%"
                valueStyle={{ color: entityStats.coverage_percent > 50 ? '#52c41a' : '#fa8c16' }}
              />
            </Col>
            <Col span={3}>
              <Statistic title="已提取公文" value={entityStats.extracted_documents} suffix={`/ ${entityStats.total_documents}`} />
            </Col>
            <Col span={3}>
              <Statistic title="提取實體" value={entityStats.total_entities} />
            </Col>
            <Col span={3}>
              <Statistic title="提取關係" value={entityStats.total_relations} />
            </Col>
            <Col span={7}>
              <div style={{ fontSize: 12, color: '#666' }}>
                <div style={{ marginBottom: 4, fontWeight: 500 }}>實體類型分佈</div>
                {Object.entries(entityStats.entity_type_stats || {}).map(([type, count]) => (
                  <Tag key={type} style={{ marginBottom: 2 }}>
                    {type}: {count}
                  </Tag>
                ))}
                {Object.keys(entityStats.entity_type_stats || {}).length === 0 && (
                  <Typography.Text type="secondary">尚無提取資料</Typography.Text>
                )}
              </div>
            </Col>
            <Col span={4} style={{ display: 'flex', alignItems: 'center' }}>
              <Button
                type="primary"
                size="small"
                loading={batchLoading}
                onClick={handleEntityBatch}
                disabled={entityStats.without_extraction === 0}
              >
                批次提取 (50 筆)
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      {/* 查詢工具列 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap style={{ marginBottom: autoMode ? 0 : 8 }}>
          <Button
            type={autoMode ? 'primary' : 'default'}
            icon={<ClockCircleOutlined />}
            onClick={handleLoadRecent}
          >
            最近公文
          </Button>
          <Typography.Text type="secondary">|</Typography.Text>
          <Input
            placeholder="輸入公文 ID（多筆以逗號分隔）"
            value={inputIds}
            onChange={(e) => setInputIds(e.target.value)}
            onPressEnter={handleLoadGraph}
            style={{ width: 280 }}
          />
          <Button
            type={!autoMode ? 'primary' : 'default'}
            icon={<SearchOutlined />}
            onClick={handleLoadGraph}
            disabled={!inputIds.trim()}
          >
            指定查詢
          </Button>
        </Space>
        {!autoMode && documentIds.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              查詢：{documentIds.map((id) => (
                <Tag key={id} color="blue" style={{ marginRight: 4 }}>ID {id}</Tag>
              ))}
            </Typography.Text>
          </div>
        )}
        {autoMode && (
          <div style={{ marginTop: 8 }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              <ApartmentOutlined /> 自動顯示最近 10 筆公文的關聯圖譜（含 NER 提取實體）
            </Typography.Text>
          </div>
        )}
      </Card>

      {/* 圖譜區域 */}
      <Card size="small" bodyStyle={{ padding: 12 }}>
        <KnowledgeGraph
          documentIds={documentIds}
          height={500}
        />
      </Card>
    </div>
  );
};

// ============================================================================
// Tab 7: AI 服務監控
// ============================================================================
const ServiceMonitorTab: React.FC = () => {
  const {
    data: health = null,
    isLoading: healthLoading,
    refetch: refetchHealth,
  } = useQuery({
    queryKey: ['ai-management', 'health'],
    queryFn: () => aiApi.checkHealth(),
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });

  const {
    data: embStats = null,
    isLoading: embLoading,
  } = useQuery({
    queryKey: ['ai-management', 'embedding-stats'],
    queryFn: () => aiApi.getEmbeddingStats(),
    staleTime: 60 * 1000,
  });

  const {
    data: config = null,
  } = useQuery({
    queryKey: ['ai-management', 'config'],
    queryFn: () => aiApi.getConfig(),
    staleTime: 5 * 60 * 1000,
  });

  const loading = healthLoading || embLoading;

  if (loading) {
    return (
      <Spin tip="檢查 AI 服務狀態...">
        <div style={{ height: 200 }} />
      </Spin>
    );
  }

  const groqOk = health?.groq?.available ?? false;
  const ollamaOk = health?.ollama?.available ?? false;
  const pgvectorOk = embStats?.pgvector_enabled ?? false;
  const rateLimit = health?.rate_limit;

  const StatusIcon: React.FC<{ ok: boolean }> = ({ ok }) =>
    ok
      ? <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 20 }} />
      : <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />;

  return (
    <div>
      {/* 服務健康卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card size="small">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <StatusIcon ok={groqOk} />
              <div>
                <Typography.Text strong>Groq API</Typography.Text>
                <br />
                <Badge
                  status={groqOk ? 'success' : 'error'}
                  text={groqOk ? '正常運作' : '無法連線'}
                />
                <br />
                <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                  {health?.groq?.message || '-'}
                </Typography.Text>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <StatusIcon ok={ollamaOk} />
              <div>
                <Typography.Text strong>Ollama</Typography.Text>
                <br />
                <Badge
                  status={ollamaOk ? 'success' : 'error'}
                  text={ollamaOk ? '正常運作' : '無法連線'}
                />
                <br />
                <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                  {health?.ollama?.message || '-'}
                </Typography.Text>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <StatusIcon ok={pgvectorOk} />
              <div>
                <Typography.Text strong>pgvector</Typography.Text>
                <br />
                <Badge
                  status={pgvectorOk ? 'success' : 'warning'}
                  text={pgvectorOk ? '已啟用' : '未啟用'}
                />
                <br />
                <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                  向量搜尋 {pgvectorOk ? '可用' : '不可用（語意搜尋降級為關鍵字模式）'}
                </Typography.Text>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Rate Limit 監控 */}
      <Card title="Rate Limit 監控" size="small" style={{ marginBottom: 24 }}
        extra={<Button size="small" icon={<ReloadOutlined />} onClick={() => refetchHealth()}>重新整理</Button>}
      >
        {rateLimit ? (
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={8}>
              <Statistic
                title="目前使用量"
                value={rateLimit.current_requests}
                suffix={`/ ${rateLimit.max_requests}`}
                valueStyle={{
                  color: rateLimit.current_requests / rateLimit.max_requests > 0.8
                    ? '#cf1322' : '#3f8600',
                }}
              />
            </Col>
            <Col xs={12} sm={8}>
              <Statistic
                title="使用率"
                value={(rateLimit.current_requests / rateLimit.max_requests * 100)}
                suffix="%"
                precision={1}
              />
            </Col>
            <Col xs={24} sm={8}>
              <Statistic
                title="時間窗口"
                value={rateLimit.window_seconds}
                suffix="秒"
              />
            </Col>
            <Col xs={24}>
              <Progress
                percent={Math.round(rateLimit.current_requests / rateLimit.max_requests * 100)}
                status={
                  rateLimit.current_requests / rateLimit.max_requests > 0.8 ? 'exception'
                    : rateLimit.current_requests / rateLimit.max_requests > 0.5 ? 'normal' : 'success'
                }
              />
            </Col>
          </Row>
        ) : (
          <Empty description="無 Rate Limit 資訊" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>

      {/* Embedding 覆蓋率 */}
      <Card title="Embedding 覆蓋率" size="small" style={{ marginBottom: 24 }}>
        <Row gutter={[16, 16]}>
          <Col xs={8}>
            <Statistic title="已生成" value={embStats?.with_embedding ?? 0} suffix="筆" />
          </Col>
          <Col xs={8}>
            <Statistic title="未生成" value={embStats?.without_embedding ?? 0} suffix="筆" />
          </Col>
          <Col xs={8}>
            <Statistic
              title="覆蓋率"
              value={embStats?.coverage_percent ?? 0}
              suffix="%"
              precision={1}
            />
          </Col>
          <Col xs={24}>
            <Progress
              percent={embStats?.coverage_percent ?? 0}
              status={(embStats?.coverage_percent ?? 0) >= 80 ? 'success' : 'normal'}
              format={(p) => `${(p ?? 0).toFixed(1)}%`}
            />
          </Col>
        </Row>
      </Card>

      {/* 服務配置 */}
      {config && (
        <Card title="AI 服務配置" size="small">
          <Descriptions column={{ xs: 1, sm: 2 }} size="small" bordered>
            <Descriptions.Item label="AI 功能">
              <Badge status={config.enabled ? 'success' : 'error'} text={config.enabled ? '已啟用' : '已停用'} />
            </Descriptions.Item>
            <Descriptions.Item label="Groq 模型">
              {config.providers.groq.model}
            </Descriptions.Item>
            <Descriptions.Item label="Ollama 模型">
              {config.providers.ollama.model}
            </Descriptions.Item>
            <Descriptions.Item label="Ollama URL">
              {config.providers.ollama.url}
            </Descriptions.Item>
            <Descriptions.Item label="Rate Limit">
              {config.rate_limit.max_requests} 次 / {config.rate_limit.window_seconds} 秒
            </Descriptions.Item>
            <Descriptions.Item label="快取">
              {config.cache.enabled ? '已啟用' : '停用'} (摘要 {config.cache.ttl_summary}s / 分類 {config.cache.ttl_classify}s)
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}
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
    {
      key: 'embedding',
      label: (
        <span><DatabaseOutlined /> Embedding 管理</span>
      ),
      children: <EmbeddingTab />,
    },
    {
      key: 'graph',
      label: (
        <span><ApartmentOutlined /> 知識圖譜</span>
      ),
      children: <KnowledgeGraphTab />,
    },
    {
      key: 'monitor',
      label: (
        <span><HeartOutlined /> AI 服務監控</span>
      ),
      children: <ServiceMonitorTab />,
    },
  ], []);

  return (
    <div style={{ padding: '0 0 24px' }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <ExperimentOutlined /> AI 助理管理
        </Title>
        <Text type="secondary">
          搜尋統計分析、歷史記錄查詢、同義詞管理、Prompt 版本管理、Embedding 管線、知識圖譜、AI 服務監控
        </Text>
      </div>
      <Tabs defaultActiveKey="overview" items={tabItems} />
    </div>
  );
};

export default AIAssistantManagementPage;

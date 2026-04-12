/**
 * WikiPage — LLM Wiki 獨立頁面
 *
 * 三個 Tab:
 * 1. Wiki 圖譜 (force-graph 2D)
 * 2. Wiki 頁面瀏覽 (搜尋 + 列表)
 * 3. Wiki 管理 (統計 + 編譯 + Lint)
 *
 * @version 1.0.0
 * @created 2026-04-13
 */

import React, { lazy, Suspense, useState } from 'react';
import {
  Typography, Tabs, Card, Spin, Button, Input, List, Tag, Space,
  Row, Col, Statistic, App, Empty, Descriptions, Result,
} from 'antd';
import {
  DeploymentUnitOutlined, SearchOutlined, SettingOutlined,
  SyncOutlined, FileTextOutlined, BranchesOutlined,
  CheckCircleOutlined, WarningOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';

const WikiGraphTab = lazy(() => import('./knowledgeBase/WikiGraphTab'));

// ── Types ──

interface WikiStats {
  entities: number;
  topics: number;
  sources: number;
  synthesis: number;
  total: number;
}

interface WikiSearchResult {
  path: string;
  title: string;
  type: string;
  score: number;
  snippet: string;
}

interface WikiLintResult {
  total_pages: number;
  page_count: Record<string, number>;
  orphan_pages: string[];
  broken_links: { from: string; to: string }[];
  health: string;
}

// ── Browse Tab ──

const BrowseTab: React.FC = () => {
  const [search, setSearch] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const { data: results, isLoading } = useQuery<WikiSearchResult[]>({
    queryKey: ['wiki-search', searchTerm],
    queryFn: async () => {
      if (!searchTerm) return [];
      const resp = await apiClient.post<{ success: boolean; data: WikiSearchResult[] }>(
        API_ENDPOINTS.WIKI.SEARCH, { query: searchTerm, limit: 20 },
      );
      return resp.data || [];
    },
    enabled: !!searchTerm,
  });

  const { data: stats } = useQuery<WikiStats>({
    queryKey: ['wiki-stats'],
    queryFn: async () => {
      const resp = await apiClient.post<{ success: boolean; data: WikiStats }>(
        API_ENDPOINTS.WIKI.STATS, {},
      );
      return resp.data;
    },
    staleTime: 60_000,
  });

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        {['entities', 'topics', 'sources', 'synthesis'].map((k) => (
          <Col span={6} key={k}>
            <Card size="small">
              <Statistic title={k} value={stats?.[k as keyof WikiStats] ?? 0} prefix={<FileTextOutlined />} />
            </Card>
          </Col>
        ))}
      </Row>

      <Input.Search
        placeholder="搜尋 Wiki 頁面..."
        enterButton={<><SearchOutlined /> 搜尋</>}
        size="large"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        onSearch={(v) => setSearchTerm(v)}
        style={{ marginBottom: 16 }}
        allowClear
      />

      {isLoading && <Spin style={{ display: 'block', margin: '40px auto' }} />}

      {searchTerm && !isLoading && (!results || results.length === 0) && (
        <Empty description={`找不到「${searchTerm}」的相關頁面`} />
      )}

      {results && results.length > 0 && (
        <List
          dataSource={results}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                title={
                  <Space>
                    <Tag color={item.type === 'entities' ? 'blue' : item.type === 'topics' ? 'purple' : 'default'}>
                      {item.type}
                    </Tag>
                    {item.title}
                    <Tag>{item.score} hits</Tag>
                  </Space>
                }
                description={item.snippet || item.path}
              />
            </List.Item>
          )}
        />
      )}

      {!searchTerm && (
        <Result
          icon={<BranchesOutlined style={{ color: '#1890ff' }} />}
          title="LLM Wiki 知識庫"
          subTitle={`共 ${stats?.total ?? 0} 頁 — 輸入關鍵字搜尋編譯好的公文知識`}
        />
      )}
    </div>
  );
};

// ── Admin Tab ──

const AdminTab: React.FC = () => {
  const { message } = App.useApp();
  const qc = useQueryClient();

  const { data: stats } = useQuery<WikiStats>({
    queryKey: ['wiki-stats'],
    queryFn: async () => {
      const resp = await apiClient.post<{ success: boolean; data: WikiStats }>(
        API_ENDPOINTS.WIKI.STATS, {},
      );
      return resp.data;
    },
  });

  const { data: lint } = useQuery<WikiLintResult>({
    queryKey: ['wiki-lint'],
    queryFn: async () => {
      const resp = await apiClient.post<{ success: boolean; data: WikiLintResult }>(
        API_ENDPOINTS.WIKI.LINT, {},
      );
      return resp.data;
    },
  });

  const compileMutation = useMutation({
    mutationFn: async (mode: string) => {
      const resp = await apiClient.post<{ success: boolean; data: Record<string, unknown> }>(
        `${API_ENDPOINTS.WIKI.COMPILE}?mode=${mode}`, {},
      );
      return resp.data;
    },
    onSuccess: (_data, mode) => {
      message.success(`Wiki ${mode} 編譯完成`);
      qc.invalidateQueries({ queryKey: ['wiki-stats'] });
      qc.invalidateQueries({ queryKey: ['wiki-lint'] });
      qc.invalidateQueries({ queryKey: ['wiki-graph'] });
    },
    onError: () => message.error('編譯失敗'),
  });

  const healthColor = lint?.health === 'good' ? '#52c41a' : '#faad14';
  const healthIcon = lint?.health === 'good' ? <CheckCircleOutlined /> : <WarningOutlined />;

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="健康狀態"
              value={lint?.health || 'unknown'}
              prefix={healthIcon}
              valueStyle={{ color: healthColor }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="總頁數" value={lint?.total_pages ?? stats?.total ?? 0} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="孤立 / 斷裂"
              value={`${lint?.orphan_pages?.length ?? 0} / ${lint?.broken_links?.length ?? 0}`}
              valueStyle={{ color: (lint?.orphan_pages?.length || 0) > 5 ? '#faad14' : undefined }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="Wiki 編譯" size="small" style={{ marginBottom: 16 }}>
        <Space>
          <Button
            type="primary"
            icon={<SyncOutlined />}
            loading={compileMutation.isPending}
            onClick={() => compileMutation.mutate('incremental')}
          >
            增量編譯
          </Button>
          <Button
            icon={<SyncOutlined />}
            loading={compileMutation.isPending}
            onClick={() => compileMutation.mutate('full')}
          >
            全量編譯
          </Button>
        </Space>
        <Typography.Text type="secondary" style={{ marginLeft: 16 }}>
          增量: 只重編有新公文的機關/案件 | 全量: 全部重新編譯
        </Typography.Text>
      </Card>

      {lint && (
        <Card title="Lint 詳情" size="small">
          <Descriptions column={2} size="small">
            <Descriptions.Item label="entities">{lint.page_count?.entities ?? 0}</Descriptions.Item>
            <Descriptions.Item label="topics">{lint.page_count?.topics ?? 0}</Descriptions.Item>
            <Descriptions.Item label="sources">{lint.page_count?.sources ?? 0}</Descriptions.Item>
            <Descriptions.Item label="synthesis">{lint.page_count?.synthesis ?? 0}</Descriptions.Item>
          </Descriptions>
          {lint.orphan_pages && lint.orphan_pages.length > 0 && (
            <>
              <Typography.Text type="secondary" style={{ display: 'block', marginTop: 12 }}>
                孤立頁面 (無入站連結):
              </Typography.Text>
              {lint.orphan_pages.slice(0, 10).map((p) => (
                <Tag key={p} style={{ margin: 2 }}>{decodeURIComponent(p.split('/').pop() || p)}</Tag>
              ))}
              {lint.orphan_pages.length > 10 && <Tag>+{lint.orphan_pages.length - 10} more</Tag>}
            </>
          )}
        </Card>
      )}
    </div>
  );
};

// ── Main Page ──

const WikiPage: React.FC = () => {
  return (
    <div style={{ padding: '0 4px' }}>
      <Typography.Title level={4} style={{ marginBottom: 16 }}>
        LLM Wiki
      </Typography.Title>
      <Tabs
        defaultActiveKey="graph"
        items={[
          {
            key: 'graph',
            label: <span><DeploymentUnitOutlined /> Wiki 圖譜</span>,
            children: (
              <Suspense fallback={<Spin style={{ display: 'block', margin: '60px auto' }} />}>
                <WikiGraphTab />
              </Suspense>
            ),
          },
          {
            key: 'browse',
            label: <span><SearchOutlined /> 頁面瀏覽</span>,
            children: <BrowseTab />,
          },
          {
            key: 'admin',
            label: <span><SettingOutlined /> 管理</span>,
            children: <AdminTab />,
          },
        ]}
      />
    </div>
  );
};

export default WikiPage;

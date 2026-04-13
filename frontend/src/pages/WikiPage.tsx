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

// Tabs content panel 需佔滿 flex 剩餘空間 (圖譜全版面)
const TABS_FLEX_CSS = `
.wiki-tabs .ant-tabs-content-holder { flex: 1; overflow: hidden; display: flex; }
.wiki-tabs .ant-tabs-content { flex: 1; overflow: hidden; }
.wiki-tabs .ant-tabs-tabpane-active { height: 100%; overflow: hidden; }
`;
import {
  DeploymentUnitOutlined, SearchOutlined, SettingOutlined,
  SyncOutlined, FileTextOutlined, BranchesOutlined,
  CheckCircleOutlined, WarningOutlined, NodeIndexOutlined,
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

const MarkdownRenderer = lazy(() => import('../components/common/MarkdownRenderer'));

const BrowseTab: React.FC = () => {
  const [search, setSearch] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedPage, setExpandedPage] = useState<string | null>(null);

  // 載入展開頁面的內容
  const { data: pageContent } = useQuery<string>({
    queryKey: ['wiki-page', expandedPage],
    queryFn: async () => {
      if (!expandedPage) return '';
      const resp = await apiClient.post<{ success: boolean; data: { content: string } }>(
        '/wiki/page', null, { params: { page_path: expandedPage } },
      );
      // 去除 frontmatter
      const raw = resp.data?.content || '';
      return raw.replace(/^---[\s\S]*?---\n*/m, '');
    },
    enabled: !!expandedPage,
    staleTime: 60_000,
  });

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
          renderItem={(item) => {
            const isExpanded = expandedPage === item.path;
            return (
            <List.Item
              style={{ cursor: 'pointer', flexDirection: 'column', alignItems: 'stretch' }}
              onClick={() => setExpandedPage(isExpanded ? null : item.path)}
            >
              <List.Item.Meta
                title={
                  <Space>
                    <Tag color={item.type === 'entities' ? 'blue' : item.type === 'topics' ? 'purple' : 'default'}>
                      {item.type}
                    </Tag>
                    {item.title}
                    <Tag>{item.score} hits</Tag>
                    {isExpanded && <Tag color="green">展開中</Tag>}
                  </Space>
                }
                description={isExpanded ? null : (item.snippet || item.path)}
              />
              {isExpanded && (
                <div style={{
                  marginTop: 12, padding: 16, background: '#fafafa',
                  borderRadius: 6, maxHeight: 500, overflow: 'auto', width: '100%',
                }}>
                  {pageContent ? (
                    <Suspense fallback={<Spin size="small" />}>
                      <MarkdownRenderer content={pageContent} />
                    </Suspense>
                  ) : (
                    <Spin size="small" />
                  )}
                </div>
              )}
            </List.Item>
            );
          }}
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

      {/* 排程器狀態 */}
      <SchedulerPanel />
    </div>
  );
};

// ── Scheduler Panel ──

interface SchedulerJob {
  id: string;
  name: string;
  next_run?: string;
  last_run?: string;
  last_status?: string;
  last_duration_ms?: number;
  success_count: number;
  failure_count: number;
  last_error?: string;
}

const SchedulerPanel: React.FC = () => {
  const { data: jobs } = useQuery<SchedulerJob[]>({
    queryKey: ['scheduler-health'],
    queryFn: async () => {
      const resp = await apiClient.post<{
        success: boolean;
        scheduler: { jobs: SchedulerJob[] };
      }>('/health/scheduler', {});
      return resp.scheduler?.jobs || [];
    },
    staleTime: 30_000,
  });

  if (!jobs || jobs.length === 0) return null;

  // 只顯示 wiki 相關 + 月度覆盤
  const wikiJobs = jobs.filter((j) =>
    j.id.includes('wiki') || j.id.includes('arch_review')
  );

  return (
    <Card title={`排程器 (${jobs.length} jobs, 顯示 wiki 相關)`} size="small" style={{ marginTop: 16 }}>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #f0f0f0', textAlign: 'left' }}>
              <th style={{ padding: 4 }}>任務</th>
              <th style={{ padding: 4 }}>上次執行</th>
              <th style={{ padding: 4 }}>狀態</th>
              <th style={{ padding: 4 }}>耗時</th>
              <th style={{ padding: 4 }}>成功/失敗</th>
            </tr>
          </thead>
          <tbody>
            {wikiJobs.map((j) => (
              <tr key={j.id} style={{ borderBottom: '1px solid #f5f5f5' }}>
                <td style={{ padding: 4 }}>{j.name || j.id}</td>
                <td style={{ padding: 4, color: '#888' }}>
                  {j.last_run ? new Date(j.last_run).toLocaleString('zh-TW') : '—'}
                </td>
                <td style={{ padding: 4 }}>
                  <Tag color={j.last_status === 'success' ? 'green' : j.last_status === 'failure' ? 'red' : 'default'}>
                    {j.last_status || 'pending'}
                  </Tag>
                </td>
                <td style={{ padding: 4 }}>{j.last_duration_ms ? `${j.last_duration_ms}ms` : '—'}</td>
                <td style={{ padding: 4 }}>{j.success_count}/{j.failure_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
};

// ── Coverage Tab ──

interface CoverageSummary {
  wiki_total: number;
  kg_total: number;
  exact_match: number;
  fuzzy_match: number;
  wiki_only: number;
  kg_only: number;
  coverage_pct: number;
}

interface CoverageData {
  summary: CoverageSummary;
  exact_matches: { name: string; wiki_type: string; kg_type: string; kg_mentions: number }[];
  kg_only_top: { name: string; type: string; mentions: number }[];
  wiki_only: { name: string; type: string; path: string }[];
}

const CoverageTab: React.FC = () => {
  const { data, isLoading } = useQuery<CoverageData>({
    queryKey: ['wiki-coverage'],
    queryFn: async () => {
      const resp = await apiClient.post<{ success: boolean; data: CoverageData }>(
        API_ENDPOINTS.WIKI.COVERAGE, {},
      );
      return resp.data;
    },
    staleTime: 5 * 60_000,
  });

  if (isLoading) return <Spin style={{ display: 'block', margin: '40px auto' }} />;
  if (!data) return <Empty description="無比對資料" />;

  const s = data.summary;

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}><Card size="small"><Statistic title="Wiki 頁面" value={s.wiki_total} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="KG 實體" value={s.kg_total} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="完全匹配" value={s.exact_match} valueStyle={{ color: '#52c41a' }} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="Wiki 獨有" value={s.wiki_only} valueStyle={{ color: '#1890ff' }} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="KG 獨有" value={s.kg_only} valueStyle={{ color: '#faad14' }} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="覆蓋率" value={s.coverage_pct} suffix="%" /></Card></Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Card title={`KG 獨有 (Top 30) — Wiki 缺少`} size="small" style={{ marginBottom: 16 }}>
            <div style={{ maxHeight: 400, overflow: 'auto' }}>
              {data.kg_only_top.slice(0, 30).map((e) => (
                <div key={e.name} style={{ padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
                  <Tag color={e.type === 'org' ? 'blue' : e.type === 'project' ? 'green' : 'default'}>{e.type}</Tag>
                  {e.name.slice(0, 35)} <Tag>{e.mentions} mentions</Tag>
                </div>
              ))}
            </div>
          </Card>
        </Col>
        <Col span={12}>
          <Card title={`完全匹配 (${s.exact_match} 筆)`} size="small" style={{ marginBottom: 16 }}>
            <div style={{ maxHeight: 400, overflow: 'auto' }}>
              {data.exact_matches.slice(0, 30).map((e) => (
                <div key={e.name} style={{ padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
                  <Tag color="success">match</Tag>
                  {e.name.slice(0, 30)} <Tag>{e.kg_mentions}</Tag>
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

// ── Main Page ──

const WikiPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('graph');
  const isGraphTab = activeTab === 'graph';

  return (
    <div style={{
      // 圖譜 tab: 去除 padding 最大化空間; 其他 tab: 正常 padding
      padding: isGraphTab ? '0' : '0 4px',
      // 外容器佔滿 Layout Content 高度
      height: 'calc(100vh - 88px)', // 64px header + 24px content padding
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* 非圖譜 tab 顯示標題 */}
      {!isGraphTab && (
        <Typography.Title level={4} style={{ marginBottom: 12, padding: '0 4px', flex: '0 0 auto' }}>
          LLM Wiki
        </Typography.Title>
      )}
      <style>{TABS_FLEX_CSS}</style>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        className="wiki-tabs"
        style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
        tabBarStyle={{ margin: 0, flex: '0 0 auto' }}
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
            key: 'coverage',
            label: <span><NodeIndexOutlined /> KG 比對</span>,
            children: <CoverageTab />,
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

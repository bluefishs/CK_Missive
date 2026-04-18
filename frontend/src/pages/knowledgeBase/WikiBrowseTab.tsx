/**
 * Wiki 頁面瀏覽 Tab — 從 WikiPage.tsx 拆分（v1.0 2026-04-18）
 */
import React, { lazy, Suspense, useState } from 'react';
import {
  Card, Spin, Input, List, Tag, Space, Row, Col, Statistic, Empty, Result,
} from 'antd';
import { SearchOutlined, FileTextOutlined, BranchesOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import type { WikiStats, WikiSearchResult } from './wikiTypes';

const MarkdownRenderer = lazy(() => import('../../components/common/MarkdownRenderer'));

const WikiBrowseTab: React.FC = () => {
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

export default WikiBrowseTab;

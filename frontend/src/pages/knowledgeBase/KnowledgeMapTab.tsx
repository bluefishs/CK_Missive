/**
 * KnowledgeMapTab - 知識地圖瀏覽（搜尋 + 樹狀目錄 + Markdown 渲染）
 *
 * 左側：搜尋框 + 分類樹狀目錄（從 docs/knowledge-map/ 掃描）
 * 右側：Markdown 內容渲染（含 Mermaid 圖表支援）
 *
 * @version 1.1.0
 */
import React, { useState, useCallback } from 'react';
import { Tree, Card, Empty, Spin, Typography, Input, List, Tag, Space } from 'antd';
import { FileTextOutlined, FolderOutlined, SearchOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import type { TreeDataNode } from 'antd';

import { knowledgeBaseApi } from '../../api/knowledgeBaseApi';
import type { SectionInfo, KBSearchResult } from '../../api/knowledgeBaseApi';
import { MarkdownRenderer } from '@ck-shared/ui-components';

/** 將 API 回傳的 sections 轉為 antd Tree DataNode */
function buildTreeData(sections: SectionInfo[]): TreeDataNode[] {
  return sections.map((sec) => ({
    key: sec.path,
    title: sec.name,
    icon: <FolderOutlined />,
    children: sec.files.map((f) => ({
      key: f.path,
      title: f.name.replace(/\.md$/, ''),
      icon: <FileTextOutlined />,
      isLeaf: true,
    })),
  }));
}

/** Highlight query text within a string */
function highlightText(text: string, query: string): React.ReactNode {
  if (!query) return text;
  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();
  const idx = lowerText.indexOf(lowerQuery);
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark style={{ backgroundColor: '#ffd666', padding: 0 }}>{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  );
}

export const KnowledgeMapTab: React.FC = () => {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSearch, setActiveSearch] = useState('');

  const { data: treeData, isLoading: treeLoading } = useQuery({
    queryKey: ['knowledge-base', 'tree'],
    queryFn: () => knowledgeBaseApi.fetchTree(),
    staleTime: 5 * 60 * 1000,
  });

  const { data: fileData, isLoading: fileLoading } = useQuery({
    queryKey: ['knowledge-base', 'file', selectedPath],
    queryFn: () => knowledgeBaseApi.fetchFile(selectedPath!),
    enabled: !!selectedPath,
    staleTime: 5 * 60 * 1000,
  });

  const { data: searchData, isLoading: searchLoading } = useQuery({
    queryKey: ['knowledge-base', 'search', activeSearch],
    queryFn: () => knowledgeBaseApi.searchContent(activeSearch),
    enabled: activeSearch.length >= 2,
    staleTime: 30 * 1000,
  });

  const treeNodes = treeData?.sections ? buildTreeData(treeData.sections) : [];

  const handleSelect = (keys: React.Key[]) => {
    const key = keys[0] as string;
    // Only select leaf nodes (files)
    if (key && !treeData?.sections.some((s) => s.path === key)) {
      setSelectedPath(key);
      // Clear search when selecting from tree
      if (activeSearch) {
        setActiveSearch('');
        setSearchQuery('');
      }
    }
  };

  const handleSearch = useCallback((value: string) => {
    const trimmed = value.trim();
    setActiveSearch(trimmed);
  }, []);

  const handleSearchResultClick = useCallback((result: KBSearchResult) => {
    setSelectedPath(result.file_path);
  }, []);

  const isSearchActive = activeSearch.length >= 2;
  const searchResults = searchData?.results ?? [];

  return (
    <div style={{ display: 'flex', gap: 16, height: 'calc(100vh - 260px)' }}>
      {/* Left: Search + Tree */}
      <Card
        size="small"
        title="知識地圖目錄"
        style={{ width: 320, flexShrink: 0, overflow: 'auto' }}
        styles={{ body: { padding: '8px 0' } }}
      >
        <div style={{ padding: '0 12px 8px' }}>
          <Input.Search
            placeholder="搜尋知識庫內容..."
            allowClear
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onSearch={handleSearch}
            enterButton={<SearchOutlined />}
            size="small"
          />
        </div>

        {isSearchActive ? (
          // Search results view
          <div style={{ padding: '0 8px' }}>
            {searchLoading ? (
              <Spin description="搜尋中..."><div style={{ padding: 40 }} /></Spin>
            ) : searchResults.length > 0 ? (
              <>
                <Typography.Text type="secondary" style={{ fontSize: 12, padding: '0 4px' }}>
                  找到 {searchData?.total ?? 0} 筆結果
                  {(searchData?.total ?? 0) > searchResults.length &&
                    `（顯示前 ${searchResults.length} 筆）`}
                </Typography.Text>
                <List
                  size="small"
                  dataSource={searchResults}
                  renderItem={(item) => (
                    <List.Item
                      style={{
                        cursor: 'pointer',
                        padding: '6px 4px',
                        backgroundColor: selectedPath === item.file_path ? '#e6f4ff' : undefined,
                      }}
                      onClick={() => handleSearchResultClick(item)}
                    >
                      <div style={{ width: '100%', overflow: 'hidden' }}>
                        <Space size={4}>
                          <FileTextOutlined style={{ color: '#1677ff' }} />
                          <Typography.Text strong ellipsis style={{ maxWidth: 200 }}>
                            {item.filename.replace(/\.md$/, '')}
                          </Typography.Text>
                          <Tag color="blue" style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px' }}>
                            L{item.line_number}
                          </Tag>
                        </Space>
                        <Typography.Paragraph
                          type="secondary"
                          ellipsis={{ rows: 2 }}
                          style={{ fontSize: 12, margin: '4px 0 0', whiteSpace: 'pre-wrap' }}
                        >
                          {highlightText(
                            item.excerpt.split('\n').find((l) => l.toLowerCase().includes(activeSearch.toLowerCase())) ?? item.excerpt.split('\n')[0] ?? '',
                            activeSearch,
                          )}
                        </Typography.Paragraph>
                      </div>
                    </List.Item>
                  )}
                />
              </>
            ) : (
              <Empty description="無搜尋結果" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </div>
        ) : (
          // Normal tree view
          treeLoading ? (
            <Spin description="載入中..."><div style={{ padding: 40 }} /></Spin>
          ) : (
            <Tree
              showIcon
              treeData={treeNodes}
              selectedKeys={selectedPath ? [selectedPath] : []}
              onSelect={handleSelect}
              defaultExpandAll
              style={{ padding: '0 8px' }}
            />
          )
        )}
      </Card>

      {/* Right: Content */}
      <Card
        size="small"
        title={fileData?.filename?.replace(/\.md$/, '') || '選擇文件'}
        style={{ flex: 1, overflow: 'auto' }}
      >
        {fileLoading ? (
          <Spin description="載入中..."><div style={{ padding: 40 }} /></Spin>
        ) : fileData?.content ? (
          <MarkdownRenderer content={fileData.content} />
        ) : (
          <Empty description={<Typography.Text type="secondary">從左側選擇一份文件開始瀏覽</Typography.Text>} />
        )}
      </Card>
    </div>
  );
};

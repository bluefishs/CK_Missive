/**
 * KnowledgeMapTab - 知識地圖瀏覽（樹狀目錄 + Markdown 渲染）
 *
 * 左側：分類樹狀目錄（從 docs/knowledge-map/ 掃描）
 * 右側：Markdown 內容渲染（含 Mermaid 圖表支援）
 *
 * @version 1.0.0
 */
import React, { useState } from 'react';
import { Tree, Card, Empty, Spin, Typography } from 'antd';
import { FileTextOutlined, FolderOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import type { DataNode } from 'antd/es/tree';

import { knowledgeBaseApi } from '../../api/knowledgeBaseApi';
import type { SectionInfo } from '../../api/knowledgeBaseApi';
import { MarkdownRenderer } from '../../components/common/MarkdownRenderer';

/** 將 API 回傳的 sections 轉為 antd Tree DataNode */
function buildTreeData(sections: SectionInfo[]): DataNode[] {
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

export const KnowledgeMapTab: React.FC = () => {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);

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

  const treeNodes = treeData?.sections ? buildTreeData(treeData.sections) : [];

  const handleSelect = (keys: React.Key[]) => {
    const key = keys[0] as string;
    // Only select leaf nodes (files)
    if (key && !treeData?.sections.some((s) => s.path === key)) {
      setSelectedPath(key);
    }
  };

  return (
    <div style={{ display: 'flex', gap: 16, height: 'calc(100vh - 260px)' }}>
      {/* Left: Tree */}
      <Card
        size="small"
        title="知識地圖目錄"
        style={{ width: 280, flexShrink: 0, overflow: 'auto' }}
        bodyStyle={{ padding: '8px 0' }}
      >
        {treeLoading ? (
          <Spin tip="載入中..."><div style={{ padding: 40 }} /></Spin>
        ) : (
          <Tree
            showIcon
            treeData={treeNodes}
            selectedKeys={selectedPath ? [selectedPath] : []}
            onSelect={handleSelect}
            defaultExpandAll
            style={{ padding: '0 8px' }}
          />
        )}
      </Card>

      {/* Right: Content */}
      <Card
        size="small"
        title={fileData?.filename?.replace(/\.md$/, '') || '選擇文件'}
        style={{ flex: 1, overflow: 'auto' }}
      >
        {fileLoading ? (
          <Spin tip="載入中..."><div style={{ padding: 40 }} /></Spin>
        ) : fileData?.content ? (
          <MarkdownRenderer content={fileData.content} />
        ) : (
          <Empty description={<Typography.Text type="secondary">從左側選擇一份文件開始瀏覽</Typography.Text>} />
        )}
      </Card>
    </div>
  );
};

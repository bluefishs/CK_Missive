/**
 * DiagramsTab - 架構圖 Mermaid 渲染
 *
 * Segmented 切換 + Markdown/Mermaid 混合渲染
 *
 * @version 1.0.0
 */
import React, { useState, useEffect, useMemo } from 'react';
import { Card, Segmented, Empty, Spin, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';

import { knowledgeBaseApi } from '../../api/knowledgeBaseApi';
import type { DiagramInfo } from '../../api/knowledgeBaseApi';
import { MarkdownRenderer } from '@ck-shared/ui-components';

export const DiagramsTab: React.FC = () => {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);

  const { data: diagramsData, isLoading: listLoading } = useQuery({
    queryKey: ['knowledge-base', 'diagrams-list'],
    queryFn: () => knowledgeBaseApi.fetchDiagramsList(),
    staleTime: 5 * 60 * 1000,
  });

  const { data: fileData, isLoading: fileLoading } = useQuery({
    queryKey: ['knowledge-base', 'file', selectedPath],
    queryFn: () => knowledgeBaseApi.fetchFile(selectedPath!),
    enabled: !!selectedPath,
    staleTime: 5 * 60 * 1000,
  });

  const items = useMemo(() => diagramsData?.items ?? [], [diagramsData?.items]);

  // Auto-select first diagram
  useEffect(() => {
    const first = items[0];
    if (first && !selectedPath) {
      setSelectedPath(first.path);
    }
  }, [items, selectedPath]);

  const segmentOptions = items.map((d: DiagramInfo) => ({
    label: d.title || d.name.replace(/\.md$/, ''),
    value: d.path,
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, height: 'calc(100vh - 260px)' }}>
      {/* Diagram Selector */}
      <Card size="small" styles={{ body: { padding: '12px 16px' } }}>
        {listLoading ? (
          <Spin description="載入中..."><div style={{ padding: 20 }} /></Spin>
        ) : items.length > 0 ? (
          <Segmented
            options={segmentOptions}
            value={selectedPath ?? undefined}
            onChange={(val) => setSelectedPath(val as string)}
            block
          />
        ) : (
          <Typography.Text type="secondary">尚無架構圖</Typography.Text>
        )}
      </Card>

      {/* Diagram Content */}
      <Card size="small" style={{ flex: 1, overflow: 'auto' }}>
        {fileLoading ? (
          <Spin description="載入圖表中..."><div style={{ padding: 40 }} /></Spin>
        ) : fileData?.content ? (
          <MarkdownRenderer content={fileData.content} />
        ) : (
          <Empty description={<Typography.Text type="secondary">選擇架構圖查看</Typography.Text>} />
        )}
      </Card>
    </div>
  );
};

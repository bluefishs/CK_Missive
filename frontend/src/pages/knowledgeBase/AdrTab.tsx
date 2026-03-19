/**
 * AdrTab - 架構決策記錄 (ADR) 瀏覽
 *
 * 上方：ADR 列表（表格 + 狀態標籤）
 * 下方：選中 ADR 的 Markdown 詳情
 *
 * @version 1.0.0
 */
import React, { useState } from 'react';
import { Table, Tag, Card, Empty, Spin, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import type { ColumnsType } from 'antd/es/table';

import { knowledgeBaseApi } from '../../api/knowledgeBaseApi';
import type { AdrInfo } from '../../api/knowledgeBaseApi';
import { MarkdownRenderer } from '@ck-shared/ui-components';

const STATUS_COLORS: Record<string, string> = {
  accepted: 'green',
  proposed: 'blue',
  deprecated: 'orange',
  superseded: 'red',
};

const columns: ColumnsType<AdrInfo> = [
  {
    title: '編號',
    dataIndex: 'number',
    width: 80,
    sorter: (a, b) => a.number.localeCompare(b.number),
  },
  {
    title: '標題',
    dataIndex: 'title',
    ellipsis: true,
  },
  {
    title: '狀態',
    dataIndex: 'status',
    width: 100,
    render: (status: string) => (
      <Tag color={STATUS_COLORS[status?.toLowerCase()] || 'default'}>
        {status || '未知'}
      </Tag>
    ),
    filters: [
      { text: 'Accepted', value: 'accepted' },
      { text: 'Proposed', value: 'proposed' },
      { text: 'Deprecated', value: 'deprecated' },
    ],
    onFilter: (value, record) => record.status?.toLowerCase() === value,
  },
  {
    title: '日期',
    dataIndex: 'date',
    width: 120,
    sorter: (a, b) => (a.date || '').localeCompare(b.date || ''),
  },
];

export const AdrTab: React.FC = () => {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);

  const { data: adrData, isLoading: listLoading } = useQuery({
    queryKey: ['knowledge-base', 'adr-list'],
    queryFn: () => knowledgeBaseApi.fetchAdrList(),
    staleTime: 5 * 60 * 1000,
  });

  const { data: fileData, isLoading: fileLoading } = useQuery({
    queryKey: ['knowledge-base', 'file', selectedPath],
    queryFn: () => knowledgeBaseApi.fetchFile(selectedPath!),
    enabled: !!selectedPath,
    staleTime: 5 * 60 * 1000,
  });

  const items = adrData?.items ?? [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, height: 'calc(100vh - 260px)' }}>
      {/* Top: ADR Table */}
      <Card size="small" title={`架構決策記錄 (${items.length} 筆)`} style={{ flexShrink: 0 }}>
        {listLoading ? (
          <Spin description="載入中..."><div style={{ padding: 40 }} /></Spin>
        ) : (
          <Table<AdrInfo>
            columns={columns}
            dataSource={items}
            rowKey="number"
            size="small"
            pagination={false}
            scroll={{ y: 200 }}
            onRow={(record) => ({
              onClick: () => setSelectedPath(record.path),
              style: {
                cursor: 'pointer',
                background: selectedPath === record.path ? '#e6f4ff' : undefined,
              },
            })}
          />
        )}
      </Card>

      {/* Bottom: ADR Detail */}
      <Card size="small" title={fileData?.filename?.replace(/\.md$/, '') || 'ADR 詳情'} style={{ flex: 1, overflow: 'auto' }}>
        {fileLoading ? (
          <Spin description="載入中..."><div style={{ padding: 40 }} /></Spin>
        ) : fileData?.content ? (
          <MarkdownRenderer content={fileData.content} />
        ) : (
          <Empty description={<Typography.Text type="secondary">點擊上方列表中的 ADR 查看詳情</Typography.Text>} />
        )}
      </Card>
    </div>
  );
};

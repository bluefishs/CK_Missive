/**
 * HistoryTab - Search history with filters
 *
 * Extracted from AIAssistantManagementPage.tsx
 */
import React, { useMemo, useState } from 'react';
import {
  Button,
  DatePicker,
  Descriptions,
  Input,
  message,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import type { ColumnsType } from 'antd/es/table';

import { aiApi } from '../../../api/aiApi';
import type { SearchHistoryItem, SearchHistoryListRequest } from '../../../types/ai';

const { Text } = Typography;

export const HistoryTab: React.FC = () => {
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

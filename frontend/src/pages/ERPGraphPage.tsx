/**
 * ERP 財務圖譜頁面 (KG-7)
 *
 * 展示 ERP 實體 (報價/費用/資產/廠商) 在知識圖譜中的分布、
 * 跨圖橋接關係、案件全流程追蹤。
 *
 * @version 1.0.0
 * @created 2026-04-08
 */

import React, { useState } from 'react';
import {
  Typography, Tabs, Card, Row, Col, Statistic, Table, Tag, Input,
  Button, Space, Alert, message,
} from 'antd';
import {
  DollarOutlined, SyncOutlined, SearchOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { createTabItem } from '../components/common/DetailPage/utils';
import { useAuthGuard } from '../hooks/utility/useAuthGuard';

const { Title, Text } = Typography;

// ── Types ──

interface ErpGraphEntity {
  name: string;
  type: string;
  detail: string;
  case_code?: string;
}

interface ErpGraphStats {
  total_entities: number;
  by_type: Record<string, number>;
}

// ── Stats Overview ──

const StatsOverview: React.FC = () => {
  const { data, isLoading } = useQuery<{ data: ErpGraphStats }>({
    queryKey: ['erp-graph-stats'],
    queryFn: async () => {
      // Count by scanning ERP entities
      const erpRes = await apiClient.post('/api/ai/graph/entity/search', {
        query: '', entity_types: ['erp_quotation', 'erp_vendor', 'erp_expense', 'erp_asset'],
        limit: 200,
      }).catch(() => ({ entities: [] })) as { entities: Array<{ entity_type: string }> };
      const entities = erpRes?.entities || [];
      const byType: Record<string, number> = {};
      entities.forEach((e: { entity_type: string }) => {
        byType[e.entity_type] = (byType[e.entity_type] || 0) + 1;
      });
      return { data: { total_entities: entities.length, by_type: byType } };
    },
    staleTime: 5 * 60_000,
  });

  const stats = data?.data;
  const typeLabels: Record<string, string> = {
    erp_quotation: '報價案件', erp_vendor: '廠商', erp_expense: '費用',
    erp_asset: '資產', erp_invoice: '開票', erp_billing: '請款',
  };

  return (
    <Row gutter={[16, 16]}>
      <Col xs={12} sm={6}>
        <Card size="small">
          <Statistic
            title="ERP 實體總數" value={stats?.total_entities ?? 0}
            prefix={<DollarOutlined />} loading={isLoading}
          />
        </Card>
      </Col>
      {Object.entries(stats?.by_type ?? {}).map(([type, count]) => (
        <Col xs={12} sm={6} key={type}>
          <Card size="small">
            <Statistic
              title={typeLabels[type] || type} value={count}
              loading={isLoading}
            />
          </Card>
        </Col>
      ))}
    </Row>
  );
};

// ── Entity Search Tab ──

const EntitySearchTab: React.FC = () => {
  const [query, setQuery] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const { data, isLoading } = useQuery<{ results: ErpGraphEntity[]; count: number }>({
    queryKey: ['erp-graph-search', searchQuery],
    queryFn: () => apiClient.post<{ results?: Array<{ name: string; entity_type: string; description: string }>; total?: number }>('/api/ai/graph/unified-search', {
      query: searchQuery || '案', include_kg: false, include_code: false,
      include_db: false, include_erp: true, include_tender: false, limit_per_graph: 20,
    }).then((res) => ({
      results: (res.results || []).map((r) => ({
        name: r.name, type: r.entity_type, detail: r.description, case_code: '',
      })),
      count: res.total || 0,
    })),
    staleTime: 30_000,
    enabled: true,
  });

  const typeColors: Record<string, string> = {
    erp_quotation: 'blue', erp_vendor: 'green', erp_expense: 'orange',
    erp_asset: 'purple', erp_invoice: 'cyan', erp_billing: 'magenta',
  };

  const columns = [
    { title: '名稱', dataIndex: 'name', key: 'name', width: 250 },
    {
      title: '類型', dataIndex: 'type', key: 'type', width: 120,
      render: (t: string) => <Tag color={typeColors[t] || 'default'}>{t.replace('erp_', '')}</Tag>,
    },
    { title: '說明', dataIndex: 'detail', key: 'detail', ellipsis: true },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Input
          placeholder="搜尋 ERP 實體 (案件名稱/廠商/發票號碼)"
          prefix={<SearchOutlined />}
          value={query}
          onChange={e => setQuery(e.target.value)}
          onPressEnter={() => setSearchQuery(query)}
          style={{ width: 400 }}
        />
        <Button type="primary" onClick={() => setSearchQuery(query)}>搜尋</Button>
      </Space>
      <Table
        dataSource={data?.results || []}
        columns={columns}
        loading={isLoading}
        rowKey={(r, i) => `${r.name}-${i}`}
        size="small"
        pagination={{ pageSize: 15 }}
      />
    </div>
  );
};

// ── Ingest Admin Tab ──

const IngestAdminTab: React.FC = () => {
  const ingestMutation = useMutation({
    mutationFn: () => apiClient.post<{ message: string; entities: number; relations: number; cross_graph_bridges: number; duration_ms: number }>('/api/ai/graph/admin/erp-ingest', {}),
    onSuccess: (data) => {
      message.success(data.message || 'ERP 入圖完成');
    },
    onError: () => {
      message.error('ERP 入圖失敗');
    },
  });

  return (
    <Card>
      <Title level={5}><ToolOutlined /> ERP 圖譜管理</Title>
      <Text type="secondary">
        手動觸發 ERP 資料入圖。系統每日 03:30 自動執行。
      </Text>
      <div style={{ marginTop: 16 }}>
        <Button
          type="primary"
          icon={<SyncOutlined spin={ingestMutation.isPending} />}
          onClick={() => ingestMutation.mutate()}
          loading={ingestMutation.isPending}
        >
          立即入圖
        </Button>
        {ingestMutation.data && (
          <Alert
            type="success"
            showIcon
            style={{ marginTop: 12 }}
            message={ingestMutation.data.message}
            description={`實體: ${ingestMutation.data.entities} | 關係: ${ingestMutation.data.relations} | 橋接: ${ingestMutation.data.cross_graph_bridges} | ${ingestMutation.data.duration_ms}ms`}
          />
        )}
      </div>
    </Card>
  );
};

// ── Main Page ──

const ERPGraphPage: React.FC = () => {
  useAuthGuard();
  const [activeTab, setActiveTab] = useState('overview');

  const tabItems = [
    createTabItem('overview', { icon: <DollarOutlined />, text: '總覽' },
      <StatsOverview />
    ),
    createTabItem('search', { icon: <SearchOutlined />, text: '實體搜尋' },
      <EntitySearchTab />
    ),
    createTabItem('admin', { icon: <ToolOutlined />, text: '入圖管理' },
      <IngestAdminTab />
    ),
  ];

  return (
    <div style={{ padding: '0 0 24px' }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <DollarOutlined /> ERP 財務圖譜
        </Title>
        <Text type="secondary">
          報價案件、費用報銷、資產、廠商在知識圖譜中的分布與跨圖關聯
        </Text>
      </div>
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
    </div>
  );
};

export default ERPGraphPage;

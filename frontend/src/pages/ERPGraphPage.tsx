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

// ── Case Flow Tab ──

interface FlowSummary {
  quotation_amount: number;
  billed_amount: number;
  vendor_paid: number;
  expenses_total: number;
  has_tender: boolean;
  has_pm_case: boolean;
  invoice_count: number;
  billing_count: number;
  stage: string;
}

interface CaseFlowData {
  case_code: string;
  tender: { title: string; unit_name: string; budget: number } | null;
  pm_case: { name: string; status: string; project_code: string } | null;
  quotation: { case_name: string; total_price: number; status: string } | null;
  invoices: Array<{ invoice_number: string; amount: number; status: string }>;
  billings: Array<{ billing_code: string; billing_amount: number; payment_status: string; billing_period: string }>;
  vendor_payables: Array<{ vendor_name: string; payable_amount: number; payment_status: string }>;
  expenses: Array<{ inv_num: string; amount: number; category: string; status: string }>;
  flow_summary: FlowSummary;
}

const stageLabels: Record<string, { text: string; color: string }> = {
  tender_found: { text: '標案階段', color: 'purple' },
  case_created: { text: '已建案', color: 'blue' },
  quoted: { text: '已報價', color: 'cyan' },
  invoiced: { text: '已開票', color: 'green' },
  billing: { text: '請款中', color: 'orange' },
  unknown: { text: '未知', color: 'default' },
};

const CaseFlowTab: React.FC = () => {
  const [caseCode, setCaseCode] = useState('');
  const [searchCode, setSearchCode] = useState('');

  const { data, isLoading, isError } = useQuery<{ data: CaseFlowData }>({
    queryKey: ['case-flow', searchCode],
    queryFn: () => apiClient.post<{ data: CaseFlowData }>('/api/ai/graph/case-flow', { case_code: searchCode }),
    enabled: !!searchCode,
    staleTime: 60_000,
  });

  const flow = data?.data;
  const summary = flow?.flow_summary;
  const stageInfo = stageLabels[summary?.stage || 'unknown'] ?? stageLabels['unknown'];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Input
          placeholder="輸入案件代碼 (case_code)"
          prefix={<SearchOutlined />}
          value={caseCode}
          onChange={e => setCaseCode(e.target.value)}
          onPressEnter={() => setSearchCode(caseCode)}
          style={{ width: 350 }}
        />
        <Button type="primary" onClick={() => setSearchCode(caseCode)} loading={isLoading}>
          查詢全流程
        </Button>
      </Space>

      {isError && <Alert type="error" message="查詢失敗" showIcon style={{ marginBottom: 12 }} />}

      {flow && summary && (
        <>
          <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
            <Col xs={8} sm={4}>
              <Card size="small"><Statistic title="階段" valueRender={() => <Tag color={stageInfo?.color ?? 'default'}>{stageInfo?.text ?? '未知'}</Tag>} value=" " /></Card>
            </Col>
            <Col xs={8} sm={4}>
              <Card size="small"><Statistic title="報價金額" value={summary.quotation_amount} precision={0} prefix="$" /></Card>
            </Col>
            <Col xs={8} sm={4}>
              <Card size="small"><Statistic title="已請款" value={summary.billed_amount} precision={0} prefix="$" /></Card>
            </Col>
            <Col xs={8} sm={4}>
              <Card size="small"><Statistic title="廠商已付" value={summary.vendor_paid} precision={0} prefix="$" /></Card>
            </Col>
            <Col xs={8} sm={4}>
              <Card size="small"><Statistic title="費用支出" value={summary.expenses_total} precision={0} prefix="$" /></Card>
            </Col>
            <Col xs={8} sm={4}>
              <Card size="small"><Statistic title="開票/請款" value={`${summary.invoice_count}/${summary.billing_count}`} /></Card>
            </Col>
          </Row>

          {/* Flow Steps */}
          <Card size="small" title="業務鏈路">
            <Space direction="vertical" style={{ width: '100%' }}>
              {flow.tender && (
                <Tag color="purple">標案: {flow.tender.title} ({flow.tender.unit_name})</Tag>
              )}
              {flow.pm_case && (
                <Tag color="blue">專案: {flow.pm_case.name} [{flow.pm_case.status}]</Tag>
              )}
              {flow.quotation && (
                <Tag color="cyan">報價: {flow.quotation.case_name} (${flow.quotation.total_price?.toLocaleString()})</Tag>
              )}
              {flow.billings.map((b, i) => (
                <Tag color="orange" key={i}>{b.billing_period}: ${b.billing_amount?.toLocaleString()} [{b.payment_status}]</Tag>
              ))}
              {flow.vendor_payables.map((v, i) => (
                <Tag color="green" key={i}>應付 {v.vendor_name}: ${v.payable_amount?.toLocaleString()} [{v.payment_status}]</Tag>
              ))}
              {flow.expenses.length > 0 && (
                <Tag color="gold">費用 {flow.expenses.length} 筆 (${summary.expenses_total?.toLocaleString()})</Tag>
              )}
            </Space>
          </Card>
        </>
      )}
    </div>
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
    createTabItem('flow', { icon: <DollarOutlined />, text: '案件全流程' },
      <CaseFlowTab />
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

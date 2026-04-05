/**
 * 標案底價分析頁面
 *
 * 兩 Tab: 單一標案分析 / 價格趨勢
 * 底價/預算/決標金額差異率、決標品項明細、分布圖表。
 */
import React, { useState } from 'react';
import {
  Card, Tabs, Form, Input, Button, Descriptions, Table, Row, Col,
  Statistic, Spin, Empty, Typography, Tag,
} from 'antd';
import {
  DollarOutlined, BarChartOutlined, SearchOutlined, FundOutlined,
} from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { useMutation } from '@tanstack/react-query';
import apiClient from '../api/client';
import { TENDER_ENDPOINTS } from '../api/endpoints';
import type { TenderPriceAnalysis, TenderPriceTrends, TenderAwardItem } from '../types/tender';

const { Title, Text } = Typography;

/* ─── helpers ─── */
const fmtMoney = (v: number | null | undefined) =>
  v != null ? `NT$ ${v.toLocaleString()}` : '-';

const pctTag = (v: number | null | undefined) => {
  if (v == null) return <Tag>N/A</Tag>;
  const color = v > 0 ? 'red' : v < 0 ? 'green' : 'default';
  return <Tag color={color}>{v > 0 ? '+' : ''}{v.toFixed(2)}%</Tag>;
};

/* ─── Tab 1: 單一標案分析 ─── */
const SingleAnalysisTab: React.FC = () => {
  const [form] = Form.useForm();
  const { mutate, data, isPending } = useMutation<TenderPriceAnalysis, Error, { unit_id: string; job_number: string }>({
    mutationFn: async (params) => {
      const res = await apiClient.post<{ data: TenderPriceAnalysis }>(
        TENDER_ENDPOINTS.ANALYTICS_PRICE_ANALYSIS, params,
      );
      return res.data;
    },
  });

  const handleAnalyze = () => {
    form.validateFields().then((values) => mutate(values));
  };

  const awardCols = [
    { title: '品項', dataIndex: 'item_no', key: 'item_no', width: 80 },
    { title: '得標廠商', dataIndex: 'winner', key: 'winner', render: (v: string | null) => v || '-' },
    { title: '金額', dataIndex: 'amount', key: 'amount', render: (v: number | null) => fmtMoney(v) },
  ];

  return (
    <Spin spinning={isPending}>
      <Form form={form} layout="inline" style={{ marginBottom: 24 }}>
        <Form.Item name="unit_id" label="機關代碼" rules={[{ required: true, message: '請輸入機關代碼' }]}>
          <Input placeholder="e.g. 3.76.50" />
        </Form.Item>
        <Form.Item name="job_number" label="標案編號" rules={[{ required: true, message: '請輸入標案編號' }]}>
          <Input placeholder="e.g. 1140101" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" icon={<SearchOutlined />} onClick={handleAnalyze}>分析</Button>
        </Form.Item>
      </Form>

      {!data && !isPending && <Empty description="輸入標案資訊後點擊分析" />}

      {data && (
        <>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Title level={5} style={{ margin: 0 }}>{data.tender.title}</Title>
            <Text type="secondary">{data.tender.unit_name} ({data.tender.unit_id})</Text>
          </Card>

          <Descriptions bordered column={{ xs: 1, sm: 2, md: 3 }} size="small" style={{ marginBottom: 16 }}>
            <Descriptions.Item label="預算金額">{fmtMoney(data.prices.budget)}</Descriptions.Item>
            <Descriptions.Item label="底價">{fmtMoney(data.prices.floor_price)}</Descriptions.Item>
            <Descriptions.Item label="決標金額">{fmtMoney(data.prices.award_amount)}</Descriptions.Item>
            <Descriptions.Item label="決標日期">{data.prices.award_date || '-'}</Descriptions.Item>
            <Descriptions.Item label="預算→決標差異">{pctTag(data.analysis.budget_award_variance_pct)}</Descriptions.Item>
            <Descriptions.Item label="底價→決標差異">{pctTag(data.analysis.floor_award_variance_pct)}</Descriptions.Item>
            <Descriptions.Item label="預算→底價差異">{pctTag(data.analysis.budget_floor_variance_pct)}</Descriptions.Item>
            <Descriptions.Item label="節省率">{pctTag(data.analysis.savings_rate_pct)}</Descriptions.Item>
          </Descriptions>

          {data.award_items.length > 0 && (
            <Table<TenderAwardItem>
              dataSource={data.award_items}
              columns={awardCols}
              rowKey="item_no"
              size="small"
              pagination={false}
            />
          )}
        </>
      )}
    </Spin>
  );
};

/* ─── Tab 2: 價格趨勢 ─── */
const PriceTrendsTab: React.FC = () => {
  const [form] = Form.useForm();
  const { mutate, data, isPending } = useMutation<TenderPriceTrends, Error, { query: string; pages?: number }>({
    mutationFn: async (params) => {
      const res = await apiClient.post<{ data: TenderPriceTrends }>(
        TENDER_ENDPOINTS.ANALYTICS_PRICE_TRENDS, params,
      );
      return res.data;
    },
  });

  const handleSearch = () => {
    form.validateFields().then((values) => mutate({ query: values.query, pages: 3 }));
  };

  const entryCols = [
    { title: '標案名稱', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
    { title: '機關', dataIndex: 'unit_name', key: 'unit_name', width: 160, ellipsis: true },
    { title: '預算', dataIndex: 'budget', key: 'budget', width: 130, render: fmtMoney },
    { title: '底價', dataIndex: 'floor_price', key: 'floor_price', width: 130, render: fmtMoney },
    { title: '決標', dataIndex: 'award_amount', key: 'award_amount', width: 130, render: fmtMoney },
  ];

  return (
    <Spin spinning={isPending}>
      <Form form={form} layout="inline" style={{ marginBottom: 24 }}>
        <Form.Item name="query" label="關鍵字" rules={[{ required: true, message: '請輸入搜尋關鍵字' }]}>
          <Input placeholder="e.g. 測量、道路養護" style={{ width: 260 }} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>查詢趨勢</Button>
        </Form.Item>
      </Form>

      {!data && !isPending && <Empty description="輸入關鍵字查詢價格趨勢" />}

      {data && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col xs={12} sm={6}>
              <Card size="small"><Statistic title="樣本數" value={data.samples} suffix={`/ ${data.total}`} /></Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small"><Statistic title="平均預算" value={data.stats.budget.avg ?? 0} prefix="NT$" precision={0} /></Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small"><Statistic title="平均底價" value={data.stats.floor_price.avg ?? 0} prefix="NT$" precision={0} /></Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small"><Statistic title="平均決標" value={data.stats.award_amount.avg ?? 0} prefix="NT$" precision={0} /></Card>
            </Col>
          </Row>

          {data.stats.award_rate_pct != null && (
            <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
              決標率: <Tag color="blue">{data.stats.award_rate_pct.toFixed(1)}%</Tag>
            </Text>
          )}

          {data.distribution.length > 0 && (
            <Card title="金額分布" size="small" style={{ marginBottom: 16 }}>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={data.distribution}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="range" fontSize={12} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#1677ff" name="標案數" />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}

          <Table
            dataSource={data.entries}
            columns={entryCols}
            rowKey={(r, i) => `${r.title}-${i}`}
            size="small"
            pagination={{ pageSize: 10 }}
            scroll={{ x: 800 }}
          />
        </>
      )}
    </Spin>
  );
};

/* ─── Main Page ─── */
const TenderPriceAnalysisPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('single');

  const tabItems = [
    {
      key: 'single',
      label: <><DollarOutlined /> 單一標案分析</>,
      children: <SingleAnalysisTab />,
    },
    {
      key: 'trends',
      label: <><FundOutlined /> 價格趨勢</>,
      children: <PriceTrendsTab />,
    },
  ];

  return (
    <ResponsiveContent>
      <Card
        title={<><BarChartOutlined /> 標案底價分析</>}
        style={{ marginBottom: 16 }}
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>
    </ResponsiveContent>
  );
};

export default TenderPriceAnalysisPage;

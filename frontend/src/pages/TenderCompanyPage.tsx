/**
 * 標案廠商歷史頁面
 *
 * 顯示公司歷年投標/得標紀錄統計。
 * 預設查詢「乾坤測繪」，可搜尋其他公司。
 * 參考 ezbid.tw/vendor/ 風格。
 *
 * @version 1.0.0
 */
import React, { useState, useMemo, useEffect } from 'react';
import {
  Card, Input, Table, Tag, Typography, Row, Col, Statistic,
  App, Progress, Empty,
} from 'antd';
import { PieChart, Pie, Cell, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';
import {
  TrophyOutlined, BankOutlined,
  BarChartOutlined, SearchOutlined,
} from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useSearchParams } from 'react-router-dom';
import { useTenderCompanySearch } from '../hooks/business/useTender';
import type { TenderRecord } from '../types/tender';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;

const DEFAULT_COMPANY = '乾坤測繪';

const TenderCompanyPage: React.FC = () => {
  const navigate = useNavigate();
  App.useApp();
  const [searchParams] = useSearchParams();
  const initialCompany = searchParams.get('q') || DEFAULT_COMPANY;
  const [company, setCompany] = useState(initialCompany);
  const [searchInput, setSearchInput] = useState(initialCompany);
  const [page, setPage] = useState(1);

  // URL query 變更時更新
  useEffect(() => {
    const q = searchParams.get('q');
    if (q && q !== company) { setCompany(q); setSearchInput(q); setPage(1); }
  }, [searchParams]); // eslint-disable-line react-hooks/exhaustive-deps

  const { data, isLoading } = useTenderCompanySearch(company, page);
  const records = useMemo(() => data?.records ?? [], [data]);

  const PIE_COLORS = ['#1890ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1', '#13c2c2'];

  // 統計
  const stats = useMemo(() => {
    if (!records.length) return { total: 0, won: 0, rate: 0 };
    const won = records.filter(r => r.type.includes('決標') && (r.winner_names ?? []).some(n => n.includes(company))).length;
    return {
      total: data?.total_records ?? records.length,
      won,
      rate: records.length > 0 ? Math.round((won / records.length) * 100) : 0,
    };
  }, [records, data, company]);

  // 類別分布
  const categoryData = useMemo(() => {
    const map: Record<string, number> = {};
    records.forEach(r => {
      const cat = r.category ? (r.category.split('-')[0] ?? '').replace(/類$/, '') || '未分類' : '未分類';
      map[cat] = (map[cat] || 0) + 1;
    });
    return Object.entries(map).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value);
  }, [records]);

  // 年度趨勢
  const yearData = useMemo(() => {
    const map: Record<string, number> = {};
    records.forEach(r => {
      const year = r.date?.slice(0, 4) || '不明';
      map[year] = (map[year] || 0) + 1;
    });
    return Object.entries(map).map(([name, value]) => ({ name, value })).sort((a, b) => a.name.localeCompare(b.name));
  }, [records]);

  const columns: ColumnsType<TenderRecord> = [
    {
      title: '日期', dataIndex: 'date', width: 105, align: 'center',
      render: (v: string) => <Text type="secondary">{v}</Text>,
    },
    {
      title: '標案名稱', dataIndex: 'title', ellipsis: true,
      render: (title: string, record) => (
        <a onClick={() => navigate(`/tender/${encodeURIComponent(record.unit_id)}/${encodeURIComponent(record.job_number)}`)}
          style={{ fontWeight: 500 }}>{title}</a>
      ),
    },
    {
      title: '招標機關', dataIndex: 'unit_name', width: 180, ellipsis: true,
      render: (v: string) => <><BankOutlined style={{ marginRight: 4, color: '#8c8c8c' }} />{v}</>,
    },
    {
      title: '類型', dataIndex: 'type', width: 120, ellipsis: true,
      render: (v: string) => {
        const isWin = v.includes('決標');
        return <Tag color={isWin ? 'green' : 'default'}>{v.length > 8 ? v.slice(0, 8) + '...' : v}</Tag>;
      },
    },
    {
      title: '得標廠商', key: 'companies', width: 160, ellipsis: true,
      render: (_: unknown, r: TenderRecord) => {
        const winners = r.winner_names ?? [];
        if (!winners.length) return <Text type="secondary">-</Text>;
        return (
          <span>
            {winners.slice(0, 2).map((name, i) => (
              <a key={i} onClick={(e) => { e.stopPropagation(); setCompany(name); setSearchInput(name); setPage(1); }}
                style={{ color: name.includes(company) ? '#52c41a' : '#1890ff', marginRight: 4 }}>
                {name.length > 10 ? name.slice(0, 10) + '...' : name}
              </a>
            ))}
          </span>
        );
      },
    },
    {
      title: '結果', key: 'result', width: 80, align: 'center',
      render: (_: unknown, r: TenderRecord) => {
        if (!r.type.includes('決標')) return <Tag>-</Tag>;
        const isWin = (r.winner_names ?? []).some(n => n.includes(company));
        return <Tag color={isWin ? 'green' : 'orange'}>{isWin ? '得標' : '未得標'}</Tag>;
      },
    },
  ];

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle" gutter={[16, 16]}>
          <Col flex="auto">
            <Title level={3} style={{ margin: 0 }}>
              <BarChartOutlined style={{ marginRight: 8 }} />廠商投標歷史
            </Title>
          </Col>
          <Col>
            <Input.Search
              placeholder="搜尋廠商名稱"
              value={searchInput}
              onChange={e => setSearchInput(e.target.value)}
              onSearch={v => { if (v.trim()) { setCompany(v.trim()); setPage(1); } }}
              enterButton={<SearchOutlined />}
              style={{ width: 280 }}
              allowClear
            />
          </Col>
        </Row>

        {records.length > 0 && (
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={12} sm={6}>
              <Statistic title="投標紀錄" value={stats.total} suffix="筆" />
            </Col>
            <Col xs={12} sm={6}>
              <Statistic title="得標" value={stats.won} suffix="筆"
                valueStyle={{ color: '#52c41a' }} prefix={<TrophyOutlined />} />
            </Col>
            <Col xs={12} sm={6}>
              <Statistic title="得標率" value={stats.rate} suffix="%"
                valueStyle={{ color: stats.rate > 50 ? '#52c41a' : '#fa8c16' }} />
            </Col>
            <Col xs={12} sm={6}>
              <Progress type="circle" percent={stats.rate} size={60}
                strokeColor={stats.rate > 50 ? '#52c41a' : '#fa8c16'} />
            </Col>
          </Row>
        )}
      </Card>

      {/* 圖表區 */}
      {records.length > 0 && (
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={12}>
            <Card title="標案類別分布" size="small">
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={categoryData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                    outerRadius={70} label>
                    {categoryData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                  </Pie>
                  <RechartsTooltip />
                </PieChart>
              </ResponsiveContainer>
            </Card>
          </Col>
          <Col xs={24} sm={12}>
            <Card title="年度投標分布" size="small">
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={yearData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                    outerRadius={70} label={({ name, value }) => `${name} (${value})`}>
                    {yearData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                  </Pie>
                  <RechartsTooltip />
                </PieChart>
              </ResponsiveContainer>
            </Card>
          </Col>
        </Row>
      )}

      <Card title={<><BankOutlined /> {company} — 投標紀錄</>}>
        {!records.length && !isLoading ? (
          <Empty description={`查無「${company}」的投標紀錄`} />
        ) : (
          <Table<TenderRecord>
            columns={columns}
            dataSource={records}
            rowKey={r => `${r.unit_id}-${r.job_number}-${r.raw_date}`}
            loading={isLoading}
            size="middle"
            scroll={{ x: 800 }}
            pagination={{
              current: page, pageSize: 100,
              total: data?.total_records ?? 0,
              onChange: setPage,
              showTotal: (t) => `共 ${t.toLocaleString()} 筆`,
            }}
            onRow={record => ({
              onClick: () => navigate(`/tender/${encodeURIComponent(record.unit_id)}/${encodeURIComponent(record.job_number)}`),
              style: { cursor: 'pointer' },
            })}
          />
        )}
      </Card>
    </ResponsiveContent>
  );
};

export default TenderCompanyPage;

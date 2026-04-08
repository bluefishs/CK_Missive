/**
 * 廠商分析頁面 — 得標歷史 + 機關分布 + 勝率
 *
 * 參考: https://app.acebidx.com/orgbidder/report/
 */
import React, { useState, useMemo, useCallback } from 'react';
import {
  Card, Row, Col, Statistic, Table, Tag, Typography, Spin, Input, Button, Empty, Space, Progress,
} from 'antd';
import { TeamOutlined, SearchOutlined, TrophyOutlined, StarOutlined, StarFilled } from '@ant-design/icons';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ResponsiveContent } from '@ck-shared/ui-components';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  // PieChart moved to CategoryPieChart shared component
} from 'recharts';
import apiClient from '../api/client';
import { useCompanyBookmarks, useAddCompanyBookmark, useRemoveCompanyBookmark } from '../hooks/business/useTender';
import { TENDER_ENDPOINTS } from '../api/endpoints';
import { ROUTES } from '../router/types';
import CategoryPieChart from '../components/tender/CategoryPieChart';

const { Title, Text } = Typography;

interface CompanyData {
  company_name: string;
  total: number;
  won_count: number;
  win_rate: number;
  year_trend: Array<{ year: string; count: number }>;
  top_agencies: Array<{ name: string; count: number }>;
  category_distribution: Array<{ name: string; value: number }>;
  recent_tenders: Array<{
    title: string; date: string; unit_name: string;
    unit_id: string; job_number: string; type?: string; category?: string;
    winner_names?: string[]; bidder_names?: string[]; is_won?: boolean;
  }>;
}

const TenderCompanyProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialCompany = searchParams.get('q') || searchParams.get('company') || '';
  const [companyInput, setCompanyInput] = useState(initialCompany);
  const [companyName, setCompanyName] = useState(initialCompany);

  // 廠商收藏
  const { data: companyBms } = useCompanyBookmarks();
  const addBm = useAddCompanyBookmark();
  const removeBm = useRemoveCompanyBookmark();
  const isBookmarked = useMemo(() => companyBms?.some((b: { company_name: string }) => b.company_name === companyName), [companyBms, companyName]);
  const toggleBookmark = useCallback(() => {
    if (isBookmarked) {
      removeBm.mutate({ company_name: companyName });
    } else {
      addBm.mutate({ company_name: companyName, tag: 'competitor' });
    }
  }, [isBookmarked, companyName, addBm, removeBm]);

  const { data, isLoading } = useQuery<CompanyData>({
    queryKey: ['company-profile', companyName],
    queryFn: async () => {
      const res = await apiClient.post<{ data: CompanyData }>(
        TENDER_ENDPOINTS.ANALYTICS_COMPANY_PROFILE,
        { company_name: companyName },
      );
      return res.data;
    },
    enabled: !!companyName,
    staleTime: 10 * 60_000,
  });

  const doSearch = () => {
    if (companyInput.trim()) {
      setCompanyName(companyInput.trim());
      setSearchParams({ company: companyInput.trim() });
    }
  };

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card style={{ marginBottom: 16 }}>
        <Title level={3} style={{ margin: '0 0 12px' }}><TeamOutlined /> 廠商投標分析</Title>
        <Space.Compact style={{ width: '100%', maxWidth: 600 }}>
          <Input
            placeholder="輸入廠商名稱 (如: 乾坤測繪科技有限公司)"
            value={companyInput}
            onChange={(e) => setCompanyInput(e.target.value)}
            onPressEnter={doSearch}
            size="large"
          />
          <Button type="primary" icon={<SearchOutlined />} size="large" onClick={doSearch}>分析</Button>
        </Space.Compact>
        {companyName && (
          <Button
            style={{ marginLeft: 12 }}
            size="large"
            icon={isBookmarked ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
            onClick={toggleBookmark}
          >
            {isBookmarked ? '已關注' : '關注廠商'}
          </Button>
        )}
      </Card>

      {/* 關注廠商清單 */}
      {!companyName && companyBms && companyBms.length > 0 && (
        <Card title={<><StarFilled style={{ color: '#faad14' }} /> 已關注廠商 ({companyBms.length})</>} size="small" style={{ marginBottom: 16 }}>
          <Row gutter={[8, 8]}>
            {companyBms.map((b) => (
              <Col key={b.id} xs={24} sm={12} md={8} lg={6}>
                <Card size="small" hoverable style={{ cursor: 'pointer' }}
                  onClick={() => { setCompanyName(b.company_name); setCompanyInput(b.company_name); setSearchParams({ company: b.company_name }); }}>
                  <Space>
                    <StarFilled style={{ color: '#faad14', fontSize: 14 }} />
                    <Text strong ellipsis style={{ maxWidth: 180 }} title={b.company_name}>{b.company_name}</Text>
                    {b.tag && <Tag color="blue">{b.tag}</Tag>}
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {isLoading && <Spin style={{ display: 'block', margin: '60px auto' }} size="large" />}

      {data && data.total > 0 && (
        <>
          {/* 統計卡片 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={12} sm={6}>
              <Card><Statistic title="參與標案" value={data.total} suffix="件" /></Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card>
                <Statistic
                  title="得標數" value={data.won_count} suffix="件"
                  prefix={<TrophyOutlined style={{ color: '#faad14' }} />}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card>
                <Text type="secondary">得標率</Text>
                <div style={{ marginTop: 8 }}>
                  <Progress
                    type="circle" size={80}
                    percent={data.win_rate}
                    format={(p) => `${p}%`}
                    strokeColor={data.win_rate >= 50 ? '#52c41a' : data.win_rate >= 30 ? '#faad14' : '#ff4d4f'}
                  />
                </div>
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card><Statistic title="合作機關" value={data.top_agencies?.length ?? 0} suffix="個" /></Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            {/* 年度趨勢 — 近 5 年降冪 */}
            <Col xs={24} lg={14}>
              {(() => {
                const sorted = (data.year_trend || [])
                  .filter((d: { year: string }) => d.year && d.year !== '未知')
                  .sort((a: { year: string }, b: { year: string }) => b.year.localeCompare(a.year));
                const recent5 = sorted.slice(0, 5).reverse(); // 近 5 年，升冪顯示 (左舊右新)
                const range = recent5.length > 0 ? `${recent5[0]?.year} – ${recent5[recent5.length - 1]?.year}` : '';
                return (
                  <Card title={`年度投標趨勢 (${range})`} size="small">
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart data={recent5}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="year" />
                        <YAxis />
                        <Tooltip />
                        <Bar dataKey="count" name="參與標案" fill="#1890ff" />
                      </BarChart>
                    </ResponsiveContainer>
                  </Card>
                );
              })()}
            </Col>

            {/* 類別分布 — 共用元件 */}
            <Col xs={24} lg={10}>
              <Card title="標案類別分布" size="small">
                <CategoryPieChart data={data.category_distribution} />
              </Card>
            </Col>
          </Row>

          {/* 合作機關排行 */}
          <Card title="常合作機關 (Top 15)" size="small" style={{ marginBottom: 16 }}>
            <Row gutter={[8, 4]}>
              {(data.top_agencies || []).map((a, i) => (
                <Col key={i} xs={24} sm={12} md={8}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid #f5f5f5' }}>
                    <a onClick={() => navigate(`${ROUTES.TENDER_ORG_ECOSYSTEM}?org=${encodeURIComponent(a.name)}`)}
                       style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}
                       title={a.name}>{a.name}</a>
                    <Tag style={{ marginLeft: 4, flexShrink: 0 }}>{a.count}</Tag>
                  </div>
                </Col>
              ))}
            </Row>
          </Card>

          {/* 投標紀錄 — 全寬顯示以完整呈現標案名稱 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24}>
              <Card title="投標紀錄" size="small">
                <Table
                  columns={[
                    {
                      title: '標案名稱', dataIndex: 'title', key: 'title',
                      ellipsis: { showTitle: true },
                      render: (v: string, r: CompanyData['recent_tenders'][0]) => (
                        <a onClick={() => navigate(`/tender/${r.unit_id}/${r.job_number}`)} title={v}>{v}</a>
                      ),
                    },
                    { title: '日期', dataIndex: 'date', key: 'date', width: 105 },
                    { title: '類型', dataIndex: 'type', key: 'type', width: 65,
                      render: (v: string) => <Tag>{v || '未知'}</Tag>,
                    },
                    {
                      title: '結果', key: 'result', width: 80,
                      render: (_: unknown, r: CompanyData['recent_tenders'][0]) => {
                        // 模糊匹配：搜尋名稱包含在得標廠商名中
                        const isWon = r.is_won || (r.winner_names || []).some(
                          (w: string) => w.includes(companyName) || companyName.includes(w)
                        );
                        return isWon
                          ? <Tag color="green">得標</Tag>
                          : <Tag color="default">投標</Tag>;
                      },
                    },
                    {
                      title: '得標廠商', key: 'winner', width: 140, ellipsis: true,
                      render: (_: unknown, r: CompanyData['recent_tenders'][0]) => {
                        const winners = r.winner_names || [];
                        if (winners.length === 0) return <Text type="secondary">-</Text>;
                        return <Text style={{ fontSize: 12 }}>{winners.join('、')}</Text>;
                      },
                    },
                  ]}
                  dataSource={data.recent_tenders}
                  rowKey={(r, i) => `${r.unit_id}-${r.job_number}-${i}`}
                  size="small"
                  pagination={{ pageSize: 10, showSizeChanger: false }}
                />
              </Card>
            </Col>
          </Row>
        </>
      )}

      {data && data.total === 0 && <Empty description={`找不到「${companyName}」的投標紀錄`} />}
    </ResponsiveContent>
  );
};

export default TenderCompanyProfilePage;

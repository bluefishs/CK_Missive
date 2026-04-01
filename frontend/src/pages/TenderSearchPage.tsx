/**
 * 標案檢索頁面
 *
 * 搜尋政府電子採購網標案，支援關鍵字搜尋、分類篩選、智能推薦。
 * 參考 ezbid.tw 風格設計。
 *
 * @version 1.0.0
 */
import React, { useState, useCallback } from 'react';
import {
  Card, Input, Table, Tag, Space, Select, Button, Typography, Row, Col,
  Statistic, Empty, Tooltip, App,
} from 'antd';
import {
  SearchOutlined, StarOutlined, BankOutlined,
  LinkOutlined, ReloadOutlined, PlusOutlined,
} from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useTenderSearch, useTenderRecommend } from '../hooks/business/useTender';
import { tenderApi } from '../api/tenderApi';
import type { TenderRecord, TenderSearchParams } from '../types/tender';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';

const { Title, Text, Paragraph } = Typography;

const CATEGORY_OPTIONS = [
  { value: '', label: '全部分類' },
  { value: '工程', label: '工程類' },
  { value: '勞務', label: '勞務類' },
  { value: '財物', label: '財物類' },
];

const TYPE_COLORS: Record<string, string> = {
  '公開取得報價單或企劃書公告': 'blue',
  '公開招標公告': 'green',
  '限制性招標公告': 'orange',
  '選擇性招標公告': 'purple',
  '定期彙送': 'default',
  '決標公告': 'cyan',
};

const TenderSearchPage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [searchInput, setSearchInput] = useState('');
  const [params, setParams] = useState<TenderSearchParams | null>(null);
  const [showRecommend, setShowRecommend] = useState(true);

  const { data: searchResult, isLoading: searching } = useTenderSearch(params);
  const { data: recommendResult, isLoading: recommending } = useTenderRecommend();

  const handleSearch = useCallback((value: string) => {
    const q = value.trim();
    if (!q) { message.warning('請輸入搜尋關鍵字'); return; }
    setParams({ query: q, page: 1 });
    setShowRecommend(false);
  }, [message]);

  const handleCategoryChange = useCallback((cat: string) => {
    if (!params?.query) return;
    setParams(p => p ? { ...p, category: cat || undefined, page: 1 } : null);
  }, [params]);

  const handlePageChange = useCallback((page: number) => {
    setParams(p => p ? { ...p, page } : null);
  }, []);

  const handleViewDetail = useCallback((record: TenderRecord) => {
    navigate(`/tender/${encodeURIComponent(record.unit_id)}/${encodeURIComponent(record.job_number)}`);
  }, [navigate]);

  const columns: ColumnsType<TenderRecord> = [
    {
      title: '公告日', dataIndex: 'date', width: 110, align: 'center',
      render: (v: string) => <Text type="secondary">{v}</Text>,
    },
    {
      title: '標案名稱', dataIndex: 'title', ellipsis: true,
      render: (title: string, record) => (
        <div>
          <a onClick={() => handleViewDetail(record)} style={{ fontWeight: 500 }}>{title}</a>
          {record.matched_keyword && (
            <Tag color="gold" style={{ marginLeft: 8, fontSize: 11 }}>{record.matched_keyword}</Tag>
          )}
        </div>
      ),
    },
    {
      title: '類型', dataIndex: 'type', width: 180, ellipsis: true,
      render: (v: string) => {
        const short = v.length > 12 ? v.slice(0, 12) + '...' : v;
        const color = Object.entries(TYPE_COLORS).find(([k]) => v.includes(k))?.[1] || 'default';
        return <Tooltip title={v}><Tag color={color}>{short}</Tag></Tooltip>;
      },
    },
    {
      title: '招標機關', dataIndex: 'unit_name', width: 180, ellipsis: true,
      render: (v: string) => <><BankOutlined style={{ marginRight: 4, color: '#8c8c8c' }} />{v}</>,
    },
    {
      title: '分類', dataIndex: 'category', width: 140, ellipsis: true,
      render: (v: string) => v ? <Tag>{v.split('-')[0]}</Tag> : '-',
    },
    {
      title: '得標廠商', key: 'companies', width: 160, ellipsis: true,
      render: (_: unknown, r: TenderRecord) =>
        r.company_names.length > 0
          ? <Text type="success">{r.company_names[0]}</Text>
          : <Text type="secondary">-</Text>,
    },
    {
      title: '', key: 'action', width: 140,
      render: (_: unknown, record: TenderRecord) => (
        <Space size={0}>
          <Button type="link" size="small" icon={<LinkOutlined />} onClick={() => handleViewDetail(record)}>
            詳情
          </Button>
          <Button type="link" size="small" icon={<PlusOutlined />} onClick={async (e) => {
            e.stopPropagation();
            try {
              const result = await tenderApi.createCase({
                unit_id: record.unit_id,
                job_number: record.job_number,
                title: record.title,
                unit_name: record.unit_name,
                category: record.category,
              });
              message.success(`${result.message} — ${result.case_code}`);
            } catch { message.error('建案失敗'); }
          }}>
            建案
          </Button>
        </Space>
      ),
    },
  ];

  const displayData = showRecommend && !params ? recommendResult?.records : searchResult?.records;
  const displayTotal = showRecommend && !params ? recommendResult?.total : searchResult?.total_records;
  const isLoading = showRecommend && !params ? recommending : searching;

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      {/* 搜尋列 */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle" gutter={[16, 16]}>
          <Col flex="auto">
            <Title level={3} style={{ margin: 0 }}>
              <SearchOutlined style={{ marginRight: 8 }} />標案檢索
            </Title>
          </Col>
          <Col>
            <Space>
              <Statistic title="資料來源" value="政府電子採購網" valueStyle={{ fontSize: 14 }} />
            </Space>
          </Col>
        </Row>

        <Row gutter={[12, 12]} style={{ marginTop: 16 }}>
          <Col xs={24} sm={16} md={12}>
            <Input.Search
              placeholder="搜尋標案名稱（如：測量、空拍、透地雷達）"
              enterButton="搜尋"
              size="large"
              value={searchInput}
              onChange={e => setSearchInput(e.target.value)}
              onSearch={handleSearch}
              allowClear
            />
          </Col>
          <Col xs={12} sm={4}>
            <Select
              style={{ width: '100%' }}
              size="large"
              options={CATEGORY_OPTIONS}
              defaultValue=""
              onChange={handleCategoryChange}
            />
          </Col>
          <Col xs={12} sm={4}>
            <Space>
              <Button
                icon={<StarOutlined />}
                size="large"
                onClick={() => { setParams(null); setShowRecommend(true); setSearchInput(''); }}
              >
                推薦
              </Button>
              <Button
                icon={<ReloadOutlined />}
                size="large"
                onClick={() => { if (params) setParams({ ...params }); }}
              />
            </Space>
          </Col>
        </Row>

        {showRecommend && !params && recommendResult && (
          <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
            <StarOutlined /> 依乾坤核心業務推薦（{recommendResult.keywords.join('、')}），共 {recommendResult.total} 筆
          </Paragraph>
        )}
      </Card>

      {/* 結果列表 */}
      <Card>
        {!displayData && !isLoading ? (
          <Empty description="輸入關鍵字搜尋標案，或點擊「推薦」查看相關標案" />
        ) : (
          <Table<TenderRecord>
            columns={columns}
            dataSource={displayData ?? []}
            rowKey={r => `${r.unit_id}-${r.job_number}-${r.raw_date}`}
            loading={isLoading}
            pagination={
              params ? {
                current: params.page ?? 1,
                pageSize: 100,
                total: displayTotal ?? 0,
                onChange: handlePageChange,
                showTotal: (total) => `共 ${total.toLocaleString()} 筆`,
                showSizeChanger: false,
              } : false
            }
            size="middle"
            scroll={{ x: 1000 }}
            onRow={record => ({
              onClick: () => handleViewDetail(record),
              style: { cursor: 'pointer' },
            })}
          />
        )}
      </Card>
    </ResponsiveContent>
  );
};

export default TenderSearchPage;

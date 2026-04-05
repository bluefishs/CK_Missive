/**
 * 標案檢索頁面
 *
 * 三 Tab: 搜尋 / 收藏書籤 / 關鍵字訂閱
 * 參考 ezbid.tw 風格設計。
 *
 * @version 2.0.0 — Phase 3 訂閱+書籤整合
 */
import React, { useState, useCallback } from 'react';
import {
  Card, Input, Table, Tag, Space, Select, Button, Typography, Row, Col,
  Statistic, Empty, Tooltip, App, Tabs, Popconfirm, Badge, Flex,
} from 'antd';
import {
  SearchOutlined, StarOutlined, BankOutlined,
  LinkOutlined, ReloadOutlined, PlusOutlined, DeleteOutlined,
  BellOutlined, BookOutlined,
} from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import {
  useTenderSearch, useTenderRecommend,
  useTenderSubscriptions, useCreateSubscription, useDeleteSubscription,
  useTenderBookmarks, useCreateBookmark, useDeleteBookmark,
} from '../hooks/business/useTender';
import { tenderApi } from '../api/tenderApi';
import type { TenderRecord, TenderSearchParams } from '../types/tender';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/types';

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
  '限制性招標': 'orange',
  '決標公告': 'cyan',
  '定期彙送': 'default',
};

const BOOKMARK_STATUS_MAP: Record<string, { color: string; label: string }> = {
  tracking: { color: 'blue', label: '追蹤中' },
  applied: { color: 'orange', label: '已投標' },
  won: { color: 'green', label: '得標' },
  lost: { color: 'default', label: '未得標' },
};

const TenderSearchPage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [searchInput, setSearchInput] = useState('');
  const [params, setParams] = useState<TenderSearchParams | null>(null);
  const [showRecommend, setShowRecommend] = useState(true);
  const [subKeyword, setSubKeyword] = useState('');

  const { data: searchResult, isLoading: searching } = useTenderSearch(params);
  const { data: recommendResult, isLoading: recommending } = useTenderRecommend();
  const { data: subscriptions } = useTenderSubscriptions();
  const { data: bookmarks } = useTenderBookmarks();
  const createSub = useCreateSubscription();
  const deleteSub = useDeleteSubscription();
  const createBm = useCreateBookmark();
  const deleteBm = useDeleteBookmark();

  const handleSearch = useCallback((value: string) => {
    const q = value.trim();
    if (!q) { message.warning('請輸入搜尋關鍵字'); return; }
    setParams({ query: q, page: 1 });
    setShowRecommend(false);
  }, [message]);

  const handleViewDetail = useCallback((record: TenderRecord) => {
    navigate(`/tender/${encodeURIComponent(record.unit_id)}/${encodeURIComponent(record.job_number)}`);
  }, [navigate]);

  const handleBookmark = useCallback(async (record: TenderRecord) => {
    try {
      await createBm.mutateAsync({
        unit_id: record.unit_id, job_number: record.job_number,
        title: record.title, unit_name: record.unit_name,
      });
      message.success('已收藏');
    } catch { message.error('收藏失敗（可能已收藏）'); }
  }, [createBm, message]);

  const columns: ColumnsType<TenderRecord> = [
    {
      title: '公告日', dataIndex: 'date', width: 105, align: 'center',
      render: (v: string) => <Text type="secondary">{v}</Text>,
    },
    {
      title: '標案名稱', dataIndex: 'title', ellipsis: true,
      render: (title: string, record) => (
        <div>
          <a onClick={() => handleViewDetail(record)} style={{ fontWeight: 500 }}>{title}</a>
          {record.matched_keyword && <Tag color="gold" style={{ marginLeft: 8, fontSize: 11 }}>{record.matched_keyword}</Tag>}
        </div>
      ),
    },
    {
      title: '類型', dataIndex: 'type', width: 160, ellipsis: true,
      render: (v: string) => {
        const color = Object.entries(TYPE_COLORS).find(([k]) => v.includes(k))?.[1] || 'default';
        return <Tooltip title={v}><Tag color={color}>{v.length > 10 ? v.slice(0, 10) + '...' : v}</Tag></Tooltip>;
      },
    },
    {
      title: '招標機關', dataIndex: 'unit_name', width: 170, ellipsis: true,
      render: (v: string) => <><BankOutlined style={{ marginRight: 4, color: '#8c8c8c' }} />{v}</>,
    },
    {
      title: '得標', key: 'companies', width: 130, ellipsis: true,
      render: (_: unknown, r: TenderRecord) =>
        r.company_names.length > 0 && r.company_names[0]
          ? <a onClick={(e) => { e.stopPropagation(); navigate(`/tender/company?q=${encodeURIComponent(r.company_names[0]!)}`); }} style={{ color: '#52c41a' }}>{r.company_names[0]!.length > 10 ? r.company_names[0]!.slice(0, 10) + '...' : r.company_names[0]}</a>
          : <Text type="secondary">-</Text>,
    },
    {
      title: '', key: 'action', width: 150,
      render: (_: unknown, record: TenderRecord) => (
        <Space size={0}>
          <Tooltip title="收藏"><Button type="text" size="small" icon={<StarOutlined />} onClick={(e) => { e.stopPropagation(); handleBookmark(record); }} /></Tooltip>
          <Button type="link" size="small" icon={<LinkOutlined />} onClick={() => handleViewDetail(record)}>詳情</Button>
          <Button type="link" size="small" icon={<PlusOutlined />} onClick={async (e) => {
            e.stopPropagation();
            try {
              if (!record.title || !record.unit_id || !record.job_number) { message.warning('此標案資訊不完整'); return; }
              const result = await tenderApi.createCase({ unit_id: record.unit_id, job_number: record.job_number, title: record.title, unit_name: record.unit_name || '', category: record.category || undefined });
              message.success(`${result.message}`);
            } catch { message.error('建案失敗'); }
          }}>建案</Button>
        </Space>
      ),
    },
  ];

  const displayData = showRecommend && !params ? recommendResult?.records : searchResult?.records;
  const displayTotal = showRecommend && !params ? recommendResult?.total : searchResult?.total_records;
  const isLoading = showRecommend && !params ? recommending : searching;

  // ========== Tab: 搜尋 ==========
  const searchTab = (
    <div>
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={14} md={10}>
          <Input.Search placeholder="搜尋標案名稱" enterButton="搜尋" size="large"
            value={searchInput} onChange={e => setSearchInput(e.target.value)} onSearch={handleSearch} allowClear />
        </Col>
        <Col xs={12} sm={5} md={3}>
          <Select style={{ width: '100%' }} size="large" options={CATEGORY_OPTIONS} defaultValue=""
            onChange={(v) => { if (params?.query) setParams(p => p ? { ...p, category: v || undefined, page: 1 } : null); }} />
        </Col>
        <Col>
          <Space>
            <Button icon={<StarOutlined />} size="large" onClick={() => { setParams(null); setShowRecommend(true); setSearchInput(''); }}>推薦</Button>
            <Button icon={<ReloadOutlined />} size="large" onClick={() => { if (params) setParams({ ...params }); }} />
          </Space>
        </Col>
      </Row>
      {showRecommend && !params && recommendResult && (
        <Paragraph type="secondary"><StarOutlined /> 依核心業務推薦（{recommendResult.keywords.join('、')}），共 {recommendResult.total} 筆</Paragraph>
      )}
      <Table<TenderRecord> columns={columns} dataSource={displayData ?? []} rowKey={(r) => `${r.unit_id}-${r.job_number}-${r.raw_date}-${r.title?.slice(0,10)}`}
        loading={isLoading} size="middle" scroll={{ x: 900 }}
        pagination={params ? { current: params.page ?? 1, pageSize: 100, total: displayTotal ?? 0,
          onChange: (p) => setParams(prev => prev ? { ...prev, page: p } : null), showTotal: (t) => `共 ${t.toLocaleString()} 筆`, showSizeChanger: false } : false}
        onRow={record => ({ onClick: () => handleViewDetail(record), style: { cursor: 'pointer' } })}
      />
    </div>
  );

  // ========== Tab: 書籤 ==========
  const bookmarkTab = (
    <div>
      {!bookmarks?.length ? <Empty description="尚無收藏標案" /> : (
        <Flex vertical gap={8}>
          {bookmarks.map((b) => (
            <Card key={b.id} size="small" extra={
              <Space>
                <Tag color={BOOKMARK_STATUS_MAP[b.status]?.color}>{BOOKMARK_STATUS_MAP[b.status]?.label ?? b.status}</Tag>
                <Button type="link" size="small" onClick={() => navigate(`/tender/${encodeURIComponent(b.unit_id)}/${encodeURIComponent(b.job_number)}`)}>詳情</Button>
                <Popconfirm title="移除收藏？" onConfirm={() => deleteBm.mutate(b.id)}><Button type="link" size="small" danger icon={<DeleteOutlined />} /></Popconfirm>
              </Space>
            }>
              <div style={{ fontWeight: 500 }}>{b.title}</div>
              <Space style={{ marginTop: 4 }}><BankOutlined />{b.unit_name ?? '-'}{b.budget && <Tag>{b.budget}</Tag>}{b.deadline && <Tag color="orange">截止: {b.deadline}</Tag>}{b.case_code && <Tag color="green">案號: {b.case_code}</Tag>}</Space>
            </Card>
          ))}
        </Flex>
      )}
    </div>
  );

  // ========== Tab: 訂閱 ==========
  const subscriptionTab = (
    <div>
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col flex="auto">
          <Input placeholder="輸入訂閱關鍵字（如：測量、空拍）" value={subKeyword} onChange={e => setSubKeyword(e.target.value)}
            onPressEnter={() => {
              if (!subKeyword.trim()) return;
              createSub.mutate({ keyword: subKeyword.trim() }, { onSuccess: () => { message.success('訂閱已建立'); setSubKeyword(''); } });
            }} />
        </Col>
        <Col><Button type="primary" icon={<PlusOutlined />} loading={createSub.isPending}
          onClick={() => { if (!subKeyword.trim()) return; createSub.mutate({ keyword: subKeyword.trim() }, { onSuccess: () => { message.success('訂閱已建立'); setSubKeyword(''); } }); }}>新增訂閱</Button></Col>
      </Row>
      {!subscriptions?.length ? <Empty description="尚無訂閱，新增關鍵字即可自動追蹤新標案" /> : (
        <Flex vertical gap={8}>
          {subscriptions.map((s) => (
            <Card key={s.id} size="small" extra={
              <Space>
                {s.last_count > 0 && <Badge count={s.last_count} style={{ backgroundColor: '#52c41a' }} />}
                <Button type="link" size="small" onClick={() => { setSearchInput(s.keyword); handleSearch(s.keyword); }}>搜尋</Button>
                <Popconfirm title="取消訂閱？" onConfirm={() => deleteSub.mutate(s.id)}><Button type="link" size="small" danger icon={<DeleteOutlined />} /></Popconfirm>
              </Space>
            }>
              <div><BellOutlined style={{ marginRight: 8 }} /><strong>{s.keyword}</strong>{s.category && <Tag style={{ marginLeft: 8 }}>{s.category}</Tag>}</div>
              <div style={{ color: '#8c8c8c', fontSize: 12 }}>{s.last_checked_at ? `最後查詢: ${s.last_checked_at}` : '尚未查詢'}</div>
            </Card>
          ))}
        </Flex>
      )}
    </div>
  );

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Title level={3} style={{ margin: 0 }}><SearchOutlined style={{ marginRight: 8 }} />標案檢索</Title>
              <Button type="link" onClick={() => navigate(ROUTES.TENDER_DASHBOARD)}>採購儀表板</Button>
              <Button type="link" onClick={() => navigate(ROUTES.TENDER_ORG_ECOSYSTEM)}>機關分析</Button>
              <Button type="link" onClick={() => navigate(ROUTES.TENDER_COMPANY_PROFILE)}>廠商分析</Button>
              <Button type="link" onClick={() => navigate(ROUTES.TENDER_GRAPH)}>標案圖譜</Button>
            </Space>
          </Col>
          <Col><Statistic title="資料來源" value="政府電子採購網" styles={{ content: { fontSize: 14 } }} /></Col>
        </Row>
      </Card>

      <Card>
        <Tabs defaultActiveKey="search" items={[
          { key: 'search', label: <><SearchOutlined /> 搜尋</>, children: searchTab },
          { key: 'bookmarks', label: <><BookOutlined /> 收藏 <Badge count={bookmarks?.length ?? 0} size="small" offset={[4, -2]} /></>, children: bookmarkTab },
          { key: 'subscriptions', label: <><BellOutlined /> 訂閱 <Badge count={subscriptions?.length ?? 0} size="small" offset={[4, -2]} /></>, children: subscriptionTab },
        ]} />
      </Card>
    </ResponsiveContent>
  );
};

export default TenderSearchPage;

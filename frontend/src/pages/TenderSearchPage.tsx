/**
 * 標案檢索頁面
 *
 * 三 Tab: 搜尋 / 訂閱 / 收藏
 * - 搜尋: 多模式 (標案/機關/廠商) + 招標類型客戶端篩選
 * - 訂閱: 關鍵字自動監控，點擊切換搜尋查看結果
 * - 收藏: 導航模式 Table，點擊跳轉詳情頁
 *
 * @version 3.1.0
 */
import React, { useState, useCallback, useMemo } from 'react';
import {
  Card, Input, Table, Tag, Space, Select, Button, Typography, Row, Col,
  Empty, Tooltip, App, Tabs, Popconfirm, Badge, Flex,
} from 'antd';
import {
  SearchOutlined, StarOutlined, StarFilled, BankOutlined,
  ReloadOutlined, PlusOutlined, DeleteOutlined,
  BellOutlined, BookOutlined, FilterOutlined,
} from '@ant-design/icons';
import { useResponsive } from '../hooks';
import { ClickableStatCard } from '../components/common';
import {
  useTenderSearch, useTenderRecommend,
  useTenderSubscriptions, useCreateSubscription, useDeleteSubscription, useUpdateSubscription,
  useTenderBookmarks, useCreateBookmark, useDeleteBookmark,
} from '../hooks/business/useTender';
import type { TenderRecord, TenderSearchParams } from '../types/tender';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/types';

const { Title, Text, Paragraph } = Typography;

const CATEGORY_OPTIONS = [
  { value: '', label: '全部類別' },
  { value: '工程', label: '工程類' },
  { value: '勞務', label: '勞務類' },
  { value: '財物', label: '財物類' },
];

const SEARCH_TYPE_OPTIONS = [
  { value: 'title', label: '標案名稱' },
  { value: 'org', label: '機關名稱' },
  { value: 'company', label: '廠商名稱' },
];

const TYPE_FILTER_OPTIONS = [
  { value: '', label: '全部類型' },
  { value: '公開招標', label: '公開招標' },
  { value: '公開取得報價單', label: '公開取得報價' },
  { value: '限制性招標', label: '限制性招標' },
  { value: '決標公告', label: '決標公告' },
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
  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  // Tab 控制
  const [activeTab, setActiveTab] = useState('search');

  // 搜尋狀態
  const [searchInput, setSearchInput] = useState('');
  const [searchType, setSearchType] = useState<'title' | 'org' | 'company'>('title');
  const [typeFilter, setTypeFilter] = useState('');
  const [params, setParams] = useState<TenderSearchParams | null>(null);
  const [showRecommend, setShowRecommend] = useState(true);

  // 訂閱狀態
  const [subKeyword, setSubKeyword] = useState('');
  const [subCategory, setSubCategory] = useState('');
  const [editingSubId, setEditingSubId] = useState<number | null>(null);
  const [editingKeyword, setEditingKeyword] = useState('');

  // React Query
  const { data: searchResult, isLoading: searching } = useTenderSearch(params);
  const { data: recommendResult, isLoading: recommending } = useTenderRecommend();
  const { data: subscriptions } = useTenderSubscriptions();
  const { data: bookmarks } = useTenderBookmarks();
  const createSub = useCreateSubscription();
  const updateSub = useUpdateSubscription();
  const deleteSub = useDeleteSubscription();
  const createBm = useCreateBookmark();
  const deleteBm = useDeleteBookmark();

  // 搜尋
  const handleSearch = useCallback((value: string, type?: 'title' | 'org' | 'company') => {
    const q = value.trim();
    if (!q) { message.warning('請輸入搜尋關鍵字'); return; }
    const st = type ?? searchType;
    setParams({ query: q, page: 1, search_type: st });
    setShowRecommend(false);
    setTypeFilter('');
  }, [message, searchType]);

  const handleViewDetail = useCallback((record: TenderRecord) => {
    navigate(`/tender/${encodeURIComponent(record.unit_id)}/${encodeURIComponent(record.job_number)}`);
  }, [navigate]);

  // 訂閱 → 搜尋 Tab 切換
  const handleSubSearch = useCallback((keyword: string) => {
    setSearchInput(keyword);
    setSearchType('title');
    setActiveTab('search');
    setParams({ query: keyword, page: 1, search_type: 'title' });
    setShowRecommend(false);
    setTypeFilter('');
  }, []);

  // 收藏 toggle — 確保 unit_name 有值
  const bookmarkedKeys = useMemo(() => {
    const keys = new Set<string>();
    bookmarks?.forEach((b) => keys.add(`${b.unit_id}-${b.job_number}`));
    return keys;
  }, [bookmarks]);

  const findBookmarkId = useCallback((record: TenderRecord) => {
    return bookmarks?.find(
      (b) => b.unit_id === record.unit_id && b.job_number === record.job_number
    )?.id;
  }, [bookmarks]);

  const handleToggleBookmark = useCallback(async (record: TenderRecord) => {
    const existingId = findBookmarkId(record);
    if (existingId) {
      try {
        await deleteBm.mutateAsync(existingId);
        message.success('已取消收藏');
      } catch { message.error('取消收藏失敗'); }
    } else {
      try {
        await createBm.mutateAsync({
          unit_id: record.unit_id, job_number: record.job_number,
          title: record.title,
          unit_name: record.unit_name || '(未知機關)',
        });
        message.success('已收藏');
      } catch { message.error('收藏失敗'); }
    }
  }, [createBm, deleteBm, findBookmarkId, message]);

  // 搜尋結果 + 客戶端招標類型篩選
  const rawData = showRecommend && !params ? recommendResult?.records : searchResult?.records;
  const filteredData = useMemo(() => {
    if (!rawData) return [];
    if (!typeFilter) return rawData;
    return rawData.filter(r => r.type.includes(typeFilter));
  }, [rawData, typeFilter]);
  const displayTotal = showRecommend && !params ? recommendResult?.total : searchResult?.total_records;
  const isLoading = showRecommend && !params ? recommending : searching;

  // 搜尋結果表格欄位
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
      render: (v: string, record) => {
        const displayName = v && /[\u4e00-\u9fff]/.test(v) ? v : record.unit_id;
        return (
          <Tooltip title={displayName}>
            <a onClick={(e) => { e.stopPropagation(); setSearchType('org'); setSearchInput(displayName); handleSearch(displayName, 'org'); }} style={{ color: '#595959' }}>
              <BankOutlined style={{ marginRight: 4, color: '#8c8c8c' }} />{displayName}
            </a>
          </Tooltip>
        );
      },
    },
    {
      title: '得標', key: 'companies', width: 130, ellipsis: true,
      render: (_: unknown, r: TenderRecord) =>
        r.company_names.length > 0 && r.company_names[0]
          ? <a onClick={(e) => { e.stopPropagation(); setSearchType('company'); setSearchInput(r.company_names[0]!); handleSearch(r.company_names[0]!, 'company'); }} style={{ color: '#52c41a' }}>{r.company_names[0]!.length > 10 ? r.company_names[0]!.slice(0, 10) + '...' : r.company_names[0]}</a>
          : <Text type="secondary">-</Text>,
    },
    {
      title: '', key: 'action', width: 50, align: 'center' as const,
      render: (_: unknown, record: TenderRecord) => {
        const isBookmarked = bookmarkedKeys.has(`${record.unit_id}-${record.job_number}`);
        return (
          <Tooltip title={isBookmarked ? '取消收藏' : '收藏'}>
            <Button
              type="text" size="small"
              icon={isBookmarked ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
              onClick={(e) => { e.stopPropagation(); handleToggleBookmark(record); }}
            />
          </Tooltip>
        );
      },
    },
  ];

  // ========== Tab 1: 搜尋 ==========
  const searchTab = (
    <div>
      <Row gutter={[8, 8]} style={{ marginBottom: 12 }}>
        <Col xs={24} sm={4} md={3}>
          <Select
            style={{ width: '100%' }} size="large"
            options={SEARCH_TYPE_OPTIONS} value={searchType}
            onChange={(v) => setSearchType(v as 'title' | 'org' | 'company')}
          />
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Input.Search
            placeholder={searchType === 'title' ? '輸入標案名稱關鍵字' : searchType === 'org' ? '輸入招標機關名稱' : '輸入廠商名稱'}
            enterButton="搜尋" size="large"
            value={searchInput} onChange={e => setSearchInput(e.target.value)}
            onSearch={(v) => handleSearch(v)} allowClear
          />
        </Col>
        <Col xs={12} sm={4} md={3}>
          <Select style={{ width: '100%' }} size="large" options={CATEGORY_OPTIONS} defaultValue=""
            onChange={(v) => { if (params?.query) setParams(p => p ? { ...p, category: v || undefined, page: 1 } : null); }}
            placeholder="採購性質"
          />
        </Col>
        <Col xs={12} sm={4} md={3}>
          <Select style={{ width: '100%' }} size="large" options={TYPE_FILTER_OPTIONS} value={typeFilter}
            onChange={setTypeFilter} placeholder="招標類型"
            suffixIcon={<FilterOutlined />}
          />
        </Col>
        <Col>
          <Space>
            <Button icon={<StarOutlined />} size="large" onClick={() => { setParams(null); setShowRecommend(true); setSearchInput(''); setTypeFilter(''); }}>推薦</Button>
            <Button icon={<ReloadOutlined />} size="large" onClick={() => { if (params) setParams({ ...params }); }} />
          </Space>
        </Col>
      </Row>
      {showRecommend && !params && recommendResult && (
        <Paragraph type="secondary"><StarOutlined /> 依核心業務推薦（{recommendResult.keywords.join('、')}），共 {recommendResult.total} 筆</Paragraph>
      )}
      {typeFilter && <Tag closable onClose={() => setTypeFilter('')} color="blue" style={{ marginBottom: 8 }}>類型篩選: {typeFilter}</Tag>}
      <Table<TenderRecord> columns={columns} dataSource={filteredData} rowKey={(r, i) => `${r.unit_id}-${r.job_number}-${r.raw_date}-${i}`}
        loading={isLoading} size="middle" scroll={{ x: 900 }}
        pagination={params ? { current: params.page ?? 1, pageSize: 100, total: typeFilter ? filteredData.length : (displayTotal ?? 0),
          onChange: (p) => { if (!typeFilter) setParams(prev => prev ? { ...prev, page: p } : null); }, showTotal: (t) => `共 ${t.toLocaleString()} 筆`, showSizeChanger: false } : false}
        onRow={record => ({ onClick: () => handleViewDetail(record), style: { cursor: 'pointer' } })}
      />
    </div>
  );

  // ========== Tab 2: 訂閱 ==========
  const subscriptionTab = (
    <div>
      <Row gutter={[8, 8]} style={{ marginBottom: 16 }}>
        <Col flex="auto">
          <Input placeholder="輸入訂閱關鍵字（如：測量、空拍、地籍）" value={subKeyword} onChange={e => setSubKeyword(e.target.value)}
            onPressEnter={() => {
              if (!subKeyword.trim()) return;
              createSub.mutate({ keyword: subKeyword.trim(), category: subCategory || undefined }, { onSuccess: () => { message.success('訂閱已建立'); setSubKeyword(''); setSubCategory(''); } });
            }} />
        </Col>
        <Col>
          <Select style={{ width: 100 }} options={CATEGORY_OPTIONS} value={subCategory}
            onChange={setSubCategory} placeholder="類別" />
        </Col>
        <Col>
          <Button type="primary" icon={<PlusOutlined />} loading={createSub.isPending}
            onClick={() => {
              if (!subKeyword.trim()) return;
              createSub.mutate({ keyword: subKeyword.trim(), category: subCategory || undefined }, { onSuccess: () => { message.success('訂閱已建立'); setSubKeyword(''); setSubCategory(''); } });
            }}>新增</Button>
        </Col>
      </Row>
      {!subscriptions?.length ? <Empty description="尚無訂閱，新增關鍵字即可自動追蹤新標案" /> : (
        <Flex vertical gap={8}>
          {subscriptions.map((s) => (
            <Card key={s.id} size="small"
              hoverable={editingSubId !== s.id}
              extra={
                <Space onClick={e => e.stopPropagation()}>
                  {editingSubId === s.id ? (
                    <Button type="link" size="small" onClick={() => {
                      if (!editingKeyword.trim()) return;
                      updateSub.mutate({ id: s.id, keyword: editingKeyword.trim() }, {
                        onSuccess: () => { message.success('已更新'); setEditingSubId(null); },
                      });
                    }}>儲存</Button>
                  ) : (
                    <Button type="link" size="small" onClick={() => { setEditingSubId(s.id); setEditingKeyword(s.keyword); }}>編輯</Button>
                  )}
                  <Popconfirm title="取消訂閱？" onConfirm={() => deleteSub.mutate(s.id)}>
                    <Button type="link" size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </Space>
              }
            >
              {editingSubId === s.id ? (
                <Space style={{ width: '100%' }} onClick={e => e.stopPropagation()}>
                  <Input size="small" value={editingKeyword} onChange={e => setEditingKeyword(e.target.value)}
                    onPressEnter={() => {
                      if (!editingKeyword.trim()) return;
                      updateSub.mutate({ id: s.id, keyword: editingKeyword.trim() }, {
                        onSuccess: () => { message.success('已更新'); setEditingSubId(null); },
                      });
                    }}
                    style={{ width: 200 }} />
                  <Select size="small" value={s.category || ''} style={{ width: 100 }}
                    options={CATEGORY_OPTIONS}
                    onChange={(v) => updateSub.mutate({ id: s.id, category: v || '' })} />
                  <Button size="small" onClick={() => setEditingSubId(null)}>取消</Button>
                </Space>
              ) : (
                <div>
                  <Row justify="space-between" align="middle"
                    onClick={() => handleSubSearch(s.keyword)}
                    style={{ cursor: 'pointer' }}
                  >
                    <Col>
                      <Space>
                        <BellOutlined />
                        <strong>{s.keyword}</strong>
                        {s.category && <Tag>{s.category}</Tag>}
                        {!s.is_active && <Tag color="default">已停用</Tag>}
                      </Space>
                    </Col>
                    <Col>
                      <Space>
                        {s.last_diff > 0 && <Tag color="red">+{s.last_diff} 新增</Tag>}
                        <Tooltip title="點擊查看全部搜尋結果">
                          <Tag color="blue" style={{ cursor: 'pointer' }}>共 {s.last_count.toLocaleString()} 筆 →</Tag>
                        </Tooltip>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {s.last_checked_at
                            ? new Date(s.last_checked_at).toLocaleString('zh-TW', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                            : '等待排程'}
                        </Text>
                      </Space>
                    </Col>
                  </Row>
                  {s.last_new_titles?.length > 0 && (
                    <div style={{ marginTop: 8, paddingLeft: 22 }}>
                      {s.last_new_titles.slice(0, 3).map((title, i) => (
                        <div key={i} style={{ fontSize: 12, color: '#595959', marginBottom: 2 }}>
                          • {title}
                        </div>
                      ))}
                      {s.last_new_titles.length > 3 && (
                        <Text type="secondary" style={{ fontSize: 11 }}>...還有 {s.last_new_titles.length - 3} 筆</Text>
                      )}
                    </div>
                  )}
                </div>
              )}
            </Card>
          ))}
        </Flex>
      )}
    </div>
  );

  // ========== Tab 3: 收藏 ==========
  const bookmarkTab = (
    <div>
      {!bookmarks?.length ? <Empty description="在搜尋結果中點擊 ★ 即可收藏標案" /> : (
        <Table
          dataSource={bookmarks}
          rowKey="id"
          size="middle"
          pagination={false}
          onRow={(record) => ({
            onClick: () => navigate(`/tender/${encodeURIComponent(record.unit_id)}/${encodeURIComponent(record.job_number)}`),
            style: { cursor: 'pointer' },
          })}
          columns={[
            {
              title: '標案名稱', dataIndex: 'title', ellipsis: true,
              render: (title: string) => <Text strong>{title}</Text>,
            },
            {
              title: '招標機關', dataIndex: 'unit_name', width: 180, ellipsis: true,
              render: (v: string | null) => v && v !== '(未知機關)'
                ? <><BankOutlined style={{ marginRight: 4, color: '#8c8c8c' }} />{v}</>
                : <Text type="secondary">-</Text>,
            },
            {
              title: '狀態', dataIndex: 'status', width: 90, align: 'center' as const,
              render: (v: string) => <Tag color={BOOKMARK_STATUS_MAP[v]?.color}>{BOOKMARK_STATUS_MAP[v]?.label ?? v}</Tag>,
            },
            {
              title: '案號', dataIndex: 'case_code', width: 150,
              render: (v: string | null) => v ? <Tag color="green">{v}</Tag> : <Text type="secondary">-</Text>,
            },
            {
              title: '收藏時間', dataIndex: 'created_at', width: 110,
              render: (v: string | null) => v ? <Text type="secondary" style={{ fontSize: 12 }}>{new Date(v).toLocaleDateString('zh-TW')}</Text> : '-',
            },
            {
              title: '', key: 'action', width: 50, align: 'center' as const,
              render: (_: unknown, record) => (
                <Popconfirm title="移除收藏？" onConfirm={(e) => { e?.stopPropagation(); deleteBm.mutate(record.id); }}>
                  <Button type="text" size="small" danger icon={<DeleteOutlined />} onClick={e => e.stopPropagation()} />
                </Popconfirm>
              ),
            },
          ]}
        />
      )}
    </div>
  );

  return (
    <div style={{ padding: pagePadding }}>
      <Card size={isMobile ? 'small' : undefined} style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} align="middle" style={{ marginBottom: 12 }}>
          <Col flex="auto">
            <Space wrap>
              <Title level={isMobile ? 4 : 3} style={{ margin: 0 }}><SearchOutlined style={{ marginRight: 8 }} />標案檢索</Title>
              {!isMobile && (
                <>
                  <Button type="link" onClick={() => navigate(ROUTES.TENDER_DASHBOARD)}>採購儀表板</Button>
                  <Button type="link" onClick={() => navigate(ROUTES.TENDER_ORG_ECOSYSTEM)}>機關分析</Button>
                  <Button type="link" onClick={() => navigate(ROUTES.TENDER_COMPANY_PROFILE)}>廠商分析</Button>
                  <Button type="link" onClick={() => navigate(ROUTES.TENDER_GRAPH)}>標案圖譜</Button>
                </>
              )}
            </Space>
          </Col>
        </Row>
        <Row gutter={[12, 12]}>
          <Col xs={8} sm={6} md={4}>
            <ClickableStatCard title="搜尋結果" value={filteredData.length} icon={<SearchOutlined />} color="#1890ff" />
          </Col>
          <Col xs={8} sm={6} md={4}>
            <ClickableStatCard title="訂閱" value={subscriptions?.length ?? 0} icon={<BellOutlined />} color="#faad14"
              onClick={() => setActiveTab('subscriptions')} active={activeTab === 'subscriptions'} />
          </Col>
          <Col xs={8} sm={6} md={4}>
            <ClickableStatCard title="收藏" value={bookmarks?.length ?? 0} icon={<BookOutlined />} color="#52c41a"
              onClick={() => setActiveTab('bookmarks')} active={activeTab === 'bookmarks'} />
          </Col>
        </Row>
      </Card>

      <Card size={isMobile ? 'small' : undefined}>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
          { key: 'search', label: <><SearchOutlined /> 搜尋</>, children: searchTab },
          { key: 'subscriptions', label: <><BellOutlined /> 訂閱 <Badge count={subscriptions?.length ?? 0} size="small" offset={[4, -2]} /></>, children: subscriptionTab },
          { key: 'bookmarks', label: <><BookOutlined /> 收藏 <Badge count={bookmarks?.length ?? 0} size="small" offset={[4, -2]} /></>, children: bookmarkTab },
        ]} />
      </Card>
    </div>
  );
};

export default TenderSearchPage;

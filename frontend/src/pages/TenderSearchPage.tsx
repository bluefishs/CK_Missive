/**
 * 標案檢索頁面
 *
 * 三 Tab: 搜尋 / 訂閱 / 收藏
 * - 搜尋: 多模式 (標案/機關/廠商) + 招標類型客戶端篩選
 * - 訂閱: 關鍵字自動監控，點擊切換搜尋查看結果
 * - 收藏: 導航模式 Table，點擊跳轉詳情頁
 *
 * @version 4.0.0 - 拆分為 SearchTab / SubscriptionTab / BookmarkTab 子元件
 */
import React, { useState, useCallback, useMemo } from 'react';
import {
  Card, Space, Button, Typography, Row, Col, App, Tabs, Badge,
} from 'antd';
import {
  SearchOutlined, StarOutlined, CalendarOutlined,
  BellOutlined, BookOutlined,
} from '@ant-design/icons';
import { useResponsive } from '../hooks';
import { ClickableStatCard } from '../components/common';
import {
  useTenderSearch, useTenderRecommend,
  useTenderSubscriptions, useCreateSubscription, useDeleteSubscription, useUpdateSubscription,
  useTenderBookmarks, useCreateBookmark, useDeleteBookmark,
} from '../hooks/business/useTender';
import type { TenderRecord, TenderSearchParams } from '../types/tender';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/types';
import { SearchTab } from './tenderSearch';
import { SubscriptionTab } from './tenderSearch';
import { BookmarkTab } from './tenderSearch';

const { Title } = Typography;

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
  const [categoryFilter, setCategoryFilter] = useState('');
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
    setParams({ query: q, page: 1, search_type: st, category: categoryFilter || undefined });
    setShowRecommend(false);
    setTypeFilter('');
  }, [message, searchType, categoryFilter]);

  const handleViewDetail = useCallback((record: TenderRecord) => {
    // ezbid 來源且無 job_number → 開 ezbid 詳情頁 (新分頁)
    if ((!record.job_number || record.job_number === '') && record.unit_id) {
      window.open(`https://cf.ezbid.tw/tender/${record.unit_id}`, '_blank');
      return;
    }
    navigate(`/tender/${encodeURIComponent(record.unit_id)}/${encodeURIComponent(record.job_number)}`);
  }, [navigate]);

  // 訂閱 → 搜尋 Tab 切換 (帶入關鍵字+類別)
  const handleSubSearch = useCallback((keyword: string, category?: string | null) => {
    setSearchInput(keyword);
    setSearchType('title');
    setCategoryFilter(category || '');
    setActiveTab('search');
    setParams({ query: keyword, page: 1, search_type: 'title', category: category || undefined });
    setShowRecommend(false);
    setTypeFilter('');
  }, []);

  // 收藏 toggle
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

  // 推薦模式切換
  const [recommendView, setRecommendView] = useState<'business' | 'today'>('business');

  // 搜尋結果 + 客戶端招標類型篩選
  const rawData = useMemo(() => {
    if (!showRecommend || params) return searchResult?.records ?? [];
    if (recommendView === 'today') return recommendResult?.today_records ?? [];
    return recommendResult?.records ?? [];
  }, [showRecommend, params, recommendView, searchResult, recommendResult]);
  const filteredData = useMemo(() => {
    if (!rawData) return [];
    if (!typeFilter) return rawData;
    return rawData.filter(r => r.type.includes(typeFilter));
  }, [rawData, typeFilter]);
  const displayTotal = showRecommend && !params ? recommendResult?.total : searchResult?.total_records;
  const isLoading = showRecommend && !params ? recommending : searching;

  // 收藏 row click handler
  const handleBookmarkRowClick = useCallback((record: { unit_id: string; job_number: string }) => {
    navigate(`/tender/${encodeURIComponent(record.unit_id)}/${encodeURIComponent(record.job_number)}`);
  }, [navigate]);

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
          {showRecommend && !params ? (
            <>
              <Col xs={8} sm={6} md={4}>
                <ClickableStatCard title="業務推薦" value={recommendResult?.records?.length ?? 0}
                  icon={<StarOutlined />} color="#722ed1"
                  active={recommendView === 'business'} onClick={() => setRecommendView('business')} />
              </Col>
              <Col xs={8} sm={6} md={4}>
                <ClickableStatCard title="今日最新" value={recommendResult?.today_records?.length ?? 0}
                  icon={<CalendarOutlined />} color="#eb2f96"
                  active={recommendView === 'today'} onClick={() => setRecommendView('today')} />
              </Col>
            </>
          ) : (
            <Col xs={8} sm={6} md={4}>
              <ClickableStatCard title="搜尋結果" value={filteredData.length} icon={<SearchOutlined />} color="#1890ff" />
            </Col>
          )}
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
          {
            key: 'search',
            label: <><SearchOutlined /> 搜尋</>,
            children: (
              <SearchTab
                searchInput={searchInput} setSearchInput={setSearchInput}
                searchType={searchType} setSearchType={setSearchType}
                categoryFilter={categoryFilter} setCategoryFilter={setCategoryFilter}
                typeFilter={typeFilter} setTypeFilter={setTypeFilter}
                params={params} setParams={setParams}
                showRecommend={showRecommend} setShowRecommend={setShowRecommend}
                recommendView={recommendView} recommendResult={recommendResult}
                filteredData={filteredData} displayTotal={displayTotal} isLoading={isLoading}
                bookmarkedKeys={bookmarkedKeys}
                handleSearch={handleSearch} handleViewDetail={handleViewDetail}
                handleToggleBookmark={handleToggleBookmark}
              />
            ),
          },
          {
            key: 'subscriptions',
            label: <><BellOutlined /> 訂閱 <Badge count={subscriptions?.length ?? 0} size="small" offset={[4, -2]} /></>,
            children: (
              <SubscriptionTab
                subscriptions={subscriptions} subKeyword={subKeyword} setSubKeyword={setSubKeyword}
                subCategory={subCategory} setSubCategory={setSubCategory}
                editingSubId={editingSubId} setEditingSubId={setEditingSubId}
                editingKeyword={editingKeyword} setEditingKeyword={setEditingKeyword}
                createSub={createSub} updateSub={updateSub} deleteSub={deleteSub}
                handleSubSearch={handleSubSearch} message={message}
              />
            ),
          },
          {
            key: 'bookmarks',
            label: <><BookOutlined /> 收藏 <Badge count={bookmarks?.length ?? 0} size="small" offset={[4, -2]} /></>,
            children: (
              <BookmarkTab
                bookmarks={bookmarks} deleteBm={deleteBm}
                onRowClick={handleBookmarkRowClick}
              />
            ),
          },
        ]} />
      </Card>
    </div>
  );
};

export default TenderSearchPage;

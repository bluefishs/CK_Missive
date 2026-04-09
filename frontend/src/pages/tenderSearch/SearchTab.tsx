/**
 * 搜尋 Tab - 多模式搜尋 (標案/機關/廠商) + 招標類型篩選
 */
import React from 'react';
import {
  Input, Tag, Select, Button, Typography, Row, Col, Tooltip,
} from 'antd';
import {
  StarOutlined, StarFilled, BankOutlined,
  ReloadOutlined, FilterOutlined,
} from '@ant-design/icons';
import type { TenderRecord, TenderSearchParams, TenderRecommendResult } from '../../types/tender';
import type { ColumnsType } from 'antd/es/table';
import { EnhancedTable } from '../../components/common/EnhancedTable';

const { Text } = Typography;

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

export interface SearchTabProps {
  searchInput: string;
  setSearchInput: (v: string) => void;
  searchType: 'title' | 'org' | 'company';
  setSearchType: (v: 'title' | 'org' | 'company') => void;
  categoryFilter: string;
  setCategoryFilter: (v: string) => void;
  typeFilter: string;
  setTypeFilter: (v: string) => void;
  params: TenderSearchParams | null;
  setParams: React.Dispatch<React.SetStateAction<TenderSearchParams | null>>;
  showRecommend: boolean;
  setShowRecommend: (v: boolean) => void;
  recommendView: 'business' | 'today';
  recommendResult: TenderRecommendResult | undefined;
  filteredData: TenderRecord[];
  displayTotal: number | undefined;
  isLoading: boolean;
  bookmarkedKeys: Set<string>;
  handleSearch: (value: string, type?: 'title' | 'org' | 'company') => void;
  handleViewDetail: (record: TenderRecord) => void;
  handleToggleBookmark: (record: TenderRecord) => void;
}

const SearchTab: React.FC<SearchTabProps> = ({
  searchInput, setSearchInput, searchType, setSearchType,
  categoryFilter, setCategoryFilter, typeFilter, setTypeFilter,
  params, setParams, showRecommend, setShowRecommend,
  recommendView, recommendResult,
  filteredData, displayTotal, isLoading,
  bookmarkedKeys, handleSearch, handleViewDetail, handleToggleBookmark,
}) => {
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

  return (
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
            value={searchInput}
            onChange={e => { setSearchInput(e.target.value); if (!e.target.value) { setParams(null); setShowRecommend(true); setTypeFilter(''); } }}
            onSearch={(v) => handleSearch(v)} allowClear
          />
        </Col>
        <Col xs={12} sm={4} md={3}>
          <Select style={{ width: '100%' }} size="large" options={CATEGORY_OPTIONS} value={categoryFilter}
            onChange={(v) => { setCategoryFilter(v); if (params?.query) setParams(p => p ? { ...p, category: v || undefined, page: 1 } : null); }}
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
          <Button icon={<ReloadOutlined />} size="large" onClick={() => {
            if (params) { setParams({ ...params }); }
            else { setParams(null); setShowRecommend(true); setSearchInput(''); setCategoryFilter(''); setTypeFilter(''); }
          }}>{params ? '重新搜尋' : '重新整理'}</Button>
        </Col>
      </Row>
      {showRecommend && !params && recommendResult && (
        <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>
          {recommendView === 'business'
            ? `依訂閱關鍵字推薦 (${(recommendResult.keywords ?? []).slice(0, 3).join('、')})`
            : '今日最新公告 (ezbid 即時)'}
        </Text>
      )}
      {typeFilter && <Tag closable onClose={() => setTypeFilter('')} color="blue" style={{ marginBottom: 8 }}>類型篩選: {typeFilter}</Tag>}
      <EnhancedTable<TenderRecord> columns={columns} dataSource={filteredData} rowKey={(r) => `${r.unit_id}-${r.job_number}-${r.raw_date}`}
        loading={isLoading} size="middle" scroll={{ x: 900 }}
        pagination={params ? { current: params.page ?? 1, pageSize: 100, total: typeFilter ? filteredData.length : (displayTotal ?? 0),
          onChange: (p) => { if (!typeFilter) setParams(prev => prev ? { ...prev, page: p } : null); }, showTotal: (t) => `共 ${t.toLocaleString()} 筆`, showSizeChanger: false } : false}
        onRow={record => ({ onClick: () => handleViewDetail(record), style: { cursor: 'pointer' } })}
      />
    </div>
  );
};

export default SearchTab;

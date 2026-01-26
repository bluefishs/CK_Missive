import React, { useState, useRef, useMemo } from 'react';
import type { InputRef, TableColumnType } from 'antd';
import type { FilterDropdownProps } from 'antd/es/table/interface';
import {
  Typography,
  Table,
  Input,
  Button,
  Space,
  Card,
  Statistic,
  Row,
  Col,
  Tag,
  App,
  Select,
  Pagination,
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  BankOutlined,
  BuildOutlined,
  TeamOutlined,
  BookOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import Highlighter from 'react-highlight-words';
import { useAgenciesPage } from '../hooks';
import { useResponsive } from '../hooks';
import type { AgencyWithStats } from '../api';
import { ROUTES } from '../router/types';
import { AGENCY_CATEGORY_OPTIONS } from '../constants';

const { Title, Text } = Typography;
const { Search } = Input;

type DataIndex = keyof AgencyWithStats;

export const AgenciesPage: React.FC = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();

  // 響應式設計
  const { isMobile, isTablet, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  // UI 狀態
  const [searchText, setSearchText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  // 欄位搜尋狀態
  const [columnSearchText, setColumnSearchText] = useState('');
  const [searchedColumn, setSearchedColumn] = useState('');
  const searchInput = useRef<InputRef>(null);

  // 構建查詢參數
  const queryParams = useMemo(() => ({
    page: currentPage,
    limit: pageSize,
    ...(searchText && { search: searchText }),
    ...(categoryFilter && { category: categoryFilter }),
    include_stats: true,
  }), [currentPage, pageSize, searchText, categoryFilter]);

  // 使用 React Query Hook
  const {
    agencies,
    pagination,
    isLoading,
    statistics,
    refetch,
    refetchStatistics,
  } = useAgenciesPage(queryParams);

  const totalAgencies = pagination?.total ?? 0;

  // 欄位搜尋功能
  const handleColumnSearch = (
    selectedKeys: string[],
    confirm: FilterDropdownProps['confirm'],
    dataIndex: DataIndex,
  ) => {
    confirm();
    setColumnSearchText(selectedKeys[0] ?? '');
    setSearchedColumn(dataIndex);
  };

  const handleColumnReset = (clearFilters: () => void) => {
    clearFilters();
    setColumnSearchText('');
  };

  // 取得欄位搜尋屬性
  const getColumnSearchProps = (dataIndex: DataIndex): TableColumnType<AgencyWithStats> => ({
    filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters, close }) => (
      <div style={{ padding: 8 }} onKeyDown={(e) => e.stopPropagation()}>
        <Input
          ref={searchInput}
          placeholder={`搜尋...`}
          value={selectedKeys[0]}
          onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
          onPressEnter={() => handleColumnSearch(selectedKeys as string[], confirm, dataIndex)}
          style={{ marginBottom: 8, display: 'block' }}
        />
        <Space>
          <Button
            type="primary"
            onClick={() => handleColumnSearch(selectedKeys as string[], confirm, dataIndex)}
            icon={<SearchOutlined />}
            size="small"
            style={{ width: 90 }}
          >
            搜尋
          </Button>
          <Button
            onClick={() => clearFilters && handleColumnReset(clearFilters)}
            size="small"
            style={{ width: 90 }}
          >
            重置
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => close()}
          >
            關閉
          </Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered: boolean) => (
      <SearchOutlined style={{ color: filtered ? '#1677ff' : undefined }} />
    ),
    onFilter: (value, record) =>
      record[dataIndex]
        ?.toString()
        .toLowerCase()
        .includes((value as string).toLowerCase()) ?? false,
    filterDropdownProps: {
      onOpenChange(open) {
        if (open) {
          setTimeout(() => searchInput.current?.select(), 100);
        }
      },
    },
    render: (text) =>
      searchedColumn === dataIndex ? (
        <Highlighter
          highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
          searchWords={[columnSearchText]}
          autoEscape
          textToHighlight={text ? text.toString() : ''}
        />
      ) : (
        text
      ),
  });

  // 搜尋處理
  const handleSearch = (value: string) => {
    setSearchText(value);
    setCurrentPage(1);
  };

  // 重新載入
  const handleRefresh = () => {
    setSearchText('');
    setCategoryFilter('');
    setCurrentPage(1);
    refetch();
    refetchStatistics();
  };

  // 分頁處理
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  // 新增機關 - 導航至表單頁
  const handleAdd = () => {
    navigate(ROUTES.AGENCY_CREATE);
  };

  // 編輯機關 - 導航至表單頁
  const handleEdit = (agency: AgencyWithStats) => {
    navigate(ROUTES.AGENCY_EDIT.replace(':id', String(agency.id)));
  };

  // 刪除功能已移至 AgencyFormPage (導航模式規範)

  // 獲取類型標籤顏色
  const getTypeTagColor = (type: string) => {
    switch (type) {
      case 'sender': return 'blue';
      case 'receiver': return 'green';
      case 'both': return 'purple';
      default: return 'default';
    }
  };

  // 獲取類型文字
  const getTypeText = (type: string) => {
    switch (type) {
      case 'sender': return '發文機關';
      case 'receiver': return '收文機關';
      case 'both': return '收發文機關';
      default: return '未知';
    }
  };

  // 獲取分類圖示（三大分類）
  const getCategoryIcon = (category: string) => {
    switch (category) {
      case '政府機關': return <BankOutlined />;
      case '民間企業': return <BuildOutlined />;
      case '其他單位': return <TeamOutlined />;
      // 相容舊分類
      case '其他機關': return <TeamOutlined />;
      case '社會團體': return <TeamOutlined />;
      case '教育機構': return <BookOutlined />;
      default: return <TeamOutlined />;
    }
  };

  // 表格欄位定義 - 含排序與篩選功能（響應式）
  // 導航模式：刪除功能已整合至 AgencyFormPage
  const columns: TableColumnType<AgencyWithStats>[] = isMobile
    ? [
        // 手機版：簡化欄位
        {
          title: '機關資訊',
          dataIndex: 'agency_name',
          key: 'agency_name',
          render: (text: string, record: AgencyWithStats) => (
            <div>
              <div style={{ fontWeight: 500 }}>{text}</div>
              {record.agency_short_name && (
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  簡稱: {record.agency_short_name}
                </Text>
              )}
              <div style={{ marginTop: 4 }}>
                <Tag icon={getCategoryIcon(record.category || '')} color="blue" style={{ fontSize: '11px' }}>
                  {['其他機關', '教育機構', '社會團體'].includes(record.category || '') ? '其他單位' : record.category}
                </Tag>
              </div>
            </div>
          ),
        },
      ]
    : [
        // 桌面版：完整欄位
        {
          title: '機關名稱',
          dataIndex: 'agency_name',
          key: 'agency_name',
          width: 280,
          sorter: (a, b) => a.agency_name.localeCompare(b.agency_name, 'zh-TW'),
          ...getColumnSearchProps('agency_name'),
          render: (text: string, record: AgencyWithStats) => (
            <div>
              <div style={{ fontWeight: 500 }}>
                {searchedColumn === 'agency_name' ? (
                  <Highlighter
                    highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
                    searchWords={[columnSearchText]}
                    autoEscape
                    textToHighlight={text || ''}
                  />
                ) : text}
              </div>
              {record.agency_short_name && (
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  簡稱: {record.agency_short_name}
                </Text>
              )}
            </div>
          ),
        },
        {
          title: '機關代碼',
          dataIndex: 'agency_code',
          key: 'agency_code',
          width: 120,
          align: 'center' as const,
          ...getColumnSearchProps('agency_code'),
          render: (code: string) => code || <Text type="secondary">-</Text>,
        },
        {
          title: '分類',
          dataIndex: 'category',
          key: 'category',
          width: 120,
          align: 'center' as const,
          filters: [
            { text: '政府機關', value: '政府機關' },
            { text: '民間企業', value: '民間企業' },
            { text: '其他單位', value: '其他單位' },
            // 相容舊分類資料
            { text: '其他機關', value: '其他機關' },
            { text: '教育機構', value: '教育機構' },
            { text: '社會團體', value: '社會團體' },
          ],
          onFilter: (value, record) => record.category === value,
          render: (category: string) => {
            // 將舊分類映射到新分類顯示（其他機關/教育機構/社會團體 → 其他單位）
            const displayCategory = ['其他機關', '教育機構', '社會團體'].includes(category) ? '其他單位' : category;
            return (
              <Tag icon={getCategoryIcon(category)} color="blue">
                {displayCategory}
              </Tag>
            );
          },
        },
    // 註解隱藏: 機關類型 (primary_type) - 因公文尚未關聯機關ID，目前無法判斷發文/收文機關
    // {
    //   title: '機關類型',
    //   dataIndex: 'primary_type',
    //   key: 'primary_type',
    //   width: 100,
    //   render: (type: string) => <Tag color={getTypeTagColor(type)}>{getTypeText(type)}</Tag>,
    // },
    // 註解隱藏: 聯絡人、電話、Email - 機關對應窗口眾多，並非單一人
    // {
    //   title: '聯絡人',
    //   dataIndex: 'contact_person',
    //   key: 'contact_person',
    //   width: 100,
    //   render: (person: string) => person || <Text type="secondary">-</Text>,
    // },
    // {
    //   title: '電話',
    //   dataIndex: 'phone',
    //   key: 'phone',
    //   width: 130,
    //   render: (phone: string) => phone || <Text type="secondary">-</Text>,
    // },
    // {
    //   title: 'Email',
    //   dataIndex: 'email',
    //   key: 'email',
    //   width: 180,
    //   ellipsis: true,
    //   render: (email: string) =>
    //     email ? <a href={`mailto:${email}`}>{email}</a> : <Text type="secondary">-</Text>,
    // },
    // 註解隱藏: 公文統計欄位 - 因 documents 表的 sender_agency_id/receiver_agency_id 尚未建立關聯
    // 待資料關聯完成後可取消註解
    // {
    //   title: '公文總數',
    //   dataIndex: 'document_count',
    //   key: 'document_count',
    //   width: 90,
    //   align: 'center' as const,
    //   sorter: (a, b) => a.document_count - b.document_count,
    // },
    // {
    //   title: '發文數',
    //   dataIndex: 'sent_count',
    //   key: 'sent_count',
    //   width: 80,
    //   align: 'center' as const,
    // },
    // {
    //   title: '收文數',
    //   dataIndex: 'received_count',
    //   key: 'received_count',
    //   width: 80,
    //   align: 'center' as const,
    // },
    // {
    //   title: '最後活動',
    //   dataIndex: 'last_activity',
    //   key: 'last_activity',
    //   width: 110,
    //   render: (date: string | null) =>
    //     date ? new Date(date).toLocaleDateString('zh-TW') : <Text type="secondary">-</Text>,
    // },
    {
      title: '建立日期',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 110,
      sorter: (a, b) => new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime(),
      render: (date: string) =>
        date ? new Date(date).toLocaleDateString('zh-TW') : '-',
    },
    // 導航模式：刪除功能已整合至 AgencyFormPage
  ];

  // 機關列表（現在由後端篩選，不需要前端再篩選）
  const filteredAgencies = agencies;

  return (
    <div style={{ padding: pagePadding }}>
      <div style={{ marginBottom: isMobile ? 16 : 24 }}>
        <Title level={isMobile ? 4 : 2}>
          <BankOutlined style={{ marginRight: isMobile ? 8 : 12, color: '#1890ff' }} />
          {isMobile ? '機關管理' : '機關單位管理'}
        </Title>
        {!isMobile && (
          <Text type="secondary">
            統計和管理公文往來的所有機關單位資訊
          </Text>
        )}
      </div>

      {/* 統計卡片 - 響應式：手機2列、平板/桌面4列 */}
      {statistics && (
        <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]} style={{ marginBottom: isMobile ? 16 : 24 }}>
          <Col xs={12} sm={6}>
            <Card size={isMobile ? 'small' : 'default'}>
              <Statistic
                title={isMobile ? '總數' : '機關總數'}
                value={statistics.total_agencies}
                prefix={<BankOutlined />}
                valueStyle={{ color: '#3f8600', fontSize: isMobile ? 20 : 24 }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size={isMobile ? 'small' : 'default'}>
              <Statistic
                title="政府機關"
                value={statistics.categories.find(c => c.category === '政府機關')?.count || 0}
                suffix={!isMobile ? `(${statistics.categories.find(c => c.category === '政府機關')?.percentage || 0}%)` : undefined}
                prefix={<BankOutlined />}
                valueStyle={{ color: '#1890ff', fontSize: isMobile ? 20 : 24 }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size={isMobile ? 'small' : 'default'}>
              <Statistic
                title="民間企業"
                value={statistics.categories.find(c => c.category === '民間企業')?.count || 0}
                suffix={!isMobile ? `(${statistics.categories.find(c => c.category === '民間企業')?.percentage || 0}%)` : undefined}
                prefix={<BuildOutlined />}
                valueStyle={{ color: '#722ed1', fontSize: isMobile ? 20 : 24 }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size={isMobile ? 'small' : 'default'}>
              <Statistic
                title="其他單位"
                value={
                  (statistics.categories.find(c => c.category === '其他機關')?.count || 0) +
                  (statistics.categories.find(c => c.category === '其他單位')?.count || 0) +
                  (statistics.categories.find(c => c.category === '社會團體')?.count || 0) +
                  (statistics.categories.find(c => c.category === '教育機構')?.count || 0)
                }
                prefix={<TeamOutlined />}
                valueStyle={{ color: '#fa541c', fontSize: isMobile ? 20 : 24 }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 搜尋和篩選 - 響應式 */}
      <Card style={{ marginBottom: isMobile ? 12 : 24 }} size={isMobile ? 'small' : 'default'}>
        <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 0]} align="middle">
          <Col xs={24} sm={24} md={10} lg={8}>
            <Search
              placeholder={isMobile ? '搜尋機關...' : '搜尋機關名稱...'}
              allowClear
              enterButton={<SearchOutlined />}
              size={isMobile ? 'middle' : 'large'}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onSearch={handleSearch}
              style={{ width: '100%' }}
            />
          </Col>
          {!isMobile && (
            <Col xs={12} sm={8} md={6} lg={4}>
              <Select
                placeholder="選擇機關類別"
                allowClear
                value={categoryFilter || undefined}
                onChange={(value) => {
                  setCategoryFilter(value || '');
                  setCurrentPage(1);  // 切換分類時重置頁碼
                }}
                style={{ width: '100%' }}
                options={AGENCY_CATEGORY_OPTIONS.map(opt => ({
                  label: opt.label,
                  value: opt.value,
                }))}
              />
            </Col>
          )}
          <Col xs={24} sm={24} md={8} lg={12} style={{ textAlign: isMobile ? 'left' : 'right' }}>
            <Space wrap size={isMobile ? 'small' : 'middle'}>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleRefresh}
                loading={isLoading}
                size={isMobile ? 'small' : 'middle'}
              >
                {isMobile ? '' : '重新載入'}
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleAdd}
                size={isMobile ? 'small' : 'middle'}
              >
                {isMobile ? '新增' : '新增機關'}
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 機關列表 - 響應式 */}
      <Card size={isMobile ? 'small' : 'default'}>
        <Table
          columns={columns}
          dataSource={filteredAgencies}
          rowKey="id"
          loading={isLoading}
          pagination={false}
          scroll={{ x: isMobile ? 300 : 700 }}
          size={isMobile ? 'small' : 'middle'}
          tableLayout="fixed"
          onRow={(record) => ({
            onClick: () => handleEdit(record),
            style: { cursor: 'pointer' },
          })}
          style={{ marginBottom: isMobile ? 8 : 16 }}
        />

        {/* 自訂分頁 - 響應式 */}
        <div style={{ textAlign: 'center', marginTop: isMobile ? 8 : 16 }}>
          <Pagination
            current={currentPage}
            total={totalAgencies}
            pageSize={pageSize}
            showSizeChanger={false}
            showQuickJumper={!isMobile}
            size={isMobile ? 'small' : 'default'}
            showTotal={isMobile
              ? (total) => `共 ${total} 項`
              : (total, range) => `第 ${range[0]}-${range[1]} 項，共 ${total} 個機關`
            }
            onChange={handlePageChange}
          />
        </div>
      </Card>
    </div>
  );
};

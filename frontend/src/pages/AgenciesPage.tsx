import React, { useState, useEffect } from 'react';
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
} from '@ant-design/icons';
import { API_BASE_URL } from '../api/config';

const { Title, Text } = Typography;
const { Search } = Input;

interface Agency {
  id: number;
  name: string;
  agency_code?: string;
  document_count: number;
  sent_count: number;
  received_count: number;
  last_activity: string | null;
  primary_type: 'sender' | 'receiver' | 'both';
  category: string;
  original_names?: string[];
}

interface AgenciesResponse {
  agencies: Agency[];
  total: number;
  returned: number;
  search?: string;
}

interface CategoryStat {
  category: string;
  count: number;
  percentage: number;
}

interface Statistics {
  total_agencies: number;
  categories: CategoryStat[];
}

export const AgenciesPage: React.FC = () => {
  const { message } = App.useApp();
  
  const [agencies, setAgencies] = useState<Agency[]>([]);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [totalAgencies, setTotalAgencies] = useState(0);

  // 載入機關單位列表
  const fetchAgencies = async (search?: string, page = 1) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit: pageSize.toString(),
        include_stats: 'true',  // 機關管理頁面需要統計數據
      });

      if (search) {
        params.append('search', search);
      }

      const response = await fetch(`${API_BASE_URL}/agencies/?${params}`);
      if (!response.ok) {
        throw new Error('載入機關單位失敗');
      }

      const data: AgenciesResponse = await response.json();
      console.log('=== API Response ===', data);
      setAgencies(data.agencies);
      setTotalAgencies(data.total);
    } catch (error) {
      console.error('載入機關單位錯誤:', error);
      message.error('載入機關單位失敗');
    } finally {
      setLoading(false);
    }
  };

  // 載入統計資料
  const fetchStatistics = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/agencies/statistics`);
      if (!response.ok) {
        throw new Error('載入統計資料失敗');
      }

      const data: Statistics = await response.json();
      setStatistics(data);
    } catch (error) {
      console.error('載入統計資料錯誤:', error);
      message.error('載入統計資料失敗');
    }
  };

  useEffect(() => {
    fetchAgencies();
    fetchStatistics();
  }, []);

  // 搜尋處理
  const handleSearch = (value: string) => {
    setSearchText(value);
    setCurrentPage(1);
    fetchAgencies(value, 1);
  };

  // 重新載入
  const handleRefresh = () => {
    setSearchText('');
    setCategoryFilter('');
    setCurrentPage(1);
    fetchAgencies();
    fetchStatistics();
  };

  // 分頁處理
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    fetchAgencies(searchText, page);
  };

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

  // 獲取分類圖示
  const getCategoryIcon = (category: string) => {
    switch (category) {
      case '政府機關': return <BankOutlined />;
      case '民間企業': return <BuildOutlined />;
      case '社會團體': return <TeamOutlined />;
      case '教育機構': return <BookOutlined />;
      default: return <BankOutlined />;
    }
  };

  // 表格欄位定義
  const columns = [
    {
      title: '機關名稱',
      dataIndex: 'name',
      key: 'name',
      width: '30%',
      render: (text: string, record: Agency) => (
        <div>
          <div style={{ fontWeight: 500 }}>{text}</div>
          <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
            {getCategoryIcon(record.category)}
            <span style={{ marginLeft: '6px' }}>{record.category}</span>
            {record.agency_code && (
              <span style={{ marginLeft: '8px', color: '#999' }}>
                代碼: {record.agency_code}
              </span>
            )}
          </div>
        </div>
      ),
    },
    {
      title: '機關類型',
      dataIndex: 'primary_type',
      key: 'primary_type',
      width: '15%',
      render: (type: string) => (
        <Tag color={getTypeTagColor(type)}>
          {getTypeText(type)}
        </Tag>
      ),
    },
    {
      title: '公文總數',
      dataIndex: 'document_count',
      key: 'document_count',
      width: '12%',
      align: 'center' as const,
      sorter: (a: Agency, b: Agency) => a.document_count - b.document_count,
    },
    {
      title: '發文數',
      dataIndex: 'sent_count',
      key: 'sent_count',
      width: '10%',
      align: 'center' as const,
      sorter: (a: Agency, b: Agency) => a.sent_count - b.sent_count,
    },
    {
      title: '收文數',
      dataIndex: 'received_count',
      key: 'received_count',
      width: '10%',
      align: 'center' as const,
      sorter: (a: Agency, b: Agency) => a.received_count - b.received_count,
    },
    {
      title: '最後活動',
      dataIndex: 'last_activity',
      key: 'last_activity',
      width: '15%',
      render: (date: string | null) =>
        date ? new Date(date).toLocaleDateString('zh-TW') : '無紀錄',
    },
  ];

  // 篩選後的機關列表
  const filteredAgencies = categoryFilter
    ? agencies.filter(agency => agency.category === categoryFilter)
    : agencies;

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <Title level={2}>
          <BankOutlined style={{ marginRight: '12px', color: '#1890ff' }} />
          機關單位管理
        </Title>
        <Text type="secondary">
          統計和管理公文往來的所有機關單位資訊
        </Text>
      </div>

      {/* 統計卡片 */}
      {statistics && (
        <Row gutter={16} style={{ marginBottom: '24px' }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="機關總數"
                value={statistics.total_agencies}
                prefix={<BankOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          {statistics.categories.slice(0, 3).map((cat, index) => (
            <Col span={6} key={cat.category}>
              <Card>
                <Statistic
                  title={cat.category}
                  value={cat.count}
                  suffix={`(${cat.percentage}%)`}
                  prefix={getCategoryIcon(cat.category)}
                  valueStyle={{ color: ['#1890ff', '#722ed1', '#fa541c'][index] }}
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* 搜尋和篩選 */}
      <Card style={{ marginBottom: '24px' }}>
        <Row gutter={16} align="middle">
          <Col flex="1">
            <Search
              placeholder="搜尋機關名稱..."
              allowClear
              enterButton={<SearchOutlined />}
              size="large"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onSearch={handleSearch}
              style={{ maxWidth: '400px' }}
            />
          </Col>
          <Col>
            <Select
              placeholder="選擇機關類別"
              allowClear
              value={categoryFilter || undefined}
              onChange={setCategoryFilter}
              style={{ width: '160px' }}
              options={statistics?.categories.map(cat => ({
                label: `${cat.category} (${cat.count})`,
                value: cat.category,
              })) || []}
            />
          </Col>
          <Col>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
              loading={loading}
            >
              重新載入
            </Button>
          </Col>
        </Row>
      </Card>

      {/* 機關列表 */}
      <Card>
        <Table
          columns={columns}
          dataSource={filteredAgencies}
          rowKey="id"
          loading={loading}
          pagination={false}
          scroll={{ x: 1000 }}
          size="middle"
          style={{ marginBottom: '16px' }}
        />
        
        {/* 自訂分頁 */}
        <div style={{ textAlign: 'center', marginTop: '16px' }}>
          <Pagination
            current={currentPage}
            total={totalAgencies}
            pageSize={pageSize}
            showSizeChanger={false}
            showQuickJumper
            showTotal={(total, range) => 
              `第 ${range[0]}-${range[1]} 項，共 ${total} 個機關`
            }
            onChange={handlePageChange}
          />
        </div>
      </Card>
    </div>
  );
};
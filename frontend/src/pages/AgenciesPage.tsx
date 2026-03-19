import React, { useState, useMemo } from 'react';
import {
  Typography,
  Input,
  Button,
  Space,
  Card,
  Statistic,
  Row,
  Col,
  Select,
  Pagination,
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  BankOutlined,
  BuildOutlined,
  TeamOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { ResponsiveTable } from '../components/common';
import { useAgenciesPage } from '../hooks';
import { useResponsive } from '../hooks';
import { ROUTES } from '../router/types';
import { AGENCY_CATEGORY_OPTIONS } from '../constants';
import { useAgenciesColumns } from './useAgenciesColumns';
import type { AgencyWithStats } from '../api';

const { Title, Text } = Typography;
const { Search } = Input;

export const AgenciesPage: React.FC = () => {
  const navigate = useNavigate();
  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  const [searchText, setSearchText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  const queryParams = useMemo(() => ({
    page: currentPage,
    limit: pageSize,
    ...(searchText && { search: searchText }),
    ...(categoryFilter && { category: categoryFilter }),
    include_stats: true,
  }), [currentPage, pageSize, searchText, categoryFilter]);

  const {
    agencies,
    pagination,
    isLoading,
    statistics,
    refetch,
    refetchStatistics,
  } = useAgenciesPage(queryParams);

  const totalAgencies = pagination?.total ?? 0;
  const { columns } = useAgenciesColumns(isMobile);

  const handleSearch = (value: string) => {
    setSearchText(value);
    setCurrentPage(1);
  };

  const handleRefresh = () => {
    setSearchText('');
    setCategoryFilter('');
    setCurrentPage(1);
    refetch();
    refetchStatistics();
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleAdd = () => {
    navigate(ROUTES.AGENCY_CREATE);
  };

  const handleEdit = (agency: AgencyWithStats) => {
    navigate(ROUTES.AGENCY_EDIT.replace(':id', String(agency.id)));
  };

  const filteredAgencies = agencies;

  return (
    <div style={{ padding: pagePadding }}>
      <div style={{ marginBottom: isMobile ? 16 : 24 }}>
        <Title level={isMobile ? 4 : 2}>
          <BankOutlined style={{ marginRight: isMobile ? 8 : 12, color: '#1890ff' }} />
          {isMobile ? '機關管理' : '機關單位管理'}
        </Title>
        {!isMobile && (
          <Text type="secondary">統計和管理公文往來的所有機關單位資訊</Text>
        )}
      </div>

      {/* 統計卡片 */}
      {statistics && (
        <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]} style={{ marginBottom: isMobile ? 16 : 24 }}>
          <Col xs={12} sm={6}>
            <Card size={isMobile ? 'small' : undefined}>
              <Statistic
                title={isMobile ? '總數' : '機關總數'}
                value={statistics.total_agencies}
                prefix={<BankOutlined />}
                styles={{ content: { color: '#3f8600', fontSize: isMobile ? 20 : 24 } }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size={isMobile ? 'small' : undefined}>
              <Statistic
                title="政府機關"
                value={statistics.categories.find(c => c.category === '政府機關')?.count || 0}
                suffix={!isMobile ? `(${statistics.categories.find(c => c.category === '政府機關')?.percentage || 0}%)` : undefined}
                prefix={<BankOutlined />}
                styles={{ content: { color: '#1890ff', fontSize: isMobile ? 20 : 24 } }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size={isMobile ? 'small' : undefined}>
              <Statistic
                title="民間企業"
                value={statistics.categories.find(c => c.category === '民間企業')?.count || 0}
                suffix={!isMobile ? `(${statistics.categories.find(c => c.category === '民間企業')?.percentage || 0}%)` : undefined}
                prefix={<BuildOutlined />}
                styles={{ content: { color: '#722ed1', fontSize: isMobile ? 20 : 24 } }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size={isMobile ? 'small' : undefined}>
              <Statistic
                title="其他單位"
                value={
                  (statistics.categories.find(c => c.category === '其他機關')?.count || 0) +
                  (statistics.categories.find(c => c.category === '其他單位')?.count || 0) +
                  (statistics.categories.find(c => c.category === '社會團體')?.count || 0) +
                  (statistics.categories.find(c => c.category === '教育機構')?.count || 0)
                }
                prefix={<TeamOutlined />}
                styles={{ content: { color: '#fa541c', fontSize: isMobile ? 20 : 24 } }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 搜尋和篩選 */}
      <Card style={{ marginBottom: isMobile ? 12 : 24 }} size={isMobile ? 'small' : undefined}>
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
                placeholder="選擇機關類別" allowClear
                value={categoryFilter || undefined}
                onChange={(value) => { setCategoryFilter(value || ''); setCurrentPage(1); }}
                style={{ width: '100%' }}
                options={AGENCY_CATEGORY_OPTIONS.map(opt => ({ label: opt.label, value: opt.value }))}
              />
            </Col>
          )}
          <Col xs={24} sm={24} md={8} lg={12} style={{ textAlign: isMobile ? 'left' : 'right' }}>
            <Space wrap size={isMobile ? 'small' : 'middle'}>
              <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={isLoading} size={isMobile ? 'small' : 'middle'}>
                {isMobile ? '' : '重新載入'}
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd} size={isMobile ? 'small' : 'middle'}>
                {isMobile ? '新增' : '新增機關'}
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 機關列表 */}
      <Card size={isMobile ? 'small' : undefined}>
        <ResponsiveTable
          columns={columns}
          dataSource={filteredAgencies}
          rowKey="id"
          loading={isLoading}
          pagination={false}
          scroll={{ x: isMobile ? 300 : 700 }}
          mobileHiddenColumns={['agency_code', 'created_at']}
          tableLayout="fixed"
          onRow={(record) => ({
            onClick: () => handleEdit(record),
            style: { cursor: 'pointer' },
          })}
          style={{ marginBottom: isMobile ? 8 : 16 }}
        />

        <div style={{ textAlign: 'center', marginTop: isMobile ? 8 : 16 }}>
          <Pagination
            current={currentPage}
            total={totalAgencies}
            pageSize={pageSize}
            showSizeChanger={false}
            showQuickJumper={!isMobile}
            size={isMobile ? 'small' : undefined}
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

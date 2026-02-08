import React, { useState, useMemo } from 'react';
import {
  Button,
  Input,
  Space,
  Card,
  App,
  Select,
  Typography,
  Tag,
  Row,
  Col,
  Statistic
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  UserOutlined,
  PhoneOutlined,
  MailOutlined,
  ShopOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { TableColumnType } from 'antd';
import { ResponsiveTable } from '../common';
import { useVendorsPage } from '../../hooks';
import { useResponsive } from '../../hooks';
import type { Vendor as ApiVendor } from '../../types/api';
import { ROUTES } from '../../router/types';
import {
  BUSINESS_TYPE_OPTIONS,
  getBusinessTypeColor,
  getRatingColor,
} from '../../constants';

const { Title } = Typography;
const { Option } = Select;

// 使用統一型別定義
type Vendor = ApiVendor;

const VendorList: React.FC = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  // UI 狀態
  const [current, setCurrent] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [searchText, setSearchText] = useState('');
  const [businessTypeFilter, setBusinessTypeFilter] = useState<string>('');
  const [ratingFilter, setRatingFilter] = useState<number | undefined>();

  // 構建查詢參數
  const queryParams = useMemo(() => ({
    page: current,
    limit: pageSize,
    ...(searchText && { search: searchText }),
    ...(businessTypeFilter && { business_type: businessTypeFilter }),
    ...(ratingFilter && { rating: ratingFilter }),
  }), [current, pageSize, searchText, businessTypeFilter, ratingFilter]);

  // 使用 React Query Hook (自動快取與更新)
  const {
    vendors,
    pagination,
    isLoading,
    isError,
  } = useVendorsPage(queryParams);

  const total = pagination?.total ?? 0;

  // 新增廠商 - 導航至表單頁
  const handleAdd = () => {
    navigate(ROUTES.VENDOR_CREATE);
  };

  // 編輯廠商 - 導航至表單頁
  const handleEdit = (vendor: Vendor) => {
    navigate(ROUTES.VENDOR_EDIT.replace(':id', String(vendor.id)));
  };

  // 刪除功能已移至 VendorFormPage (導航模式規範)

  // 響應式表格欄位 (導航模式：刪除功能已整合至 VendorFormPage)
  const columns: TableColumnType<Vendor>[] = isMobile
    ? [
        {
          title: '廠商',
          dataIndex: 'vendor_name',
          key: 'vendor_name',
          render: (text: string, record: Vendor) => (
            <Space direction="vertical" size={0}>
              <strong>{text}</strong>
              {record.contact_person && <small><UserOutlined /> {record.contact_person}</small>}
              {record.business_type && <Tag color={getBusinessTypeColor(record.business_type)}>{record.business_type}</Tag>}
            </Space>
          ),
        },
      ]
    : [
        {
          title: '廠商名稱',
          dataIndex: 'vendor_name',
          key: 'vendor_name',
          sorter: (a, b) => a.vendor_name.localeCompare(b.vendor_name, 'zh-TW'),
          render: (text: string, record: Vendor) => (
            <Space direction="vertical" size="small">
              <strong>{text}</strong>
              {record.vendor_code && (
                <small style={{ color: '#666' }}>統編: {record.vendor_code}</small>
              )}
            </Space>
          ),
        },
        {
          title: '聯絡資訊',
          key: 'contact',
          sorter: (a, b) => (a.contact_person || '').localeCompare(b.contact_person || '', 'zh-TW'),
          render: (_, record: Vendor) => (
            <Space direction="vertical" size="small">
              {record.contact_person && (<span><UserOutlined /> {record.contact_person}</span>)}
              {record.phone && (<span><PhoneOutlined /> {record.phone}</span>)}
              {record.email && (<span><MailOutlined /> {record.email}</span>)}
            </Space>
          ),
        },
        {
          title: '營業項目',
          dataIndex: 'business_type',
          key: 'business_type',
          width: 130,
          sorter: (a, b) => (a.business_type || '').localeCompare(b.business_type || '', 'zh-TW'),
          filters: BUSINESS_TYPE_OPTIONS.map(opt => ({ text: opt.label, value: opt.value })),
          onFilter: (value, record) => record.business_type === value,
          render: (text: string) => text ? (
            <Tag icon={<ShopOutlined />} color={getBusinessTypeColor(text)}>{text}</Tag>
          ) : <span style={{ color: '#999' }}>未設定</span>,
        },
        {
          title: '評價',
          dataIndex: 'rating',
          key: 'rating',
          sorter: (a, b) => (a.rating || 0) - (b.rating || 0),
          filters: [
            { text: '5星', value: 5 },
            { text: '4星', value: 4 },
            { text: '3星', value: 3 },
            { text: '2星', value: 2 },
            { text: '1星', value: 1 },
            { text: '未評價', value: 0 },
          ],
          onFilter: (value, record) => (record.rating || 0) === value,
          render: (rating: number) => (
            rating ? (<Tag color={getRatingColor(rating)}>{rating} 星</Tag>) : <span style={{ color: '#999' }}>未評價</span>
          ),
        },
        {
          title: '建立時間',
          dataIndex: 'created_at',
          key: 'created_at',
          sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
          render: (date: string) => new Date(date).toLocaleDateString(),
        },
        // 導航模式：刪除功能已整合至 VendorFormPage
      ];

  return (
    <div style={{ padding: pagePadding }}>
      <Card size={isMobile ? 'small' : 'default'}>
        <div style={{ marginBottom: isMobile ? 12 : 16 }}>
          <Row gutter={[8, 8]} align="middle">
            <Col xs={12} sm={6}>
              <Statistic title={isMobile ? '總數' : '總廠商數'} value={total} />
            </Col>
            <Col xs={12} sm={18} style={{ textAlign: 'right' }}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                size={isMobile ? 'small' : 'middle'}
                onClick={handleAdd}
              >
                {isMobile ? '' : '新增廠商'}
              </Button>
            </Col>
          </Row>
        </div>

        <div style={{ marginBottom: isMobile ? 12 : 16 }}>
          <Title level={isMobile ? 4 : 3} style={{ marginBottom: isMobile ? 8 : 16 }}>
            {isMobile ? '廠商' : '廠商管理'}
          </Title>

          <Space wrap style={{ marginBottom: isMobile ? 8 : 16 }}>
            <Input
              placeholder={isMobile ? '搜尋廠商' : '搜尋廠商名稱、聯絡人或營業項目'}
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ width: isMobile ? '100%' : 300 }}
              size={isMobile ? 'small' : 'middle'}
              allowClear
            />

            {!isMobile && (
              <>
                <Select
                  placeholder="營業項目篩選"
                  value={businessTypeFilter || undefined}
                  onChange={(value) => {
                    setBusinessTypeFilter(value || '');
                    setCurrent(1);  // 切換篩選時重置頁碼
                  }}
                  style={{ width: 150 }}
                  allowClear
                >
                  {BUSINESS_TYPE_OPTIONS.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select>

                <Select
                  placeholder="評價篩選"
                  value={ratingFilter}
                  onChange={(value) => {
                    setRatingFilter(value);
                    setCurrent(1);  // 切換篩選時重置頁碼
                  }}
                  style={{ width: 120 }}
                  allowClear
                >
                  <Option value={5}>5星</Option>
                  <Option value={4}>4星</Option>
                  <Option value={3}>3星</Option>
                  <Option value={2}>2星</Option>
                  <Option value={1}>1星</Option>
                </Select>
              </>
            )}
          </Space>
        </div>

        <ResponsiveTable
          columns={columns}
          dataSource={vendors}
          rowKey="id"
          loading={isLoading}
          scroll={{ x: isMobile ? 300 : undefined }}
          mobileHiddenColumns={['created_at', 'rating']}
          onRow={(record) => ({
            onClick: () => handleEdit(record),
            style: { cursor: 'pointer' },
          })}
          pagination={{
            current,
            pageSize: isMobile ? 10 : pageSize,
            total,
            showSizeChanger: !isMobile,
            showQuickJumper: !isMobile,
            showTotal: isMobile ? undefined : (total, range) =>
              `第 ${range[0]}-${range[1]} 項，共 ${total} 項`,
            onChange: (page, size) => {
              setCurrent(page);
              setPageSize(size || 10);
            },
            size: isMobile ? 'small' : 'default',
          }}
        />
      </Card>
    </div>
  );
};

export default VendorList;
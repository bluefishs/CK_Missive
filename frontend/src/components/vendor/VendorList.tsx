import React, { useState, useMemo } from 'react';
import { serverFilter, pickFilter, pickFilterNumber } from '../../utils/tableFilters';
import {
  Button,
  Input,
  Space,
  Card,
  Select,
  Typography,
  Tag,
  Row,
  Col,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  UserOutlined,
  PhoneOutlined,
  MailOutlined,
  ShopOutlined,
  TeamOutlined,
  StarOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { TableColumnType } from 'antd';
import { ResponsiveTable, ClickableStatCard } from '../common';
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

interface VendorListProps {
  vendorType?: 'subcontractor' | 'client';
  title?: string;
  createRoute?: string;
}

const VendorList: React.FC<VendorListProps> = ({ vendorType, title, createRoute }) => {
  const navigate = useNavigate();
  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  // UI 狀態
  const [current, setCurrent] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [searchText, setSearchText] = useState('');
  const [businessTypeFilter, setBusinessTypeFilter] = useState<string | undefined>('');
  const [ratingFilter, setRatingFilter] = useState<number | undefined>();
  const [statFilter, setStatFilter] = useState<string | null>(null);

  // 構建查詢參數
  const queryParams = useMemo(() => ({
    page: current,
    limit: pageSize,
    ...(searchText && { search: searchText }),
    ...(vendorType && { vendor_type: vendorType }),
    ...(businessTypeFilter && { business_type: businessTypeFilter }),
    ...(ratingFilter && { rating: ratingFilter }),
  }), [current, pageSize, searchText, vendorType, businessTypeFilter, ratingFilter]);

  // 使用 React Query Hook (自動快取與更新)
  const {
    vendors,
    pagination,
    isLoading,
  } = useVendorsPage(queryParams);

  const total = pagination?.total ?? 0;

  // 新增廠商 - 導航至表單頁
  const handleAdd = () => {
    navigate(createRoute || ROUTES.VENDOR_CREATE);
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
            <Space vertical size={0}>
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
            <Space vertical size="small">
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
            <Space vertical size="small">
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
          // 2026-09-09：後端分頁的表格帶 onFilter 會被 stripClientOnlyColumnFeatures
          // 連 filters 一起剝掉 ⇒ 原始碼看得到漏斗、線上看不到。
          // 後端本來就支援 business_type（vendor_repository.py:100），缺的是把值送過去。
          ...serverFilter<Vendor>(BUSINESS_TYPE_OPTIONS, businessTypeFilter),
          render: (text: string) => text ? (
            <Tag icon={<ShopOutlined />} color={getBusinessTypeColor(text)}>{text}</Tag>
          ) : <span style={{ color: '#999' }}>未設定</span>,
        },
        {
          title: '評價',
          dataIndex: 'rating',
          key: 'rating',
          sorter: (a, b) => (a.rating || 0) - (b.rating || 0),
          ...serverFilter<Vendor>(
            [5, 4, 3, 2, 1].map((n) => ({ value: n, label: `${n}星` })).concat([{ value: 0, label: '未評價' }]),
            ratingFilter,
          ),
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
      <Card size={isMobile ? 'small' : undefined}>
        {/* 互動統計卡片 */}
        <Row gutter={[12, 12]} style={{ marginBottom: 16 }} align="middle">
          <Col xs={12} sm={6} md={4}>
            <ClickableStatCard
              title="全部"
              value={total}
              icon={<TeamOutlined />}
              color="#1890ff"
              active={statFilter === null}
              onClick={() => { setStatFilter(null); setRatingFilter(undefined); setCurrent(1); }}
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <ClickableStatCard
              title="高評價"
              value={vendors.filter(v => (v.rating || 0) >= 4).length}
              icon={<StarOutlined />}
              color="#52c41a"
              active={statFilter === 'high_rating'}
              onClick={() => { setStatFilter(statFilter === 'high_rating' ? null : 'high_rating'); setRatingFilter(statFilter === 'high_rating' ? undefined : 4); setCurrent(1); }}
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <ClickableStatCard
              title="未評價"
              value={vendors.filter(v => !v.rating).length}
              icon={<ShopOutlined />}
              color="#faad14"
              active={statFilter === 'no_rating'}
              onClick={() => { setStatFilter(statFilter === 'no_rating' ? null : 'no_rating'); setRatingFilter(statFilter === 'no_rating' ? undefined : 0); setCurrent(1); }}
            />
          </Col>
          <Col xs={12} sm={6} md={12} style={{ textAlign: 'right' }}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              size={isMobile ? 'small' : 'middle'}
              onClick={handleAdd}
            >
              {isMobile ? '' : `新增${vendorType === 'client' ? '委託單位' : '廠商'}`}
            </Button>
          </Col>
        </Row>

        <div style={{ marginBottom: isMobile ? 12 : 16 }}>
          <Title level={isMobile ? 4 : 3} style={{ marginBottom: isMobile ? 8 : 16 }}>
            {title || (isMobile ? '廠商' : '廠商管理')}
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
          onChange={(_pagination, filters) => {
            // 2026-09-09：後端分頁 ⇒ 漏斗的值只能從這裡進查詢參數（欄位不得帶 onFilter）
            setBusinessTypeFilter(pickFilter(filters, 'business_type'));
            setRatingFilter(pickFilterNumber(filters, 'rating'));
            setCurrent(1);
          }}
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
            size: isMobile ? 'small' : undefined,
          }}
        />
      </Card>
    </div>
  );
};

export default VendorList;
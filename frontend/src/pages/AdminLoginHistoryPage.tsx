/**
 * 管理員登入紀錄頁面
 *
 * 資安管理：顯示所有使用者的登入紀錄，含帳號、登入方式、IP、日期時間。
 * 支援按使用者、登入方式、事件類型篩選。
 *
 * @version 1.0.0
 * @date 2026-03-23
 */

import { useState, useCallback, useMemo } from 'react';
import {
  Card,
  Input,
  Select,
  Row,
  Col,
  Typography,
  Tag,
  Space,
  DatePicker,
} from 'antd';
import type { TableProps } from 'antd';
import {
  SearchOutlined,
  HistoryOutlined,
  GlobalOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  StopOutlined,
  LogoutOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-tw';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { useResponsive } from '../hooks';
import { ResponsiveTable } from '../components/common';
import type { AdminLoginHistoryItem, AdminLoginHistoryResponse } from '../types/api';

dayjs.locale('zh-tw');

const { Title } = Typography;
const { RangePicker } = DatePicker;

const EVENT_LABELS: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  LOGIN_SUCCESS: { label: '登入成功', color: 'green', icon: <CheckCircleOutlined /> },
  LOGIN_FAILED: { label: '登入失敗', color: 'red', icon: <CloseCircleOutlined /> },
  LOGIN_BLOCKED: { label: '登入封鎖', color: 'orange', icon: <StopOutlined /> },
  LOGOUT: { label: '登出', color: 'blue', icon: <LogoutOutlined /> },
  TOKEN_REFRESH: { label: '權杖刷新', color: 'cyan', icon: <SyncOutlined /> },
};

const PROVIDER_LABELS: Record<string, { label: string; color: string }> = {
  email: { label: '郵箱', color: 'green' },
  google: { label: 'Google', color: 'blue' },
  line: { label: 'LINE', color: 'lime' },
  internal: { label: '內網', color: 'cyan' },
};

export const AdminLoginHistoryPage = () => {
  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchText, setSearchText] = useState('');
  const [providerFilter, setProviderFilter] = useState<string | undefined>();
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);

  const queryParams = useMemo(() => ({
    page,
    page_size: pageSize,
    ...(providerFilter && { auth_provider: providerFilter }),
  }), [page, pageSize, providerFilter]);

  const { data, isLoading } = useQuery<AdminLoginHistoryResponse>({
    queryKey: ['admin-login-history', queryParams],
    queryFn: () =>
      apiClient.post<AdminLoginHistoryResponse>(
        API_ENDPOINTS.AUTH.LOGIN_HISTORY_ADMIN,
        {},
        { params: queryParams }
      ),
    staleTime: 30 * 1000,
    retry: 1,
  });

  // 前端搜尋 + 日期篩選
  const filteredItems = useMemo(() => {
    let items = data?.items ?? [];
    if (searchText) {
      const lower = searchText.toLowerCase();
      items = items.filter(
        (item) =>
          item.email?.toLowerCase().includes(lower) ||
          item.username?.toLowerCase().includes(lower) ||
          item.ip_address?.toLowerCase().includes(lower)
      );
    }
    if (dateRange && dateRange.length === 2) {
      const [start, end] = dateRange;
      items = items.filter((item) => {
        const d = dayjs(item.created_at);
        return d.isAfter(start.startOf('day')) && d.isBefore(end.endOf('day'));
      });
    }
    return items;
  }, [data?.items, searchText, dateRange]);

  const columns: TableProps<AdminLoginHistoryItem>['columns'] = [
    {
      title: '帳號',
      dataIndex: 'email',
      key: 'email',
      width: isMobile ? 120 : 200,
      ellipsis: true,
    },
    {
      title: '事件',
      dataIndex: 'event_type',
      key: 'event_type',
      width: isMobile ? 90 : 120,
      render: (eventType: string) => {
        const info = EVENT_LABELS[eventType] || { label: eventType, color: 'default', icon: null };
        return (
          <Tag icon={info.icon} color={info.color}>
            {info.label}
          </Tag>
        );
      },
    },
    {
      title: '登入方式',
      dataIndex: 'auth_provider',
      key: 'auth_provider',
      width: 100,
      render: (provider: string | undefined) => {
        if (!provider) return <Tag>-</Tag>;
        const info = PROVIDER_LABELS[provider];
        return info ? <Tag color={info.color}>{info.label}</Tag> : <Tag>{provider}</Tag>;
      },
    },
    {
      title: 'IP 位址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 140,
      render: (ip: string | undefined) =>
        ip ? (
          <span>
            <GlobalOutlined style={{ marginRight: 4 }} />
            {ip}
          </span>
        ) : (
          '-'
        ),
    },
    {
      title: '時間',
      dataIndex: 'created_at',
      key: 'created_at',
      width: isMobile ? 130 : 180,
      render: (dt: string) => dayjs(dt).format(isMobile ? 'MM/DD HH:mm' : 'YYYY-MM-DD HH:mm:ss'),
      sorter: (a, b) => dayjs(a.created_at).unix() - dayjs(b.created_at).unix(),
      defaultSortOrder: 'descend',
    },
    {
      title: '裝置',
      dataIndex: 'user_agent',
      key: 'user_agent',
      width: 150,
      ellipsis: true,
      render: (ua: string | undefined) => {
        if (!ua) return '-';
        const lower = ua.toLowerCase();
        let browser = '瀏覽器';
        if (lower.includes('edg/')) browser = 'Edge';
        else if (lower.includes('chrome') && !lower.includes('edg')) browser = 'Chrome';
        else if (lower.includes('firefox')) browser = 'Firefox';
        else if (lower.includes('safari') && !lower.includes('chrome')) browser = 'Safari';
        let os = '';
        if (lower.includes('windows')) os = 'Win';
        else if (lower.includes('mac')) os = 'Mac';
        else if (lower.includes('linux')) os = 'Linux';
        else if (lower.includes('android')) os = 'Android';
        else if (lower.includes('iphone')) os = 'iPhone';
        return os ? `${os} ${browser}` : browser;
      },
    },
  ];

  const handleTableChange = useCallback(
    (pagination: { current?: number; pageSize?: number }) => {
      setPage(pagination.current || 1);
      setPageSize(pagination.pageSize || 20);
    },
    []
  );

  return (
    <div style={{ padding: pagePadding }}>
      <Card size={isMobile ? 'small' : undefined}>
        <div style={{ marginBottom: isMobile ? 12 : 24 }}>
          <Title level={isMobile ? 4 : 3} style={{ margin: 0 }}>
            <HistoryOutlined style={{ marginRight: 8 }} />
            登入紀錄
          </Title>
        </div>

        <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]} style={{ marginBottom: isMobile ? 12 : 16 }}>
          <Col xs={24} sm={8} md={6}>
            <Input
              placeholder="搜尋帳號 / IP"
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              size={isMobile ? 'small' : 'middle'}
              allowClear
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select
              placeholder="登入方式"
              allowClear
              value={providerFilter}
              onChange={setProviderFilter}
              style={{ width: '100%' }}
              size={isMobile ? 'small' : 'middle'}
            >
              <Select.Option value="email">郵箱</Select.Option>
              <Select.Option value="google">Google</Select.Option>
              <Select.Option value="line">LINE</Select.Option>
              <Select.Option value="internal">內網</Select.Option>
            </Select>
          </Col>
          {!isMobile && (
            <Col md={8}>
              <Space>
                <RangePicker
                  value={dateRange}
                  onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
                  size="middle"
                  allowClear
                />
              </Space>
            </Col>
          )}
        </Row>

        <ResponsiveTable
          columns={columns}
          dataSource={filteredItems}
          loading={isLoading}
          rowKey="id"
          scroll={{ x: isMobile ? 500 : 900 }}
          mobileHiddenColumns={['user_agent', 'auth_provider']}
          onChange={handleTableChange}
          pagination={{
            current: page,
            pageSize: isMobile ? 10 : pageSize,
            total: data?.total ?? 0,
            showSizeChanger: !isMobile,
            showQuickJumper: !isMobile,
            showTotal: isMobile ? undefined : (t, range) => `第 ${range[0]}-${range[1]} 項，共 ${t} 項`,
          }}
        />
      </Card>
    </div>
  );
};

export default AdminLoginHistoryPage;

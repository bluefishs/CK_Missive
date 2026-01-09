/**
 * 儀表板總覽頁面
 *
 * 架構說明：
 * - React Query: 唯一的伺服器資料來源（統計資料、近期公文）
 * - Zustand: 不使用（本頁面無需跨頁面共享狀態）
 *
 * @version 2.0.0 - 優化為 React Query 架構
 * @date 2026-01-08
 */
import React from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Button, Space, Typography, Spin } from 'antd';
import {
  FileTextOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  PlusOutlined,
  EyeOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { useDashboardPage } from '../hooks';
import { useResponsive } from '../hooks/useResponsive';

const { Title } = Typography;

// ============================================================================
// 輔助函式
// ============================================================================

const getStatusTag = (status: string) => {
  const statusMap = {
    '收文完成': { color: 'orange', text: '收文完成' },
    '使用者確認': { color: 'green', text: '使用者確認' },
    '收文異常': { color: 'red', text: '收文異常' },
  };
  const config = statusMap[status as keyof typeof statusMap] || { color: 'default', text: status };
  return <Tag color={config.color}>{config.text}</Tag>;
};

// ============================================================================
// 元件
// ============================================================================

export const DashboardPage: React.FC = () => {
  // ============================================================================
  // React Query: 唯一的伺服器資料來源
  // ============================================================================

  const {
    stats,
    recentDocuments,
    isLoading,
  } = useDashboardPage();

  // ============================================================================
  // 響應式設計
  // ============================================================================

  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });
  const cardGutter = responsiveValue({ mobile: 8, tablet: 12, desktop: 16 }) as number;

  // ============================================================================
  // 表格欄位
  // ============================================================================

  // 手機版精簡欄位，桌面版完整欄位
  const columns = isMobile
    ? [
        { title: '編號', dataIndex: 'id', key: 'id', width: 80 },
        { title: '標題', dataIndex: 'title', key: 'title', ellipsis: true },
        { title: '狀態', dataIndex: 'status', key: 'status', width: 80, render: getStatusTag },
        {
          title: '操作',
          key: 'action',
          width: 60,
          render: () => <Button type="link" icon={<EyeOutlined />} size="small" />,
        },
      ]
    : [
        { title: '公文編號', dataIndex: 'id', key: 'id', width: 120 },
        { title: '標題', dataIndex: 'title', key: 'title', ellipsis: true },
        { title: '類型', dataIndex: 'type', key: 'type', width: 100 },
        { title: '狀態', dataIndex: 'status', key: 'status', width: 120, render: getStatusTag },
        { title: '發文單位', dataIndex: 'agency', key: 'agency', ellipsis: true },
        { title: '建立日期', dataIndex: 'createDate', key: 'createDate', width: 110 },
        {
          title: '操作',
          key: 'action',
          width: 120,
          render: () => (
            <Space size="small">
              <Button type="link" icon={<EyeOutlined />} size="small">查看</Button>
              <Button type="link" icon={<EditOutlined />} size="small">編輯</Button>
            </Space>
          ),
        },
      ];

  // ============================================================================
  // 渲染
  // ============================================================================

  return (
    <div style={{ padding: pagePadding, background: '#f5f5f5', minHeight: '100vh' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <Title level={isMobile ? 4 : 2} style={{ marginBottom: isMobile ? 16 : 24, color: '#1976d2' }}>
          {isMobile ? '儀表板' : '儀表板總覽'}
        </Title>
        <Spin spinning={isLoading}>
          <Row gutter={[cardGutter, cardGutter]} style={{ marginBottom: isMobile ? 16 : 24 }}>
            <Col xs={12} sm={12} md={6} lg={6}>
              <Card size={isMobile ? 'small' : 'default'}>
                <Statistic
                  title={isMobile ? '總數' : '總公文數'}
                  value={stats.total}
                  prefix={<FileTextOutlined />}
                />
              </Card>
            </Col>
            <Col xs={12} sm={12} md={6} lg={6}>
              <Card size={isMobile ? 'small' : 'default'}>
                <Statistic
                  title="已核准"
                  value={stats.approved}
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={12} md={6} lg={6}>
              <Card size={isMobile ? 'small' : 'default'}>
                <Statistic
                  title="待處理"
                  value={stats.pending}
                  prefix={<ClockCircleOutlined />}
                  valueStyle={{ color: '#faad14' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={12} md={6} lg={6}>
              <Card size={isMobile ? 'small' : 'default'}>
                <Statistic
                  title="已駁回"
                  value={stats.rejected}
                  prefix={<ExclamationCircleOutlined />}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Card>
            </Col>
          </Row>
          <Card
            title="近期公文"
            size={isMobile ? 'small' : 'default'}
            extra={
              <Button
                type="primary"
                icon={<PlusOutlined />}
                size={isMobile ? 'small' : 'middle'}
              >
                {isMobile ? '' : '新增公文'}
              </Button>
            }
          >
            <Table
              columns={columns}
              dataSource={recentDocuments}
              pagination={false}
              scroll={{ x: isMobile ? 400 : 1000 }}
              size={isMobile ? 'small' : 'middle'}
            />
          </Card>
        </Spin>
      </div>
    </div>
  );
};

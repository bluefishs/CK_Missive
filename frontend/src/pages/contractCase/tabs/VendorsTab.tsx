/**
 * 協力廠商 Tab
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import React from 'react';
import { Card, Button, Space, Tag, Typography, Row, Col, Statistic, Empty } from 'antd';
import { ShopOutlined, PlusOutlined, UserOutlined, PhoneOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../../router/types';
import { EnhancedTable, type ResponsiveColumn } from '../../../components/common/EnhancedTable';

import type { VendorsTabProps, VendorAssociation } from './types';
import { VENDOR_ROLE_OPTIONS } from './constants';

const { Text } = Typography;
// 輔助函數
const getVendorRoleColor = (role: string) => {
  const option = VENDOR_ROLE_OPTIONS.find(opt => opt.value === role);
  return option?.color || 'default';
};

const getStatusColor = (status: string) => {
  switch (status) {
    case 'active': return 'processing';
    case 'completed': return 'success';
    case 'inactive': return 'warning';
    default: return 'default';
  }
};

const formatAmount = (amount?: number) => {
  if (!amount) return '-';
  return new Intl.NumberFormat('zh-TW').format(amount);
};

export const VendorsTab: React.FC<VendorsTabProps> = ({
  vendorList,
  projectId,
}) => {
  const navigate = useNavigate();

  const columns: ResponsiveColumn<VendorAssociation>[] = [
    {
      title: '廠商資訊',
      key: 'vendor_info',
      render: (_, record) => (
        <Space vertical size="small">
          <Text strong>{record.vendor_name}</Text>
          {record.vendor_code && <Text type="secondary">統編: {record.vendor_code}</Text>}
        </Space>
      ),
    },
    {
      title: '業務類別', hideOnMobile: true,
      dataIndex: 'role',
      key: 'role',
      width: 140,
      // 2026-08-04：就地編輯一併移除 —— 詳情頁 tab 只呈現，類別變更在填報頁。
      render: (role: string) => <Tag color={getVendorRoleColor(role)}>{role}</Tag>,
    },
    {
      title: '聯絡人',
      key: 'contact',
      render: (_, record) => (
        <Space vertical size="small">
          {record.contact_person && <span><UserOutlined /> {record.contact_person}</span>}
          {record.phone && <span><PhoneOutlined /> {record.phone}</span>}
        </Space>
      ),
    },
    {
      title: '合約金額',
      dataIndex: 'contract_amount',
      key: 'contract_amount',
      render: (amount) => <Text>NT$ {formatAmount(amount)}</Text>,
    },
    {
      title: '合作期間', hideOnMobile: true,
      key: 'period',
      render: (_, record) => (
        <Space vertical size="small">
          <span>{record.start_date} ~</span>
          <span>{record.end_date}</span>
        </Space>
      ),
    },
    {
      title: '狀態', hideOnMobile: true,
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={getStatusColor(status)}>
          {status === 'active' ? '合作中' : status === 'completed' ? '已完成' : '暫停'}
        </Tag>
      ),
    },
  ];

  return (
    <>
      <Card
        title={
          <Space>
            <ShopOutlined />
            <span>協力廠商</span>
            <Tag color="blue">{vendorList.length} 家</Tag>
          </Space>
        }
        extra={
          <Button
            type="primary" icon={<PlusOutlined />}
            onClick={() => navigate(ROUTES.CONTRACT_CASE_VENDOR_CREATE.replace(':caseId', String(projectId)))}
          >
            新增廠商
          </Button>
        }
      >
        {/* 統計概覽 */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={12}>
            <Card size="small" style={{ textAlign: 'center' }}>
              <Statistic
                title="合約總金額"
                value={vendorList.reduce((sum, v) => sum + (v.contract_amount || 0), 0)}
                formatter={value => `NT$ ${formatAmount(Number(value))}`}
              />
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small" style={{ textAlign: 'center' }}>
              <Statistic
                title="合作中廠商"
                value={vendorList.filter(v => v.status === 'active').length}
                suffix={`/ ${vendorList.length}`}
                styles={{ content: { color: '#52c41a' } }}
              />
            </Card>
          </Col>
        </Row>

        {vendorList.length > 0 ? (
          <EnhancedTable
            columns={columns}
            dataSource={vendorList}
            rowKey="id"
            pagination={false}
            size="middle"
            onRow={(row: VendorAssociation) => ({
              // 操作欄與 Modal 移除後，這是進到編輯/移除的唯一入口
              onClick: () => navigate(
                ROUTES.CONTRACT_CASE_VENDOR_EDIT
                  .replace(':caseId', String(projectId))
                  .replace(':vendorId', String(row.vendor_id)),
              ),
              style: { cursor: 'pointer' },
            })}
          />
        ) : (
          <Empty description="尚無協力廠商" />
        )}
      </Card>

    </>
  );
};

export default VendorsTab;

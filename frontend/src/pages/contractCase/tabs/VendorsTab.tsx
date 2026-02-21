/**
 * 協力廠商 Tab
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import React from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Typography,
  Row,
  Col,
  Statistic,
  Modal,
  Form,
  Select,
  InputNumber,
  DatePicker,
  Popconfirm,
  Tooltip,
  Empty,
} from 'antd';
import {
  ShopOutlined,
  PlusOutlined,
  UserOutlined,
  PhoneOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { VendorsTabProps, VendorAssociation } from './types';
import { VENDOR_ROLE_OPTIONS } from './constants';

const { Text } = Typography;
const { Option } = Select;

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
  editingVendorId,
  setEditingVendorId,
  onRoleChange,
  onDelete,
  modalVisible,
  setModalVisible,
  form,
  onAddVendor,
  vendorOptions,
  loadVendorOptions,
}) => {
  const columns: ColumnsType<VendorAssociation> = [
    {
      title: '廠商資訊',
      key: 'vendor_info',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <Text strong>{record.vendor_name}</Text>
          {record.vendor_code && <Text type="secondary">統編: {record.vendor_code}</Text>}
        </Space>
      ),
    },
    {
      title: '業務類別',
      dataIndex: 'role',
      key: 'role',
      width: 140,
      render: (role, record) =>
        editingVendorId === record.vendor_id ? (
          <Select
            size="small"
            defaultValue={role}
            style={{ width: 120 }}
            onChange={(value) => onRoleChange(record.vendor_id, value)}
            autoFocus
            open={true}
            onOpenChange={(open) => {
              if (!open) setEditingVendorId(null);
            }}
          >
            {VENDOR_ROLE_OPTIONS.map(opt => (
              <Option key={opt.value} value={opt.value}>{opt.label}</Option>
            ))}
          </Select>
        ) : (
          <Tag
            color={getVendorRoleColor(role)}
            style={{ cursor: 'pointer' }}
            onClick={() => setEditingVendorId(record.vendor_id)}
          >
            {role} <EditOutlined style={{ fontSize: 10, marginLeft: 4 }} />
          </Tag>
        ),
    },
    {
      title: '聯絡人',
      key: 'contact',
      render: (_, record) => (
        <Space direction="vertical" size="small">
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
      title: '合作期間',
      key: 'period',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <span>{record.start_date} ~</span>
          <span>{record.end_date}</span>
        </Space>
      ),
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={getStatusColor(status)}>
          {status === 'active' ? '合作中' : status === 'completed' ? '已完成' : '暫停'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Popconfirm
          title="確定要移除此廠商？"
          okText="確定"
          cancelText="取消"
          onConfirm={() => onDelete(record.vendor_id)}
        >
          <Tooltip title="移除">
            <Button size="small" danger icon={<DeleteOutlined />} aria-label="移除" />
          </Tooltip>
        </Popconfirm>
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
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
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
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
        </Row>

        {vendorList.length > 0 ? (
          <Table
            columns={columns}
            dataSource={vendorList}
            rowKey="id"
            pagination={false}
            size="middle"
          />
        ) : (
          <Empty description="尚無協力廠商" />
        )}
      </Card>

      {/* 新增廠商 Modal */}
      <Modal
        title="新增協力廠商"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
        destroyOnHidden
        afterOpenChange={(open) => {
          if (open) loadVendorOptions();
        }}
      >
        <Form form={form} layout="vertical" onFinish={onAddVendor}>
          <Form.Item name="vendor_id" label="選擇廠商" rules={[{ required: true, message: '請選擇廠商' }]}>
            <Select
              placeholder="請選擇廠商"
              showSearch
              optionFilterProp="label"
              options={vendorOptions.map(v => ({
                value: v.id,
                label: `${v.name}${v.code ? ` (${v.code})` : ''}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="role" label="業務類別" rules={[{ required: true, message: '請選擇業務類別' }]}>
            <Select placeholder="請選擇業務類別">
              {VENDOR_ROLE_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>{opt.label}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="contract_amount" label="合約金額">
            <InputNumber
              style={{ width: '100%' }}
              placeholder="請輸入合約金額"
              formatter={value => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              parser={value => value?.replace(/\$\s?|(,*)/g, '') as any}
            />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="start_date" label="合作開始日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="end_date" label="合作結束日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
            <Space>
              <Button onClick={() => setModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">新增</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default VendorsTab;

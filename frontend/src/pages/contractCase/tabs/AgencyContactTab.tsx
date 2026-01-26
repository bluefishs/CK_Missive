/**
 * 機關承辦 Tab
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
  Avatar,
  Modal,
  Form,
  Input,
  Select,
  Row,
  Col,
  Popconfirm,
  Empty,
} from 'antd';
import {
  BankOutlined,
  PlusOutlined,
  UserOutlined,
  PhoneOutlined,
  MailOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { AgencyContactTabProps } from './types';
import type { ProjectAgencyContact } from '../../../api/projectAgencyContacts';

const { Option } = Select;

export const AgencyContactTab: React.FC<AgencyContactTabProps> = ({
  agencyContacts,
  modalVisible,
  setModalVisible,
  editingId,
  setEditingId,
  form,
  onSubmit,
  onDelete,
}) => {
  const openEditModal = (contact: ProjectAgencyContact) => {
    setEditingId(contact.id);
    form.setFieldsValue(contact);
    setModalVisible(true);
  };

  const columns: ColumnsType<ProjectAgencyContact> = [
    {
      title: '姓名',
      dataIndex: 'contact_name',
      key: 'contact_name',
      render: (name: string, record: ProjectAgencyContact) => (
        <Space>
          <Avatar icon={<UserOutlined />} style={{ backgroundColor: record.is_primary ? '#1890ff' : '#87d068' }} />
          <span>{name}</span>
          {record.is_primary && <Tag color="blue">主要</Tag>}
        </Space>
      ),
    },
    {
      title: '職稱',
      dataIndex: 'position',
      key: 'position',
      render: (text: string) => text || '-',
    },
    {
      title: '單位/科室',
      dataIndex: 'department',
      key: 'department',
      render: (text: string) => text || '-',
    },
    {
      title: '聯絡電話',
      key: 'phones',
      render: (_: unknown, record: ProjectAgencyContact) => (
        <Space direction="vertical" size={0}>
          {record.phone && <span><PhoneOutlined /> {record.phone}</span>}
          {record.mobile && <span><PhoneOutlined /> {record.mobile}</span>}
          {!record.phone && !record.mobile && '-'}
        </Space>
      ),
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      render: (email: string) => email ? <a href={`mailto:${email}`}><MailOutlined /> {email}</a> : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: ProjectAgencyContact) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEditModal(record)}>
            編輯
          </Button>
          <Popconfirm
            title="確定要刪除此承辦人嗎？"
            onConfirm={() => onDelete(record.id)}
            okText="確定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>刪除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={
        <Space>
          <BankOutlined />
          <span>機關承辦</span>
          <Tag color="blue">{agencyContacts.length} 人</Tag>
        </Space>
      }
      extra={
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            setEditingId(null);
            form.resetFields();
            setModalVisible(true);
          }}
        >
          新增承辦人
        </Button>
      }
    >
      {agencyContacts.length > 0 ? (
        <Table
          columns={columns}
          dataSource={agencyContacts}
          rowKey="id"
          pagination={false}
          size="middle"
        />
      ) : (
        <Empty description="尚無機關承辦資料" />
      )}

      {/* 機關承辦 Modal */}
      <Modal
        title={editingId ? '編輯機關承辦' : '新增機關承辦'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setEditingId(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={onSubmit}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="contact_name" label="姓名" rules={[{ required: true, message: '請輸入姓名' }]}>
                <Input placeholder="請輸入承辦人姓名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="position" label="職稱">
                <Input placeholder="請輸入職稱" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="department" label="單位/科室">
            <Input placeholder="請輸入單位或科室名稱" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="phone" label="電話">
                <Input placeholder="請輸入電話" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="mobile" label="手機">
                <Input placeholder="請輸入手機" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="email" label="電子郵件">
            <Input placeholder="請輸入電子郵件" />
          </Form.Item>
          <Form.Item name="is_primary" valuePropName="checked">
            <Select placeholder="是否為主要承辦人" allowClear>
              <Option value={true}>是 (主要承辦人)</Option>
              <Option value={false}>否</Option>
            </Select>
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} placeholder="請輸入備註" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default AgencyContactTab;

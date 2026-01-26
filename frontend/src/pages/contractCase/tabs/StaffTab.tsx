/**
 * 承辦同仁 Tab
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
  Select,
  Popconfirm,
  Tooltip,
  Empty,
} from 'antd';
import {
  TeamOutlined,
  PlusOutlined,
  UserOutlined,
  PhoneOutlined,
  MailOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { StaffTabProps, Staff } from './types';
import { STAFF_ROLE_OPTIONS } from './constants';

const { Option } = Select;

// 輔助函數
const getStaffRoleColor = (role: string) => {
  const option = STAFF_ROLE_OPTIONS.find(opt => opt.value === role);
  return option?.color || 'default';
};

export const StaffTab: React.FC<StaffTabProps> = ({
  staffList,
  editingStaffId,
  setEditingStaffId,
  onRoleChange,
  onDelete,
  modalVisible,
  setModalVisible,
  form,
  onAddStaff,
  userOptions,
  loadUserOptions,
}) => {
  const columns: ColumnsType<Staff> = [
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space>
          <Avatar icon={<UserOutlined />} style={{ backgroundColor: getStaffRoleColor(record.role) === 'red' ? '#f5222d' : '#1890ff' }} />
          <span style={{ fontWeight: 500 }}>{name}</span>
        </Space>
      ),
    },
    {
      title: '角色/職責',
      dataIndex: 'role',
      key: 'role',
      width: 140,
      render: (role, record) =>
        editingStaffId === record.id ? (
          <Select
            size="small"
            defaultValue={role}
            style={{ width: 130 }}
            onChange={(value) => onRoleChange(record.id, value)}
            autoFocus
            open={true}
            onOpenChange={(open) => {
              if (!open) setEditingStaffId(null);
            }}
          >
            {STAFF_ROLE_OPTIONS.map(opt => (
              <Option key={opt.value} value={opt.value}>{opt.label}</Option>
            ))}
          </Select>
        ) : (
          <Tag
            color={getStaffRoleColor(role)}
            style={{ cursor: 'pointer' }}
            onClick={() => setEditingStaffId(record.id)}
          >
            {role} <EditOutlined style={{ fontSize: 10, marginLeft: 4 }} />
          </Tag>
        ),
    },
    {
      title: '部門',
      dataIndex: 'department',
      key: 'department',
    },
    {
      title: '聯絡方式',
      key: 'contact',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          {record.phone && <span><PhoneOutlined /> {record.phone}</span>}
          {record.email && <span><MailOutlined /> {record.email}</span>}
        </Space>
      ),
    },
    {
      title: '加入日期',
      dataIndex: 'join_date',
      key: 'join_date',
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'active' ? 'success' : 'default'}>
          {status === 'active' ? '在職' : '離職'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Popconfirm
          title="確定要移除此同仁？"
          okText="確定"
          cancelText="取消"
          onConfirm={() => onDelete(record.id)}
        >
          <Tooltip title="移除">
            <Button size="small" danger icon={<DeleteOutlined />} />
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
            <TeamOutlined />
            <span>承辦同仁</span>
            <Tag color="blue">{staffList.length} 人</Tag>
          </Space>
        }
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
            新增同仁
          </Button>
        }
      >
        {staffList.length > 0 ? (
          <Table
            columns={columns}
            dataSource={staffList}
            rowKey="id"
            pagination={false}
            size="middle"
          />
        ) : (
          <Empty description="尚無承辦同仁" />
        )}
      </Card>

      {/* 新增同仁 Modal */}
      <Modal
        title="新增承辦同仁"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={500}
        destroyOnHidden
        afterOpenChange={(open) => {
          if (open) loadUserOptions();
        }}
      >
        <Form form={form} layout="vertical" onFinish={onAddStaff}>
          <Form.Item name="user_id" label="選擇同仁" rules={[{ required: true, message: '請選擇同仁' }]}>
            <Select
              placeholder="請選擇同仁"
              showSearch
              optionFilterProp="label"
              options={userOptions.map(u => ({
                value: u.id,
                label: `${u.name} (${u.email})`,
              }))}
            />
          </Form.Item>
          <Form.Item name="role" label="角色/職責" rules={[{ required: true, message: '請選擇角色/職責' }]}>
            <Select placeholder="請選擇角色/職責">
              {STAFF_ROLE_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>{opt.label}</Option>
              ))}
            </Select>
          </Form.Item>
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

export default StaffTab;
